import os
from typing import Any

class EmailService:
    def __init__(self):
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.use_sendgrid = bool(self.sendgrid_api_key)
        self.from_email = os.getenv("FROM_EMAIL", "alexkavanagh6@gmail.com")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        if self.use_sendgrid:
            print(f"✅ SendGrid email service initialized")
        print(f"📧 Email service ready (SendGrid: {self.use_sendgrid})")

    async def _send_via_sendgrid(self, to_email: str, subject: str, content: str, plain_text: str = None) -> tuple:
        """Send email using SendGrid API"""
        if not self.use_sendgrid or not self.sendgrid_api_key:
            return False, "SendGrid not configured"
        
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            sg = SendGridAPIClient(self.sendgrid_api_key)
            
            from_email = Email(self.from_email)
            to_email_obj = To(to_email)
            
            mail = Mail(from_email, to_email_obj, subject, Content("text/plain", content))
            
            response = sg.send(mail)
            
            if response.status_code == 202:
                print(f"✅ Email sent to {to_email}")
                return True, "Email sent"
            else:
                print(f"❌ SendGrid error: {response.status_code}")
                return False, f"Error: {response.status_code}"
                
        except Exception as e:
            print(f"❌ SendGrid error: {e}")
            return False, str(e)

    async def send_verification_email(self, to_email: str, username: str, token: str):
        """Send verification email"""
        if not self.use_sendgrid:
            return False, "Not configured"
        
        verification_link = f"{self.frontend_url}/verification-success?token={token}"
        
        content = f"""
Verify Your Email

Hi {username},

Click the link below to verify your email:

{verification_link}

This link expires in 24 hours.

Agentic Analyst Team
"""
        return await self._send_via_sendgrid(to_email, "Verify Your Email", content)

    async def send_password_reset_email(self, to_email: str, username: str, token: str):
        """Send password reset email"""
        if not self.use_sendgrid:
            return False, "Not configured"
        
        reset_link = f"{self.frontend_url}/reset-password?token={token}"
        
        content = f"""
Password Reset

Hi {username},

Click the link below to reset your password:

{reset_link}

This link expires in 24 hours.

Agentic Analyst Team
"""
        return await self._send_via_sendgrid(to_email, "Reset Your Password", content)

    async def send_analysis_results(self, to_email: str, question: str, results: dict, charts: dict = None):
        """Send analysis results email - FIXED KPI FORMATTING"""
        subject = f"Agentic Analyst Results: {question[:40]}..."
        
        # Extract insights
        insights = results.get("insights", "No insights available")
        if isinstance(insights, dict):
            insights = insights.get("human_readable_summary") or insights.get("answer") or str(insights)
        
        # Get KPIs
        kpis = results.get("results", {}).get("kpis", {})
        if not kpis:
            kpis = results.get("kpis", {})
        
        # Build KPIs text - FIXED FORMATTING
        kpi_text = ""
        if kpis:
            kpi_text = "\n\nKey Metrics:\n"
            for key, value in kpis.items():
                if isinstance(value, (int, float)):
                    # Handle different KPI types
                    if "margin" in key:
                        formatted = f"{value:.1%}"  # Percentage
                    elif "revenue" in key or "profit" in key or "cost" in key:
                        formatted = f"${value:,.0f}"  # Currency
                    else:
                        formatted = f"{value:,.0f}"  # Regular number
                else:
                    formatted = str(value)
                
                label = key.replace('_', ' ').title()
                kpi_text += f"  • {label}: {formatted}\n"
        
        # Charts notice
        charts_text = ""
        if charts and len(charts) > 0:
            charts_text = f"\n\n📎 {len(charts)} chart(s) attached.\n"
        
        content = f"""
    {'='*50}
    Agentic Analyst Results
    {'='*50}

    Your Question: {question}

    Key Insights:
    {insights}
    {kpi_text}
    {charts_text}
    {'='*50}
    Complete analysis results attached.

    Agentic Analyst Team
    """
        return await self._send_via_sendgrid(to_email, subject, content)