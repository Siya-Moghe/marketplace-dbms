from flask import Blueprint, jsonify, request
from db import get_db_connection
import mysql.connector
import bcrypt  

auth_bp = Blueprint("auth", __name__)

# ---------- LOGIN ----------
@auth_bp.route("/auth/login", methods=["POST"])
def login():
    """
    POST /api/auth/login
    JSON body: { "email": "user@example.com", "password": "1234" }
    """
    data = request.get_json(force=True, silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password required"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch stored hash from DB
        cursor.execute("""
            SELECT c.CustomerID, c.Name, c.Email, p.Password AS hashed_pw
            FROM Customer c
            JOIN Password p ON c.CustomerID = p.CustomerID
            WHERE c.Email = %s
        """, (email,))
        user = cursor.fetchone()

        # Compare provided password with stored hash
        if user and bcrypt.checkpw(password.encode('utf-8'), user["hashed_pw"].encode('utf-8')):
            user.pop("hashed_pw")  # remove hash before returning
            return jsonify({"success": True, "user": user}), 200
        else:
            return jsonify({"success": False, "error": "Invalid email or password"}), 401

    except mysql.connector.Error as err:
        return jsonify({"success": False, "error": str(err)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ---------- REGISTER ----------
@auth_bp.route("/auth/register", methods=["POST"])
def register():
    """
    POST /api/auth/register
    JSON body: {
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "9998887777",
      "password": "test123"
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    password = data.get("password")

    if not name or not email or not phone or not password:
        return jsonify({"success": False, "error": "Missing required fields"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Hash the password before saving
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Insert into Customer
        cursor.execute("""
            INSERT INTO Customer (Name, Email, Phone)
            VALUES (%s, %s, %s)
        """, (name, email, phone))
        cust_id = cursor.lastrowid

        # Insert hashed password
        cursor.execute("""
            INSERT INTO Password (CustomerID, Password)
            VALUES (%s, %s)
        """, (cust_id, hashed_pw))

        conn.commit()
        return jsonify({
            "success": True,
            "message": "Registered successfully",
            "customer_id": cust_id
        }), 201

    except mysql.connector.IntegrityError as e:
        if "Email" in str(e):
            return jsonify({"success": False, "error": "Email already exists"}), 400
        elif "Phone" in str(e):
            return jsonify({"success": False, "error": "Phone number already exists"}), 400
        else:
            return jsonify({"success": False, "error": str(e)}), 400

    except mysql.connector.Error as err:
        return jsonify({"success": False, "error": str(err)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ---------- UPDATE PASSWORD ----------
@auth_bp.route("/auth/update-password", methods=["POST"])
def update_password():
    """
    POST /api/auth/update-password
    JSON body: { "email": "...", "old_password": "...", "new_password": "..." }
    """
    data = request.get_json(force=True, silent=True) or {}
    email = data.get("email")
    old_pw = data.get("old_password")
    new_pw = data.get("new_password")

    if not email or not old_pw or not new_pw:
        return jsonify({"success": False, "error": "Missing required fields"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verify old password
        cursor.execute("""
            SELECT c.CustomerID, p.Password AS hashed_pw
            FROM Customer c
            JOIN Password p ON c.CustomerID = p.CustomerID
            WHERE c.Email = %s
        """, (email,))
        record = cursor.fetchone()

        if not record or not bcrypt.checkpw(old_pw.encode('utf-8'), record["hashed_pw"].encode('utf-8')):
            return jsonify({"success": False, "error": "Invalid old password or email"}), 400

        # Hash new password
        new_hashed_pw = bcrypt.hashpw(new_pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Update
        cursor.execute("""
            UPDATE Password
            SET Password = %s
            WHERE CustomerID = %s
        """, (new_hashed_pw, record["CustomerID"]))

        conn.commit()
        return jsonify({"success": True, "message": "Password updated successfully"}), 200

    except mysql.connector.Error as err:
        return jsonify({"success": False, "error": str(err)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
