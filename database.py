import sqlite3

DATABASE = "sales.db"


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():

    connection = get_db()
    cursor = connection.cursor()

    # Products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            purchase_price REAL NOT NULL,
            selling_price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            minimum_stock INTEGER NOT NULL
        )
    """)

    # Sales table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            quantity INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            sale_date TEXT NOT NULL
        )
    """)

    # Check existing columns
    columns = cursor.execute(
        "PRAGMA table_info(sales)"
    ).fetchall()

    column_names = [column[1] for column in columns]

    if "purchase_price_at_sale" not in column_names:

        cursor.execute("""
            ALTER TABLE sales
            ADD COLUMN purchase_price_at_sale REAL
        """)

    if "selling_price_at_sale" not in column_names:

        cursor.execute("""
            ALTER TABLE sales
            ADD COLUMN selling_price_at_sale REAL
        """)

    if "profit" not in column_names:

        cursor.execute("""
            ALTER TABLE sales
            ADD COLUMN profit REAL
        """)

    connection.commit()
    connection.close()