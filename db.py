import sqlite3

DATABASE_NAME = "database.sqlite"


conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

    # Customers Table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Products Table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        price DECIMAL(10, 2) NOT NULL,
        category TEXT,
        stock INTEGER NOT NULL,
        rating DECIMAL(3, 2) DEFAULT 0.0,
        image_url TEXT
    )
    """)

    # Orders Table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        total_amount DECIMAL(10, 2) NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
    """)

    # Order Items Table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price_at_purchase DECIMAL(10, 2) NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    """)

    # Seed Customers
customers = [
        ("Alice Johnson", "alice@example.com"),
        ("Bob Smith", "bob@example.com"),
        ("Carol Davis", "carol@example.com"),
        ("David Wilson", "david@example.com"),
        ("Eve Martinez", "eve@example.com"),
        ("Frank Brown", "frank@example.com"),
        ("Grace Lee", "grace@example.com"),
        ("Henry Walker", "henry@example.com"),
        ("Isabel Hall", "isabel@example.com"),
        ("Jack Young", "jack@example.com")
    ]
cursor.executemany("INSERT OR IGNORE INTO customers (name, email) VALUES (?, ?)", customers)

    # Seed Products
products = [
        ("Basketball", "Official size basketball", 29.99, "Sports", 50, 4.5, "https://example.com/basketball.jpg"),
        ("Soccer Ball", "FIFA approved soccer ball", 25.50, "Sports", 40, 4.2, "https://example.com/soccerball.jpg"),
        ("Tennis Racket", "Lightweight tennis racket", 79.99, "Sports", 30, 4.7, "https://example.com/tennisracket.jpg"),
        ("Running Shoes", "Comfortable running shoes", 120.00, "Footwear", 20, 4.8, "https://example.com/runningshoes.jpg"),
        ("Yoga Mat", "Non-slip yoga mat", 19.99, "Fitness", 100, 4.3, "https://example.com/yogamat.jpg"),
        ("Dumbbell Set", "Adjustable dumbbells 5-50 lbs", 150.00, "Fitness", 15, 4.6, "https://example.com/dumbbells.jpg"),
        ("Water Bottle", "Insulated 1L bottle", 14.99, "Accessories", 200, 4.1, "https://example.com/waterbottle.jpg"),
        ("Fitness Tracker", "Step and heart rate tracker", 99.99, "Electronics", 25, 4.4, "https://example.com/tracker.jpg"),
        ("Gym Bag", "Durable gym bag", 39.99, "Accessories", 30, 4.5, "https://example.com/gymbag.jpg"),
        ("Jump Rope", "Speed jump rope", 9.99, "Fitness", 150, 4.2, "https://example.com/jumprope.jpg")
    ]
cursor.executemany("""
    INSERT OR IGNORE INTO products (name, description, price, category, stock, rating, image_url)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, products)

    # Save changes
conn.commit()
conn.close()
print("Database initialized and seeded.")