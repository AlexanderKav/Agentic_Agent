import json
import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)

        print(f"📧 Email service initialized with: {self.smtp_host}:{self.smtp_port}")
        print(f"📧 From: {self.from_email}")

    async def _send_email(self, to_email: str, subject: str, html_content: str) -> tuple:
        """Internal method to send emails"""
        try:
            print(f"📧 Preparing to send email to {to_email}")
            print(f"📧 Subject: {subject}")

            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Subject"] = subject

            # Attach HTML content
            msg.attach(MIMEText(html_content, "html"))

            # Connect to SMTP server
            print(f"📧 Connecting to {self.smtp_host}:{self.smtp_port}...")
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                print("📧 TLS started")
                server.login(self.smtp_user, self.smtp_password)
                print("📧 Login successful")
                server.send_message(msg)
                print(f"✅ Email sent successfully to {to_email}")

            return True, "Email sent successfully"

        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg

    async def send_verification_email(self, to_email: str, username: str, token: str):
        """Send email verification link"""
        # Point to the frontend success page that will handle the verification
        verification_link = f"http://localhost:3000/verification-success?token={token}"

        print(f"📧 Sending verification email to {to_email}")
        print(f"🔗 Verification link: {verification_link}")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background-color: #f4f4f4;
                }}
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 40px 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 600;
                }}
                .content {{
                    padding: 40px 30px;
                    background: white;
                }}
                .button {{
                    display: inline-block;
                    padding: 14px 30px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    text-decoration: none;
                    border-radius: 50px;
                    font-weight: 600;
                    margin: 20px 0;
                    transition: transform 0.2s;
                }}
                .button:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px 30px;
                    text-align: center;
                    color: #666;
                    font-size: 14px;
                    border-top: 1px solid #eee;
                }}
                .note {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 5px;
                }}
                .logo {{
                    font-size: 48px;
                    margin-bottom: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🤖</div>
                    <h1>Welcome to Agentic Analyst!</h1>
                </div>
                
                <div class="content">
                    <h2>Hi {username}!</h2>
                    
                    <p>Thanks for registering. Please verify your email address to start using all features of Agentic Analyst.</p>
                    
                    <div style="text-align: center;">
                        <a href="{verification_link}" class="button">Verify Email Address</a>
                    </div>
                    
                    <div class="note">
                        <strong>🔒 Security Note:</strong> This link will expire in 24 hours. If you didn't create an account, you can safely ignore this email.
                    </div>
                    
                    <p style="margin-top: 30px;">
                        Or copy this link to your browser:<br>
                        <small style="color: #667eea; word-break: break-all;">{verification_link}</small>
                    </p>
                </div>
                
                <div class="footer">
                    <p>© 2024 Agentic Analyst. All rights reserved.</p>
                    <p style="margin-top: 10px; font-size: 12px;">
                        This is an automated message, please do not reply to this email.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self._send_email(to_email, "Verify Your Email - Agentic Analyst", html)

    async def send_analysis_results(self, to_email: str, question: str, results: dict[str, Any],
                                    charts: dict[str, str] | None = None):
        """Send analysis results via email"""
        subject = f"📊 Agentic Analyst Results: {question[:50]}..."

        # Extract insights - handle different data structures
        insights = results.get("insights", "No insights available")
        if isinstance(insights, dict):
            insights = insights.get("human_readable_summary") or insights.get("answer") or str(insights)

        # Get KPIs - try multiple locations
        kpis = {}

        # Try results.results.kpis
        if results.get("results", {}).get("kpis"):
            kpis = results["results"]["kpis"]
        # Try results.kpis
        elif results.get("kpis"):
            kpis = results["kpis"]
        # Try direct metrics
        else:
            for key in ['total_revenue', 'profit_margin', 'total_profit', 'avg_order_value']:
                if key in results:
                    kpis[key] = results[key]

        # Get data summary
        data_summary = results.get("data_summary", {})
        if not data_summary and results.get("results", {}).get("data_summary"):
            data_summary = results["results"]["data_summary"]

        # Create HTML content
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background-color: #f4f4f4;
                }}
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .content {{
                    padding: 30px;
                }}
                .insights-box {{
                    background: #e3f2fd;
                    padding: 20px;
                    border-left: 4px solid #1976d2;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .kpi-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 15px;
                    margin: 20px 0;
                }}
                .kpi-card {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                    border: 1px solid #e0e0e0;
                }}
                .kpi-value {{
                    font-size: 20px;
                    font-weight: bold;
                    color: #1976d2;
                    margin-top: 5px;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                    border-top: 1px solid #eee;
                }}
                .question {{
                    font-style: italic;
                    color: #555;
                    background: #f5f5f5;
                    padding: 15px;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🤖 Agentic Analyst</h1>
                    <p>Your AI-Powered Business Intelligence Results</p>
                </div>
                
                <div class="content">
                    <div class="question">
                        <strong>Your Question:</strong><br>
                        "{question if question else 'General Business Overview'}"
                    </div>
                    
                    <div class="insights-box">
                        <h3>💡 Key Insights</h3>
                        <p>{insights}</p>
                    </div>
        """

        # Add KPIs if available
        if kpis:
            html += '<h3>📊 Key Performance Indicators</h3><div class="kpi-grid">'

            for key, value in kpis.items():
                if isinstance(value, (int, float)):
                    if "revenue" in key or "profit" in key or "cost" in key:
                        formatted = f"${value:,.0f}"
                    elif "margin" in key:
                        formatted = f"{value:.1%}"
                    else:
                        formatted = f"{value:,.0f}"
                else:
                    formatted = str(value)

                html += f"""
                    <div class="kpi-card">
                        <div style="font-size: 14px; color: #666;">{key.replace('_', ' ').title()}</div>
                        <div class="kpi-value">{formatted}</div>
                    </div>
                """
            html += "</div>"

        # Add data summary
        data_summary = results.get("data_summary", {})
        if data_summary:
            html += f"""
                <div style="margin-top: 20px; padding: 15px; background: #f5f5f5; border-radius: 5px;">
                    <strong>📋 Data Summary:</strong><br>
                    Rows: {data_summary.get('rows', 'N/A')} | 
                    Columns: {len(data_summary.get('columns', []))}
                </div>
            """

        html += """
                    <p style="margin-top: 30px; padding: 15px; background: #e8f5e8; border-radius: 5px;">
                        📎 A JSON file with complete analysis results is attached to this email.
                    </p>
                </div>
                
                <div class="footer">
                    <p>Sent by Agentic Analyst - Your AI Business Intelligence Assistant</p>
                    <p>© 2024 Agentic Analyst. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Create message with attachments
        try:
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Subject"] = subject

            # Attach HTML content
            msg.attach(MIMEText(html, "html"))

            # Attach JSON results
            json_str = json.dumps(results, indent=2, default=str)
            json_attachment = MIMEApplication(json_str.encode("utf-8"), Name="analysis_results.json")
            json_attachment["Content-Disposition"] = 'attachment; filename="analysis_results.json"'
            msg.attach(json_attachment)

            # Attach charts if available
            if charts:
                for name, path in charts.items():
                    if os.path.exists(path):
                        with open(path, "rb") as f:
                            chart_data = f.read()
                            attachment = MIMEApplication(chart_data, Name=f"{name}.png")
                            attachment["Content-Disposition"] = f'attachment; filename="{name}.png"'
                            msg.attach(attachment)
                            print(f"📎 Attached chart: {name}.png")

            # Send email
            print(f"📧 Sending analysis results to {to_email}")
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            print(f"✅ Analysis results sent successfully to {to_email}")
            return True, "Email sent successfully"

        except Exception as e:
            error_msg = f"Failed to send analysis email: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg
    # app/services/email.py

    # Add this method to your EmailService class

    # app/services/email.py - Update the send_password_reset_email method
    async def send_password_reset_email(self, to_email: str, username: str, token: str):
        """Send password reset email"""
        reset_link = f"http://localhost:3000/reset-password?token={token}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background-color: #f4f4f4;
                }}
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 40px 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 600;
                }}
                .content {{
                    padding: 40px 30px;
                    background: white;
                }}
                .button {{
                    display: inline-block;
                    padding: 14px 30px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    text-decoration: none;
                    border-radius: 50px;
                    font-weight: 600;
                    margin: 20px 0;
                    transition: transform 0.2s;
                }}
                .button:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px 30px;
                    text-align: center;
                    color: #666;
                    font-size: 14px;
                    border-top: 1px solid #eee;
                }}
                .note {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Password Reset</h1>
                </div>
                
                <div class="content">
                    <h2>Hi {username},</h2>
                    
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    
                    <div style="text-align: center;">
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </div>
                    
                    <div class="note">
                        <strong>🔒 Security Note:</strong> This link will expire in 24 hours. If you didn't request this, you can safely ignore this email.
                    </div>
                    
                    <p style="margin-top: 30px;">
                        Or copy this link to your browser:<br>
                        <small style="color: #667eea; word-break: break-all;">{reset_link}</small>
                    </p>
                </div>
                
                <div class="footer">
                    <p>© 2024 Agentic Analyst. All rights reserved.</p>
                    <p style="margin-top: 10px; font-size: 12px;">
                        This is an automated message, please do not reply to this email.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self._send_email(to_email, "Reset Your Password - Agentic Analyst", html)


__all__ = ['ABTestService']  # For ab_testing.py
__all__ = ['EmailService']   # For email.py
__all__ = ['KeyRotationService', 'get_key_rotation_service']  # For key_rotation.py
__all__ = ['SecretsManager', 'get_secrets_manager']  # For secrets_manager.py