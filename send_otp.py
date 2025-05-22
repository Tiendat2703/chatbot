import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr





def send_otp(receiver_email):
    otp_code = str(random.randint(100000, 999999))

    sender_email = "unix2425@gmail.com"
    sender_password = "ktqv rlew yyix ywwu" 

    html_content = f"""
    <html>
    <body>
        <p>Dear {receiver_email.split('@')[0].capitalize()},</p>
        <p>Here is your <strong>OTP code</strong> for verifying your email address:</p>
        <h2 style="color:#2e6c80;">{otp_code}</h2>
        <p><i>Note:</i> Please do not share this code with anyone for security reasons.</p>
        <br>
        <p>Best regards,<br>UniX Support Team</p>
        <hr>
        <small>This is an automated message. Please do not reply.</small>
    </body>
    </html>
    """

    plain_text = f"""Dear user,

    Your OTP code is: {otp_code}

    Please do not share this code with anyone.

    Best regards,
    UniX Support Team
    """



    message = MIMEMultipart("alternative")
    message['Subject'] = "Your OTP Verification Code"
    message['From'] = formataddr(("UniX Support", sender_email))
    message['To'] = receiver_email

    message.attach(MIMEText(plain_text, "plain"))
    message.attach(MIMEText(html_content, "html"))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(message)
        server.quit()
        return otp_code  # ✅ Gửi thành công thì trả về mã OTP
    except Exception as e:
        print(f"Failed to send email: {e}")
        return None  # 🔴 Gửi thất bại thì trả về None
