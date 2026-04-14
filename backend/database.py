import os
import sqlite3
import hashlib
import secrets
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "antigravity.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT DEFAULT '',
            plan TEXT DEFAULT 'free',
            daily_requests INTEGER DEFAULT 0,
            last_request_date TEXT DEFAULT '',
            token TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan TEXT NOT NULL,
            started_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS build_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            prompt TEXT,
            project_name TEXT,
            project_type TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token() -> str:
    return secrets.token_urlsafe(32)

# ─── User CRUD ──────────────────────────────────────────

def create_user(email: str, password: str, name: str = "") -> dict:
    conn = get_db()
    pw_hash = hash_password(password)
    token = generate_token()
    try:
        conn.execute(
            "INSERT INTO users (email, password_hash, name, token) VALUES (?, ?, ?, ?)",
            (email, pw_hash, name, token)
        )
        conn.commit()
        return {"success": True, "token": token}
    except sqlite3.IntegrityError:
        return {"success": False, "error": "Email already registered."}
    finally:
        conn.close()

def login_user(email: str, password: str) -> dict:
    conn = get_db()
    pw_hash = hash_password(password)
    row = conn.execute(
        "SELECT * FROM users WHERE email = ? AND password_hash = ?",
        (email, pw_hash)
    ).fetchone()
    conn.close()
    if row:
        return {"success": True, "token": row["token"], "plan": row["plan"], "name": row["name"]}
    return {"success": False, "error": "Invalid credentials."}

def get_user_by_token(token: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()
    conn.close()
    return dict(row) if row else None

def check_rate_limit(user: dict) -> bool:
    """Free users: 50 requests/day. Paid users: unlimited."""
    if user["plan"] != "free":
        return True
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if user["last_request_date"] != today:
        # Reset counter for a new day
        conn = get_db()
        conn.execute("UPDATE users SET daily_requests = 0, last_request_date = ? WHERE id = ?", (today, user["id"]))
        conn.commit()
        conn.close()
        return True
    return user["daily_requests"] < 50

def increment_request_count(user_id: int):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    conn = get_db()
    conn.execute(
        "UPDATE users SET daily_requests = daily_requests + 1, last_request_date = ? WHERE id = ?",
        (today, user_id)
    )
    conn.commit()
    conn.close()

def upgrade_plan(user_id: int, plan: str):
    conn = get_db()
    conn.execute("UPDATE users SET plan = ? WHERE id = ?", (plan, user_id))
    conn.execute(
        "INSERT INTO subscriptions (user_id, plan) VALUES (?, ?)",
        (user_id, plan)
    )
    conn.commit()
    conn.close()

# ─── Build Logs ─────────────────────────────────────────

def log_build(user_id: int, prompt: str, project_name: str, project_type: str, status: str = "pending"):
    conn = get_db()
    conn.execute(
        "INSERT INTO build_logs (user_id, prompt, project_name, project_type, status) VALUES (?, ?, ?, ?, ?)",
        (user_id, prompt, project_name, project_type, status)
    )
    conn.commit()
    conn.close()

# ─── Admin Queries ──────────────────────────────────────

def get_all_users():
    conn = get_db()
    rows = conn.execute("SELECT id, email, name, plan, daily_requests, created_at FROM users ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_build_logs():
    conn = get_db()
    rows = conn.execute("SELECT * FROM build_logs ORDER BY id DESC LIMIT 100").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_stats():
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    pro_users = conn.execute("SELECT COUNT(*) FROM users WHERE plan = 'pro'").fetchone()[0]
    total_builds = conn.execute("SELECT COUNT(*) FROM build_logs").fetchone()[0]
    conn.close()
    return {"total_users": total_users, "pro_users": pro_users, "total_builds": total_builds}
