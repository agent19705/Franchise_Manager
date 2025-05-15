import sqlite3
import hashlib
from datetime import datetime, timedelta

def insert_dummy_data():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Clear existing data
    c.execute("DELETE FROM users")
    c.execute("DELETE FROM franchises")
    c.execute("DELETE FROM displays")
    c.execute("DELETE FROM inventory")
    c.execute("DELETE FROM schedule")
    c.execute("DELETE FROM logs")
    c.execute("DELETE FROM media")
    c.execute("DELETE FROM assignments")

    # Insert franchises
    franchises = [
        ('F001', 'Pune'),
        ('F002', 'Mumbai'),
        ('F003', 'Surat'),
        ('F004', 'Vapi')
    ]
    c.executemany("INSERT INTO franchises (id, location) VALUES (?, ?)", franchises)

    # Insert displays
    displays = [
        ('D001', 'F001', 'Display 1'),
        ('D002', 'F001', 'Display 2'),
        ('D003', 'F002', 'Display 3'),
        ('D004', 'F002', 'Display 4'),
        ('D005', 'F003', 'Display 5'),
        ('D006', 'F003', 'Display 6'),
        ('D007', 'F004', 'Display 7'),
        ('D008', 'F004', 'Display 8')
    ]
    c.executemany("INSERT INTO displays (display_id, franchise_id, display_name) VALUES (?, ?, ?)", displays)

    # Insert inventory (food raw materials for each franchise)
    inventory = [
        # Franchise F001 - Pune
        ('Rice', 200, 'F001'),
        ('Wheat Flour', 150, 'F001'),
        ('Sugar', 100, 'F001'),
        ('Salt', 50, 'F001'),
        ('Cooking Oil', 75, 'F001'),
        ('Tomatoes', 40, 'F001'),
        ('Onions', 30, 'F001'),
        ('Garlic', 25, 'F001'),
        ('Ginger', 20, 'F001'),
        ('Spices', 150, 'F001'),

        # Franchise F002 - Mumbai
        ('Rice', 180, 'F002'),
        ('Wheat Flour', 140, 'F002'),
        ('Sugar', 90, 'F002'),
        ('Salt', 45, 'F002'),
        ('Cooking Oil', 65, 'F002'),
        ('Tomatoes', 38, 'F002'),
        ('Onions', 28, 'F002'),
        ('Garlic', 22, 'F002'),
        ('Ginger', 18, 'F002'),
        ('Spices', 130, 'F002'),

        # Franchise F003 - Surat
        ('Rice', 220, 'F003'),
        ('Wheat Flour', 170, 'F003'),
        ('Sugar', 110, 'F003'),
        ('Salt', 55, 'F003'),
        ('Cooking Oil', 80, 'F003'),
        ('Tomatoes', 45, 'F003'),
        ('Onions', 35, 'F003'),
        ('Garlic', 28, 'F003'),
        ('Ginger', 24, 'F003'),
        ('Spices', 160, 'F003'),

        # Franchise F004 - Vapi
        ('Rice', 210, 'F004'),
        ('Wheat Flour', 160, 'F004'),
        ('Sugar', 95, 'F004'),
        ('Salt', 48, 'F004'),
        ('Cooking Oil', 70, 'F004'),
        ('Tomatoes', 42, 'F004'),
        ('Onions', 32, 'F004'),
        ('Garlic', 26, 'F004'),
        ('Ginger', 21, 'F004'),
        ('Spices', 140, 'F004')
    ]
    c.executemany("INSERT INTO inventory (item_name, quantity, franchise_id) VALUES (?, ?, ?)", inventory)

    # Insert logs (10 per location)
    logs = [
        # Logs for Pune (F001)
        ('Alice', 'Added', 'Rice', 20, 'F001'),
        ('Bob', 'Removed', 'Wheat Flour', 5, 'F001'),
        ('Charlie', 'Updated', 'Sugar', 10, 'F001'),
        ('David', 'Added', 'Salt', 15, 'F001'),
        ('Eve', 'Removed', 'Cooking Oil', 10, 'F001'),
        ('Frank', 'Added', 'Tomatoes', 10, 'F001'),
        ('Grace', 'Updated', 'Onions', 5, 'F001'),
        ('Hannah', 'Added', 'Garlic', 5, 'F001'),
        ('Ian', 'Removed', 'Ginger', 2, 'F001'),
        ('Jack', 'Updated', 'Spices', 20, 'F001'),

        # Logs for Mumbai (F002)
        ('Alice', 'Added', 'Rice', 15, 'F002'),
        ('Bob', 'Removed', 'Wheat Flour', 3, 'F002'),
        ('Charlie', 'Updated', 'Sugar', 5, 'F002'),
        ('David', 'Added', 'Salt', 12, 'F002'),
        ('Eve', 'Removed', 'Cooking Oil', 7, 'F002'),
        ('Frank', 'Added', 'Tomatoes', 8, 'F002'),
        ('Grace', 'Updated', 'Onions', 4, 'F002'),
        ('Hannah', 'Added', 'Garlic', 3, 'F002'),
        ('Ian', 'Removed', 'Ginger', 1, 'F002'),
        ('Jack', 'Updated', 'Spices', 15, 'F002'),

        # Logs for Surat (F003)
        ('Alice', 'Added', 'Rice', 25, 'F003'),
        ('Bob', 'Removed', 'Wheat Flour', 4, 'F003'),
        ('Charlie', 'Updated', 'Sugar', 12, 'F003'),
        ('David', 'Added', 'Salt', 18, 'F003'),
        ('Eve', 'Removed', 'Cooking Oil', 8, 'F003'),
        ('Frank', 'Added', 'Tomatoes', 12, 'F003'),
        ('Grace', 'Updated', 'Onions', 6, 'F003'),
        ('Hannah', 'Added', 'Garlic', 7, 'F003'),
        ('Ian', 'Removed', 'Ginger', 3, 'F003'),
        ('Jack', 'Updated', 'Spices', 25, 'F003'),

        # Logs for Vapi (F004)
        ('Alice', 'Added', 'Rice', 18, 'F004'),
        ('Bob', 'Removed', 'Wheat Flour', 2, 'F004'),
        ('Charlie', 'Updated', 'Sugar', 8, 'F004'),
        ('David', 'Added', 'Salt', 10, 'F004'),
        ('Eve', 'Removed', 'Cooking Oil', 5, 'F004'),
        ('Frank', 'Added', 'Tomatoes', 7, 'F004'),
        ('Grace', 'Updated', 'Onions', 3, 'F004'),
        ('Hannah', 'Added', 'Garlic', 4, 'F004'),
        ('Ian', 'Removed', 'Ginger', 1, 'F004'),
        ('Jack', 'Updated', 'Spices', 18, 'F004')
    ]
    for log in logs:
        c.execute('''INSERT INTO logs (staff_name, action, item_name, quantity, franchise_id)
                     VALUES (?, ?, ?, ?, ?)''', log)

    # Insert users
    def hash_pw(password):
        return hashlib.sha256(password.encode()).hexdigest()

    users = [
        ('admin', hash_pw('admin123'), 'owner', None),
        ('manager1', hash_pw('manager123'), 'manager', 'F001'),
        ('manager2', hash_pw('manager123'), 'manager', 'F002'),
        ('manager3', hash_pw('manager123'), 'manager', 'F003'),
        ('manager4', hash_pw('manager123'), 'manager', 'F004'),
        ('staff1', hash_pw('staff123'), 'staff', 'F001'),
        ('staff2', hash_pw('staff123'), 'staff', 'F002'),
        ('staff3', hash_pw('staff123'), 'staff', 'F003'),
        ('staff4', hash_pw('staff123'), 'staff', 'F004')
    ]
    c.executemany("INSERT INTO users (username, password_hash, role, franchise_id) VALUES (?, ?, ?, ?)", users)

    conn.commit()
    conn.close()
    print("Dummy data inserted successfully.")

if __name__ == "__main__":
    insert_dummy_data()
