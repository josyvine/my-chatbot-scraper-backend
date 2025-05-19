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

if not VALID_SCRAPER_API_KEYS:
    print("CRITICAL WARNING: No valid ScraperAPI keys were loaded from environment variables.")
    print("Attempting to use hardcoded fallback ScraperAPI keys. THIS IS NOT SECURE FOR PRODUCTION. Please use environment variables on Render.")
    fallback_keys = [
        'e1b46d8eff3b21afeadf257677bae4dd', '378152f7116a6232d4634bf7d12eec2a',
        '06037a3f065fcd4f868f29c170d0837c2150a7', 'c6c1d589f3dc88619ddc7ef198',
        '38e69420dd78bb074f278d554e07eb7f', '2d16fc2834936dc5a07bccb3d6a09cb0',
        '7a6b83fba134eb2a0f6231da49c6db7f'
    ]
    VALID_SCRAPER_API_KEYS = [key for key in fallback_keys if key and len(key) > 20] 
    if not VALID_SCRAPER_API_KEYS:
         print("CRITICAL ERROR: No ScraperAPI keys available even after fallback. Scraping will fail.")
    else:
        print(f"Loaded {len(VALID_SCRAPER_API_KEYS)} fallback keys. THIS IS NOT SECURE FOR PRODUCTION.")


MAX_CONCURRENT_SCRAPES = min(5, len(VALID_SCRAPER_API_KEYS)) if VALID_SCRAPER_API_KEYS else 1
MIN_CONTENT_LENGTH_FOR_SUMMARY = 200 
DEFAULT_MAX_DEPTH_INTERNAL_SPIDER = 0 
DEFAULT_MAX_LINKS_PER_PAGE_SPIDER = 3
SCRAPER_API_TIMEOUT = 40 
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
MAX_DUCKDUCKGO_RESULTS_TO_PROCESS = 5
