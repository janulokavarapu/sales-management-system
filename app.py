from flask import Flask, render_template, request, redirect, session
from database import create_database, get_db
from datetime import datetime

app = Flask(__name__)

app.secret_key = "sales_management_secret_key"


# =========================
# LOGIN PROTECTION
# =========================
@app.before_request
def require_login():

    if request.path == "/login":
        return

    if request.path.startswith("/static/"):
        return

    if "logged_in" not in session:
        return redirect("/login")


# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            session["logged_in"] = True

            return redirect("/")

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template("login.html")


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =========================
# DASHBOARD
# =========================
@app.route("/")
def home():

    connection = get_db()

    # TOTAL PRODUCTS
    total_products = connection.execute(
        """
        SELECT COUNT(*)
        FROM products
        """
    ).fetchone()[0]

    # CURRENT STOCK
    total_stock = connection.execute(
        """
        SELECT COALESCE(SUM(quantity), 0)
        FROM products
        """
    ).fetchone()[0]

    # TODAY'S SALES
    today_sales = connection.execute(
        """
        SELECT COALESCE(SUM(total_amount), 0)
        FROM sales
        WHERE DATE(sale_date) = DATE('now')
        """
    ).fetchone()[0]

    # PRODUCTS SOLD TODAY
    products_sold_today = connection.execute(
        """
        SELECT COALESCE(SUM(quantity), 0)
        FROM sales
        WHERE DATE(sale_date) = DATE('now')
        """
    ).fetchone()[0]

    # TOTAL PROFIT
    total_profit = connection.execute(
        """
        SELECT COALESCE(SUM(profit), 0)
        FROM sales
        """
    ).fetchone()[0]

    # LOW STOCK PRODUCTS
    low_stock_products = connection.execute(
        """
        SELECT *
        FROM products
        WHERE quantity <= minimum_stock
        """
    ).fetchall()

    # DAILY SALES DATA
    daily_data_rows = connection.execute(
        """
        SELECT
            DATE(sale_date) AS sale_day,
            COALESCE(SUM(total_amount), 0) AS sales
        FROM sales
        GROUP BY DATE(sale_date)
        ORDER BY sale_day
        """
    ).fetchall()

    daily_data = []

    for row in daily_data_rows:

        daily_data.append({
            "sale_day": row["sale_day"],
            "sales": row["sales"]
        })

    connection.close()

    return render_template(
        "dashboard.html",
        total_products=total_products,
        total_stock=total_stock,
        today_sales=today_sales,
        products_sold_today=products_sold_today,
        total_profit=total_profit,
        low_stock_products=low_stock_products,
        daily_data=daily_data
    )


# =========================
# PRODUCTS + SEARCH
# =========================
@app.route("/products")
def products():

    search = request.args.get("search", "")

    connection = get_db()

    if search:

        products = connection.execute(
            """
            SELECT *
            FROM products
            WHERE name LIKE ?
               OR category LIKE ?
            ORDER BY id DESC
            """,
            (
                "%" + search + "%",
                "%" + search + "%"
            )
        ).fetchall()

    else:

        products = connection.execute(
            """
            SELECT *
            FROM products
            ORDER BY id DESC
            """
        ).fetchall()

    connection.close()

    return render_template(
        "products.html",
        products=products,
        search=search
    )


# =========================
# ADD PRODUCT
# =========================
@app.route("/add-product", methods=["GET", "POST"])
def add_product():

    if request.method == "POST":

        name = request.form["name"]
        category = request.form["category"]
        purchase_price = request.form["purchase_price"]
        selling_price = request.form["selling_price"]
        quantity = request.form["quantity"]
        minimum_stock = request.form["minimum_stock"]

        connection = get_db()

        connection.execute(
            """
            INSERT INTO products
            (
                name,
                category,
                purchase_price,
                selling_price,
                quantity,
                minimum_stock
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                category,
                purchase_price,
                selling_price,
                quantity,
                minimum_stock
            )
        )

        connection.commit()
        connection.close()

        return redirect("/products")

    return render_template("add_product.html")


# =========================
# EDIT PRODUCT
# =========================
@app.route("/edit-product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):

    connection = get_db()

    product = connection.execute(
        """
        SELECT *
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    ).fetchone()

    if request.method == "POST":

        name = request.form["name"]
        category = request.form["category"]
        purchase_price = request.form["purchase_price"]
        selling_price = request.form["selling_price"]
        quantity = request.form["quantity"]
        minimum_stock = request.form["minimum_stock"]

        connection.execute(
            """
            UPDATE products
            SET
                name = ?,
                category = ?,
                purchase_price = ?,
                selling_price = ?,
                quantity = ?,
                minimum_stock = ?
            WHERE id = ?
            """,
            (
                name,
                category,
                purchase_price,
                selling_price,
                quantity,
                minimum_stock,
                product_id
            )
        )

        connection.commit()
        connection.close()

        return redirect("/products")

    connection.close()

    return render_template(
        "edit_product.html",
        product=product
    )


