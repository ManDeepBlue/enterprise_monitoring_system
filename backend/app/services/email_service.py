from email.message import EmailMessage
import aiosmtplib
from ..settings import settings


async def send_alert_email(subject: str, body: str):
    if not settings.smtp_user or not settings.smtp_password or not settings.alert_email_to:
        print("Email settings not configured")
        return

    msg = EmailMessage()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = settings.alert_email_to
    msg["Subject"] = subject
    msg.set_content(body)

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )

    print("Email alert sent successfully")