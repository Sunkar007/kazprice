from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3, hashlib
from datetime import datetime

app = Flask(__name__)
DATABASE = "kazprice.db"
app.secret_key = 'secret123'


@app.context_processor
def inject_view_flags():
    # Provide booleans to templates so Jinja does not need to inspect Python globals
    from flask import session as _session
    return {
        'has_favorites_view': ('favorites_view' in app.view_functions),
        'has_cart_view': ('cart_view' in app.view_functions),
        # convenience value for navbar badge
        'cart_count': sum(_session.get('cart', {}).values()) if _session.get('cart') else 0
    }

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_user_columns():
    """Ensure `users` table has phone and address columns, and cards table exists.
    Adds them if missing. This runs at app startup to avoid "no such column" errors on older databases.
    """
    try:
        conn = get_db_connection()
        # Ensure users columns
        cur = conn.execute("PRAGMA table_info(users)")
        cols = [r['name'] for r in cur.fetchall()]
        added = False
        if 'phone' not in cols:
            conn.execute('ALTER TABLE users ADD COLUMN phone TEXT')
            added = True
        if 'address' not in cols:
            conn.execute('ALTER TABLE users ADD COLUMN address TEXT')
            added = True
        
        # Ensure cards table exists
        try:
            conn.execute('PRAGMA table_info(cards)')
        except sqlite3.OperationalError:
            conn.execute('''
                CREATE TABLE cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    card_name TEXT NOT NULL,
                    balance INTEGER NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            added = True
        
        if added:
            conn.commit()
        conn.close()
    except sqlite3.OperationalError:
        # Table may not exist yet (fresh DB) — ignore; db_init.sql will create it
        try:
            conn.close()
        except Exception:
            pass


# Ensure schema compatibility on startup
ensure_user_columns()

@app.route('/')
def index():
    return redirect(url_for('login'))

# --- Тіркелу ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        pw_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)',
                (name, email, pw_hash, datetime.now())
            )
            conn.commit()
            flash('Тіркелу сәтті өтті! Енді жүйеге кіріңіз.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Бұл почта бұрын тіркелген!', 'danger')
            return redirect(url_for('register'))
        finally:
            conn.close()

    return render_template('register.html')

# --- Кіру ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        pw_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email=? AND password_hash=?', (email, pw_hash)).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('main'))
        else:
            flash('Почта немесе құпия сөз қате!', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# --- Басты бет ---
@app.route('/main')
def main():
    conn = get_db_connection()
    # Get product list with a best (minimal) price if prices table exists
    products = conn.execute('''
        SELECT p.*, MIN(pr.price) as price
        FROM products p
        LEFT JOIN prices pr ON pr.product_id = p.id
        GROUP BY p.id
    ''').fetchall()
    conn.close()
    
    # Row → dict түріне айналдыру
    products = [dict(p) for p in products]
    # session-backed favorites and cart
    favorites = session.get('favorites', [])
    cart = session.get('cart', {})

    return render_template('main.html', products=products, favorites=favorites, cart=cart)


def _get_products_by_ids(conn, ids):
    if not ids:
        return []
    q = 'SELECT p.*, MIN(pr.price) as price FROM products p LEFT JOIN prices pr ON pr.product_id=p.id WHERE p.id IN ({seq}) GROUP BY p.id'.format(seq=','.join(['?']*len(ids)))
    rows = conn.execute(q, ids).fetchall()
    return [dict(r) for r in rows]


@app.route('/favorites')
def favorites_view():
    favs = session.get('favorites', [])
    conn = get_db_connection()
    products = _get_products_by_ids(conn, favs)
    conn.close()
    return render_template('favorites.html', products=products)


@app.route('/cart')
def cart_view():
    cart = session.get('cart', {})
    ids = list(cart.keys())
    # convert string keys to ints for query
    ids_int = [int(i) for i in ids] if ids else []
    conn = get_db_connection()
    products = _get_products_by_ids(conn, ids_int)
    conn.close()

    # attach quantity
    for p in products:
        p['quantity'] = cart.get(str(p['id']), 0)

    return render_template('cart.html', products=products)


@app.route('/toggle_favorite', methods=['POST'])
def toggle_favorite():
    data = request.get_json() or {}
    pid = data.get('product_id')
    if pid is None:
        return jsonify({'error':'missing product_id'}), 400
    pid = int(pid)

    favs = set(session.get('favorites', []))
    action = 'added'
    if pid in favs:
        favs.remove(pid)
        action = 'removed'
    else:
        favs.add(pid)

    session['favorites'] = list(favs)
    session.modified = True
    return jsonify({'status': action, 'favorites': session['favorites']})


@app.route('/toggle_favorite/<int:product_id>', methods=['POST'])
def toggle_favorite_by_id(product_id: int):
    """Toggle favorite by URL path (POST) and return simple JSON {status: 'added'|'removed'}."""
    pid = int(product_id)
    favs = set(session.get('favorites', []))
    action = 'added'
    if pid in favs:
        favs.remove(pid)
        action = 'removed'
    else:
        favs.add(pid)

    session['favorites'] = list(favs)
    session.modified = True
    return jsonify({'status': action})


@app.route('/remove_favorite/<int:product_id>', methods=['POST'])
def remove_favorite(product_id: int):
    """Remove product_id from session['favorites'] and return JSON response for client-side removal."""
    pid = int(product_id)
    favs = set(session.get('favorites', []))
    if pid in favs:
        favs.remove(pid)
        session['favorites'] = list(favs)
        session.modified = True
        return jsonify({'status': 'removed', 'product_id': pid})
    else:
        return jsonify({'status': 'not_found', 'product_id': pid}), 404


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    data = request.get_json() or {}
    pid = data.get('product_id')
    qty = int(data.get('quantity', 1))
    if pid is None:
        return jsonify({'error':'missing product_id'}), 400
    pid = str(int(pid))

    cart = session.get('cart', {})
    cart[pid] = cart.get(pid, 0) + max(1, qty)
    session['cart'] = cart
    session.modified = True

    total_items = sum(cart.values())
    return jsonify({'status':'ok', 'cart_count': total_items})


@app.route('/update_cart_quantity', methods=['POST'])
def update_cart_quantity():
    data = request.get_json() or {}
    pid = data.get('product_id')
    qty = int(data.get('quantity', 0))
    if pid is None:
        return jsonify({'error': 'missing product_id'}), 400

    pid = str(int(pid))
    cart = session.get('cart', {})

    # remove item if qty <= 0
    if qty <= 0:
        if pid in cart:
            del cart[pid]
    else:
        cart[pid] = qty

    session['cart'] = cart
    session.modified = True

    # Recompute totals
    conn = get_db_connection()
    ids = [int(k) for k in cart.keys()] if cart else []
    products = _get_products_by_ids(conn, ids) if ids else []
    conn.close()

    # Find updated product price
    updated_price = 0
    for p in products:
        if str(p['id']) == pid:
            price = p.get('price') or 0
            updated_price = price * cart.get(pid, 0)

    total = 0
    for p in products:
        price = p.get('price') or 0
        qty_i = cart.get(str(p['id']), 0)
        total += price * qty_i

    # Also return current cart item count so the navbar badge can be updated
    cart_count = sum(cart.values()) if cart else 0
    return jsonify({'updated_price': updated_price, 'updated_total': total, 'cart_count': cart_count, 'status': 'ok'})


@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id: int):
    """Remove an item from the session cart by product_id and return updated totals and cart_count."""
    pid = str(int(product_id))
    cart = session.get('cart', {})

    removed = False
    if pid in cart:
        del cart[pid]
        removed = True

    session['cart'] = cart
    session.modified = True

    # Recompute totals
    conn = get_db_connection()
    ids = [int(k) for k in cart.keys()] if cart else []
    products = _get_products_by_ids(conn, ids) if ids else []
    conn.close()

    total = 0
    for p in products:
        price = p.get('price') or 0
        qty_i = cart.get(str(p['id']), 0)
        total += price * qty_i

    cart_count = sum(cart.values()) if cart else 0

    return jsonify({'status': 'removed' if removed else 'not_found', 'product_id': int(product_id), 'updated_total': total, 'cart_count': cart_count})


@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    session['cart'] = {}
    session.modified = True
    # Return new cart count (0) so frontend can update the UI immediately
    return jsonify({'status': 'cleared', 'cart_count': 0})

# --- Профиль ---
@app.route('/profile')
def profile():
    # Require login
    if 'user_id' not in session:
        flash('Профильді көру үшін алдымен кіріңіз!', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    # Select only the fields we need
    user = conn.execute('SELECT id, name, email, phone, address, created_at FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()

    # If the user record does not exist (stale session), clear session and redirect to login
    if not user:
        session.clear()
        flash('Пайдаланушы табылмады. Қайта кіруіңізді сұраймыз.', 'warning')
        return redirect(url_for('login'))

    return render_template('profile.html', user=user)


@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    # Require login
    if 'user_id' not in session:
        flash('Профильді өңдеу үшін алдымен кіріңіз!', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        phone = request.form.get('phone','').strip()
        address = request.form.get('address','').strip()

        errors = []
        if not name:
            errors.append('Атыңыз қажет.')
        if not email or '@' not in email:
            errors.append('Жарамды почта қажет.')

        if errors:
            for e in errors:
                flash(e, 'error')
            # re-render form with posted values
            conn.close()
            return render_template('edit_profile.html', user={'id':user_id,'name':name,'email':email,'phone':phone,'address':address})

        try:
            conn.execute('UPDATE users SET name=?, email=?, phone=?, address=? WHERE id=?', (name, email, phone, address, user_id))
            conn.commit()
            flash('Профиль сәтті жаңартылды.', 'success')
            return redirect(url_for('profile'))
        except sqlite3.IntegrityError:
            flash('Бұл почта басқа пайдаланушыға тіркелген болуы мүмкін.', 'error')
            conn.close()
            return render_template('edit_profile.html', user={'id':user_id,'name':name,'email':email,'phone':phone,'address':address})
    else:
        user = conn.execute('SELECT id, name, email, phone, address FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        if not user:
            session.clear()
            flash('Пайдаланушы табылмады. Қайта кіруіңізді сұраймыз.', 'warning')
            return redirect(url_for('login'))
        return render_template('edit_profile.html', user=user)

# --- Шығу ---
@app.route('/logout')
def logout():
    # Clear the session and redirect to login
    session.clear()
    flash('Сіз жүйеден шықтыңыз.', 'info')
    return redirect(url_for('login'))


# --- Demo form: shows validation and flash messages ---
@app.route('/demo-form', methods=['GET', 'POST'])
def demo_form():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        message = request.form.get('message','').strip()

        errors = []
        if not name:
            errors.append('Атыңызды енгізіңіз.')
        if not email or '@' not in email:
            errors.append('Жарамды почта енгізіңіз.')
        if not message or len(message) < 10:
            errors.append('Хабарлама кемінде 10 таңбадан тұру керек.')

        if errors:
            for e in errors:
                flash(e, 'error')
            # Keep form values by re-rendering template (request.form used in template)
            return render_template('demo_form.html')

        # Simulate successful processing
        flash('Хабарлама жіберілді. Құрметпен, KazPrice командасы.', 'success')
        return redirect(url_for('demo_form'))

    return render_template('demo_form.html')

# --- Checkout flow ---
@app.route('/checkout')
def checkout():
    """Display checkout page with cart items and delivery cost."""
    if 'user_id' not in session:
        flash('Төлеуге өту үшін алдымен кіріңіз!', 'warning')
        return redirect(url_for('login'))

    cart = session.get('cart', {})
    if not cart:
        flash('Себет бос!', 'warning')
        return redirect(url_for('cart_view'))

    # Get cart items with prices
    ids = [int(k) for k in cart.keys()] if cart else []
    conn = get_db_connection()
    products = _get_products_by_ids(conn, ids) if ids else []
    conn.close()

    # Attach quantities
    for p in products:
        p['quantity'] = cart.get(str(p['id']), 0)

    # Calculate cart total
    cart_total = sum((p.get('price') or 0) * (p.get('quantity') or 0) for p in products)
    
    # Delivery cost (fixed)
    delivery_cost = 1500

    return render_template('checkout.html', products=products, cart_total=cart_total, delivery_cost=delivery_cost)


@app.route('/payment')
def payment():
    """Display payment method selection page."""
    if 'user_id' not in session:
        flash('Төлеуге өту үшін алдымен кіріңіз!', 'warning')
        return redirect(url_for('login'))

    cart = session.get('cart', {})
    if not cart:
        flash('Себет бос!', 'warning')
        return redirect(url_for('cart_view'))

    # Get cart total
    ids = [int(k) for k in cart.keys()] if cart else []
    conn = get_db_connection()
    products = _get_products_by_ids(conn, ids) if ids else []
    
    # Get user's cards
    cards = conn.execute('SELECT id, card_name, balance FROM cards WHERE user_id = ? ORDER BY created_at DESC', 
                         (session['user_id'],)).fetchall()
    cards = [dict(c) for c in cards] if cards else []
    
    conn.close()

    # Calculate total
    cart_total = sum((p.get('price') or 0) * (cart.get(str(p['id']), 0) or 0) for p in products)
    delivery_cost = 1500
    total_amount = cart_total + delivery_cost

    return render_template('payment.html', cards=cards, cart_total=cart_total, 
                         delivery_cost=delivery_cost, total_amount=total_amount)


@app.route('/process_payment', methods=['POST'])
def process_payment():
    """Process payment: deduct from card and clear cart."""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Кіруіңіз қажет'}), 401

    cart = session.get('cart', {})
    if not cart:
        return jsonify({'status': 'error', 'message': 'Себет бос'}), 400

    # Get request data
    data = request.get_json() or {}
    card_id = data.get('card_id')
    
    if not card_id:
        return jsonify({'status': 'error', 'message': 'Картасын таңдаңыз'}), 400

    # Get cart total
    ids = [int(k) for k in cart.keys()] if cart else []
    conn = get_db_connection()
    products = _get_products_by_ids(conn, ids) if ids else []
    
    cart_total = sum((p.get('price') or 0) * (cart.get(str(p['id']), 0) or 0) for p in products)
    delivery_cost = 1500
    total_amount = cart_total + delivery_cost

    # Get the card
    card = conn.execute('SELECT id, balance FROM cards WHERE id = ? AND user_id = ?', 
                       (int(card_id), session['user_id'])).fetchone()
    
    if not card:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Карта табылмады'}), 404

    card_balance = card['balance']
    
    # Check if enough balance
    if card_balance < total_amount:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Қаражатыңыз жеткіліксіз'}), 400

    # Deduct from card balance
    new_balance = card_balance - total_amount
    conn.execute('UPDATE cards SET balance = ? WHERE id = ?', (new_balance, card['id']))
    
    # Clear session cart
    session['cart'] = {}
    session.modified = True
    
    conn.commit()
    conn.close()

    return jsonify({
        'status': 'success', 
        'message': 'Төлем сәтті жасалды',
        'new_balance': new_balance,
        'total_paid': total_amount
    })


if __name__ == '__main__':
    app.run(debug=True)
