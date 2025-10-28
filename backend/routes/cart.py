# routes/cart.py
from flask import Blueprint, jsonify, request
from db import get_db_connection
import mysql.connector

cart_bp = Blueprint("cart", __name__)

def _fetch_proc_results(cursor):
    """
    Helper: consume stored_results() and return combined list of dict rows.
    Expects cursor configured with dictionary=True.
    """
    rows = []
    for result in cursor.stored_results():
        rows.extend(result.fetchall())
    return rows

@cart_bp.route("/cart/<int:cust_id>", methods=["GET"])
def get_cart(cust_id):
    """
    GET /api/cart/<cust_id>
    Returns the customer's cart using show_cart(cust_id).
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc("show_cart", (cust_id,))
        data = _fetch_proc_results(cursor)
        return jsonify({"success": True, "data": data}), 200

    except mysql.connector.Error as err:
        # MySQL stored procs may SIGNAL errors; return them
        return jsonify({"success": False, "error": str(err)}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@cart_bp.route("/cart/add", methods=["POST"])
def add_to_cart():
    """
    POST /api/cart/add
    JSON body: { "customer_id": 1, "variant_id": 2, "quantity": 3 }
    Uses sp_add_to_cart(cust_id, variant_id, qty) -> will INSERT or UPDATE Quantity += qty
    """
    payload = request.get_json(force=True, silent=True) or {}
    cust_id = payload.get("customer_id")
    variant_id = payload.get("variant_id")
    qty = payload.get("quantity", 1)

    if not cust_id or not variant_id:
        return jsonify({"success": False, "error": "customer_id and variant_id required"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # call stored procedure that raises SIGNAL on insufficient stock
        cursor.callproc("sp_add_to_cart", (cust_id, variant_id, qty))
        # consume any results (some connectors require this)
        for _ in cursor.stored_results():
            pass
        # return updated cart
        cursor.close()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc("show_cart", (cust_id,))
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


@cart_bp.route("/cart/remove", methods=["DELETE"])
def remove_from_cart():
    """
    DELETE /api/cart/remove?customer_id=1&variant_id=2
    Or JSON body: { "customer_id": 1, "variant_id": 2 }
    Uses sp_remove_from_cart(cust_id, variant_id)
    """
    # accept both query params and JSON body
    cust_id = request.args.get("customer_id", None)
    variant_id = request.args.get("variant_id", None)
    if not cust_id or not variant_id:
        payload = request.get_json(force=True, silent=True) or {}
        cust_id = payload.get("customer_id", cust_id)
        variant_id = payload.get("variant_id", variant_id)

    if not cust_id or not variant_id:
        return jsonify({"success": False, "error": "customer_id and variant_id required"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.callproc("sp_remove_from_cart", (int(cust_id), int(variant_id)))
        for _ in cursor.stored_results():
            pass
        return jsonify({"success": True, "message": "removed from cart"}), 200

    except mysql.connector.Error as err:
        return jsonify({"success": False, "error": str(err)}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@cart_bp.route("/cart/update", methods=["PUT"])
def update_cart_quantity():
    """
    PUT /api/cart/update
    JSON body: { "customer_id": 1, "variant_id": 2, "quantity": 5 }
    Sets the cart quantity to the given absolute quantity by:
      - calling sp_remove_from_cart
      - then calling sp_add_to_cart with new qty (inside a transaction)
    Note: if quantity == 0, item is removed.
    """
    payload = request.get_json(force=True, silent=True) or {}
    cust_id = payload.get("customer_id")
    variant_id = payload.get("variant_id")
    qty = payload.get("quantity")

    if not cust_id or not variant_id or qty is None:
        return jsonify({"success": False, "error": "customer_id, variant_id and quantity required"}), 400

    try:
        qty = int(qty)
    except:
        return jsonify({"success": False, "error": "quantity must be integer"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        # start explicit transaction to keep operations atomic
        conn.start_transaction()
        cursor = conn.cursor()
        # remove any existing entry
        cursor.callproc("sp_remove_from_cart", (cust_id, variant_id))
        for _ in cursor.stored_results():
            pass

        if qty > 0:
            # add with exact qty (sp_add_to_cart increments if exists, but we've removed it above)
            cursor.callproc("sp_add_to_cart", (cust_id, variant_id, qty))
            for _ in cursor.stored_results():
                pass

        conn.commit()

        # fetch and return updated cart
        cursor.close()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc("show_cart", (cust_id,))
        data = _fetch_proc_results(cursor)
        return jsonify({"success": True, "data": data}), 200

    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": str(err)}), 400

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
