import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
ADMIN_NOTIFICATION_EMAIL = os.getenv("ADMIN_NOTIFICATION_EMAIL")

async def send_admin_notification(company_data: dict):
    if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, ADMIN_NOTIFICATION_EMAIL]):
        print("⚠️ SMTP settings missing. Skipping email notification.")
        return

    subject = "New Company Registration"
    body = f"""
    A new company has registered:\n
    Name: {company_data.get('name')}
    Phone Number ID: {company_data.get('phone_number_id')}
    Language: {company_data.get('language')}
    Tone: {company_data.get('tone')}
    AI Prompt: {company_data.get('ai_prompt')}\n
    (Tokens and secrets are safely stored encrypted.)
    """

    message = MIMEMultipart()
    message["From"] = SMTP_USERNAME
    message["To"] = ADMIN_NOTIFICATION_EMAIL
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, ADMIN_NOTIFICATION_EMAIL, message.as_string())
        print("✅ Admin notification email sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send admin notification: {e}")
