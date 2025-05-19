import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

SCRAPER_API_KEYS_CONFIG: List[str] = [
    os.getenv("SCRAPER_API_KEY_1", ""),
    os.getenv("SCRAPER_API_KEY_2", ""),
    os.getenv("SCRAPER_API_KEY_3", ""),
    os.getenv("SCRAPER_API_KEY_4", ""),
    os.getenv("SCRAPER_API_KEY_5", ""),
    os.getenv("SCRAPER_API_KEY_6", ""),
    os.getenv("SCRAPER_API_KEY_7", "")
]

VALID_SCRAPER_API_KEYS: List[str] = [
    key for key in SCRAPER_API_KEYS_CONFIG if key and len(key) > 20 and not key.lower().startswith("your_")
]

# Fallback to your provided keys if environment variables are not set (for easier local testing startup)
# IMPORTANT: For Render deployment, ALWAYS use environment variables.
if not VALID_SCRAPER_API_KEYS:
    print("WARNING: No valid ScraperAPI keys loaded from environment. Using hardcoded fallbacks for now. SET ENVIRONMENT VARIABLES ON RENDER.")
    VALID_SCRAPER_API_KEYS = [
        'e1b46d8eff3b21afeadf257677bae4dd', '378152f7116a6232d4634bf7d12eec2a',
        '06037a3f065fcd4f868f29c170d0837c2150a7', 'c6c1d589f3dc88619ddc7ef198',
        '38e69420dd78bb074f278d554e07eb7f', '2d16fc2834936dc5a07bccb3d6a09cb0',
        '7a6b83fba134eb2a0f6231da49c6db7f'
    ]
    VALID_SCRAPER_API_KEYS = [key for key in VALID_SCRAPER_API_KEYS if key and len(key) > 20] # Re-filter

if not VALID_SCRAPER_API_KEYS:
    print("CRITICAL ERROR: No ScraperAPI keys available after checking env and fallbacks. Scraping will fail.")
    # Or raise an exception to prevent startup without keys
    # raise ValueError("No valid ScraperAPI keys configured.")

MAX_CONCURRENT_SCRAPES = min(5, len(VALID_SCRAPER_API_KEYS)) if VALID_SCRAPER_API_KEYS else 1
MIN_CONTENT_LENGTH_FOR_SUMMARY = 200
DEFAULT_MAX_DEPTH_INTERNAL_SPIDER = 0 # Set to 0 for less ScraperAPI usage initially
DEFAULT_MAX_LINKS_PER_PAGE_SPIDER = 3
SCRAPER_API_TIMEOUT = 40
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
MAX_DUCKDUCKGO_RESULTS_TO_PROCESS = 5
