from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

from flask_sqlalchemy import SQLAlchemy

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)

from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from pathlib import Path
import re
import shutil


# =========================================================
# APP CONFIGURATION
# =========================================================

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent

app.config["SECRET_KEY"] = "laptech_world_secret_key"

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + str(BASE_DIR / "instance" / "database.db")
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["RECOVERY_CODE"] = "shop-reset-2026"

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

PASSWORD_PATTERN = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>_\-+=~`\[\];\'\\/]).{8,}$'
)


# =========================================================
# DATABASE MODELS
# =========================================================

class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True, nullable=False)

    email = db.Column(db.String(150), nullable=True)

    password = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(50), default="admin")


class Product(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    category = db.Column(db.String(50), nullable=True)

    product_name = db.Column(db.String(200), nullable=True)

    brand = db.Column(db.String(100), nullable=True)

    imei = db.Column(db.String(50), nullable=True)

    imei2 = db.Column(db.String(50), nullable=True)

    serial_number = db.Column(db.String(100), nullable=True)

    ram = db.Column(db.String(50), nullable=True)

    storage = db.Column(db.String(50), nullable=True)

    generation = db.Column(db.String(50), nullable=True)

    processor = db.Column(db.String(50), nullable=True)

    supplier_name = db.Column(db.String(150), nullable=True)

    purchase_paid_amount = db.Column(db.Float, nullable=True)

    purchase_price = db.Column(db.Float, nullable=True)

    sale_price = db.Column(db.Float, nullable=True)

    quantity = db.Column(db.Integer, default=0)

    is_available = db.Column(db.Boolean, default=True)

    is_deleted = db.Column(db.Boolean, default=False)

    deleted_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Invoice(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    invoice_number = db.Column(db.String(50), unique=True, nullable=False)

    customer_name = db.Column(db.String(150), nullable=True)

    customer_phone = db.Column(db.String(50), nullable=True)

    invoice_date = db.Column(db.DateTime, default=datetime.now)

    paid_amount = db.Column(db.Float, nullable=True)

    is_deleted = db.Column(db.Boolean, default=False)

    deleted_at = db.Column(db.DateTime, nullable=True)

    items = db.relationship(
        "InvoiceItem",
        backref="invoice",
        cascade="all, delete-orphan"
    )


class InvoiceItem(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    invoice_id = db.Column(
        db.Integer,
        db.ForeignKey("invoice.id"),
        nullable=False
    )

    product_id = db.Column(db.Integer, nullable=True)

    category = db.Column(db.String(50), nullable=True)

    product_name = db.Column(db.String(200), nullable=True)

    brand = db.Column(db.String(100), nullable=True)

    imei = db.Column(db.String(50), nullable=True)

    imei2 = db.Column(db.String(50), nullable=True)

    serial_number = db.Column(db.String(100), nullable=True)

    quantity = db.Column(db.Integer, default=1)

    purchase_price = db.Column(db.Float, nullable=True)

    sale_price = db.Column(db.Float, nullable=True)


class DeletedInvoiceItem(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    invoice_id = db.Column(db.Integer, nullable=True)

    invoice_number = db.Column(db.String(50), nullable=True)

    product_id = db.Column(db.Integer, nullable=True)

    category = db.Column(db.String(50), nullable=True)

    product_name = db.Column(db.String(200), nullable=True)

    brand = db.Column(db.String(100), nullable=True)

    imei = db.Column(db.String(50), nullable=True)

    imei2 = db.Column(db.String(50), nullable=True)

    serial_number = db.Column(db.String(100), nullable=True)

    quantity = db.Column(db.Integer, default=1)

    purchase_price = db.Column(db.Float, nullable=True)

    sale_price = db.Column(db.Float, nullable=True)

    restocked = db.Column(db.Boolean, default=False)

    deleted_at = db.Column(db.DateTime, default=datetime.now)


class SupplierLedger(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    supplier_name = db.Column(db.String(150), nullable=False)

    phone = db.Column(db.String(50), nullable=True)

    entry_date = db.Column(db.DateTime, default=datetime.now)

    total_amount = db.Column(db.Float, default=0.0)

    paid_amount = db.Column(db.Float, default=0.0)

    notes = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.now)


# =========================================================
# LOGIN MANAGER
# =========================================================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# =========================================================
# DATABASE MIGRATIONS & FIXES
# =========================================================

def fix_supplier_columns():

    inspector = db.session.execute(
        db.text("PRAGMA table_info(product)")
    ).fetchall()

    if not inspector:
        return

    existing_columns = [col[1] for col in inspector]

    if "supplier_name" not in existing_columns:
        db.session.execute(
            db.text("ALTER TABLE product ADD COLUMN supplier_name VARCHAR(150)")
        )

    if "purchase_paid_amount" not in existing_columns:
        db.session.execute(
            db.text("ALTER TABLE product ADD COLUMN purchase_paid_amount FLOAT")
        )

    db.session.commit()


def fix_product_name_nullable():

    inspector = db.session.execute(
        db.text("PRAGMA table_info(product)")
    ).fetchall()

    if not inspector:
        return

    p_col = next(
        (c for c in inspector if c[1] == "product_name"),
        None
    )

    if not p_col or p_col[3] == 0:
        return

    db.session.execute(db.text("PRAGMA foreign_keys=OFF"))

    db.session.execute(db.text("ALTER TABLE product RENAME TO product_old"))

    db.session.execute(
        db.text(
            """
            CREATE TABLE product (
                id INTEGER PRIMARY KEY,
                category VARCHAR(50),
                product_name VARCHAR(200),
                brand VARCHAR(100),
                imei VARCHAR(50),
                imei2 VARCHAR(50),
                serial_number VARCHAR(100),
                ram VARCHAR(50),
                storage VARCHAR(50),
                generation VARCHAR(50),
                processor VARCHAR(50),
                supplier_name VARCHAR(150),
                purchase_paid_amount FLOAT,
                purchase_price FLOAT,
                sale_price FLOAT,
                quantity INTEGER,
                is_available BOOLEAN,
                is_deleted BOOLEAN DEFAULT 0,
                deleted_at DATETIME,
                created_at DATETIME
            )
            """
        )
    )

    db.session.execute(
        db.text(
            """
            INSERT INTO product (
                id, category, product_name, brand, imei, imei2,
                serial_number, ram, storage, generation, processor,
                supplier_name, purchase_paid_amount, purchase_price,
                sale_price, quantity, is_available, is_deleted,
                deleted_at, created_at
            )
            SELECT
                id, category, product_name, brand, imei, imei2,
                serial_number, ram, storage, generation, processor,
                supplier_name, purchase_paid_amount, purchase_price,
                sale_price, quantity, is_available, is_deleted,
                deleted_at, created_at
            FROM product_old
            """
        )
    )

    db.session.execute(db.text("DROP TABLE product_old"))

    db.session.execute(db.text("PRAGMA foreign_keys=ON"))

    db.session.commit()


def fix_user_email_column():

    inspector = db.session.execute(
        db.text("PRAGMA table_info(user)")
    ).fetchall()

    if inspector and not any(c[1] == "email" for c in inspector):

        db.session.execute(
            db.text("ALTER TABLE user ADD COLUMN email VARCHAR(150)")
        )

        db.session.commit()


def fix_product_spec_columns():

    inspector = db.session.execute(
        db.text("PRAGMA table_info(product)")
    ).fetchall()

    if not inspector:
        return

    existing = [c[1] for c in inspector]

    for col, ctype in [
        ("ram", "VARCHAR(50)"),
        ("storage", "VARCHAR(50)"),
        ("generation", "VARCHAR(50)"),
        ("processor", "VARCHAR(50)"),
        ("imei2", "VARCHAR(50)")
    ]:

        if col not in existing:

            db.session.execute(
                db.text(f"ALTER TABLE product ADD COLUMN {col} {ctype}")
            )

    db.session.commit()


def fix_soft_delete_columns():

    for table in ["product", "invoice"]:

        inspector = db.session.execute(
            db.text(f"PRAGMA table_info({table})")
        ).fetchall()

        if not inspector:
            continue

        existing = [c[1] for c in inspector]

        if "is_deleted" not in existing:

            db.session.execute(
                db.text(
                    f"ALTER TABLE {table} ADD COLUMN is_deleted BOOLEAN DEFAULT 0"
                )
            )

        if "deleted_at" not in existing:

            db.session.execute(
                db.text(
                    f"ALTER TABLE {table} ADD COLUMN deleted_at DATETIME"
                )
            )

    db.session.commit()


def fix_invoice_payment_column():

    inspector = db.session.execute(
        db.text("PRAGMA table_info(invoice)")
    ).fetchall()

    if inspector and "paid_amount" not in [c[1] for c in inspector]:

        db.session.execute(
            db.text("ALTER TABLE invoice ADD COLUMN paid_amount FLOAT")
        )

        db.session.commit()


def fix_invoice_item_imei2_column():

    inspector = db.session.execute(
        db.text("PRAGMA table_info(invoice_item)")
    ).fetchall()

    if not inspector:
        return

    existing = [c[1] for c in inspector]

    if "imei2" not in existing:

        db.session.execute(
            db.text("ALTER TABLE invoice_item ADD COLUMN imei2 VARCHAR(50)")
        )

        db.session.commit()


def backup_database():

    try:

        backups_folder = BASE_DIR / "instance" / "backups"

        backups_folder.mkdir(exist_ok=True)

        db_path = BASE_DIR / "instance" / "database.db"

        if not db_path.exists():
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        shutil.copy2(
            db_path,
            backups_folder / f"database_{timestamp}.db"
        )

        all_backups = sorted(backups_folder.glob("database_*.db"))

        if len(all_backups) > 10:

            for old in all_backups[:-10]:
                old.unlink()

    except Exception as e:

        print(f"Backup failed: {e}")


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def generate_invoice_number():

    last_invoice = Invoice.query.order_by(Invoice.id.desc()).first()

    return f"INV-{(last_invoice.id + 1 if last_invoice else 1):04d}"


def clean_float(value):

    if value is None:
        return None

    v = str(value).strip()

    try:
        return float(v) if v != "" else None
    except ValueError:
        return None


def clean_int(value, default=0):

    if value is None:
        return default

    v = str(value).strip()

    try:
        return int(v) if v != "" else default
    except ValueError:
        return default


def clean_text(value):

    if value is None:
        return None

    v = str(value).strip()

    return v if v else None


def pick_text(values, i, default):

    v = clean_text(values[i]) if i < len(values) else None

    return v if v else default


def pick_float(values, i, default):

    v = clean_float(values[i]) if i < len(values) else None

    return v if v is not None else default


def pick_strip(values, i, default):

    v = values[i].strip() if i < len(values) else ""

    return v if v else default


# =========================================================
# HOME / DASHBOARD
# =========================================================

@app.route("/")
@login_required
def dashboard():

    filter_type = request.args.get("filter", "today")

    now = datetime.now()

    today_start = datetime(now.year, now.month, now.day)

    start_date = None
    end_date = None

    if filter_type == "today":

        start_date = today_start
        end_date = now

    elif filter_type == "yesterday":

        start_date = today_start - timedelta(days=1)
        end_date = today_start

    elif filter_type == "7days":

        start_date = today_start - timedelta(days=7)
        end_date = now

    elif filter_type == "month":

        start_date = datetime(now.year, now.month, 1)
        end_date = now

    elif filter_type == "year":

        start_date = datetime(now.year, 1, 1)
        end_date = now

    elif filter_type == "all":

        start_date = None
        end_date = None

    sales_query = Invoice.query.filter_by(is_deleted=False)

    if start_date and end_date:

        sales_query = sales_query.filter(
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= end_date
        )

    invoices = sales_query.all()

    sales_amount = 0.0
    profit_amount = 0.0
    sold_purchase_cost = 0.0
    sales_count = 0

    for inv in invoices:

        for item in inv.items:

            qty = item.quantity or 0
            sp = item.sale_price or 0.0
            pp = item.purchase_price or 0.0

            sales_amount += sp * qty
            profit_amount += (sp - pp) * qty
            sold_purchase_cost += pp * qty
            sales_count += qty

    purchase_query = Product.query.filter_by(is_deleted=False)

    if start_date and end_date:

        purchase_query = purchase_query.filter(
            Product.created_at >= start_date,
            Product.created_at <= end_date
        )

    purchased_products = purchase_query.all()

    # Har product mein kitni units bik chuki hain
    sold_map = {}

    for it in InvoiceItem.query.all():

        if it.product_id:

            sold_map[it.product_id] = (
                sold_map.get(it.product_id, 0) + (it.quantity or 0)
            )

    # Kharidi hui units (maujooda + bik chuki)
    purchase_count = sum(
        (p.quantity or 0) + sold_map.get(p.id, 0)
        for p in purchased_products
    )

    purchase_amount = sum(
        (p.purchase_price or 0.0) *
        ((p.quantity or 0) + sold_map.get(p.id, 0))
        for p in purchased_products
    )

    # Selected muddat ke end ka stock (Yesterday = kal raat ka stock)
    stock_asof = today_start.date()

    if filter_type == "yesterday":
        stock_asof = stock_asof - timedelta(days=1)

    stock_asof_units = 0
    stock_value = 0.0

    live_products = Product.query.filter_by(is_deleted=False).all()

    live_by_id = {p.id: p for p in live_products}

    for p in live_products:

        if p.created_at and p.created_at.date() <= stock_asof:

            bought = (p.quantity or 0) + sold_map.get(p.id, 0)

            stock_asof_units += bought

            stock_value += (p.purchase_price or 0.0) * bought

    for it in InvoiceItem.query.all():

        p = live_by_id.get(it.product_id)

        if (
            p
            and it.invoice
            and it.invoice.invoice_date
            and it.invoice.invoice_date.date() <= stock_asof
        ):

            q = it.quantity or 0

            stock_asof_units -= q

            stock_value -= (p.purchase_price or 0.0) * q

    # Supplier dues SupplierLedger se calculate hote hain
    supplier_entries = SupplierLedger.query.all()

    total_supplier_dues = sum(
        ((e.total_amount or 0.0) - (e.paid_amount or 0.0))
        for e in supplier_entries
        if ((e.total_amount or 0.0) - (e.paid_amount or 0.0)) > 0
    )

    return render_template(
        "dashboard.html",
        filter_type=filter_type,
        sales_amount=sales_amount,
        todays_sales_amount=sales_amount,
        purchase_amount=purchase_amount,
        todays_purchase_amount=purchase_amount,
        profit_amount=profit_amount,
        todays_profit_amount=profit_amount,
        total_supplier_dues=total_supplier_dues,
        total_stock_qty=stock_asof_units,
        sales_count=sales_count,
        sold_purchase_cost=sold_purchase_cost,
        purchase_count=purchase_count,
        stock_value=stock_value
    )


# =========================================================
# LOGIN / WELCOME / FORGOT PASSWORD / ACCOUNT
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        identifier = request.form.get("username", "").strip()

        password = request.form.get("password", "")

        # Check by Username OR Email
        user = User.query.filter(
            db.or_(
                User.username == identifier,
                User.email == identifier
            )
        ).first()

        if user and check_password_hash(user.password, password):

            login_user(user)

            return redirect(url_for("welcome"))

        flash("Invalid username/email or password.", "danger")

    return render_template("login.html")


@app.route("/welcome")
@login_required
def welcome():

    return render_template("welcome.html")


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        username = request.form.get("username", "").strip()

        recovery_code = request.form.get("recovery_code", "").strip()

        new_password = request.form.get("new_password", "")

        confirm_password = request.form.get("confirm_password", "")

        if recovery_code != app.config["RECOVERY_CODE"]:

            flash("Recovery code is incorrect.", "danger")

            return redirect(url_for("forgot_password"))

        user = User.query.filter_by(username=username).first()

        if not user:

            flash("No account found with that username.", "danger")

            return redirect(url_for("forgot_password"))

        if not PASSWORD_PATTERN.match(new_password):

            flash(
                "Password must be at least 8 characters and include uppercase, lowercase, number, and special character.",
                "danger"
            )

            return redirect(url_for("forgot_password"))

        if new_password != confirm_password:

            flash("Passwords do not match.", "danger")

            return redirect(url_for("forgot_password"))

        user.password = generate_password_hash(new_password)

        db.session.commit()

        flash("Password reset successfully. Please login.", "success")

        return redirect(url_for("login"))

    return render_template("forgot_password.html")


@app.route("/forgot_username", methods=["GET", "POST"])
def forgot_username():

    if request.method == "POST":

        email = request.form.get("email", "").strip()

        current_username = request.form.get("current_username", "").strip()

        recovery_code = request.form.get("recovery_code", "").strip()

        new_username = request.form.get("new_username", "").strip()

        if recovery_code != app.config["RECOVERY_CODE"]:

            flash("Recovery code is incorrect.", "danger")

            return redirect(url_for("forgot_username"))

        if not new_username:

            flash("Please enter a new username.", "danger")

            return redirect(url_for("forgot_username"))

        user = None

        if email:

            user = User.query.filter_by(email=email).first()

        elif current_username:

            user = User.query.filter_by(username=current_username).first()

        if not user:

            flash("No account found.", "danger")

            return redirect(url_for("forgot_username"))

        user.username = new_username

        db.session.commit()

        flash(
            f"Username updated successfully. Your new username is: {new_username}",
            "success"
        )

        return redirect(url_for("login"))

    return render_template("forgot_username.html")


@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(url_for("login"))


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():

    if request.method == "POST":

        action = request.form.get("action")

        if action == "update_profile":

            username = request.form.get("username", "").strip()

            email = request.form.get("email", "").strip()

            if not username:

                flash("Username cannot be empty.", "danger")

                return redirect(url_for("account"))

            current_user.username = username
            current_user.email = email or None

            db.session.commit()

            flash("Profile updated successfully.", "success")

            return redirect(url_for("account"))

        elif action == "change_password":

            current_password = request.form.get("current_password", "")

            new_password = request.form.get("new_password", "")

            confirm_password = request.form.get("confirm_password", "")

            if not check_password_hash(current_user.password, current_password):

                flash("Current password is incorrect.", "danger")

                return redirect(url_for("account"))

            if new_password != confirm_password:

                flash("New passwords do not match.", "danger")

                return redirect(url_for("account"))

            if not PASSWORD_PATTERN.match(new_password):

                flash(
                    "Password must be at least 8 characters and include uppercase, lowercase, number, and special character.",
                    "danger"
                )

                return redirect(url_for("account"))

            current_user.password = generate_password_hash(new_password)

            db.session.commit()

            flash("Password changed successfully.", "success")

            return redirect(url_for("account"))

    return render_template("account.html")


# =========================================================
# CUSTOMERS & CUSTOMER HISTORY
# =========================================================

@app.route("/customers")
@login_required
def customers():

    invoices = (
        Invoice.query
        .filter_by(is_deleted=False)
        .order_by(Invoice.invoice_date.desc())
        .all()
    )

    customer_map = {}

    for inv in invoices:

        phone = (inv.customer_phone or "").strip()

        name = (inv.customer_name or "Unknown").strip()

        key = phone if phone else name

        if key not in customer_map:

            customer_map[key] = {
                "name": name,
                "phone": phone or "-",
                "orders": 0,
                "total_spent": 0.0,
                "outstanding": 0.0,
                "last_purchase": inv.invoice_date
            }

        entry = customer_map[key]

        entry["orders"] += 1

        invoice_total = sum(
            (item.sale_price or 0) * item.quantity
            for item in inv.items
        )

        paid_amt = (
            inv.paid_amount
            if inv.paid_amount is not None
            else invoice_total
        )

        remaining_amt = invoice_total - paid_amt

        entry["total_spent"] += invoice_total
        entry["outstanding"] += remaining_amt

        if (
            inv.invoice_date
            and (
                entry["last_purchase"] is None
                or inv.invoice_date > entry["last_purchase"]
            )
        ):

            entry["last_purchase"] = inv.invoice_date

    customers_list = sorted(
        customer_map.values(),
        key=lambda c: c["last_purchase"] or datetime.min,
        reverse=True
    )

    paid_customers = [
        c for c in customers_list
        if c["outstanding"] <= 0.009
    ]

    pending_customers = sorted(
        [
            c for c in customers_list
            if c["outstanding"] > 0.009
        ],
        key=lambda c: c["outstanding"],
        reverse=True
    )

    return render_template(
        "customers.html",
        paid_customers=paid_customers,
        pending_customers=pending_customers
    )


@app.route("/customer_history")
@login_required
def customer_history():

    phone = request.args.get("phone", "").strip()

    name = request.args.get("name", "").strip()

    if phone and phone != "-":

        matching_invoices = (
            Invoice.query
            .filter_by(customer_phone=phone, is_deleted=False)
            .order_by(Invoice.invoice_date.desc())
            .all()
        )

    else:

        matching_invoices = (
            Invoice.query
            .filter_by(customer_name=name, is_deleted=False)
            .order_by(Invoice.invoice_date.desc())
            .all()
        )

    history = []

    for inv in matching_invoices:

        invoice_total = sum(
            (item.sale_price or 0) * item.quantity
            for item in inv.items
        )

        paid_amt = (
            inv.paid_amount
            if inv.paid_amount is not None
            else invoice_total
        )

        remaining_amt = invoice_total - paid_amt

        history.append({
            "invoice": inv,
            "total": invoice_total,
            "item_count": len(inv.items),
            "paid": paid_amt,
            "remaining": remaining_amt
        })

    return render_template(
        "customer_history.html",
        history=history,
        phone=phone,
        name=name
    )


# =========================================================
# STOCK
# =========================================================

@app.route("/stock")
@login_required
def stock():

    def by_category(cat):
        return (
            Product.query
            .filter(
                Product.category == cat,
                Product.is_deleted == False
            )
            .order_by(Product.id.desc())
            .all()
        )

    mobile_products = by_category("Mobile")

    laptop_products = by_category("Laptop")

    accessory_products = by_category("Accessories")

    other_products = by_category("Other")

    def total_qty(products):
        return sum(p.quantity or 0 for p in products)

    all_products = (
        mobile_products +
        laptop_products +
        accessory_products +
        other_products
    )

    low_stock = [
        p for p in all_products
        if (p.quantity or 0) <= 2
    ]

    return render_template(
        "stock.html",
        mobile_products=mobile_products,
        laptop_products=laptop_products,
        accessory_products=accessory_products,
        other_products=other_products,
        mobile_total=total_qty(mobile_products),
        laptop_total=total_qty(laptop_products),
        accessory_total=total_qty(accessory_products),
        other_total=total_qty(other_products),
        low_stock=low_stock
    )


# =========================================================
# PURCHASES
# =========================================================

@app.route("/purchases")
@login_required
def purchases():

    all_products = (
        Product.query
        .filter_by(is_deleted=False)
        .order_by(Product.created_at.desc())
        .all()
    )

    purchases_list = []
    total_purchase_value = 0.0
    today_purchase_value = 0.0

    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)

    for p in all_products:

        qty = p.quantity or 0
        pp = p.purchase_price or 0.0
        tot_cost = pp * qty

        paid = (
            p.purchase_paid_amount
            if p.purchase_paid_amount is not None
            else tot_cost
        )

        due = (
            tot_cost - paid
            if tot_cost > paid
            else 0.0
        )

        total_purchase_value += tot_cost

        # Calculate today's purchases
        if p.created_at and p.created_at >= today_start:
            today_purchase_value += tot_cost

        purchases_list.append({
            "id": p.id,
            "date": p.created_at,
            "category": p.category,
            "product_name": p.product_name,
            "brand": p.brand,
            "supplier_name": p.supplier_name or "-",
            "quantity": qty,
            "purchase_price": pp,
            "total_cost": tot_cost,
            "paid_amount": paid,
            "due_amount": due
        })

    return render_template(
        "purchases.html",
        purchases=purchases_list,
        total_purchase_value=total_purchase_value,
        today_purchase_value=today_purchase_value
    )


# =========================================================
# SUPPLIER LEDGER (separate page)
# =========================================================

@app.route("/suppliers", methods=["GET", "POST"])
@login_required
def suppliers():

    if request.method == "POST":

        supplier_name = request.form.get("supplier_name", "").strip()

        phone = request.form.get("phone", "").strip()

        entry_date_str = request.form.get("entry_date", "").strip()

        total_amount = clean_float(request.form.get("total_amount")) or 0.0

        paid_amount = clean_float(request.form.get("paid_amount")) or 0.0

        notes = clean_text(request.form.get("notes"))

        if not supplier_name:

            flash("Supplier ka naam likhna zaroori hai.", "danger")

            return redirect(url_for("suppliers"))

        if paid_amount > total_amount:
            paid_amount = total_amount

        entry_date = datetime.now()

        if entry_date_str:

            try:
                entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d")
            except ValueError:
                entry_date = datetime.now()

        entry = SupplierLedger(
            supplier_name=supplier_name,
            phone=phone or None,
            entry_date=entry_date,
            total_amount=total_amount,
            paid_amount=paid_amount,
            notes=notes
        )

        db.session.add(entry)

        db.session.commit()

        flash("Supplier entry add ho gayi.", "success")

        return redirect(url_for("suppliers"))

    entries = SupplierLedger.query.order_by(
        SupplierLedger.entry_date.desc()
    ).all()

    total_amount_sum = 0.0
    total_paid_sum = 0.0
    total_due_sum = 0.0

    ledger_list = []

    for e in entries:

        due = (e.total_amount or 0.0) - (e.paid_amount or 0.0)

        if due < 0:
            due = 0.0

        total_amount_sum += e.total_amount or 0.0
        total_paid_sum += e.paid_amount or 0.0
        total_due_sum += due

        ledger_list.append({
            "id": e.id,
            "supplier_name": e.supplier_name,
            "phone": e.phone or "-",
            "entry_date": e.entry_date,
            "total_amount": e.total_amount or 0.0,
            "paid_amount": e.paid_amount or 0.0,
            "due_amount": due,
            "notes": e.notes or "-"
        })

    return render_template(
        "suppliers.html",
        ledger=ledger_list,
        total_amount_sum=total_amount_sum,
        total_paid_sum=total_paid_sum,
        total_due_sum=total_due_sum
    )


@app.route("/suppliers/<int:entry_id>/add_payment", methods=["POST"])
@login_required
def add_supplier_ledger_payment(entry_id):

    entry = db.session.get(SupplierLedger, entry_id)

    if entry:

        add_pay = clean_float(request.form.get("additional_payment")) or 0.0

        new_paid = (entry.paid_amount or 0.0) + add_pay

        if new_paid > (entry.total_amount or 0.0):
            new_paid = entry.total_amount or 0.0

        if new_paid < 0:
            new_paid = 0.0

        entry.paid_amount = new_paid

        db.session.commit()

        flash("Payment record ho gaya.", "success")

    return redirect(url_for("suppliers"))


@app.route("/suppliers/<int:entry_id>/edit", methods=["POST"])
@login_required
def edit_supplier_ledger(entry_id):

    entry = db.session.get(SupplierLedger, entry_id)

    if entry:

        supplier_name = request.form.get("supplier_name", "").strip()

        phone = request.form.get("phone", "").strip()

        entry_date_str = request.form.get("entry_date", "").strip()

        total_amount = clean_float(request.form.get("total_amount"))

        paid_amount = clean_float(request.form.get("paid_amount"))

        notes = clean_text(request.form.get("notes"))

        if supplier_name:
            entry.supplier_name = supplier_name

        entry.phone = phone or None

        if entry_date_str:

            try:
                entry.entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d")
            except ValueError:
                pass

        if total_amount is not None:
            entry.total_amount = total_amount

        if paid_amount is not None:
            entry.paid_amount = paid_amount

        if entry.paid_amount and entry.total_amount and entry.paid_amount > entry.total_amount:
            entry.paid_amount = entry.total_amount

        entry.notes = notes

        db.session.commit()

        flash("Supplier entry update ho gayi.", "success")

    return redirect(url_for("suppliers"))


@app.route("/suppliers/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_supplier_ledger(entry_id):

    entry = db.session.get(SupplierLedger, entry_id)

    if entry:

        db.session.delete(entry)

        db.session.commit()

        flash("Supplier entry delete ho gayi.", "success")

    return redirect(url_for("suppliers"))


# =========================================================
# PRODUCTS
# =========================================================

@app.route("/products", methods=["GET", "POST"])
@login_required
def products():

    if request.method == "POST":

        action = request.form.get("action", "add_product")

        if action == "add_product":

            category = request.form.get("category", "").strip()

            if category == "Accessory":
                category = "Accessories"

            product_name = request.form.get("product_name", "").strip()

            brand = request.form.get("brand", "").strip()

            supplier_name = request.form.get("supplier_name", "").strip()

            quantity = clean_int(request.form.get("quantity"), 1)

            if quantity < 1:
                quantity = 1

            common_pp = (
                clean_float(request.form.get("common_purchase_price"))
                or clean_float(request.form.get("purchase_price"))
            )

            common_sp = (
                clean_float(request.form.get("common_sale_price"))
                or clean_float(request.form.get("sale_price"))
            )

            paid_amount = clean_float(request.form.get("purchase_paid_amount"))

            common_ram = clean_text(request.form.get("common_ram"))

            common_storage = clean_text(request.form.get("common_storage"))

            common_gen = clean_text(request.form.get("common_generation"))

            common_proc = clean_text(request.form.get("common_processor"))

            products_added = 0

            if category == "Mobile":

                imeis = request.form.getlist("imei[]")

                imei2s = request.form.getlist("imei2[]")

                rams = request.form.getlist("ram[]")

                storages = request.form.getlist("storage[]")

                pps = request.form.getlist("purchase_price[]")

                sps = request.form.getlist("sale_price[]")

                for i in range(quantity):

                    imei = imeis[i].strip() if i < len(imeis) else ""

                    imei2 = imei2s[i].strip() if i < len(imei2s) else ""

                    p = Product(
                        category="Mobile",
                        product_name=product_name or None,
                        brand=brand or None,
                        imei=imei or None,
                        imei2=imei2 or None,
                        ram=pick_text(rams, i, common_ram),
                        storage=pick_text(storages, i, common_storage),
                        supplier_name=supplier_name or None,
                        purchase_paid_amount=paid_amount,
                        purchase_price=pick_float(pps, i, common_pp),
                        sale_price=pick_float(sps, i, common_sp),
                        quantity=1,
                        is_available=True
                    )

                    db.session.add(p)

                    products_added += 1

            elif category == "Laptop":

                serials = request.form.getlist("serial[]")

                gens = request.form.getlist("generation[]")

                procs = request.form.getlist("processor[]")

                pps = request.form.getlist("purchase_price[]")

                sps = request.form.getlist("sale_price[]")

                for i in range(quantity):

                    sn = serials[i].strip() if i < len(serials) else ""

                    p = Product(
                        category="Laptop",
                        product_name=product_name or None,
                        brand=brand or None,
                        serial_number=sn or None,
                        generation=pick_text(gens, i, common_gen),
                        processor=pick_text(procs, i, common_proc),
                        supplier_name=supplier_name or None,
                        purchase_paid_amount=paid_amount,
                        purchase_price=pick_float(pps, i, common_pp),
                        sale_price=pick_float(sps, i, common_sp),
                        quantity=1,
                        is_available=True
                    )

                    db.session.add(p)

                    products_added += 1

            elif category in ["Accessories", "Other"]:

                if category == "Accessories":
                    names = request.form.getlist("accessory_product_name[]")
                    brands = request.form.getlist("accessory_brand[]")
                else:
                    names = request.form.getlist("other_product_name[]")
                    brands = request.form.getlist("other_brand[]")

                pps = request.form.getlist("purchase_price[]")

                sps = request.form.getlist("sale_price[]")

                for i in range(quantity):

                    fn = pick_strip(names, i, product_name)

                    fb = pick_strip(brands, i, brand)

                    p = Product(
                        category=category,
                        product_name=fn or None,
                        brand=fb or None,
                        supplier_name=supplier_name or None,
                        purchase_paid_amount=paid_amount,
                        purchase_price=pick_float(pps, i, common_pp),
                        sale_price=pick_float(sps, i, common_sp),
                        quantity=1,
                        is_available=True
                    )

                    db.session.add(p)

                    products_added += 1

            db.session.commit()

            flash(
                f"{products_added} {category} product(s) added successfully.",
                "success"
            )

            return redirect(url_for("products"))

    all_products = (
        Product.query
        .filter_by(is_deleted=False)
        .order_by(Product.id.desc())
        .all()
    )

    mobile_products = [p for p in all_products if p.category == "Mobile"]

    laptop_products = [p for p in all_products if p.category == "Laptop"]

    accessory_products = [p for p in all_products if p.category == "Accessories"]

    other_products = [p for p in all_products if p.category == "Other"]

    return render_template(
        "products.html",
        products=all_products,
        mobile_products=mobile_products,
        laptop_products=laptop_products,
        accessory_products=accessory_products,
        other_products=other_products
    )


@app.route("/edit_product/<int:product_id>", methods=["GET", "POST"])
@login_required
def edit_product(product_id):

    product = db.session.get(Product, product_id)

    if not product:

        flash("Product not found.", "danger")

        return redirect(url_for("products"))

    if request.method == "POST":

        product.category = request.form.get("category", "").strip() or None

        product.product_name = request.form.get("product_name", "").strip() or None

        product.brand = request.form.get("brand", "").strip() or None

        product.supplier_name = request.form.get("supplier_name", "").strip() or None

        product.purchase_paid_amount = clean_float(
            request.form.get("purchase_paid_amount")
        )

        product.imei = request.form.get("imei", "").strip() or None

        product.imei2 = request.form.get("imei2", "").strip() or None

        product.serial_number = request.form.get("serial_number", "").strip() or None

        product.ram = clean_text(request.form.get("ram"))

        product.storage = clean_text(request.form.get("storage"))

        product.generation = clean_text(request.form.get("generation"))

        product.processor = clean_text(request.form.get("processor"))

        product.purchase_price = clean_float(request.form.get("purchase_price"))

        product.sale_price = clean_float(request.form.get("sale_price"))

        product.quantity = clean_int(request.form.get("quantity"), 0)

        db.session.commit()

        flash("Product updated successfully.", "success")

        return redirect(url_for("products"))

    return render_template("edit_product.html", product=product)


@app.route("/delete_product/<int:product_id>", methods=["GET", "POST"])
@login_required
def delete_product(product_id):

    product = db.session.get(Product, product_id)

    if product:

        product.is_deleted = True
        product.deleted_at = datetime.now()

        db.session.commit()

        flash(
            "Product moved to Trash. You can restore it within 7 days.",
            "success"
        )

    return redirect(url_for("products"))


@app.route("/bulk_delete_products", methods=["POST"])
@login_required
def bulk_delete_products():

    ids_str = request.form.get("product_ids", "")

    id_list = [
        int(i)
        for i in ids_str.split(",")
        if i.strip().isdigit()
    ]

    if not id_list:

        flash("Koi product select nahi kiya gaya.", "danger")

        return redirect(url_for("products"))

    count = 0

    for product_id in id_list:

        product = db.session.get(Product, product_id)

        if product:

            product.is_deleted = True
            product.deleted_at = datetime.now()

            count += 1

    db.session.commit()

    flash(
        f"{count} product(s) Trash mein chali gayi. 7 din tak restore kar sakte hain.",
        "success"
    )

    return redirect(url_for("products"))


# =========================================================
# SALES & CART
# =========================================================

@app.route("/sales", methods=["GET", "POST"])
@login_required
def sales():

    if "cart" not in session:
        session["cart"] = []

    if request.method == "POST":

        action = request.form.get("action")

        # -------------------------------------------------
        # ADD TO CART
        # -------------------------------------------------

        if action == "add_to_cart":

            product_id = clean_int(request.form.get("product_id"), 0)

            quantity = clean_int(request.form.get("quantity"), 1)

            identifier = request.form.get("imei", "").strip()

            if not identifier:

                identifier = request.form.get("serial_number", "").strip()

            product = None

            # Search exact unit by IMEI1, IMEI2 or Serial
            if identifier:

                product = Product.query.filter(
                    Product.is_deleted == False,
                    Product.is_available == True,
                    db.or_(
                        Product.imei == identifier,
                        Product.imei2 == identifier,
                        Product.serial_number == identifier
                    )
                ).first()

            # Existing dropdown functionality
            if not product and product_id:

                product = db.session.get(Product, product_id)

            if not product or not product.is_available:

                return render_sales("Product not available.")

            # Ek hi product dobara cart mein na aaye
            if any(
                c.get("product_id") == product.id
                for c in session.get("cart", [])
            ):

                return render_sales("Ye product pehle se cart mein hai.")

            # Mobile and Laptop are individual units
            if product.category in ["Mobile", "Laptop"]:

                quantity = 1

            else:

                if quantity < 1:
                    quantity = 1

                if quantity > product.quantity:

                    return render_sales("Not enough stock available.")

            sale_price = clean_float(request.form.get("sale_price"))

            if sale_price is None:
                sale_price = product.sale_price

            cart = session.get("cart", [])

            cart.append({
                "product_id": product.id,
                "category": product.category,
                "product_name": product.product_name,
                "brand": product.brand,
                "imei": product.imei,
                "imei2": product.imei2,
                "serial_number": product.serial_number,
                "quantity": quantity,
                "purchase_price": product.purchase_price,
                "sale_price": sale_price
            })

            session["cart"] = cart

            session.modified = True

            return redirect(url_for("sales"))

        # -------------------------------------------------
        # REMOVE FROM CART
        # -------------------------------------------------

        elif action == "remove_cart":

            index = clean_int(request.form.get("index"), -1)

            cart = session.get("cart", [])

            if 0 <= index < len(cart):

                cart.pop(index)

            session["cart"] = cart

            session.modified = True

            return redirect(url_for("sales"))

        # -------------------------------------------------
        # EDIT CART
        # -------------------------------------------------

        elif action == "edit_cart":

            index = clean_int(request.form.get("index"), -1)

            cart = session.get("cart", [])

            if 0 <= index < len(cart):

                product = db.session.get(Product, cart[index]["product_id"])

                if product:

                    quantity = clean_int(request.form.get("quantity"), 1)

                    sale_price = clean_float(request.form.get("sale_price"))

                    if product.category in ["Mobile", "Laptop"]:

                        quantity = 1

                    if sale_price is None:

                        sale_price = product.sale_price

                    cart[index]["quantity"] = quantity

                    cart[index]["sale_price"] = sale_price

                    session["cart"] = cart

                    session.modified = True

            return redirect(url_for("sales"))

        # -------------------------------------------------
        # COMPLETE SALE
        # -------------------------------------------------

        elif action == "complete_sale":

            cart = session.get("cart", [])

            if not cart:

                return render_sales("Cart is empty.")

            customer_name = request.form.get("customer_name", "").strip()

            customer_phone = request.form.get("customer_phone", "").strip()

            if not customer_name or not customer_phone:

                return render_sales("Customer details are required.")

            cart_total = sum(
                (item["sale_price"] or 0) * item["quantity"]
                for item in cart
            )

            amount_paid = clean_float(request.form.get("amount_paid"))

            if amount_paid is None or amount_paid > cart_total:

                amount_paid = cart_total

            invoice = Invoice(
                invoice_number=generate_invoice_number(),
                customer_name=customer_name,
                customer_phone=customer_phone,
                paid_amount=amount_paid
            )

            db.session.add(invoice)

            db.session.flush()

            for item in cart:

                product = db.session.get(Product, item["product_id"])

                invoice_item = InvoiceItem(
                    invoice_id=invoice.id,
                    product_id=product.id,
                    category=product.category,
                    product_name=product.product_name,
                    brand=product.brand,
                    imei=product.imei,
                    imei2=product.imei2,
                    serial_number=product.serial_number,
                    quantity=item["quantity"],
                    purchase_price=product.purchase_price,
                    sale_price=item["sale_price"]
                )

                db.session.add(invoice_item)

                product.quantity -= item["quantity"]

                if product.quantity <= 0:

                    product.quantity = 0

                    product.is_available = False

            db.session.commit()

            session["cart"] = []

            session.modified = True

            flash("Sale completed successfully.", "success")

            return redirect(url_for("invoice", invoice_id=invoice.id))

    return render_sales()


# =========================================================
# SEARCH STOCK BY IMEI / SERIAL
# =========================================================

@app.route("/search_stock_identifier")
@login_required
def search_stock_identifier():

    identifier = request.args.get("identifier", "").strip()

    if not identifier:

        return jsonify({
            "found": False,
            "message": "IMEI or Serial Number required."
        })

    ident_lower = identifier.lower()

    product = Product.query.filter(

        Product.is_deleted == False,

        Product.is_available == True,

        db.or_(
            Product.imei == identifier,
            Product.imei2 == identifier,
            db.func.lower(db.func.trim(Product.serial_number)) == ident_lower
        )

    ).first()

    if not product:

        return jsonify({
            "found": False,
            "message": "No matching stock found."
        })

    if any(
        c.get("product_id") == product.id
        for c in session.get("cart", [])
    ):

        return jsonify({
            "found": False,
            "message": "Ye product pehle se cart mein hai."
        })

    return jsonify({
        "found": True,
        "product_id": product.id,
        "category": product.category,
        "product_name": product.product_name or "",
        "brand": product.brand or "",
        "imei": product.imei or "",
        "imei2": product.imei2 or "",
        "serial_number": product.serial_number or "",
        "sale_price": (
            product.sale_price
            if product.sale_price is not None
            else ""
        ),
        "quantity": product.quantity
    })


def render_sales(error=None):

    def available(cat):
        return (
            Product.query
            .filter(
                Product.category == cat,
                Product.quantity > 0,
                Product.is_deleted == False
            )
            .order_by(Product.id.desc())
            .all()
        )

    mobile_products = available("Mobile")

    laptop_products = available("Laptop")

    accessory_products = available("Accessories")

    other_products = available("Other")

    # Jo cheezein cart mein hain wo dropdown mein dobara na aayen
    in_cart_ids = {
        c.get("product_id")
        for c in session.get("cart", [])
    }

    mobile_products = [p for p in mobile_products if p.id not in in_cart_ids]

    laptop_products = [p for p in laptop_products if p.id not in in_cart_ids]

    accessory_products = [p for p in accessory_products if p.id not in in_cart_ids]

    other_products = [p for p in other_products if p.id not in in_cart_ids]

    invoices = (
        Invoice.query
        .filter_by(is_deleted=False)
        .order_by(Invoice.id.desc())
        .all()
    )

    return render_template(
        "sales.html",
        mobile_products=mobile_products,
        laptop_products=laptop_products,
        accessory_products=accessory_products,
        other_products=other_products,
        cart=session.get("cart", []),
        invoices=invoices,
        error=error
    )


# =========================================================
# SALE PLACEHOLDERS
# =========================================================

@app.route("/edit_sale/<int:sale_id>", methods=["GET", "POST"])
@login_required
def edit_sale(sale_id):

    return redirect(url_for("sales"))


@app.route("/delete_sale/<int:sale_id>", methods=["GET", "POST"])
@login_required
def delete_sale(sale_id):

    return redirect(url_for("sales"))


# =========================================================
# INVOICE MANAGEMENT
# =========================================================

@app.route("/invoice/<int:invoice_id>")
@login_required
def invoice(invoice_id):

    invoice_data = db.session.get(Invoice, invoice_id)

    if not invoice_data:

        flash("Invoice not found.", "danger")

        return redirect(url_for("sales"))

    return render_template("invoice.html", invoice=invoice_data)


@app.route("/view_invoice/<int:invoice_id>")
@login_required
def view_invoice(invoice_id):

    return redirect(url_for("invoice", invoice_id=invoice_id))


@app.route("/edit_invoice_customer/<int:invoice_id>", methods=["POST"])
@login_required
def edit_invoice_customer(invoice_id):

    invoice_data = db.session.get(Invoice, invoice_id)

    if invoice_data:

        invoice_data.customer_name = (
            request.form.get("customer_name", "").strip()
            or invoice_data.customer_name
        )

        invoice_data.customer_phone = (
            request.form.get("customer_phone", "").strip()
            or None
        )

        db.session.commit()

        flash("Customer details updated successfully.", "success")

    return redirect(url_for("invoice", invoice_id=invoice_id))


@app.route("/update_invoice_payment/<int:invoice_id>", methods=["POST"])
@login_required
def update_invoice_payment(invoice_id):

    invoice_data = db.session.get(Invoice, invoice_id)

    if invoice_data:

        additional_payment = (
            clean_float(request.form.get("additional_payment")) or 0
        )

        grand_total = sum(
            (item.sale_price or 0) * item.quantity
            for item in invoice_data.items
        )

        current_paid = (
            invoice_data.paid_amount
            if invoice_data.paid_amount is not None
            else grand_total
        )

        new_paid = current_paid + additional_payment

        if new_paid > grand_total:
            new_paid = grand_total

        invoice_data.paid_amount = new_paid

        db.session.commit()

        flash("Payment recorded successfully.", "success")

    return redirect(url_for("invoice", invoice_id=invoice_id))


@app.route("/edit_invoice_item/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_invoice_item(item_id):

    item = db.session.get(InvoiceItem, item_id)

    if not item:
        return redirect(url_for("sales"))

    if request.method == "POST":

        item.product_name = (
            request.form.get("product_name", "").strip()
            or item.product_name
        )

        item.brand = (
            request.form.get("brand", "").strip()
            or item.brand
        )

        item.sale_price = (
            clean_float(request.form.get("sale_price"))
            or item.sale_price
        )

        db.session.commit()

        flash("Invoice item updated successfully.", "success")

        return redirect(url_for("invoice", invoice_id=item.invoice_id))

    return render_template("edit_invoice_item.html", item=item)


@app.route("/delete_invoice_item/<int:item_id>", methods=["POST"])
@login_required
def delete_invoice_item(item_id):

    item = db.session.get(InvoiceItem, item_id)

    if item:

        invoice_id = item.invoice_id

        restock = request.form.get("restock", "yes")

        product = (
            db.session.get(Product, item.product_id)
            if item.product_id
            else None
        )

        if restock == "yes" and product:

            product.quantity += item.quantity

            product.is_available = True

        db.session.add(
            DeletedInvoiceItem(
                invoice_id=item.invoice_id,
                invoice_number=(
                    item.invoice.invoice_number
                    if item.invoice
                    else None
                ),
                product_id=item.product_id,
                category=item.category,
                product_name=item.product_name,
                brand=item.brand,
                imei=item.imei,
                imei2=item.imei2,
                serial_number=item.serial_number,
                quantity=item.quantity,
                purchase_price=item.purchase_price,
                sale_price=item.sale_price,
                restocked=(restock == "yes" and product is not None)
            )
        )

        db.session.delete(item)

        db.session.commit()

        flash(
            "Item Trash mein chala gaya. Wahan se restore kar sakte hain.",
            "success"
        )

        return redirect(url_for("invoice", invoice_id=invoice_id))

    return redirect(url_for("sales"))


@app.route("/delete_invoice/<int:invoice_id>", methods=["GET", "POST"])
@login_required
def delete_invoice(invoice_id):

    invoice_data = db.session.get(Invoice, invoice_id)

    if invoice_data:

        invoice_data.is_deleted = True

        invoice_data.deleted_at = datetime.now()

        db.session.commit()

        flash("Invoice moved to Trash.", "success")

    return redirect(url_for("sales"))


@app.route("/bulk_delete_invoices", methods=["POST"])
@login_required
def bulk_delete_invoices():

    ids_str = request.form.get("invoice_ids", "")

    id_list = [
        int(i)
        for i in ids_str.split(",")
        if i.strip().isdigit()
    ]

    count = 0

    for invoice_id in id_list:

        invoice_data = db.session.get(Invoice, invoice_id)

        if invoice_data:

            invoice_data.is_deleted = True

            invoice_data.deleted_at = datetime.now()

            count += 1

    db.session.commit()

    flash(f"{count} invoice(s) Trash mein chali gayi.", "success")

    return redirect(url_for("sales"))


# =========================================================
# TRASH
# =========================================================

@app.route("/trash")
@login_required
def trash():

    trashed_products = (
        Product.query
        .filter_by(is_deleted=True)
        .order_by(Product.deleted_at.desc())
        .all()
    )

    trashed_invoices = (
        Invoice.query
        .filter_by(is_deleted=True)
        .order_by(Invoice.deleted_at.desc())
        .all()
    )

    trashed_items = (
        DeletedInvoiceItem.query
        .order_by(DeletedInvoiceItem.deleted_at.desc())
        .all()
    )

    return render_template(
        "trash.html",
        trashed_products=trashed_products,
        trashed_invoices=trashed_invoices,
        trashed_items=trashed_items
    )


@app.route("/restore_product/<int:product_id>", methods=["POST"])
@login_required
def restore_product(product_id):

    product = db.session.get(Product, product_id)

    if product:

        product.is_deleted = False
        product.deleted_at = None

        db.session.commit()

        flash("Product restored successfully.", "success")

    return redirect(url_for("trash"))


@app.route("/restore_invoice/<int:invoice_id>", methods=["POST"])
@login_required
def restore_invoice(invoice_id):

    invoice_data = db.session.get(Invoice, invoice_id)

    if invoice_data:

        invoice_data.is_deleted = False
        invoice_data.deleted_at = None

        db.session.commit()

        flash("Invoice restored successfully.", "success")

    return redirect(url_for("trash"))


@app.route("/permanently_delete_product/<int:product_id>", methods=["POST"])
@login_required
def permanently_delete_product(product_id):

    product = db.session.get(Product, product_id)

    if product:

        db.session.delete(product)

        db.session.commit()

        flash("Product permanently deleted.", "success")

    return redirect(url_for("trash"))


@app.route("/permanently_delete_invoice/<int:invoice_id>", methods=["POST"])
@login_required
def permanently_delete_invoice(invoice_id):

    invoice_data = db.session.get(Invoice, invoice_id)

    if invoice_data:

        for item in invoice_data.items:

            product = db.session.get(Product, item.product_id)

            if product:

                product.quantity += item.quantity

                product.is_available = True

        db.session.delete(invoice_data)

        db.session.commit()

        flash("Invoice permanently deleted and stock restored.", "success")

    return redirect(url_for("trash"))


@app.route("/bulk_restore_products", methods=["POST"])
@login_required
def bulk_restore_products():

    ids_str = request.form.get("product_ids", "")

    id_list = [
        int(i)
        for i in ids_str.split(",")
        if i.strip().isdigit()
    ]

    count = 0

    for product_id in id_list:

        product = db.session.get(Product, product_id)

        if product:

            product.is_deleted = False
            product.deleted_at = None

            count += 1

    db.session.commit()

    flash(f"{count} product(s) restore ho gaye.", "success")

    return redirect(url_for("trash"))


@app.route("/bulk_permanently_delete_products", methods=["POST"])
@login_required
def bulk_permanently_delete_products():

    ids_str = request.form.get("product_ids", "")

    id_list = [
        int(i)
        for i in ids_str.split(",")
        if i.strip().isdigit()
    ]

    count = 0

    for product_id in id_list:

        product = db.session.get(Product, product_id)

        if product:

            db.session.delete(product)

            count += 1

    db.session.commit()

    flash(f"{count} product(s) hamesha ke liye delete ho gaye.", "success")

    return redirect(url_for("trash"))


@app.route("/bulk_restore_invoices", methods=["POST"])
@login_required
def bulk_restore_invoices():

    ids_str = request.form.get("invoice_ids", "")

    id_list = [
        int(i)
        for i in ids_str.split(",")
        if i.strip().isdigit()
    ]

    count = 0

    for invoice_id in id_list:

        invoice_data = db.session.get(Invoice, invoice_id)

        if invoice_data:

            invoice_data.is_deleted = False

            invoice_data.deleted_at = None

            count += 1

    db.session.commit()

    flash(f"{count} invoice(s) restore ho gayi.", "success")

    return redirect(url_for("trash"))


@app.route("/bulk_permanently_delete_invoices", methods=["POST"])
@login_required
def bulk_permanently_delete_invoices():

    ids_str = request.form.get("invoice_ids", "")

    id_list = [
        int(i)
        for i in ids_str.split(",")
        if i.strip().isdigit()
    ]

    count = 0

    for invoice_id in id_list:

        invoice_data = db.session.get(Invoice, invoice_id)

        if invoice_data:

            for item in invoice_data.items:

                product = db.session.get(Product, item.product_id)

                if product:

                    product.quantity += item.quantity

                    product.is_available = True

            db.session.delete(invoice_data)

            count += 1

    db.session.commit()

    flash(
        f"{count} invoice(s) hamesha ke liye delete ho gayi aur stock restore ho gaya.",
        "success"
    )

    return redirect(url_for("trash"))


# =========================================================
# TRASHED INVOICE ITEMS (restore / permanent delete)
# =========================================================

@app.route("/restore_invoice_item/<int:trash_id>", methods=["POST"])
@login_required
def restore_invoice_item(trash_id):

    t = db.session.get(DeletedInvoiceItem, trash_id)

    if not t:
        return redirect(url_for("trash"))

    inv = (
        db.session.get(Invoice, t.invoice_id)
        if t.invoice_id
        else None
    )

    if not inv:

        flash(
            "Is item ki invoice maujood nahi, isliye restore nahi ho sakta.",
            "danger"
        )

        return redirect(url_for("trash"))

    if inv.is_deleted:

        flash(
            "Pehle invoice ko Trash se restore karein, phir item restore karein.",
            "danger"
        )

        return redirect(url_for("trash"))

    product = (
        db.session.get(Product, t.product_id)
        if t.product_id
        else None
    )

    if t.restocked:

        if (
            not product
            or product.is_deleted
            or (product.quantity or 0) < (t.quantity or 0)
        ):

            flash(
                "Ye product ab stock mein nahi hai (dobara bik chuka ya delete ho chuka), isliye restore nahi ho sakta.",
                "danger"
            )

            return redirect(url_for("trash"))

        product.quantity -= (t.quantity or 0)

        if product.quantity <= 0:

            product.quantity = 0

            product.is_available = False

    db.session.add(
        InvoiceItem(
            invoice_id=inv.id,
            product_id=t.product_id,
            category=t.category,
            product_name=t.product_name,
            brand=t.brand,
            imei=t.imei,
            imei2=t.imei2,
            serial_number=t.serial_number,
            quantity=t.quantity,
            purchase_price=t.purchase_price,
            sale_price=t.sale_price
        )
    )

    db.session.delete(t)

    db.session.commit()

    flash("Item invoice mein wapas aa gaya.", "success")

    return redirect(url_for("trash"))


@app.route("/permanently_delete_invoice_item/<int:trash_id>", methods=["POST"])
@login_required
def permanently_delete_invoice_item(trash_id):

    t = db.session.get(DeletedInvoiceItem, trash_id)

    if t:

        db.session.delete(t)

        db.session.commit()

        flash("Item hamesha ke liye delete ho gaya.", "success")

    return redirect(url_for("trash"))


# =========================================================
# HISTORY (har block ka din ba din hisaab)
# =========================================================

HISTORY_BLOCKS = {
    "sales": "Total Sales",
    "purchase": "Total Purchase",
    "profit": "Net Profit",
    "sales_count": "Sales Count (Items Sold)",
    "sold_cost": "Sold Items Cost",
    "purchase_count": "Purchase Count (Items Purchased)",
    "stock": "Stock (Units & Value)",
    "dues": "Supplier Dues"
}


@app.route("/history")
@login_required
def history():

    block = request.args.get("block", "sales")

    if block not in HISTORY_BLOCKS:
        block = "sales"

    today = datetime.now().date()

    year_arg = request.args.get("year", "")

    all_time = (year_arg == "all")

    year = today.year if all_time else clean_int(year_arg, today.year)

    def money(x):
        return "Rs. %.2f" % (x or 0.0)

    def fmt(d):
        return d.strftime("%d-%m-%Y")

    daily = {}

    def day_row(d):

        if d not in daily:

            daily[d] = {
                "sales_invoices": 0,
                "count": 0,
                "sales": 0.0,
                "cost": 0.0,
                "purchase_count": 0,
                "purchase": 0.0,
                "entries": 0,
                "due_total": 0.0,
                "due_paid": 0.0,
                "due_left": 0.0
            }

        return daily[d]

    # ---------- Sales ----------

    invoices = Invoice.query.filter_by(is_deleted=False).all()

    for inv in invoices:

        if not inv.invoice_date:
            continue

        row = day_row(inv.invoice_date.date())

        row["sales_invoices"] += 1

        for item in inv.items:

            qty = item.quantity or 0
            sp = item.sale_price or 0.0
            pp = item.purchase_price or 0.0

            row["sales"] += sp * qty
            row["cost"] += pp * qty
            row["count"] += qty

    # ---------- Purchases + Stock events ----------

    all_items = InvoiceItem.query.all()

    sold_map = {}

    for it in all_items:

        if it.product_id:

            sold_map[it.product_id] = (
                sold_map.get(it.product_id, 0) + (it.quantity or 0)
            )

    products = Product.query.filter_by(is_deleted=False).all()

    product_by_id = {p.id: p for p in products}

    stock_events = {}

    def add_event(d, units, value):

        e = stock_events.setdefault(d, [0, 0.0])

        e[0] += units
        e[1] += value

    for p in products:

        if not p.created_at:
            continue

        d = p.created_at.date()

        pp = p.purchase_price or 0.0

        qty = (p.quantity or 0) + sold_map.get(p.id, 0)

        row = day_row(d)

        row["purchase_count"] += qty
        row["purchase"] += pp * qty

        add_event(d, qty, pp * qty)

    for it in all_items:

        p = product_by_id.get(it.product_id)

        if (
            not p
            or not it.invoice
            or not it.invoice.invoice_date
        ):
            continue

        qty = it.quantity or 0

        add_event(
            it.invoice.invoice_date.date(),
            -qty,
            -(p.purchase_price or 0.0) * qty
        )

    stock_by_day = {}

    if stock_events:

        d = min(stock_events)

        units = 0
        value = 0.0

        while d <= today:

            ev = stock_events.get(d)

            if ev:
                units += ev[0]
                value += ev[1]

            stock_by_day[d] = (units, value)

            d += timedelta(days=1)

    # ---------- Supplier ledger ----------

    for e in SupplierLedger.query.all():

        if not e.entry_date:
            continue

        row = day_row(e.entry_date.date())

        total = e.total_amount or 0.0
        paid = e.paid_amount or 0.0

        row["entries"] += 1
        row["due_total"] += total
        row["due_paid"] += paid
        row["due_left"] += max(total - paid, 0.0)

    # ---------- Table banao ----------

    years = sorted(
        {d.year for d in daily}
        | {d.year for d in stock_by_day}
        | {today.year},
        reverse=True
    )

    year_days = sorted(
        [d for d in daily if all_time or d.year == year],
        reverse=True
    )

    columns = []
    rows = []
    total_row = None

    if block in ("sales", "profit", "sales_count", "sold_cost"):

        days = [d for d in year_days if daily[d]["sales_invoices"] > 0]

        t_inv = sum(daily[d]["sales_invoices"] for d in days)
        t_cnt = sum(daily[d]["count"] for d in days)
        t_sales = sum(daily[d]["sales"] for d in days)
        t_cost = sum(daily[d]["cost"] for d in days)

        if block == "sales":

            columns = ["Date", "Invoices", "Items Sold", "Total Sales"]

            for d in days:
                r = daily[d]
                rows.append([fmt(d), r["sales_invoices"], r["count"], money(r["sales"])])

            total_row = ["Year Total", t_inv, t_cnt, money(t_sales)]

        elif block == "profit":

            columns = ["Date", "Total Sales", "Sold Items Cost", "Net Profit"]

            for d in days:
                r = daily[d]
                rows.append([fmt(d), money(r["sales"]), money(r["cost"]), money(r["sales"] - r["cost"])])

            total_row = ["Year Total", money(t_sales), money(t_cost), money(t_sales - t_cost)]

        elif block == "sales_count":

            columns = ["Date", "Invoices", "Items Sold"]

            for d in days:
                r = daily[d]
                rows.append([fmt(d), r["sales_invoices"], r["count"]])

            total_row = ["Year Total", t_inv, t_cnt]

        else:

            columns = ["Date", "Items Sold", "Sold Items Cost"]

            for d in days:
                r = daily[d]
                rows.append([fmt(d), r["count"], money(r["cost"])])

            total_row = ["Year Total", t_cnt, money(t_cost)]

    elif block in ("purchase", "purchase_count"):

        days = [
            d for d in year_days
            if daily[d]["purchase_count"] > 0 or daily[d]["purchase"] > 0
        ]

        t_cnt = sum(daily[d]["purchase_count"] for d in days)
        t_amt = sum(daily[d]["purchase"] for d in days)

        if block == "purchase":

            columns = ["Date", "Items Purchased", "Total Purchase"]

            for d in days:
                r = daily[d]
                rows.append([fmt(d), r["purchase_count"], money(r["purchase"])])

            total_row = ["Year Total", t_cnt, money(t_amt)]

        else:

            columns = ["Date", "Items Purchased"]

            for d in days:
                rows.append([fmt(d), daily[d]["purchase_count"]])

            total_row = ["Year Total", t_cnt]

    elif block == "stock":

        columns = ["Date", "Stock Units", "Stock Value (Purchase Price)"]

        days = sorted(
            [d for d in stock_by_day if all_time or d.year == year],
            reverse=True
        )

        for d in days:

            u, v = stock_by_day[d]

            rows.append([fmt(d), u, money(v)])

    else:

        columns = ["Date", "Entries", "Total", "Paid", "Due"]

        days = [d for d in year_days if daily[d]["entries"] > 0]

        for d in days:

            r = daily[d]

            rows.append([
                fmt(d),
                r["entries"],
                money(r["due_total"]),
                money(r["due_paid"]),
                money(r["due_left"])
            ])

        total_row = [
            "Year Total",
            sum(daily[d]["entries"] for d in days),
            money(sum(daily[d]["due_total"] for d in days)),
            money(sum(daily[d]["due_paid"] for d in days)),
            money(sum(daily[d]["due_left"] for d in days))
        ]

    if total_row and all_time:
        total_row[0] = "All Time Total"

    return render_template(
        "history.html",
        block=block,
        blocks=HISTORY_BLOCKS,
        title=HISTORY_BLOCKS[block],
        year=year,
        all_time=all_time,
        years=years,
        columns=columns,
        rows=rows,
        total_row=total_row
    )


# =========================================================
# DARK LOOK (har page par same rang, extension ki zaroorat nahi)
# =========================================================

DARK_LOOK_CSS = """<style id="dark-look">
:root {
    --border: #6f6c66;
    --muted: #b4c0dc;
}

.container h1,
.page-head h1 {
    color: #22d3ee;
    text-shadow: 0 0 20px rgba(34,211,238,0.55);
}

.navbar-brand h2 {
    color: #67e8f9;
}
</style>
"""


@app.after_request
def add_dark_look(response):

    if (
        response.mimetype == "text/html"
        and not response.direct_passthrough
    ):

        html = response.get_data(as_text=True)

        if "</head>" in html and 'id="dark-look"' not in html:

            html = html.replace(
                "</head>",
                DARK_LOOK_CSS + "</head>",
                1
            )

            response.set_data(html)

    return response


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

with app.app_context():

    instance_folder = BASE_DIR / "instance"

    instance_folder.mkdir(exist_ok=True)

    db.create_all()

    fix_product_name_nullable()

    fix_user_email_column()

    fix_product_spec_columns()

    fix_soft_delete_columns()

    fix_invoice_payment_column()

    fix_invoice_item_imei2_column()

    fix_supplier_columns()

    backup_database()

    admin = User.query.first()

    if admin:
        # Purane admin user par email attach karne ke liye
        if not admin.email:
            admin.email = "admin@gmail.com"
            db.session.commit()
    else:
        admin = User(
            username="admin",
            email="admin@gmail.com",
            password=generate_password_hash("admin123"),
            role="admin"
        )

        db.session.add(admin)

        db.session.commit()


# =========================================================
# RUN APP
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )