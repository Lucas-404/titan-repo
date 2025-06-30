import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Diretórios
BASE_DIR = Path(__file__).parent
CHATS_DIR = BASE_DIR / 'chats'
BACKUPS_DIR = CHATS_DIR / 'backups'
EXPORTS_DIR = CHATS_DIR / 'exports'
STATIC_DIR = BASE_DIR / 'static'
TEMPLATES_DIR = BASE_DIR / 'templates'
DATABASE_FILE = BASE_DIR / 'titan_memory.db'
FEEDBACK_DATABASE_FILE = BASE_DIR / 'titan_feedbacks.db'

#  NOVO: Diretórios de sessões isoladas
SESSIONS_DIR = CHATS_DIR / 'sessions'
SECURITY_LOGS_DIR = BASE_DIR / 'security_logs'

# Configurações do chat
CHAT_HISTORY_FILE = CHATS_DIR / 'chat_history.json'  # Mantido para compatibilidade
MAX_BACKUPS = 10
AUTO_BACKUP = True

# Configurações de sessão - CORRIGIDAS
MAX_USUARIOS_SIMULTANEOS = 5
TIMEOUT_SESSAO = 3600  # 🔧 MUDANÇA: 1 hora ao invés de 30 minutos
TEMPO_RESPOSTA_ESTIMADO = 6  # segundos
CLEANUP_INTERVAL = 300  # 🔧 MUDANÇA: 5 minutos ao invés de 1 minuto

#  NOVO: Configurações de limpeza automática
AUTO_CLEANUP_ENABLED = True
CLEANUP_ORPHANED_DATA_INTERVAL = 3600  # 1 hora
CLEANUP_OLD_SESSIONS_DAYS = 7  # Limpar sessões após 7 dias
DATABASE_VACUUM_INTERVAL = 86400  # 24 horas - otimizar banco

# Configurações da IA
AI_BASE_URL = "http://localhost:11434/api/chat"
AI_MODEL = "Saturno"
AI_TEMPERATURE = 0.5
AI_MAX_TOKENS = 1024
AI_TIMEOUT = 300

# Flask
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("A SECRET_KEY não foi definida nas variáveis de ambiente. É obrigatória para produção.")

DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
HOST = '0.0.0.0'
PORT = 5001


#  NOVO: Configurações de segurança e logs
SAFE_LOGGING = True
MAX_LOG_VALUE_LENGTH = 50
SECURITY_MONITORING_ENABLED = True
MAX_DATA_ACCESS_PER_MINUTE = 50  # Limite de acessos por minuto
ALERT_SUSPICIOUS_ACTIVITY = True

#  NOVO: Configurações de isolamento
ENFORCE_SESSION_ISOLATION = True
LOG_CROSS_SESSION_ATTEMPTS = True
VALIDATE_SESSION_OWNERSHIP = True

#  NOVO: Funções utilitárias de segurança
def safe_log_value(value, max_length=MAX_LOG_VALUE_LENGTH):
    """Log seguro que oculta dados sensíveis"""
    if not SAFE_LOGGING:
        return value
    
    if value is None:
        return "None"
    
    str_value = str(value)
    if len(str_value) > max_length:
        return str_value[:max_length] + "..."
    return str_value

def safe_log_session_id(session_id):
    """Log seguro para session_id (mostra apenas primeiros 8 chars)"""
    if not session_id:
        return "None"
    return session_id[:8] + "..." if len(session_id) > 8 else session_id

def get_session_chat_dir(session_id):
    """ Retorna diretório específico da sessão para chats"""
    if not session_id:
        raise ValueError("session_id é obrigatório")
    
    session_dir = SESSIONS_DIR / session_id[:8]
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir

def get_session_backup_dir(session_id):
    """ Retorna diretório específico da sessão para backups"""
    if not session_id:
        raise ValueError("session_id é obrigatório")
    
    backup_dir = BACKUPS_DIR / session_id[:8]
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir

#  NOVO: Validações de segurança
def validate_session_access(session_id, resource_session_id):
    """Valida se a sessão pode acessar o recurso"""
    if not ENFORCE_SESSION_ISOLATION:
        return True
    
    if not session_id or not resource_session_id:
        return False
    
    return session_id == resource_session_id

def log_security_event(event_type, session_id, details=None):
    """ Log de eventos de segurança"""
    if not SECURITY_MONITORING_ENABLED:
        return
    
    import datetime
    timestamp = datetime.datetime.now().isoformat()
    safe_session = safe_log_session_id(session_id)
    
    log_entry = f"[{timestamp}] {event_type} - Sessão: {safe_session}"
    if details:
        safe_details = safe_log_value(details)
        log_entry += f" - Detalhes: {safe_details}"
    
    print(f" SECURITY: {log_entry}")
    
    # Salvar em arquivo de log se necessário
    if SECURITY_LOGS_DIR:
        SECURITY_LOGS_DIR.mkdir(exist_ok=True)
        log_file = SECURITY_LOGS_DIR / f"security_{datetime.date.today().isoformat()}.log"
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f" Erro ao salvar log de segurança: {e}")

