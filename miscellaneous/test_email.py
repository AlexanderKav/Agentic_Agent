import asyncio
import os
from dotenv import load_dotenv
from app.services.email import EmailService

# Load environment variables
load_dotenv()

async def test_email():
    print("📧 Testing email configuration...")
    print(f"SMTP_HOST: {os.getenv('SMTP_HOST')}")
    print(f"SMTP_PORT: {os.getenv('SMTP_PORT')}")
    print(f"SMTP_USER: {os.getenv('SMTP_USER')}")
    print(f"FROM_EMAIL: {os.getenv('FROM_EMAIL')}")
    
    # Check if credentials are set
    if not os.getenv('SMTP_USER') or not os.getenv('SMTP_PASSWORD'):
        print("❌ ERROR: SMTP credentials not set in .env file")
        print("Please update your .env file with:")
        print("SMTP_HOST=smtp.gmail.com")
        print("SMTP_PORT=587")
        print("SMTP_USER=your-email@gmail.com")
        print("SMTP_PASSWORD=your-app-password")
        print("FROM_EMAIL=your-email@gmail.com")
        return
    
    email_service = EmailService()
    
    # Test verification email
    success, message = await email_service.send_verification_email(
        to_email=os.getenv('SMTP_USER'),  # Send to yourself
        username="TestUser",
        token="test-token-123"
    )
    
    if success:
        print("✅ Email sent successfully! Check your inbox.")
    else:
        print(f"❌ Failed: {message}")

if __name__ == "__main__":
    asyncio.run(test_email())