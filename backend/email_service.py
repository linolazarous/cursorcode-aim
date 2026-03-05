"""
CursorCode AI - Email Service
Send emails via SendGrid
"""

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")

def send_email(to_email: str, subject: str, html_content: str):
    if not SENDGRID_API_KEY:
        return
    message = Mail(
        from_email=EMAIL_FROM,
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    sg.send(message)
