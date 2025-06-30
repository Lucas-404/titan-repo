from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from models.auth_manager import auth_manager
from models.rate_limiter import rate_limiter
import stripe
from config import (
    STRIPE_PUBLISHABLE_KEY, 
    STRIPE_SUCCESS_URL, 
    STRIPE_CANCEL_URL, 
    STRIPE_SECRET_KEY, 
    get_price_id_by_plan,
    DATABASE_FILE,
    get_valid_price_ids
    )
import time
import sqlite3
from datetime import datetime
import uuid

stripe.api_key = STRIPE_SECRET_KEY

# Criar blueprint para rotas de autenticação
auth_bp = Blueprint('auth', __name__)

# =================== ROTAS DE REGISTRO E LOGIN ===================

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registro de novo usuário"""
    if request.method == 'GET':
        # Mostrar página de registro
        return render_template('auth/register.html')
    
    try:
        # Obter dados do formulário
        data = request.get_json() if request.is_json else request.form
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        
        # Validações básicas
        if not email or '@' not in email:
            return jsonify({'status': 'erro', 'message': 'Email inválido'}), 400
        
        if not password or len(password) < 6:
            return jsonify({'status': 'erro', 'message': 'Senha deve ter pelo menos 6 caracteres'}), 400
        
        if not name or len(name) < 2:
            return jsonify({'status': 'erro', 'message': 'Nome deve ter pelo menos 2 caracteres'}), 400
        
        # Criar usuário
        resultado = auth_manager.create_user(email, password, name)
        
        if resultado['status'] == 'sucesso':
            # Login automático após registro
            session['user_id'] = resultado['user_id']
            session['user_email'] = email
            session['user_name'] = name
            session.permanent = True
            
            print(f"🆕 Novo usuário registrado e logado: {email} (ID: {resultado['user_id']})")
            
            return jsonify({
                'status': 'sucesso',
                'message': 'Conta criada com sucesso!',
                'user_id': resultado['user_id'],
                'redirect': '/dashboard'
            })
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        print(f" Erro no registro: {e}")
        return jsonify({'status': 'erro', 'message': 'Erro interno do servidor'}), 500

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login do usuário"""
    if request.method == 'GET':
        # Mostrar página de login
        return render_template('auth/login.html')
    
    try:
        # Obter dados do formulário
        data = request.get_json() if request.is_json else request.form
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'status': 'erro', 'message': 'Email e senha são obrigatórios'}), 400
        
        # Autenticar usuário
        resultado = auth_manager.authenticate_user(email, password)
        
        if resultado['status'] == 'sucesso':
            # Criar sessão
            session['user_id'] = resultado['user_id']
            session['user_email'] = resultado['email']
            session['user_name'] = resultado['name']
            session.permanent = True
            
            print(f" Usuário logado: {email} (ID: {resultado['user_id']})")
            
            return jsonify({
                'status': 'sucesso',
                'message': 'Login realizado com sucesso!',
                'user_id': resultado['user_id'],
                'redirect': '/dashboard'
            })
        else:
            return jsonify(resultado), 401
            
    except Exception as e:
        print(f" Erro no login: {e}")
        return jsonify({'status': 'erro', 'message': 'Erro interno do servidor'}), 500

@auth_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    """Logout do usuário"""
    user_email = session.get('user_email', 'usuário')
    
    # Limpar sessão
    session.clear()
    
    print(f"👋 Usuário deslogado: {user_email}")
    
    if request.is_json:
        return jsonify({'status': 'sucesso', 'message': 'Logout realizado com sucesso'})
    else:
        flash('Logout realizado com sucesso', 'success')
        return redirect(url_for('main.home'))

# =================== ROTAS DE DASHBOARD E PERFIL ===================

@auth_bp.route('/dashboard')
def dashboard():
    """Dashboard do usuário logado"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    
    try:
        # Buscar informações do usuário
        user_info = auth_manager.get_user_by_id(user_id)
        if not user_info:
            session.clear()
            return redirect(url_for('auth.login'))
        
        # Buscar limites e plano atual
        limits = auth_manager.get_user_limits(user_id)
        
        # Buscar uso atual
        usage = rate_limiter.get_current_usage(user_id)
        
        # Buscar todos os planos disponíveis
        all_plans = auth_manager.get_all_plans()
        
        return render_template('auth/dashboard.html', 
                             user=user_info,
                             limits=limits,
                             usage=usage,
                             plans=all_plans)
        
    except Exception as e:
        print(f" Erro no dashboard: {e}")
        flash('Erro ao carregar dashboard', 'error')
        return redirect(url_for('main.home'))

@auth_bp.route('/profile')
def profile():
    """Perfil do usuário"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    
    try:
        # Buscar informações do usuário
        user_info = auth_manager.get_user_by_id(user_id)
        
        # Buscar estatísticas de uso
        stats = rate_limiter.get_usage_stats(user_id, days=30)
        
        return render_template('auth/profile.html', 
                             user=user_info,
                             stats=stats)
        
    except Exception as e:
        print(f" Erro no perfil: {e}")
        flash('Erro ao carregar perfil', 'error')
        return redirect(url_for('auth.dashboard'))

