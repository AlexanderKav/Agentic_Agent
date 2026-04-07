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
        """Send analysis results email - MATCHING FRONTEND QUALITY"""
        subject = f"Agentic Analyst Results: {question[:40]}..."
        
        # Extract insights
        insights = results.get("insights", "No insights available")
        if isinstance(insights, dict):
            insights = insights.get("human_readable_summary") or insights.get("answer") or str(insights)
        
        # Extract raw insights for detailed sections
        raw_insights = results.get("raw_insights", {})
        supporting_insights = raw_insights.get("supporting_insights", {})
        key_findings = supporting_insights.get("key_findings", [])
        anomalies = raw_insights.get("anomalies", {}).get("identified", [])
        recommendations = raw_insights.get("recommended_metrics", {}).get("next_steps", [])
        
        # Get KPIs
        kpis = results.get("results", {}).get("kpis", {})
        if not kpis:
            kpis = results.get("kpis", {})
        
        # Get forecast details
        forecast_details = supporting_insights.get("metrics", {}).get("forecast_details", "")
        
        # Build Key Findings section
        findings_text = ""
        if key_findings:
            findings_text = "\n\nKey Findings:\n"
            for finding in key_findings:
                findings_text += f"  • {finding}\n"
        
        # Build KPIs text
        kpi_text = ""
        if kpis:
            kpi_text = "\n\nKey Metrics:\n"
            for key, value in kpis.items():
                if isinstance(value, (int, float)):
                    if "margin" in key:
                        formatted = f"{value:.1%}"
                    elif "revenue" in key or "profit" in key or "cost" in key:
                        formatted = f"${value:,.0f}"
                    else:
                        formatted = f"{value:,.0f}"
                else:
                    formatted = str(value)
                label = key.replace('_', ' ').title()
                kpi_text += f"  • {label}: {formatted}\n"
        
        # Add forecast details if available
        if forecast_details:
            kpi_text += f"  • Forecast Details: {forecast_details}\n"
        
        # Build Anomalies section
        anomalies_text = ""
        if anomalies:
            anomalies_text = "\n\n⚠️ Detected Anomalies:\n"
            for anomaly in anomalies:
                anomalies_text += f"  • {anomaly}\n"
        
        # Build Recommendations section
        recommendations_text = ""
        if recommendations:
            recommendations_text = "\n\n📊 Recommended Next Steps:\n"
            for i, step in enumerate(recommendations, 1):
                recommendations_text += f"  {i}. {step}\n"
        
        # Charts notice
        charts_text = ""
        if charts and len(charts) > 0:
            charts_text = f"\n\n📎 {len(charts)} chart(s) attached to this email.\n"
        
        # Create the full email content
        content = f"""
    {'='*60}
    🤖 AGENTIC ANALYST - ANALYSIS RESULTS
    {'='*60}

    Your Question: "{question}"

    Analysis Summary:
    {insights}
    {findings_text}
    {kpi_text}
    {anomalies_text}
    {recommendations_text}
    {charts_text}
    {'='*60}
    📎 Complete analysis results attached as JSON file.

    Agentic Analyst Team
    """
        
        return await self._send_via_sendgrid(to_email, subject, content)