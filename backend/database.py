import os
import json
import base64
import urllib.request
import urllib.error
import sqlite3

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
try:
    os.makedirs(DB_DIR, exist_ok=True)
except OSError:
    pass
LOCAL_DB_PATH = os.path.join(DB_DIR, "finance.db")

# Read Turso credentials. Fallback to local SQLite file url if not set.
TURSO_DB_URL = os.environ.get("TURSO_DB_URL", "")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")

# Determine if we should connect to Turso cloud or local SQLite
IS_TURSO = bool(TURSO_DB_URL and (TURSO_DB_URL.startswith("libsql://") or TURSO_DB_URL.startswith("https://")))

def execute_sqlite_local(query, params=(), is_select=True):
    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if is_select:
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        else:
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"Local SQLite error: {e}")
        raise e
    finally:
        conn.close()

def execute_turso_http(query, params=(), is_select=True):
    url = TURSO_DB_URL
    if url.startswith("libsql://"):
        url = "https://" + url[9:]
        
    endpoint = f"{url.rstrip('/')}/v2/pipeline"
    
    args = []
    for param in params:
        if param is None:
            args.append({"type": "null"})
        elif isinstance(param, int):
            args.append({"type": "integer", "value": str(param)})
        elif isinstance(param, float):
            args.append({"type": "float", "value": param})
        elif isinstance(param, str):
            args.append({"type": "text", "value": param})
        elif isinstance(param, bytes):
            args.append({"type": "blob", "value": base64.b64encode(param).decode('utf-8')})
        else:
            args.append({"type": "text", "value": str(param)})
            
    req_body = {
        "requests": [
            {
                "type": "execute",
                "stmt": {
                    "sql": query,
                    "args": args
                }
            },
            {
                "type": "close"
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TURSO_AUTH_TOKEN}"
    }
    
    data = json.dumps(req_body).encode("utf-8")
    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            results = res_body.get("results", [])
            if not results:
                raise Exception("Empty response from database")
                
            first_res = results[0]
            if first_res.get("type") == "error":
                raise Exception(first_res.get("error", {}).get("message", "Database query execution error"))
                
            execute_result = first_res.get("response", {}).get("result", {})
            
            if is_select:
                cols = [c["name"] for c in execute_result.get("cols", [])]
                rows = []
                for row_vals in execute_result.get("rows", []):
                    row_dict = {}
                    for col_name, val_obj in zip(cols, row_vals):
                        val_type = val_obj.get("type")
                        val_raw = val_obj.get("value")
                        if val_type == "null":
                            row_dict[col_name] = None
                        elif val_type == "integer":
                            row_dict[col_name] = int(val_raw)
                        elif val_type == "float":
                            row_dict[col_name] = float(val_raw)
                        elif val_type == "text":
                            row_dict[col_name] = val_raw
                        elif val_type == "blob":
                            row_dict[col_name] = base64.b64decode(val_raw)
                        else:
                            row_dict[col_name] = val_raw
                    rows.append(row_dict)
                return rows
            else:
                last_rowid = execute_result.get("last_insert_rowid")
                if last_rowid is not None:
                    return int(last_rowid)
                return 0
                
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"HTTP Error executing query on Turso: {e.code} - {err_msg}")
        raise e
    except Exception as e:
        print(f"Error executing query on Turso: {e}")
        raise e

def execute_query(query, params=(), is_select=True):
    if IS_TURSO:
        return execute_turso_http(query, params, is_select)
    else:
        return execute_sqlite_local(query, params, is_select)

def init_db():
    db_needs_reset = False
    try:
        execute_query("SELECT username FROM users LIMIT 1", is_select=True)
    except Exception:
        db_needs_reset = True
        
    if db_needs_reset:
        print("Schema update detected. Resetting database tables...")
        statements = [
            "DROP TABLE IF EXISTS emergency_fund;",
            "DROP TABLE IF EXISTS insurance;",
            "DROP TABLE IF EXISTS investments;",
            "DROP TABLE IF EXISTS goals;",
            "DROP TABLE IF EXISTS budgets;",
            "DROP TABLE IF EXISTS transactions;",
            "DROP TABLE IF EXISTS members;",
            "DROP TABLE IF EXISTS users;"
        ]
        for stmt in statements:
            try:
                execute_query(stmt, is_select=False)
            except Exception:
                pass
                
    # 1. users table
    execute_query("""
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
    """, is_select=False)
    
    # 2. members table
    execute_query("""
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
    """, is_select=False)

    # 3. transactions table
    execute_query("""
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
    """, is_select=False)

    # 4. budgets table
    execute_query("""
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
    """, is_select=False)

    # 5. goals table
    execute_query("""
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
    """, is_select=False)

    # 6. investments table
    execute_query("""
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
    """, is_select=False)

    # 7. insurance table
    execute_query("""
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
    """, is_select=False)

    # 8. emergency_fund table
    execute_query("""
    CREATE TABLE IF NOT EXISTS emergency_fund (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        current_amount REAL NOT NULL DEFAULT 0.0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """, is_select=False)
