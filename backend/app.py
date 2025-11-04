# backend/app.py
import requests
from flask import (
    Flask, render_template, request, redirect, url_for, session, flash
)
from flask_cors import CORS
from db import get_db_connection

# import your existing backend API blueprints (unchanged)
from routes.products import products_bp
from routes.cart import cart_bp
from routes.auth import auth_bp
from routes.customers import customers_bp
from routes.orders import orders_bp
from routes.payments import payments_bp

app = Flask(__name__)
app.secret_key = "supersecretkey"
CORS(app)

# register API blueprints under /api (these are your existing routes)
app.register_blueprint(products_bp, url_prefix="/api")
app.register_blueprint(cart_bp, url_prefix="/api")
app.register_blueprint(auth_bp, url_prefix="/api")
app.register_blueprint(customers_bp, url_prefix="/api")
app.register_blueprint(orders_bp, url_prefix="/api")
app.register_blueprint(payments_bp, url_prefix="/api")

BASE_API_URL = "http://127.0.0.1:5000/api"  # same server

@app.context_processor
def inject_current_year():
    from datetime import datetime
    return {"current_year": datetime.now().year}


# ---------------- Landing (welcome) ----------------
@app.route("/")
def home():
    # simple landing page: if logged in -> go to products
    if session.get("user"):
        return redirect(url_for("products_page"))

    # show a few featured products (read directly from DB for reliable variant info)
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT p.ProductID, p.Prod_Name, p.Description, v.VariantID, v.Size, v.Color, v.Price, v.Stock
            FROM Product p
            JOIN ProductVariant v ON p.ProductID = v.ProductID
            ORDER BY p.Prod_Name
            LIMIT 3
        """)
        rows = cur.fetchall() or []
        featured = {}
        for r in rows:
            pid = r["ProductID"]
            if pid not in featured:
                featured[pid] = {
                    "ProductID": pid,
                    "Prod_Name": r["Prod_Name"],
                    "Description": r["Description"],
                    "variants": []
                }
            featured[pid]["variants"].append({
                "VariantID": r["VariantID"],
                "Size": r["Size"],
                "Color": r["Color"],
                "Price": float(r["Price"]),
                "Stock": int(r["Stock"])
            })
        featured_products = list(featured.values())
    except Exception as e:
        featured_products = []
        flash(f"Error loading featured products: {e}", "danger")
    finally:
        try:
            cur.close(); conn.close()
        except:
            pass

    return render_template("home.html", featured_products=featured_products)


# ---------------- Products ----------------
@app.route("/products")
def products_page():
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM Product ORDER BY Prod_Name")
        products = cur.fetchall() or []
        cur.execute("SELECT * FROM ProductVariant")
        variants = cur.fetchall() or []
        # attach variants to products (guaranteed VariantID present)
        for p in products:
            p["variants"] = [v for v in variants if v["ProductID"] == p["ProductID"]]
            for v in p["variants"]:
                v["Price"] = float(v["Price"])
                v["Stock"] = int(v["Stock"])
    except Exception as e:
        products = []
        flash(f"Error loading products: {e}", "danger")
    finally:
        try:
            cur.close(); conn.close()
        except:
            pass

    return render_template("products.html", products=products)


# ---------------- Add to cart (frontend form) ----------------
@app.route("/add-to-cart", methods=["POST"])
def add_to_cart_front():
    if not session.get("user"):
        flash("Please login to add items to cart", "warning")
        return redirect(url_for("login_page"))

    cust_id = session["user"].get("CustomerID")
    variant_id = request.form.get("variant_id")
    quantity_raw = request.form.get("quantity", "1")

    try:
        quantity = int(quantity_raw)
        if quantity < 1:
            raise ValueError()
    except Exception:
        flash("Quantity must be a positive integer", "danger")
        return redirect(request.referrer or url_for("products_page"))

    if not variant_id:
        flash("No variant specified", "danger")
        return redirect(request.referrer or url_for("products_page"))

    # quick stock check (DB) to provide helpful message before calling API
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT Stock FROM ProductVariant WHERE VariantID = %s", (variant_id,))
        r = cur.fetchone()
        if not r:
            flash("Invalid product variant", "danger")
            return redirect(request.referrer or url_for("products_page"))
        if int(r["Stock"]) < quantity:
            flash("Insufficient stock for selected quantity", "danger")
            return redirect(request.referrer or url_for("products_page"))
    except Exception as e:
        flash(f"Error checking stock: {e}", "danger")
        return redirect(request.referrer or url_for("products_page"))
    finally:
        try:
            cur.close(); conn.close()
        except:
            pass

    # call API to add to cart (stored proc handles duplicate/atomic increments)
    try:
        payload = {"customer_id": int(cust_id), "variant_id": int(variant_id), "quantity": int(quantity)}
        resp = requests.post(f"{BASE_API_URL}/cart/add", json=payload, timeout=8)
        j = resp.json() if resp.content else {}
        if resp.status_code == 200 and j.get("success"):
            flash("Added to cart", "success")
        else:
            flash(j.get("error") or j.get("message") or "Could not add to cart", "danger")
    except Exception as e:
        flash(f"Error adding to cart: {e}", "danger")

    return redirect(request.referrer or url_for("products_page"))


# ---------------- Cart view (reads DB so VariantID is present) ----------------
@app.route("/cart")
def cart_page():
    if not session.get("user"):
        flash("Please login to view cart", "warning")
        return redirect(url_for("login_page"))

    cust_id = session["user"]["CustomerID"]
    items = []
    total = 0.0

    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT c.VariantID, p.Prod_Name AS ProductName, v.Size, v.Color, c.Quantity, v.Price
            FROM Cart c
            JOIN ProductVariant v ON c.VariantID = v.VariantID
            JOIN Product p ON v.ProductID = p.ProductID
            WHERE c.CustomerID = %s
        """, (cust_id,))
        rows = cur.fetchall() or []
        for r in rows:
            price = float(r.get("Price") or 0)
            qty = int(r.get("Quantity") or 1)
            subtotal = price * qty
            items.append({
                "VariantID": r["VariantID"],
                "ProductName": r["ProductName"],
                "Size": r.get("Size"),
                "Color": r.get("Color"),
                "Price": price,
                "Quantity": qty,
                "Subtotal": subtotal
            })
            total += subtotal
    except Exception as e:
        flash(f"Error loading cart: {e}", "danger")
        items = []
    finally:
        try:
            cur.close(); conn.close()
        except:
            pass

    return render_template("cart.html", cart_items=items, total_price=round(total, 2))


# ---------------- Update cart item ----------------
@app.route("/cart/update", methods=["POST"])
def update_cart():
    if not session.get("user"):
        flash("Please login to update cart", "warning")
        return redirect(url_for("login_page"))

    cust_id = session["user"]["CustomerID"]
    variant_id = request.form.get("variant_id")
    qty_raw = request.form.get("quantity")

    if not variant_id or qty_raw is None:
        flash("Invalid request (missing variant or quantity)", "danger")
        return redirect(url_for("cart_page"))

    try:
        quantity = int(qty_raw)
        if quantity < 0:
            raise ValueError()
    except Exception:
        flash("Quantity must be a non-negative integer", "danger")
        return redirect(url_for("cart_page"))

    # If quantity == 0 -> remove, else call update API
    try:
        if quantity == 0:
            payload = {"customer_id": int(cust_id), "variant_id": int(variant_id)}
            resp = requests.delete(f"{BASE_API_URL}/cart/remove", json=payload, timeout=8)
        else:
            payload = {"customer_id": int(cust_id), "variant_id": int(variant_id), "quantity": int(quantity)}
            resp = requests.put(f"{BASE_API_URL}/cart/update", json=payload, timeout=8)

        j = resp.json() if resp.content else {}
        if resp.status_code in (200, 201) and j.get("success"):
            flash("Cart updated", "success")
        else:
            flash(j.get("error") or j.get("message") or "Failed to update cart", "danger")
    except Exception as e:
        flash(f"Error updating cart: {e}", "danger")

    return redirect(url_for("cart_page"))


