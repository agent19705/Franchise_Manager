from flask import Flask, request, render_template, redirect, url_for, session,flash
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
import json
from werkzeug.utils import secure_filename
from datetime import datetime

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
        c.execute('''
    CREATE TABLE IF NOT EXISTS schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        display_id TEXT,
        media_id INTEGER,
        start_time DATETIME,
        end_time DATETIME,
        FOREIGN KEY(display_id) REFERENCES displays(display_id),
        FOREIGN KEY(media_id) REFERENCES media(id)
    )
''')


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
        c.execute('''CREATE TABLE IF NOT EXISTS product_inventory (
    product_id INTEGER,
    item_id INTEGER,
    quantity_needed INTEGER,
    FOREIGN KEY(product_id) REFERENCES inventory(id),
    FOREIGN KEY(item_id) REFERENCES inventory(id)
);
''')
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



from threading import Timer
from datetime import datetime
import sqlite3

def assign_scheduled_media(display_id, filename):
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("INSERT INTO media (filename) VALUES (?)", (filename,))
        media_id = c.lastrowid
        c.execute("INSERT INTO assignments (display_id, media_id) VALUES (?, ?)", (display_id, media_id))
        conn.commit()
        print(f"✅ Scheduled media {filename} assigned to {display_id} at {datetime.now()}")

def schedule_media_switch(display_id, filename, start_time_str):
    try:
        start_time = datetime.fromisoformat(start_time_str)
        delay = (start_time - datetime.now()).total_seconds()
        if delay <= 0:
            assign_scheduled_media(display_id, filename)
        else:
            print(f"⏳ Scheduling media for {display_id} after {delay:.2f} seconds")
            Timer(delay, assign_scheduled_media, args=[display_id, filename]).start()
    except Exception as e:
        print(f"❌ Failed to schedule media: {e}")




# Replace @app.before_first_request with @app.before_request


# The rest of your code follows...




@app.context_processor
def inject_user():
    if 'username' in session:
        return {
            'user': {
                'name': session.get('username'),
                'role': session.get('role'),
                'franchise_id': session.get('franchise_id')
            }
        }
    return {}








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

        if user:
            # Hash the input password using SHA256
            hashed_input_password = hashlib.sha256(password.encode()).hexdigest()

            if user['password_hash'] == hashed_input_password:
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
        # Total branches
        branches = conn.execute('SELECT COUNT(*) FROM franchises').fetchone()[0]

        # Total displays
        displays = conn.execute('SELECT COUNT(*) FROM displays').fetchone()[0]

        # Scheduled content count
        scheduled_content = conn.execute('SELECT COUNT(*) FROM schedule').fetchone()[0]

        # Inventory per branch (for chart)
        inventory_chart = conn.execute('''
            SELECT f.location, SUM(i.quantity) as total_quantity
            FROM inventory i
            JOIN franchises f ON i.franchise_id = f.id
            GROUP BY f.id
        ''').fetchall()

        # Upcoming display changes (next 4 scheduled)
        upcoming_schedule = conn.execute('''
            SELECT s.display_id, s.start_time
            FROM schedule s
            WHERE s.start_time > CURRENT_TIMESTAMP
            ORDER BY s.start_time ASC
            LIMIT 4
        ''').fetchall()

        # Inventory overview
        inventory_status = conn.execute('''
            SELECT f.location, MIN(i.quantity) as lowest_quantity
            FROM franchises f
            JOIN inventory i ON i.franchise_id = f.id
            GROUP BY f.id
            LIMIT 3
        ''').fetchall()

        low_stock_items = [item for item in inventory_status if item[1] < 5]

        return render_template('index.html',
                               role=role,
                               user={'name': session.get('username', 'User'), 'role': role},
                               branches=branches,
                               displays=displays,
                               scheduled_content=scheduled_content,
                               inventory_chart=inventory_chart,
                               upcoming_schedule=upcoming_schedule,
                               inventory_status=inventory_status,
                               low_stock_items=low_stock_items)

    elif role == 'manager':
        franchise = conn.execute('SELECT * FROM franchises WHERE id = ?', (franchise_id,)).fetchone()
        inventory = conn.execute('SELECT item_name, quantity FROM inventory WHERE franchise_id = ?', (franchise_id,)).fetchall()
        logs = conn.execute('SELECT * FROM logs WHERE franchise_id = ? ORDER BY timestamp DESC LIMIT 10', (franchise_id,)).fetchall()
        displays = conn.execute('SELECT COUNT(*) FROM displays WHERE franchise_id = ?', (franchise_id,)).fetchone()[0]

        inventory_chart = [(item['item_name'], item['quantity']) for item in inventory]
        low_stock_items = [item for item in inventory if item['quantity'] < 5]

        return render_template('index.html',
                               role=role,
                               user={'name': session.get('username', 'Manager'), 'role': role},
                               franchise=franchise,
                               inventory_chart=inventory_chart,
                               low_stock_items=low_stock_items,
                               branches=None,
                               displays=displays,
                               scheduled_content=None)

    elif role == 'staff':
        return render_template('staff.html')

    return 'Invalid role'



