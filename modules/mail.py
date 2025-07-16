import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
# Example usage
import asyncio
from settings.config import EmailConfig
import aiohttp
import datetime

import traceback

server: aiosmtplib.SMTP = None

from services.logging import logger

from modules.data import get_config

async def connect_smtp():
    try:
        server = aiosmtplib.SMTP(
            hostname=EmailConfig.SMTP_SERVER,
            port=EmailConfig.SMTP_PORT,
            use_tls=True
        )
        await server.connect()
        await server.login(EmailConfig.SMTP_USER, EmailConfig.SMTP_PASSWORD)
        logger.info("Login successful!")
        return server
    except Exception as e:
        logger.error(f"Failed to connect or login: {e}")
        return None

async def get_connection():
    global server
    if not server or not server.is_connected:
        server = await connect_smtp()
    return server


async def send_mail(
    text: str,
    type: str = "plain", # plain, html, multipart
    subject: str = None,
    sender: str = None,
    recipients: list = None,
    attachments: list = None,
):
    try:
        server = await get_connection()
        if not server:
            logger.error("No SMTP connection available.")
            return False

        if type == "plain":
            msg = MIMEText(text, "plain")
        elif type == "html":
            msg = MIMEText(text, "html")
        elif type == "multipart":
            msg = MIMEMultipart()
            msg.attach(MIMEText(text, "html"))
            for attachment in attachments:
                with open(attachment, 'rb') as f:
                    img_data = f.read()
                    image = MIMEImage(img_data)
                    image.add_header('Content-ID', f'<{attachment}>')
                    msg.attach(image)

        if subject:
            msg["Subject"] = subject
        if sender:
            msg["From"] = sender
        if recipients:
            msg["To"] = ", ".join(recipients)

        sended_message_response = await server.send_message(msg)
        logger.info(f"Email sent to {recipients}")
        logger.debug(f"Email response: {sended_message_response}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


async def generate_verify_email_html(user_id, fullname, email, verify_url, expired_at, sitename="Unknown"):
    try:
        # Format the expiration time in a user-friendly way
        expiry_formatted = expired_at.strftime("%d %b %Y, %I:%M %p") + f" ({expired_at.strftime('%Z')})"
        expirs_in_text = expired_at - datetime.datetime.now(datetime.timezone.utc)
        if expirs_in_text.days > 0:
            expirs_in_text = f"{expirs_in_text.days} days"
        elif expirs_in_text.seconds > 3600:
            expirs_in_text = f"{expirs_in_text.seconds // 3600} hours"
        elif expirs_in_text.seconds > 60:
            expirs_in_text = f"{expirs_in_text.seconds // 60} minutes"
        else:
            expirs_in_text = f"{expirs_in_text.seconds} seconds"
            
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{sitename} - Verify Your Email</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
                
                body {{
                    font-family: 'Poppins', sans-serif;
                    line-height: 1.6;
                    color: #333333;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                }}
                
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    background-color: #ffffff;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
                }}
                
                .header {{
                    background: linear-gradient(45deg, #4f46e5, #7c3aed);
                    padding: 35px 20px;
                    text-align: center;
                    position: relative;
                }}
                
                .header:after {{
                    content: '';
                    position: absolute;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    height: 30px;
                    background: linear-gradient(to right bottom, transparent 49%, white 51%);
                }}
                
                .header h1 {{
                    color: white;
                    margin: 0;
                    font-size: 28px;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                }}
                
                .icon-container {{
                    width: 80px;
                    height: 80px;
                    margin: -40px auto 20px;
                    background-color: #4f46e5;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
                    border: 4px solid white;
                    position: relative;
                    z-index: 2;
                }}
                
                .icon {{
                    width: 40px;
                    height: 40px;
                }}
                
                .content {{
                    padding: 20px 40px 40px;
                    text-align: center;
                }}
                
                .greeting {{
                    font-size: 22px;
                    font-weight: 600;
                    color: #333;
                    margin-bottom: 15px;
                }}
                
                .content p {{
                    margin-bottom: 20px;
                    font-size: 16px;
                    color: #4b5563;
                    line-height: 1.7;
                }}
                
                .highlight {{
                    font-weight: 600;
                    color: #4f46e5;
                }}
                
                .btn {{
                    display: inline-block;
                    background-color: #4f46e5;
                    color: #ffffff !important;
                    text-decoration: none;
                    padding: 16px 32px;
                    border-radius: 8px;
                    font-weight: 700;
                    font-size: 18px;
                    margin: 25px 0;
                    transition: all 0.3s;
                    box-shadow: 0 4px 10px rgba(79, 70, 229, 0.3);
                    border: none;
                    cursor: pointer;
                }}
                
                .btn:hover {{
                    background-color: #4338ca;
                    transform: translateY(-2px);
                    box-shadow: 0 6px 15px rgba(79, 70, 229, 0.4);
                }}
                
                .link-container {{
                    background-color: #f9fafb;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 20px 0;
                    border: 1px solid #e5e7eb;
                }}
                
                .verification-link {{
                    word-break: break-all;
                    font-size: 14px;
                    color: #4f46e5;
                    font-family: monospace;
                    background-color: #f3f4f6;
                    padding: 10px;
                    border-radius: 5px;
                    border: 1px dashed #d1d5db;
                    display: inline-block;
                    margin-top: 5px;
                    text-align: left;
                }}
                
                .expiry {{
                    font-size: 14px;
                    color: #6b7280;
                    margin-top: 30px;
                    padding: 20px;
                    border-radius: 8px;
                    background-color: #f9fafb;
                    border: 1px solid #e5e7eb;
                }}
                
                .expiry-title {{
                    font-weight: 600;
                    color: #4b5563;
                    margin-bottom: 5px;
                }}
                
                .expiry-date {{
                    font-weight: 700;
                    color: #4f46e5;
                    font-size: 16px;
                }}
                
                .help-text {{
                    font-size: 14px;
                    color: #6b7280;
                    font-style: italic;
                    margin-top: 10px;
                }}
                
                .footer {{
                    background-color: #f9fafb;
                    padding: 25px 20px;
                    text-align: center;
                    font-size: 14px;
                    color: #6b7280;
                    border-top: 1px solid #e5e7eb;
                }}
                
                .user-info {{
                    font-size: 13px;
                    color: #9ca3af;
                    margin-top: 20px;
                    background-color: #f3f4f6;
                    padding: 10px;
                    border-radius: 5px;
                    display: inline-block;
                }}
                
                .copyright {{
                    margin-top: 15px;
                    font-weight: 500;
                }}
                
                @media only screen and (max-width: 550px) {{
                    .container {{
                        width: 100%;
                        margin: 0;
                        border-radius: 0;
                    }}
                    
                    .content {{
                        padding: 20px;
                    }}
                    
                    .header:after {{
                        height: 20px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{sitename} Email Verification</h1>
                </div>
                
                <div class="content">                    
                    <p class="greeting">Hello <span class="highlight">{fullname}</span>!</p>
                    
                    <p>Thank you for registering with <strong>{sitename}</strong>! To activate your account and access all our features, please verify your email address by clicking the button below:</p>
                    
                    <a href="{verify_url}" class="btn">Verify My Email</a>
                    
                    <p>If the button above doesn't work, you can copy and paste the following link into your browser:</p>
                    
                    <div class="link-container">
                        <div class="verification-link">{verify_url}</div>
                    </div>
                    
                    <div class="expiry">
                        <p class="expiry-title">This verification link will expire on:</p>
                        <p class="expiry-date">{expiry_formatted}</p>
                        <p class="expiry-title">Time remaining:</p>
                        <p class="expiry-date">{expirs_in_text}</p>
                        <p class="help-text">If the link expires, you can request a new verification link from your account settings.</p>
                    </div>
                    
                    <div class="user-info">
                        User ID: {user_id} | Email: {email}
                    </div>
                </div>
                
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p class="copyright">&copy; {datetime.datetime.now().year} {sitename}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    except Exception as e:
        logger.error(f"Error generating verify email HTML: {traceback.format_exc()}")
        return None
    

async def generate_renewal_email(
    full_name: str,
    username: str,
    email: str,
    months_extended: int,
    old_end_date: datetime.datetime,
    new_end_date: datetime.datetime,
):
    try:
        config_data = await get_config()
        sitename = config_data.get("name")
        # Format dates in a user-friendly way
        old_date_formatted = old_end_date.strftime("%d %b %Y")
        new_date_formatted = new_end_date.strftime("%d %b %Y")
        
        # Calculate days added
        days_extended = (new_end_date - old_end_date).days
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{sitename} - Subscription Renewed</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
                
                body {{
                    font-family: 'Poppins', sans-serif;
                    line-height: 1.6;
                    color: #333333;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                }}
                
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    background-color: #ffffff;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
                }}
                
                .header {{
                    background: linear-gradient(45deg, #10b981, #059669);
                    padding: 35px 20px;
                    text-align: center;
                    position: relative;
                }}
                
                .header:after {{
                    content: '';
                    position: absolute;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    height: 30px;
                    background: linear-gradient(to right bottom, transparent 49%, white 51%);
                }}
                
                .header h1 {{
                    color: white;
                    margin: 0;
                    font-size: 28px;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                }}
                
                .content {{
                    padding: 40px 40px 40px;
                    text-align: center;
                }}
                
                .greeting {{
                    font-size: 22px;
                    font-weight: 600;
                    color: #333;
                    margin-bottom: 15px;
                }}
                
                .content p {{
                    margin-bottom: 20px;
                    font-size: 16px;
                    color: #4b5563;
                    line-height: 1.7;
                }}
                
                .highlight {{
                    font-weight: 600;
                    color: #10b981;
                }}
                
                .success-badge {{
                    background: linear-gradient(45deg, #10b981, #059669);
                    color: white;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 14px;
                    display: inline-block;
                    margin: 10px 0;
                    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
                }}
                
                .details-card {{
                    background-color: #f9fafb;
                    border-radius: 12px;
                    padding: 25px;
                    margin: 25px 0;
                    border: 1px solid #e5e7eb;
                    text-align: left;
                }}
                
                .detail-row {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px 0;
                    border-bottom: 1px solid #e5e7eb;
                }}
                
                .detail-row:last-child {{
                    border-bottom: none;
                }}
                
                .detail-label {{
                    font-weight: 600;
                    color: #374151;
                    font-size: 15px;
                }}
                
                .detail-value {{
                    font-weight: 500;
                    color: #10b981;
                    font-size: 15px;
                }}
                
                .date-highlight {{
                    background: linear-gradient(45deg, #10b981, #059669);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    font-weight: 700;
                    font-size: 16px;
                }}
                
                .extension-summary {{
                    background: linear-gradient(45deg, #10b981, #059669);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                    text-align: center;
                }}
                
                .extension-summary h3 {{
                    margin: 0 0 10px 0;
                    font-size: 20px;
                    font-weight: 700;
                }}
                
                .extension-summary p {{
                    margin: 0;
                    font-size: 16px;
                    opacity: 0.9;
                }}
                
                .footer {{
                    background-color: #f9fafb;
                    padding: 25px 20px;
                    text-align: center;
                    font-size: 14px;
                    color: #6b7280;
                    border-top: 1px solid #e5e7eb;
                }}
                
                .user-info {{
                    font-size: 13px;
                    color: #9ca3af;
                    margin-top: 20px;
                    background-color: #f3f4f6;
                    padding: 10px;
                    border-radius: 5px;
                    display: inline-block;
                }}
                
                .copyright {{
                    margin-top: 15px;
                    font-weight: 500;
                }}
                
                .celebration {{
                    font-size: 24px;
                    margin: 10px 0;
                }}
                
                @media only screen and (max-width: 550px) {{
                    .container {{
                        width: 100%;
                        margin: 0;
                        border-radius: 0;
                    }}
                    
                    .content {{
                        padding: 20px;
                    }}
                    
                    .details-card {{
                        padding: 15px;
                    }}
                    
                    .detail-row {{
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 5px;
                    }}
                    
                    .header:after {{
                        height: 20px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Subscription Renewed!</h1>
                </div>
                
                <div class="content">
                    <div class="celebration">🎉</div>
                    <p class="greeting">Great news, <span class="highlight">{full_name}</span>!</p>
                    
                    <div class="success-badge">Subscription Successfully Extended</div>
                    
                    <p>Your <strong>{sitename}</strong> membership has been successfully renewed! You can now continue enjoying all our premium fitness facilities and services.</p>
                    
                    <div class="extension-summary">
                        <h3>Extension Summary</h3>
                        <p>Your membership has been extended by <strong>{months_extended} month{'s' if months_extended != 1 else ''}</strong> ({days_extended} days)</p>
                    </div>
                    
                    <div class="details-card">
                        <div class="detail-row">
                            <span class="detail-label">Member Name:</span>
                            <span class="detail-value">{full_name}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Username:</span>
                            <span class="detail-value">@{username}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Email:</span>
                            <span class="detail-value">{email}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Previous End Date:</span>
                            <span class="detail-value">{old_date_formatted}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">New End Date:</span>
                            <span class="date-highlight">{new_date_formatted}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Extension Period:</span>
                            <span class="detail-value">{months_extended} Month{'s' if months_extended != 1 else ''}</span>
                        </div>
                    </div>
                    
                    <p>Thank you for being a valued member of our fitness community! We look forward to supporting you on your fitness journey.</p>
                    
                    <p><strong>What's Next?</strong></p>
                    <p>• Continue accessing all gym facilities<br>
                    • Book classes and personal training sessions<br>
                    • Track your fitness progress<br>
                    • Enjoy member-exclusive benefits</p>
                    
                    <div class="user-info">
                        Renewal processed on: {datetime.datetime.now().strftime('%d %b %Y at %I:%M %p')}
                    </div>
                </div>
                
                <div class="footer">
                    <p>Thank you for choosing <strong>{sitename}</strong> for your fitness journey!</p>
                    <p>If you have any questions, please don't hesitate to contact our support team.</p>
                    <p class="copyright">&copy; {datetime.datetime.now().year} {sitename}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    except Exception as e:
        logger.error(f"Error generating renewal email HTML: {traceback.format_exc()}")
        return None