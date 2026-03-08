import schedule
import time
import json
import os
from datetime import datetime
from automation.email_service import EmailService
from dotenv import load_dotenv

load_dotenv()


class ReportScheduler:

    def __init__(self, analyst):
        self.analyst = analyst
        self.email_service = EmailService()

    def format_report(self, insights):
        """
        Convert AI insights JSON into a readable report.
        """

        report = []
        report.append("AI BUSINESS PERFORMANCE REPORT")
        report.append("=" * 40)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("")

        if isinstance(insights, dict):

            for section, content in insights.items():

                report.append(section.replace("_", " ").title())
                report.append("-" * 30)

                if isinstance(content, list):
                    for item in content:
                        report.append(f"• {item}")

                elif isinstance(content, dict):
                    for k, v in content.items():
                        report.append(f"{k}: {v}")

                else:
                    report.append(str(content))

                report.append("")

        else:
            report.append(str(insights))

        return "\n".join(report)

    def scheduled_report(self):

        question = "Generate a business performance report"

        raw_plan, plan, results, raw_insights, insights = self.analyst.run(question)

        print("\n=== Scheduled AI Report ===")
        print(insights)

        # Convert to readable report
        report_text = self.format_report(insights)

        subject = f"AI Business Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        self.email_service.send_email(
            recipient=os.getenv("REPORT_RECIPIENT"),
            subject=subject,
            body=report_text
        )

        print("Email report sent.")

    def start(self):

        # testing interval
        schedule.every(30).seconds.do(self.scheduled_report)

        print("Scheduler running (30 second test interval)...")

        while True:
            schedule.run_pending()
            time.sleep(1)