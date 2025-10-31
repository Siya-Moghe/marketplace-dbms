# routes/payments.py
from flask import Blueprint, jsonify, request
from db import get_db_connection
import mysql.connector

payments_bp = Blueprint("payments", __name__)

def _fetch_proc_results(cursor):
    rows = []
    for result in cursor.stored_results():
        rows.extend(result.fetchall())
    return rows

@payments_bp.route("/payments/make", methods=["POST"])
def make_payment():
    """
    POST /api/payments/make
    JSON body: { "order_id": 101, "method": "Credit Card", "amount": 5898.99 }
    Uses sp_make_payment(order_id, method, amt)
    """
    payload = request.get_json()
    order_id = payload.get("order_id")
    method = payload.get("method")
    amount = payload.get("amount")

    if not all([order_id, method, amount]):
        return jsonify({"success": False, "error": "order_id, method, and amount are required"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.callproc("sp_make_payment", (order_id, method, amount))
        
        for _ in cursor.stored_results(): 
            pass
        
        conn.commit()
        return jsonify({"success": True, "message": "Payment recorded successfully"}), 201

    except mysql.connector.Error as err:
        if conn: conn.rollback()
        return jsonify({"success": False, "error": str(err)}), 400
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@payments_bp.route("/payments/refund", methods=["POST"])
def process_refund():
    """
    POST /api/payments/refund
    JSON body: { "payment_id": 1001 }
    Uses process_refund(payment_id)
    """
    payload = request.get_json()
    payment_id = payload.get("payment_id")

    if not payment_id:
        return jsonify({"success": False, "error": "payment_id is required"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.callproc("process_refund", (payment_id,))
        for _ in cursor.stored_results(): 
            pass
        
        conn.commit()
        return jsonify({"success": True, "message": "Refund processed successfully"}), 200

    except mysql.connector.Error as err:
        if conn: conn.rollback()
        return jsonify({"success": False, "error": str(err)}), 400
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()