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

    @classmethod
    def send_custom_email(
        cls,
        to_email: str,
        subject: str,
        heading: str,
        body_html: str,
        *,
        recipient_name: str = "Farmer",
        cta_text: str | None = None,
        cta_url: str | None = None,
        badge_text: str | None = None,
        badge_color: str = "#2E7D32",
    ) -> bool:
        """Send a beautifully styled custom email from the admin panel.

        Parameters
        ----------
        to_email : str
            Recipient email address.
        subject : str
            Email subject line.
        heading : str
            Large heading displayed in the email body.
        body_html : str
            HTML content for the email body (paragraphs, lists, etc.).
        recipient_name : str
            Name shown in greeting ("Dear {name},").
        cta_text : str | None
            Call-to-action button label (optional).
        cta_url : str | None
            Call-to-action button link (optional).
        badge_text : str | None
            Optional badge/tag shown above the heading (e.g. "NEW FEATURE").
        badge_color : str
            Hex color for the badge.
        """
        html = _custom_email_template(
            name=recipient_name,
            heading=heading,
            body_html=body_html,
            cta_text=cta_text,
            cta_url=cta_url,
            badge_text=badge_text,
            badge_color=badge_color,
        )
        return cls._send(to_email, subject, html)

    @classmethod
    def send_broadcast(
        cls,
        recipients: list[dict],
        subject: str,
        heading: str,
        body_html: str,
        *,
        cta_text: str | None = None,
        cta_url: str | None = None,
        badge_text: str | None = None,
        badge_color: str = "#2E7D32",
    ) -> dict:
        """Broadcast an email to multiple recipients.

        Parameters
        ----------
        recipients : list[dict]
            Each dict has ``email`` and optional ``full_name``.

        Returns
        -------
        dict with ``sent``, ``failed``, ``errors`` keys.
        """
        sent = 0
        failed = 0
        errors: list[str] = []

        for r in recipients:
            email = r.get("email", "")
            name = r.get("full_name") or "Farmer"
            if not email:
                continue
            ok = cls.send_custom_email(
                to_email=email,
                subject=subject,
                heading=heading,
                body_html=body_html,
                recipient_name=name,
                cta_text=cta_text,
                cta_url=cta_url,
                badge_text=badge_text,
                badge_color=badge_color,
            )
            if ok:
                sent += 1
            else:
                failed += 1
                errors.append(email)

        return {"sent": sent, "failed": failed, "errors": errors}

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


# ═══════════════════════════════════════════════════════════════════════
#  Custom email template — uses SAME design as auth emails (_BASE_STYLE)
# ═══════════════════════════════════════════════════════════════════════


def _custom_email_template(
    name: str,
    heading: str,
    body_html: str,
    cta_text: str | None = None,
    cta_url: str | None = None,
    badge_text: str | None = None,
    badge_color: str = "#2E7D32",
) -> str:
    """Generate a custom email using the same beautiful template as auth emails."""
    badge_block = ""
    if badge_text:
        badge_block = (
            f'<div style="display:inline-block;padding:4px 14px;border-radius:20px;'
            f'background:{badge_color};color:#fff;font-size:11px;font-weight:700;'
            f'letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;">'
            f'{badge_text}</div><br>'
        )

    cta_block = ""
    if cta_text and cta_url:
        cta_block = (
            f'<div style="text-align:center; margin: 20px 0;">'
            f'<a href="{cta_url}" class="btn" style="background-color:#2E7D32;">{cta_text}</a>'
            f'</div>'
        )

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{_BASE_STYLE}</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>KrishiSaathi</h1>
    <p>AI Agricultural Advisory System</p>
  </div>
  <div class="body">
    {badge_block}
    <h2>{heading}</h2>
    <p>Dear {name},</p>
    {body_html}
    {cta_block}
    <div class="note">
      Thank you for being part of the KrishiSaathi community. Together, we're
      empowering Indian agriculture with AI-driven insights.
    </div>
    <p>Happy Farming,<br><strong>Team KrishiSaathi</strong></p>
  </div>
  <div class="footer">
    <div><strong>KrishiSaathi</strong> &mdash; Empowering Farmers with Real-Time Market Intelligence.</div>
    <div>This is an automated message. Please do not reply directly to this email.</div>
  </div>
