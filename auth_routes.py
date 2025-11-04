# ---------------------------------- Imports ----------------------------------
from flask import Blueprint, request, jsonify, Response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt, get_jwt_identity
)
from sqlalchemy import extract
from extensions import db
from models import User, TokenBlocklist, UserProfile, Transaction, Bill, Payment, Notification
from email_utils import send_otp_email
from email_validator import validate_email, EmailNotValidError
from datetime import datetime, timedelta,timezone
import random
import razorpay
import hmac
import hashlib
import json

# ---------------------------------- Blueprint Configuration ----------------------------------
auth_bp = Blueprint("auth_bp", __name__, url_prefix="/auth")
OTP_EXP_MINUTES = 5

# ---------------------------------- Razorpay Configuration ----------------------------------
RAZORPAY_KEY_ID = "rzp_test_RbDp1J1gZzApDr"
RAZORPAY_KEY_SECRET = "jq2LiXt7vEpgeL2zcdWbAAVp"
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# ---------------------------------- OTP Generator ----------------------------------
def _generate_otp():
    return f"{random.randint(100000, 999999):06d}"

# ---------------------------------- Check Email ----------------------------------
@auth_bp.route("/check-email", methods=["POST"])
def check_email():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"valid": False, "exists": False}), 400
    try:
        validate_email(email)
    except EmailNotValidError as e:
        return jsonify({"valid": False, "exists": False, "reason": str(e)}), 200
    user = User.query.filter_by(email=email).first()
    if user:
        if not user.is_verified:
            return jsonify({
                "valid": True,
                "exists": False,
                "note": "User exists but not verified, can re-register"
            }), 200
        else:
            return jsonify({"valid": True, "exists": True}), 200
    return jsonify({"valid": True, "exists": False}), 200

# ---------------------------------- User Registration ----------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "")
    username = data.get("username")
    if not email or not password or not username:
        return jsonify({"msg": "Email, password, and username required"}), 400
    try:
        validate_email(email)
    except EmailNotValidError as e:
        return jsonify({"msg": "Invalid email", "detail": str(e)}), 400
    if len(password) < 8:
        return jsonify({"msg": "Password must be at least 8 characters"}), 400
    existing_user = User.query.filter_by(email=email).first()
    if existing_user and existing_user.is_verified:
        return jsonify({"msg": "Email already registered"}), 409
    if existing_user and not existing_user.is_verified:
        otp = _generate_otp()
        existing_user.otp = otp
        existing_user.otp_expiry = datetime.utcnow() + timedelta(minutes=OTP_EXP_MINUTES)
        db.session.commit()
        send_otp_email(email, otp, expiry_minutes=OTP_EXP_MINUTES)
        return jsonify({"msg": "New OTP sent", "email": email}), 200
    hashed = generate_password_hash(password)
    user = User(email=email, username=username, password_hash=hashed, is_verified=False)
    db.session.add(user)
    db.session.commit()
    otp = _generate_otp()
    user.otp = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=OTP_EXP_MINUTES)
    db.session.commit()
    send_otp_email(email, otp, expiry_minutes=OTP_EXP_MINUTES)
    return jsonify({"msg": "Registered — OTP sent to email", "email": email}), 201

# ---------------------------------- Verify OTP ----------------------------------
@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    otp = (data.get("otp") or "").strip()
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"msg": "User not found"}), 404
    if not user.otp or user.otp != otp:
        return jsonify({"msg": "Invalid OTP"}), 400
    if datetime.utcnow() > user.otp_expiry:
        return jsonify({"msg": "OTP expired"}), 400
    user.is_verified = True
    user.otp = None
    user.otp_expiry = None
    db.session.commit()
    if not UserProfile.query.filter_by(user_id=user.id).first():
        profile = UserProfile(
            user_id=user.id,
            name=email.split("@")[0].capitalize(),
            plan="Free",
            next_invoice=None,
            total_payments=0,
            total_amount=0,
            balance=0.0
        )
        db.session.add(profile)
        db.session.commit()
    return jsonify({"msg": "Email verified & profile created"}), 200

# ---------------------------------- User Login ----------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"msg": "Invalid credentials"}), 401
    if not user.is_verified:
        return jsonify({"msg": "Please verify email before logging in"}), 403
    access = create_access_token(identity=str(user.email))
    refresh = create_refresh_token(identity=str(user.email))
    return jsonify({
        "msg": "Login successful",
        "access_token": access,
        "refresh_token": refresh,
        "role": "admin" if user.is_admin else "user"
    }), 200

# ---------------------------------- Token Refresh ----------------------------------
@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    new_access = create_access_token(identity=identity)
    return jsonify({"access_token": new_access}), 200

# ---------------------------------- Logout ----------------------------------
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    db.session.add(TokenBlocklist(jti=jti))
    db.session.commit()
    return jsonify({"msg": "Logged out"}), 200

# ---------------------------------- Dashboard Data ----------------------------------
@auth_bp.route("/dashboard/data", methods=["GET"])
@jwt_required()
def dashboard_data():
    try:
        user_email = get_jwt_identity()
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        profile = UserProfile.query.filter_by(user_id=user.id).first()
        current_bill = Bill.query.filter_by(user_id=user.id, status="Pending") \
                                 .order_by(Bill.created_at.desc()).first()
        upcoming_bills = Bill.query.filter_by(user_id=user.id, status="Pending") \
                                   .order_by(Bill.due_date.asc()).all()
        notifications = Notification.query.filter_by(user_id=user.id) \
                                          .order_by(Notification.created_at.desc()).limit(5).all()

        transactions = Transaction.query.filter_by(user_id=user.id) \
                                        .order_by(Transaction.id.desc()).all()

        recent_txn = []
        IST = timezone(timedelta(hours=5, minutes=30))
        for t in transactions:
            bill = Bill.query.get(t.bill_id) if t.bill_id else None
            recent_txn.append({
                "id": t.id,
                "date": t.created_at.strftime("%Y-%m-%d"),
                "time": t.created_at.replace(tzinfo=timezone.utc).astimezone(IST).strftime("%I:%M:%S %p"),
                "plan": bill.bill_type if bill else "N/A",
                "amount": float(t.amount),
                "status": t.status
            })

        dashboard = {
            "name": profile.name if profile else "User",
            "email": user.email,
            "username": user.username,
            "bill": {
                "id": current_bill.id if current_bill else None,
                "utility": current_bill.bill_type if current_bill else "No pending bills",
                "amount_due": float(current_bill.amount_due) if current_bill else 0.0,
                "due_date": current_bill.due_date if current_bill else "—",
                "status": current_bill.status if current_bill else "—"
            },
            "upcoming": [
                {
                    "id": b.id,
                    "utility": b.bill_type,
                    "amount_due": float(b.amount_due),
                    "due_date": b.due_date,
                    "status": b.status
                } for b in upcoming_bills
            ],
            "avg_spend": float(profile.total_amount / profile.total_payments)
                         if profile and profile.total_payments > 0 else 0.0,
            "saved_methods": ["Razorpay", "UPI", "Wallet"],
            "transactions": recent_txn,
            "notifications": [n.message for n in notifications]
        }

        return jsonify(dashboard), 200

    except Exception as e:
        print("Dashboard fetch error:", e)
        return jsonify({"error": "Something went wrong loading dashboard."}), 500

