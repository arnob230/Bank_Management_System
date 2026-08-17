from flask import Blueprint, request, jsonify, g

from auth import token_required, log_action
from db import get_conn

loans_bp = Blueprint("loans", __name__)


def calculate_emi(principal: float, annual_rate: float, months: int) -> float:
    """Standard reducing-balance EMI formula."""
    monthly_rate = annual_rate / 12 / 100
    if monthly_rate == 0:
        return round(principal / months, 2)
    emi = principal * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)
    return round(emi, 2)


@loans_bp.route("/loans/apply", methods=["POST"])
@token_required()
def apply_loan():
    data = request.get_json(force=True) or {}
    amount = data.get("amount")
    term_months = data.get("term_months")
    interest_rate = data.get("interest_rate", 9.00)

    if not amount or float(amount) <= 0 or not term_months or int(term_months) <= 0:
        return jsonify({"error": "Enter a valid loan amount and term"}), 400

    emi = calculate_emi(float(amount), float(interest_rate), int(term_months))

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO loans (user_id, amount, interest_rate, term_months, monthly_emi, status)
               VALUES (%s, %s, %s, %s, %s, 'pending')""",
            (g.user_id, amount, interest_rate, term_months, emi),
        )
        loan_id = cur.lastrowid
        log_action(conn, g.user_id, "LOAN_APPLY", f"loan:{loan_id}", f"{amount} over {term_months}mo")
        conn.commit()
        return jsonify({"loan_id": loan_id, "monthly_emi": emi}), 201
    finally:
        conn.close()


@loans_bp.route("/loans/mine", methods=["GET"])
@token_required()
def my_loans():
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT id, amount, interest_rate, term_months, monthly_emi, status, created_at
               FROM loans WHERE user_id = %s ORDER BY created_at DESC""",
            (g.user_id,),
        )
        return jsonify(cur.fetchall())
    finally:
        conn.close()


@loans_bp.route("/loans/calculate", methods=["GET"])
def calculate():
    """Public EMI calculator preview — no auth needed."""
    try:
        amount = float(request.args.get("amount", 0))
        rate = float(request.args.get("rate", 9.0))
        months = int(request.args.get("months", 12))
        return jsonify({"monthly_emi": calculate_emi(amount, rate, months)})
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid parameters"}), 400
