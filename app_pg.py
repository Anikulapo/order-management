from flask import Flask, request, jsonify
from pydantic import ValidationError
from schemas import CreateOrder
from database_conn import get_db_connection_pg

app = Flask(__name__)

def db_connection():
    return get_db_connection_pg()


@app.route('/')
def hello_world():
    return 'Hello, World! This is Tobi (PostgreSQL Version).'


# ========================
# GET CUSTOMERS
# ========================
@app.route("/customers", methods=['GET'])
def get_customers():
    conn = None
    try:
        conn = db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, name, email, created_at FROM customers")
        rows = cursor.fetchall()

        customers = [
            {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "created_at": row[3]
            }
            for row in rows
        ]

        return jsonify(customers), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"message": "An error occurred"}), 500

    finally:
        if conn:
            conn.close()


# ========================
# GET PRODUCTS
# ========================
@app.route("/products", methods=['GET'])
def get_products():
    conn = None
    try:
        conn = db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, description, price, category, stock, rating, image_url
            FROM products
        """)
        rows = cursor.fetchall()

        products = [
            {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "price": row[3],
                "category": row[4],
                "stock": row[5],
                "rating": row[6],
                "image_url": row[7]
            }
            for row in rows
        ]

        return jsonify(products), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"message": "An error occurred"}), 500

    finally:
        if conn:
            conn.close()


# ========================
# CREATE ORDER
# ========================
@app.route('/orders', methods=['POST'])
def create_order():
    conn = None

    try:
        conn = db_connection()
        cursor = conn.cursor()

        raw_data = request.get_json()
        if not raw_data:
            return jsonify({"message": "JSON body required"}), 400

        try:
            data = CreateOrder(**raw_data).model_dump()
        except ValidationError as e:
            field_name = e.errors()[0]['loc'][0]
            return jsonify({"message": f"Invalid data for field '{field_name}'"}), 400

        customer_id = data["customer_id"]
        items = data["items"]

        # Check customer exists
        cursor.execute(
            "SELECT id FROM customers WHERE id = %s",
            (customer_id,)
        )
        if not cursor.fetchone():
            return jsonify({"message": "Customer not found"}), 404

        total_amount = 0

        # Begin transaction
        conn.autocommit = False

        # Validate products
        for item in items:
            cursor.execute(
                "SELECT price, stock FROM products WHERE id = %s",
                (item["product_id"],)
            )
            product = cursor.fetchone()

            if not product:
                conn.rollback()
                return jsonify({"message": f"Product {item['product_id']} not found"}), 404

            price, stock = product

            if stock < item["quantity"]:
                conn.rollback()
                return jsonify({"message": "Not enough stock"}), 400

            total_amount += price * item["quantity"]

        # Insert order
        cursor.execute("""
            INSERT INTO orders (customer_id, total_amount)
            VALUES (%s, %s)
            RETURNING id
        """, (customer_id, total_amount))

        order_id = cursor.fetchone()[0]

        # Insert order items + reduce stock
        for item in items:
            cursor.execute(
                "SELECT price, stock FROM products WHERE id = %s",
                (item["product_id"],)
            )
            price, stock = cursor.fetchone()

            # Insert order item
            cursor.execute("""
                INSERT INTO order_items
                (order_id, product_id, quantity, price_at_purchase)
                VALUES (%s, %s, %s, %s)
            """, (
                order_id,
                item["product_id"],
                item["quantity"],
                price
            ))

            # Reduce stock
            cursor.execute("""
                UPDATE products
                SET stock = %s
                WHERE id = %s
            """, (
                stock - item["quantity"],
                item["product_id"]
            ))

        conn.commit()

        return jsonify({
            "message": "Order created successfully",
            "order_id": order_id,
            "total_amount": total_amount
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        print("Error creating order:", e)
        return jsonify({"message": "An error occurred"}), 500

    finally:
        if conn:
            conn.close()


# ========================
# GET ALL ORDERS
# ========================
@app.route('/orders', methods=['GET'])
def get_orders():
    conn = None
    try:
        conn = db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                o.id,
                c.id,
                o.total_amount,
                o.created_at,
                c.name,
                c.email
            FROM orders o
            INNER JOIN customers c ON o.customer_id = c.id
            ORDER BY o.created_at DESC
        """)

        orders_rows = cursor.fetchall()
        orders = []

        for row in orders_rows:
            order_id = row[0]

            cursor.execute("""
                SELECT 
                    oi.id,
                    p.id,
                    p.name,
                    p.description,
                    p.category,
                    oi.quantity,
                    oi.price_at_purchase
                FROM order_items oi
                INNER JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
            """, (order_id,))

            items_rows = cursor.fetchall()

            items = [
                {
                    "order_item_id": item[0],
                    "product_id": item[1],
                    "product_name": item[2],
                    "description": item[3],
                    "category": item[4],
                    "quantity": item[5],
                    "price_at_purchase": item[6]
                }
                for item in items_rows
            ]

            orders.append({
                "order_id": order_id,
                "customer": {
                    "id": row[1],
                    "name": row[4],
                    "email": row[5]
                },
                "total_amount": row[2],
                "created_at": row[3],
                "items": items
            })
        if len(orders) < 1:
            return jsonify({"message":"There are no current orders"})
        return jsonify(orders), 200


    except Exception as e:
        print("Error fetching orders:", e)
        return jsonify({"message": "An error occurred"}), 500

    finally:
        if conn:
            conn.close()


@app.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    try:
        conn = db_connection()
        cursor = conn.cursor()

        # Fetch order with customer info
        cursor.execute("""
            SELECT 
                orders.id,
                customer_id,
                total_amount,
                orders.created_at,
                name,
                email
            FROM orders 
            INNER JOIN customers ON customer_id = customers.id
            WHERE orders.id = %s
        """, (order_id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({"message": "Order not found"}), 404

        # Fetch order items
        cursor.execute("""
            SELECT 
                order_items.id,
                product_id,
                name,
                description,
                category,
                quantity,
                price_at_purchase
            FROM order_items 
            INNER JOIN products ON product_id = products.id
            WHERE order_id = %s
        """, (order_id,))
        items_rows = cursor.fetchall()

        items = []
        for item in items_rows:
            items.append({
                "order_item_id": item[0],
                "product_id": item[1],
                "product_name": item[2],
                "description": item[3],
                "category": item[4],
                "quantity": item[5],
                "price_at_purchase": item[6]
            })

        order = {
            "order_id": row[0],
            "customer": {
                "id": row[1],
                "name": row[4],
                "email": row[5]
            },
            "total_amount": row[2],
            "created_at": row[3],
            "items": items
        }

        return jsonify(order), 200

    except Exception as e:
        print("Error fetching order:", e)
        return jsonify({"message": "AN ERROR HAS OCCURRED"}), 500

    finally:
        if conn:
            conn.close()



if __name__ == '__main__':
    app.run(debug=True)