import os
import libsql_client

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
try:
    os.makedirs(DB_DIR, exist_ok=True)
except OSError:
    pass
LOCAL_DB_PATH = os.path.join(DB_DIR, "finance.db")

# Read Turso credentials. Fallback to local SQLite file url if not set.
TURSO_DB_URL = os.environ.get("TURSO_DB_URL", f"file:{LOCAL_DB_PATH}")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")

def get_client():
    """Returns a synchronous libsql client connection."""
    return libsql_client.create_client_sync(
        url=TURSO_DB_URL,
        auth_token=TURSO_AUTH_TOKEN
    )

def init_db():
    """Initializes the database schema. Resets tables if user schema changes."""
    client = get_client()
    try:
        # Check if users table is old style or needs reset
        db_needs_reset = False
        try:
            client.execute("SELECT username FROM users LIMIT 1")
        except Exception:
            db_needs_reset = True
            
        if db_needs_reset:
            print("Schema update detected. Resetting database tables on Turso...")
            client.execute("DROP TABLE IF EXISTS emergency_fund;")
            client.execute("DROP TABLE IF EXISTS insurance;")
            client.execute("DROP TABLE IF EXISTS investments;")
            client.execute("DROP TABLE IF EXISTS goals;")
            client.execute("DROP TABLE IF EXISTS budgets;")
            client.execute("DROP TABLE IF EXISTS transactions;")
            client.execute("DROP TABLE IF EXISTS members;")
            client.execute("DROP TABLE IF EXISTS users;")
            
        # 1. users table
        client.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            name TEXT NOT NULL,
            age INTEGER,
            mode TEXT CHECK(mode IN ('Bachelor', 'Family')) NOT NULL,
            monthly_income REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. members table
        client.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            age INTEGER,
            relationship TEXT NOT NULL,
            monthly_income REAL DEFAULT 0.0,
            is_dependent INTEGER DEFAULT 1 CHECK(is_dependent IN (0, 1)),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        # 3. transactions table
        client.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            type TEXT CHECK(type IN ('Income', 'Expense')) NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT,
            FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE
        );
        """)

        # 4. budgets table
        client.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            member_id INTEGER,
            month TEXT NOT NULL,
            category TEXT NOT NULL,
            limit_amount REAL NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE,
            UNIQUE(user_id, member_id, month, category)
        );
        """)

        # 5. goals table
        client.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            member_id INTEGER,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            saved_amount REAL NOT NULL DEFAULT 0.0,
            monthly_contribution REAL NOT NULL DEFAULT 0.0,
            deadline TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE
        );
        """)

        # 6. investments table
        client.execute("""
        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            type TEXT CHECK(type IN ('MF', 'SIP', 'FD', 'PPF', 'Stocks', 'Gold', 'RD')) NOT NULL,
            name TEXT NOT NULL,
            invested_amount REAL NOT NULL,
            current_value REAL NOT NULL,
            start_date TEXT NOT NULL,
            FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE
        );
        """)

        # 7. insurance table
        client.execute("""
        CREATE TABLE IF NOT EXISTS insurance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            type TEXT CHECK(type IN ('Life', 'Health', 'Term', 'Vehicle', 'Home')) NOT NULL,
            provider TEXT NOT NULL,
            premium REAL NOT NULL,
            sum_assured REAL NOT NULL,
            renewal_date TEXT NOT NULL,
            FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE
        );
        """)

        # 8. emergency_fund table
        client.execute("""
        CREATE TABLE IF NOT EXISTS emergency_fund (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            current_amount REAL NOT NULL DEFAULT 0.0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

    except Exception as e:
        print(f"Failed to initialize Turso database: {e}")
        raise e
    finally:
        client.close()

def execute_query(query, params=(), is_select=True):
    """Executes a query on Turso and returns result set as dict rows or last row ID."""
    client = get_client()
    try:
        result = client.execute(query, params)
        if is_select:
            columns = result.columns
            return [dict(zip(columns, row)) for row in result.rows]
        else:
            return result.last_insert_rowid
    except Exception as e:
        print(f"Turso database execution error: {e}")
        raise e
    finally:
        client.close()
