from flask import Flask, request, render_template, redirect, url_for, session
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------- DB SETUP --------------------
def init_db():
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS media (id INTEGER PRIMARY KEY, filename TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS assignments (display_id TEXT, media_id INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            quantity INTEGER,
            franchise_id TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_name TEXT,
            action TEXT,
            item_name TEXT,
            quantity INTEGER,
            franchise_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            action_score INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password_hash TEXT,
            role TEXT,
            franchise_id TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS franchises (
            id TEXT PRIMARY KEY,
            location TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS displays (
    display_id TEXT PRIMARY KEY,
    franchise_id TEXT,
    display_name TEXT
);
''')


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


# -------------------- REGISTER --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        franchise_id = request.form['franchise_id']
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        existing_user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if existing_user:
            return 'Username already exists.'
        conn.execute('''INSERT INTO users (username, password_hash, role, franchise_id) VALUES (?, ?, ?, ?)''',
                     (username, hashed_password, role, franchise_id))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')


# -------------------- AUTH --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['franchise_id'] = user['franchise_id']
            return redirect(url_for('home'))
        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -------------------- ROUTES --------------------
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    role = session['role']
    franchise_id = session['franchise_id']
    conn = get_db_connection()

    if role == 'owner':
        franchises = conn.execute('SELECT * FROM franchises').fetchall()
        low_inventory = conn.execute('SELECT item_name, quantity, franchise_id FROM inventory WHERE quantity < 5').fetchall()
        return render_template('index.html', role=role, franchises=franchises, low_inventory=low_inventory)

    elif role == 'manager':
        franchise = conn.execute('SELECT * FROM franchises WHERE id = ?', (franchise_id,)).fetchone()
        inventory = conn.execute('SELECT * FROM inventory WHERE franchise_id = ?', (franchise_id,)).fetchall()
        logs = conn.execute('SELECT * FROM logs WHERE franchise_id = ? ORDER BY timestamp DESC LIMIT 10', (franchise_id,)).fetchall()
        return render_template('index.html', role=role, franchise=franchise, inventory=inventory, logs=logs)

    elif role == 'staff':
        return render_template('index.html', role=role)

    return 'Invalid role'

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if session.get('role') != 'owner':
        return 'Unauthorized'
    
    conn = get_db_connection()

    # Handle file upload
    if request.method == 'POST':
        f = request.files['media']
        filepath = os.path.join(UPLOAD_FOLDER, f.filename)
        f.save(filepath)
        conn.execute("INSERT INTO media (filename) VALUES (?)", (f.filename,))
        conn.commit()
        return redirect(url_for('upload'))

    # Pagination Logic
    page = request.args.get('page', 1, type=int)  # Get the page number from the query string, default is 1
    items_per_page = 6  # Adjust the number of items per page
    offset = (page - 1) * items_per_page

    # Get the paginated media files
    media_files = conn.execute("SELECT * FROM media LIMIT ? OFFSET ?", (items_per_page, offset)).fetchall()

    # Get the total count of media files for pagination
    total_files = conn.execute("SELECT COUNT(*) FROM media").fetchone()[0]
    total_pages = (total_files + items_per_page - 1) // items_per_page  # Calculate the total number of pages

    conn.close()

    return render_template('upload.html', media_files=media_files, page=page, total_pages=total_pages)



@app.route('/assign', methods=['GET', 'POST'])
def assign():
    with sqlite3.connect("database.db") as conn:
        media = conn.execute("SELECT id, filename FROM media").fetchall()

    if request.method == 'POST':
        display_id = request.form['display_id']
        media_id = request.form['media_id']
        with sqlite3.connect("database.db") as conn:
            conn.execute("INSERT INTO assignments (display_id, media_id) VALUES (?, ?)", (display_id, media_id))
        return redirect(url_for('assign'))

    return render_template('assign.html', media=media)

@app.route('/display/<display_id>')
def display(display_id):
    with get_db_connection() as conn:
        row = conn.execute("""
            SELECT m.filename FROM assignments a
            JOIN media m ON m.id = a.media_id
            WHERE a.display_id = ?
            ORDER BY a.rowid DESC LIMIT 1
        """, (display_id,)).fetchone()
        media_file = row[0] if row else None
        inventory = conn.execute("""
            SELECT item_name, quantity FROM inventory WHERE franchise_id = ?
        """, (display_id,)).fetchall()
    return render_template('display.html', filename=media_file, inventory=inventory, franchise_id=display_id)

@app.route('/inventory')
def inventory():
    # Check if the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    role = session['role']
    franchise_id = request.args.get('franchise_id')  # Get franchise_id from query parameter

    conn = get_db_connection()

    # If the user is an owner
    if role == 'owner':
        # If no franchise_id is passed, show a list of franchises to choose from
        if not franchise_id:
            franchises = conn.execute('SELECT * FROM franchises').fetchall()
            conn.close()
            return render_template('inventory.html', role=role, franchises=franchises, franchise_id='all')

        # If a franchise_id is selected, show its inventory
        else:
            items = conn.execute('SELECT * FROM inventory WHERE franchise_id = ?', (franchise_id,)).fetchall()
            conn.close()
            return render_template('inventory.html', role=role, items=items, franchise_id=franchise_id)

    # If the user is a manager, show only their assigned franchise inventory
    if role == 'manager':
        # The manager should have a franchise_id saved in their session
        franchise_id = session.get('franchise_id')
        if not franchise_id:
            conn.close()
            return 'No franchise assigned to this manager'

        items = conn.execute('SELECT * FROM inventory WHERE franchise_id = ?', (franchise_id,)).fetchall()
        conn.close()
        return render_template('inventory.html', role=role, items=items, franchise_id=franchise_id)

    # If the user is neither an owner nor a manager, return unauthorized
    return 'Unauthorized', 403

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    role = session['role']
    user_franchise_id = session.get('franchise_id')

    if request.method == 'POST':
        item = request.form['item']
        quantity = int(request.form['quantity'])
        franchise_id = request.form.get('franchise') or user_franchise_id
        staff_name = session.get('username')

        # Check if item already exists in the franchise's inventory
        existing = conn.execute(
            'SELECT * FROM inventory WHERE item_name = ? AND franchise_id = ?',
            (item, franchise_id)
        ).fetchone()

        if existing:
            # Update existing item
            conn.execute(
                'UPDATE inventory SET quantity = quantity + ? WHERE item_name = ? AND franchise_id = ?',
                (quantity, item, franchise_id)
            )
        else:
            # Insert new item
            conn.execute(
                'INSERT INTO inventory (item_name, quantity, franchise_id) VALUES (?, ?, ?)',
                (item, quantity, franchise_id)
            )

        # Log the addition
        conn.execute(
            '''INSERT INTO logs (staff_name, action, item_name, quantity, franchise_id, action_score)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (staff_name, 'added', item, quantity, franchise_id, 10)
        )

        conn.commit()
        conn.close()
        return redirect(url_for('inventory', franchise_id=franchise_id))

    franchises = []
    if role == 'owner':
        franchises = conn.execute('SELECT * FROM franchises').fetchall()
    elif role == 'manager':
        franchises = conn.execute('SELECT * FROM franchises WHERE id = ?', (user_franchise_id,)).fetchall()

    conn.close()
    return render_template('add_item.html', franchises=franchises)

@app.route('/restock', methods=['GET', 'POST'])
def restock():
    if session.get('role') == 'staff':
        return 'Unauthorized'

    conn = get_db_connection()
    if session.get('role') == 'owner':
        franchises = conn.execute('SELECT * FROM franchises').fetchall()
    else:
        franchises = conn.execute('SELECT * FROM franchises WHERE id = ?', (session['franchise_id'],)).fetchall()

    # Default values for item name and quantity
    item_name = ''
    quantity = 0
    item_id = None

    if request.method == 'POST':
        item = request.form['item']
        quantity = int(request.form['quantity'])
        franchise = request.form['franchise']
        staff = session.get('username')

        # Check if the item already exists in the inventory for the selected franchise
        existing_item = conn.execute('SELECT * FROM inventory WHERE item_name = ? AND franchise_id = ?',
                                     (item, franchise)).fetchone()

        if existing_item:
            # If item exists, update the quantity
            conn.execute('UPDATE inventory SET quantity = quantity + ? WHERE item_name = ? AND franchise_id = ?',
                         (quantity, item, franchise))
        else:
            # If item doesn't exist, insert it into the inventory
            conn.execute('INSERT INTO inventory (item_name, quantity, franchise_id) VALUES (?, ?, ?)',
                         (item, quantity, franchise))

        # Log the restocking action
        conn.execute('INSERT INTO logs (staff_name, action, item_name, quantity, franchise_id, action_score) VALUES (?, ?, ?, ?, ?, ?)',
                     (staff, 'restocked', item, quantity, franchise, 5))

        conn.commit()
        conn.close()
        return redirect(url_for('inventory', franchise_id=franchise))

    # Fetch inventory items for the selected franchise
    inventory_items = []
    if franchises:
        inventory_items = conn.execute('SELECT * FROM inventory WHERE franchise_id = ?', (franchises[0]['id'],)).fetchall()

    conn.close()

    # If an item is selected, pre-fill the form with that item's data (from GET params or selected inventory item)
    item_id = request.args.get('item_id')
    if item_id:
        item = conn.execute('SELECT * FROM inventory WHERE id = ?', (item_id,)).fetchone()
        if item:
            item_name = item['item_name']
            quantity = item['quantity']

    return render_template('restock.html', franchises=franchises, inventory_items=inventory_items, 
                           item_name=item_name, item_id=item_id, quantity=quantity)


@app.route('/checkout/<franchise_id>', methods=['GET', 'POST'])
def checkout(franchise_id):
    if session.get('role') not in ['owner', 'manager']:
        return 'Unauthorized'
    conn = get_db_connection()
    if request.method == 'POST':
        for item in request.form:
            qty = int(request.form[item])
            conn.execute('UPDATE inventory SET quantity = quantity - ? WHERE id = ?', (qty, item))
            conn.execute('INSERT INTO logs (staff_name, action, item_name, quantity, franchise_id, action_score) VALUES (?, ?, ?, ?, ?, ?)',
                         (session['username'], 'checkout', item, qty, franchise_id, 15))
        conn.commit()
        conn.close()
        return redirect(url_for('inventory', franchise_id=franchise_id))
    items = conn.execute('SELECT * FROM inventory WHERE franchise_id = ?', (franchise_id,)).fetchall()
    conn.close()
    return render_template('checkout.html', items=items, franchise_id=franchise_id)


@app.route('/logs', methods=['GET'])
def view_logs():
    conn = get_db_connection()
    role = session['role']
    franchise_id = session.get('franchise_id')
    
    if role == 'owner':
        # Check if a specific franchise is selected, otherwise show all logs
        selected_franchise_id = request.args.get('franchise_id')
        
        if selected_franchise_id:
            # Fetch logs for the selected franchise
            logs = conn.execute(''' 
                SELECT l.id, l.staff_name, l.action, l.item_name, l.quantity, l.timestamp, l.action_score, f.location 
                FROM logs l 
                JOIN franchises f ON l.franchise_id = f.id 
                WHERE l.franchise_id = ? 
                ORDER BY l.timestamp DESC
            ''', (selected_franchise_id,)).fetchall()
            
            franchise_location = conn.execute('SELECT location FROM franchises WHERE id = ?', (selected_franchise_id,)).fetchone()
            conn.close()
            return render_template('logs.html', logs=logs, franchise_location=franchise_location, selected_franchise=True)

        else:
            # Fetch all logs for the owner
            logs = conn.execute(''' 
                SELECT l.id, l.staff_name, l.action, l.item_name, l.quantity, l.timestamp, l.action_score, f.location 
                FROM logs l 
                JOIN franchises f ON l.franchise_id = f.id 
                ORDER BY l.timestamp DESC
            ''').fetchall()
            
            franchises = conn.execute('SELECT id, location FROM franchises').fetchall()
            conn.close()
            return render_template('logs.html', logs=logs, franchises=franchises, selected_franchise=False)

    elif role == 'manager':
        # Fetch logs for the manager's assigned franchise
        logs = conn.execute(''' 
            SELECT l.id, l.staff_name, l.action, l.item_name, l.quantity, l.timestamp, l.action_score, f.location 
            FROM logs l 
            JOIN franchises f ON l.franchise_id = f.id 
            WHERE l.franchise_id = ? 
            ORDER BY l.timestamp DESC
        ''', (franchise_id,)).fetchall()
        conn.close()
        return render_template('logs.html', logs=logs, franchise_id=franchise_id, selected_franchise=True)
    
    return 'Unauthorized', 403


@app.route('/performance')
def performance():
    conn = get_db_connection()
    scores = conn.execute('''
        SELECT staff_name, SUM(action_score) as score 
        FROM logs 
        GROUP BY staff_name 
        ORDER BY score DESC
    ''').fetchall()
    conn.close()
    return render_template('performance.html', scores=scores)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)


