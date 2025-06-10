# SkinBid CS2 Telegram Bot

A Telegram bot that monitors SkinBid.com for new CS2 knives and gloves with discounts of 9% or higher.

## Features

- Monitors SkinBid.com for new CS2 items (knives and gloves)
- Sends notifications to Telegram groups when items with 9% or higher discount are found
- Checks for new items every 5 minutes
- Automatic configuration reload every 5 minutes
- Runs continuously on Railway.app

## Deployment

1. Create a Railway account at https://railway.app/
2. Install the Railway CLI:
   ```bash
   curl -fsSL https://railway.app/install.sh | sh
   ```
3. Login to Railway:
   ```bash
   railway login
   ```
4. Deploy the bot:
   ```bash
   railway up
   ```

## Configuration

The bot uses environment variables for configuration. You can set these in Railway's dashboard:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `MIN_DISCOUNT_PERCENTAGE`: Minimum discount percentage (default: 9)
- `CHECK_INTERVAL_MINUTES`: Check interval in minutes (default: 5)

## Usage

1. Add the bot to your Telegram group
2. Type `/start` to subscribe to notifications
3. The bot will check for new items every 5 minutes
4. Use `/checknow` to perform an immediate check
5. Use `/stop` to unsubscribe from notifications

## Requirements

- Python 3.11+
- Chrome browser
- ChromeDriver
- Telegram bot token

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Get a Telegram bot token:
   - Open Telegram and search for @BotFather
   - Send `/newbot` to create a new bot
   - Follow the instructions to get your bot token

3. Replace 'YOUR_BOT_TOKEN' in `skinbid_bot.py` with your actual bot token

4. Run the bot:
```bash
python skinbid_bot.py
```

## Usage

- `/start` - Subscribe to receive alerts
- `/stop` - Unsubscribe from alerts
- `/checknow` - Check for items immediately

The bot will automatically check for new items every 5 minutes and notify you when it finds any CS2 knives or gloves with 11% or higher discount.

## Note

You may need to adjust the HTML selectors in the `scrape_skinbid()` function based on the actual structure of SkinBid.com. The current selectors are placeholders and will need to be modified to match the actual website structure.
