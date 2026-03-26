import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from core.config import SENDGRID_API_KEY, EMAIL_FROM, FRONTEND_URL

logger = logging.getLogger(__name__)


async def send_email(to_email: str, subject: str, html_content: str):
    if not SENDGRID_API_KEY:
        logger.warning("SendGrid API key not configured, skipping email")
        return False
    try:
        message = Mail(from_email=EMAIL_FROM, to_emails=to_email, subject=subject, html_content=html_content)
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


async def send_verification_email(email: str, name: str, token: str):
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #3B82F6, #10B981); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0;">CursorCode AI</h1>
        </div>
        <div style="padding: 30px; background: #f8f9fa;">
            <h2 style="color: #333;">Verify your email, {name}!</h2>
            <p style="color: #666;">Thanks for signing up. Please verify your email address.</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verify_url}" style="background: #3B82F6; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                    Verify Email Address
                </a>
            </div>
        </div>
    </div>"""
    return await send_email(email, "Verify your CursorCode AI account", html_content)


async def send_welcome_email(email: str, name: str):
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #3B82F6, #10B981); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0;">Welcome to CursorCode AI!</h1>
        </div>
        <div style="padding: 30px; background: #f8f9fa;">
            <h2 style="color: #333;">You're all set, {name}!</h2>
            <p style="color: #666;">Your email has been verified. Start building with AI.</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{FRONTEND_URL}/dashboard" style="background: #3B82F6; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                    Start Building
                </a>
            </div>
        </div>
    </div>"""
    return await send_email(email, "Welcome to CursorCode AI", html_content)
