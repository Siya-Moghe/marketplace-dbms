# routes/orders.py
from flask import Blueprint, jsonify, request
from db import get_db_connection
import mysql.connector

# Must be initialized to define routes
orders_bp = Blueprint("orders", __name__)

def _fetch_proc_results(cursor):
    rows = []
    for result in cursor.stored_results():
        rows.extend(result.fetchall())
    return rows

@orders_bp.route("/orders/history/<int:cust_id>", methods=["GET"])
def get_order_history(cust_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Assuming 'show_order_history' stored procedure exists
        cursor.callproc("show_order_history", (cust_id,))
        data = _fetch_proc_results(cursor)
        return jsonify({"success": True, "data": data}), 200
    except mysql.connector.Error as err:
        return jsonify({"success": False, "error": str(err)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@orders_bp.route("/orders/details/<int:order_id>", methods=["GET"])
def get_order_details(order_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Assuming 'show_order_details' stored procedure exists
        cursor.callproc("show_order_details", (order_id,))
        data = _fetch_proc_results(cursor)
        return jsonify({"success": True, "data": data}), 200
    except mysql.connector.Error as err:
        return jsonify({"success": False, "error": str(err)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@orders_bp.route("/orders/place", methods=["POST"])
def place_order():
    payload = request.get_json()
    cust_id = payload.get("customer_id")
    addr_id = payload.get("shipping_address_id")

    if not cust_id or not addr_id:
        return jsonify({"success": False, "error": "customer_id and shipping_address_id are required"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Assuming 'sp_place_order' stored procedure exists
        cursor.callproc("sp_place_order", (cust_id, addr_id))
        data = _fetch_proc_results(cursor)
        new_order_id = data[0] if data else None
        conn.commit()
        return jsonify({"success": True, "message": "Order placed successfully", "data": new_order_id}), 201
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

@orders_bp.route("/orders/cancel", methods=["POST"])
def cancel_order():
    payload = request.get_json()
    order_id = payload.get("order_id")

    if not order_id:
        return jsonify({"success": False, "error": "order_id is required"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Assuming 'cancel_order' stored procedure exists
        cursor.callproc("cancel_order", (order_id,))
        for _ in cursor.stored_results():
            pass
        conn.commit()
        return jsonify({"success": True, "message": "Order cancelled"}), 200
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

