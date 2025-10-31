# routes/customers.py
from flask import Blueprint, jsonify, request
from db import get_db_connection
import mysql.connector

customers_bp = Blueprint("customers", __name__)

def _fetch_proc_results(cursor):
    rows = []
    for result in cursor.stored_results():
        rows.extend(result.fetchall())
    return rows

@customers_bp.route("/customers/<int:cust_id>/addresses", methods=["GET"])
def get_customer_addresses(cust_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Address WHERE CustomerID = %s", (cust_id,))
        data = cursor.fetchall()
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

@customers_bp.route("/customers/addresses/add", methods=["POST"])
def add_customer_address():
    payload = request.get_json()
    cust_id = payload.get("customer_id")
    addr_line = payload.get("address_line_1")
    city = payload.get("city")
    pincode = payload.get("pincode")
    addr_type = payload.get("type", "Home")

    if not all([cust_id, addr_line, city, pincode]):
        return jsonify({"success": False, "error": "customer_id, address_line_1, city, and pincode are required"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO Address (CustomerID, AddressLine1, City, PinCode, AddressType)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (cust_id, addr_line, city, pincode, addr_type))
        conn.commit()
        return jsonify({"success": True, "message": "Address added"}), 201
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

