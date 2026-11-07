import logging
import resend
from app.core.config import settings

logger = logging.getLogger(__name__)


def send_verification_email(email: str, token: str, first_name: str | None = None) -> bool:
    """
    Sends an email verification link using Resend.
    If RESEND_API_KEY is not configured, logs a warning and prints the token to console.
    """
    verify_url = f"{settings.FRONTEND_URL}/verify?token={token}"
    greeting = f"Hello {first_name}," if first_name else "Hello,"
    
    if not settings.RESEND_API_KEY:
        logger.warning(
            f"[EMAIL MOCK] RESEND_API_KEY not configured. Mock verification email for {email}: {verify_url}"
        )
        return False

    try:
        resend.api_key = settings.RESEND_API_KEY
        params: resend.Emails.SendParams = {
            "from": settings.EMAIL_FROM,
            "to": [email],
            "subject": "Verify your VEX IAM Account",
            "html": f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f17; color: #f3f4f6; padding: 40px; border-radius: 8px;">
                <div style="max-width: 500px; margin: 0 auto; background: #111827; padding: 32px; border-radius: 12px; border: 1px solid #1f2937;">
                    <h2 style="color: #6366f1; margin-top: 0;">VEX IAM Verification</h2>
                    <p style="font-size: 16px; color: #9ca3af;">{greeting}</p>
                    <p style="font-size: 15px; color: #d1d5db; line-height: 1.5;">
                        Thank you for registering your global identity with VEX IAM. Please verify your email address to activate your account and access organizations and POS licensing.
                    </p>
                    <div style="margin: 32px 0; text-align: center;">
                        <a href="{verify_url}" style="background-color: #4f46e5; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block;">
                            Verify Email Address
                        </a>
                    </div>
                    <p style="font-size: 13px; color: #6b7280; word-break: break-all;">
                        If the button above does not work, copy and paste this URL into your browser:<br/>
                        <a href="{verify_url}" style="color: #818cf8;">{verify_url}</a>
                    </p>
                    <hr style="border: 0; border-top: 1px solid #1f2937; margin: 24px 0;" />
                    <p style="font-size: 12px; color: #4b5563; margin-bottom: 0;">
                        © 2026 VEX IAM. All rights reserved.
                    </p>
                </div>
            </div>
            """,
        }
        response = resend.Emails.send(params)
        logger.info(f"Verification email sent to {email}. Resend ID: {response.get('id')}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email via Resend to {email}: {str(e)}")
        return False
