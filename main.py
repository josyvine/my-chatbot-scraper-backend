from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field 
from typing import List, Optional, Any, Dict

# Corrected: Direct imports for modules in the same directory
from scraper_service import (
    process_spider_crawl_batch_endpoint_logic, 
    process_duckduckgo_search_and_scrape_endpoint_logic
)
from config import (
    DEFAULT_MAX_DEPTH_INTERNAL_SPIDER, 
    DEFAULT_MAX_LINKS_PER_PAGE_SPIDER,
    MAX_DUCKDUCKGO_RESULTS_TO_PROCESS,
    VALID_SCRAPER_API_KEYS,
    MAX_CONCURRENT_SCRAPES # Ensure this is available for startup log
)

app = FastAPI(
    title="Chatbot Scraper Backend API",
    description="Handles web scraping tasks for the chatbot, using ScraperAPI and other tools.",
    version="1.0.4" # Incremented version
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"], 
    allow_headers=["*"], 
)

class SpiderCrawlRequest(BaseModel):
    query: str
    base_urls: List[HttpUrl] = Field(..., min_length=1, max_length=10) 
    max_depth_internal: int = DEFAULT_MAX_DEPTH_INTERNAL_SPIDER
    max_links_per_url: int = DEFAULT_MAX_LINKS_PER_PAGE_SPIDER

class DuckDuckGoScrapeRequest(BaseModel):
    query: str
    num_results: int = Field(default=MAX_DUCKDUCKGO_RESULTS_TO_PROCESS, ge=1, le=10)

class ScrapeResponse(BaseModel):
    aggregated_content: Optional[str] = None
    all_errors: List[str] = []

class DuckDuckGoScrapeResponse(BaseModel):
    aggregated_search_content: Optional[str] = None
    sources: List[Dict[str, str]] = []
    all_errors: List[str] = []

class ErrorResponse(BaseModel):
    detail: str

@app.on_event("startup")
async def startup_event():
    if not VALID_SCRAPER_API_KEYS:
        print("FATAL: Application starting without any valid ScraperAPI keys. Scraping endpoints will likely fail or use insecure fallbacks.")
    else:
        # MAX_CONCURRENT_SCRAPES is defined in config.py and imported
        print(f"FastAPI application startup complete. {len(VALID_SCRAPER_API_KEYS)} ScraperAPI key(s) loaded. MAX_CONCURRENT_SCRAPES set to {MAX_CONCURRENT_SCRAPES}.")
    print(f"Default internal crawl depth: {DEFAULT_MAX_DEPTH_INTERNAL_SPIDER}, max links per page: {DEFAULT_MAX_LINKS_PER_PAGE_SPIDER}")

@app.post("/api/spider-crawl-batch", response_model=ScrapeResponse, responses={500: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
async def api_spider_crawl_batch(request_data: SpiderCrawlRequest, request: Request):
    client_host = request.client.host if request.client else "unknown"
    print(f"Received /api/spider-crawl-batch request from {client_host} for query: '{request_data.query}' with {len(request_data.base_urls)} base URLs.")

    if not VALID_SCRAPER_API_KEYS: # Check if any valid keys are loaded
        raise HTTPException(status_code=503, detail="Server configuration error: No valid ScraperAPI keys available. Please check server logs and environment variables.")

    try:
        str_base_urls = [str(url) for url in request_data.base_urls]

        result = await process_spider_crawl_batch_endpoint_logic(
            request_data.query,
            str_base_urls,
            request_data.max_depth_internal,
            request_data.max_links_per_url
        )
        return ScrapeResponse(**result) 
    except Exception as e:
        print(f"Unhandled error in /api/spider-crawl-batch endpoint for query '{request_data.query}': {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=f"Internal server error during spider crawl: {str(e)}")

@app.post("/api/duckduckgo-scrape", response_model=DuckDuckGoScrapeResponse, responses={500: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
async def api_duckduckgo_scrape(request_data: DuckDuckGoScrapeRequest, request: Request):
    client_host = request.client.host if request.client else "unknown"
    print(f"Received /api/duckduckgo-scrape request from {client_host} for query: '{request_data.query}'")

    if not VALID_SCRAPER_API_KEYS:
        raise HTTPException(status_code=503, detail="Server configuration error: No valid ScraperAPI keys available. Please check server logs and environment variables.")

    try:
        result = await process_duckduckgo_search_and_scrape_endpoint_logic(
            request_data.query,
            request_data.num_results
        )
        return DuckDuckGoScrapeResponse(**result)
    except Exception as e:
        print(f"Unhandled error in /api/duckduckgo-scrape endpoint for query '{request_data.query}': {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error during DuckDuckGo scrape: {str(e)}")

@app.get("/", include_in_schema=False) 
async def read_root():
    return {"message": "Chatbot Scraper API is running. Version 1.0.4. See /docs for API documentation."}
