import random
import string
from datetime import datetime, timedelta
from functools import wraps

import bcrypt
import jwt
from flask import Blueprint, request, jsonify, g

from config import Config
from db import get_conn

auth_bp = Blueprint("auth", __name__)


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def generate_account_number() -> str:
    # ASB + 10 random digits, e.g. ASB4820193756
    return "ASB" + "".join(random.choices(string.digits, k=10))


def generate_ref_id() -> str:
    return "TXN" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + "".join(
        random.choices(string.digits, k=4)
    )


def make_token(user):
    payload = {
        "sub": user["id"],
        "role": user["role"],
        "email": user["email"],
        "exp": datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")


def token_required(roles=None):
    """Decorator: validates JWT and optionally restricts by role list."""

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
            token = auth_header.split(" ", 1)[1]
            try:
                payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Session expired, please log in again"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid session token"}), 401

            if roles and payload["role"] not in roles:
                return jsonify({"error": "You do not have permission to do that"}), 403

            g.user_id = payload["sub"]
            g.role = payload["role"]
            g.email = payload["email"]
            return f(*args, **kwargs)

        return wrapper

    return decorator


def log_action(conn, actor_id, action, target=None, details=None):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO audit_logs (actor_id, action, target, details) VALUES (%s,%s,%s,%s)",
        (actor_id, action, target, details),
    )
    cur.close()


# ---------------------------------------------------------------
# Routes
# ---------------------------------------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True) or {}
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    password = data.get("password") or ""
    account_type = data.get("account_type", "savings")

    if not full_name or not email or not phone or len(password) < 6:
        return jsonify({"error": "Please fill all fields; password needs 6+ characters"}), 400

    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            return jsonify({"error": "An account with this email already exists"}), 409

        pw_hash = hash_password(password)
        cur.execute(
            """INSERT INTO users (full_name, email, phone, password_hash, role)
               VALUES (%s, %s, %s, %s, 'customer')""",
            (full_name, email, phone, pw_hash),
        )
        user_id = cur.lastrowid

        acc_number = generate_account_number()
        cur.execute(
            """INSERT INTO accounts (account_number, user_id, account_type, balance)
               VALUES (%s, %s, %s, 0.00)""",
            (acc_number, user_id, account_type),
        )

        log_action(conn, user_id, "REGISTER", f"user:{user_id}", f"Opened account {acc_number}")
        conn.commit()

        cur.execute("SELECT id, full_name, email, role FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        token = make_token(user)
        return jsonify({"token": token, "user": user, "account_number": acc_number}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Registration failed", "detail": str(e)}), 500
    finally:
        conn.close()


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        if not user or not check_password(password, user["password_hash"]):
            return jsonify({"error": "Incorrect email or password"}), 401
        if user["status"] != "active":
            return jsonify({"error": f"This account is {user['status']}. Contact support."}), 403

        token = make_token(user)
        log_action(conn, user["id"], "LOGIN", f"user:{user['id']}")
        conn.commit()

        safe_user = {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
        }
        return jsonify({"token": token, "user": safe_user})
    finally:
        conn.close()
