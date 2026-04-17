"""
Email Notification Service
--------------------------
Handles the delivery of alerts to configured administrative email addresses 
using asynchronous SMTP communication.
"""

from email.message import EmailMessage
import aiosmtplib
from ..settings import settings


async def send_alert_email(subject: str, body: str):
    """
    Send an email alert to the destination configured in system settings.
    
    This function initializes an asynchronous SMTP connection using provided
    credentials, starts TLS for security, and sends a standard EmailMessage.
    
    If critical SMTP settings (user, password, recipient) are missing, it 
    silently reports the issue to logs and returns.
    
    :param subject: The subject line of the email alert.
    :param body: The main content (body) of the email alert.
    """
    # Validation: Ensure minimum settings are present before attempting to send.
    if not settings.smtp_user or not settings.smtp_password or not settings.alert_email_to:
        print("Email settings not configured; alert email will not be sent.")
        return

    # Build the standard email message structure.
    msg = EmailMessage()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = settings.alert_email_to
    msg["Subject"] = subject
    msg.set_content(body)

    # Use aiosmtplib for non-blocking SMTP delivery.
    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )

    print(f"Email alert successfully sent to: {settings.alert_email_to}")