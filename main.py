from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field # HttpUrl for automatic URL validation
from typing import List, Optional, Any, Dict

# Corrected imports for modules in the same directory
from scraper_service import (
    process_spider_crawl_batch_endpoint_logic, 
    process_duckduckgo_search_and_scrape_endpoint_logic
)
from config import (
    DEFAULT_MAX_DEPTH_INTERNAL_SPIDER, 
    DEFAULT_MAX_LINKS_PER_PAGE_SPIDER,
    MAX_DUCKDUCKGO_RESULTS_TO_PROCESS,
    VALID_SCRAPER_API_KEYS # Import to check if keys are loaded
)

app = FastAPI(
    title="Chatbot Scraper Backend API",
    description="Handles web scraping tasks for the chatbot, using ScraperAPI and other tools.",
    version="1.0.1" # Incremented version
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development. Restrict this to your chatbot's actual domain in production.
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"], # Added OPTIONS for preflight requests
    allow_headers=["*"], 
)

# --- Request Pydantic Models ---
class SpiderCrawlRequest(BaseModel):
    query: str
    base_urls: List[HttpUrl] = Field(..., min_length=1, max_length=10) 
    max_depth_internal: int = DEFAULT_MAX_DEPTH_INTERNAL_SPIDER
    max_links_per_url: int = DEFAULT_MAX_LINKS_PER_PAGE_SPIDER

class DuckDuckGoScrapeRequest(BaseModel):
    query: str
    num_results: int = Field(default=MAX_DUCKDUCKGO_RESULTS_TO_PROCESS, ge=1, le=10)

# --- Response Pydantic Models (Optional but good practice) ---
class ScrapeResponse(BaseModel):
    aggregated_content: Optional[str] = None
    all_errors: List[str] = []
    # images_to_summarize: Optional[List[str]] = None # If you implement image selection

class DuckDuckGoScrapeResponse(BaseModel):
    aggregated_search_content: Optional[str] = None
    sources: List[Dict[str, str]] = []
    all_errors: List[str] = []

class ErrorResponse(BaseModel):
    detail: str


# --- API Endpoints ---
@app.on_event("startup")
async def startup_event():
    if not VALID_SCRAPER_API_KEYS:
        print("FATAL: Application starting without any valid ScraperAPI keys. Scraping endpoints will fail.")
        # In a real production app, you might prevent startup here or have a degraded mode.
    else:
        print(f"FastAPI application startup complete. {len(VALID_SCRAPER_API_KEYS)} ScraperAPI key(s) loaded.")
    print(f"Default internal crawl depth: {DEFAULT_MAX_DEPTH_INTERNAL_SPIDER}, max links per page: {DEFAULT_MAX_LINKS_PER_PAGE_SPIDER}")

@app.post("/api/spider-crawl-batch", response_model=ScrapeResponse, responses={500: {"model": ErrorResponse}})
async def api_spider_crawl_batch(request_data: SpiderCrawlRequest, request: Request):
    client_host = request.client.host if request.client else "unknown"
    print(f"Received /api/spider-crawl-batch request from {client_host} for query: '{request_data.query}' with {len(request_data.base_urls)} base URLs.")
    
    if not VALID_SCRAPER_API_KEYS:
        raise HTTPException(status_code=503, detail="Server configuration error: No valid ScraperAPI keys available.")

    try:
        # Convert HttpUrl back to string for service layer if it expects strings
        str_base_urls = [str(url) for url in request_data.base_urls]
        
        result = await process_spider_crawl_batch_endpoint_logic(
            request_data.query,
            str_base_urls,
            request_data.max_depth_internal,
            request_data.max_links_per_url
        )
        # Check if the service logic itself returned an error message to be displayed
        if "error" in result and result["error"]: # Should not happen if VALID_SCRAPER_API_KEYS is checked above
             raise HTTPException(status_code=500, detail=result["error"])
        return ScrapeResponse(**result)
    except Exception as e:
        print(f"Unhandled error in /api/spider-crawl-batch endpoint for query '{request_data.query}': {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error during spider crawl: {str(e)}")

@app.post("/api/duckduckgo-scrape", response_model=DuckDuckGoScrapeResponse, responses={500: {"model": ErrorResponse}})
async def api_duckduckgo_scrape(request_data: DuckDuckGoScrapeRequest, request: Request):
    client_host = request.client.host if request.client else "unknown"
    print(f"Received /api/duckduckgo-scrape request from {client_host} for query: '{request_data.query}'")

    if not VALID_SCRAPER_API_KEYS:
        raise HTTPException(status_code=503, detail="Server configuration error: No valid ScraperAPI keys available.")

    try:
        result = await process_duckduckgo_search_and_scrape_endpoint_logic(
            request_data.query,
            request_data.num_results
        )
        if "error" in result and result["error"]: # Should not happen
             raise HTTPException(status_code=500, detail=result["error"])
        return DuckDuckGoScrapeResponse(**result)
    except Exception as e:
        print(f"Unhandled error in /api/duckduckgo-scrape endpoint for query '{request_data.query}': {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error during DuckDuckGo scrape: {str(e)}")

@app.get("/", include_in_schema=False) # Basic root endpoint
async def read_root():
    return {"message": "Chatbot Scraper API is running. See /docs for API documentation."}

# To run locally (for development only - Render uses the Start Command):
# uvicorn main:app --reload --port 8008 --host 0.0.0.0
