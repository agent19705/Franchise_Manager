import sqlite3
from werkzeug.security import generate_password_hash

# Connect to the database
conn = sqlite3.connect('database.db')
c = conn.cursor()

# Password to be used for all users
password = '1234'

# Generate hashed password
hashed_password = generate_password_hash(password)

# Insert dummy users (owner, manager, staff)
users = [
    ('owner1', hashed_password, 'owner', 'F1'),
    ('manager1', hashed_password, 'manager', 'F1'),
    ('staff1', hashed_password, 'staff', 'F1')
]

# Insert users into the database
c.executemany('INSERT INTO users (username, password_hash, role, franchise_id) VALUES (?, ?, ?, ?)', users)

# Commit the transaction and close the connection
conn.commit()
conn.close()

print("Owner, Manager, and Staff with password '1234' added successfully.")
