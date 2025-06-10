# Configuration settings

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = '7569089797:AAGtbPWSi-KgzKi7Y87qYRn_b6FgTzhYu4c'

# Minimum discount percentage to notify about
MIN_DISCOUNT_PERCENTAGE = 9

# How often to check for new items (in minutes)
CHECK_INTERVAL_MINUTES = 5

# URL to monitor
BASE_URL = 'https://skinbid.com/market?sort=created%23desc&sellType=all&take=120&skip=0'

# CSS selectors for scraping (these will be adjusted after inspecting the page)
SELECTORS = {
    'items': '',  # Will be updated after inspecting the page
    'name': '',   # Will be updated after inspecting the page
    'price': '',  # Will be updated after inspecting the page
    'discount': '', # Will be updated after inspecting the page
    'link': ''    # Will be updated after inspecting the page
}

# Categories to monitor
CATEGORIES = {
    'knives': ['knife', 'karambit', 'm9', 'bayonet', 'flip', 'gut', 'huntsman', 'falchion', 'ursus', 'talon', 'stiletto', 'shadow', 'butterfly', 'navaja', 'daggers', 'bowie'],
    'gloves': ['glove', 'sport', 'bloodhound', 'handwraps', 'specialist', 'hydra', 'broken', 'sleeves', 'sleeve', 'specialist', 'hydra', 'broken', 'sleeves', 'sleeve']
}
