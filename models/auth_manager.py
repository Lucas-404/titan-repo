import sqlite3
import hashlib
import uuid
import stripe
import json
from datetime import datetime
from config import DATABASE_FILE

# Configurar Stripe (você vai adicionar as chaves no config.py depois)
try:
    from config import STRIPE_SECRET_KEY
    stripe.api_key = STRIPE_SECRET_KEY
except ImportError:
    print(" STRIPE_SECRET_KEY não encontrada no config.py")
    stripe.api_key = "sk_test_placeholder"  # Placeholder por enquanto

class AuthManager:
    def __init__(self):
        self.db_file = DATABASE_FILE
        self.init_auth_tables()
        print(" AuthManager inicializado")
    
    def init_auth_tables(self):
        """Criar todas as tabelas necessárias para autenticação e assinaturas"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            # 1. TABELA DE USUÁRIOS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    name TEXT,
                    stripe_customer_id TEXT UNIQUE,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 2. TABELA DE ASSINATURAS (sincronizada com Stripe)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    stripe_subscription_id TEXT UNIQUE NOT NULL,
                    stripe_price_id TEXT NOT NULL,
                    status TEXT NOT NULL,  -- active, canceled, past_due, trialing
                    current_period_start INTEGER NOT NULL,
                    current_period_end INTEGER NOT NULL,
                    cancel_at_period_end BOOLEAN DEFAULT 0,
                    trial_end INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # 3. TABELA DE PLANOS DISPONÍVEIS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    stripe_price_id TEXT UNIQUE NOT NULL,
                    messages_per_hour INTEGER NOT NULL,
                    messages_per_day INTEGER NOT NULL,
                    features TEXT,  -- JSON com features disponíveis
                    price_cents INTEGER NOT NULL,
                    interval_type TEXT NOT NULL,  -- month, year
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 4. TABELA DE TRACKING DE USO
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    hour INTEGER NOT NULL,  -- 0-23
                    messages_used INTEGER DEFAULT 0,
                    characters_used INTEGER DEFAULT 0,
                    thinking_messages INTEGER DEFAULT 0,
                    web_searches INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, date, hour)
                )
            """)
            
            # 5. ÍNDICES PARA PERFORMANCE
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_stripe_customer ON users(stripe_customer_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe ON subscriptions(stripe_subscription_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_user_date ON usage_tracking(user_id, date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_plans_stripe_price ON plans(stripe_price_id)")
            
            # 6. INSERIR PLANOS PADRÃO (se não existirem)
            self._insert_default_plans(cursor)
            
            conn.commit()
            print(" Tabelas de autenticação criadas/verificadas")
            
        except Exception as e:
            print(f" Erro ao criar tabelas: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _insert_default_plans(self, cursor):
        """Inserir planos padrão se não existirem"""
        
        # Verificar se já existem planos
        cursor.execute("SELECT COUNT(*) FROM plans")
        if cursor.fetchone()[0] > 0:
            return  # Já existem planos
        
        default_plans = [
            {
                'name': 'Gratuito',
                'description': 'Plano básico para experimentar o Titan',
                'stripe_price_id': 'price_free',  # Não será usado no Stripe
                'messages_per_hour': 10,
                'messages_per_day': 50,
                'features': json.dumps(['basic_chat']),
                'price_cents': 0,
                'interval_type': 'month'
            },
            {
                'name': 'Básico',
                'description': 'Ideal para uso pessoal',
                'stripe_price_id': 'price_basic_monthly',  # Você vai criar no Stripe
                'messages_per_hour': 100,
                'messages_per_day': 500,
                'features': json.dumps(['basic_chat', 'thinking_mode', 'memory']),
                'price_cents': 1999,  # R$ 19,99
                'interval_type': 'month'
            },
            {
                'name': 'Pro',
                'description': 'Para usuários avançados',
                'stripe_price_id': 'price_pro_monthly',  # Você vai criar no Stripe
                'messages_per_hour': 1000,
                'messages_per_day': 5000,
                'features': json.dumps(['basic_chat', 'thinking_mode', 'memory', 'web_search', 'priority_support']),
                'price_cents': 4999,  # R$ 49,99
                'interval_type': 'month'
            }
        ]
        
        for plan in default_plans:
            cursor.execute("""
                INSERT INTO plans (name, description, stripe_price_id, messages_per_hour, 
                                 messages_per_day, features, price_cents, interval_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                plan['name'], plan['description'], plan['stripe_price_id'],
                plan['messages_per_hour'], plan['messages_per_day'], 
                plan['features'], plan['price_cents'], plan['interval_type']
            ))
        
        print(" Planos padrão inseridos")
    
    def _hash_password(self, password):
        """Hash seguro da senha"""
        salt = uuid.uuid4().hex
        return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt
    
    def _verify_password(self, hashed_password, user_password):
        """Verificar senha"""
        password, salt = hashed_password.split(':')
        return password == hashlib.sha256(salt.encode() + user_password.encode()).hexdigest()
    
    
    
    def authenticate_user(self, email, password):
        """Autenticar usuário"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, password_hash, name, stripe_customer_id, is_active
                FROM users WHERE email = ?
            """, (email,))
            
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                return {'status': 'erro', 'message': 'Email não encontrado'}
            
            user_id, password_hash, name, stripe_customer_id, is_active = user
            
            if not is_active:
                return {'status': 'erro', 'message': 'Conta desativada'}
            
            if not self._verify_password(password_hash, password):
                return {'status': 'erro', 'message': 'Senha incorreta'}
            
            return {
                'status': 'sucesso',
                'user_id': user_id,
                'email': email,
                'name': name,
                'stripe_customer_id': stripe_customer_id
            }
            
        except Exception as e:
            print(f" Erro na autenticação: {e}")
            return {'status': 'erro', 'message': 'Erro interno do servidor'}
    
    def get_user_by_id(self, user_id):
        """Buscar usuário por ID"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, email, name, stripe_customer_id, is_active, created_at
                FROM users WHERE id = ?
            """, (user_id,))
            
            user = cursor.fetchone()
            conn.close()
            
            if user:
                return {
                    'id': user[0],
                    'email': user[1],
                    'name': user[2],
                    'stripe_customer_id': user[3],
                    'is_active': bool(user[4]),
                    'created_at': user[5]
                }
            
            return None
            
        except Exception as e:
            print(f" Erro ao buscar usuário: {e}")
            return None
    
    def get_user_limits(self, user_id):
        """Buscar limites do usuário baseado na assinatura ativa"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.messages_per_hour, p.messages_per_day, p.features, p.name
                FROM users u
                LEFT JOIN subscriptions s ON u.id = s.user_id AND s.status = 'active'
                LEFT JOIN plans p ON s.stripe_price_id = p.stripe_price_id
                WHERE u.id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            
            if result and result[0] is not None:
                features = json.loads(result[2]) if result[2] else []
                conn.close()
                return {
                    'plan_name': result[3],
                    'messages_per_hour': result[0],
                    'messages_per_day': result[1],
                    'features': features,
                    'is_premium': True
                }
            else:
                cursor.execute("""
                    SELECT messages_per_hour, messages_per_day, features, name
                    FROM plans WHERE stripe_price_id = 'price_free'
                """)
                free_plan = cursor.fetchone()
                conn.close()
                
                if free_plan:
                    features = json.loads(free_plan[2]) if free_plan[2] else []
                    return {
                        'plan_name': free_plan[3],
                        'messages_per_hour': free_plan[0],
                        'messages_per_day': free_plan[1],
                        'features': features,
                        'is_premium': False
                    }
                else:
                    return {
                        'plan_name': 'Gratuito',
                        'messages_per_hour': 10,
                        'messages_per_day': 50,
                        'features': ['basic_chat'],
                        'is_premium': False
                    }
                    
        except Exception as e:
            print(f" Erro ao buscar limites do usuário: {e}")
            return {
                'plan_name': 'Gratuito',
                'messages_per_hour': 10,
                'messages_per_day': 50,
                'features': ['basic_chat'],
                'is_premium': False
            }
    
    def get_all_plans(self):
        """Buscar todos os planos disponíveis"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, description, stripe_price_id, messages_per_hour,
                       messages_per_day, features, price_cents, interval_type
                FROM plans WHERE active = 1
                ORDER BY price_cents ASC
            """)
            
            plans = []
            for row in cursor.fetchall():
                features = json.loads(row[6]) if row[6] else []
                plans.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'stripe_price_id': row[3],
                    'messages_per_hour': row[4],
                    'messages_per_day': row[5],
                    'features': features,
                    'price_cents': row[7],
                    'price_formatted': f"R$ {row[7]/100:.2f}",
                    'interval_type': row[8]
                })
            
            conn.close()
            return plans
            
        except Exception as e:
            print(f" Erro ao buscar planos: {e}")
            return []

auth_manager = AuthManager()