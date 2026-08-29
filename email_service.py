import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

SENDER = os.environ.get("EMAIL_SENDER", "")
PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
ADMIN_EMAIL = os.environ.get("EMAIL_ADMIN", "")


def _send(to_email, subject, html_body):
    if not SENDER or not PASSWORD or not to_email:
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"AI Security Chatbot <{SENDER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER, PASSWORD)
            server.sendmail(SENDER, to_email, msg.as_string())
    except Exception as e:
        print(f"[Email Error] {e}")


def notify_new_user(username):
    if not ADMIN_EMAIL:
        return
    subject = f"New User Registered: {username}"
    html = f"""
    <div style="font-family:sans-serif;max-width:500px;margin:auto;padding:20px;
                border:1px solid #e0e0e0;border-radius:12px;">
        <div style="background:linear-gradient(135deg,#667eea,#764ba2);
                    padding:20px;border-radius:8px;text-align:center;margin-bottom:20px;">
            <h2 style="color:white;margin:0;">AI Security Chatbot</h2>
        </div>
        <h3 style="color:#333;">New User Registered</h3>
        <table style="width:100%;border-collapse:collapse;">
            <tr>
                <td style="padding:8px;color:#666;width:120px;">Username</td>
                <td style="padding:8px;font-weight:bold;color:#333;">{username}</td>
            </tr>
            <tr style="background:#f9f9f9;">
                <td style="padding:8px;color:#666;">Time</td>
                <td style="padding:8px;color:#333;">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td>
            </tr>
        </table>
        <p style="color:#aaa;font-size:0.75rem;margin-top:20px;text-align:center;">
            AI Security Chatbot Admin Notification
        </p>
    </div>
    """
    _send(ADMIN_EMAIL, subject, html)


def notify_chat_saved(username, title, message_count):
    if not ADMIN_EMAIL:
        return
    subject = f"Chat Saved by {username}"
    html = f"""
    <div style="font-family:sans-serif;max-width:500px;margin:auto;padding:20px;
                border:1px solid #e0e0e0;border-radius:12px;">
        <div style="background:linear-gradient(135deg,#667eea,#764ba2);
                    padding:20px;border-radius:8px;text-align:center;margin-bottom:20px;">
            <h2 style="color:white;margin:0;">AI Security Chatbot</h2>
        </div>
        <h3 style="color:#333;">Chat Log Saved</h3>
        <table style="width:100%;border-collapse:collapse;">
            <tr>
                <td style="padding:8px;color:#666;width:120px;">User</td>
                <td style="padding:8px;font-weight:bold;color:#333;">{username}</td>
            </tr>
            <tr style="background:#f9f9f9;">
                <td style="padding:8px;color:#666;">Title</td>
                <td style="padding:8px;color:#333;">{title}</td>
            </tr>
            <tr>
                <td style="padding:8px;color:#666;">Messages</td>
                <td style="padding:8px;color:#333;">{message_count} messages</td>
            </tr>
            <tr style="background:#f9f9f9;">
                <td style="padding:8px;color:#666;">Saved At</td>
                <td style="padding:8px;color:#333;">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td>
            </tr>
        </table>
        <p style="color:#aaa;font-size:0.75rem;margin-top:20px;text-align:center;">
            AI Security Chatbot Admin Notification
        </p>
    </div>
    """
    _send(ADMIN_EMAIL, subject, html)


def send_welcome_email(username, to_email=None):
    if not to_email:
        return
    subject = "Welcome to AI Security Chatbot!"
    html = f"""
    <div style="font-family:sans-serif;max-width:500px;margin:auto;padding:20px;
                border:1px solid #e0e0e0;border-radius:12px;">
        <div style="background:linear-gradient(135deg,#667eea,#764ba2);
                    padding:30px;border-radius:8px;text-align:center;margin-bottom:25px;">
            <h1 style="color:white;margin:0;font-size:1.6rem;">AI Security Chatbot</h1>
            <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;">
                Your AI-powered security knowledge assistant
            </p>
        </div>
        <h2 style="color:#333;">Welcome, {username}!</h2>
        <p style="color:#555;line-height:1.6;">Your account has been created. Here is what you can do:</p>
        <ul style="color:#555;line-height:2;">
            <li>Ask questions about AI security</li>
            <li>Upload your own PDF to chat with it</li>
            <li>Save and download your chat logs</li>
            <li>Toggle dark mode for night reading</li>
        </ul>
        <p style="color:#aaa;font-size:0.75rem;margin-top:25px;text-align:center;">
            AI Security Chatbot - Powered by Claude AI
        </p>
    </div>
    """
    _send(to_email, subject, html)
