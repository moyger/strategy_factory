# Email Notifications Setup Guide

This guide will help you set up email notifications for your crypto trading bot. Email serves as a great **backup** to Telegram or for users who prefer traditional email alerts.

---

## Email Provider Options

We support 3 email providers:

| Provider | Cost | Setup Time | Best For |
|----------|------|------------|----------|
| **Gmail** | FREE (500/day) | 10 min | Personal use, easy setup |
| **SendGrid** | FREE (100/day) | 15 min | Better deliverability |
| **AWS SES** | $0.10/1000 emails | 20 min | Enterprise, high volume |

---

## Option 1: Gmail (Recommended for Personal Use)

### Pros:
- ✅ FREE (500 emails/day limit)
- ✅ Easy setup
- ✅ Familiar to everyone
- ✅ Works immediately

### Cons:
- ⚠️ May go to spam folder initially
- ⚠️ Requires "App Password" (2FA must be enabled)
- ⚠️ 500 emails/day limit

---

### Step 1: Enable 2-Factor Authentication

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Under "Signing in to Google", click **2-Step Verification**
3. Follow prompts to enable 2FA (using phone SMS or authenticator app)

**Why needed?** App Passwords require 2FA to be enabled for security.

---

### Step 2: Generate App Password

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Sign in if prompted
3. Under "App passwords", enter app name: `Crypto Trading Bot`
4. Click **Create**
5. Google will show a 16-character password like: `abcd efgh ijkl mnop`
6. **Copy this password** - you won't see it again!

**Example App Password:**
```
abcd efgh ijkl mnop
```

**IMPORTANT:** Use this app password, NOT your regular Gmail password.

---

### Step 3: Configure Bot

Edit `config_crypto_bybit.json`:

```json
"notifications": {
    "telegram_enabled": true,
    "telegram_bot_token": "...",
    "telegram_chat_id": "...",

    "email_enabled": true,
    "email_provider": "gmail",
    "email_from": "your_email@gmail.com",
    "email_to": "your_email@gmail.com",
    "email_smtp_host": "smtp.gmail.com",
    "email_smtp_port": 587,
    "email_password": "abcd efgh ijkl mnop",
    "email_use_tls": true,

    "notify_on_trade": true,
    "notify_on_error": true,
    "notify_on_stop_loss": true,
    "notify_on_startup": true,
    "notify_on_rebalance": true
}
```

**Replace:**
- `email_from` with your Gmail address
- `email_to` with recipient email (can be same or different)
- `email_password` with the 16-character app password (remove spaces)

**Example:**
```json
"email_from": "john.trader@gmail.com",
"email_to": "john.trader@gmail.com",
"email_password": "abcdefghijklmnop"
```

---

### Step 4: Test Gmail Setup

```bash
cd deployment_package
python test_notifications.py --email
```

You should receive a test email!

**Check spam folder** if you don't see it in inbox.

---

### Step 5: Prevent Spam Filtering

**First email might go to spam.** To fix:

1. Open Gmail
2. Find the test email in Spam folder
3. Click "Not spam" or drag to Inbox
4. (Optional) Create filter: Settings → Filters → Create new filter → From: your_email@gmail.com → Never send to Spam

---

## Option 2: SendGrid (Better Deliverability)

### Pros:
- ✅ FREE tier (100 emails/day)
- ✅ Better deliverability than Gmail
- ✅ Professional email service
- ✅ Detailed analytics

### Cons:
- ⚠️ Requires signup and verification
- ⚠️ More complex setup

---

### Step 1: Create SendGrid Account

