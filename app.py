from flask import Flask, request, jsonify
from pydantic import ValidationError
from schemas import CreateOrder
import json
import sqlite3

app = Flask(__name__)

def db_connection():
    conn = None
    try:
        conn = sqlite3.connect("database.sqlite")
        return conn
    except sqlite3.error as e:
        print(e)

@app.route('/')
def hello_world():
    return 'Hello, World! This is Tobi.'

@app.route("/customers", methods=['GET'])
def get_customers():
    try:
        conn = db_connection()
        print("Database connection established.: ", conn)
        cursor = conn.execute("SELECT * FROM customers")
        customers = [
            dict(id=row[0], name=row[1],email=row[2], created_at=row[3])
            for row in cursor.fetchall()
        ]
        if customers is not None:
            return jsonify(customers), 200
        else:
            return jsonify({"message": "We have no customers in the database"}), 404
    except Exception as e:
        return jsonify({"message": "An error occurred while processing the request. "}), 500


@app.route("/products", methods=['GET'])
def get_products():
    try:
        conn = db_connection()
        print("Database connection established.: ", conn)
        cursor = conn.execute("SELECT * FROM products")
        customers = [
            dict(id=row[0], name=row[1],description=row[2], price=row[3], category=row[4],stock=row[5], rating=row[6], image_url=row[7])
            for row in cursor.fetchall()
        ]
        if customers is not None:
            return jsonify(customers), 200
        else:
            return jsonify({"message": "We have no products in the database"}), 404
    except Exception as e:
        return jsonify({"message": "An error occurred while processing the request. "}), 500




@app.route('/orders', methods=['POST'])
def create_order():
    conn = None
    try:
        conn = db_connection()
        cursor = conn.cursor()

        raw_data = request.get_json()

        if not raw_data:
            return jsonify({"message": "JSON body required"}), 400

        # Validate with Pydantic
        try:
            data = CreateOrder(**raw_data).model_dump()
        except ValidationError as e:
            field_name = e.errors()[0]['loc'][0]
            # print("Error validating product data: ", e.__dict__)
            return jsonify({"message": f"Invalid product data for field '{field_name}'"}), 400

        customer_id = data["customer_id"]
        items = data["items"]

        # Check customer exists
        cursor.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
        customer = cursor.fetchone()

        if not customer:
            return jsonify({"message": "Customer not found"}), 404

        total_amount = 0

        # Start Transaction
        conn.execute("BEGIN")

        # Validate products and check stock
        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]

            cursor.execute("SELECT price, stock FROM products WHERE id=?", (product_id,))
            product = cursor.fetchone()

            if not product:
                conn.rollback()
                return jsonify({"message": f"Product {product_id} not found"}), 404

            price = product[0]
            stock = product[1]

            if stock < quantity:
                conn.rollback()
                return jsonify({
                    "message": f"Not enough stock for product {product_id}"
                }), 400

            total_amount += price * quantity

        # Insert order
        cursor.execute(
            "INSERT INTO orders (customer_id, total_amount) VALUES (?, ?)",
            (customer_id, total_amount)
        )

        order_id = cursor.lastrowid

        # Insert order items and Reduce stock
        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]

            cursor.execute("SELECT price, stock FROM products WHERE id=?", (product_id,))
            product = cursor.fetchone()

            price = product[0]
            stock = product[1]

            # Insert into order_items
            cursor.execute("""
                INSERT INTO order_items
                (order_id, product_id, quantity, price_at_purchase)
                VALUES (?, ?, ?, ?)
            """, (order_id, product_id, quantity, price))

            # Reduce stock
            new_stock = stock - quantity
            cursor.execute("""
                UPDATE products SET stock=? WHERE id=?
            """, (new_stock, product_id))

        # Commit everything
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
        return jsonify({"message": "AN ERROR HAS OCCURRED"}), 500

    finally:
        if conn:
            conn.close()

@app.route('/orders', methods=['GET'])
def get_orders():
    try:
        conn = db_connection()
        cursor = conn.cursor()

        # Fetch orders with customer info
        cursor.execute("""
            SELECT 
                orders.id,
                customers.id,
                total_amount,
                orders.created_at,
                name,
                email
            FROM orders 
            INNER JOIN customers ON orders.customer_id = customers.id
            ORDER BY orders.created_at DESC
        """)
        orders_rows = cursor.fetchall()

        orders = []
        for row in orders_rows:
            order_id = row[0]

            # Fetch order items for this order
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
                WHERE order_id = ?
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
        return jsonify({"message": "AN ERROR HAS OCCURRED"}), 500

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
            WHERE orders.id = ?
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
            WHERE order_id = ?
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