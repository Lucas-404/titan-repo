import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

try:
    from config import FEEDBACK_DATABASE_FILE
except ImportError:
    FEEDBACK_DATABASE_FILE = Path(__file__).parent.parent / 'titan_feedbacks.db'

class FeedbackDatabase:
    def __init__(self):
        self.db_file = FEEDBACK_DATABASE_FILE
        self.init_database()
        print(f"👍👎 FeedbackDatabase inicializado: {self.db_file}")
    
    def init_database(self):
        """Criar tabela específica para feedbacks de ações"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS action_feedbacks (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_ip TEXT,
                action_type TEXT NOT NULL,  -- 'like' ou 'dislike'
                message_content TEXT,       -- Preview da mensagem avaliada
                thinking_mode BOOLEAN DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_agent TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_action_type ON action_feedbacks(action_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session ON action_feedbacks(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON action_feedbacks(timestamp)")
        
        conn.commit()
        conn.close()
        print(" Tabela action_feedbacks criada/verificada")
    
    def salvar_feedback(self, session_id, user_ip, action_type, message_content="", thinking_mode=False, user_agent=""):
        """Salvar feedback de like/dislike com conteúdo completo para dislikes"""
        try:
            # Validar action_type
            if action_type not in ['like', 'dislike']:
                return {'status': 'erro', 'message': 'Tipo inválido'}
            
            feedback_id = str(uuid.uuid4())
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            if action_type == 'dislike':
                content_to_save = message_content[:2000] if message_content else ''
                print(f"Salvando mensagem completa do dislike ({len(content_to_save)} chars)")
            else:
                content_to_save = message_content[:200] if message_content else ''
            
            cursor.execute("""
                INSERT INTO action_feedbacks 
                (id, session_id, user_ip, action_type, message_content, thinking_mode, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                feedback_id,
                session_id or 'anonimo',
                user_ip,
                action_type,
                content_to_save,
                thinking_mode,
                user_agent[:100] if user_agent else ''
            ))
            
            conn.commit()
            conn.close()
            
            emoji = '👍' if action_type == 'like' else '👎'
            session_info = session_id[:8] + '...' if session_id else 'anônima'
            print(f"{emoji} {action_type.upper()} salvo da sessão {session_info}")
            
            return {
                'status': 'sucesso',
                'feedback_id': feedback_id,
                'message': f'{action_type.capitalize()} registrado!'
            }
            
        except Exception as e:
            print(f" Erro ao salvar feedback: {e}")
            return {'status': 'erro', 'message': str(e)}
    
    def obter_estatisticas(self, session_id=None):
        """Obter estatísticas de feedbacks"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            where_clause = ""
            params = []
            
            if session_id:
                where_clause = "WHERE session_id = ?"
                params = [session_id]
            
            cursor.execute(f"""
                SELECT action_type, COUNT(*) 
                FROM action_feedbacks 
                {where_clause}
                GROUP BY action_type
            """, params)
            
            counts = dict(cursor.fetchall())
            likes = counts.get('like', 0)
            dislikes = counts.get('dislike', 0)
            total = likes + dislikes
            
            aprovacao = (likes / total * 100) if total > 0 else 0
            
            conn.close()
            
            return {
                'status': 'sucesso',
                'likes': likes,
                'dislikes': dislikes,
                'total_avaliacoes': total,
                'aprovacao': round(aprovacao, 1)
            }
            
        except Exception as e:
            print(f" Erro ao obter estatísticas: {e}")
            return {'status': 'erro', 'message': str(e)}
    
    def listar_feedbacks(self, limit=50, session_id=None):
        """Listar feedbacks recentes"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            where_clause = ""
            params = []
            
            if session_id:
                where_clause = "WHERE session_id = ?"
                params = [session_id]
            
            cursor.execute(f"""
                SELECT id, session_id, action_type, thinking_mode, timestamp
                FROM action_feedbacks 
                {where_clause}
                ORDER BY timestamp DESC 
                LIMIT ?
            """, params + [limit])
            
            feedbacks = []
            for row in cursor.fetchall():
                feedbacks.append({
                    'id': row[0],
                    'session_id': row[1][:8] + '...' if row[1] else 'anônima',
                    'action_type': row[2],
                    'thinking_mode': bool(row[3]),
                    'timestamp': row[4]
                })
            
            conn.close()
            
            return {
                'status': 'sucesso',
                'feedbacks': feedbacks,
                'total': len(feedbacks)
            }
            
        except Exception as e:
            print(f" Erro ao listar feedbacks: {e}")
            return {'status': 'erro', 'message': str(e)}

    def obter_mensagens_com_dislike(self, limit=20):
        """Obter mensagens que receberam dislike"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, session_id, message_content, thinking_mode, timestamp, user_agent
                FROM action_feedbacks 
                WHERE action_type = 'dislike' 
                AND message_content != ''
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            mensagens_problematicas = []
            for row in cursor.fetchall():
                mensagens_problematicas.append({
                    'id': row[0],
                    'session_id': row[1][:8] + '...' if row[1] else 'anônima',
                    'conteudo_completo': row[2],
                    'preview': row[2][:100] + '...' if len(row[2]) > 100 else row[2],
                    'thinking_mode': bool(row[3]),
                    'timestamp': row[4],
                    'user_agent': row[5][:50] + '...' if len(row[5]) > 50 else row[5],
                    'tamanho_mensagem': len(row[2]),
                    'palavras': len(row[2].split()) if row[2] else 0
                })
            
            conn.close()
            
            return {
                'status': 'sucesso',
                'mensagens_com_dislike': mensagens_problematicas,
                'total_encontradas': len(mensagens_problematicas)
            }
            
        except Exception as e:
            print(f" Erro ao buscar mensagens com dislike: {e}")
            return {'status': 'erro', 'message': str(e)}

    def analisar_padroes_dislike(self):
        """Analisar padrões nas mensagens com dislike"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT message_content, thinking_mode, timestamp
                FROM action_feedbacks 
                WHERE action_type = 'dislike' 
                AND message_content != ''
            """)
            
            mensagens = cursor.fetchall()
            
            if not mensagens:
                return {
                    'status': 'sucesso',
                    'analise': 'Nenhuma mensagem com dislike encontrada'
                }
            
            total_mensagens = len(mensagens)
            com_thinking = sum(1 for m in mensagens if m[1])
            sem_thinking = total_mensagens - com_thinking
            
            tamanhos = [len(m[0]) for m in mensagens if m[0]]
            tamanho_medio = sum(tamanhos) / len(tamanhos) if tamanhos else 0
            
            todas_palavras = []
            for mensagem in mensagens:
                if mensagem[0]:
                    palavras = mensagem[0].lower().split()
                    todas_palavras.extend(palavras)
            
            from collections import Counter
            palavras_comuns = Counter(todas_palavras).most_common(10)
            
            conn.close()
            
            return {
                'status': 'sucesso',
                'analise': {
                    'total_mensagens_dislike': total_mensagens,
                    'com_thinking_mode': com_thinking,
                    'sem_thinking_mode': sem_thinking,
                    'tamanho_medio_caracteres': round(tamanho_medio, 1),
                    'palavras_mais_frequentes': palavras_comuns,
                    'percentual_thinking': round((com_thinking / total_mensagens * 100), 1) if total_mensagens > 0 else 0
                }
            }
            
        except Exception as e:
            print(f" Erro na análise de padrões: {e}")
            return {'status': 'erro', 'message': str(e)}

    def obter_mensagem_dislike_por_id(self, feedback_id):
        """Obter mensagem específica com dislike por ID"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, session_id, message_content, thinking_mode, timestamp, user_agent, user_ip
                FROM action_feedbacks 
                WHERE id = ? AND action_type = 'dislike'
            """, (feedback_id,))
            
            row = cursor.fetchone()
            
            if not row:
                return {'status': 'erro', 'message': 'Mensagem não encontrada'}
            
            conn.close()
            
            return {
                'status': 'sucesso',
                'mensagem': {
                    'id': row[0],
                    'session_id': row[1][:8] + '...',
                    'conteudo_completo': row[2],
                    'thinking_mode': bool(row[3]),
                    'timestamp': row[4],
                    'user_agent': row[5],
                    'user_ip': row[6][:10] + '...' if row[6] else None,
                    'estatisticas': {
                        'caracteres': len(row[2]) if row[2] else 0,
                        'palavras': len(row[2].split()) if row[2] else 0,
                        'linhas': row[2].count('\n') + 1 if row[2] else 0
                    }
                }
            }
            
        except Exception as e:
            print(f" Erro ao buscar mensagem específica: {e}")
            return {'status': 'erro', 'message': str(e)}

    def obter_mensagens_com_dislike_detalhado(self, limit=20):
        """Ver mensagens que receberam dislike com detalhes completos"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, session_id, message_content, thinking_mode, timestamp, user_agent
                FROM action_feedbacks 
                WHERE action_type = 'dislike' 
                AND message_content != ''
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            mensagens_problematicas = []
            for row in cursor.fetchall():
                mensagem = {
                    'id': row[0],
                    'session_id': row[1][:8] + '...',
                    'mensagem_completa': row[2],
                    'thinking_mode': 'Pensamento Prolongado' if row[3] else 'Resposta Direta',
                    'quando': row[4],
                    'navegador': row[5][:100] if row[5] else 'Desconhecido',
                    'resumo': {
                        'caracteres': len(row[2]),
                        'palavras': len(row[2].split()),
                        'tem_codigo': '```' in row[2] or 'def ' in row[2] or 'import ' in row[2],
                        'tem_lista': any(x in row[2] for x in ['1.', '2.', '•', '-']),
                        'e_longa': len(row[2]) > 500,
                        'tem_desculpa': any(palavra in row[2].lower() for palavra in ['desculpe', 'não posso', 'não consigo', 'lamento'])
                    }
                }
                mensagens_problematicas.append(mensagem)
            
            conn.close()
            
            total = len(mensagens_problematicas)
            com_thinking = sum(1 for m in mensagens_problematicas if 'Pensamento' in m['thinking_mode'])
            com_desculpa = sum(1 for m in mensagens_problematicas if m['resumo']['tem_desculpa'])
            
            return {
                'status': 'sucesso',
                'mensagens_com_dislike': mensagens_problematicas,
                'resumo_geral': {
                    'total_dislikes': total,
                    'modo_thinking': com_thinking,
                    'modo_direto': total - com_thinking,
                    'mais_problematico': 'Pensamento Prolongado' if com_thinking > (total - com_thinking) else 'Resposta Direta',
                    'mensagens_com_desculpa': com_desculpa,
                    'percentual_desculpas': round((com_desculpa / total * 100), 1) if total > 0 else 0
                }
            }
            
        except Exception as e:
            print(f" Erro ao buscar dislikes: {e}")
            return {'status': 'erro', 'message': str(e)}

    def analisar_padroes_dislike_simples(self):
        """Análise simples dos padrões de dislike"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT message_content, thinking_mode
                FROM action_feedbacks 
                WHERE action_type = 'dislike' 
                AND message_content != ''
            """)
            
            mensagens = cursor.fetchall()
            
            if not mensagens:
                return {
                    'status': 'sucesso',
                    'analise': 'Nenhuma mensagem com dislike encontrada'
                }
            
            total = len(mensagens)
            thinking_count = sum(1 for m in mensagens if m[1])
            
            palavras_problema = ['desculpe', 'não posso', 'não consigo', 'lamento', 'impossível', 'limitação']
            frases_problema = []
            
            for mensagem_content, _ in mensagens:
                texto_lower = mensagem_content.lower()
                for palavra in palavras_problema:
                    if palavra in texto_lower:
                        frases_problema.append(palavra)
            
            from collections import Counter
            palavras_frequentes = Counter(frases_problema).most_common(5)
            
            conn.close()
            
            return {
                'status': 'sucesso',
                'analise': {
                    'total_mensagens_dislike': total,
                    'thinking_mode': thinking_count,
                    'direto_mode': total - thinking_count,
                    'palavras_problematicas_frequentes': palavras_frequentes,
                    'recomendacao': 'Evitar frases como "desculpe, não posso" e ser mais proativo' if palavras_frequentes else 'Padrões não identificados'
                }
            }
            
        except Exception as e:
            print(f" Erro na análise: {e}")
            return {'status': 'erro', 'message': str(e)}

feedback_db = FeedbackDatabase()