import os
import sqlite3

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
DB_PATH = os.path.join(DB_DIR, "finance.db")

def get_connection():
    """Returns a SQLite connection with foreign keys enabled."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if it doesn't already exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER,
        mode TEXT CHECK(mode IN ('Bachelor', 'Family')) NOT NULL,
        monthly_income REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. members table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        age INTEGER,
        relationship TEXT NOT NULL, -- 'Self', 'Spouse', 'Child', 'Parent'
        monthly_income REAL DEFAULT 0.0,
        is_dependent INTEGER DEFAULT 1 CHECK(is_dependent IN (0, 1)),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # 3. transactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER,
        date TEXT NOT NULL, -- YYYY-MM-DD
        type TEXT CHECK(type IN ('Income', 'Expense')) NOT NULL,
        category TEXT NOT NULL, -- Food, Rent, EMI, Education, Medical, Travel, Entertainment, Utilities, Other
        amount REAL NOT NULL,
        note TEXT,
        FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE
    );
    """)

    # 4. budgets table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER, -- NULL means Family budget (or we can associate with members)
        month TEXT NOT NULL, -- YYYY-MM
        category TEXT NOT NULL,
        limit_amount REAL NOT NULL,
        FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE,
        UNIQUE(member_id, month, category)
    );
    """)

    # 5. goals table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER, -- NULL means Family-level goal
        name TEXT NOT NULL,
        target_amount REAL NOT NULL,
        saved_amount REAL NOT NULL DEFAULT 0.0,
        monthly_contribution REAL NOT NULL DEFAULT 0.0,
        deadline TEXT NOT NULL, -- YYYY-MM-DD
        FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE
    );
    """)

    # 6. investments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS investments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER,
        type TEXT CHECK(type IN ('MF', 'SIP', 'FD', 'PPF', 'Stocks', 'Gold', 'RD')) NOT NULL,
        name TEXT NOT NULL,
        invested_amount REAL NOT NULL,
        current_value REAL NOT NULL,
        start_date TEXT NOT NULL, -- YYYY-MM-DD
        FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE
    );
    """)

    # 7. insurance table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS insurance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER,
        type TEXT CHECK(type IN ('Life', 'Health', 'Term', 'Vehicle', 'Home')) NOT NULL,
        provider TEXT NOT NULL,
        premium REAL NOT NULL,
        sum_assured REAL NOT NULL,
        renewal_date TEXT NOT NULL, -- YYYY-MM-DD
        FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE
    );
    """)

    # 8. emergency_fund table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emergency_fund (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        current_amount REAL NOT NULL DEFAULT 0.0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()

def execute_query(query, params=(), is_select=True):
    """Executes a query and returns the results or commits updates."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if is_select:
            results = [dict(row) for row in cursor.fetchall()]
            return results
        else:
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        raise e
    finally:
        conn.close()
