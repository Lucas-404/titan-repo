import sqlite3
from datetime import datetime, date
from config import DATABASE_FILE

class AnonymousLimiter:
    def __init__(self):
        self.db_file = DATABASE_FILE
        self.init_anonymous_table()
        print("AnonymousLimiter inicializado")
    
    def init_anonymous_table(self):
        """Criar tabela para usuários anônimos"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anonymous_usage (
                session_id TEXT PRIMARY KEY,
                messages_used INTEGER DEFAULT 0,
                first_message_date DATE DEFAULT CURRENT_DATE,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        print(" Tabela anonymous_usage criada")
    
    def can_send_message(self, session_id):
        """Verificar se usuário anônimo pode enviar mensagem"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT messages_used FROM anonymous_usage 
                WHERE session_id = ? AND first_message_date = CURRENT_DATE
            """, (session_id,))
            
            result = cursor.fetchone()
            messages_used = result[0] if result else 0
            
            conn.close()
            
            if messages_used >= 5:
                return False, {
                    'error': 'Limite de 5 mensagens gratuitas atingido! Crie uma conta para continuar.',
                    'action_required': 'create_account',
                    'messages_used': messages_used,
                    'limit': 5,
                    'remaining': 0
                }
            
            return True, {
                'remaining': 5 - messages_used,
                'used': messages_used,
                'limit': 5
            }
            
        except Exception as e:
            print(f" Erro no anonymous limiter: {e}")
            return True, None
    
    def track_message_usage(self, session_id):
        """Registrar uso de mensagem para usuário anônimo"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
        
            cursor.execute("""
                INSERT INTO anonymous_usage (session_id, messages_used)
                VALUES (?, 1)
                ON CONFLICT(session_id) DO UPDATE SET
                    messages_used = messages_used + 1,
                    last_activity = CURRENT_TIMESTAMP
            """, (session_id,))
            
            cursor.execute("""
                SELECT messages_used FROM anonymous_usage WHERE session_id = ?
            """, (session_id,))
            
            result = cursor.fetchone()
            current_usage = result[0] if result else 1
            
            conn.commit()
            conn.close()
            
            print(f"[ANONYMOUS] Session {session_id[:8]}...: {current_usage}/5 mensagens")
            
            return {
                'messages_used': current_usage,
                'remaining': max(0, 5 - current_usage),
                'limit_reached': current_usage >= 5
            }
            
        except Exception as e:
            print(f" Erro ao registrar uso anônimo: {e}")
            return {'messages_used': 0, 'remaining': 5, 'limit_reached': False}

    def reset_daily_usage(self):
        """Limpar dados antigos (executar diariamente)"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM anonymous_usage 
                WHERE first_message_date < CURRENT_DATE
            """)
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted > 0:
                print(f" [CLEANUP] {deleted} registros anônimos antigos removidos")
            
            return deleted
            
        except Exception as e:
            print(f" Erro na limpeza de dados anônimos: {e}")
            return 0

# Instância global
anonymous_limiter = AnonymousLimiter()