from flask import session, redirect, url_for

@app.route('/display')
def display():
    # Check if the user is a manager (based on the role in the session)
    if 'role' in session and session['role'] == 'manager':
        # If the role is manager, get the franchise_id from the session
        franchise_id = session.get('franchise_id')
        # Redirect to the select_display route with the manager's franchise_id
        return redirect(url_for('select_display', franchise_id=franchise_id))
    elif 'role' in session and session['role'] == 'manager':
        return 'Unauthorized', 403

    # For non-managers, continue with the normal display logic
    conn = get_db_connection()

    # Fetch the user data
    user_query = "SELECT * FROM users WHERE id = 1"  # Replace with actual user session ID
    user = conn.execute(user_query).fetchone()

    # Fetch all displays from the database
    displays = conn.execute(''' 
    SELECT d.display_id, d.display_name, d.franchise_id, m.filename
    FROM displays d
    LEFT JOIN (
        SELECT a1.display_id, a1.media_id
        FROM assignments a1
        INNER JOIN (
            SELECT display_id, MAX(rowid) as max_id
            FROM assignments
            GROUP BY display_id
        ) latest_assignments
        ON a1.rowid = latest_assignments.max_id
    ) latest_a ON d.display_id = latest_a.display_id
    LEFT JOIN media m ON latest_a.media_id = m.id
    ''').fetchall()

    # Fetch all franchises
    franchises = conn.execute('SELECT id, location FROM franchises').fetchall()

    conn.close()

    # Render the display page with user data and list of displays
    return render_template('display.html', user=user, displays=displays, franchises=franchises)

@app.route('/select_display')
def select_display():
    conn = get_db_connection()

    user = conn.execute("SELECT * FROM users WHERE id = 1").fetchone()
    franchises = conn.execute("SELECT * FROM franchises").fetchall()

    franchise_id = request.args.get('franchise_id')
    selected_franchise = None

    if franchise_id:
        selected_franchise = conn.execute("SELECT * FROM franchises WHERE id = ?", (franchise_id,)).fetchone()
        displays = conn.execute('''
    SELECT d.display_id, d.display_name, d.franchise_id, m.filename
    FROM displays d
    LEFT JOIN (
        SELECT a1.display_id, a1.media_id
        FROM assignments a1
        INNER JOIN (
            SELECT display_id, MAX(rowid) as max_id
            FROM assignments
            GROUP BY display_id
        ) latest_assignments
        ON a1.rowid = latest_assignments.max_id
    ) latest_a ON d.display_id = latest_a.display_id
    LEFT JOIN media m ON latest_a.media_id = m.id
    WHERE d.franchise_id = ?
''', (franchise_id,)).fetchall()

    else:
        displays = conn.execute('''
    SELECT d.display_id, d.display_name, d.franchise_id, m.filename
    FROM displays d
    LEFT JOIN (
        SELECT a1.display_id, a1.media_id
        FROM assignments a1
        INNER JOIN (
            SELECT display_id, MAX(rowid) as max_id
            FROM assignments
            GROUP BY display_id
        ) latest_assignments
        ON a1.rowid = latest_assignments.max_id
    ) latest_a ON d.display_id = latest_a.display_id
    LEFT JOIN media m ON latest_a.media_id = m.id
''').fetchall()


    conn.close()

    return render_template(
        'select_display.html',
        user=user,
        franchises=franchises,
        displays=displays,
        selected_franchise=selected_franchise
    )




from datetime import datetime, timedelta

import json
from datetime import datetime

SCHEDULE_FILE = 'schedules.json'

def load_schedules():
    if not os.path.exists(SCHEDULE_FILE):
        return {}
    with open(SCHEDULE_FILE, 'r') as f:
        return json.load(f)


def save_schedules(schedules):
    with open(SCHEDULE_FILE, 'w') as f:
        json.dump(schedules, f, indent=2)
    print("✅ Schedule saved to JSON.")



