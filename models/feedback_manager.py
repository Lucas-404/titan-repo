import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from config import DATABASE_FILE

class FeedbackManager:
    def __init__(self):
        self.db_file = DATABASE_FILE
        self.init_feedback_database()
        print(" FeedbackManager inicializado")
    
    def init_feedback_database(self):
        """Criar tabela de feedbacks se não existir"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                usuario_ip TEXT,
                tipo_feedback TEXT NOT NULL,
                categoria TEXT NOT NULL,
                prioridade TEXT DEFAULT 'media',
                titulo TEXT NOT NULL,
                descricao TEXT NOT NULL,
                passos_reproducao TEXT,
                comportamento_esperado TEXT,
                resultado_atual TEXT,
                informacoes_sistema TEXT,
                anexos TEXT,
                status TEXT DEFAULT 'aberto',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notas_admin TEXT
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedbacks(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_tipo ON feedbacks(tipo_feedback)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedbacks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_data ON feedbacks(data_criacao)")
        
        conn.commit()
        conn.close()
        print(" Tabela de feedbacks inicializada")
    
    def criar_feedback(self, feedback_data, session_id, user_ip):
        """Criar novo feedback"""
        try:
            feedback_id = str(uuid.uuid4())
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO feedbacks (
                    id, session_id, usuario_ip, tipo_feedback, categoria, 
                    prioridade, titulo, descricao, passos_reproducao,
                    comportamento_esperado, resultado_atual, informacoes_sistema, anexos
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                feedback_id,
                session_id,
                user_ip,
                feedback_data.get('tipo', 'bug'),
                feedback_data.get('categoria', 'geral'),
                feedback_data.get('prioridade', 'media'),
                feedback_data.get('titulo', ''),
                feedback_data.get('descricao', ''),
                feedback_data.get('passos_reproducao', ''),
                feedback_data.get('comportamento_esperado', ''),
                feedback_data.get('resultado_atual', ''),
                feedback_data.get('informacoes_sistema', ''),
                json.dumps(feedback_data.get('anexos', []))
            ))
            
            conn.commit()
            conn.close()
            
            print(f" Feedback criado: {feedback_id} - {feedback_data.get('titulo')}")
            
            return {
                'status': 'sucesso',
                'feedback_id': feedback_id,
                'message': 'Feedback enviado com sucesso!'
            }
            
        except Exception as e:
            print(f" Erro ao criar feedback: {e}")
            return {
                'status': 'erro',
                'message': f'Erro ao salvar feedback: {str(e)}'
            }
    
    def listar_feedbacks(self, session_id=None, tipo=None, status=None, limit=50):
        """Listar feedbacks com filtros"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            query = """
                SELECT id, session_id, tipo_feedback, categoria, prioridade,
                       titulo, descricao, status, data_criacao, data_atualizacao
                FROM feedbacks WHERE 1=1
            """
            params = []
            
            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)
            
            if tipo:
                query += " AND tipo_feedback = ?"
                params.append(tipo)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY data_criacao DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            feedbacks = []
            for row in results:
                feedbacks.append({
                    'id': row[0],
                    'session_id': row[1][:8] + "..." if row[1] else None,
                    'tipo': row[2],
                    'categoria': row[3],
                    'prioridade': row[4],
                    'titulo': row[5],
                    'descricao': row[6][:100] + "..." if len(row[6]) > 100 else row[6],
                    'status': row[7],
                    'data_criacao': row[8],
                    'data_atualizacao': row[9]
                })
            
            conn.close()
            
            return {
                'status': 'sucesso',
                'feedbacks': feedbacks,
                'total': len(feedbacks)
            }
            
        except Exception as e:
            print(f" Erro ao listar feedbacks: {e}")
            return {
                'status': 'erro',
                'message': str(e)
            }
    
    def obter_feedback(self, feedback_id):
        """Obter feedback específico"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM feedbacks WHERE id = ?
            """, (feedback_id,))
            
            row = cursor.fetchone()
            if not row:
                return {
                    'status': 'erro',
                    'message': 'Feedback não encontrado'
                }
            
            columns = [desc[0] for desc in cursor.description]
            feedback = dict(zip(columns, row))
            
            try:
                feedback['anexos'] = json.loads(feedback['anexos']) if feedback['anexos'] else []
            except:
                feedback['anexos'] = []
            
            conn.close()
            
            return {
                'status': 'sucesso',
                'feedback': feedback
            }
            
        except Exception as e:
            print(f" Erro ao obter feedback: {e}")
            return {
                'status': 'erro',
                'message': str(e)
            }
    
    def atualizar_status(self, feedback_id, novo_status, notas_admin=""):
        """Atualizar status do feedback (para admins)"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE feedbacks 
                SET status = ?, notas_admin = ?, data_atualizacao = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (novo_status, notas_admin, feedback_id))
            
            if cursor.rowcount == 0:
                conn.close()
                return {
                    'status': 'erro',
                    'message': 'Feedback não encontrado'
                }
            
            conn.commit()
            conn.close()
            
            print(f" Feedback {feedback_id} atualizado para: {novo_status}")
            
            return {
                'status': 'sucesso',
                'message': f'Status atualizado para: {novo_status}'
            }
            
        except Exception as e:
            print(f" Erro ao atualizar feedback: {e}")
            return {
                'status': 'erro',
                'message': str(e)
            }
    
    def obter_estatisticas(self):
        """Estatísticas dos feedbacks"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT tipo_feedback, COUNT(*) as total
                FROM feedbacks
                GROUP BY tipo_feedback
            """)
            por_tipo = dict(cursor.fetchall())
            
            cursor.execute("""
                SELECT status, COUNT(*) as total
                FROM feedbacks
                GROUP BY status
            """)
            por_status = dict(cursor.fetchall())
            
            cursor.execute("""
                SELECT prioridade, COUNT(*) as total
                FROM feedbacks
                GROUP BY prioridade
            """)
            por_prioridade = dict(cursor.fetchall())
            
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM feedbacks
                WHERE datetime(data_criacao) >= datetime('now', '-7 days')
            """)
            recentes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM feedbacks")
            total = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'status': 'sucesso',
                'estatisticas': {
                    'total_feedbacks': total,
                    'feedbacks_recentes': recentes,
                    'por_tipo': por_tipo,
                    'por_status': por_status,
                    'por_prioridade': por_prioridade
                }
            }
            
        except Exception as e:
            print(f" Erro ao obter estatísticas: {e}")
            return {
                'status': 'erro',
                'message': str(e)
            }

feedback_manager = FeedbackManager()