# ---------------- Remove from cart ----------------
@app.route("/cart/remove", methods=["POST"])
def remove_from_cart():
    if not session.get("user"):
        flash("Please login to update cart", "warning")
        return redirect(url_for("login_page"))

    cust_id = session["user"]["CustomerID"]
    variant_id = request.form.get("variant_id")

    if not variant_id:
        flash("Invalid request (missing variant ID)", "danger")
        return redirect(url_for("cart_page"))

    try:
        payload = {"customer_id": int(cust_id), "variant_id": int(variant_id)}
        resp = requests.delete(f"{BASE_API_URL}/cart/remove", json=payload, timeout=8)
        j = resp.json() if resp.content else {}
        if resp.status_code == 200 and j.get("success"):
            flash("Item removed from cart", "info")
        else:
            flash(j.get("error") or j.get("message") or "Failed to remove item", "danger")
    except Exception as e:
        flash(f"Error removing item: {e}", "danger")

    return redirect(url_for("cart_page"))



# ---------------- Checkout ----------------
@app.route("/checkout", methods=["GET", "POST"])
def checkout_page():
    if not session.get("user"):
        flash("Please login to checkout", "warning")
        return redirect(url_for("login_page"))

    cust_id = session["user"]["CustomerID"]

    # Fetch cart items and addresses safely
    cart_items, total, addresses = [], 0.0, []
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # Fetch cart items
        cur.execute("""
            SELECT c.VariantID, p.Prod_Name AS ProductName, v.Size, v.Color, c.Quantity, v.Price
            FROM Cart c
            JOIN ProductVariant v ON c.VariantID = v.VariantID
            JOIN Product p ON v.ProductID = p.ProductID
            WHERE c.CustomerID = %s
        """, (cust_id,))
        rows = cur.fetchall() or []
        for r in rows:
            price = float(r.get("Price", 0) or 0)
            qty = int(r.get("Quantity", 1) or 1)
            subtotal = price * qty
            total += subtotal
            cart_items.append({
                "VariantID": r["VariantID"],
                "ProductName": r["ProductName"],
                "Size": r.get("Size"),
                "Color": r.get("Color"),
                "Price": price,
                "Quantity": qty,
                "Subtotal": subtotal
            })

        # Fetch addresses
        resp = requests.get(f"{BASE_API_URL}/customers/{cust_id}/addresses", timeout=6)
        j = resp.json() if resp.content else {}
        addresses = j.get("data", []) if j.get("success", True) else []
    except Exception as e:
        flash(f"Error loading checkout data: {e}", "danger")
    finally:
        try:
            cur.close(); conn.close()
        except:
            pass

    # ---- POST request handling ----
    if request.method == "POST":
        # Case 1: Add address
        if "add_address" in request.form:
            addr_line = request.form.get("address_line_1", "").strip()
            city = request.form.get("city", "").strip()
            pincode = request.form.get("pincode", "").strip()
            addr_type = request.form.get("type", "Home")

            if not all([addr_line, city, pincode]):
                flash("Please fill all address fields", "warning")
                return redirect(url_for("checkout_page"))

            try:
                payload = {
                    "customer_id": int(cust_id),
                    "address_line_1": addr_line,
                    "city": city,
                    "pincode": pincode,
                    "type": addr_type
                }
                resp = requests.post(f"{BASE_API_URL}/customers/addresses/add", json=payload, timeout=8)
                jr = resp.json() if resp.content else {}
                if resp.status_code in (200, 201) and jr.get("success"):
                    flash("Address added successfully", "success")
                else:
                    flash(jr.get("error") or jr.get("message") or "Failed to add address", "danger")
            except Exception as e:
                flash(f"Error adding address: {e}", "danger")

            return redirect(url_for("checkout_page"))

        # Case 2: Place order
        shipping_address_id = request.form.get("shipping_address_id")
        if not shipping_address_id:
            flash("Please select a shipping address", "warning")
            return redirect(url_for("checkout_page"))

        try:
            payload = {
                "customer_id": int(cust_id),
                "shipping_address_id": int(shipping_address_id)
            }
            resp_ord = requests.post(f"{BASE_API_URL}/orders/place", json=payload, timeout=12)
            j_ord = resp_ord.json() if resp_ord.content else {}

            if resp_ord.status_code in (200, 201) and j_ord.get("success"):
                data = j_ord.get("data")
                order_id = None
                # Try extracting order ID cleanly
                if isinstance(data, dict):
                    order_id = data.get("OrderID") or data.get("NewOrderID")
                elif isinstance(data, list) and data:
                    first = data[0]
                    order_id = first.get("OrderID") if isinstance(first, dict) else first
                if not order_id:
                    order_id = 0

                flash("Order placed successfully. Proceed to payment.", "success")
                return redirect(url_for("pay_page", order_id=order_id))
            else:
                flash(j_ord.get("error") or j_ord.get("message") or "Could not place order", "danger")

        except Exception as e:
            flash(f"Error placing order: {e}", "danger")

        return redirect(url_for("checkout_page"))

    # ---- Render page ----
    return render_template(
        "checkout.html",
        cart_items=cart_items,
        total=round(total, 2),
        addresses=addresses
    )






# ---------------- Pay (simulate) ----------------
@app.route("/pay/<order_id>", methods=["GET", "POST"])
def pay_page(order_id):
    if not session.get("user"):
        flash("Please login to pay", "warning")
        return redirect(url_for("login_page"))

    cust_id = session["user"]["CustomerID"]
    order_details = []
    try:
        resp = requests.get(f"{BASE_API_URL}/orders/details/{order_id}", timeout=8)
        j = resp.json() if resp.content else {}
        order_details = j.get("data", []) if j.get("success", True) else []
    except Exception as e:
        flash(f"Error fetching order details: {e}", "danger")
        order_details = []

    amount = 0.0
    for it in order_details:
        try:
            amount += float(it.get("Price", 0)) * int(it.get("Quantity", 0))
        except:
            pass

    if request.method == "POST":
        method = request.form.get("method", "UPI")
        try:
            payload = {"order_id": int(order_id), "method": method, "amount": float(amount)}
            resp = requests.post(f"{BASE_API_URL}/payments/make", json=payload, timeout=8)
            j = resp.json() if resp.content else {}
            if resp.status_code in (200, 201) and j.get("success"):
                flash("Payment recorded. Order processed.", "success")
                return redirect(url_for("orders_history", user_id=cust_id))
            else:
                flash(j.get("error") or j.get("message") or "Payment failed", "danger")
        except Exception as e:
            flash(f"Payment error: {e}", "danger")

    return render_template("pay.html", order_details=order_details, amount=round(amount, 2), order_id=order_id)


# ---------------- Orders ----------------
@app.route("/orders")
def my_orders_redirect():
    if not session.get("user"):
        flash("Please login", "warning")
        return redirect(url_for("login_page"))
    uid = session["user"]["CustomerID"]
    return redirect(url_for("orders_history", user_id=uid))


@app.route("/orders/history/<int:user_id>")
def orders_history(user_id):
    try:
        resp = requests.get(f"{BASE_API_URL}/orders/history/{user_id}", timeout=8)
        j = resp.json() if resp.content else {}
        orders = j.get("data", []) if j.get("success", True) else []
    except Exception as e:
        flash(f"Error fetching orders: {e}", "danger")
        orders = []
    return render_template("orders.html", orders=orders)


# ---------------- Auth ----------------
@app.route("/auth/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            payload = {"email": email, "password": password}
            resp = requests.post(f"{BASE_API_URL}/auth/login", json=payload, timeout=6)
            j = resp.json() if resp.content else {}
            if resp.status_code == 200 and j.get("success"):
                session["user"] = j.get("user") or {}
                flash("Logged in successfully", "success")
                return redirect(url_for("products_page"))
            else:
                flash(j.get("error") or "Invalid credentials", "danger")
        except Exception as e:
            flash(f"Login error: {e}", "danger")
    return render_template("login.html")


@app.route("/auth/register", methods=["GET", "POST"])
def register_page():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")
        try:
            payload = {"name": name, "email": email, "phone": phone, "password": password}
            resp = requests.post(f"{BASE_API_URL}/auth/register", json=payload, timeout=6)
            j = resp.json() if resp.content else {}
            if resp.status_code in (200, 201) and j.get("success"):
                flash("Registration successful — please login", "success")
                return redirect(url_for("login_page"))
            else:
                flash(j.get("error") or j.get("message") or "Registration failed", "danger")
        except Exception as e:
            flash(f"Registration error: {e}", "danger")
    return render_template("register.html")


@app.route("/auth/logout")
def logout_page():
    session.pop("user", None)
    flash("Logged out", "info")
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
