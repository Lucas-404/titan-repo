from flask import request, jsonify, session
from models.session_manager import session_manager

def setup_session_middleware(app):
    """Configura middleware de controle de sessão"""
    
    @app.before_request
    def verificar_sessao():
        """Middleware para controlar acesso"""
        
        # Rotas protegidas
        rotas_protegidas = [
            'main.chat',
            'main.chat_stream',
            'main.api_chats'
        ]
        
        if request.endpoint not in rotas_protegidas:
            return
        
        user_ip = request.remote_addr
        session_id = session.get('titan_session_id')
        
        print(f"🔍 Verificando: {user_ip} - Sessão: {session_id[:8] if session_id else 'None'}...")
        
        # Verificar sessão válida
        if session_id and session_manager.get_session_data(session_id):
            if session_manager.atualizar_atividade(session_id):
                print(f"✅ Sessão válida: {session_id[:8]}...")
                return None
            else:
                session.pop('titan_session_id', None)
        
        # Tentar criar nova sessão
        if session_manager.pode_entrar():
            novo_session_id = session_manager.criar_sessao(user_ip)
            if novo_session_id:
                session['titan_session_id'] = novo_session_id
                print(f"🆕 Nova sessão: {user_ip}")
                return
        
        # Sistema lotado
        session_manager.stats['requests_rejeitados'] += 1
        fila_info = session_manager.get_posicao_fila(user_ip)
        status_sistema = session_manager.get_status()
        
        print(f"🚫 Acesso negado: {user_ip} - Sistema lotado")
        
        return jsonify({
            'erro': 'Sistema ocupado',
            'status': 'fila',
            'sistema': {
                'usuarios_ativos': status_sistema['usuarios_ativos'],
                'maximo_usuarios': status_sistema['maximo_usuarios'],
                'fila_espera': status_sistema['fila_espera']
            },
            'fila': fila_info,
            'mensagem': f"Você é o {fila_info['posicao']}º na fila."
        }), 429