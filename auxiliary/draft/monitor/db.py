import sqlite3
import pandas as pd
from datetime import datetime
import os

# Use absolute path to ensure DB is found regardless of where script is run
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "monitor.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stats
                 (timestamp TEXT, cpu REAL, gpu INTEGER, ram REAL, temp REAL,
                  disk_read REAL, disk_write REAL, net_up REAL, net_down REAL)''')
    conn.commit()
    conn.close()

def log_stats(stats):
    """
    Insert a stats dictionary into the database.
    Expects structure from monitor_core.SystemMonitor.get_stats()
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO stats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (datetime.now().isoformat(),
               stats['cpu'], 
               stats['gpu'], 
               stats['ram'], 
               stats['temp'],
               stats['disk']['read_speed'], 
               stats['disk']['write_speed'],
               stats['net']['up_speed'], 
               stats['net']['down_speed']))
    conn.commit()
    conn.close()

def get_history(limit=100):
    """Return the last 'limit' records as a pandas DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    try:
        query = f"SELECT * FROM stats ORDER BY timestamp DESC LIMIT {limit}"
        df = pd.read_sql_query(query, conn)
        
        # Reverse to chronological order for charting
        if not df.empty:
            df = df.iloc[::-1].reset_index(drop=True)
        return df
    finally:
        conn.close()