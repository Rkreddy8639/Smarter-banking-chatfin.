import os
from decimal import Decimal, InvalidOperation
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from sqlalchemy import text
from database.db import engine, SessionLocal, init_db
from models.fraud_detection import predict_fraud

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-development-secret")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

@app.before_request
def ensure_db():
    # Tables are created on startup; this also makes first-run setup straightforward.
    if not app.config.get("DB_READY"):
        init_db()
        app.config["DB_READY"] = True

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def current_user(db):
    return db.execute(text("SELECT id, full_name, email, account_number, balance, role FROM users WHERE id=:id"),
                      {"id": session["user_id"]}).mappings().first()

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name, a valid email, and a password of at least 8 characters.", "danger")
            return render_template("register.html")
        with SessionLocal() as db:
            exists = db.execute(text("SELECT id FROM users WHERE email=:email"), {"email": email}).first()
            if exists:
                flash("An account with that email already exists.", "warning")
                return render_template("register.html")
            account_number = "CHAT" + os.urandom(4).hex().upper()
            result = db.execute(text("""INSERT INTO users(full_name,email,password_hash,account_number,balance,role)
                VALUES(:name,:email,:password,:account,10000.00,'customer')"""),
                {"name": name, "email": email, "password": generate_password_hash(password), "account": account_number})
            db.commit()
            user_id = result.lastrowid
            db.execute(text("""INSERT INTO transactions(user_id, txn_type, amount, description, status)
                VALUES(:uid,'CREDIT',10000.00,'Welcome demo balance','SUCCESS')"""), {"uid": user_id})
            db.commit()
        flash("Registration successful. Your demo account starts with ₹10,000.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with SessionLocal() as db:
            user = db.execute(text("SELECT id,password_hash FROM users WHERE email=:email"), {"email": email}).mappings().first()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    with SessionLocal() as db:
        user = current_user(db)
        txns = db.execute(text("""SELECT id,txn_type,amount,description,status,created_at
            FROM transactions WHERE user_id=:uid ORDER BY created_at DESC LIMIT 5"""),
            {"uid": session["user_id"]}).mappings().all()
        totals = db.execute(text("""SELECT
            COALESCE(SUM(CASE WHEN txn_type='CREDIT' THEN amount ELSE 0 END),0) credits,
            COALESCE(SUM(CASE WHEN txn_type='DEBIT' THEN amount ELSE 0 END),0) debits
            FROM transactions WHERE user_id=:uid"""), {"uid": session["user_id"]}).mappings().first()
    return render_template("dashboard.html", user=user, transactions=txns, totals=totals)

@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    if request.method == "POST":
        recipient_account = request.form.get("recipient_account", "").strip().upper()
        description = request.form.get("description", "Demo fund transfer").strip()[:150]
        try:
            amount = Decimal(request.form.get("amount", "0"))
            if not amount.is_finite() or amount <= 0 or amount > Decimal("50000"):
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash("Enter a valid amount greater than ₹0 and not more than ₹50,000.", "danger")
            return redirect(url_for("transfer"))
        if recipient_account == "":
            flash("Enter the recipient account number.", "danger")
            return redirect(url_for("transfer"))
        # Atomic transaction with row locks. For local MySQL/InnoDB this prevents overspending.
        with engine.begin() as conn:
            sender = conn.execute(text("SELECT id,balance FROM users WHERE id=:id FOR UPDATE"),
                                  {"id": session["user_id"]}).mappings().first()
            recipient = conn.execute(text("SELECT id FROM users WHERE account_number=:acc FOR UPDATE"),
                                     {"acc": recipient_account}).mappings().first()
            if not recipient:
                flash("Recipient account was not found.", "danger")
                return redirect(url_for("transfer"))
            if recipient["id"] == sender["id"]:
                flash("You cannot transfer money to your own account.", "warning")
                return redirect(url_for("transfer"))
            if Decimal(str(sender["balance"])) < amount:
                flash("Insufficient demo balance.", "danger")
                return redirect(url_for("transfer"))
            fraud = predict_fraud(float(amount), description)
            if fraud["is_fraud"]:
                conn.execute(text("""INSERT INTO fraud_alerts(user_id,amount,reason,risk_score)
                    VALUES(:uid,:amount,:reason,:score)"""),
                    {"uid": sender["id"], "amount": amount, "reason": fraud["reason"], "score": fraud["risk_score"]})
                flash("Transfer held for review by the demo fraud checker. No money was moved.", "warning")
                return redirect(url_for("transfer"))
            conn.execute(text("UPDATE users SET balance=balance-:amt WHERE id=:uid"),
                         {"amt": amount, "uid": sender["id"]})
            conn.execute(text("UPDATE users SET balance=balance+:amt WHERE id=:uid"),
                         {"amt": amount, "uid": recipient["id"]})
            conn.execute(text("""INSERT INTO transactions(user_id,txn_type,amount,description,status,reference)
                VALUES(:uid,'DEBIT',:amt,:desc,'SUCCESS',:ref)"""),
                {"uid": sender["id"], "amt": amount, "desc": "To " + recipient_account + ": " + description,
                 "ref": os.urandom(6).hex().upper()})
            conn.execute(text("""INSERT INTO transactions(user_id,txn_type,amount,description,status,reference)
                VALUES(:uid,'CREDIT',:amt,:desc,'SUCCESS',:ref)"""),
                {"uid": recipient["id"], "amt": amount, "desc": "From " + str(sender["id"]) + ": " + description,
                 "ref": os.urandom(6).hex().upper()})
        flash("Demo transfer completed successfully.", "success")
        return redirect(url_for("dashboard"))
    return render_template("transfer.html")

@app.route("/transactions")
@login_required
def transactions():
    with SessionLocal() as db:
        txns = db.execute(text("""SELECT id,txn_type,amount,description,status,reference,created_at
            FROM transactions WHERE user_id=:uid ORDER BY created_at DESC"""),
            {"uid": session["user_id"]}).mappings().all()
    return render_template("transactions.html", transactions=txns)

@app.route("/chatbot", methods=["GET", "POST"])
@login_required
def chatbot():
    answer = None
    question = ""
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        q = question.lower()
        if any(k in q for k in ["balance", "money", "available"]):
            with SessionLocal() as db:
                u = current_user(db)
            answer = f"Your current demo balance is ₹{Decimal(str(u['balance'])):,.2f}. This is simulated project data."
        elif "transfer" in q or "send" in q:
            answer = "To make a demo transfer, open Transfer from the navigation bar, enter the recipient's Chatfin account number and amount, then submit."
        elif "fraud" in q or "security" in q:
            answer = "Chatfin checks demo transfers using simple risk rules. Large transfers or suspicious keywords can be held for review. This is an academic demonstration, not a bank-grade fraud system."
        elif "transaction" in q or "history" in q:
            answer = "Open Transaction History to view your recent credits and debits."
        elif "password" in q or "login" in q:
            answer = "Use your registered email and password. If login fails, check your email spelling. The demo app does not currently provide password reset."
        else:
            answer = "I can help with demo balance, transfers, transaction history, login, and fraud detection. Please ask about one of these topics."
    return render_template("chatbot.html", answer=answer, question=question)

@app.route("/api/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return jsonify({"status": "ok", "database": "connected"})
    except Exception:
        return jsonify({"status": "error", "database": "unavailable"}), 503

@app.route("/admin")
@login_required
def admin():
    with SessionLocal() as db:
        me = current_user(db)
        if me["role"] != "admin":
            flash("Admin access only.", "danger")
            return redirect(url_for("dashboard"))
        users = db.execute(text("SELECT id,full_name,email,account_number,balance FROM users ORDER BY id DESC")).mappings().all()
        alerts = db.execute(text("""SELECT f.id,u.full_name,f.amount,f.reason,f.risk_score,f.created_at
            FROM fraud_alerts f JOIN users u ON u.id=f.user_id ORDER BY f.created_at DESC LIMIT 50""")).mappings().all()
    return render_template("admin.html", users=users, alerts=alerts)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG", "0") == "1")
