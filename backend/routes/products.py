from flask import Blueprint, jsonify, request
from db import get_db_connection

products_bp = Blueprint('products', __name__)

@products_bp.route('/products', methods=['GET'])
def get_products():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        category_id = request.args.get('category_id', None)
        search_kw = request.args.get('search', '')

        if category_id:
            cursor.callproc('show_product_catalog', (category_id, search_kw))
        else:
            cursor.callproc('show_product_catalog', (None, search_kw))

        # Stored procedures return results through cursor.stored_results()
        data = []
        for result in cursor.stored_results():
            data.extend(result.fetchall())

        return jsonify({'success': True, 'data': data})

    except Exception as e:
        print("Error:", e)
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()



@products_bp.route('/products/<int:variant_id>', methods=['GET'])
def get_product_details(variant_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Columns match your schema exactly
        cursor.execute("""
            SELECT p.Prod_Name AS ProductName,
                   CONCAT(v.Size, '/', v.Color) AS Variant,
                   v.Price,
                   v.Stock
            FROM ProductVariant v
            JOIN Product p ON p.ProductID = v.ProductID
            WHERE v.VariantID = %s
        """, (variant_id,))
        product = cursor.fetchone()

        if not product:
            return jsonify({'success': False, 'message': 'Product not found'}), 404

        # Reviews fetched using your stored procedure
        cursor.callproc('show_product_reviews', (variant_id,))
        reviews = []
        for result in cursor.stored_results():
            reviews.extend(result.fetchall())

        return jsonify({
            'success': True,
            'product': product,
            'reviews': reviews
        })

    except Exception as e:
        print("Error:", e)
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()