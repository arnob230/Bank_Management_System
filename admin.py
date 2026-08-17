from flask import Blueprint, request, jsonify, g

from auth import token_required, log_action
from db import get_conn

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin/stats", methods=["GET"])
@token_required(roles=["admin", "teller"])
def stats():
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) AS total_customers FROM users WHERE role='customer'")
        total_customers = cur.fetchone()["total_customers"]

        cur.execute("SELECT COUNT(*) AS total_accounts, COALESCE(SUM(balance),0) AS total_deposits FROM accounts")
        acc_row = cur.fetchone()

        cur.execute(
            "SELECT COUNT(*) AS txns_today FROM transactions WHERE DATE(created_at) = CURDATE()"
        )
        txns_today = cur.fetchone()["txns_today"]

        cur.execute(
            "SELECT COUNT(*) AS pending_loans FROM loans WHERE status='pending'"
        )
        pending_loans = cur.fetchone()["pending_loans"]

        return jsonify({
            "total_customers": total_customers,
            "total_accounts": acc_row["total_accounts"],
            "total_deposits": float(acc_row["total_deposits"]),
            "txns_today": txns_today,
            "pending_loans": pending_loans,
        })
    finally:
        conn.close()


@admin_bp.route("/admin/customers", methods=["GET"])
@token_required(roles=["admin", "teller"])
def customers():
    search = request.args.get("q", "").strip()
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        if search:
            like = f"%{search}%"
            cur.execute(
                """SELECT id, full_name, email, phone, status, created_at
                   FROM users WHERE role='customer'
                   AND (full_name LIKE %s OR email LIKE %s OR phone LIKE %s)
                   ORDER BY created_at DESC LIMIT 100""",
                (like, like, like),
            )
        else:
            cur.execute(
                """SELECT id, full_name, email, phone, status, created_at
                   FROM users WHERE role='customer'
                   ORDER BY created_at DESC LIMIT 100"""
            )
        return jsonify(cur.fetchall())
    finally:
        conn.close()


@admin_bp.route("/admin/customers/<int:user_id>/status", methods=["POST"])
@token_required(roles=["admin"])
def set_customer_status(user_id):
    data = request.get_json(force=True) or {}
    new_status = data.get("status")
    if new_status not in ("active", "frozen", "closed"):
        return jsonify({"error": "Status must be active, frozen, or closed"}), 400

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET status = %s WHERE id = %s", (new_status, user_id))
        log_action(conn, g.user_id, "SET_CUSTOMER_STATUS", f"user:{user_id}", new_status)
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@admin_bp.route("/admin/loans", methods=["GET"])
@token_required(roles=["admin", "teller"])
def list_loans():
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT l.id, l.amount, l.interest_rate, l.term_months, l.monthly_emi,
                      l.status, l.created_at, u.full_name, u.email
               FROM loans l JOIN users u ON u.id = l.user_id
               ORDER BY l.created_at DESC LIMIT 100"""
        )
        return jsonify(cur.fetchall())
    finally:
        conn.close()


@admin_bp.route("/admin/loans/<int:loan_id>/decision", methods=["POST"])
@token_required(roles=["admin"])
def loan_decision(loan_id):
    data = request.get_json(force=True) or {}
    decision = data.get("decision")
    if decision not in ("approved", "rejected"):
        return jsonify({"error": "Decision must be approved or rejected"}), 400

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE loans SET status = %s WHERE id = %s", (decision, loan_id))
        log_action(conn, g.user_id, "LOAN_DECISION", f"loan:{loan_id}", decision)
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()
