#!/usr/bin/env python3
"""
Test Notification System

Tests Telegram and Email notifications to verify setup.

Usage:
    python test_notifications.py              # Test all enabled channels
    python test_notifications.py --telegram   # Test Telegram only
    python test_notifications.py --email      # Test Email only
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

def load_config():
    """Load configuration file"""
    config_path = Path(__file__).parent / "config_crypto_bybit.json"

    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        print("   Make sure you're in the deployment_package folder")
        sys.exit(1)

    with open(config_path) as f:
        return json.load(f)

def test_telegram(config):
    """Test Telegram notification"""
    print("\n" + "="*60)
    print("TESTING TELEGRAM NOTIFICATION")
    print("="*60)

    if not config['notifications'].get('telegram_enabled'):
        print("⚠️  Telegram is DISABLED in config")
        print("   Set telegram_enabled: true to enable")
        return False

    try:
        import requests

        bot_token = config['notifications']['telegram_bot_token']
        chat_id = config['notifications']['telegram_chat_id']

        if not bot_token or not chat_id:
            print("❌ Telegram not configured")
            print("   Please set telegram_bot_token and telegram_chat_id in config")
            return False

        print(f"📱 Bot Token: {bot_token[:20]}...")
        print(f"💬 Chat ID: {chat_id}")
        print(f"\n📤 Sending test message...")

        # Test message
        message = f"""
🧪 <b>Test Notification - Telegram</b>

✅ Telegram is configured correctly!

<b>Bot Status:</b>
• Connection: Active
• Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Test: PASSED

You should see this message on your Telegram app.