# =================== ROTAS DE ASSINATURA (STRIPE) ===================

@auth_bp.route('/pricing')
def pricing():
    """Página de planos e preços"""
    try:
        # Buscar todos os planos
        plans = auth_manager.get_all_plans()
        
        # Se usuário logado, buscar plano atual
        current_plan = None
        if 'user_id' in session:
            limits = auth_manager.get_user_limits(session['user_id'])
            current_plan = limits.get('plan_name', 'Gratuito')
        
        return render_template('auth/pricing.html', 
                             plans=plans,
                             current_plan=current_plan,
                             stripe_publishable_key=STRIPE_PUBLISHABLE_KEY)
        
    except Exception as e:
        print(f" Erro na página de preços: {e}")
        flash('Erro ao carregar planos', 'error')
        return redirect(url_for('main.home'))

@auth_bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Criar sessão de checkout do Stripe"""
    try:
        data = request.get_json()
        print(f"🔍 [DEBUG] Dados recebidos: {data}")
        
        price_id = data.get('price_id')
        print(f"🔍 [DEBUG] Price ID: {price_id}")
        
        if not price_id:
            return jsonify({'error': 'Price ID é obrigatório'}), 400
        
        #  USAR FUNÇÃO DO CONFIG EM VEZ DE HARDCODE
        try:
            valid_price_ids = get_valid_price_ids()
            print(f"🔍 [DEBUG] Price IDs válidos do config: {valid_price_ids}")
        except Exception as e:
            print(f" Erro ao obter Price IDs: {e}")
            #  FALLBACK COM PRICE IDS CORRETOS
            valid_price_ids = [
                'price_1Rb8yJI0nP81FHlVezCBt5jT',  #  CORRIGIDO: "8y" e "ez"
                'price_1Rb92YI0nP81FHlVGTp9sYKT'   #  Pro (já estava certo)
            ]
        
        if price_id not in valid_price_ids:
            print(f" Price ID inválido: {price_id}")
            print(f" Price IDs válidos: {valid_price_ids}")
            return jsonify({'error': f'Price ID inválido: {price_id}'}), 400
        
        # Verificar se usuário está logado, se não, criar anônimo
        user_id = session.get('user_id')
        print(f"🔍 [DEBUG] User ID da sessão: {user_id}")
        
        if not user_id:
            # Criar usuário anônimo temporário
            user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            timestamp = int(time.time())
            anon_email = f"anon_{user_ip.replace('.', '_')}_{timestamp}@temp.local"
            
            result = auth_manager.create_user(
                email=anon_email,
                password="temp_password",
                name=f"Usuário Anônimo {user_ip}"
            )
            
            if result['status'] == 'sucesso':
                user_id = result['user_id']
                session['user_id'] = user_id
                session['user_email'] = anon_email
                session['user_name'] = f"Anônimo {user_ip}"
                session['is_anonymous'] = True
                session.permanent = True
                print(f"🔍 [DEBUG] Usuário anônimo criado: {user_id}")
            else:
                print(f" Erro ao criar usuário anônimo: {result}")
                return jsonify({'error': 'Erro ao criar usuário'}), 400
        
        # Buscar usuário
        user_info = auth_manager.get_user_by_id(user_id)
        print(f"🔍 [DEBUG] User info: {user_info}")
        
        if not user_info:
            return jsonify({'error': 'Usuário não encontrado'}), 400
        
        stripe_customer_id = user_info.get('stripe_customer_id')
        print(f"🔍 [DEBUG] Stripe Customer ID: {stripe_customer_id}")
     
        #  SE CUSTOMER ID É NULL, CRIAR UM NOVO
        if not stripe_customer_id:
            print(" Customer ID é None, criando novo customer...")
            try:
                stripe_customer = stripe.Customer.create(
                    email=user_info['email'],
                    name=user_info['name'],
                    metadata={
                        'user_id': str(user_id),
                        'source': 'titan_checkout'
                    }
                )
                stripe_customer_id = stripe_customer.id
                
                #  ATUALIZAR NO BANCO
                conn = sqlite3.connect(DATABASE_FILE)
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET stripe_customer_id = ? WHERE id = ?",
                              (stripe_customer_id, user_id))
                conn.commit()
                conn.close()
                
                print(f" Novo customer criado: {stripe_customer_id}")
                
            except Exception as stripe_error:
                print(f" Erro ao criar customer: {stripe_error}")
                return jsonify({'error': f'Erro ao criar customer Stripe: {str(stripe_error)}'}), 400
        
        #  CRIAR SESSÃO DE CHECKOUT COM VALIDAÇÃO
        try:
            checkout_session = stripe.checkout.Session.create(
                customer=stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=f"{STRIPE_SUCCESS_URL}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=STRIPE_CANCEL_URL,
                metadata={
                    'user_id': str(user_id),
                    'price_id': price_id
                },
                allow_promotion_codes=True,
                billing_address_collection='auto'
            )
            
            print(f"Checkout criado: {checkout_session.url}")
            
            return jsonify({
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id
            })
            
        except stripe.error.InvalidRequestError as e:
            print(f" Erro de request inválido no Stripe: {e}")
            return jsonify({'error': f'Erro no Stripe: {str(e)}'}), 400
            
        except Exception as stripe_error:
            print(f" Erro genérico no Stripe: {stripe_error}")
            return jsonify({'error': f'Erro ao criar checkout: {str(stripe_error)}'}), 500
        
    except Exception as e:
        print(f" Erro geral no checkout: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@auth_bp.route('/success')
def payment_success():
    """Página de sucesso após pagamento"""
    session_id = request.args.get('session_id')
    
    if session_id:
        try:
            # Verificar sessão do Stripe
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            
            return render_template('auth/success.html', 
                                 session=checkout_session)
        except:
            pass
    
    return render_template('auth/success.html')

@auth_bp.route('/cancel')
def payment_cancel():
    """Página de cancelamento de pagamento"""
    return render_template('auth/cancel.html')

# =================== API ENDPOINTS ===================

@auth_bp.route('/api/current-user')
def api_current_user():
    """API para obter usuário atual"""
    if 'user_id' not in session:
        return jsonify({'logged_in': False})
    
    try:
        user_info = auth_manager.get_user_by_id(session['user_id'])
        limits = auth_manager.get_user_limits(session['user_id'])
        usage = rate_limiter.get_current_usage(session['user_id'])
        
        return jsonify({
            'logged_in': True,
            'user': {
                'id': user_info['id'],
                'email': user_info['email'],
                'name': user_info['name']
            },
            'plan': limits,
            'usage': usage
        })
        
    except Exception as e:
        print(f" Erro na API current-user: {e}")
        return jsonify({'logged_in': False})

@auth_bp.route('/api/usage')
def api_usage():
    """API para obter uso atual do usuário"""
    if 'user_id' not in session:
        return jsonify({'error': 'Login necessário'}), 401
    
    try:
        usage = rate_limiter.get_current_usage(session['user_id'])
        return jsonify(usage)
        
    except Exception as e:
        print(f" Erro na API usage: {e}")
        return jsonify({'error': 'Erro interno'}), 500

# =================== MIDDLEWARES E HELPERS ===================

def login_required(f):
    """Decorator para rotas que requerem login"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Login necessário'}), 401
            else:
                flash('Você precisa fazer login', 'warning')
                return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Helper para obter usuário atual da sessão"""
    if 'user_id' in session:
        return auth_manager.get_user_by_id(session['user_id'])
    return None

print(" Rotas de autenticação carregadas")

def create_user(self, email, password, name=None):
    """Criar novo usuário e customer no Stripe"""
    try:
        # 1. Validar email
        if not email or '@' not in email:
            return {'status': 'erro', 'message': 'Email inválido'}
        
        # 2. Verificar se email já existe
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return {'status': 'erro', 'message': 'Email já cadastrado'}
        
        # 3. Hash da senha
        password_hash = self._hash_password(password)
        
        # 4.  TENTAR CRIAR CUSTOMER NO STRIPE COM RETRY
        stripe_customer_id = None
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                stripe_customer = stripe.Customer.create(
                    email=email,
                    name=name,
                    metadata={
                        'source': 'titan_app',
                        'created_at': datetime.now().isoformat(),
                        'attempt': str(attempt + 1)
                    }
                )
                stripe_customer_id = stripe_customer.id
                print(f" Customer Stripe criado (tentativa {attempt + 1}): {stripe_customer_id}")
                break
                
            except Exception as stripe_error:
                print(f" Tentativa {attempt + 1} falhou: {stripe_error}")
                if attempt == max_retries - 1:
                    #  NA ÚLTIMA TENTATIVA, USAR ID TEMPORÁRIO
                    stripe_customer_id = f"temp_customer_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                    print(f" Usando customer temporário: {stripe_customer_id}")
                time.sleep(1)  # Aguardar 1 segundo antes da próxima tentativa
        
        # 5. Salvar usuário no banco
        cursor.execute("""
            INSERT INTO users (email, password_hash, name, stripe_customer_id)
            VALUES (?, ?, ?, ?)
        """, (email, password_hash, name, stripe_customer_id))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"👤 Usuário criado: {email} (ID: {user_id})")
        
        return {
            'status': 'sucesso',
            'user_id': user_id,
            'stripe_customer_id': stripe_customer_id,
            'message': 'Usuário criado com sucesso'
        }
        
    except Exception as e:
        print(f" Erro ao criar usuário: {e}")
        return {'status': 'erro', 'message': 'Erro interno do servidor'}