from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional

# Relative imports for sibling modules
from .scraper_service import (
    process_spider_crawl_batch_endpoint_logic, 
    process_duckduckgo_search_and_scrape_endpoint_logic
)
from .config import (
    DEFAULT_MAX_DEPTH_INTERNAL_SPIDER, 
    DEFAULT_MAX_LINKS_PER_PAGE_SPIDER,
    MAX_DUCKDUCKGO_RESULTS_TO_PROCESS
)

app = FastAPI(
    title="Chatbot Scraper Backend API",
    description="Handles web scraping tasks for the chatbot, using ScraperAPI and other tools.",
    version="1.0.0"
)

# Configure CORS
# Adjust allow_origins for production to your chatbot's frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins for now, restrict in production
    allow_credentials=True,
    allow_methods=["POST", "GET"], # Specify allowed methods
    allow_headers=["*"], # Allows all headers
)

# --- Request Models ---
class SpiderCrawlRequest(BaseModel):
    query: str
    base_urls: List[HttpUrl] = Field(..., min_items=1, max_items=10) # Ensure at least one URL, max 10
    max_depth_internal: Optional[int] = DEFAULT_MAX_DEPTH_INTERNAL_SPIDER
    max_links_per_url: Optional[int] = DEFAULT_MAX_LINKS_PER_PAGE_SPIDER

class DuckDuckGoScrapeRequest(BaseModel):
    query: str
    num_results: Optional[int] = Field(default=MAX_DUCKDUCKGO_RESULTS_TO_PROCESS, ge=1, le=10)


# --- API Endpoints ---
@app.post("/api/spider-crawl-batch")
async def api_spider_crawl_batch(request_data: SpiderCrawlRequest, request: Request):
    client_host = request.client.host
    print(f"Received /api/spider-crawl-batch request from {client_host} for query: '{request_data.query}' with base URLs: {request_data.base_urls}")
    try:
        result = await process_spider_crawl_batch_endpoint_logic(
            request_data.query,
            [str(url) for url in request_data.base_urls], # Convert Pydantic HttpUrl to string
            request_data.max_depth_internal,
            request_data.max_links_per_url
        )
        if result.get("error"): # If the service itself reports a configuration error
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        print(f"Unhandled error in /api/spider-crawl-batch endpoint for query '{request_data.query}': {e}")
        # Log the full exception traceback here in a real application
        raise HTTPException(status_code=500, detail=f"Internal server error during spider crawl: {str(e)}")

@app.post("/api/duckduckgo-scrape")
async def api_duckduckgo_scrape(request_data: DuckDuckGoScrapeRequest, request: Request):
    client_host = request.client.host
    print(f"Received /api/duckduckgo-scrape request from {client_host} for query: '{request_data.query}'")
    try:
        result = await process_duckduckgo_search_and_scrape_endpoint_logic(
            request_data.query,
            request_data.num_results
        )
        if result.get("error"): # If the service itself reports a configuration error
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        print(f"Unhandled error in /api/duckduckgo-scrape endpoint for query '{request_data.query}': {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error during DuckDuckGo scrape: {str(e)}")

@app.get("/")
async def read_root():
    return {"message": "Chatbot Scraper API is running. Use POST requests to /api/spider-crawl-batch or /api/duckduckgo-scrape."}

# To run locally (for development):
# uvicorn main:app --reload --port 8008
# (Ensure .env file with API keys is in the same directory as main.py and config.py)
# For Render, you'll use a Procfile or their dashboard settings to specify the start command,
# e.g., gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT
