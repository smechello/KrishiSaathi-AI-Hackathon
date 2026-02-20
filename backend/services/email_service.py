"""Custom email service for KrishiSaathi — Gmail SMTP.

Sends verification emails, password-reset links, and welcome emails
using the app's own Gmail credentials instead of Supabase's built-in
email service.

Required env vars / Streamlit secrets::

    EMAIL_ADDRESS  — Gmail address (e.g. krishisaathi@gmail.com)
    EMAIL_PASSWORD — Gmail **App Password** (NOT your regular password)

To generate a Gmail App Password:
    1. Enable 2-Step Verification on your Google Account
    2. Go to https://myaccount.google.com/apppasswords
    3. Create a new App Password for "Mail"
    4. Copy the 16-char password into EMAIL_PASSWORD
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from backend.config import Config

logger = logging.getLogger(__name__)

# ── SMTP defaults (Gmail) ─────────────────────────────────────────────
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


class EmailService:
    """Send branded HTML emails via Gmail SMTP."""

    # ── status ────────────────────────────────────────────────────────

    @classmethod
    def is_configured(cls) -> bool:
        """``True`` when both EMAIL_ADDRESS and EMAIL_PASSWORD are set."""
        return bool(
            getattr(Config, "EMAIL_ADDRESS", None)
            and getattr(Config, "EMAIL_PASSWORD", None)
        )

    # ── public senders ────────────────────────────────────────────────

    @classmethod
    def send_verification_email(
        cls, to_email: str, full_name: str, token: str
    ) -> bool:
        """Send an email-verification link."""
        verify_url = f"{Config.APP_URL}?verify_token={token}"
        subject = "Welcome to KrishiSaathi — confirm your email"
        html = _verification_template(full_name or "Farmer", verify_url)
        return cls._send(to_email, subject, html)

    @classmethod
    def send_password_reset_email(
        cls, to_email: str, full_name: str, token: str
    ) -> bool:
        """Send a password-reset link."""
        reset_url = f"{Config.APP_URL}?reset_token={token}"
        subject = "Reset your KrishiSaathi password"
        html = _password_reset_template(full_name or "Farmer", reset_url)
        return cls._send(to_email, subject, html)

    @classmethod
    def send_welcome_email(cls, to_email: str, full_name: str) -> bool:
        """Send a welcome email after successful verification."""
        subject = "Your KrishiSaathi account is ready"
        html = _welcome_template(full_name or "Farmer")
        return cls._send(to_email, subject, html)

    # ── internal SMTP sender ─────────────────────────────────────────

    @classmethod
    def _send(cls, to: str, subject: str, html_body: str) -> bool:
        """Low-level SMTP send using Gmail STARTTLS."""
        if not cls.is_configured():
            logger.warning("Email not configured — skipping send to %s", to)
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"KrishiSaathi <{Config.EMAIL_ADDRESS}>"
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
                server.sendmail(Config.EMAIL_ADDRESS, to, msg.as_string())

            logger.info("Email sent to %s — %s", to, subject)
            return True
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", to, exc)
            return False


# ═══════════════════════════════════════════════════════════════════════
#  HTML email templates (inline CSS for maximum email-client compat)
# ═══════════════════════════════════════════════════════════════════════

_BASE_STYLE = """
    body { margin:0; padding:0; background:#f4f7f6; font-family: 'Segoe UI', Arial, sans-serif; }
    .container { max-width:520px; margin:40px auto; background:#ffffff; border-radius:16px;
                 box-shadow:0 4px 24px rgba(0,0,0,0.08); overflow:hidden; }
    .header { background: linear-gradient(135deg, #2E7D32, #43A047); padding:32px 24px;
              text-align:center; color:#fff; }
    .header h1 { margin:0; font-size:28px; font-weight:800; letter-spacing:-0.5px; }
    .header p { margin:6px 0 0; opacity:0.9; font-size:14px; }
    .body { padding:32px 28px; color:#333; line-height:1.7; font-size:15px; }
    .body h2 { color:#2E7D32; margin-top:0; font-size:20px; }
    .btn { display:inline-block; padding:14px 36px; background:#2E7D32; color:#ffffff !important;
           text-decoration:none; border-radius:10px; font-weight:700; font-size:15px;
           margin:20px 0; }
  .footer { padding:16px 28px; background:#f9faf9; text-align:left;
        font-size:12px; color:#7a7a7a; border-top:1px solid #eee; }
  .note { background:#f6f8f7; border-left:4px solid #2E7D32; padding:12px 16px;
      border-radius:0 8px 8px 0; margin:16px 0; font-size:13px; color:#2b2b2b; }
  .muted { color:#666; font-size:13px; }
"""


def _verification_template(name: str, url: str) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{_BASE_STYLE}</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>KrishiSaathi</h1>
    <p>AI Agricultural Advisory System</p>
  </div>
  <div class="body">
    <h2>Welcome to KrishiSaathi</h2>
    <p>Dear {name},</p>
    <p>
      Thank you for joining <strong>KrishiSaathi</strong> — your trusted companion for real-time mandi prices,
      crop insights, and agricultural intelligence.
    </p>
    <p>Please confirm your email address to activate your account.</p>
    <div style="text-align:center; margin: 20px 0;">
      <a href="{url}" class="btn" style="background-color:#2E7D32;">Confirm My Email</a>
    </div>
    <div class="note">
      This link expires in <strong>24 hours</strong>. If you did not create this account,
      you can safely ignore this email.
    </div>
    <p class="muted">
      If the button doesn't work, copy and paste this link in your browser:<br>
      <a href="{url}" style="color:#2E7D32;word-break:break-all">{url}</a>
    </p>
    <p>Happy Farming,<br><strong>Team KrishiSaathi</strong></p>
  </div>
  <div class="footer">
    <div><strong>KrishiSaathi</strong> — Empowering Farmers with Real-Time Market Intelligence.</div>
    <div>This is an automated message. Please do not reply directly to this email.</div>
  </div>
</div>
</body></html>"""


def _password_reset_template(name: str, url: str) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{_BASE_STYLE}</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>KrishiSaathi</h1>
    <p>AI Agricultural Advisory System</p>
  </div>
  <div class="body">
    <h2>Reset Your KrishiSaathi Password</h2>
    <p>Hello {name},</p>
    <p>We received a request to reset the password for your <strong>KrishiSaathi</strong> account.</p>
    <div style="text-align:center; margin: 20px 0;">
      <a href="{url}" class="btn" style="background-color:#C62828;">Reset Password</a>
    </div>
    <div class="note" style="border-left-color:#C62828;">
      This link expires in <strong>1 hour</strong>. If you did not request a password reset,
      please ignore this email — your account remains secure.
    </div>
    <p class="muted">
      If the button doesn't work, copy and paste this link in your browser:<br>
      <a href="{url}" style="color:#2E7D32;word-break:break-all">{url}</a>
    </p>
    <p>Stay Secure,<br><strong>Team KrishiSaathi</strong></p>
  </div>
  <div class="footer">
    <div><strong>KrishiSaathi</strong> — Empowering Farmers with Real-Time Market Intelligence.</div>
    <div>This is an automated message. Please do not reply directly to this email.</div>
  </div>
</div>
</body></html>"""


def _welcome_template(name: str) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{_BASE_STYLE}</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>KrishiSaathi</h1>
    <p>AI Agricultural Advisory System</p>
  </div>
  <div class="body">
    <h2>Your account is ready</h2>
    <p>Dear {name},</p>
    <p>
      Your email has been verified successfully, and your <strong>KrishiSaathi</strong> account is now active.
      You can sign in any time to explore mandi prices, crop guidance, schemes, and weather updates.
    </p>
    <div style="text-align:center; margin: 20px 0;">
      <a href="{Config.APP_URL}" class="btn" style="background-color:#2E7D32;">Open KrishiSaathi</a>
    </div>
    <div class="note">
      Security tip: KrishiSaathi will never ask you for your password by email.
    </div>
    <p>Regards,<br><strong>Team KrishiSaathi</strong></p>
  </div>
  <div class="footer">
    <div><strong>KrishiSaathi</strong> — Empowering Farmers with Real-Time Market Intelligence.</div>
    <div>This is an automated message. Please do not reply directly to this email.</div>
  </div>
</div>
</body></html>"""
