import json
import logging
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        # SendGrid configuration
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.use_sendgrid = bool(self.sendgrid_api_key)
        
        # Common settings
        self.from_email = os.getenv("FROM_EMAIL", "alexkavanagh6@gmail.com")
        self.from_name = os.getenv("FROM_NAME", "Agentic Analyst")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        # Initialize SendGrid
        self.sendgrid_client = None
        if self.use_sendgrid:
            try:
                from sendgrid import SendGridAPIClient
                self.sendgrid_client = SendGridAPIClient(self.sendgrid_api_key)
                print(f"✅ SendGrid email service initialized")
            except ImportError:
                print("⚠️ SendGrid package not installed. Install with: pip install sendgrid")
                self.use_sendgrid = False
            except Exception as e:
                print(f"⚠️ SendGrid initialization failed: {e}")
                self.use_sendgrid = False
        
        print(f"📧 Email service initialized (SendGrid: {self.use_sendgrid})")
        print(f"📧 From: {self.from_email}")
        print(f"📧 Frontend URL: {self.frontend_url}")

    async def _send_via_sendgrid(self, to_email: str, subject: str, html_content: str, plain_text_content: str = None) -> tuple:
        """Send email using SendGrid API"""
        if not self.sendgrid_client:
            return False, "SendGrid client not initialized"
        
        try:
            from sendgrid.helpers.mail import Mail
            
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject
            )
            message.html_content = html_content
            
            # Add plain text version if provided (fallback for email clients)
            if plain_text_content:
                message.plain_text_content = plain_text_content
            
            # Log request details for debugging
            print(f"📧 SendGrid Request:")
            print(f"   From: {self.from_email}")
            print(f"   To: {to_email}")
            print(f"   Subject: {subject}")
            print(f"   HTML length: {len(html_content)} chars")
            
            response = self.sendgrid_client.send(message)
            
            if response.status_code == 202:
                print(f"✅ Email sent via SendGrid to {to_email}")
                return True, "Email sent successfully"
            else:
                print(f"❌ SendGrid returned {response.status_code}")
                try:
                    print(f"Response body: {response.body}")
                except:
                    pass
                return False, f"SendGrid error: {response.status_code}"
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ SendGrid error: {error_msg}")
            
            # Try to extract more details from the exception
            if hasattr(e, 'body'):
                print(f"Error body: {e.body}")
            if hasattr(e, 'headers'):
                print(f"Error headers: {e.headers}")
            
            import traceback
            traceback.print_exc()
            return False, error_msg

    async def send_verification_email(self, to_email: str, username: str, token: str):
        """Send email verification link"""
        if not self.use_sendgrid:
            print("❌ SendGrid not configured. Cannot send email.")
            return False, "Email service not configured"
        
        verification_link = f"{self.frontend_url}/verification-success?token={token}"

        print(f"📧 Sending verification email to {to_email}")
        print(f"🔗 Verification link: {verification_link}")

        html = self._get_verification_html(username, verification_link)
        plain_text = self._get_verification_plain_text(username, verification_link)
        
        return await self._send_via_sendgrid(to_email, "Verify Your Email - Agentic Analyst", html, plain_text)

    async def send_password_reset_email(self, to_email: str, username: str, token: str):
        """Send password reset email"""
        if not self.use_sendgrid:
            print("❌ SendGrid not configured. Cannot send email.")
            return False, "Email service not configured"
        
        reset_link = f"{self.frontend_url}/reset-password?token={token}"

        print(f"📧 Sending password reset email to {to_email}")
        print(f"🔗 Reset link: {reset_link}")

        html = self._get_password_reset_html(username, reset_link)
        plain_text = self._get_password_reset_plain_text(username, reset_link)
        
        return await self._send_via_sendgrid(to_email, "Reset Your Password - Agentic Analyst", html, plain_text)

    async def send_analysis_results(self, to_email: str, question: str, results: dict[str, Any],
                                    charts: dict[str, str] | None = None):
        """Send analysis results via email"""
        if not self.use_sendgrid:
            print("❌ SendGrid not configured. Cannot send email.")
            return False, "Email service not configured"
        
        subject = f"📊 Agentic Analyst Results: {question[:50]}..."
        
        html = self._get_analysis_html(question, results)
        plain_text = self._get_analysis_plain_text(question, results)
        
        return await self._send_via_sendgrid(to_email, subject, html, plain_text)

    def _get_verification_html(self, username: str, verification_link: str) -> str:
        """Generate verification email HTML"""
        return f"""
        <html>
        <body>
            <h2>Welcome to Agentic Analyst!</h2>
            <p>Hi {username},</p>
            <p>Please verify your email address by clicking the link below:</p>
            <p><a href="{verification_link}">Verify Email Address</a></p>
            <p>This link expires in 24 hours.</p>
            <p>If you didn't create an account, please ignore this email.</p>
            <br>
            <p>Agentic Analyst Team</p>
        </body>
        </html>
        """

    def _get_verification_plain_text(self, username: str, verification_link: str) -> str:
        """Generate verification email plain text"""
        return f"""
Welcome to Agentic Analyst!

Hi {username},

Please verify your email address by clicking the link below:

{verification_link}

This link expires in 24 hours.

If you didn't create an account, please ignore this email.

Agentic Analyst Team
"""

    def _get_password_reset_html(self, username: str, reset_link: str) -> str:
        """Generate password reset email HTML"""
        return f"""
        <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>Hi {username},</p>
            <p>We received a request to reset your password. Click the link below to reset it:</p>
            <p><a href="{reset_link}">Reset Password</a></p>
            <p>This link expires in 24 hours.</p>
            <p>If you didn't request this, please ignore this email.</p>
            <br>
            <p>Agentic Analyst Team</p>
        </body>
        </html>
        """

    def _get_password_reset_plain_text(self, username: str, reset_link: str) -> str:
        """Generate password reset email plain text"""
        return f"""
Password Reset Request

Hi {username},

We received a request to reset your password. Click the link below to reset it:

{reset_link}

This link expires in 24 hours.

If you didn't request this, please ignore this email.

Agentic Analyst Team
"""

    def _get_analysis_html(self, question: str, results: dict) -> str:
        """Generate analysis results email HTML"""
        insights = results.get("insights", "No insights available")
        if isinstance(insights, dict):
            insights = insights.get("human_readable_summary") or insights.get("answer") or str(insights)
        
        # Get KPIs if available
        kpis = results.get("results", {}).get("kpis", {})
        if not kpis:
            kpis = results.get("kpis", {})
        
        kpi_html = ""
        if kpis:
            kpi_html = "<h3>Key Metrics:</h3><ul>"
            for key, value in kpis.items():
                if isinstance(value, (int, float)):
                    if "revenue" in key or "profit" in key:
                        formatted = f"${value:,.0f}"
                    elif "margin" in key:
                        formatted = f"{value:.1%}"
                    else:
                        formatted = f"{value:,.0f}"
                else:
                    formatted = str(value)
                kpi_html += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {formatted}</li>"
            kpi_html += "</ul>"
        
        return f"""
        <html>
        <body>
            <h2>🤖 Agentic Analyst Results</h2>
            <p><strong>Your Question:</strong> "{question if question else 'General Business Overview'}"</p>
            
            <div style="background: #e3f2fd; padding: 15px; border-left: 4px solid #1976d2;">
                <h3>💡 Key Insights</h3>
                <p>{insights}</p>
            </div>
            
            {kpi_html}
            
            <p>A complete JSON file with analysis results is attached to this email.</p>
            <br>
            <p>Agentic Analyst Team</p>
        </body>
        </html>
        """

    def _get_analysis_plain_text(self, question: str, results: dict) -> str:
        """Generate analysis results email plain text"""
        insights = results.get("insights", "No insights available")
        if isinstance(insights, dict):
            insights = insights.get("human_readable_summary") or insights.get("answer") or str(insights)
        
        # Get KPIs if available
        kpis = results.get("results", {}).get("kpis", {})
        if not kpis:
            kpis = results.get("kpis", {})
        
        kpi_text = ""
        if kpis:
            kpi_text = "\nKey Metrics:\n"
            for key, value in kpis.items():
                if isinstance(value, (int, float)):
                    if "revenue" in key or "profit" in key:
                        formatted = f"${value:,.0f}"
                    elif "margin" in key:
                        formatted = f"{value:.1%}"
                    else:
                        formatted = f"{value:,.0f}"
                else:
                    formatted = str(value)
                kpi_text += f"  {key.replace('_', ' ').title()}: {formatted}\n"
        
        return f"""
🤖 Agentic Analyst Results

Your Question: "{question if question else 'General Business Overview'}"

💡 Key Insights:
{insights}
{kpi_text}
A complete JSON file with analysis results is attached to this email.

Agentic Analyst Team
"""


__all__ = ['EmailService']