<i>Nick Radge Crypto Hybrid Bot</i>
        """

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message.strip(),
            'parse_mode': 'HTML'
        }

        response = requests.post(url, data=data, timeout=10)

        if response.status_code == 200:
            print("✅ Telegram notification sent successfully!")
            print(f"\n💬 Check your Telegram app (chat with bot)")
            return True
        else:
            print(f"❌ Telegram error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except ImportError:
        print("❌ requests library not installed")
        print("   Run: pip install requests")
        return False

    except Exception as e:
        print(f"❌ Telegram test failed: {e}")
        return False

def test_email(config):
    """Test Email notification"""
    print("\n" + "="*60)
    print("TESTING EMAIL NOTIFICATION")
    print("="*60)

    if not config['notifications'].get('email_enabled'):
        print("⚠️  Email is DISABLED in config")
        print("   Set email_enabled: true to enable")
        return False

    provider = config['notifications'].get('email_provider', 'gmail')
    print(f"📧 Email Provider: {provider.upper()}")

    if provider == 'gmail':
        return test_gmail(config)
    elif provider == 'sendgrid':
        return test_sendgrid(config)
    elif provider == 'ses':
        return test_ses(config)
    else:
        print(f"❌ Unknown email provider: {provider}")
        return False

def test_gmail(config):
    """Test Gmail SMTP"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        email_from = config['notifications']['email_from']
        email_to = config['notifications']['email_to']
        smtp_host = config['notifications']['email_smtp_host']
        smtp_port = config['notifications']['email_smtp_port']
        password = config['notifications']['email_password']

        if not email_from or not email_to or not password:
            print("❌ Gmail not configured")
            print("   Please set email_from, email_to, and email_password")
            print("\n📖 See docs/TELEGRAM_SETUP_GUIDE.md for setup instructions")
            return False

        print(f"📬 From: {email_from}")
        print(f"📭 To: {email_to}")
        print(f"🌐 SMTP: {smtp_host}:{smtp_port}")
        print(f"\n📤 Sending test email...")

        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = "🧪 Test Notification - Crypto Bot"

        # Plain text version
        text_message = f"""
Test Notification - Email

✅ Email is configured correctly!

Bot Status:
• Provider: Gmail SMTP
• Connection: Active
• Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Test: PASSED

You should see this email in your inbox.

Nick Radge Crypto Hybrid Bot
        """

        # HTML version
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: #4CAF50;
                    color: white;
                    padding: 20px;
                    border-radius: 8px 8px 0 0;
                    text-align: center;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 20px;
                    border: 1px solid #ddd;
                    border-radius: 0 0 8px 8px;
                }}
                .success {{
                    background: #E8F5E9;
                    padding: 15px;
                    border-left: 4px solid #4CAF50;
                    margin: 15px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    font-size: 12px;
                    color: #999;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🧪 Test Notification</h2>
                <p>Nick Radge Crypto Hybrid Bot</p>
            </div>
            <div class="content">
                <div class="success">
                    <h3>✅ Email Configured Correctly!</h3>
                </div>

                <p><strong>Bot Status:</strong></p>
                <ul>
                    <li>Provider: Gmail SMTP</li>
                    <li>Connection: Active</li>
                    <li>Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                    <li>Test: PASSED</li>
                </ul>

                <p>You should see this email in your inbox.</p>
                <p>If it's in spam, please mark as "Not spam" to ensure future notifications arrive in your inbox.</p>
            </div>
            <div class="footer">
                <p>Automated test from your Crypto Trading Bot</p>
            </div>
        </body>
        </html>
        """

        text_part = MIMEText(text_message.strip(), 'plain')
        html_part = MIMEText(html_message.strip(), 'html')

        msg.attach(text_part)
        msg.attach(html_part)

        # Send email
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(email_from, password)
            server.send_message(msg)

        print("✅ Email sent successfully!")
        print(f"\n📬 Check your inbox: {email_to}")
        print("   (Check spam folder if not in inbox)")
        return True

    except smtplib.SMTPAuthenticationError:
        print("❌ Gmail authentication failed")
        print("   Make sure you're using an App Password, not your regular password")
        print("\n📖 See docs/EMAIL_SETUP_GUIDE.md for setup instructions")
        return False

    except Exception as e:
        print(f"❌ Gmail test failed: {e}")
        return False

def test_sendgrid(config):
    """Test SendGrid API"""
    try:
        import requests

        api_key = config['notifications'].get('sendgrid_api_key')
        email_from = config['notifications']['email_from']
        email_to = config['notifications']['email_to']

        if not api_key or not email_from or not email_to:
            print("❌ SendGrid not configured")
            print("   Please set sendgrid_api_key, email_from, and email_to")
            return False

        print(f"📬 From: {email_from}")
        print(f"📭 To: {email_to}")
        print(f"🔑 API Key: {api_key[:20]}...")
        print(f"\n📤 Sending test email...")

        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        data = {
            'personalizations': [{'to': [{'email': email_to}]}],
            'from': {'email': email_from},
            'subject': '🧪 Test Notification - Crypto Bot',
            'content': [
                {
                    'type': 'text/plain',
                    'value': 'Test notification from your crypto bot. Email is working!'
                }
            ]
        }

        response = requests.post(url, json=data, headers=headers, timeout=30)

        if response.status_code in [200, 202]:
            print("✅ Email sent successfully via SendGrid!")
            print(f"\n📬 Check your inbox: {email_to}")
            return True
        else:
            print(f"❌ SendGrid error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ SendGrid test failed: {e}")
        return False

def test_ses(config):
    """Test AWS SES"""
    try:
        import boto3

        region = config['notifications'].get('aws_ses_region', 'us-east-1')
        access_key = config['notifications'].get('aws_access_key')
        secret_key = config['notifications'].get('aws_secret_key')
        email_from = config['notifications']['email_from']
        email_to = config['notifications']['email_to']

        if not access_key or not secret_key or not email_from or not email_to:
            print("❌ AWS SES not configured")
            print("   Please set aws_access_key, aws_secret_key, email_from, and email_to")
            return False

        print(f"📬 From: {email_from}")
        print(f"📭 To: {email_to}")
        print(f"🌍 Region: {region}")
        print(f"\n📤 Sending test email...")

        client = boto3.client(
            'ses',
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

        response = client.send_email(
            Source=email_from,
            Destination={'ToAddresses': [email_to]},
            Message={
                'Subject': {'Data': '🧪 Test Notification - Crypto Bot'},
                'Body': {
                    'Text': {'Data': 'Test notification from your crypto bot. AWS SES is working!'}
                }
            }
        )

        print("✅ Email sent successfully via AWS SES!")
        print(f"\n📬 Check your inbox: {email_to}")
        print(f"   Message ID: {response['MessageId']}")
        return True

    except ImportError:
        print("❌ boto3 library not installed")
        print("   Run: pip install boto3")
        return False

    except Exception as e:
        print(f"❌ AWS SES test failed: {e}")
        return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Test notification system')
    parser.add_argument('--telegram', action='store_true', help='Test Telegram only')
    parser.add_argument('--email', action='store_true', help='Test Email only')
    args = parser.parse_args()

    print("\n" + "="*60)
    print("CRYPTO BOT NOTIFICATION TEST")
    print("="*60)

    # Load config
    try:
        config = load_config()
        print("✅ Config loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        sys.exit(1)

    results = {}

    # Test based on arguments
    if args.telegram:
        results['telegram'] = test_telegram(config)
    elif args.email:
        results['email'] = test_email(config)
    else:
        # Test all enabled channels
        if config['notifications'].get('telegram_enabled'):
            results['telegram'] = test_telegram(config)

        if config['notifications'].get('email_enabled'):
            results['email'] = test_email(config)

        if not results:
            print("\n⚠️  No notification channels enabled")
            print("   Enable telegram or email in config_crypto_bybit.json")

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    if results:
        for channel, success in results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{channel.upper()}: {status}")

        all_passed = all(results.values())
        if all_passed:
            print("\n✅ All tests PASSED!")
            print("   Your notification system is ready.")
        else:
            print("\n⚠️  Some tests FAILED")
            print("   Check the error messages above and fix configuration")
            print("\n📖 Setup guides:")
            print("   - docs/TELEGRAM_SETUP_GUIDE.md")
            print("   - docs/EMAIL_SETUP_GUIDE.md")
    else:
        print("⚠️  No tests run (all channels disabled)")

    print("="*60 + "\n")

if __name__ == '__main__':
    main()
