import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Create inventory table
cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    franchise_id TEXT NOT NULL
);
""")

# Create logs table
cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_name TEXT NOT NULL,
    action TEXT NOT NULL,
    item_name TEXT NOT NULL,
    quantity INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    franchise_id TEXT NOT NULL
);
""")

conn.commit()
conn.close()
print("Database setup complete.")
