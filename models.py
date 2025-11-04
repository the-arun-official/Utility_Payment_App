from extensions import db
from datetime import datetime, timezone

# ------------------ USER ------------------
class User(db.Model):
    username = db.Column(db.String(80), nullable=False) 
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(300), nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)


# ------------------ TOKEN BLOCKLIST ------------------
class TokenBlocklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

# ------------------ USER PROFILE ------------------
class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100))
    plan = db.Column(db.String(50), default="Free")
    balance = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    total_payments = db.Column(db.Integer, default=0)
    next_invoice = db.Column(db.String(20), default="0000-00-00")

# ------------------ PAYMENT HISTORY ------------------
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    plan = db.Column(db.String(50))
    amount = db.Column(db.Float)
    status = db.Column(db.String(20), default="None")
    provider = db.Column(db.String(50), default="Utility Service")
    payment_id = db.Column(db.String(100), nullable=True)
    due_date = db.Column(db.String(20), default="0000-00-00")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------ NOTIFICATIONS ------------------
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------ BILLS ------------------
class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    bill_type = db.Column(db.String(50)) 
    amount_due = db.Column(db.Float)
    due_date = db.Column(db.String(20))
    status = db.Column(db.String(20), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------ TRANSACTIONS ------------------
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'))
    amount = db.Column(db.Float)
    method = db.Column(db.String(30))
    status = db.Column(db.String(20), default="Success")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
