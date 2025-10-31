from flask import Flask, jsonify
from flask_cors import CORS
from db import get_db_connection

from routes.products import products_bp
from routes.cart import cart_bp
from routes.auth import auth_bp
from routes.customers import customers_bp
from routes.orders import orders_bp
from routes.payments import payments_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(products_bp, url_prefix='/api')
app.register_blueprint(cart_bp, url_prefix="/api")
app.register_blueprint(auth_bp, url_prefix="/api")
app.register_blueprint(customers_bp, url_prefix='/api')
app.register_blueprint(orders_bp, url_prefix='/api')
app.register_blueprint(payments_bp, url_prefix='/api')

@app.route('/')
def home():
    return jsonify({'message': 'Retail marketplace API running'})

@app.route('/api/test')
def test_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        db_name = cursor.fetchone()[0]
        return jsonify({'success': True, 'database': db_name})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
