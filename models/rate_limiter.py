import sqlite3
from datetime import datetime, date, timedelta
from config import DATABASE_FILE

class RateLimiter:
    def __init__(self):
        self.db_file = DATABASE_FILE
        print(" RateLimiter inicializado")
    
    def can_send_message(self, user_id):
        """Verificar se usuário pode enviar mensagem"""
        try:
            from models.auth_manager import auth_manager
            limits = auth_manager.get_user_limits(user_id)
            
            if not limits:
                return False, "Usuário não encontrado"
            
            now = datetime.now()
            today = now.date()
            current_hour = now.hour
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT messages_used, characters_used, thinking_messages 
                FROM usage_tracking 
                WHERE user_id = ? AND date = ? AND hour = ?
            """, (user_id, today, current_hour))
            
            hour_result = cursor.fetchone()
            hour_usage = hour_result[0] if hour_result else 0
            
            cursor.execute("""
                SELECT SUM(messages_used), SUM(characters_used), SUM(thinking_messages)
                FROM usage_tracking 
                WHERE user_id = ? AND date = ?
            """, (user_id, today))
            
            day_result = cursor.fetchone()
            day_usage = day_result[0] if day_result and day_result[0] else 0
            
            conn.close()
            
            max_hour = limits['messages_per_hour']
            max_day = limits['messages_per_day']
            
            print(f" [RATE LIMIT] User {user_id} - Hora: {hour_usage}/{max_hour}, Dia: {day_usage}/{max_day}")
            
            if hour_usage >= max_hour:
                remaining_minutes = 60 - now.minute
                return False, f"Limite de {max_hour} mensagens por hora excedido. Tente em {remaining_minutes} minutos."
            
            if day_usage >= max_day:
                return False, f"Limite diário de {max_day} mensagens excedido. Renova às 00:00h."
            
            return True, None
            
        except Exception as e:
            print(f" Erro no rate limiter: {e}")
            return True, None
    
    def track_message_usage(self, user_id, character_count=0, is_thinking=False):
        """Registrar uso de mensagem"""
        try:
            now = datetime.now()
            today = now.date()
            current_hour = now.hour
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Inserir ou atualizar uso
            cursor.execute("""
                INSERT INTO usage_tracking 
                (user_id, date, hour, messages_used, characters_used, thinking_messages)
                VALUES (?, ?, ?, 1, ?, ?)
                ON CONFLICT(user_id, date, hour) DO UPDATE SET
                    messages_used = messages_used + 1,
                    characters_used = characters_used + ?,
                    thinking_messages = thinking_messages + ?
            """, (
                user_id, today, current_hour, 
                character_count, 1 if is_thinking else 0,
                character_count, 1 if is_thinking else 0
            ))
            
            conn.commit()
            conn.close()
            
            mode = "thinking" if is_thinking else "normal"
            print(f" [USAGE] User {user_id}: +1 msg {mode} ({character_count} chars)")
            
            return True
            
        except Exception as e:
            print(f" Erro ao registrar uso: {e}")
            return False
    
    def get_usage_stats(self, user_id, days=7):
        """Obter estatísticas de uso dos últimos N dias"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days-1)
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT date, SUM(messages_used) as daily_messages, 
                       SUM(characters_used) as daily_chars,
                       SUM(thinking_messages) as daily_thinking
                FROM usage_tracking 
                WHERE user_id = ? AND date BETWEEN ? AND ?
                GROUP BY date
                ORDER BY date DESC
            """, (user_id, start_date, end_date))
            
            daily_stats = []
            for row in cursor.fetchall():
                daily_stats.append({
                    'date': row[0],
                    'messages': row[1],
                    'characters': row[2],
                    'thinking_messages': row[3]
                })
            
            cursor.execute("""
                SELECT hour, messages_used, characters_used, thinking_messages
                FROM usage_tracking 
                WHERE user_id = ? AND date = ?
                ORDER BY hour
            """, (user_id, end_date))
            
            hourly_today = []
            for row in cursor.fetchall():
                hourly_today.append({
                    'hour': row[0],
                    'messages': row[1],
                    'characters': row[2],
                    'thinking_messages': row[3]
                })
            
            cursor.execute("""
                SELECT SUM(messages_used) as total_messages,
                       SUM(characters_used) as total_chars,
                       SUM(thinking_messages) as total_thinking
                FROM usage_tracking 
                WHERE user_id = ? AND date BETWEEN ? AND ?
            """, (user_id, start_date, end_date))
            
            totals = cursor.fetchone()
            
            conn.close()
            
            return {
                'status': 'sucesso',
                'user_id': user_id,
                'period_days': days,
                'daily_stats': daily_stats,
                'hourly_today': hourly_today,
                'totals': {
                    'messages': totals[0] or 0,
                    'characters': totals[1] or 0,
                    'thinking_messages': totals[2] or 0
                }
            }
            
        except Exception as e:
            print(f" Erro ao buscar estatísticas: {e}")
            return {'status': 'erro', 'message': str(e)}
    
    def get_current_usage(self, user_id):
        """Obter uso atual (hoje e hora atual)"""
        try:
            now = datetime.now()
            today = now.date()
            current_hour = now.hour
            
            from models.auth_manager import auth_manager
            limits = auth_manager.get_user_limits(user_id)
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT messages_used, characters_used, thinking_messages 
                FROM usage_tracking 
                WHERE user_id = ? AND date = ? AND hour = ?
            """, (user_id, today, current_hour))
            
            hour_result = cursor.fetchone()
            hour_usage = {
                'messages': hour_result[0] if hour_result else 0,
                'characters': hour_result[1] if hour_result else 0,
                'thinking': hour_result[2] if hour_result else 0
            }
            
            cursor.execute("""
                SELECT SUM(messages_used), SUM(characters_used), SUM(thinking_messages)
                FROM usage_tracking 
                WHERE user_id = ? AND date = ?
            """, (user_id, today))
            
            day_result = cursor.fetchone()
            day_usage = {
                'messages': day_result[0] if day_result and day_result[0] else 0,
                'characters': day_result[1] if day_result and day_result[1] else 0,
                'thinking': day_result[2] if day_result and day_result[2] else 0
            }
            
            conn.close()
            
            hour_percent = (hour_usage['messages'] / limits['messages_per_hour']) * 100 if limits['messages_per_hour'] > 0 else 0
            day_percent = (day_usage['messages'] / limits['messages_per_day']) * 100 if limits['messages_per_day'] > 0 else 0
            
            return {
                'status': 'sucesso',
                'user_id': user_id,
                'plan': limits['plan_name'],
                'limits': {
                    'messages_per_hour': limits['messages_per_hour'],
                    'messages_per_day': limits['messages_per_day']
                },
                'current_usage': {
                    'hour': hour_usage,
                    'day': day_usage
                },
                'remaining': {
                    'hour': max(0, limits['messages_per_hour'] - hour_usage['messages']),
                    'day': max(0, limits['messages_per_day'] - day_usage['messages'])
                },
                'percentages': {
                    'hour': min(100, hour_percent),
                    'day': min(100, day_percent)
                }
            }
            
        except Exception as e:
            print(f" Erro ao buscar uso atual: {e}")
            return {'status': 'erro', 'message': str(e)}
    
    def reset_usage_for_testing(self, user_id):
        """APENAS PARA TESTES - Resetar uso do usuário"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM usage_tracking WHERE user_id = ?
            """, (user_id,))
            
            conn.commit()
            conn.close()
            
            print(f" [TEST] Usage resetado para user {user_id}")
            return True
            
        except Exception as e:
            print(f" Erro ao resetar usage: {e}")
            return False
    
    def cleanup_old_usage(self, days_to_keep=90):
        """Limpar dados antigos de usage (executar periodicamente)"""
        try:
            cutoff_date = date.today() - timedelta(days=days_to_keep)
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM usage_tracking WHERE date < ?
            """, (cutoff_date,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                print(f" [CLEANUP] {deleted_count} registros antigos de usage removidos")
            
            return deleted_count
            
        except Exception as e:
            print(f" Erro na limpeza de usage: {e}")
            return 0

    def can_send_message_anonymous(self, session_id):
        try:
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
        
            cursor.execute("""
                SELECT messages_used FROM anonymous_usage 
                WHERE session_id = ? AND first_message_date = CURRENT_DATE
            """, (session_id,))
        
            result = cursor.fetchone()
            messages_used = result[0] if result else 0
        
            conn.close()
        
            if messages_used >= 5:
                return False, {
                    'error': 'Limite de 5 mensagens gratuitas atingido!',
                    'action_required': 'create_account',
                    'messages_used': messages_used,
                    'limit': 5
                }
        
            return True, {
                'remaining': 5 - messages_used,
                'used': messages_used,
                'limit': 5
            }
        
        except Exception as e:
            print(f" Erro no rate limiter anônimo: {e}")
            return True, None

    def track_anonymous_usage(self, session_id):
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
        
            print(f" [ANONYMOUS] Session {session_id[:8]}...: {current_usage}/5 mensagens")
        
            return {
                'messages_used': current_usage,
                'remaining': max(0, 5 - current_usage),
                'limit_reached': current_usage >= 5
            }
        
        except Exception as e:
            print(f" Erro ao registrar uso anônimo: {e}")
            return {'messages_used': 0, 'remaining': 5, 'limit_reached': False}

    def cleanup_anonymous_usage(self, days_old=7):
        """Limpar dados antigos de usuários anônimos"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
        
            cursor.execute("""
                DELETE FROM anonymous_usage 
                WHERE first_message_date < date('now', '-{} days')
            """.format(days_old))
        
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
        
            if deleted > 0:
                print(f" [CLEANUP] {deleted} sessões anônimas antigas removidas")
        
            return deleted
        
        except Exception as e:
            print(f" Erro na limpeza de dados anônimos: {e}")
            return 0

    def check_rate_limit(self, session_id, user_id=None):
        try:
            if user_id:
                print(f" Verificando limite para usuário autenticado: {user_id}")
                return self.can_send_message(user_id)
            else:
                print(f" Verificando limite para usuário anônimo: {session_id[:8]}...")
                return self.can_send_message_anonymous(session_id)
            
        except Exception as e:
            print(f" Erro na verificação de rate limit: {e}")
            return True, None 

    def track_usage(self, session_id, user_id=None, character_count=0, is_thinking=False):
        """Tracking unificado de uso"""
        try:
            if user_id:
                return self.track_message_usage(user_id, character_count, is_thinking)
            else:
                return self.track_anonymous_usage(session_id)
            
        except Exception as e:
            print(f" Erro no tracking de uso: {e}")
            return False

rate_limiter = RateLimiter()