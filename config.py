import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file for local development

# Your 7 ScraperAPI Keys
# For deployment on Render, set these as individual environment variables
# e.g., SCRAPER_API_KEY_1, SCRAPER_API_KEY_2, etc.
SCRAPER_API_KEYS_CONFIG = [
    os.getenv("SCRAPER_API_KEY_1", "e1b46d8eff3b21afeadf257677bae4dd"),
    os.getenv("SCRAPER_API_KEY_2", "378152f7116a6232d4634bf7d12eec2a"),
    os.getenv("SCRAPER_API_KEY_3", "06037a3f065fcd4f868f29c170d0837c2150a7"),
    os.getenv("SCRAPER_API_KEY_4", "c6c1d589f3dc88619ddc7ef198"),
    os.getenv("SCRAPER_API_KEY_5", "38e69420dd78bb074f278d554e07eb7f"),
    os.getenv("SCRAPER_API_KEY_6", "2d16fc2834936dc5a07bccb3d6a09cb0"),
    os.getenv("SCRAPER_API_KEY_7", "7a6b83fba134eb2a0f6231da49c6db7f") # The one from your Python test
]

# Filter out any placeholder or clearly invalid keys
VALID_SCRAPER_API_KEYS = [
    key for key in SCRAPER_API_KEYS_CONFIG 
    if key and not key.lower().startswith("your_") and len(key) > 20 # Basic validity check
]

if not VALID_SCRAPER_API_KEYS:
    print("CRITICAL WARNING: No valid ScraperAPI keys seem to be configured. Please check .env or environment variables. Scraping will likely fail.")
    # In a real app, you might want to raise an exception or prevent startup
    # For now, functions using keys will also check.

# Max number of concurrent ScraperAPI calls for batch operations (e.g., # command)
# Should not exceed the number of valid keys or a sensible limit like 5.
MAX_CONCURRENT_SCRAPES = 5 

# Minimum length of extracted content to be considered "substantial" for summarization
MIN_CONTENT_LENGTH_FOR_SUMMARY = 250 # characters

# Default depth for internal spidering within a single base URL
DEFAULT_MAX_DEPTH_INTERNAL_SPIDER = 1 # 0 = base URL only, 1 = base URL + one level of internal links

# Default max number of internal links to follow per page during spidering
DEFAULT_MAX_LINKS_PER_PAGE_SPIDER = 3

# Timeout for individual ScraperAPI calls in seconds
SCRAPER_API_TIMEOUT = 45

# User-Agent for scraping requests (can be rotated for better results)
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36"

# For DuckDuckGo search results
MAX_DUCKDUCKGO_RESULTS_TO_PROCESS = 5
