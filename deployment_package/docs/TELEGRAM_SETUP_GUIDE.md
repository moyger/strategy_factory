# Telegram Notifications Setup Guide

This guide will help you set up Telegram notifications for your crypto trading bot. Telegram is **FREE**, instant, and requires only 5 minutes to set up.

---

## Why Telegram?

- ✅ **FREE** - No costs, ever
- ✅ **INSTANT** - 1-2 second delivery
- ✅ **RELIABLE** - 99.9% uptime
- ✅ **WORLDWIDE** - Works in every country
- ✅ **RICH FORMATTING** - Emojis, bold, links
- ✅ **MESSAGE HISTORY** - All alerts stored
- ✅ **CROSS-PLATFORM** - Mobile + Desktop + Web

---

## Step 1: Install Telegram

If you don't have Telegram installed:

**Mobile:**
- iOS: [App Store](https://apps.apple.com/app/telegram-messenger/id686449807)
- Android: [Google Play](https://play.google.com/store/apps/details?id=org.telegram.messenger)

**Desktop:**
- Windows/Mac/Linux: [telegram.org/apps](https://telegram.org/apps)

**Web:**
- [web.telegram.org](https://web.telegram.org)

---

## Step 2: Create Your Telegram Bot (2 minutes)

### 2.1 Open Telegram

Open Telegram app on your phone or desktop.

### 2.2 Find BotFather

In the search bar, type: **@BotFather**

Click on the official **@BotFather** account (verified with blue checkmark).

### 2.3 Create New Bot

Send this command to BotFather:

```
/newbot
```

### 2.4 Choose Bot Name

BotFather will ask: "Alright, a new bot. How are we going to call it?"

Choose a friendly name (can be anything):

```
My Crypto Trading Bot
```

Or:

```
Nick Radge Crypto Bot
```

### 2.5 Choose Bot Username

BotFather will ask: "Now let's choose a username for your bot."

Username must:
- End with "bot" (e.g., `my_crypto_bot`, `radge_bot`)
- Be unique (not taken by someone else)
- Use only letters, numbers, and underscores

Example:

```
my_crypto_trading_bot
```

If taken, try:

```
my_crypto_bot_2025
john_crypto_bot
radge_momentum_bot
```

### 2.6 Copy Your Bot Token

BotFather will respond with:

```
Done! Congratulations on your new bot. You will find it at t.me/your_bot_username.

Use this token to access the HTTP API:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567

For a description of the Bot API, see this page: https://core.telegram.org/bots/api
```

**IMPORTANT:** Copy the entire token starting with numbers and containing a colon `:` and letters.

Example token:
```
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567
```

**Keep this token SECRET!** Anyone with this token can control your bot.

---

## Step 3: Get Your Chat ID (2 minutes)

### 3.1 Start Chat with Your Bot

In Telegram search, find your bot by username (e.g., `@my_crypto_bot_2025`).

Click on it, then click **START** or send any message:

```
Hello
```

### 3.2 Get Your Chat ID

**Method 1: Using Browser (Easiest)**

1. Open your browser
2. Replace `YOUR_BOT_TOKEN` with your actual bot token in this URL:

```
https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
```

Example:
```
https://api.telegram.org/bot1234567890:ABCdefGHIjklMNOpqrsTUVwxyz/getUpdates
```

3. Press Enter
4. You'll see JSON response. Look for:

```json
{
  "ok": true,
  "result": [
    {
      "update_id": 123456789,
      "message": {
        "message_id": 1,
        "from": {
          "id": 987654321,  ← This is your CHAT ID
          ...
        },
        "chat": {
          "id": 987654321,  ← This is your CHAT ID
          ...
        }
      }
    }
  ]
}
```

5. Copy the `"id"` number under `"chat"` - this is your **CHAT ID**

Example Chat ID:
```
987654321
```

**Method 2: Using Command Line**

```bash
curl "https://api.telegram.org/bot1234567890:ABCdefGHIjklMNOpqrsTUVwxyz/getUpdates"
```

Look for `"chat":{"id": 987654321}` in the output.

---

## Step 4: Configure Your Bot (1 minute)

### 4.1 Edit Config File

Open `config_crypto_bybit.json` and update the notifications section:

```json
"notifications": {
    "telegram_enabled": true,
    "telegram_bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
    "telegram_chat_id": "987654321",

    "email_enabled": false,

    "notify_on_trade": true,
    "notify_on_error": true,
    "notify_on_stop_loss": true,
    "notify_on_startup": true,
    "notify_on_rebalance": true
}
```

**Replace:**
- `telegram_bot_token` with your actual bot token (from Step 2.6)
- `telegram_chat_id` with your actual chat ID (from Step 3.2)

### 4.2 Notification Options

**Control what you get notified about:**

```json
"notify_on_startup": true       // Bot starts/restarts
"notify_on_trade": true          // Trades executed
"notify_on_stop_loss": true      // 40% position stop triggered
"notify_on_error": true          // Fatal errors
"notify_on_rebalance": true      // Quarterly rebalancing
```

Set to `false` to disable specific notifications.

---

## Step 5: Test Your Setup

### 5.1 Run Test Script

```bash
cd deployment_package
python test_notifications.py
```

You should receive a test message on Telegram!

### 5.2 Manual Test

Start your bot in dry run mode:

```bash
python live_crypto_bybit.py
```

You should receive a startup notification:

```
🚀 Crypto Trading Bot Started
Mode: DRY RUN
Testnet: True
Strategy: Nick Radge Crypto Hybrid
Position Stops: 40%
```

---

## Troubleshooting

### "Error: Unauthorized"

**Problem:** Bot token is incorrect.

**Solution:**
1. Go back to @BotFather on Telegram
2. Send `/token`
3. Select your bot
4. Copy the new token
5. Update config file

### "Error: Chat not found"

**Problem:** Chat ID is incorrect or you haven't started the bot yet.

**Solution:**
1. Make sure you sent a message to your bot (Step 3.1)
2. Get chat ID again using the browser method (Step 3.2)
3. Make sure chat ID is a number, not a string

### "No notification received"

**Problem:** Bot is not configured or network issue.

**Solution:**
1. Check `telegram_enabled: true` in config
2. Check internet connection
3. Check bot token and chat ID are correct
4. Check firewall/VPS network settings
5. Try sending a message directly to your bot to test

### "Telegram API timeout"

**Problem:** Network connectivity or Telegram servers down (rare).

**Solution:**
1. Check internet connection
2. Wait a few minutes and try again
3. Email notifications will still work if enabled

---

## What Notifications You'll Receive

### Bot Startup
```
🚀 Crypto Trading Bot Started
Mode: DRY RUN
Testnet: True
Strategy: Nick Radge Crypto Hybrid
Position Stops: 40%
```

### Position Stop-Loss
```
🚨 Position Stop-Loss Triggered
Symbol: SOL/USDT
Loss: -42.3%
Position closed
```

### Emergency Stop
```
🚨🚨 EMERGENCY STOP 🚨🚨
Portfolio DD: -51.2%
All positions closed
Bot stopped
```

### Bot Error
```
🚨 Bot Error: Connection timeout
```

### Rebalancing (Quarterly)
```
🔄 Portfolio Rebalanced
Old satellites: [ADA, AVAX, DOGE]
New satellites: [ARB, INJ, SUI]
Trades executed: 6
```

---

## Advanced: Group Notifications

Want to share notifications with your team?

### Create a Group

1. Create a new Telegram group
2. Add your bot to the group
3. Make bot an admin (optional)
4. Get group chat ID (same method as Step 3, but the ID will be negative)

Example group chat ID:
```
-1001234567890
```

Update config:
```json
"telegram_chat_id": "-1001234567890"
```

Now all team members in the group will see notifications!

---

## Security Best Practices

1. **Keep bot token SECRET** - Don't share in public repos
2. **Don't give bot admin powers** - Not needed for notifications
3. **Use environment variables** (optional but recommended):

```bash
export TELEGRAM_BOT_TOKEN="1234567890:ABC..."
export TELEGRAM_CHAT_ID="987654321"
```

Then in code (advanced):
```python
import os
bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')
```

4. **Rotate tokens periodically** - Use @BotFather `/revoke` command

---

## Additional Features (Future)

Telegram bots can do much more than just send notifications:

- **Two-way commands** - Send commands to bot (e.g., "check balance", "close position")
- **Interactive keyboards** - Buttons for actions
- **Rich media** - Send charts, images, files
- **Alerts** - Price alerts, regime changes

These features can be added in future updates!

---

## Cost: FREE Forever

Telegram notifications are **100% FREE** with no limits on:
- Number of messages
- Number of bots
- Message length
- Rich formatting
- File attachments

---

## Support

**Telegram Bot API Documentation:**
- https://core.telegram.org/bots/api

**BotFather Commands:**
- `/newbot` - Create new bot
- `/mybots` - Manage your bots
- `/deletebot` - Delete bot
- `/token` - Regenerate token
- `/setname` - Change bot name
- `/setdescription` - Change bot description
- `/setuserpic` - Set bot profile picture

---

**Setup complete! You should now receive instant trading notifications on Telegram.**

Next: [Email Setup Guide](EMAIL_SETUP_GUIDE.md) (optional backup notifications)
