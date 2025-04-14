from flask import Flask, request, render_template, redirect, url_for, send_from_directory
import os
import sqlite3

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# SQLite setup
def init_db():
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS media (id INTEGER PRIMARY KEY, filename TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS assignments (display_id TEXT, media_id INTEGER)''')

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Optional: for dict-like access to rows
    return conn
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        f = request.files['media']
        filepath = os.path.join(UPLOAD_FOLDER, f.filename)
        f.save(filepath)

        with sqlite3.connect("database.db") as conn:
            conn.execute("INSERT INTO media (filename) VALUES (?)", (f.filename,))
        return redirect(url_for('upload'))

    return render_template('upload.html')

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
    with sqlite3.connect("database.db") as conn:
        # Get media
        row = conn.execute("""
            SELECT m.filename FROM assignments a
            JOIN media m ON m.id = a.media_id
            WHERE a.display_id = ?
            ORDER BY a.rowid DESC LIMIT 1
        """, (display_id,)).fetchone()
        media_file = row[0] if row else None

        # Get inventory for this display_id (same as franchise_id)
        inventory = conn.execute("""
            SELECT item_name, quantity FROM inventory WHERE franchise_id = ?
        """, (display_id,)).fetchall()

    return render_template('display.html', filename=media_file, inventory=inventory, franchise_id=display_id)


@app.route('/inventory/<franchise_id>')
def inventory(franchise_id):
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM inventory WHERE franchise_id = ?', (franchise_id,)).fetchall()
    conn.close()
    return render_template('inventory.html', items=items, franchise_id=franchise_id)

# Add new item to inventory
@app.route('/add', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        item = request.form['item']
        quantity = int(request.form['quantity'])
        franchise = request.form['franchise']
        staff = request.form['staff']

        conn = get_db_connection()
        conn.execute('INSERT INTO inventory (item_name, quantity, franchise_id) VALUES (?, ?, ?)',
                     (item, quantity, franchise))
        conn.execute('INSERT INTO logs (staff_name, action, item_name, quantity, franchise_id) VALUES (?, ?, ?, ?, ?)',
                     (staff, 'added', item, quantity, franchise))
        conn.commit()
        conn.close()

        return redirect(url_for('inventory', franchise_id=franchise))
    
    return render_template('add_item.html')

# Restock existing item
@app.route('/restock', methods=['GET', 'POST'])
def restock():
    if request.method == 'POST':
        item = request.form['item']
        quantity = int(request.form['quantity'])
        franchise = request.form['franchise']
        staff = request.form['staff']

        conn = get_db_connection()
        conn.execute('UPDATE inventory SET quantity = quantity + ? WHERE item_name = ? AND franchise_id = ?',
                     (quantity, item, franchise))
        conn.execute('INSERT INTO logs (staff_name, action, item_name, quantity, franchise_id) VALUES (?, ?, ?, ?, ?)',
                     (staff, 'restocked', item, quantity, franchise))
        conn.commit()
        conn.close()

        return redirect(url_for('inventory', franchise_id=franchise))
    
    return render_template('restock.html')

# Staff log view
@app.route('/logs')
def view_logs():
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM logs ORDER BY timestamp DESC').fetchall()
    conn.close()
    return render_template('logs.html', logs=logs)

if __name__ == '__main__':
    app.run(debug=True)


# Start app
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
