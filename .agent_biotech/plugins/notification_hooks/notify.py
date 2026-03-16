"""
Notification Hooks Plugin — Send alerts via Slack or email.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def validate_smtp_config() -> bool:
    """Check that all required SMTP environment variables are set.

    Logs a WARNING if any are missing so operators know before a run starts
    that email notifications are disabled.  Does NOT raise — the system
    degrades gracefully to Slack-only notifications.

    Returns:
        True if SMTP is fully configured, False otherwise.
    """
    required = ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "ALERT_EMAIL_TO"]
    missing = [name for name in required if not os.getenv(name, "")]
    if missing:
        logger.warning(
            "Email notifications disabled — missing SMTP environment variables: %s. "
            "Set them in your .env file to enable email alerts.",
            ", ".join(missing),
        )
        return False
    return True


_SMTP_READY = validate_smtp_config()


def send_slack_notification(message: str, webhook_url: str | None = None) -> bool:
    """Send a notification to Slack via webhook."""
    url = webhook_url or os.getenv("SLACK_WEBHOOK_URL", "")
    if not url:
        print("No Slack webhook URL configured")
        return False

    try:
        response = httpx.post(url, json={"text": message}, timeout=10)
        return response.status_code == 200
    except httpx.RequestError:
        logger.debug("Slack notification failed", exc_info=True)
        print("Slack notification failed. Check logs for details.")
        return False


def send_email_notification(
    subject: str,
    body: str,
    to_email: str | None = None,
) -> bool:
    """Send an email notification via SMTP."""
    if not _SMTP_READY:
        return False

    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    recipient = to_email or os.getenv("ALERT_EMAIL_TO", "")

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        return True
    except (smtplib.SMTPException, OSError):
        logger.debug("Email notification failed", exc_info=True)
        print("Email notification failed. Check logs for details.")
        return False


def notify_catalyst_alert(catalyst: dict) -> None:
    """Send alerts for an upcoming catalyst."""
    message = (
        f"🧬 Upcoming Catalyst Alert\n"
        f"Ticker: {catalyst.get('ticker', 'N/A')}\n"
        f"Product: {catalyst.get('product', 'N/A')}\n"
        f"Catalyst: {catalyst.get('catalyst_type', 'N/A')}\n"
        f"Date: {catalyst.get('date', 'N/A')}\n"
        f"Source: {catalyst.get('source_confidence', 'N/A')}"
    )

    send_slack_notification(message)
    send_email_notification(
        subject=f"Catalyst Alert: {catalyst.get('ticker', '')} — {catalyst.get('catalyst_type', '')}",
        body=message,
    )


def notify_approval(event: dict) -> None:
    """Send alerts for a new FDA approval."""
    message = (
        f"✅ New FDA Approval\n"
        f"Product: {event.get('product_name', 'N/A')}\n"
        f"Sponsor: {event.get('sponsor', 'N/A')}\n"
        f"Pathway: {event.get('pathway', 'N/A')}\n"
        f"Date: {event.get('event_date', 'N/A')}"
    )

    send_slack_notification(message)
    send_email_notification(
        subject=f"FDA Approval: {event.get('product_name', '')}",
        body=message,
    )


if __name__ == "__main__":
    # Test notification (dry run)
    test_catalyst = {
        "ticker": "TEST",
        "product": "Test Drug",
        "catalyst_type": "PDUFA Date",
        "date": "2026-04-15",
        "source_confidence": "primary",
    }
    print("Would send catalyst alert:")
    print(f"  {test_catalyst}")
