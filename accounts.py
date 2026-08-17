from flask import Blueprint, request, jsonify, g

from auth import token_required, generate_ref_id, log_action
from db import get_conn

accounts_bp = Blueprint("accounts", __name__)


def _account_owned_by(cur, account_id, user_id):
    cur.execute("SELECT * FROM accounts WHERE id = %s AND user_id = %s", (account_id, user_id))
    return cur.fetchone()


@accounts_bp.route("/accounts", methods=["GET"])
@token_required()
def list_accounts():
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, account_number, account_type, balance, interest_rate, status, created_at "
            "FROM accounts WHERE user_id = %s ORDER BY created_at",
            (g.user_id,),
        )
        return jsonify(cur.fetchall())
    finally:
        conn.close()


@accounts_bp.route("/accounts/<int:account_id>/transactions", methods=["GET"])
@token_required()
def account_transactions(account_id):
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        acc = _account_owned_by(cur, account_id, g.user_id)
        if not acc and g.role not in ("admin", "teller"):
            return jsonify({"error": "Account not found"}), 404

        cur.execute(
            """SELECT id, ref_id, type, amount, balance_after, note, created_at
               FROM transactions WHERE account_id = %s
               ORDER BY created_at DESC LIMIT 200""",
            (account_id,),
        )
        return jsonify(cur.fetchall())
    finally:
        conn.close()


@accounts_bp.route("/accounts/deposit", methods=["POST"])
@token_required()
def deposit():
    data = request.get_json(force=True) or {}
    account_id = data.get("account_id")
    amount = data.get("amount")

    if not account_id or amount is None or float(amount) <= 0:
        return jsonify({"error": "Enter a valid account and a positive amount"}), 400

    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        conn.start_transaction()

        # Row lock prevents a concurrent transaction on this account mid-update
        cur.execute("SELECT * FROM accounts WHERE id = %s FOR UPDATE", (account_id,))
        acc = cur.fetchone()
        if not acc or acc["user_id"] != g.user_id:
            conn.rollback()
            return jsonify({"error": "Account not found"}), 404
        if acc["status"] != "active":
            conn.rollback()
            return jsonify({"error": "This account is not active"}), 403

        new_balance = float(acc["balance"]) + float(amount)
        cur.execute("UPDATE accounts SET balance = %s WHERE id = %s", (new_balance, account_id))

        ref_id = generate_ref_id()
        cur.execute(
            """INSERT INTO transactions (ref_id, account_id, type, amount, balance_after, note)
               VALUES (%s, %s, 'deposit', %s, %s, %s)""",
            (ref_id, account_id, amount, new_balance, data.get("note", "Cash deposit")),
        )
        log_action(conn, g.user_id, "DEPOSIT", f"account:{account_id}", f"+{amount}")
        conn.commit()
        return jsonify({"ref_id": ref_id, "balance": new_balance}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Deposit failed", "detail": str(e)}), 500
    finally:
        conn.close()


@accounts_bp.route("/accounts/withdraw", methods=["POST"])
@token_required()
def withdraw():
    data = request.get_json(force=True) or {}
    account_id = data.get("account_id")
    amount = data.get("amount")

    if not account_id or amount is None or float(amount) <= 0:
        return jsonify({"error": "Enter a valid account and a positive amount"}), 400

    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        conn.start_transaction()

        cur.execute("SELECT * FROM accounts WHERE id = %s FOR UPDATE", (account_id,))
        acc = cur.fetchone()
        if not acc or acc["user_id"] != g.user_id:
            conn.rollback()
            return jsonify({"error": "Account not found"}), 404
        if acc["status"] != "active":
            conn.rollback()
            return jsonify({"error": "This account is not active"}), 403

        remaining = float(acc["balance"]) - float(amount)
        if remaining < float(acc["min_balance"]):
            conn.rollback()
            return jsonify({
                "error": f"Withdrawal would drop below the required minimum balance of {acc['min_balance']}"
            }), 400

        cur.execute("UPDATE accounts SET balance = %s WHERE id = %s", (remaining, account_id))
        ref_id = generate_ref_id()
        cur.execute(
            """INSERT INTO transactions (ref_id, account_id, type, amount, balance_after, note)
               VALUES (%s, %s, 'withdraw', %s, %s, %s)""",
            (ref_id, account_id, amount, remaining, data.get("note", "Cash withdrawal")),
        )
        log_action(conn, g.user_id, "WITHDRAW", f"account:{account_id}", f"-{amount}")
        conn.commit()
        return jsonify({"ref_id": ref_id, "balance": remaining}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Withdrawal failed", "detail": str(e)}), 500
    finally:
        conn.close()


@accounts_bp.route("/accounts/transfer", methods=["POST"])
@token_required()
def transfer():
    data = request.get_json(force=True) or {}
    from_account_id = data.get("from_account_id")
    to_account_number = (data.get("to_account_number") or "").strip()
    amount = data.get("amount")

    if not from_account_id or not to_account_number or amount is None or float(amount) <= 0:
        return jsonify({"error": "Enter a source account, destination account number, and a positive amount"}), 400

    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        conn.start_transaction()

        # Lock both accounts in a consistent order (by id) to avoid deadlocks
        cur.execute("SELECT * FROM accounts WHERE id = %s FOR UPDATE", (from_account_id,))
        src = cur.fetchone()
        if not src or src["user_id"] != g.user_id:
            conn.rollback()
            return jsonify({"error": "Source account not found"}), 404

        cur.execute("SELECT * FROM accounts WHERE account_number = %s FOR UPDATE", (to_account_number,))
        dst = cur.fetchone()
        if not dst:
            conn.rollback()
            return jsonify({"error": "Destination account number not found"}), 404
        if dst["id"] == src["id"]:
            conn.rollback()
            return jsonify({"error": "Cannot transfer to the same account"}), 400
        if src["status"] != "active" or dst["status"] != "active":
            conn.rollback()
            return jsonify({"error": "One of the accounts is not active"}), 403

        remaining = float(src["balance"]) - float(amount)
        if remaining < float(src["min_balance"]):
            conn.rollback()
            return jsonify({
                "error": f"Transfer would drop below the required minimum balance of {src['min_balance']}"
            }), 400

        new_dst_balance = float(dst["balance"]) + float(amount)

        cur.execute("UPDATE accounts SET balance = %s WHERE id = %s", (remaining, src["id"]))
        cur.execute("UPDATE accounts SET balance = %s WHERE id = %s", (new_dst_balance, dst["id"]))

        ref_out = generate_ref_id()
        ref_in = generate_ref_id()
        note = data.get("note", "Fund transfer")

        cur.execute(
            """INSERT INTO transactions (ref_id, account_id, related_account_id, type, amount, balance_after, note)
               VALUES (%s, %s, %s, 'transfer_out', %s, %s, %s)""",
            (ref_out, src["id"], dst["id"], amount, remaining, note),
        )
        cur.execute(
            """INSERT INTO transactions (ref_id, account_id, related_account_id, type, amount, balance_after, note)
               VALUES (%s, %s, %s, 'transfer_in', %s, %s, %s)""",
            (ref_in, dst["id"], src["id"], amount, new_dst_balance, note),
        )
        log_action(conn, g.user_id, "TRANSFER", f"{src['id']}->{dst['id']}", f"{amount}")
        conn.commit()
        return jsonify({"ref_id": ref_out, "balance": remaining}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Transfer failed", "detail": str(e)}), 500
    finally:
        conn.close()
