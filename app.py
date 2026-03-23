from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_for_banking_app'
DATABASE = 'banking.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return dict(current_user=user)

@app.template_filter('currency')
def format_currency(value):
    return "${:,.2f}".format(value)

@app.template_filter('datetime')
def format_datetime(value):
    if not value:
        return ""
    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%A, %b %d, %Y %I:%M %p")
    except:
        return value

# --- Auth Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES ---
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        account_number = request.form.get('account_number')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
            
        hashed_password = generate_password_hash(password)
        db = get_db()
        
        existing = db.execute('SELECT * FROM users WHERE email = ? OR account_number = ?', (email, account_number)).fetchone()
        if existing:
            flash('Email or Account Number already registered.', 'error')
            return render_template('register.html')
            
        try:
            cursor = db.cursor()
            cursor.execute('''
                INSERT INTO users (full_name, email, phone, account_number, password, balance, cibil_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (full_name, email, phone, account_number, hashed_password, 1000.00, 750))
            db.commit()
            
            user_id = cursor.lastrowid
            cursor.execute('''
                INSERT INTO accounts (user_id, account_type, balance) VALUES (?, ?, ?)
            ''', (user_id, 'Savings', 1000.00))
            db.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.rollback()
            flash('An error occurred during registration.', 'error')
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    
    # Get recent transactions
    transactions = db.execute('''
        SELECT * FROM transactions 
        WHERE sender_id = ? OR receiver_id = ? 
        ORDER BY timestamp DESC LIMIT 5
    ''', (session['user_id'], session['user_id'])).fetchall()
    
    # We will compute monthly spending for chart logic in javascript using an API endpoint, 
    # but let's pass initial data via template for simplicity if needed.
    
    return render_template('dashboard.html', transactions=transactions)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        
        db = get_db()
        db.execute('UPDATE users SET full_name = ?, phone = ? WHERE id = ?', (full_name, phone, session['user_id']))
        db.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
        
    return render_template('profile.html')

@app.route('/transactions')
@login_required
def transactions():
    db = get_db()
    type_filter = request.args.get('type', 'all')
    
    query = 'SELECT * FROM transactions WHERE sender_id = ? OR receiver_id = ? ORDER BY timestamp DESC'
    params = [session['user_id'], session['user_id']]
    
    all_transactions = db.execute(query, params).fetchall()
    
    filtered_transactions = []
    for t in all_transactions:
        is_sender = (t['sender_id'] == session['user_id'])
        t_type = 'debit' if is_sender else 'credit'
        if type_filter == 'all' or type_filter == t_type:
            filtered_transactions.append({
                'id': t['id'],
                'amount': t['amount'],
                'type': t['type'],
                'flow_type': t_type,
                'status': t['status'],
                'timestamp': t['timestamp'],
                'other_party_id': t['receiver_id'] if is_sender else t['sender_id']
            })
            
    return render_template('transactions.html', transactions=filtered_transactions, filter=type_filter)

@app.route('/send_money', methods=['GET', 'POST'])
@login_required
def send_money():
    if request.method == 'POST':
        receiver_account = request.form.get('account_number')
        amount = request.form.get('amount')
        
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except:
            flash('Invalid amount.', 'error')
            return redirect(url_for('send_money'))
            
        db = get_db()
        sender = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        
        if sender['balance'] < amount:
            flash('Insufficient funds.', 'error')
            return redirect(url_for('send_money'))
            
        receiver = db.execute('SELECT * FROM users WHERE account_number = ?', (receiver_account,)).fetchone()
        
        if not receiver:
            flash('Receiver account not found.', 'error')
            return redirect(url_for('send_money'))
            
        if receiver['id'] == sender['id']:
            flash('You cannot send money to yourself.', 'error')
            return redirect(url_for('send_money'))
            
        try:
            cursor = db.cursor()
            cursor.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, sender['id']))
            cursor.execute('UPDATE accounts SET balance = balance - ? WHERE user_id = ?', (amount, sender['id']))
            cursor.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, receiver['id']))
            cursor.execute('UPDATE accounts SET balance = balance + ? WHERE user_id = ?', (amount, receiver['id']))
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO transactions (sender_id, receiver_id, amount, type, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (sender['id'], receiver['id'], amount, 'transfer', 'completed', timestamp))
            
            db.commit()
            flash(f'Successfully transferred ${amount:.2f} to {receiver["full_name"]}', 'success')
            return redirect(url_for('transactions'))
            
        except sqlite3.Error as e:
            db.rollback()
            flash('Transaction failed.', 'error')
            
    return render_template('send_money.html')

@app.route('/cibil')
@login_required
def cibil():
    return render_template('cibil.html')

@app.route('/services', methods=['GET', 'POST'])
@login_required
def services():
    if request.method == 'POST':
        service_type = request.form.get('service_type')
        amount = request.form.get('amount')
        
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except:
            flash('Invalid amount.', 'error')
            return redirect(url_for('services'))
            
        db = get_db()
        sender = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        
        if sender['balance'] < amount:
            flash('Insufficient funds.', 'error')
            return redirect(url_for('services'))
            
        try:
            cursor = db.cursor()
            cursor.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, sender['id']))
            cursor.execute('UPDATE accounts SET balance = balance - ? WHERE user_id = ?', (amount, sender['id']))
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO transactions (sender_id, receiver_id, amount, type, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (sender['id'], 0, amount, f'{service_type}_payment', 'completed', timestamp))
            
            db.commit()
            flash(f'{service_type.replace("_", " ").title()} of ${amount:.2f} successful!', 'success')
            return redirect(url_for('services'))
            
        except sqlite3.Error as e:
            db.rollback()
            flash('Payment failed.', 'error')
            
    return render_template('services.html')

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        from init_db import init_db
        init_db()
    app.run(debug=True, port=5000)
