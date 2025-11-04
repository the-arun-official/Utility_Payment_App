# ----------------------------------File Header-------------------------------------------
# mailer.py
# Purpose: Handle sending OTP emails via Brevo (formerly Sendinblue) API.

# ----------------------------------Imports-------------------------------------------
import os
import requests

# ----------------------------------Send OTP Email Function-------------------------------------------
def send_otp_email(recipient_email: str, otp: str, expiry_minutes: int = 5) -> bool:
    BREVO_API_KEY = os.getenv("BREVO_API_KEY")
    MAIL_SENDER_NAME = os.getenv("MAIL_SENDER_NAME", "PaySub")
    MAIL_SENDER_EMAIL = os.getenv("MAIL_SENDER_EMAIL")

    # ----------------------------------Fallback for Development Mode-------------------------------------------
    if not BREVO_API_KEY or not MAIL_SENDER_EMAIL:
        print(f"[DEV] OTP for {recipient_email}: {otp} (expires in {expiry_minutes} minutes)")
        return True

    # ----------------------------------Preparing Brevo API Request-------------------------------------------
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    # ----------------------------------Email Content-------------------------------------------
    html = f"""
    <div style="font-family: Arial, sans-serif; line-height:1.4;">
      <h3>Verify your PaySub account</h3>
      <p>Your OTP: <strong style="font-size:18px">{otp}</strong></p>
      <p>This code will expire in {expiry_minutes} minutes.</p>
      <p>If you did not request this, ignore this email.</p>
    </div>
    """

    # ----------------------------------Sending Email Request-------------------------------------------
    payload = {
        "sender": {"name": MAIL_SENDER_NAME, "email": MAIL_SENDER_EMAIL},
        "to": [{"email": recipient_email}],
        "subject": "PaySub — Your verification code",
        "htmlContent": html
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    print("BREVO RESPONSE:", resp.status_code, resp.text)

    # ----------------------------------Return Status-------------------------------------------
    return resp.status_code in (200, 201)
