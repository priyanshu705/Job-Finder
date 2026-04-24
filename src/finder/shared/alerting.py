"""
src/finder/shared/alerting.py
-----------------------------
Lightweight alerting system using free services.
"""

import os
import smtplib
import urllib.request
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from finder.shared.logger import get_logger

log = get_logger("alerting")

ALERT_LEVELS = {"warning", "error", "critical"}

def send_telegram(message: str) -> bool:
    token   = os.getenv("TELEGRAM_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        log.debug("Telegram not configured — skipping")
        return False

    try:
        url  = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id":    chat_id,
            "text":       message,
            "parse_mode": "Markdown",
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                log.info("Telegram alert sent")
                return True
    except Exception as exc:
        log.warning(f"Telegram alert failed: {exc}")
    return False

def send_email(subject: str, body: str) -> bool:
    sender   = os.getenv("ALERT_EMAIL", "")
    password = os.getenv("ALERT_EMAIL_PASSWORD", "")
    receiver = os.getenv("ALERT_RECEIVER", sender)

    if not sender or not password:
        log.debug("Email alerting not configured — skipping")
        return False

    try:
        msg            = MIMEMultipart()
        msg["From"]    = sender
        msg["To"]      = receiver
        msg["Subject"] = f"[Finder] {subject}"
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(msg)

        log.info(f"Email alert sent: {subject}")
        return True
    except Exception as exc:
        log.warning(f"Email alert failed: {exc}")
    return False

def alert(subject: str, body: str, level: str = "info") -> bool:
    if level not in ALERT_LEVELS:
        return False

    emoji = {
        "warning":  "⚠️",
        "error":    "🔴",
        "critical": "🚨",
    }.get(level, "ℹ️")

    full_msg = f"{emoji} *{subject}*\n\n{body}"
    log.warning(f"ALERT [{level}]: {subject}")

    if send_telegram(full_msg):
        return True

    return send_email(subject, body)

def send_daily_summary(stats: dict) -> bool:
    body = (
        f"📊 *Daily Run Summary*\n\n"
        f"Applied:      {stats.get('total_applied', 0)}\n"
        f"Failed:       {stats.get('total_failed', 0)}\n"
        f"Success Rate: {stats.get('success_rate', '0%')}\n"
        f"Duration:     {stats.get('elapsed_minutes', 0)} minutes\n"
        f"Mode:         {stats.get('behavior_mode', 'normal')}\n"
        f"Per Platform: {stats.get('per_platform', {})}"
    )
    return alert("Daily Run Complete", body, level="warning")