@app.route('/assign_upload/<string:display_id>', methods=['GET', 'POST'])
def assign_upload(display_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Get display details
    c.execute("SELECT * FROM displays WHERE display_id = ?", (display_id,))
    display_data = c.fetchone()
    if not display_data:
        flash("Display not found.", "error")
        return redirect(url_for('home'))

    display = {
        'display_id': display_data[0],
        'franchise_id': display_data[1],
        'display_name': display_data[2],
    }

    # Get the latest assigned media for the display
    c.execute('''
        SELECT m.filename 
        FROM assignments a
        JOIN media m ON a.media_id = m.id
        WHERE a.display_id = ?
        ORDER BY a.rowid DESC
        LIMIT 1
    ''', (display_id,))
    media = c.fetchone()
    display['filename'] = media[0] if media else None

    # Handle file upload
    if request.method == 'POST':
        if 'media_file' in request.files:
            file = request.files['media_file']
            if file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join('static/uploads', filename)
                file.save(filepath)

                # Save media only (not assigned yet)
                c.execute("INSERT INTO media (filename) VALUES (?)", (filename,))
                media_id = c.lastrowid
                conn.commit()

                # Optional: Handle schedule time
                start_time = request.form.get("start_time")
                if start_time:
                    try:
                        # Save schedule to JSON
                        schedules = load_schedules()
                        display_schedules = schedules.get(display_id, [])
                        display_schedules.append({
                            "start_time": start_time,
                            "filename": filename
                        })
                        schedules[display_id] = display_schedules
                        save_schedules(schedules)

                        # Schedule actual DB assignment
                        schedule_media_switch(display_id, filename, start_time)
                        flash("Scheduled media successfully.", "success")
                    except Exception as e:
                        flash(f"Error in scheduling: {e}", "danger")
                else:
                    # No schedule provided → assign immediately
                    c.execute("INSERT INTO assignments (display_id, media_id) VALUES (?, ?)", (display_id, media_id))
                    conn.commit()
                    flash('Media uploaded and assigned successfully.', 'success')

                return redirect(url_for('assign_upload', display_id=display_id))
            else:
                flash("No file selected.", "warning")

    conn.close()
    return render_template('assign_upload.html', display=display)












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
def display_sim(display_id):
    now = datetime.now()
    media_file = None

    # 1. Check schedule.json
    schedules = load_schedules()
    display_schedule = schedules.get(display_id, [])

    for entry in sorted(display_schedule, key=lambda x: x['start_time'], reverse=True):
        try:
            start_time = datetime.fromisoformat(entry['start_time'])
            if start_time <= now:
                media_file = entry['filename']
                break
        except Exception as e:
            print(f"❌ Error parsing start_time: {entry['start_time']} - {e}")

    with get_db_connection() as conn:
        # 2. Fallback to latest manually assigned media
        if not media_file:
            row = conn.execute("""
                SELECT m.filename FROM assignments a
                JOIN media m ON m.id = a.media_id
                WHERE a.display_id = ?
                ORDER BY a.rowid DESC
                LIMIT 1
            """, (display_id,)).fetchone()
            media_file = row[0] if row else None

        # 3. Always show inventory
        inventory = conn.execute("""
            SELECT item_name, quantity FROM inventory WHERE franchise_id = ?
        """, (display_id,)).fetchall()

    return render_template('view_display.html', filename=media_file, inventory=inventory, franchise_id=display_id)





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


@app.route('/checkout', methods=['GET'])
def select_franchise_for_checkout():
    if session.get('role') not in ['owner', 'manager']:
        return 'Unauthorized'

    conn = get_db_connection()
    user = session.get('username')
    franchises = conn.execute('SELECT * FROM franchises').fetchall()
    conn.close()
    return render_template('checkout.html', franchises=franchises,user=user)


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Process payment
    if request.method == 'POST':
        cart = request.json.get('cart', [])
        franchise_id = request.json.get('franchise_id')

        for item in cart:
            item_id = item['id']
            qty = item['qty']
            # Deduct inventory only for that franchise
            c.execute("""
                UPDATE inventory
                SET quantity = quantity - ?
                WHERE id = ? AND franchise_id = ? AND quantity >= ?
            """, (qty, item_id, franchise_id, qty))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Payment successful and inventory updated.'})

    # If no franchise selected, show franchise selector
    franchise_id = request.args.get('franchise_id')
    if not franchise_id:
        c.execute("SELECT id, location FROM franchises")
        franchises = c.fetchall()
        conn.close()
        return render_template("select_franchise.html", franchises=franchises)

    # Show inventory for selected franchise
    c.execute("SELECT id, item_name, quantity FROM inventory WHERE franchise_id = ?", (franchise_id,))
    items = c.fetchall()
    conn.close()
    return render_template("checkout.html", items=items, franchise_id=franchise_id)









@app.route('/logs', methods=['GET'])
def view_logs():
    conn = get_db_connection()
    role = session['role']
    franchise_id = session.get('franchise_id')

    # Fetch the user data (you can modify this to match your logged-in user logic)
    user_query = "SELECT * FROM users WHERE id = 1"  # Replace with actual user session ID
    user = conn.execute(user_query).fetchone()  # Fetch the user data
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
            return render_template('logs.html', logs=logs, franchise_location=franchise_location, selected_franchise=True, user=user)

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
            return render_template('logs.html', logs=logs, franchises=franchises, selected_franchise=False,user=user)

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
        return render_template('logs.html', logs=logs, franchise_id=franchise_id, selected_franchise=True, user=user)
    
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
    app.run(debug=True, use_reloader=False)



