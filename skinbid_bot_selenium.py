from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
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

def setup_driver():
    """Set up Chrome WebDriver with headless mode."""
    options = Options()
    options.add_argument('--headless=new')  # Run in headless mode
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def scrape_skinbid():
    """Scrape SkinBid.com using Selenium."""
    try:
        driver = setup_driver()
        url = "https://skinbid.com/market?sort=created%23desc&take=120&skip=0"
        
        try:
            driver.get(url)
            
            # Wait for items to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='market-item']"))
            )
            
            # Get all items
            items = driver.find_elements(By.CSS_SELECTOR, "[class*='market-item']")
            results = []
            
            for item in items:
                try:
                    # Get item name
                    name = item.find_element(By.CSS_SELECTOR, "[class*='title']").text
                    
                    # Get discount percentage
                    discount = item.find_element(By.CSS_SELECTOR, "[class*='discount']").text
                    discount_percent = float(discount.strip('%'))
                    
                    # Check if it's a knife or glove
                    if any(keyword in name.lower() for keyword in ['knife', 'glove']):
                        if discount_percent >= MIN_DISCOUNT_PERCENTAGE:
                            # Get link
                            link = item.find_element(By.TAG_NAME, "a").get_attribute("href")
                            
                            results.append({
                                'name': name,
                                'discount': discount,
                                'link': link
                            })
                except Exception as e:
                    logger.error(f"Error processing item: {e}")
                    continue
            
            logger.info(f"Found {len(results)} items meeting criteria")
            if not results:
                logger.info("No knives or gloves found with sufficient discount")
            return results
        
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return []
        
        finally:
            try:
                driver.quit()
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
    
    except Exception as e:
        logger.error(f"Error in scrape_skinbid: {e}")
        return []
            
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
