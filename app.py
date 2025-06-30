import os
import secrets
import threading
import time
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_cors import CORS

from config import SECRET_KEY, DEBUG, HOST, PORT, TEMPLATES_DIR, STATIC_DIR

def create_secure_app():    
    app = Flask(__name__, 
               template_folder=str(TEMPLATES_DIR),
               static_folder=str(STATIC_DIR))
    
    CORS(app, 
        origins=['https://titaniq.netlify.app'],
        supports_credentials=True,
        allow_headers=['Content-Type', 'Authorization', 'X-CSRFToken'],
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['WTF_CSRF_TIME_LIMIT'] = 7200  
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'
    app.config['PERMANENT_SESSION_LIFETIME'] = 7200  
    app.config['SESSION_COOKIE_DOMAIN'] = '.outzapp.com'  
    
    
    if DEBUG:
        app.config['SESSION_COOKIE_SECURE'] = False
        app.config['WTF_CSRF_ENABLED'] = False  
        force_https = False
    else:
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['WTF_CSRF_ENABLED'] = True
        force_https = True
    
    # CSRF Protection CORRIGIDO PARA FLASK 3.x
    csrf = CSRFProtect()
    csrf.init_app(app)  # CORRIGIDO: Adicionar inicialização
    if not DEBUG:
        print("CSRF ativado para produção")
    else:
        print(" CSRF criado mas permissivo para debug")
    
    limiter = Limiter(
        key_func=get_remote_address,  
        default_limits=["200 per day", "50 per hour"]
    )
    limiter.init_app(app)  
    
   
    if not DEBUG: 
        Talisman(app, 
            force_https=force_https,
            strict_transport_security=True,
            content_security_policy={
                'default-src': "'self'",
                'script-src': "'self' 'unsafe-inline'",
                'style-src': "'self' 'unsafe-inline'",
                'img-src': "'self' data:",
                'font-src': "'self'"
            }
        )
    
    @app.after_request
    def security_headers(response):
        """Headers de segurança obrigatórios"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    
    
        return response
    
    print(" DEBUG: Importando blueprints...")
    
    try:
        from routes.main_routes import create_main_blueprint
        main_bp = create_main_blueprint(csrf)
        app.register_blueprint(main_bp)
        print("Blueprint main_bp registrado")
    except Exception as e:
        print(f" Erro ao importar main_routes: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        from routes.auth_routes import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
        print("Blueprint auth_bp registrado")
    except Exception as e:
        print(f" Erro ao importar auth_routes: {e}")
        print("Continuando sem rotas de autenticação...")
    
    print(" DEBUG: Rotas registradas:")
    for rule in app.url_map.iter_rules():
        print(f"   {rule.methods} {rule.rule} -> {rule.endpoint}")
    
    try:
        from middleware.session_middleware import setup_session_middleware
        setup_session_middleware(app)
        print("Session middleware ATIVADO")
    except Exception as e:
        print(f"Erro ao configurar session middleware: {e}")
    
    try:
        from models.cache_manager import cache
        app.config['CACHE_TYPE'] = 'simple'
        app.config['CACHE_DEFAULT_TIMEOUT'] = 300
        cache.init_app(app)
        print("Cache configurado")
    except Exception as e:
        print(f"Cache não disponível: {e}")
    
    @app.errorhandler(403)
    def forbidden(error):
        return {'erro': 'Acesso negado'}, 403
    
    @app.errorhandler(429)
    def ratelimit_handler(error):
        return {'erro': 'Muitas requisições - tente novamente em alguns minutos'}, 429
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'erro': 'Erro interno do servidor'}, 500
    
    return app, csrf, limiter

def cache_cleanup_thread():
    """ Thread para limpar cache antigo"""
    while True:
        time.sleep(1800)
        try:
            from models.cache_manager import context_cache
            cleaned = context_cache.cleanup_old_cache()
            if cleaned > 0:
                print(f" Cache cleanup: {cleaned} sessões antigas removidas")
        except Exception as e:
            print(f" Erro na limpeza de cache: {e}")

print("Criando aplicação...")
app, csrf, limiter = create_secure_app()

cleanup_thread = threading.Thread(target=cache_cleanup_thread, daemon=True)
cleanup_thread.start()
print(" Thread de limpeza de cache iniciada")

if __name__ == '__main__':
    print("TITAN AI - SEGURO")
    print(f"CSRF Protection: {'DESABILITADO (DEBUG)' if DEBUG else 'ATIVO'}")
    print(f"Rate Limiting: ATIVO") 
    print(f"Security Headers: ATIVO")
    print(f"Acesse: http://{HOST}:{PORT}")
    
    app.run(
        host=HOST, 
        port=PORT, 
        debug=DEBUG,
        threaded=True,  
        use_reloader=False 
    )

AI_STREAM_CHUNK_SIZE = 4096
AI_STREAM_TIMEOUT = 200  
AI_THROTTLE_MS = 30
AI_BATCH_SIZE = 128
AI_NUM_THREADS = -1
AI_CONTEXT_SIZE = 8192