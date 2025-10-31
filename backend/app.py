from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from flask_cors import CORS
from db import get_db_connection

# Import blueprints
from routes.products import products_bp
from routes.cart import cart_bp
from routes.auth import auth_bp
from routes.customers import customers_bp
from routes.orders import orders_bp
from routes.payments import payments_bp

# --------------------------------------------------
# Flask App Setup
# --------------------------------------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"
CORS(app)

# --------------------------------------------------
# Register Blueprints (API)
# --------------------------------------------------
app.register_blueprint(products_bp, url_prefix="/api")
app.register_blueprint(cart_bp, url_prefix="/api")
app.register_blueprint(auth_bp, url_prefix="/api")
app.register_blueprint(customers_bp, url_prefix="/api")
app.register_blueprint(orders_bp, url_prefix="/api")
app.register_blueprint(payments_bp, url_prefix="/api")

# --------------------------------------------------
# Frontend Routes (HTML Pages)
# --------------------------------------------------
@app.route("/")
def home():
    """Homepage that lists all products."""
    try:
        client = app.test_client()
        response = client.get("/api/products")
        data = response.get_json() or {}
        products = data.get("products", [])
    except Exception as e:
        products = []
        flash(f"Error loading products: {e}", "danger")

    return render_template("home.html", products=products, user=session.get("user"))


from flask import render_template
from db import get_db_connection

@app.route('/products')
def products_page():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch all products (you can later add filters/search)
        cursor.callproc('show_product_catalog', (None, ''))
        data = []
        for result in cursor.stored_results():
            data.extend(result.fetchall())

        return render_template('products.html', products=data)

    except Exception as e:
        print("Error:", e)
        return render_template('products.html', products=[])

    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    app.run(debug=True)