# ---------------------------------- Bill Payment ----------------------------------
@auth_bp.route("/bill/pay", methods=["POST"])
@jwt_required()
def pay_bill():
    try:
        user_email = get_jwt_identity()
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        data = request.get_json() or {}
        bill_id = data.get("bill_id")
        method = data.get("method", "UPI")
        confirm_payment = data.get("confirm_payment", False)
        if not bill_id:
            return jsonify({"error": "bill_id required"}), 400
        bill = Bill.query.filter_by(id=bill_id, user_id=user.id).first()
        if not bill:
            return jsonify({"error": "Bill not found"}), 404
        if bill.status == "Paid":
            return jsonify({"msg": "Bill already paid"}), 200

        today = datetime.utcnow().date()
        due_date = datetime.strptime(bill.due_date, "%Y-%m-%d").date()
        penalty = 10 * (today - due_date).days if today > due_date else 0
        total_amount = bill.amount_due + penalty if penalty else bill.amount_due

        if penalty > 0 and not confirm_payment:
            return jsonify({
                "msg": "Bill is overdue",
                "bill_type": bill.bill_type,
                "original_amount": float(bill.amount_due),
                "penalty": penalty,
                "total_amount": total_amount
            }), 200

        if penalty > 0:
            bill.amount_due = total_amount
            db.session.add(Notification(
                user_id=user.id,
                message=f"⚠️ Penalty of ₹{penalty} added for {bill.bill_type} bill."
            ))

        bill.status = "Paid"
        db.session.add(bill)

        payment = Payment(
            user_id=user.id,
            plan=bill.bill_type,
            amount=bill.amount_due,
            status="Paid",
            provider="UtilityPay",
            due_date=bill.due_date
        )
        db.session.add(payment)

        txn = Transaction(
            user_id=user.id,
            bill_id=bill.id,
            amount=bill.amount_due,
            method=method,
            status="Success"
        )
        db.session.add(txn)

        profile = UserProfile.query.filter_by(user_id=user.id).first()
        if profile:
            profile.total_payments = (profile.total_payments or 0) + 1
            profile.total_amount = (profile.total_amount or 0.0) + float(bill.amount_due)
            db.session.add(profile)

        db.session.add(Notification(
            user_id=user.id,
            message=f"{bill.bill_type} bill of ₹{bill.amount_due:.2f} paid successfully."
        ))

        db.session.commit()
        return jsonify({
            "msg": f"Payment successful{f' (Penalty ₹{penalty})' if penalty else ''}",
            "bill_id": bill.id,
            "original_amount": float(bill.amount_due) - penalty,
            "penalty": penalty,
            "total_amount": float(bill.amount_due),
            "payment": {
                "id": payment.id,
                "date": payment.created_at.strftime("%Y-%m-%d"),
                "plan": payment.plan,
                "amount": f"₹{payment.amount:.2f}",
                "status": payment.status
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        print("pay_bill error:", e)
        return jsonify({"error": "Failed to process payment"}), 500

# ---------------------------------- Generate Monthly Bills ----------------------------------
@auth_bp.route("/generate-bills", methods=["POST"])
@jwt_required()
def generate_bills():
    user_email = get_jwt_identity()
    admin = User.query.filter_by(email=user_email).first()
    if not admin or not admin.is_admin:
        return jsonify({"error": "Access denied. Admins only."}), 403
    try:
        users = User.query.filter_by(is_verified=True, is_admin=False).all()
        bill_types = ["Electricity", "Water", "Internet", "Gas"]
        now = datetime.utcnow()
        bills_created = 0
        for u in users:
            existing_bill = Bill.query.filter(
                Bill.user_id == u.id,
                extract('month', Bill.created_at) == now.month,
                extract('year', Bill.created_at) == now.year
            ).first()
            if existing_bill:
                continue
            for bt in bill_types:
                db.session.add(Bill(
                    user_id=u.id,
                    bill_type=bt,
                    amount_due=round(random.uniform(300, 1200), 2),
                    due_date=(now + timedelta(days=random.randint(5, 15))).strftime("%Y-%m-%d"),
                    status="Pending"
                ))
            db.session.add(Notification(
                user_id=u.id,
                message=f"New monthly bills have been generated for {now.strftime('%B %Y')}."
            ))
            bills_created += 1
        db.session.commit()
        return jsonify({"message": f"✅ Monthly bills generated for {bills_created} new users."}), 200
    except Exception as e:
        db.session.rollback()
        print("generate_bills error:", e)
        return jsonify({"error": f"Failed to generate bills: {str(e)}"}), 500

# ---------------------------------- Generate Custom Bill ----------------------------------
@auth_bp.route("/generate-custom-bill", methods=["POST"])
@jwt_required()
def generate_custom_bill():
    user_email = get_jwt_identity()
    admin = User.query.filter_by(email=user_email).first()
    if not admin or not admin.is_admin:
        return jsonify({"error": "Access denied. Admins only."}), 403
    data = request.get_json()
    target_email = data.get("email")
    bill_type = data.get("bill_type")
    amount_due = data.get("amount_due")
    due_date = data.get("due_date")
    if not all([target_email, bill_type, amount_due, due_date]):
        return jsonify({"error": "Missing required fields"}), 400
    user = User.query.filter_by(email=target_email, is_verified=True, is_admin=False).first()
    if not user:
        return jsonify({"error": "User not found or not verified"}), 404
    try:
        db.session.add(Bill(
            user_id=user.id,
            bill_type=bill_type,
            amount_due=float(amount_due),
            due_date=due_date,
            status="Pending"
        ))
        db.session.add(Notification(
            user_id=user.id,
            message=f"A new {bill_type} bill of ₹{amount_due} has been added."
        ))
        db.session.commit()
        return jsonify({"message": f"✅ {bill_type} bill added for {user.email}!"}), 200
    except Exception as e:
        db.session.rollback()
        print("generate_custom_bill error:", e)
        return jsonify({"error": f"Failed to generate custom bill: {str(e)}"}), 500

# ---------------------------------- Download Bills CSV ----------------------------------
@auth_bp.route("/download_bills_csv")
@jwt_required()
def download_bills_csv():
    user_email = get_jwt_identity()
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return "User not found", 404
    bills = Bill.query.filter_by(user_id=user.id).order_by(Bill.created_at.desc()).all()
    def generate():
        yield "ID,User ID,Bill Type,Amount Due,Due Date,Status,Created At\n"
        for b in bills:
            yield f'{b.id},{b.user_id},"{b.bill_type}",{b.amount_due:.2f},"{b.due_date}","{b.status}","{b.created_at.strftime("%Y-%m-%d")}"\n'
    return Response(generate(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=bills_history.csv"})

# ---------------------------------- Check Bill Penalty ----------------------------------
@auth_bp.route("/bill/check-penalty", methods=["POST"])
@jwt_required()
def check_penalty():
    data = request.get_json() or {}
    bill_id = data.get("bill_id")
    if not bill_id:
        return jsonify({"error": "bill_id required"}), 400

    user_email = get_jwt_identity()
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    bill = Bill.query.filter_by(id=bill_id, user_id=user.id).first()
    if not bill:
        return jsonify({"error": "Bill not found"}), 404

    today = datetime.utcnow().date()
    due_date = datetime.strptime(bill.due_date, "%Y-%m-%d").date()
    penalty = 0
    if today > due_date:
        days_overdue = (today - due_date).days
        penalty = 10 * days_overdue

    total_amount = float(bill.amount_due) + penalty

    return jsonify({
        "bill_type": bill.bill_type,
        "amount_due": float(bill.amount_due),
        "penalty": penalty,
        "total_amount": total_amount
    }), 200

# ---------------------------------- Record Failed Transaction ----------------------------------
@auth_bp.route("/bill/record-failed-transaction", methods=["POST"])
@jwt_required()
def record_failed_transaction():
    data = request.get_json() or {}
    bill_id = data.get("bill_id")
    amount = data.get("amount")
    method = data.get("method", "Razorpay")

    if not bill_id or amount is None:
        return jsonify({"error": "bill_id and amount required"}), 400

    user_email = get_jwt_identity()
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    bill = Bill.query.filter_by(id=bill_id, user_id=user.id).first()
    if not bill:
        return jsonify({"error": "Bill not found"}), 404

    txn = Transaction(
        user_id=user.id,
        bill_id=bill.id,
        amount=float(amount),
        method=method,
        status="Failed"
    )
    db.session.add(txn)
    db.session.commit()

    return jsonify({"msg": "Failed transaction recorded"}), 200

# ---------------------------------- Create Razorpay Order ----------------------------------
@auth_bp.route("/bill/create-order", methods=["POST"])
@jwt_required()
def create_razorpay_order():
    user_email = get_jwt_identity()
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    bill_id = data.get("bill_id")
    if not bill_id:
        return jsonify({"error": "bill_id required"}), 400

    bill = Bill.query.filter_by(id=bill_id, user_id=user.id).first()
    if not bill:
        return jsonify({"error": "Bill not found"}), 404

    today = datetime.utcnow().date()
    due_date = datetime.strptime(bill.due_date, "%Y-%m-%d").date()
    penalty = max(0, (today - due_date).days * 10)
    total_amount = float(bill.amount_due) + penalty

    razorpay_order = razorpay_client.order.create({
        "amount": int(total_amount * 100),
        "currency": "INR",
        "payment_capture": 1,
        "notes": {"bill_id": str(bill.id), "user_id": str(user.id)}
    })

    return jsonify({
        "order_id": razorpay_order["id"],
        "total_amount": total_amount,
        "currency": "INR",
        "key": RAZORPAY_KEY_ID,
        "bill_type": bill.bill_type,
        "penalty": penalty,
        "original_amount": float(bill.amount_due)
    }), 200

# ---------------------------------- Verify Razorpay Payment ----------------------------------
@auth_bp.route("/bill/verify-payment", methods=["POST"])
@jwt_required()
def verify_razorpay_payment():
    try:
        user_email = get_jwt_identity()
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json() or {}
        bill_id = data.get("bill_id")
        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_signature = data.get("razorpay_signature")

        if not bill_id:
            return jsonify({"error": "bill_id required"}), 400

        bill = Bill.query.filter_by(id=bill_id, user_id=user.id).first()
        if not bill:
            return jsonify({"error": "Bill not found"}), 404

        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        }

        try:
            if razorpay_signature:
                razorpay_client.utility.verify_payment_signature(params_dict)

            if bill.status != "Paid":
                bill.status = "Paid"
                db.session.add(bill)

                payment = Payment(
                    user_id=user.id,
                    plan=bill.bill_type,
                    amount=bill.amount_due,
                    status="Paid",
                    provider="Razorpay",
                    due_date=bill.due_date,
                    payment_id=razorpay_payment_id
                )
                db.session.add(payment)

                txn = Transaction(
                    user_id=user.id,
                    bill_id=bill.id,
                    amount=bill.amount_due,
                    method="Razorpay",
                    status="Success"
                )
                db.session.add(txn)

                profile = UserProfile.query.filter_by(user_id=user.id).first()
                if profile:
                    profile.total_payments = (profile.total_payments or 0) + 1
                    profile.total_amount = (profile.total_amount or 0.0) + float(bill.amount_due)
                    db.session.add(profile)

                notif = Notification(
                    user_id=user.id,
                    message=f"{bill.bill_type} bill of ₹{bill.amount_due:.2f} paid successfully via Razorpay."
                )
                db.session.add(notif)

            db.session.commit()
            return jsonify({"msg": "Payment successful via Razorpay", "bill_id": bill.id}), 200

        except razorpay.errors.SignatureVerificationError:
            txn = Transaction(
                user_id=user.id,
                bill_id=bill.id,
                amount=bill.amount_due,
                method="Razorpay",
                status="Failed"
            )
            db.session.add(txn)
            db.session.commit()
            return jsonify({"error": "Razorpay payment verification failed"}), 400

    except Exception as e:
        db.session.rollback()
        print("verify_razorpay_payment error:", e)
        try:
            txn = Transaction(
                user_id=user.id,
                bill_id=bill.id,
                amount=bill.amount_due,
                method="Razorpay",
                status="Failed"
            )
            db.session.add(txn)
            db.session.commit()
        except:
            pass
        return jsonify({"error": "Failed to verify payment"}), 500