# =========================
# DELETE PRODUCT
# =========================
@app.route("/delete-product/<int:product_id>")
def delete_product(product_id):

    connection = get_db()

    connection.execute(
        """
        DELETE FROM products
        WHERE id = ?
        """,
        (product_id,)
    )

    connection.commit()
    connection.close()

    return redirect("/products")


# =========================
# SALES
# =========================
@app.route("/sales", methods=["GET", "POST"])
def sales():

    connection = get_db()

    if request.method == "POST":

        product_id = request.form["product_id"]
        quantity = int(request.form["quantity"])

        product = connection.execute(
            """
            SELECT *
            FROM products
            WHERE id = ?
            """,
            (product_id,)
        ).fetchone()

        if product and quantity > 0 and quantity <= product["quantity"]:

            purchase_price = product["purchase_price"]
            selling_price = product["selling_price"]

            total_amount = selling_price * quantity

            profit = (
                selling_price - purchase_price
            ) * quantity

            connection.execute(
                """
                INSERT INTO sales
                (
                    product_id,
                    quantity,
                    total_amount,
                    sale_date,
                    purchase_price_at_sale,
                    selling_price_at_sale,
                    profit
                )
                VALUES (?, ?, ?, datetime('now'), ?, ?, ?)
                """,
                (
                    product_id,
                    quantity,
                    total_amount,
                    purchase_price,
                    selling_price,
                    profit
                )
            )

            connection.execute(
                """
                UPDATE products
                SET quantity = quantity - ?
                WHERE id = ?
                """,
                (
                    quantity,
                    product_id
                )
            )

            connection.commit()

    connection.close()

    connection = get_db()

    products = connection.execute(
        """
        SELECT *
        FROM products
        ORDER BY name
        """
    ).fetchall()

    sales = connection.execute(
        """
        SELECT
            sales.id,
            products.name AS product_name,
            sales.quantity,
            sales.total_amount,
            sales.sale_date,
            sales.purchase_price_at_sale,
            sales.selling_price_at_sale,
            sales.profit
        FROM sales
        JOIN products
        ON sales.product_id = products.id
        ORDER BY sales.id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "sales.html",
        products=products,
        sales=sales
    )


# =========================
# REPORTS
# =========================
@app.route("/reports")
def reports():

    connection = get_db()

    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    if start_date and end_date:

        report = connection.execute(
            """
            SELECT
                COALESCE(SUM(total_amount), 0) AS sales,
                COALESCE(SUM(profit), 0) AS profit,
                COALESCE(SUM(quantity), 0) AS products_sold
            FROM sales
            WHERE DATE(sale_date)
            BETWEEN DATE(?) AND DATE(?)
            """,
            (
                start_date,
                end_date
            )
        ).fetchone()

        top_products = connection.execute(
            """
            SELECT
                products.name AS product_name,
                SUM(sales.quantity) AS total_sold
            FROM sales
            JOIN products
            ON sales.product_id = products.id
            WHERE DATE(sale_date)
            BETWEEN DATE(?) AND DATE(?)
            GROUP BY sales.product_id
            ORDER BY total_sold DESC
            """,
            (
                start_date,
                end_date
            )
        ).fetchall()

    else:

        report = connection.execute(
            """
            SELECT
                COALESCE(SUM(total_amount), 0) AS sales,
                COALESCE(SUM(profit), 0) AS profit,
                COALESCE(SUM(quantity), 0) AS products_sold
            FROM sales
            WHERE DATE(sale_date) = DATE('now')
            """
        ).fetchone()

        top_products = connection.execute(
            """
            SELECT
                products.name AS product_name,
                SUM(sales.quantity) AS total_sold
            FROM sales
            JOIN products
            ON sales.product_id = products.id
            WHERE DATE(sale_date) = DATE('now')
            GROUP BY sales.product_id
            ORDER BY total_sold DESC
            """
        ).fetchall()

    connection.close()

    return render_template(
        "reports.html",
        report=report,
        top_products=top_products,
        start_date=start_date,
        end_date=end_date
    )


# =========================
# INVOICE
# =========================
@app.route("/invoice")
def invoice():

    connection = get_db()

    products = connection.execute(
        """
        SELECT *
        FROM products
        ORDER BY name
        """
    ).fetchall()

    invoice_data = None

    product_id = request.args.get("product_id")
    quantity = request.args.get("quantity")

    if product_id and quantity:

        try:
            quantity = int(quantity)
        except ValueError:
            quantity = 0

        product = connection.execute(
            """
            SELECT *
            FROM products
            WHERE id = ?
            """,
            (product_id,)
        ).fetchone()

        if product and quantity > 0:

            total_amount = (
                product["selling_price"] * quantity
            )

            profit = (
                product["selling_price"]
                - product["purchase_price"]
            ) * quantity

            invoice_data = {
                "date": datetime.now().strftime(
                    "%d-%m-%Y %H:%M"
                ),
                "product_name": product["name"],
                "quantity": quantity,
                "selling_price": product["selling_price"],
                "total_amount": total_amount,
                "profit": profit
            }

    connection.close()

    return render_template(
        "invoice.html",
        products=products,
        invoice=invoice_data
    )


# =========================
# START APPLICATION
# =========================
if __name__ == "__main__":

    create_database()

    app.run(debug=True)