# Criar diretórios
for directory in [CHATS_DIR, BACKUPS_DIR, EXPORTS_DIR, SESSIONS_DIR, SECURITY_LOGS_DIR]:
    directory.mkdir(exist_ok=True)

print(f" Configuração carregada - Base: {BASE_DIR}")
print(f" Chats salvos em: {CHATS_DIR}")
print(f" Sessões isoladas em: {SESSIONS_DIR}")
print(f" Logs de segurança em: {SECURITY_LOGS_DIR}")
print(f" Limpeza automática: {'Ativada' if AUTO_CLEANUP_ENABLED else 'Desativada'}")
print(f" Isolamento de sessão: {'Ativado' if ENFORCE_SESSION_ISOLATION else 'Desativado'}")
print(f" Timeout de sessão: {TIMEOUT_SESSAO}s ({TIMEOUT_SESSAO//60} minutos)")
print(f" Intervalo de limpeza: {CLEANUP_INTERVAL}s ({CLEANUP_INTERVAL//60} minutos)")

# --- Configurações Stripe ---

# Chaves Stripe (obrigatórias, carregadas do .env)
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# URLs de redirecionamento
STRIPE_SUCCESS_URL = os.getenv('STRIPE_SUCCESS_URL', 'http://localhost:5000/success')
STRIPE_CANCEL_URL = os.getenv('STRIPE_CANCEL_URL', 'http://localhost:5000/pricing')

# Price IDs dos produtos (obrigatórios, carregados do .env)
STRIPE_PRICES = {
    'basic_monthly': os.getenv('STRIPE_PRICE_BASIC_MONTHLY'),
    'basic_yearly': os.getenv('STRIPE_PRICE_BASIC_YEARLY'),
    'pro_monthly': os.getenv('STRIPE_PRICE_PRO_MONTHLY'),
    'pro_yearly': os.getenv('STRIPE_PRICE_PRO_YEA RLY'),
}

# Validação para garantir que as configurações do Stripe não estão vazias
if not all([STRIPE_PUBLISHABLE_KEY, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, all(STRIPE_PRICES.values())]):
    print("ALERTA: As configurações do Stripe (chaves e/ou Price IDs) não estão completas no arquivo .env. Funcionalidades de pagamento serão desativadas.")
    STRIPE_ENABLED = False
else:
    STRIPE_ENABLED = True

# Configuração dos planos e limites
PLAN_LIMITS = {
    'free': {
        'messages_per_hour': 10,
        'messages_per_day': 5, # Reduzido para 5 para teste
        'characters_per_message': 1000,
        'thinking_mode': False,
        'web_search': False,
        'memory_enabled': False,
        'features': ['basic_chat']
    },
    'basic': {
        'messages_per_hour': 100,
        'messages_per_day': 500,
        'characters_per_message': 5000,
        'thinking_mode': True,
        'web_search': True,
        'memory_enabled': True,
        'features': ['basic_chat', 'thinking_mode', 'memory', 'web_search']
    },
    'pro': {
        'messages_per_hour': 1000,
        'messages_per_day': 5000,
        'characters_per_message': 10000,
        'thinking_mode': True,
        'web_search': True,
        'memory_enabled': True,
        'priority_support': True,
        'features': ['basic_chat', 'thinking_mode', 'memory', 'web_search', 'priority_support']
    }
}

# Funções auxiliares
def get_plan_by_price_id(price_id):
    """Descobrir qual plano corresponde ao Price ID do Stripe"""
    price_to_plan = {
        STRIPE_PRICES['basic_monthly']: 'basic',
        STRIPE_PRICES['basic_yearly']: 'basic', 
        STRIPE_PRICES['pro_monthly']: 'pro',
        STRIPE_PRICES['pro_yearly']: 'pro',
    }
    plan_name = price_to_plan.get(price_id, 'free')
    return plan_name, PLAN_LIMITS[plan_name]

def get_price_id_by_plan(plan_name, interval='monthly'):
    """Buscar Price ID pelo nome do plano"""
    price_key = f"{plan_name}_{interval}"
    return STRIPE_PRICES.get(price_key)

def get_valid_price_ids():
    """Retorna lista de Price IDs válidos (sem placeholders)"""
    if not STRIPE_ENABLED:
        return []
    return [price_id for price_id in STRIPE_PRICES.values() if price_id]

print("Configurações Stripe carregadas")
if STRIPE_ENABLED:
    print(f"Chave Publicável Stripe: CONFIGURADA")
    print(f"Price IDs válidos: {get_valid_price_ids()}")
    print(f"URL de Sucesso: {STRIPE_SUCCESS_URL}")
    print(f"URL de Cancelamento: {STRIPE_CANCEL_URL}")
    print(f"Segredo do Webhook: CONFIGURADO")
else:
    print("Funcionalidades de pagamento desativadas. Configure as variáveis de ambiente do Stripe.")

print(f"Modo Debug: {DEBUG}")
print(f"Chave Secreta: {'CONFIGURADA' if SECRET_KEY else 'NÃO CONFIGURADA'}")