</div>
</body></html>"""


# ═══════════════════════════════════════════════════════════════════════
#  Pre-loaded email templates for admin broadcasts
# ═══════════════════════════════════════════════════════════════════════

EMAIL_TEMPLATES: list[dict] = [
    {
        "id": "welcome_back",
        "name": "Welcome Back — We Miss You!",
        "subject": "We miss you at KrishiSaathi!",
        "heading": "We Miss You!",
        "badge_text": "COME BACK",
        "badge_color": "#FF6F00",
        "body_html": """
        <p>It's been a while since you last visited KrishiSaathi, and a lot has changed!</p>
        <div class="note">
          Since your last visit, we've added:<br>
          <strong>Voice support</strong> in 10 Indian languages,
          <strong>real-time mandi prices</strong>, and
          <strong>AI-powered crop disease diagnosis</strong> via photo.
        </div>
        <p>Your personalized farming insights are waiting. Just ask a question — type it,
        speak it, or send a crop photo!</p>
        """,
        "cta_text": "Open KrishiSaathi Now",
        "cta_url": "{APP_URL}",
    },
    {
        "id": "new_feature_voice",
        "name": "New Feature — Voice & Telegram",
        "subject": "NEW: Talk to KrishiSaathi in your language!",
        "heading": "Voice Support is Here!",
        "badge_text": "NEW FEATURE",
        "badge_color": "#1565C0",
        "body_html": """
        <p>Great news! KrishiSaathi now supports <strong>voice input and output</strong> in
        all 10 major Indian languages.</p>
        <ul>
          <li>Click the mic button and ask your question aloud</li>
          <li>Get responses read back to you in your language</li>
          <li>Works on web and our new <strong>Telegram bot</strong>: <a href="https://t.me/Krishi_Saathi_bot">@Krishi_Saathi_bot</a></li>
        </ul>
        <p>Try our Telegram bot — send text, voice messages, or crop photos directly from your phone!</p>
        """,
        "cta_text": "Try on Telegram",
        "cta_url": "https://t.me/Krishi_Saathi_bot",
    },
    {
        "id": "mandi_prices",
        "name": "Daily Mandi Prices Alert",
        "subject": "Today's Mandi Prices — KrishiSaathi",
        "heading": "Today's Market Update",
        "badge_text": "MANDI PRICES",
        "badge_color": "#E65100",
        "body_html": """
        <p>Stay ahead of the market! Here's a quick look at today's mandi price trends:</p>
        <div class="note">
          Ask KrishiSaathi: <em>"What is today's price of wheat in my area?"</em>
          or <em>"Best mandi to sell tomatoes near me"</em> for personalized, real-time quotes.
        </div>
        <p>KrishiSaathi pulls live data from government mandi APIs to give you the most
        accurate prices — so you can sell at the right time, at the right place.</p>
        """,
        "cta_text": "Check Prices Now",
        "cta_url": "{APP_URL}",
    },
    {
        "id": "crop_doctor",
        "name": "Crop Doctor — Photo Diagnosis",
        "subject": "Is your crop sick? Send us a photo!",
        "heading": "AI Crop Doctor",
        "badge_text": "CROP HEALTH",
        "badge_color": "#2E7D32",
        "body_html": """
        <p>Did you know KrishiSaathi can <strong>diagnose crop diseases from a photo</strong>?</p>
        <ul>
          <li>Take a close-up photo of the affected leaf or plant</li>
          <li>Upload it on the web app or send it to our Telegram bot</li>
          <li>Get instant diagnosis + treatment recommendations</li>
        </ul>
        <div class="note">
          Our AI has been trained on thousands of crop diseases across major Indian crops
          including rice, wheat, cotton, tomato, potato, and more.
        </div>
        <p>Early detection saves crops — try it today!</p>
        """,
        "cta_text": "Diagnose Your Crop",
        "cta_url": "{APP_URL}",
    },
    {
        "id": "govt_schemes",
        "name": "Government Schemes You May Be Missing",
        "subject": "Are you getting all the benefits you deserve?",
        "heading": "Government Schemes for Farmers",
        "badge_text": "SCHEMES",
        "badge_color": "#6A1B9A",
        "body_html": """
        <p>The Indian government offers <strong>dozens of schemes</strong> specifically
        for farmers — subsidies, insurance, loans, and direct benefit transfers.</p>
        <p>Many farmers miss out simply because they don't know about them. KrishiSaathi
        has a comprehensive database of active schemes and can tell you:</p>
        <ul>
          <li>Which schemes you're eligible for based on your crop and location</li>
          <li>How and where to apply</li>
          <li>Important deadlines</li>
          <li>Required documents</li>
        </ul>
        <div class="note">
          Just ask: <em>"What government schemes are available for rice farmers in Telangana?"</em>
        </div>
        """,
        "cta_text": "Explore Schemes",
        "cta_url": "{APP_URL}",
    },
    {
        "id": "weather_alert",
        "name": "Weather Advisory",
        "subject": "Weather Advisory — Plan Your Farm Activities",
        "heading": "Weather Advisory for Farmers",
        "badge_text": "WEATHER ALERT",
        "badge_color": "#D84315",
        "body_html": """
        <p>Weather conditions are changing! Make sure you're prepared.</p>
        <p>KrishiSaathi provides <strong>hyper-local weather forecasts</strong> tailored
        for farming activities:</p>
        <ul>
          <li>5-day forecast with temperature, humidity, and rainfall</li>
          <li>Best days for sowing, spraying, and harvesting</li>
          <li>Frost, heatwave, and heavy rain warnings</li>
          <li>Soil moisture recommendations</li>
        </ul>
        <div class="note">
          Ask: <em>"Should I irrigate my wheat field this week?"</em> — and get an
          AI-powered recommendation based on your local weather data.
        </div>
        """,
        "cta_text": "Check Weather Now",
        "cta_url": "{APP_URL}",
    },
    {
        "id": "feedback_survey",
        "name": "We'd Love Your Feedback",
        "subject": "Help us improve KrishiSaathi — 2 min survey",
        "heading": "Your Feedback Matters",
        "badge_text": "SURVEY",
        "badge_color": "#00695C",
        "body_html": """
        <p>KrishiSaathi is built <strong>for farmers, by listening to farmers</strong>.</p>
        <p>We'd love to hear from you:</p>
        <ul>
          <li>What features do you use the most?</li>
          <li>What would you like us to add next?</li>
          <li>How has KrishiSaathi helped your farming?</li>
        </ul>
        <p>Your answers help us build a better tool for millions of Indian farmers.
        It only takes 2 minutes!</p>
        <div class="note">
          Every piece of feedback directly shapes our next update. Your voice matters.
        </div>
        """,
        "cta_text": "Share Feedback",
        "cta_url": "{APP_URL}",
    },
    {
        "id": "soil_health",
        "name": "Soil Health Tips",
        "subject": "Improve your soil, improve your yield",
        "heading": "Soil Health Guide",
        "badge_text": "SOIL TIPS",
        "badge_color": "#4E342E",
        "body_html": """
        <p>Healthy soil = healthy crops = better income. Here are some tips:</p>
        <ul>
          <li><strong>Get your soil tested</strong> — Ask KrishiSaathi where the nearest
          soil testing lab is and what to test for</li>
          <li><strong>Crop rotation</strong> — Alternate between cereals and legumes to
          naturally replenish nitrogen</li>
          <li><strong>Organic matter</strong> — Add compost or green manure to improve
          soil structure and water retention</li>
          <li><strong>Micronutrients</strong> — Zinc and boron deficiencies are common
          but easily fixable</li>
        </ul>
        <div class="note">
          Ask our AI Soil Expert: <em>"What fertilizer should I use for my sandy loam soil
          to grow tomatoes?"</em>
        </div>
        """,
        "cta_text": "Ask Soil Expert",
        "cta_url": "{APP_URL}",
    },
    {
        "id": "app_update_march_2026",
        "name": "🚀 Major App Update — March 2026",
        "subject": "Big Update: 3 Powerful New Features Added to KrishiSaathi!",
        "heading": "Exciting New Features Just Launched!",
        "badge_text": "MAJOR UPDATE",
        "badge_color": "#1565C0",
        "body_html": """
        <p>We've been working hard to make KrishiSaathi even more useful for you,
        and today we're launching <strong>3 powerful new features</strong>!</p>

        <div class="note">
          <strong>🌾 Meri Fasal — Smart Farm Diary &amp; AI Daily Planner</strong><br>
          Register your fields, track crop growth stages in real-time with visual
          progress bars, log every farming activity (sowing, irrigation, fertilizer,
          harvest), and get a personalised <em>AI Daily Action Plan</em> that tells
          you exactly what to do today based on your crops.
        </div>

        <div class="note">
          <strong>💹 Profit &amp; Loss Calculator</strong><br>
          Full economics data for 15 Telangana crops — see cost breakdowns, compare
          crop profitability side-by-side, and get an AI Financial Advisor that builds
          a custom budget plan for your farm.
        </div>

        <div class="note">
          <strong>📅 Crop Calendar &amp; Seasonal Planner</strong><br>
          Visual Gantt chart showing sowing-to-harvest timelines, "What to Plant Now"
          recommendations based on the current month, and a detailed variety guide
          for every major crop.
        </div>

        <p>All features support <strong>Telugu, Hindi, and English</strong> with
        voice input and output.</p>

        <p>Log in now to explore what's new — and don't forget to try the
        <strong>"Load Demo Farm"</strong> button in Meri Fasal to see it in action!
        </p>
        """,
        "cta_text": "Explore New Features",
        "cta_url": "{APP_URL}",
    },
]
