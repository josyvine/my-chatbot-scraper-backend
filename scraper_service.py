import asyncio
import httpx
from urllib.parse import urlparse, urljoin
import re
from typing import List, Dict, Any, Tuple, Optional, Set

# Assuming config.py and content_utils.py are in the same directory or accessible in PYTHONPATH
from .config import (
    VALID_SCRAPER_API_KEYS, 
    SCRAPER_API_TIMEOUT, 
    MIN_CONTENT_LENGTH_FOR_SUMMARY,
    DEFAULT_USER_AGENT,
    MAX_CONCURRENT_SCRAPES # Used in main.py but relevant for context
)
from .content_utils import (
    get_main_content_from_html, 
    extract_relevant_internal_links,
    extract_shopping_product_details 
)

# For DuckDuckGo searches
from duckduckgo_search import DDGS

# To manage key rotation for parallel tasks more explicitly if needed, though httpx handles concurrency.
# This index is for single URL scrapes to try and rotate through the pool over time.
scraper_key_round_robin_index = 0

async def fetch_url_with_scraperapi(
    target_url: str, 
    api_key: str, 
    output_format: str = "html", # "html" or "markdown"
    render_js: bool = True,
    country_code: Optional[str] = None,
    retry_count: int = 0,
    max_retries: int = 1 # Max retries for this specific key for transient errors
) -> Dict[str, Any]:
    """
    Fetches a single URL using a specific ScraperAPI key.
    Returns a dictionary: {'raw_response_text': str, 'status_code': int, 'error_message': str|None, 'final_url': str, 'key_used': str}
    """
    if not api_key or api_key.startswith("YOUR_SCRAPERAPI_KEY_"):
        error_msg = f"Invalid/Placeholder ScraperAPI key used for {target_url}."
        print(f"ERROR: {error_msg}")
        return {'raw_response_text': None, 'status_code': 0, 'error_message': error_msg, 'final_url': target_url, 'key_used': api_key, 'is_critical_error': True}

    params = {
        'api_key': api_key,
        'url': target_url,
        'render_js': str(render_js).lower(),
    }
    if output_format == "markdown":
        params['output_format'] = "markdown"
    else: # Default to HTML for link extraction etc.
        params['autoparse'] = "false" # Important for getting raw HTML
    
    if country_code:
        params['country_code'] = country_code

    scraper_api_url = "https://api.scraperapi.com/"
    
    headers = {'User-Agent': DEFAULT_USER_AGENT} # Can add more headers if needed

    async with httpx.AsyncClient(timeout=SCRAPER_API_TIMEOUT + 10, follow_redirects=True) as client:
        try:
            # print(f"Attempting fetch: {target_url} with key ...{api_key[-4:]}, format: {output_format}, attempt: {retry_count + 1}")
            response = await client.get(scraper_api_url, params=params, headers=headers)
            
            # Log the actual URL ScraperAPI tried to fetch if available (useful for debugging redirects)
            # ScraperAPI doesn't directly expose this in headers easily, but the final URL is on response.url
            
            final_url_from_response = str(response.url) # This would be the ScraperAPI URL itself
                                                      # The true final URL of the target isn't directly available here
                                                      # unless ScraperAPI returns it in a custom header or body.

            if response.status_code == 401:
                error_msg = f"ScraperAPI key ...{api_key[-4:]} FAILED (401 Unauthorized) for {target_url}."
                print(f"ERROR: {error_msg}")
                return {'raw_response_text': await response.text(), 'status_code': response.status_code, 'error_message': error_msg, 'final_url': target_url, 'key_used': api_key, 'is_critical_error': True}
            
            if response.status_code == 403:
                error_msg = f"ScraperAPI request FORBIDDEN (403) for {target_url} with key ...{api_key[-4:]}."
                print(f"ERROR: {error_msg}")
                return {'raw_response_text': await response.text(), 'status_code': response.status_code, 'error_message': error_msg, 'final_url': target_url, 'key_used': api_key, 'is_critical_error': True}

            if response.status_code in [429, 500, 502, 503, 504]: # Retryable errors
                if retry_count < max_retries:
                    retry_delay = (retry_count + 1) * 3 # seconds
                    print(f"ScraperAPI returned {response.status_code} for {target_url} with key ...{api_key[-4:]}. Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    return await fetch_url_with_scraperapi(target_url, api_key, output_format, render_js, country_code, retry_count + 1, max_retries)
                else:
                    error_msg = f"Max retries ({max_retries}) reached for {target_url} with key ...{api_key[-4:]}. Last status: {response.status_code}."
                    print(f"ERROR: {error_msg}")
                    return {'raw_response_text': await response.text(), 'status_code': response.status_code, 'error_message': error_msg, 'final_url': target_url, 'key_used': api_key, 'is_critical_error': True}

            response.raise_for_status() # For other 4xx/5xx client/server errors from ScraperAPI

            return {'raw_response_text': response.text, 'status_code': response.status_code, 'error_message': None, 'final_url': target_url, 'key_used': api_key, 'is_critical_error': False}
        
        except httpx.TimeoutException as e:
            error_msg = f"Timeout fetching {target_url} via ScraperAPI (key ...{api_key[-4:]}): {str(e)}"
            print(f"ERROR: {error_msg}")
            return {'raw_response_text': None, 'status_code': 0, 'error_message': error_msg, 'final_url': target_url, 'key_used': api_key, 'is_critical_error': True if retry_count >=max_retries else False}
        except httpx.RequestError as e:
            error_msg = f"Network/RequestError for {target_url} via ScraperAPI (key ...{api_key[-4:]}): {str(e)}"
            print(f"ERROR: {error_msg}")
            # For some request errors, retrying might be valid if it's not a critical setup issue
            if retry_count < max_retries:
                await asyncio.sleep((retry_count + 1) * 2)
                return await fetch_url_with_scraperapi(target_url, api_key, output_format, render_js, country_code, retry_count + 1, max_retries)
            return {'raw_response_text': None, 'status_code': 0, 'error_message': error_msg, 'final_url': target_url, 'key_used': api_key, 'is_critical_error': True}
        except Exception as e: # Catch-all for other unexpected errors
            error_msg = f"Unexpected error fetching {target_url} via ScraperAPI (key ...{api_key[-4:]}): {str(e)}"
            print(f"ERROR: {error_msg}")
            return {'raw_response_text': None, 'status_code': 0, 'error_message': error_msg, 'final_url': target_url, 'key_used': api_key, 'is_critical_error': True}


async def process_single_site_for_spider_crawl(
    base_url: str, 
    api_key: str, 
    original_query: str, 
    max_depth: int, 
    max_links_to_crawl_per_site: int # Renamed for clarity
) -> Dict[str, Any]:
    """
    Crawls a single base_url and its relevant internal links using a specific ScraperAPI key.
    Primarily fetches HTML for link extraction and content processing.
    """
    site_content_parts: List[str] = []
    site_images: List[Dict[str, str]] = [] # Could store {'src': url, 'alt': text}
    site_errors: List[str] = []
    visited_on_this_site: Set[str] = set()
    
    queue: List[Tuple[str, int]] = [(base_url, 0)] # (url, depth)
    
    query_terms = [term.strip() for term in original_query.lower().split() if term.strip()] if original_query else []

    processed_page_count = 0

    while queue and processed_page_count < max_links_to_crawl_per_site:
        current_url, current_d = queue.pop(0)
        
        if current_url in visited_on_this_site:
            continue
        if current_d > max_depth:
            continue
        
        visited_on_this_site.add(current_url)
        processed_page_count += 1
        print(f"  Spidering: {current_url} (Depth: {current_d}, Total for site: {processed_page_count}/{max_links_to_crawl_per_site}) with key ...{api_key[-4:]}")

        # Fetch HTML for link extraction AND content processing
        fetch_result = await fetch_url_with_scraperapi(current_url, api_key, output_format="html")

        if fetch_result['error_message']:
            site_errors.append(f"Fetch error for {current_url} (Key ...{fetch_result['key_used'][-4:]}, Status {fetch_result['status_code']}): {fetch_result['error_message']}")
            if fetch_result.get('is_critical_error'): # If key is bad (401/403) or persistent error, stop this site's crawl
                print(f"    Critical error for key ...{api_key[-4:]} on {current_url}. Aborting crawl for this base_url.")
                break 
            continue # Try next URL in queue if not critical for this specific page

        raw_html = fetch_result['raw_response_text']
        if not raw_html:
            site_errors.append(f"No HTML content received for {current_url} (Key ...{fetch_result['key_used'][-4:]})")
            continue

        # Extract main content using readability-lxml
        # content_utils.py should handle this
        extracted_markdown = get_main_content_from_html(raw_html, current_url) 

        if extracted_markdown and len(extracted_markdown) > MIN_CONTENT_LENGTH_FOR_SUMMARY / 2 :
            site_content_parts.append(f"### Content from: {current_url}\n{extracted_markdown}")
        else:
            # Log even if content is short or primarily an error message from readability
            site_content_parts.append(f"### Low/No substantial content from: {current_url} (Readability output length: {len(extracted_markdown)})")

        # Link extraction for deeper crawl (if current_d < max_depth)
        if current_d < max_depth:
            internal_links = extract_relevant_internal_links(raw_html, current_url, query_terms, DEFAULT_MAX_LINKS_PER_PAGE_SPIDER)
            for link in internal_links:
                if len(visited_on_this_site) + len(queue) < max_links_to_crawl_per_site * 1.5: # Control queue size
                    if link not in visited_on_this_site and not any(q_item[0] == link for q_item in queue):
                        queue.append((link, current_d + 1))
    
    return {
        "source_base_url": base_url,
        "aggregated_content": "\n\n---\n\n".join(site_content_parts) if site_content_parts else f"No content gathered from {base_url} or its subpages.",
        "images": site_images, # Implement image extraction in content_utils if needed
        "errors": site_errors,
        "key_used_for_base": api_key
    }

async def process_spider_crawl_batch_endpoint_logic(query: str, base_urls: List[str], max_depth_internal: int, max_links_per_url: int):
    if not VALID_SCRAPER_API_KEYS:
        return {"error": "No valid ScraperAPI keys configured on server.", "aggregated_content": "", "all_errors": ["Server configuration error: No ScraperAPI keys."]}

    tasks = []
    num_valid_keys = len(VALID_SCRAPER_API_KEYS)
    
    # Determine how many URLs to process in parallel based on available keys and concurrency limit
    urls_to_process_count = min(len(base_urls), num_valid_keys, MAX_CONCURRENT_SCRAPES)
    
    key_assignment_index = 0
    for i in range(urls_to_process_count):
        base_url_to_process = base_urls[i]
        api_key_to_use = VALID_SCRAPER_API_KEYS[key_assignment_index % num_valid_keys]
        key_assignment_index += 1
        
        tasks.append(
            process_single_site_for_spider_crawl(
                base_url_to_process, 
                api_key_to_use, 
                query, 
                max_depth_internal, 
                max_links_per_url
            )
        )
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    final_aggregated_content_parts = []
    all_errors_reported = []
    # all_images_combined = [] # If you implement image extraction

    for i, res_or_exc in enumerate(results):
        processed_url = base_urls[i] # Assuming results are in order
        if isinstance(res_or_exc, Exception):
            err_msg = f"Task for {processed_url} failed with unhandled exception: {str(res_or_exc)}"
            print(f"ERROR: {err_msg}")
            all_errors_reported.append(err_msg)
            final_aggregated_content_parts.append(f"### Major error processing {processed_url}\n{str(res_or_exc)}")
        elif res_or_exc: # It's a dictionary result
            if res_or_exc.get("aggregated_content"):
                final_aggregated_content_parts.append(res_or_exc["aggregated_content"])
            if res_or_exc.get("errors"):
                all_errors_reported.extend(res_or_exc["errors"])
            # if res_or_exc.get("images"): all_images_combined.extend(res_or_exc["images"])

    content_str = "\n\n".join(final_aggregated_content_parts)
    
    # Filter out placeholder/error messages from the final aggregation
    # This regex needs to be robust to catch various forms of failure messages
    filter_patterns = [
        r"### (Low/No substantial content|No content gathered from|Fetch error for|Major error processing|Status for) [^\n]+.*?\n?",
        r"ScraperAPI key .*? (is invalid/unauthorized|FAILED|was Forbidden).*?\n?",
        r"Max retries reached for key .*?\n?",
        r"Failed to fetch/process content from .*? after all attempts:.*?\n?",
        r"Failed to fetch .*?: Invalid or placeholder ScraperAPI key.*?\n?"
    ]
    
    meaningful_content_str = content_str
    for pattern in filter_patterns:
        meaningful_content_str = re.sub(pattern, "", meaningful_content_str, flags=re.IGNORECASE | re.MULTILINE).strip()
    
    print(f"process_spider_crawl_batch_endpoint_logic: Original aggregated length: {len(content_str)}, Filtered length: {len(meaningful_content_str)}")

    if not meaningful_content_str or len(meaningful_content_str) < MIN_CONTENT_LENGTH_FOR_SUMMARY:
         final_report = "After attempting to scrape, no substantial content was found to summarize."
         if all_errors_reported:
             final_report += " Encountered issues (see system messages/console for details). Please ensure ScraperAPI keys are valid and sites are accessible."
         return {
            "aggregated_content": final_report,
            "all_errors": all_errors_reported
            # "images_to_summarize": []
        }

    return {
        "aggregated_content": meaningful_content_str,
        "all_errors": all_errors_reported
        # "images_to_summarize": select_relevant_images(all_images_combined, query, 2) # Placeholder for image selection logic
    }

async def process_duckduckgo_search_and_scrape_endpoint_logic(query: str, num_results: int):
    if not VALID_SCRAPER_API_KEYS:
        return {"error": "No valid ScraperAPI keys configured on server.", "aggregated_search_content": "", "sources": [], "all_errors": ["Server configuration error: No ScraperAPI keys."]}

    print(f"Performing DuckDuckGo search for: '{query}'")
    ddg_search_results: List[Dict[str, str]] = []
    try:
        with DDGS(timeout=20) as ddgs: # DDGS can be slow
            for r in ddgs.text(query, max_results=num_results):
                if r.get('href'): # Ensure URL exists
                    ddg_search_results.append({"url": r['href'], "title": r.get('title', 'No Title'), "snippet": r.get('body', '')})
    except Exception as e:
        error_msg = f"DuckDuckGo search failed: {e}"
        print(f"ERROR: {error_msg}")
        return {"error": error_msg, "aggregated_search_content": "", "sources": [], "all_errors": [error_msg]}

    if not ddg_search_results:
        return {"aggregated_search_content": "No results found on DuckDuckGo for your query.", "sources": [], "all_errors": []}

    tasks = []
    num_valid_keys = len(VALID_SCRAPER_API_KEYS)
    global current_key_index_for_parallel # Re-initialize or manage for each request batch
    current_key_index_for_parallel = 0

    # Limit parallel tasks
    urls_to_process_count = min(len(ddg_search_results), num_valid_keys, MAX_CONCURRENT_SCRAPES)
    
    for i in range(urls_to_process_count):
        target_url_info = ddg_search_results[i]
        api_key_to_use = VALID_SCRAPER_API_KEYS[current_key_index_for_parallel % num_valid_keys]
        current_key_index_for_parallel += 1
        # For DDG results, directly request Markdown from ScraperAPI for simplicity and potentially better results
        tasks.append(fetch_url_with_scraperapi(target_url_info['url'], api_key_to_use, output_format="markdown"))
    
    scraped_page_results = await asyncio.gather(*tasks, return_exceptions=True)

    final_aggregated_content_parts = []
    all_errors_reported = []
    processed_sources = []

    for i, res_or_exc in enumerate(scraped_page_results):
        source_info = ddg_search_results[i]
        if isinstance(res_or_exc, Exception):
            err_msg = f"Task failed for {source_info['url']}: {str(res_or_exc)}"
            all_errors_reported.append(err_msg)
            print(f"ERROR: {err_msg}")
        elif res_or_exc: # It's a dictionary from fetch_url_with_scraperapi
            if res_or_exc['error_message']:
                err_msg = f"Error fetching {source_info['url']} (Key ...{res_or_exc['key_used'][-4:]}, Status {res_or_exc['status_code']}): {res_or_exc['error_message']}"
                all_errors_reported.append(err_msg)
                print(f"ERROR: {err_msg}")
            # Check if raw_response_text (which is markdown here) is substantial
            elif res_or_exc['raw_response_text'] and len(res_or_exc['raw_response_text']) > MIN_CONTENT_LENGTH_FOR_SUMMARY / 2: 
                final_aggregated_content_parts.append(f"### Content from: {source_info['title']} ({source_info['url']})\n{res_or_exc['raw_response_text']}")
                processed_sources.append({"title": source_info['title'], "url": source_info['url']})
            else:
                 all_errors_reported.append(f"Low/No content from {source_info['url']} (Key ...{res_or_exc['key_used'][-4:]}, Status {res_or_exc['status_code']}). Markdown length: {len(res_or_exc['raw_response_text'] or '')}")


    content_str = "\n\n---\n\n".join(final_aggregated_content_parts)
    filter_patterns = [ /* ... as defined in previous function ... */ ] 
    for pattern in filter_patterns:
        content_str = re.sub(pattern, "", content_str, flags=re.IGNORECASE | re.MULTILINE)
    meaningful_content_str = content_str.strip()

    print(f"process_duckduckgo_search: Original aggregated length: {len(content_str)}, Filtered length: {len(meaningful_content_str)}")

    if not meaningful_content_str or len(meaningful_content_str) < MIN_CONTENT_LENGTH_FOR_SUMMARY:
        final_report = "After fetching DuckDuckGo results, no substantial content was extracted to provide a meaningful summary."
        if all_errors_reported:
             final_report += " Encountered issues (see system messages/console for details). Please ensure ScraperAPI keys are valid and sites are accessible."
        return {
            "aggregated_search_content": final_report,
            "sources": processed_sources, # Still return sources even if content is low
            "all_errors": all_errors_reported
        }

    return {
        "aggregated_search_content": meaningful_content_str,
        "sources": processed_sources,
        "all_errors": all_errors_reported
    }
