import smtplib
from email.mime.text import MIMEText

SMTP_USER = "admin@try-tradeos.com"
SMTP_PASS = "app_pass"


def send_cold_email(to_email, biz_name, city="British Columbia"):
    footer = "\n\n--\nReply STOP to unsubscribe.\nTrade-OS Systems, BC, Canada."
    msg = MIMEText(
        f"Hi {biz_name},\n\nWe help trades in {city} answer missed calls automatically. Want a demo?{footer}")
    msg['Subject'] = f"Missed calls in {city}?"
    msg['From'] = SMTP_USER
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    except:
        pass