import sqlite3

conn = sqlite3.connect("tickets.db")
cursor = conn.cursor()

cursor.execute("SELECT id, username, password, role FROM users")

for row in cursor.fetchall():
    print(row)

conn.close()