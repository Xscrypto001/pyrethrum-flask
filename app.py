from flask import Flask, render_template, redirect, url_for, request, session, flash
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Decorators

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('You do not have permission to view this page.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def farmer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'farmer':
            flash('You do not have permission to view this page.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'customer':
            flash('You do not have permission to view this page.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# Database Initialization

def init_db():
    with sqlite3.connect('ecommerce.db') as con:
        cur = con.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT,
                description TEXT,
                price REAL,
                image TEXT
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                product_id INTEGER,
                quantity INTEGER
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                total REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                password TEXT,
                profile_picture TEXT,
                role TEXT,
                approved INTEGER DEFAULT 0
            )
        ''')
        con.commit()

# Routes

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
@login_required
def services():
    with sqlite3.connect('ecommerce.db') as con:
        cur = con.cursor()
        cur.execute('SELECT * FROM products')
        products = cur.fetchall()
    return render_template('services.html', products=products)

@app.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    with sqlite3.connect('ecommerce.db') as con:
        cur = con.cursor()
        cur.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cur.fetchone()
    return render_template('product_detail.html', product=product)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    quantity = int(request.form['quantity'])
    user_id = session['user_id']
    with sqlite3.connect('ecommerce.db') as con:
        cur = con.cursor()
        cur.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)', (user_id, product_id, quantity))
        con.commit()
    flash('Item added to cart')
    return redirect(url_for('services'))

@app.route('/cart')
@login_required
def cart():
    user_id = session['user_id']
    with sqlite3.connect('ecommerce.db') as con:
        cur = con.cursor()
        cur.execute('''
            SELECT cart.id, products.name, products.price, cart.quantity
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.user_id = ?
        ''', (user_id,))
        cart_items = cur.fetchall()
    return render_template('cart.html', cart_items=cart_items)

@app.route('/checkout')
@login_required
def checkout():
    user_id = session['user_id']
    with sqlite3.connect('ecommerce.db') as con:
        cur = con.cursor()
        cur.execute('''
            SELECT products.price, cart.quantity
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.user_id = ?
        ''', (user_id,))
        cart_items = cur.fetchall()
        total = sum(item[0] * item[1] for item in cart_items)
        cur.execute('INSERT INTO orders (user_id, total) VALUES (?, ?)', (user_id, total))
        cur.execute('DELETE FROM cart WHERE user_id = ?', (user_id,))
        con.commit()
    flash('Checkout successful!')
    return redirect(url_for('services'))

@app.route('/profile')
@login_required
def profile():
    # Fetch user profile information from session or database
    user = {
        'username': session['username'],
        'email': 'user@example.com',  # Replace with actual email
        'profile_picture': session['profile_picture'],  # Assuming profile picture is stored in session
        # Add more profile information as needed
    }
    return render_template('profile.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect('ecommerce.db') as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
            user = cur.fetchone()
            if user:
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['profile_picture'] = user[3]
                session['role'] = user[4]
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials. Please try again.', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        profile_picture = 'profile_picture.png'  # Dummy profile picture
        approved = 1 if role == 'customer' else 0  # Automatically approve customers
        with sqlite3.connect('ecommerce.db') as con:
            cur = con.cursor()
            cur.execute("INSERT INTO users (username, password, profile_picture, role, approved) VALUES (?, ?, ?, ?, ?)", (username, password, profile_picture, role, approved))
            con.commit()
        if role == 'admin':
            flash('Admin account created. Waiting for approval.')
        elif role == 'farmer':
            flash('Farmer account created. Waiting for approval.')
        else:
            flash('Registration successful. You can now log in.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if 'username' in session:
        username = session['username']
        # Replace this with your actual way of fetching user data
        user = {
            'username': username,
            'email': 'user@example.com',  # Replace with actual email
            'registration_date': '2024-06-18',  # Replace with actual registration date
            # Add more user-related information as needed
        }
        if session.get('role') == 'admin':
            return render_template('admin_dashboard.html', user=user)
        elif session.get('role') == 'farmer':
            return render_template('farmer_dashboard.html', user=user)
        elif session.get('role') == 'customer':
            return render_template('customer_dashboard.html', user=user)
        else:
            flash('Unknown user role')
            return redirect(url_for('logout'))
    else:
        # Handle case when user is not logged in
        return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/manage_users')
@login_required
@admin_required
def manage_users():
    with sqlite3.connect('ecommerce.db') as con:
        cur = con.cursor()
        cur.execute('SELECT id, username, role, approved FROM users WHERE role = "farmer" AND approved = 0')
        pending_users = cur.fetchall()
    return render_template('manage_users.html', pending_users=pending_users)

@app.route('/approve_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    with sqlite3.connect('ecommerce.db') as con:
        cur = con.cursor()
        cur.execute('UPDATE users SET approved = 1 WHERE id = ?', (user_id,))
        con.commit()
    flash('User approved successfully.')
    return redirect(url_for('manage_users'))

@app.route('/reject_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def reject_user(user_id):
    with sqlite.connect('ecommerce.db') as con:
        cur = con.cursor()
        cur.execute('DELETE FROM users WHERE id = ?', (user_id,))
        con.commit()
    flash('User rejected successfully.')
    return redirect(url_for('manage_users'))

@app.route('/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        image = request.form['image']
        with sqlite3.connect('ecommerce.db') as con:
            cur = con.cursor()
            cur.execute("INSERT INTO products (name, description, price, image) VALUES (?, ?, ?, ?)", (name, description, price, image))
            con.commit()
        flash('Product added successfully.', 'success')
        return redirect(url_for('services'))
    return render_template('product_form.html')

@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    with sqlite3.connect('ecommerce.db') as con:
        cur = con.cursor()
        cur.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cur.fetchone()
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        image = request.form['image']
        with sqlite3.connect('ecommerce.db') as con:
            cur = con.cursor()
            cur.execute("UPDATE products SET name = ?, description = ?, price = ?, image = ? WHERE id = ?", (name, description, price, image, product_id))
            con.commit()
        flash('Product updated successfully.', 'success')
        return redirect(url_for('services'))
    return render_template('product_form.html', product=product)

@app.route('/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    with sqlite3.connect('ecommerce.db') as con:
        cur = con.cursor()
        cur.execute('DELETE FROM products WHERE id = ?', (product_id,))
        con.commit()
    flash('Product deleted successfully.', 'success')
    return redirect(url_for('services'))

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

