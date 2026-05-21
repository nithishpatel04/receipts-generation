from flask import Flask, render_template, request, redirect, url_for, abort, session, flash
import os
from datetime import datetime

# Database
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret")

# Use DATABASE_URL env var (Postgres) or default to SQLite for local/dev
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///orders.db")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -----------------------------
# Admin credentials (change here only)
# -----------------------------
# WARNING: Hardcoding credentials in source is intentional per your request
# and requires a code change + redeploy to update. For production, prefer
# environment variables or a secrets manager.
ADMIN_USER = "admin"
ADMIN_PASS = "secret"



class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    product = db.Column(db.String(200), nullable=False)
    material = db.Column(db.String(100), nullable=True)
    qty = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "OrderID": self.order_id,
            "Name": self.name,
            "Phone": self.phone,
            "Product": self.product,
            "Material": self.material,
            "Qty": self.qty,
            "Amount": self.amount,
            "Date": self.date_created.strftime("%Y-%m-%d %H:%M:%S")
        }




def generate_order_id():
    return "3DP-" + datetime.now().strftime("%Y%m%d%H%M%S")


@app.route("/")
def home():
    return render_template("form.html")


@app.route("/submit", methods=["POST"])
def submit():
    data = request.form

    order_id = generate_order_id()

    order = Order(
        order_id=order_id,
        name=data.get("name"),
        phone=data.get("phone"),
        product=data.get("product"),
        material=data.get("material"),
        qty=int(data.get("qty")),
        amount=float(data.get("amount"))
    )

    db.session.add(order)
    db.session.commit()

    return redirect(url_for("receipt", order_id=order_id))


@app.route("/receipt/<order_id>")
def receipt(order_id):
    order = Order.query.filter_by(order_id=order_id).first()
    if not order:
        abort(404)

    return render_template("receipt.html", order=order.to_dict())


# --- Simple admin auth via login page ---
def admin_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)

    return wrapper


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["admin_authenticated"] = True
            return redirect(url_for("admin"))
        flash("Invalid admin username or password.", "error")

    return render_template("login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_authenticated", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin():
    orders = Order.query.order_by(Order.date_created.desc()).all()
    return render_template("admin.html", orders=[o.to_dict() for o in orders])


if __name__ == "__main__":
    # Ensure DB tables are created within the application context
    with app.app_context():
        db.create_all()
    app.run(debug=True)