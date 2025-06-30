import time
import re
import json
import uuid
from datetime import datetime
from pathlib import Path
from flask import Blueprint, app, request, jsonify, session, render_template, Response, stream_with_context
from models import auth_manager, rate_limiter
from models.session_manager import session_manager
from models.database import db_manager
from utils.ai_client import ai_client
from models.request_manager import request_manager
from models.cache_manager import context_cache, cache_context
import requests
from config import DATABASE_FILE, FEEDBACK_DATABASE_FILE
from flask_wtf.csrf import CSRFProtect, validate_csrf
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Regexp
import secrets
import os
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from models.auth_manager import auth_manager
from models.rate_limiter import rate_limiter
import stripe
import sqlite3
from models.anonymous_limiter import anonymous_limiter

logger = logging.getLogger(__name__)

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

# ===== CONFIGURAÇÃO DE ONDE SALVAR FEEDBACK (SEGURO) =====
FEEDBACK_DIR = Path(__file__).parent.parent / 'data' / 'feedbacks'
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)

def get_safe_feedback_path():
    """Retorna path seguro para feedback"""
    filename = f"feedbacks_{datetime.now().strftime('%Y%m')}.json"
    safe_filename = secure_filename(filename)
    return FEEDBACK_DIR / safe_filename

# ===== CLASSE DE FORMULÁRIO DE FEEDBACK =====
class FeedbackForm(FlaskForm):
    titulo = StringField('Título', validators=[
        DataRequired(message="Título obrigatório"),
        Length(min=5, max=100, message="Título deve ter 5-100 caracteres"),
        Regexp(r'^[a-zA-Z0-9\s\.,!?-]+$', message="Caracteres inválidos")
    ])
    descricao = TextAreaField('Descrição', validators=[
        DataRequired(message="Descrição obrigatória"),
        Length(min=10, max=1000, message="Descrição deve ter 10-1000 caracteres"),
        Regexp(r'^[a-zA-Z0-9\s\.,!?\n-]+$', message="Caracteres inválidos")
    ])

def create_main_blueprint(csrf):
    main_bp = Blueprint('main', __name__)

    # ===== FUNÇÕES DE FEEDBACK =====
    def salvar_feedback_json(feedback_data):
        """Salva feedback em arquivo JSON"""
        try:
            feedback_path = get_safe_feedback_path()
            if feedback_path.exists():
                with open(feedback_path, 'r', encoding='utf-8') as f:
                    feedbacks = json.load(f)
            else:
                feedbacks = []
            
            feedback_data['id'] = str(uuid.uuid4())
            feedback_data['timestamp'] = datetime.now().isoformat()
            feedbacks.append(feedback_data)
            
            with open(feedback_path, 'w', encoding='utf-8') as f:
                json.dump(feedbacks, f, ensure_ascii=False, indent=2)
            
            return {
                'status': 'sucesso',
                'feedback_id': feedback_data['id'],
                'message': 'Feedback salvo com sucesso!'
            }
            
        except Exception as e:
            return {
                'status': 'erro',
                'message': f'Erro ao salvar: {str(e)}'
            }

    @main_bp.route('/')
    def home():
        """Página principal do app"""
        return render_template('index.html')

    @main_bp.route('/feedback.html')
    def feedback_page():
        """Página de feedback do sistema"""
        return render_template('feedback.html')

    @main_bp.route('/status')
    def status():
        """Status do sistema"""
        status_data = session_manager.get_status()
        return jsonify({
            'status': 'online',
            'usuarios_ativos': status_data['usuarios_ativos'],
            'maximo_usuarios': status_data['maximo_usuarios'],
            'disponivel': status_data['usuarios_ativos'] < status_data['maximo_usuarios'],
            'fila_espera': status_data['fila_espera'],
            'stats': status_data['stats']
        })

    @cache_context(timeout=300)
    def get_user_context(session_id):
        """Busca contexto do usuário com cache inteligente"""
        try:
            dados_contexto_result = db_manager.buscar_dados(session_id=session_id)
            
            if (dados_contexto_result['status'] == 'sucesso' and 
                dados_contexto_result.get('dados') and 
                len(dados_contexto_result['dados']) > 0):
                
                contexto_dados = "Informações conhecidas sobre você:\n"
                for dado in dados_contexto_result['dados'][:5]:
                    contexto_dados += f"- {dado['chave']}: {dado['valor']}\n"
                
                return contexto_dados
            else:
                return "Primeira conversa - ainda não sei nada sobre você."
                
        except Exception as e:
            print(f" Erro ao buscar contexto: {e}")
            return "Erro ao acessar dados salvos."

    def processar_thinking_mode(mensagem, frontend_thinking_mode, session_data=None):
        """
        Processa thinking mode mas MANTÉM comandos na mensagem
        """
        
        # 1. PRIORIDADE: Frontend definiu explicitamente  
        if frontend_thinking_mode is not None:
            print(f" [THINKING] Frontend definiu: {frontend_thinking_mode}")
            return frontend_thinking_mode, mensagem  # NÃO REMOVE COMANDOS
        
        # 2. DETECTAR comandos inline para determinar modo
        thinking_mode_final = None
        
        if '/no_think' in mensagem:
            thinking_mode_final = False
            print(f"[THINKING] Comando /no_think detectado")
        
        if '/think' in mensagem:
            thinking_mode_final = True  
            print(f"[THINKING] Comando /think detectado")
        
        # RETORNAR MENSAGEM ORIGINAL COM COMANDOS
        if thinking_mode_final is not None:
            return thinking_mode_final, mensagem
        
        # 3. Padrão do sistema
        default_mode = session_data.get('default_thinking', False) if session_data else False
        print(f" [THINKING] Usando padrão: {default_mode}")
        
        return default_mode, mensagem

    @main_bp.route('/chat-stream', methods=['POST'])
    def chat_stream():
        """🌊 CHAT STREAMING COM SISTEMA DE 5 MENSAGENS GRATUITAS"""
        try:

            raw_data = request.get_data()
            content_type = request.content_type

            print(f" [DEBUG] Raw data: {raw_data}")
            print(f" [DEBUG] Content-Type: {content_type}")
            print(f" [DEBUG] Primeiros 500 chars: {raw_data[:500]}")
            
            # Tentar parse JSON
            data = {}
            if content_type == 'application/json' and raw_data:
                try:
                    data = request.get_json()
                    print(f" [DEBUG] JSON parseado: {data}")
                except Exception as json_error:
                    print(f" [DEBUG] Erro no JSON: {json_error}")
                    print(f" [DEBUG] Raw data que causou erro: {raw_data[:100]}")
                    return jsonify({'error': f'JSON inválido: {str(json_error)}'}), 400

            # 1. IDENTIFICAR TIPO DE USUÁRIO
            user_id = session.get('user_id')
            is_authenticated = bool(user_id)
            
            print(f" [AUTH] User ID: {user_id}, Autenticado: {is_authenticated}")
            
            # 2. OBTER SESSION_ID PARA ANÔNIMOS
            session_id = session.get('titan_session_id')
            if not session_id:
                return jsonify({
                    'error': 'Sessão não encontrada. Por favor, inicie uma nova sessão.',
                    'type': 'session_error',
                    'action_required': 'init_session'
                }), 401

            # 3. VERIFICAR LIMITES BASEADO NO TIPO DE USUÁRIO
            if is_authenticated:
                # USUÁRIO AUTENTICADO - USAR RATE LIMITER NORMAL
                can_send, error_msg = rate_limiter.can_send_message(user_id)
                if not can_send:
                    return jsonify({
                        'error': error_msg,
                        'type': 'rate_limit_authenticated',
                        'user_id': user_id
                    }), 429
                    
                print(f"[AUTH USER] Limite OK para user {user_id}")
            else:
                # USUÁRIO ANÔNIMO - USAR ANONYMOUS LIMITER
                can_send, limit_info = anonymous_limiter.can_send_message(session_id)
                if not can_send:
                    return jsonify({
                        'error': 'Você atingiu o limite de mensagens do Titan gratuito, crie sua conta para liberar mais mensagens.',
                        'type': 'error',
                        'action_required': limit_info['action_required'],
                        'messages_used': limit_info['messages_used'],
                        'limit': limit_info['limit'],
                        'remaining': limit_info['remaining']
                    }), 429
                    
                print(f"[ANON USER] Limite OK - {limit_info['used']}/5 mensagens")

            # 4. VALIDAÇÃO DA MENSAGEM
            print(f" [DEBUG CHAT] Raw data antes do parsing: {raw_data}")
            print(f" [DEBUG CHAT] Content-Type: {content_type}")
            
            # Tentar parse JSON
            data = {}
            if content_type == 'application/json' and raw_data:
                try:
                    data = request.get_json()
                    print(f" [DEBUG CHAT] JSON parseado: {data}")
                except Exception as json_error:
                    print(f" [DEBUG CHAT] Erro no JSON: {json_error}")
                    print(f" [DEBUG CHAT] Raw data que causou erro: {raw_data[:100]}")
                    return jsonify({'error': f'JSON inválido: {str(json_error)}'}), 400
            
            print(f" [DEBUG CHAT] Data (após parsing): {data}")
            mensagem = data.get('mensagem', '').strip()
            thinking_mode = data.get('thinking_mode', False)
            print(f" [DEBUG CHAT] Mensagem extraída: '{mensagem}'")
            print(f" [DEBUG CHAT] Thinking mode extraído: {thinking_mode}")
            
            if not mensagem:
                return jsonify({'error': 'Mensagem obrigatória'}), 400

            # 5. VERIFICAR THINKING MODE (APENAS PARA AUTENTICADOS)
            if thinking_mode and not is_authenticated:
                return jsonify({
                    'error': 'Thinking Mode disponível apenas para usuários registrados. Crie sua conta gratuitamente!',
                    'type': 'feature_restricted',
                    'upgrade_needed': True,
                    'action_required': 'create_account'
                }), 402  # Payment Required

            if is_authenticated:
                # Verificar se o plano permite thinking mode
                user_limits = auth_manager.get_user_limits(user_id)
                features = user_limits.get('features', [])
                
                if thinking_mode and 'thinking_mode' not in features:
                    return jsonify({
                        'error': 'Thinking Mode disponível apenas para usuários Premium. Faça upgrade do seu plano!',
                        'type': 'feature_restricted',
                        'upgrade_needed': True,
                        'current_plan': user_limits.get('plan_name', 'Gratuito')
                    }), 402

            # 6. VERIFICAR OLLAMA
            try:
                test_response = requests.get("http://localhost:11434/api/tags", timeout=5)
                if test_response.status_code != 200:
                    return jsonify({'error': 'IA temporariamente indisponível'}), 503
            except:
                return jsonify({'error': 'IA offline'}), 503

            # 7. REQUEST MANAGER
            request_id = str(uuid.uuid4())
            
            # 8. MENSAGENS
            messages = [
                {"role": "system", "content": "Você é o Titan, um assistente inteligente."},
                {"role": "user", "content": mensagem}
            ]

            print(f"💬 [CHAT] {'Auth' if is_authenticated else 'Anon'}: {mensagem[:50]}...")

            # 9. THINKING MODE FINAL (SEMPRE FALSE PARA ANÔNIMOS)
            final_thinking_mode = thinking_mode if is_authenticated else False

            print(f"[AI] Thinking solicitado={thinking_mode}, final={final_thinking_mode}")

            # 10. STREAM GENERATOR
            def generate():
                try:
                    chunks_received = 0
                    for chunk in ai_client.send_message_streaming(
                        messages,
                        use_tools=True,
                        thinking_mode=final_thinking_mode,
                        session_id=session_id,
                        request_id=request_id
                    ):
                        yield f"data: {json.dumps(chunk, ensure_ascii=False, separators=(',', ':'))}\n\n"
                        chunks_received += 1
                        
                    # REGISTRAR USO APÓS STREAM COMPLETO
                    if chunks_received > 0:
                        if is_authenticated:
                            # Usuário autenticado - usar rate limiter normal
                            rate_limiter.track_message_usage(
                                user_id=user_id,
                                character_count=len(mensagem),
                                is_thinking=final_thinking_mode
                            )
                            print(f"📊 [USAGE AUTH] Registrado para user {user_id}")
                        else:
                            # Usuário anônimo - usar anonymous limiter
                            usage_result = anonymous_limiter.track_message_usage(session_id)
                            print(f"📊 [USAGE ANON] {usage_result['messages_used']}/5 mensagens")
                            
                            # ENVIAR INFO DE LIMITE NA RESPOSTA
                            limit_chunk = {
                                "type": "limit_info",
                                "remaining": usage_result['remaining'],
                                "used": usage_result['messages_used'],
                                "limit": 5,
                                "limit_reached": usage_result['limit_reached']
                            }
                            yield f"data: {json.dumps(limit_chunk)}\n\n"
                        
                except PermissionError as pe:
                    error_chunk = {"type": "error", "error": str(pe), "action_required": "create_account"}
                    yield f"data: {json.dumps(error_chunk, ensure_ascii=False, separators=(',', ':'))}\n\n"
                except Exception as e:
                    error_chunk = {"type": "error", "error": str(e)}
                    yield f"data: {json.dumps(error_chunk, ensure_ascii=False, separators=(',', ':'))}\n\n"

            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
            )

        except Exception as e:
            print(f" Erro no chat: {e}")
            return jsonify({'error': str(e)}), 500
        
    @main_bp.route('/thinking-mode', methods=['GET', 'POST'])
    def thinking_mode():
        """Gerenciar thinking mode"""
        if request.method == 'POST':
            data = request.json
            enabled = data.get('enabled')
            session['thinking_mode'] = enabled
            return jsonify({'status': 'sucesso', 'thinking_mode': enabled})
        else:
            current_mode = session.get('thinking_mode', False)
            return jsonify({'thinking_mode': current_mode, 'status': 'sucesso'})

    @main_bp.route('/debug-session')
    def debug_session():
        """Debug da sessão atual"""
        flask_session_id = session.get('titan_session_id')
        
        debug_info = {
            'flask_session_id': flask_session_id,
            'session_exists_in_manager': False,
            'session_data': None,
            'manager_status': session_manager.get_status(),
            'timestamp': datetime.now().isoformat()
        }
        
        if flask_session_id:
            session_data = session_manager.get_session_data(flask_session_id)
            debug_info['session_exists_in_manager'] = session_data is not None
            if session_data:
                debug_info['session_data'] = {
                    'ip': session_data.get('ip'),
                    'inicio': session_data.get('inicio'),
                    'ultima_atividade': session_data.get('ultima_atividade'),
                    'requests_count': session_data.get('requests_count'),
                    'chat_history_length': len(session_data.get('chat_history', []))
                }
        
        return jsonify(debug_info)

    # ===== OUTRAS ROTAS ESSENCIAIS =====
    @main_bp.route('/new-session', methods=['POST'])
    def new_session():
        """Iniciar nova sessão"""
        try:
            user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            
            if not session_manager.pode_entrar():
                return jsonify({'status': 'erro', 'message': 'Sistema ocupado'}), 503
            
            backend_session_id = session_manager.criar_sessao(user_ip)
            if not backend_session_id:
                return jsonify({'status': 'erro', 'message': 'Falha ao criar sessão'}), 500
            
            session['titan_session_id'] = backend_session_id
            session.permanent = True
            
            return jsonify({
                'status': 'sucesso',
                'session_id': backend_session_id,
                'message': 'Nova sessão criada'
            })
            
        except Exception as e:
            return jsonify({'status': 'erro', 'message': str(e)}), 500

    @main_bp.route('/cancel-request', methods=['POST'])
    def cancel_request():
        """Cancelar request ativa da sessão"""
        try:
            session_id = session.get('titan_session_id')
            if not session_id:
                return jsonify({'erro': 'Sessão inválida'}), 401
            
            request_manager.cancel_session_requests(session_id)
            return jsonify({'status': 'sucesso', 'message': 'Requests canceladas'})
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500

    @main_bp.route('/clear-chat-history', methods=['POST'])
    def clear_chat_history():
        """Limpar histórico de chat"""
        try:
            session_id = session.get('titan_session_id')
            if not session_id:
                return jsonify({"erro": "Sessão inválida"}), 401
            
            session_manager.update_chat_history(session_id, [])
            return jsonify({'status': 'sucesso', 'message': 'Histórico limpo'})
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500

    # ===== ROTAS DE FEEDBACK =====
    @main_bp.route('/api/feedback', methods=['POST'])
    def criar_feedback():
        try:
            titulo = request.json.get('titulo', '')
            descricao = request.json.get('descricao', '')
            
            if len(titulo) < 5 or len(descricao) < 10:
                return jsonify({'erro': 'Título e descrição muito curtos'}), 400
            
            session_id = session.get('titan_session_id', 'anonymous')
            user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            
            feedback_data = {
                'session_id': session_id,
                'user_ip': user_ip,
                'tipo': request.json.get('tipo', 'geral'),
                'titulo': titulo,
                'descricao': descricao,
                'thinking_mode': request.json.get('thinking_mode', False)
            }
            
            resultado = salvar_feedback_json(feedback_data)
            return jsonify(resultado)
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
        
    @main_bp.route('/api/recent-chats')
    def get_recent_chats():
        """Buscar conversas recentes da sessão"""
        try:
            session_id = session.get('titan_session_id')
            if not session_id:
                return jsonify({'status': 'sucesso', 'chats': []})
            
            # Usar o chat_manager existente
            from models.chat_manager import chat_manager
            history = chat_manager.load_history(session_id=session_id)
            
            # Pegar apenas as 10 mais recentes
            recent_chats = history[:10] if history else []
            
            return jsonify({
                'status': 'sucesso',
                'chats': recent_chats
            })
        except Exception as e:
            return jsonify({'status': 'erro', 'message': str(e)})
        
    @main_bp.route('/api/save-chat', methods=['POST'])
    def save_chat():
        """Salvar conversa"""
        try:
            session_id = session.get('titan_session_id')
            if not session_id:
                return jsonify({'status': 'erro', 'message': 'Sessão inválida'})
            
            chat_data = request.json
            chat_data['session_id'] = session_id
            
            from models.chat_manager import chat_manager
            result = chat_manager.save_chat(chat_data)
            
            return jsonify(result)
        except Exception as e:
            return jsonify({'status': 'erro', 'message': str(e)})

    # ===== ROTAS ADMIN =====
    @main_bp.route('/admin/stats')
    def admin_stats():
        """Estatísticas do sistema"""
        return jsonify(session_manager.get_status())

    @main_bp.route('/end-session', methods=['POST'])
    def end_session():
        """Finalizar sessão"""
        return jsonify({'status': 'sucesso'})

    @main_bp.route('/feedback', methods=['POST'])
    @limiter.limit("50 per minute") 
    def feedback_like_dislike():
        """👍👎 Endpoint para like/dislike usando banco separado"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'Dados não fornecidos'}), 400
            
            # Extrair dados
            feedback_type = data.get('type')
            content = data.get('content', '')
            session_id = data.get('session_id') or session.get('titan_session_id')
            
            # Validar apenas like/dislike
            if feedback_type not in ['like', 'dislike']:
                return jsonify({'error': 'Apenas like/dislike são aceitos'}), 400
            
            # Informações do sistema
            user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            user_agent = request.headers.get('User-Agent', '')
            thinking_mode = session.get('thinking_mode', False)
            
            # USAR BANCO SEPARADO
            from models.feedback_database import feedback_db
            
            resultado = feedback_db.salvar_feedback(
                session_id=session_id,
                user_ip=user_ip,
                action_type=feedback_type,
                message_content=content,
                thinking_mode=thinking_mode,
                user_agent=user_agent
            )
            
            return jsonify(resultado), 200
            
        except Exception as e:
            print(f" Erro ao registrar {data.get('type', 'feedback')}: {str(e)}")
            return jsonify({'error': 'Não foi possível registrar a avaliação'}), 500

    @main_bp.route('/feedback/stats')
    def feedback_stats():
        """📊 Estatísticas de like/dislike do banco separado"""
        try:
            from models.feedback_database import feedback_db
            
            # Estatísticas gerais
            stats = feedback_db.obter_estatisticas()
            
            # Adicionar informações extras
            if stats['status'] == 'sucesso':
                stats['banco_usado'] = 'titan_feedbacks.db'
                stats['separado_da_memoria'] = True
            
            return jsonify(stats)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        
    @main_bp.route('/debug/memoria')
    def debug_memoria():
        """Ver dados da memória persistente dos usuários"""
        try:
            import sqlite3
            from config import DATABASE_FILE
            
            if not DATABASE_FILE.exists():
                return jsonify({'error': 'Banco de memória não encontrado'})
            
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            # Dados por sessão
            cursor.execute("""
                SELECT session_id, COUNT(*) as total_dados,
                   GROUP_CONCAT(chave, ', ') as chaves_salvas
                FROM dados_salvos 
                GROUP BY session_id
                ORDER BY total_dados DESC
            """)
            
            sessoes = []
            for row in cursor.fetchall():
                sessoes.append({
                    'session_id': row[0][:8] + '...',
                    'total_dados': row[1],
                    'chaves_salvas': row[2]
                })
            
            # Dados mais recentes
            cursor.execute("""
                SELECT session_id, chave, valor, categoria, data_criacao
                FROM dados_salvos 
                ORDER BY data_criacao DESC 
                LIMIT 10
            """)
            
            dados_recentes = []
            for row in cursor.fetchall():
                dados_recentes.append({
                    'session_id': row[0][:8] + '...',
                    'chave': row[1],
                    'valor': row[2][:50] + '...' if len(row[2]) > 50 else row[2],
                    'categoria': row[3],
                    'data_criacao': row[4]
                })
            
            conn.close()
            
            return jsonify({
                'banco': str(DATABASE_FILE),
                'sessoes_com_dados': sessoes,
                'dados_recentes': dados_recentes,
                'total_sessoes': len(sessoes),
                'status': 'sucesso'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @main_bp.route('/debug/feedbacks')
    def debug_feedbacks():
        """👍👎 Ver feedbacks de like/dislike"""
        try:
            from models.feedback_database import feedback_db
            
            # Estatísticas gerais
            stats = feedback_db.obter_estatisticas()
            
            # Feedbacks recentes
            feedbacks_recentes = feedback_db.listar_feedbacks(limit=20)
            
            # Estatísticas por modo thinking
            import sqlite3
            from config import FEEDBACK_DATABASE_FILE
            
            conn = sqlite3.connect(FEEDBACK_DATABASE_FILE)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT thinking_mode, action_type, COUNT(*) 
                FROM action_feedbacks 
                GROUP BY thinking_mode, action_type
            """)
            
            por_thinking = {}
            for row in cursor.fetchall():
                modo = 'thinking' if row[0] else 'direto'
                if modo not in por_thinking:
                    por_thinking[modo] = {}
                por_thinking[modo][row[1]] = row[2]
            
            conn.close()
            
            return jsonify({
                'banco': str(FEEDBACK_DATABASE_FILE),
                'estatisticas_gerais': stats,
                'feedbacks_recentes': feedbacks_recentes,
                'por_modo_thinking': por_thinking,
                'status': 'sucesso'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @main_bp.route('/debug/sistema')
    def debug_sistema():
        """🔧 Visão geral do sistema"""
        try:
            from config import DATABASE_FILE, FEEDBACK_DATABASE_FILE
            from models.session_manager import session_manager
            
            # Status das sessões
            status_sessoes = session_manager.get_status()
            
            # Verificar arquivos
            arquivos = {
                'memoria_existe': DATABASE_FILE.exists(),
                'memoria_tamanho': DATABASE_FILE.stat().st_size if DATABASE_FILE.exists() else 0,
                'feedbacks_existe': FEEDBACK_DATABASE_FILE.exists(),
                'feedbacks_tamanho': FEEDBACK_DATABASE_FILE.stat().st_size if FEEDBACK_DATABASE_FILE.exists() else 0
            }
            
            return jsonify({
                'sessoes_ativas': status_sessoes,
                'arquivos_banco': arquivos,
                'paths': {
                    'memoria': str(DATABASE_FILE),
                    'feedbacks': str(FEEDBACK_DATABASE_FILE)
                },
                'status': 'sucesso'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        
    @main_bp.route('/debug/mensagens-dislike')
    def debug_mensagens_dislike():
        """👎 Ver mensagens que receberam dislike"""
        try:
            from models.feedback_database import feedback_db
            
            # Obter mensagens com dislike
            resultado = feedback_db.obter_mensagens_com_dislike(limit=50)
            
            if resultado['status'] == 'sucesso':
                return jsonify({
                    'banco': str(FEEDBACK_DATABASE_FILE),
                    'mensagens_problematicas': resultado['mensagens_com_dislike'],
                    'total_mensagens': resultado['total_encontradas'],
                    'status': 'sucesso'
                })
            else:
                return jsonify(resultado), 500
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @main_bp.route('/debug/analise-dislike')
    def debug_analise_dislike():
        """📊 Análise de padrões nas mensagens com dislike"""
        try:
            from models.feedback_database import feedback_db
            
            # Análise de padrões
            analise = feedback_db.analisar_padroes_dislike()
            
            return jsonify(analise)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @main_bp.route('/debug/mensagem-dislike/<feedback_id>')
    def debug_mensagem_dislike_detalhada(feedback_id):
        """ Ver mensagem específica com dislike em detalhes"""
        try:
            from models.feedback_database import feedback_db
            
            resultado = feedback_db.obter_mensagem_dislike_por_id(feedback_id)
            
            return jsonify(resultado)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        
    @main_bp.route('/debug/dislikes')
    def debug_dislikes():
        """👎 Ver todas as mensagens que receberam dislike"""
        try:
            from models.feedback_database import feedback_db
            
            resultado = feedback_db.obter_mensagens_com_dislike_detalhado(limit=50)
            
            return jsonify(resultado)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @main_bp.route('/analytics')
    def analytics_dashboard():
        """Dashboard de analytics usando dados existentes"""
        # MOVER IMPORT PARA O TOPO DA FUNÇÃO
        import json
        
        try:
            print(" [ANALYTICS] Iniciando...")
            
            # Coletar todos os dados
            session_stats = session_manager.get_status()
            print(f"[ANALYTICS] Session stats: {session_stats}")
            
            from models.feedback_database import feedback_db
            feedback_stats = feedback_db.obter_estatisticas()
            print(f"[ANALYTICS] Feedback stats: {feedback_stats}")
            
            mensagens_dislike = feedback_db.obter_mensagens_com_dislike(limit=5)
            
            from models.cache_manager import context_cache
            cache_stats = context_cache.get_stats()
            
            import sqlite3
            try:
                conn = sqlite3.connect(DATABASE_FILE)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT COUNT(DISTINCT session_id) as usuarios_hoje
                    FROM dados_salvos 
                    WHERE date(data_criacao) = date('now')
                """)
                usuarios_hoje = cursor.fetchone()[0] or 0
                
                cursor.execute("""
                    SELECT COUNT(*) as total_memorias
                    FROM dados_salvos 
                    WHERE ativo = 1
                """)
                total_memorias = cursor.fetchone()[0] or 0
                
                cursor.execute("""
                    SELECT strftime('%H', data_criacao) as hora, COUNT(*) as atividade
                    FROM dados_salvos 
                    WHERE datetime(data_criacao) >= datetime('now', '-24 hours')
                    GROUP BY strftime('%H', data_criacao)
                    ORDER BY hora
                """)
                atividade_horas = dict(cursor.fetchall())
                
                cursor.execute("""
                    SELECT categoria, COUNT(*) as total
                    FROM dados_salvos 
                    WHERE ativo = 1
                    GROUP BY categoria
                    ORDER BY total DESC
                    LIMIT 5
                """)
                categorias_top = cursor.fetchall()
                
                conn.close()
                
            except Exception as e:
                print(f"Erro ao buscar dados SQLite: {e}")
                usuarios_hoje = 0
                total_memorias = 0
                atividade_horas = {}
                categorias_top = []
            
            # CORREÇÃO: Verificar tipo de usuarios_unicos_hoje
            usuarios_unicos_stat = session_stats['stats'].get('usuarios_unicos_hoje', [])
            
            # Se for int, converter para 0; se for list, pegar o len
            if isinstance(usuarios_unicos_stat, int):
                usuarios_unicos_count = usuarios_unicos_stat
            elif isinstance(usuarios_unicos_stat, list):
                usuarios_unicos_count = len(usuarios_unicos_stat)
            else:
                usuarios_unicos_count = 0
            
            # CRIAR JSON LIMPO AQUI NO PYTHON
            analytics_data = {
                'usuarios_ativos': session_stats['usuarios_ativos'],
                'usuarios_hoje': usuarios_hoje,
                'total_requests': session_stats['stats']['total_requests'],
                'uptime_horas': round(session_stats['uptime'] / 3600, 1),
                'likes': feedback_stats.get('likes', 0),
                'dislikes': feedback_stats.get('dislikes', 0),
                'aprovacao': feedback_stats.get('aprovacao', 0),
                'total_avaliacoes': feedback_stats.get('total_avaliacoes', 0),
                'total_memorias': total_memorias,
                'cached_sessions': cache_stats['cached_sessions'],
                'cache_efficiency': round((cache_stats['cached_sessions'] / max(cache_stats['total_tracked'], 1)) * 100, 1),
                'atividade_horas': atividade_horas,
                'categorias_top': categorias_top,
                'mensagens_problematicas': mensagens_dislike.get('mensagens_com_dislike', [])[:3],
                'max_usuarios': session_stats['maximo_usuarios'],
                'requests_rejeitados': session_stats['stats']['requests_rejeitados'],
                'usuarios_unicos_hoje': usuarios_unicos_count  # CORRIGIDO
            }
            
            # PASSAR JSON COMO STRING SEGURA
            analytics_json = json.dumps(analytics_data, ensure_ascii=False)
            print(f"[ANALYTICS] JSON criado com {len(analytics_json)} caracteres")
            
            return render_template('analytics.html', analytics_json=analytics_json)
            
        except Exception as e:
            print(f" [ANALYTICS] ERRO: {e}")
            import traceback
            traceback.print_exc()
            
            # JSON já está no escopo agora
            error_data = {'erro': str(e)}
            analytics_json = json.dumps(error_data, ensure_ascii=False)
            return render_template('analytics.html', analytics_json=analytics_json)
        
    @main_bp.route('/analytics/api')
    def analytics_api():
        """API JSON para atualizações em tempo real"""
        try:
            session_stats = session_manager.get_status()
            from models.feedback_database import feedback_db
            feedback_stats = feedback_db.obter_estatisticas()
            from models.cache_manager import context_cache
            cache_stats = context_cache.get_stats()
            
            return jsonify({
                'timestamp': datetime.now().isoformat(),
                'usuarios_ativos': session_stats['usuarios_ativos'],
                'total_requests': session_stats['stats']['total_requests'],
                'uptime_horas': round(session_stats['uptime'] / 3600, 1),
                'aprovacao': feedback_stats.get('aprovacao', 0),
                'cache_hit_rate': round((cache_stats['cached_sessions'] / max(cache_stats['total_tracked'], 1)) * 100, 1)
            })
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
        
    @main_bp.route('/api/user-status')
    def user_status():
        """API para mostrar status do usuário atual"""
        try:
            user_id = session.get('user_id')
            session_id = session.get('titan_session_id')  # ADICIONAR
            
            if not user_id:
                # PARA USUÁRIOS ANÔNIMOS, RETORNAR DADOS DA SESSÃO
                if session_id:
                    try:
                        can_send, limit_info = anonymous_limiter.can_send_message(session_id)
                        return jsonify({
                            'logged_in': False,
                            'anonymous': True,
                            'session_id': session_id,
                            'anonymous_limits': {
                                'used': limit_info.get('messages_used', 0),
                                'limit': 5,
                                'remaining': limit_info.get('remaining', 5)
                            }
                        })
                    except Exception as e:
                        print(f"Erro ao verificar limites anônimos: {e}")
                
                # SE NÃO TEM SESSION_ID, PRECISA INICIALIZAR
                return jsonify({
                    'logged_in': False,
                    'anonymous': False,
                    'needs_session_init': True,
                    'message': 'Sessão precisa ser inicializada'
                })

            # Buscar informações do usuário autenticado
            user_info = auth_manager.get_user_by_id(user_id)
            user_limits = auth_manager.get_user_limits(user_id)
            current_usage = rate_limiter.get_current_usage(user_id)
            
            return jsonify({
                'logged_in': True,
                'user': {
                    'id': user_id,
                    'email': user_info['email'] if user_info else 'Anônimo',
                    'name': user_info['name'] if user_info else 'Usuário Anônimo',
                    'is_anonymous': session.get('is_anonymous', False)
                },
                'plan': {
                    'name': user_limits['plan_name'],
                    'messages_per_hour': user_limits['messages_per_hour'],
                    'messages_per_day': user_limits['messages_per_day'],
                    'features': user_limits.get('features', []),
                    'is_premium': user_limits.get('is_premium', False)
                },
                'usage': {
                    'hour': current_usage['current_usage']['hour'] if current_usage and current_usage['status'] == 'sucesso' else {'messages': 0},
                    'day': current_usage['current_usage']['day'] if current_usage and current_usage['status'] == 'sucesso' else {'messages': 0},
                    'remaining': current_usage['remaining'] if current_usage and current_usage['status'] == 'sucesso' else {'day': 50, 'hour': 10}
                }
            })
            
        except Exception as e:
            print(f" Erro no user-status: {e}")
            return jsonify({
                'logged_in': False,
                'error': str(e)
            }), 500
        

    @main_bp.route('/api/init-session', methods=['POST'])
    @csrf.exempt
    def init_session():
        """Inicializar sessão anônima SIMPLES"""
        print(" [DEBUG] === INIT SESSION CHAMADA ===")
        print(f" [DEBUG] Request Method: {request.method}")
        print(f" [DEBUG] Request Headers: {request.headers}")
        print(f" [DEBUG] Request Data: {request.data}")
        print(f" [DEBUG] Request Form: {request.form}")
        
        try:
            session_id = session.get('titan_session_id')
            print(f" [DEBUG] session_id atual: {session_id}")
            
            if not session_id:
                session_id = str(uuid.uuid4())
                session['titan_session_id'] = session_id
                session['is_anonymous'] = True
                session.permanent = True
                print(f" [DEBUG] Nova sessão criada: {session_id[:8]}...")
            
            print(" [DEBUG] Verificando limites anônimos...")
            # Verificar limites anônimos
            can_send, limit_info = anonymous_limiter.can_send_message(session_id)
            print(f" [DEBUG] can_send: {can_send}, limit_info: {limit_info}")
            
            response_data = {
                'status': 'sucesso',
                'session_id': session_id,
                'anonymous': True,
                'limits': limit_info if can_send else {
                    'used': limit_info.get('messages_used', 0),
                    'limit': 5,
                    'remaining': limit_info.get('remaining', 0)
                }
            }
            
            print(f" [DEBUG] Retornando: {response_data}")
            return jsonify(response_data)
            
        except Exception as e:
            print(f" [DEBUG] Erro detalhado: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'status': 'erro', 'message': str(e)}), 500
        
    @main_bp.route('/stripe/webhook', methods=['POST'])
    def stripe_webhook():
        """ Webhook para processar eventos do Stripe"""
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        
        try:
            # Verificar assinatura do webhook
            event = stripe.Webhook.construct_event(
                payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET')
            )
        except ValueError as e:
            print(f" Invalid payload: {e}")
            return 'Invalid payload', 400
        except stripe.error.SignatureVerificationError as e:
            print(f" Invalid signature: {e}")
            return 'Invalid signature', 400
        
        print(f" Webhook recebido: {event['type']}")
        
        # Processar eventos de assinatura
        if event['type'] == 'customer.subscription.created':
            handle_subscription_created(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            handle_subscription_deleted(event['data']['object'])
        elif event['type'] == 'checkout.session.completed':
            handle_checkout_completed(event['data']['object'])
        
        return 'Success', 200
    
    def handle_subscription_created(subscription):
        """Nova assinatura criada"""
        customer_id = subscription['customer']
        
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            # Buscar usuário pelo Stripe Customer ID
            cursor.execute("SELECT id FROM users WHERE stripe_customer_id = ?", (customer_id,))
            user = cursor.fetchone()
            
            if user:
                user_id = user[0]
                
                # Inserir assinatura
                cursor.execute("""
                    INSERT OR REPLACE INTO subscriptions 
                    (user_id, stripe_subscription_id, stripe_price_id, status,
                     current_period_start, current_period_end)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    subscription['id'],
                    subscription['items']['data'][0]['price']['id'],
                    subscription['status'],
                    subscription['current_period_start'],
                    subscription['current_period_end']
                ))
                
                conn.commit()
                print(f"Assinatura criada para usuário {user_id}")
            else:
                print(f" Usuário não encontrado para customer {customer_id}")
            
            conn.close()
            
        except Exception as e:
            print(f" Erro ao processar assinatura: {e}")

    def handle_subscription_updated(subscription):
        """🔄 Assinatura atualizada"""
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE subscriptions 
                SET status = ?, current_period_start = ?, current_period_end = ?
                WHERE stripe_subscription_id = ?
            """, (
                subscription['status'],
                subscription['current_period_start'],
                subscription['current_period_end'],
                subscription['id']
            ))
            
            conn.commit()
            conn.close()
            print(f"🔄 Assinatura {subscription['id']} atualizada")
            
        except Exception as e:
            print(f" Erro ao atualizar assinatura: {e}")

    def handle_subscription_deleted(subscription):
        """ Assinatura cancelada"""
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE subscriptions 
                SET status = 'canceled'
                WHERE stripe_subscription_id = ?
            """, (subscription['id'],))
            
            conn.commit()
            conn.close()
            print(f" Assinatura {subscription['id']} cancelada")
            
        except Exception as e:
            print(f" Erro ao cancelar assinatura: {e}")

    def handle_checkout_completed(session):
        """Checkout concluído"""
        print(f"Checkout concluído: {session['id']}")


    @main_bp.route('/send_message', methods=['POST'])
    def send_message():
        try:
            data = request.get_json()
            session_id = data.get('session_id')
            message = data.get('message', '')
            
            # Verificar se usuário está autenticado
            user_id = session.get('user_id')  # Do Flask session
            is_authenticated = bool(user_id)
            
            print(f" Enviando mensagem - Autenticado: {is_authenticated}")
            
            # VERIFICAÇÃO UNIFICADA DE RATE LIMIT
            can_send, limit_info = rate_limiter.check_rate_limit(session_id, user_id)
            
            if not can_send:
                # Se é usuário anônimo que atingiu limite
                if not is_authenticated and isinstance(limit_info, dict) and limit_info.get('action_required') == 'create_account':
                    return jsonify({
                        'error': limit_info['error'],
                        'limit_reached': True,
                        'action_required': 'create_account',
                        'messages_used': limit_info['messages_used'],
                        'limit': limit_info['limit']
                    }), 429
                else:
                    # Usuário autenticado que atingiu limite
                    return jsonify({
                        'error': limit_info if isinstance(limit_info, str) else 'Limite excedido',
                        'limit_reached': True
                    }), 429
            
            # PROCESSAR MENSAGEM (seu código normal aqui)
            # ... seu código de IA aqui ...
            
            # REGISTRAR USO APÓS SUCESSO
            usage_result = rate_limiter.track_usage(
                session_id, 
                user_id,
                len(message),
                data.get('thinking_mode', False)
            )

            response_data = {
                'resposta': 'Sua resposta da IA aqui...',
                'limit_info': {
                    'is_authenticated': is_authenticated,
                    'usage': usage_result,
                    'limit_status': limit_info
                }
            }
            
            return jsonify(response_data)
            
        except Exception as e:
            print(f" Erro no envio: {e}")
            return jsonify({'error': str(e)}), 500
        
    @main_bp.route('/auth/register', methods=['POST'])
    def register():
        """Criar nova conta"""
        try:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password') 
            name = data.get('name', '')
            
            if not email or not password:
                return jsonify({'status': 'erro', 'message': 'Email e senha são obrigatórios'}), 400
            
            result = auth_manager.create_user(email, password, name)
            
            if result['status'] == 'sucesso':
                session['user_id'] = result['user_id']
                session['user_email'] = email
                session['user_name'] = name
                session['authenticated'] = True
                session['is_anonymous'] = False
                
                print(f"👤 [AUTH] Conta criada: {email} (ID: {result['user_id']})")
                
            return jsonify(result)
            
        except Exception as e:
            print(f" Erro no registro: {e}")
            return jsonify({'status': 'erro', 'message': str(e)}), 500

    @main_bp.route('/auth/login', methods=['POST'])  
    def login():
        """Login de usuário"""
        try:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
            
            if not email or not password:
                return jsonify({'status': 'erro', 'message': 'Email e senha são obrigatórios'}), 400
            
            result = auth_manager.authenticate_user(email, password)
            
            if result['status'] == 'sucesso':
                session['user_id'] = result['user_id']
                session['user_email'] = email
                session['user_name'] = result.get('name', '')
                session['authenticated'] = True
                session['is_anonymous'] = False
                
                print(f"[AUTH] Login: {email} (ID: {result['user_id']})")
                
            return jsonify(result)
            
        except Exception as e:
            print(f" Erro no login: {e}")
            return jsonify({'status': 'erro', 'message': str(e)}), 500

    @main_bp.route('/auth/check', methods=['GET'])
    def check_auth():
        """Verificar se usuário está logado"""
        user_id = session.get('user_id')
        is_authenticated = bool(user_id)
        
        if is_authenticated:
            try:
                user_limits = auth_manager.get_user_limits(user_id)
                current_usage = rate_limiter.get_current_usage(user_id)
                
                return jsonify({
                    'authenticated': True,
                    'user_id': user_id,
                    'email': session.get('user_email'),
                    'name': session.get('user_name'),
                    'is_anonymous': False,
                    'plan': user_limits,
                    'usage': current_usage
                })
            except Exception as e:
                print(f" Erro ao buscar dados do usuário: {e}")
                return jsonify({
                    'authenticated': True,
                    'user_id': user_id,
                    'email': session.get('user_email'),
                    'error': 'Erro ao carregar dados do usuário'
                })
        else:
            session_id = session.get('titan_session_id')
            if session_id:
                can_send, limit_info = anonymous_limiter.can_send_message(session_id)
                
                return jsonify({
                    'authenticated': False,
                    'is_anonymous': True,
                    'anonymous_limits': limit_info if can_send else {
                        'used': limit_info.get('messages_used', 0),
                        'limit': 5,
                        'remaining': limit_info.get('remaining', 0)
                    }
                })
            else:
                return jsonify({
                    'authenticated': False,
                    'is_anonymous': True,
                    'anonymous_limits': {
                        'used': 0,
                        'limit': 5,
                        'remaining': 5
                    }
                })

    @main_bp.route('/auth/logout', methods=['POST'])
    def logout():
        """Logout do usuário"""
        session.clear()
        return jsonify({'status': 'sucesso', 'message': 'Logout realizado'})
    
    return main_bp