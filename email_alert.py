import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

GMAIL_SENDER_EMAIL = os.getenv("GMAIL_SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
    

# ── Email template ────────────────────────────────────────────────────────────

def build_alert_email_html(
    product_title: str,
    current_price: float,
    target_price: float,
    product_url: str,
) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0; padding:0; background-color:#f4f4f4; font-family:Arial,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
                <td align="center" style="padding:40px 0;">
                    <table width="600" cellpadding="0" cellspacing="0"
                           style="background:#ffffff; border-radius:8px;
                                  box-shadow:0 2px 8px rgba(0,0,0,0.1);">

                        <!-- Header -->
                        <tr>
                            <td style="background:#2874f0; padding:24px 32px;
                                       border-radius:8px 8px 0 0;">
                                <h1 style="margin:0; color:#ffffff; font-size:22px;">
                                    🎉 Price Drop Alert!
                                </h1>
                            </td>
                        </tr>

                        <!-- Body -->
                        <tr>
                            <td style="padding:32px;">
                                <p style="color:#333333; font-size:16px; margin:0 0 16px;">
                                    Good news! A product you are tracking has
                                    dropped to your target price.
                                </p>

                                <p style="color:#555555; font-size:14px;
                                          margin:0 0 24px; font-style:italic;">
                                    {product_title}
                                </p>

                                <!-- Price comparison box -->
                                <table width="100%" cellpadding="0" cellspacing="0"
                                       style="background:#f8f9fa; border-radius:6px;
                                              margin-bottom:24px;">
                                    <tr>
                                        <td align="center" style="padding:20px;">
                                            <p style="margin:0 0 8px; color:#888888;
                                                      font-size:13px; text-transform:uppercase;
                                                      letter-spacing:1px;">
                                                Current Price
                                            </p>
                                            <p style="margin:0; color:#2ecc71;
                                                      font-size:36px; font-weight:bold;">
                                                &#8377;{current_price:,.0f}
                                            </p>
                                        </td>
                                        <td align="center"
                                            style="padding:20px; border-left:1px solid #e0e0e0;">
                                            <p style="margin:0 0 8px; color:#888888;
                                                      font-size:13px; text-transform:uppercase;
                                                      letter-spacing:1px;">
                                                Your Target
                                            </p>
                                            <p style="margin:0; color:#e74c3c;
                                                      font-size:36px; font-weight:bold;">
                                                &#8377;{target_price:,.0f}
                                            </p>
                                        </td>
                                    </tr>
                                </table>

                                <!-- Savings callout -->
                                <p style="color:#2ecc71; font-size:15px;
                                          font-weight:bold; text-align:center;
                                          margin:0 0 24px;">
                                    You save &#8377;{target_price - current_price:,.0f}
                                    below your target!
                                </p>

                                <!-- CTA button -->
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center">
                                            <a href="{product_url}"
                                               style="display:inline-block;
                                                      background:#2874f0;
                                                      color:#ffffff;
                                                      padding:14px 32px;
                                                      border-radius:4px;
                                                      text-decoration:none;
                                                      font-size:16px;
                                                      font-weight:bold;">
                                                Buy Now on Flipkart
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="padding:16px 32px;
                                       border-top:1px solid #eeeeee;">
                                <p style="margin:0; color:#aaaaaa; font-size:12px;
                                          text-align:center;">
                                    You are receiving this because you set up a
                                    price alert on Flipkart Price Tracker.
                                </p>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
def build_alert_email_plain(
    product_title: str,
    current_price: float,
    target_price: float,
    product_url: str,
) -> str:
    return (
        f"Price Drop Alert!\n\n"
        f"Good news! A product you are tracking has dropped to your target price.\n\n"
        f"Product: {product_title}\n"
        f"Current Price: Rs.{current_price:,.0f}\n"
        f"Your Target:   Rs.{target_price:,.0f}\n"
        f"You save:      Rs.{target_price - current_price:,.0f} below your target!\n\n"
        f"Buy now: {product_url}\n\n"
        f"You are receiving this because you set up a price alert "
        f"on Flipkart Price Tracker."
    )


# ── Send function ─────────────────────────────────────────────────────────────

def send_price_alert(
    product_title: str,
    current_price: float,
    target_price: float,
    product_url: str,
    recipient_email: str,
) -> bool:
    """
    Send a price drop alert email via Gmail SMTP.
    Works with any recipient email address.
    Returns True if sent successfully, False otherwise.
    """
    if not GMAIL_SENDER_EMAIL or not GMAIL_APP_PASSWORD:
        logger.error(
            "GMAIL_SENDER_EMAIL or GMAIL_APP_PASSWORD not set in .env"
        )
        return False

    if not recipient_email:
        logger.error("No recipient email provided")
        return False

    try:
        # Build the email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = (
            f"Price Drop: {product_title[:60]} "
            f"is now ₹{current_price:,.0f}"
        )
        msg["From"] = f"Flipkart Price Tracker <{GMAIL_SENDER_EMAIL}>"
        msg["To"] = recipient_email
        msg["Date"] = formatdate(localtime=True)           
        msg["Message-ID"] = make_msgid(domain="gmail.com") 
        
        plain_body = build_alert_email_plain(
            product_title=product_title,
            current_price=current_price,
            target_price=target_price,
            product_url=product_url,
        )
        html_body = build_alert_email_html(
            product_title=product_title,
            current_price=current_price,
            target_price=target_price,
            product_url=product_url,
        )
        msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Send via Gmail SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER_EMAIL, GMAIL_APP_PASSWORD)
            server.sendmail(
                GMAIL_SENDER_EMAIL,
                recipient_email,
                msg.as_string(),
            )

        logger.info(
            f"Alert email sent to {recipient_email} "
            f"for '{product_title}'"
        )
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Gmail authentication failed. Make sure you are using "
            "an App Password, not your regular Gmail password."
        )
        return False

    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")
        return False