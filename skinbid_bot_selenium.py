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
        url = "https://skinbid.com/market?goodDeals=true&sort=created%23desc&sellType=all&take=120&skip=0"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        logger.info(f"Starting scraping process...")
        logger.info(f"Fetching URL: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.info(f"Response encoding: {response.encoding}")
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch page: {response.status_code}")
                logger.error(f"Response content (first 500 chars): {response.text[:500]}")
                return []
            
            # Parse the response
            soup = BeautifulSoup(response.text, 'html.parser')
            logger.info("Parsing HTML...")
            
            # Log some basic page info
            logger.info(f"Page title: {soup.title.string if soup.title else 'No title'}")
            logger.info(f"Page contains {len(soup.find_all('div'))} div elements")
            logger.info(f"Page contains {len(soup.find_all('a'))} links")
            logger.info(f"Page contains {len(soup.find_all('span'))} spans")
            
            # Log some page content
            logger.info("First 500 chars of page content:")
            logger.info(response.text[:500])
            
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            logger.error(f"Response text: {response.text[:500] if hasattr(response, 'text') else 'No response'}")
            return []
        logger.info("Parsing HTML...")
        
        # Log some basic page info
        logger.info(f"Page title: {soup.title.string if soup.title else 'No title'}")
        logger.info(f"Page contains {len(soup.find_all('div'))} div elements")
        
        # Try multiple selectors since the page structure might have changed
        selectors = [
            "[class*='market-item']",
            "[class*='item']",
            "[class*='product']",
            "[class*='listing']",
            "[class*='marketListing']",
            "[class*='marketEntry']",
            "[class*='marketRow']",
            "div[class*='market']",
            "div[class*='item']",
            "div[class*='product']"
        ]
        
        items = None
        for selector in selectors:
            try:
                items = soup.select(selector)
                logger.info(f"Trying selector '{selector}': Found {len(items)} items")
                if items:
                    logger.info(f"First item HTML structure:")
                    logger.info(items[0].prettify())
                    break
            except Exception as e:
                logger.error(f"Error using selector '{selector}': {e}")
        
        if not items:
            logger.error("No items found with any selector")
            logger.error("Full page HTML structure:")
            logger.error(soup.prettify()[:1000])
            return []
        
        items = None
        for selector in selectors:
            items = soup.select(selector)
            logger.info(f"Trying selector '{selector}': Found {len(items)} items")
            if items:
                logger.info(f"First item HTML: {items[0].prettify()[:1000]}")
                break
        
        if not items:
            logger.error("No items found with any selector")
            logger.error(f"Full page HTML: {soup.prettify()[:1000]}")
            return []
            
        results = []
        logger.info(f"Processing {len(items)} items...")
        
        for item in items:
            try:
                # Log item HTML for debugging
                logger.info(f"Processing item HTML: {item.prettify()[:1000]}")
                
                # Try multiple selectors for name
                name = None
                name_selectors = [
                    "[class*='title']", 
                    "[class*='name']", 
                    "[class*='itemName']", 
                    "[class*='marketName']",
                    "[class*='itemTitle']",
                    "[class*='itemName']"
                ]
                
                for name_selector in name_selectors:
                    try:
                        name_elem = item.select_one(name_selector)
                        if name_elem:
                            name = name_elem.text.strip()
                            logger.info(f"Found name with selector '{name_selector}': {name}")
                            break
                    except Exception as e:
                        logger.error(f"Error finding name with selector '{name_selector}': {e}")
                
                if not name:
                    logger.error("Could not find name in item")
                    logger.error(f"Tried selectors: {name_selectors}")
                    continue
                    
                # Try multiple selectors for discount
                discount = None
                discount_selectors = [
                    "[class*='discount']", 
                    "[class*='discountPercentage']", 
                    "[class*='discountValue']", 
                    "[class*='marketDiscount']",
                    "[class*='itemDiscount']"
                ]
                
                for discount_selector in discount_selectors:
                    try:
                        discount_elem = item.select_one(discount_selector)
                        if discount_elem:
                            discount = discount_elem.text.strip()
                            logger.info(f"Found discount with selector '{discount_selector}': {discount}")
                            break
                    except Exception as e:
                        logger.error(f"Error finding discount with selector '{discount_selector}': {e}")
                
                if not discount:
                    logger.error("Could not find discount in item")
                    logger.error(f"Tried selectors: {discount_selectors}")
                    continue
                    
                try:
                    discount_percent = float(discount.strip('%'))
                    logger.info(f"Successfully parsed discount: {discount_percent}%")
                except ValueError:
                    logger.error(f"Could not convert discount to float: {discount}")
                    continue
                    
                logger.info(f"Processing item: {name} with discount {discount_percent}%")
                logger.info(f"Item HTML structure:")
                logger.info(item.prettify())
                
                # Check if it's a knife or glove
                if any(keyword in name.lower() for keyword in ['knife', 'glove']):
                    logger.info(f"Found knife/glove: {name}")
                    
                    if discount_percent >= MIN_DISCOUNT_PERCENTAGE:
                        logger.info(f"Item meets discount criteria: {discount_percent}%")
                        
                        # Get link
                        link = None
                        for link_elem in item.find_all('a'):
                            if 'href' in link_elem.attrs:
                                link = link_elem['href']
                                if not link.startswith('http'):
                                    link = f"https://skinbid.com{link}"
                                break
                        
                        if link:
                            results.append({
                                'name': name,
                                'discount': discount,
                                'link': link
                            })
                            logger.info(f"Added item to results: {name}")
                        else:
                            logger.error("Could not find link in item")
                else:
                    logger.info(f"Skipping non-knife/glove item: {name}")
            except Exception as e:
                logger.error(f"Error processing item: {e}")
                logger.error(f"Item HTML: {item.prettify()[:1000]}")
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
                     f"Discount: {item['discount']}%\n"
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
        # Check if another instance is running
        try:
            # Try to get updates with a very short timeout
            bot = Application.builder().token(TELEGRAM_BOT_TOKEN).build().bot
            updates = bot.get_updates(timeout=1)
            logger.info("No active instances found. Starting new instance...")
        except telegram.error.Conflict:
            logger.error("Another instance of this bot is already running. Stopping this instance.")
            return
        except Exception as e:
            logger.warning(f"Error checking for active instances: {e}")

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

        # Add error handler
        async def error_handler(update: Update, context: CallbackContext) -> None:
            logger.error(f"Error while handling update: {context.error}")
            logger.error(f"Update that caused error: {update}")
        
        application.add_error_handler(error_handler)

        # Run the bot
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            close_loop=True
        )
        
    except telegram.error.Conflict as e:
        logger.error(f"Bot conflict error: {e}")
        logger.error("Another instance of this bot is already running. Stopping this instance.")
        return
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == '__main__':
    main()
