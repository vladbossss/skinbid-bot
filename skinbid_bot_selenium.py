import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
import schedule
import time
import logging
from config import TELEGRAM_BOT_TOKEN, MIN_DISCOUNT_PERCENTAGE, CHECK_INTERVAL_MINUTES

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global application instance
application = None

# Store group subscriptions
subscribed_groups = set()

# Track last notified items to avoid duplicates
last_notified_items = set()

def scrape_skinbid():
    """Scrape SkinBid.com using requests and BeautifulSoup."""
    try:
        url = "https://skinbid.com/market?sort=created%23desc&take=120&skip=0"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to fetch page: {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select("[class*='market-item']")
        results = []
        
        for item in items:
            try:
                name = item.select_one("[class*='title']").text.strip()
                discount = item.select_one("[class*='discount']").text.strip()
                discount_percent = float(discount.strip('%'))
                
                if any(keyword in name.lower() for keyword in ['knife', 'glove']):
                    if discount_percent >= MIN_DISCOUNT_PERCENTAGE:
                        link = item.find('a')['href']
                        if not link.startswith('http'):
                            link = f"https://skinbid.com{link}"
                            
                        results.append({
                            'name': name,
                            'discount': discount,
                            'link': link
                        })
                        logger.info(f"Found item: {name} with discount {discount_percent}%")
            except Exception as e:
                logger.error(f"Error processing item: {e}")
                continue
        
        logger.info(f"Found {len(results)} items meeting criteria")
        if not results:
            logger.info("No knives or gloves found with sufficient discount")
        return results
        
    except Exception as e:
        logger.error(f"Error scraping SkinBid: {e}")
        return []

async def start(update: Update, context: CallbackContext) -> None:
    """Handle the /start command."""
    chat_id = update.effective_chat.id
    if chat_id not in subscribed_groups:
        subscribed_groups.add(chat_id)
        await update.message.reply_text(
            f'I will now notify this group about new CS2 knives and gloves with {MIN_DISCOUNT_PERCENTAGE}% or higher discount on SkinBid.com\n'
            'Use /stop to unsubscribe\n'
            'Use /checknow to check immediately'
        )
    else:
        await update.message.reply_text('This group is already subscribed!')

async def stop(update: Update, context: CallbackContext) -> None:
    """Handle the /stop command."""
    chat_id = update.effective_chat.id
    if chat_id in subscribed_groups:
        subscribed_groups.remove(chat_id)
        await update.message.reply_text('This group has been unsubscribed.')
    else:
        await update.message.reply_text('This group is not subscribed.')

async def checknow(update: Update, context: CallbackContext) -> None:
    """Handle the /checknow command."""
    chat_id = update.effective_chat.id
    if chat_id not in subscribed_groups:
        await update.message.reply_text('Please subscribe first using /start')
        return
    
    items = scrape_skinbid()
    if items:
        for item in items:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"New item found!\n"
                     f"Name: {item['name']}\n"
                     f"Discount: {item['discount']}\n"
                     f"Link: {item['link']}\n"
                     "---"
            )
    else:
        await context.bot.send_message(chat_id=chat_id, text="No items found with 11% or higher discount.")

async def reload_config():
    """Reload configuration from config.py"""
    global MIN_DISCOUNT_PERCENTAGE
    try:
        import importlib
        import config
        importlib.reload(config)
        MIN_DISCOUNT_PERCENTAGE = config.MIN_DISCOUNT_PERCENTAGE
        logger.info(f"Configuration reloaded. New minimum discount: {MIN_DISCOUNT_PERCENTAGE}%")
    except Exception as e:
        logger.error(f"Error reloading configuration: {e}")

async def check_items(context):
    """Check for new items periodically."""
    try:
        items = scrape_skinbid()
        if items:
            for chat_id in subscribed_groups:
                for item in items:
                    # Create a unique identifier for the item
                    item_id = f"{item['name']}_{item['price']}_{item['discount']}"
                    
                    # Only notify if this is a new item and discount meets criteria
                    if item_id not in last_notified_items and float(item['discount'].strip('%')) >= MIN_DISCOUNT_PERCENTAGE:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"New item found!\n"
                            f"Name: {item['name']}\n"
                            f"Price: {item['price']}\n"
                            f"Discount: {item['discount']}%\n"
                            f"Link: {item['link']}"
                        )
                        # Add to set of notified items
                        last_notified_items.add(item_id)
                        # Remove old items to prevent memory issues
                        if len(last_notified_items) > 1000:
                            last_notified_items.pop()
    except Exception as e:
        logger.error(f"Error in check_items: {e}")

def main():
    """Start the bot."""
    try:
        # Create the Application
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("stop", stop))
        application.add_handler(CommandHandler("checknow", checknow))

        # Schedule periodic checks
        schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_items)
        # Schedule config reload every 5 minutes
        schedule.every(5).minutes.do(reload_config)

        # Run the bot
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == '__main__':
    main()
