import sqlite3
from werkzeug.security import generate_password_hash

# Connect to the database
conn = sqlite3.connect('database.db')
c = conn.cursor()

# Insert dummy franchises
franchises = [
    ('F1', 'Location 1'),
    ('F2', 'Location 2'),
    ('F3', 'Location 3')
]
c.executemany('INSERT INTO franchises (id, location) VALUES (?, ?)', franchises)

# Insert dummy users (owner, manager, staff)
users = [
    ('owner1', generate_password_hash('password'), 'owner', 'F1'),
    ('manager1', generate_password_hash('password'), 'manager', 'F1'),
    ('staff1', generate_password_hash('password'), 'staff', 'F1'),
    ('manager2', generate_password_hash('password'), 'manager', 'F2'),
    ('staff2', generate_password_hash('password'), 'staff', 'F2'),
]
c.executemany('INSERT INTO users (username, password_hash, role, franchise_id) VALUES (?, ?, ?, ?)', users)

# Insert dummy inventory items
inventory = [
    ('Item1', 10, 'F1'),
    ('Item2', 3, 'F1'),
    ('Item3', 5, 'F2'),
    ('Item4', 20, 'F2'),
    ('Item5', 0, 'F3'),
]
c.executemany('INSERT INTO inventory (item_name, quantity, franchise_id) VALUES (?, ?, ?)', inventory)

# Insert dummy media files (fixed the issue here, now it is a list of strings)
media = [
    ('media1.jpg',),
    ('media2.jpg',),
    ('media3.jpg',)
]
c.executemany('INSERT INTO media (filename) VALUES (?)', media)

# Insert dummy assignments
assignments = [
    ('display1', 1),
    ('display2', 2),
    ('display3', 3),
]
c.executemany('INSERT INTO assignments (display_id, media_id) VALUES (?, ?)', assignments)

# Insert dummy logs
logs = [
    ('staff1', 'added', 'Item1', 5, 'F1', '2025-04-20 10:00:00', 10),
    ('staff1', 'restocked', 'Item2', 5, 'F1', '2025-04-20 11:00:00', 5),
    ('staff2', 'checkout', 'Item3', 2, 'F2', '2025-04-20 12:00:00', 15),
]
c.executemany('INSERT INTO logs (staff_name, action, item_name, quantity, franchise_id, timestamp, action_score) VALUES (?, ?, ?, ?, ?, ?, ?)', logs)

# Commit and close
conn.commit()
conn.close()

print("Dummy data inserted successfully.")
