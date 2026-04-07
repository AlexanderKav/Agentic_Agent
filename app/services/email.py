import os
import json
import base64
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

    async def _send_via_sendgrid(self, to_email: str, subject: str, content: str, charts: dict = None, json_results: bytes = None) -> tuple:
        """Send email using SendGrid API with optional chart and JSON attachments"""
        if not self.use_sendgrid or not self.sendgrid_api_key:
            return False, "SendGrid not configured"
        
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment
            
            sg = SendGridAPIClient(self.sendgrid_api_key)
            
            from_email = Email(self.from_email)
            to_email_obj = To(to_email)
            
            mail = Mail(from_email, to_email_obj, subject, Content("text/plain", content))
            
            # Attach charts if provided
            if charts:
                for chart_name, chart_path in charts.items():
                    if chart_path and os.path.exists(chart_path):
                        with open(chart_path, 'rb') as f:
                            file_data = f.read()
                            encoded = base64.b64encode(file_data).decode()
                            
                            attachment = Attachment()
                            attachment.content = encoded
                            attachment.type = "image/png"
                            attachment.filename = f"{chart_name}.png"
                            attachment.disposition = "attachment"
                            mail.add_attachment(attachment)
                            print(f"📎 Attached chart: {chart_name}.png ({len(file_data)} bytes)")
                    else:
                        print(f"⚠️ Chart file not found: {chart_path}")
            
            # Attach JSON results if provided
            if json_results:
                encoded_json = base64.b64encode(json_results).decode()
                json_attachment = Attachment()
                json_attachment.content = encoded_json
                json_attachment.type = "application/json"
                json_attachment.filename = "analysis_results.json"
                json_attachment.disposition = "attachment"
                mail.add_attachment(json_attachment)
                print(f"📎 Attached JSON results ({len(json_results)} bytes)")
            
            response = sg.send(mail)
            
            if response.status_code == 202:
                chart_count = len(charts) if charts else 0
                print(f"✅ Email sent to {to_email} with {chart_count} chart(s) and JSON attachment")
                return True, "Email sent"
            else:
                print(f"❌ SendGrid error: {response.status_code}")
                return False, f"Error: {response.status_code}"
                
        except Exception as e:
            print(f"❌ SendGrid error: {e}")
            import traceback
            traceback.print_exc()
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
        """Send analysis results email with chart attachments (if available)"""
        subject = f"Agentic Analyst Results: {question[:40]}..."
        
        # Extract insights safely
        insights = results.get("insights", "No insights available")
        if isinstance(insights, dict):
            insights = insights.get("human_readable_summary") or insights.get("answer") or str(insights)
        
        # Extract raw insights safely (handle None)
        raw_insights = results.get("raw_insights")
        if raw_insights is None:
            raw_insights = {}
        
        supporting_insights = raw_insights.get("supporting_insights", {}) if isinstance(raw_insights, dict) else {}
        key_findings = supporting_insights.get("key_findings", []) if isinstance(supporting_insights, dict) else []
        
        anomalies_dict = raw_insights.get("anomalies", {}) if isinstance(raw_insights, dict) else {}
        anomalies = anomalies_dict.get("identified", []) if isinstance(anomalies_dict, dict) else []
        
        recommendations_dict = raw_insights.get("recommended_metrics", {}) if isinstance(raw_insights, dict) else {}
        recommendations = recommendations_dict.get("next_steps", []) if isinstance(recommendations_dict, dict) else []
        
        # Get KPIs safely
        results_dict = results.get("results", {}) if isinstance(results.get("results"), dict) else {}
        kpis = results_dict.get("kpis", {}) if isinstance(results_dict, dict) else {}
        if not kpis:
            kpis = results.get("kpis", {}) if isinstance(results.get("kpis"), dict) else {}
        
        # Get forecast details safely
        forecast_details = ""
        if isinstance(supporting_insights, dict):
            metrics = supporting_insights.get("metrics", {})
            if isinstance(metrics, dict):
                forecast_details = metrics.get("forecast_details", "")
        
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
        
        # Charts notice (only if charts actually exist)
        charts_text = ""
        valid_charts = {}
        if charts:
            # Only include charts that actually exist
            for name, path in charts.items():
                if path and os.path.exists(path):
                    valid_charts[name] = path
                    print(f"✅ Chart found: {name} at {path}")
                else:
                    print(f"⚠️ Chart not found: {name} at {path}")
            
            if valid_charts:
                charts_text = f"\n\n📎 {len(valid_charts)} chart(s) attached to this email.\n"
            else:
                charts_text = "\n\n⚠️ No charts were generated for this analysis.\n"
        
        # Create JSON attachment (without charts data)
        json_results = None
        if results:
            try:
                # Remove charts from results to save space
                clean_results = results.copy()
                if 'results' in clean_results and isinstance(clean_results['results'], dict):
                    clean_results['results'].pop('charts', None)
                json_str = json.dumps(clean_results, indent=2, default=str)
                json_results = json_str.encode('utf-8')
            except Exception as e:
                print(f"⚠️ Could not create JSON attachment: {e}")
        
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
        
        return await self._send_via_sendgrid(to_email, subject, content, valid_charts, json_results)


__all__ = ['EmailService']