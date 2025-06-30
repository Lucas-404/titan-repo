@main_bp.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400
    
    # Processar eventos
    if event['type'] == 'customer.subscription.created':
        handle_subscription_created(event['data']['object'])
    elif event['type'] == 'customer.subscription.updated':
        handle_subscription_updated(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_deleted(event['data']['object'])
    
    return 'Success', 200

def handle_subscription_created(subscription):
    """Nova assinatura criada"""
    customer_id = subscription['customer']
    
    # Buscar usuário
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id FROM users WHERE stripe_customer_id = ?
    """, (customer_id,))
    
    user = cursor.fetchone()
    if user:
        # Inserir/atualizar assinatura
        cursor.execute("""
            INSERT OR REPLACE INTO subscriptions 
            (user_id, stripe_subscription_id, stripe_price_id, status,
             current_period_start, current_period_end)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user[0],
            subscription['id'],
            subscription['items']['data'][0]['price']['id'],
            subscription['status'],
            subscription['current_period_start'],
            subscription['current_period_end']
        ))
        
        conn.commit()
    
    conn.close()