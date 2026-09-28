import sqlite3

def init_db():
    conn = sqlite3.connect("lupus_tracker.db")
    with open("database.sql", "r") as f:
        sql_script = f.read()
    conn.executescript(sql_script)
    conn.commit()
    conn.close()