1. Go to [signup.sendgrid.com](https://signup.sendgrid.com/)
2. Sign up (FREE account)
3. Verify your email address
4. Complete profile setup

---

### Step 2: Create API Key

1. Log in to [SendGrid Dashboard](https://app.sendgrid.com/)
2. Go to Settings → API Keys
3. Click "Create API Key"
4. Name: `Crypto Trading Bot`
5. Permissions: **Full Access** (or at minimum "Mail Send")
6. Click "Create & View"
7. **Copy the API Key** - you won't see it again!

**Example API Key:**
```
SG.1234567890abcdefghij.KLMNOPQRSTUVWXYZ1234567890abcdefghij
```

---

### Step 3: Verify Sender Identity

SendGrid requires sender verification (anti-spam):

**Option A: Single Sender Verification (Easiest)**

1. Go to Settings → Sender Authentication → Single Sender Verification
2. Click "Create New Sender"
3. Fill in your details:
   - From Name: `Crypto Trading Bot`
   - From Email: `your_email@gmail.com` (or any email you own)
   - Reply To: Same as From Email
4. Submit
5. Check your email for verification link
6. Click verification link

**Option B: Domain Authentication (Advanced)**

For professional custom domain emails (e.g., `bot@yourdomain.com`).

---

### Step 4: Configure Bot

Edit `config_crypto_bybit.json`:

```json
"notifications": {
    "telegram_enabled": true,
    "telegram_bot_token": "...",
    "telegram_chat_id": "...",

    "email_enabled": true,
    "email_provider": "sendgrid",
    "email_from": "your_email@gmail.com",
    "email_to": "recipient@example.com",
    "sendgrid_api_key": "SG.1234567890abcdefghij.KLMNOPQRST...",

    "notify_on_trade": true,
    "notify_on_error": true,
    "notify_on_stop_loss": true,
    "notify_on_startup": true,
    "notify_on_rebalance": true
}
```

**Replace:**
- `email_from` with verified sender email
- `email_to` with recipient email
- `sendgrid_api_key` with your API key

---

### Step 5: Test SendGrid

```bash
python test_notifications.py --email
```

Check for email (should arrive in inbox, not spam).

---

## Option 3: AWS SES (Enterprise)

### Pros:
- ✅ Extremely cheap ($0.10 per 1,000 emails)
- ✅ Highly reliable
- ✅ Scalable
- ✅ Professional

### Cons:
- ⚠️ Requires AWS account
- ⚠️ More complex setup
- ⚠️ Starts in "sandbox mode" (limited)

---

### Step 1: Create AWS Account

1. Go to [aws.amazon.com](https://aws.amazon.com/)
2. Create account (requires credit card)
3. Complete verification

---

### Step 2: Enable AWS SES

1. Log in to AWS Console
2. Search for "SES" (Simple Email Service)
3. Select region (e.g., us-east-1)
4. Go to "Verified identities"
5. Click "Create identity"

---

### Step 3: Verify Email Address

1. Choose "Email address"
2. Enter your email: `your_email@example.com`
3. Click "Create identity"
4. Check your email for verification link
5. Click verification link

---

### Step 4: Request Production Access

By default, SES starts in "sandbox mode" (can only send to verified emails).

To send to any email:

1. Go to SES Dashboard
2. Click "Get set up" or "Request production access"
3. Fill out form explaining use case: "Trading bot notifications"
4. Submit (usually approved in 24 hours)

**For testing:** Can skip this step and just send to verified emails.

---

### Step 5: Create IAM User

1. Go to IAM (Identity and Access Management)
2. Users → Add user
3. Name: `crypto-bot-ses`
4. Access type: **Programmatic access**
5. Permissions: Attach `AmazonSESFullAccess` policy
6. Create user
7. **Copy Access Key ID and Secret Access Key**

---

### Step 6: Configure Bot

Edit `config_crypto_bybit.json`:

```json
"notifications": {
    "telegram_enabled": true,
    "telegram_bot_token": "...",
    "telegram_chat_id": "...",

    "email_enabled": true,
    "email_provider": "ses",
    "email_from": "your_email@example.com",
    "email_to": "recipient@example.com",
    "aws_ses_region": "us-east-1",
    "aws_access_key": "AKIAIOSFODNN7EXAMPLE",
    "aws_secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",

    "notify_on_trade": true,
    "notify_on_error": true,
    "notify_on_stop_loss": true,
    "notify_on_startup": true,
    "notify_on_rebalance": true
}
```

---

### Step 7: Test AWS SES

```bash
pip install boto3
python test_notifications.py --email
```

---

## Email Notification Features

### HTML Email Templates

All emails are sent in beautiful HTML format with:

- **Color-coded headers** based on event type
- **Green** for startup
- **Blue** for trades
- **Red** for stop-loss
- **Orange** for rebalancing
- **Professional formatting**

### Email Subjects

Automatically generated based on event:

- `🚀 Crypto Bot Started - Mode: DRY RUN`
- `💰 Trade Executed - BUY SOL/USDT`
- `🚨 Stop-Loss Triggered - SOL/USDT -42.3%`
- `🔄 Portfolio Rebalanced - 6 trades executed`
- `❌ Bot Error Alert - Connection timeout`

### Example Email

**Subject:** `🚨 Stop-Loss Triggered - SOL/USDT -42.3%`

**Body:**
```
Nick Radge Crypto Hybrid Bot

🚨 Position Stop-Loss Triggered
Symbol: SOL/USDT
Loss: -42.3%
Position closed

---
Automated notification from your Crypto Trading Bot
Timestamp: 2025-10-15 14:23:45
```

---

## Troubleshooting

### Gmail: "Username and Password not accepted"

**Problem:** Using regular Gmail password instead of App Password.

**Solution:**
1. Enable 2FA on Google account
2. Generate App Password (Step 2 above)
3. Use 16-character app password in config

### Gmail: Emails going to spam

**Problem:** Gmail treats automated emails as spam initially.

**Solution:**
1. Mark first email as "Not spam"
2. Create filter to never send to spam
3. (Advanced) Use SendGrid for better deliverability

### SendGrid: "Sender not verified"

**Problem:** Haven't verified sender email.

**Solution:**
1. Complete Single Sender Verification (Step 3 above)
2. Check verification email and click link

### SendGrid: "Forbidden"

**Problem:** API key doesn't have permission.

**Solution:**
1. Regenerate API key with "Full Access" or "Mail Send" permission

### AWS SES: "Email address not verified"

**Problem:** SES is in sandbox mode.

**Solution:**
1. Verify recipient email in SES console
2. OR request production access

### AWS SES: "AccessDeniedException"

**Problem:** IAM user doesn't have SES permissions.

**Solution:**
1. Add `AmazonSESFullAccess` policy to IAM user

### No emails received

**Check:**
1. `email_enabled: true` in config
2. Check spam/junk folder
3. Verify "From" email is correct
4. Check bot logs for error messages
5. Test with `test_notifications.py --email`

---

## Cost Comparison

| Provider | Free Tier | Paid Pricing | Best For |
|----------|-----------|--------------|----------|
| **Gmail** | 500/day | N/A (personal use) | Personal trading |
| **SendGrid** | 100/day | $15/mo (40K/day) | Small teams |
| **AWS SES** | 1,000/day | $0.10/1K emails | High volume |

**For typical crypto bot:**
- Startup: 1 email/day
- Stop-loss: ~1-2 emails/month
- Rebalancing: 1 email/quarter
- **Total: ~35 emails/month** (well within all free tiers)

---

## Multiple Recipients

Want to send notifications to multiple people?

### Gmail/SendGrid:

```json
"email_to": "person1@example.com, person2@example.com, person3@example.com"
```

### AWS SES (advanced):

Modify code to support multiple recipients (requires code change).

---

## Security Best Practices

1. **Use App Passwords** (Gmail) - Never use main password
2. **Rotate API Keys** periodically
3. **Use Environment Variables** for sensitive data:

```bash
export EMAIL_PASSWORD="your_app_password"
export SENDGRID_API_KEY="SG...."
export AWS_SECRET_KEY="..."
```

4. **Don't commit secrets** to Git
5. **Limit API Key permissions** to minimum required

---

## Telegram + Email: Best of Both Worlds

**Recommended Setup:**

```json
"notifications": {
    "telegram_enabled": true,
    "email_enabled": true,

    // Telegram for instant alerts
    "notify_on_startup": true,
    "notify_on_error": true,
    "notify_on_stop_loss": true,

    // Email for record-keeping
    "notify_on_rebalance": true,
    "notify_on_trade": true
}
```

**Why both?**
- Telegram = Instant, always with you
- Email = Permanent record, searchable history
- Redundancy if one fails

---

## Future Enhancements

Possible email features to add:

- **Daily summaries** - End-of-day performance report
- **Weekly reports** - Portfolio performance charts
- **Attachments** - CSV trade logs, equity curves
- **Rich charts** - Embedded performance graphs
- **Priority levels** - Different emails for different severity

---

## Support

**Gmail Help:**
- [App Passwords Guide](https://support.google.com/accounts/answer/185833)

**SendGrid Help:**
- [SendGrid Docs](https://docs.sendgrid.com/)
- [API Reference](https://docs.sendgrid.com/api-reference/mail-send/mail-send)

**AWS SES Help:**
- [SES Documentation](https://docs.aws.amazon.com/ses/)
- [Getting Started](https://docs.aws.amazon.com/ses/latest/dg/getting-started.html)

---

**Setup complete! You should now receive trading notifications via email.**

**Recommended:** Set up both [Telegram](TELEGRAM_SETUP_GUIDE.md) (primary) + Email (backup) for maximum reliability.
