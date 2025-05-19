import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from readability import Document # from readability-lxml

def get_main_content_from_html(html_content: str, base_url: str) -> str:
    """
    Uses readability-lxml to extract main content and return it as text.
    """
    if not html_content:
        return ""
    try:
        doc = Document(html_content, url=base_url)
        title = doc.title()
        # Get text content, try to clean up excessive newlines
        text_content = doc.summary() # This gives HTML of summary
        soup = BeautifulSoup(text_content, 'lxml')
        cleaned_text = soup.get_text(separator='\n', strip=True)
        cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text) # Consolidate multiple newlines
        
        return f"# {title}\n\n{cleaned_text}"
    except Exception as e:
        print(f"Error processing HTML with Readability for {base_url}: {e}")
        return ""

def extract_relevant_internal_links(html_content: str, base_url_str: str, query_terms: list[str], max_links_to_return: int = 5):
    """
    Extracts internal links from HTML that seem relevant to the query terms.
    """
    links = set()
    if not html_content:
        return list(links)
    
    try:
        base_url_obj = urlparse(base_url_str)
        soup = BeautifulSoup(html_content, 'lxml')
        
        for a_tag in soup.find_all('a', href=True):
            if len(links) >= max_links_to_return:
                break

            href = a_tag['href']
            if not href or href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                continue
            
            try:
                absolute_url = urljoin(base_url_str, href)
                parsed_absolute_url = urlparse(absolute_url)

                if parsed_absolute_url.scheme not in ['http', 'https'] or parsed_absolute_url.netloc != base_url_obj.netloc:
                    continue # Skip external links or non-http(s) links

                # Relevance check
                link_text = a_tag.get_text(separator=' ').lower().strip()
                url_path_query = (parsed_absolute_url.path + parsed_absolute_url.query).lower()
                is_relevant = False

                if query_terms:
                    is_relevant = any(term in link_text or term in url_path_query for term in query_terms)
                else: # If no query terms (e.g., direct site scrape), consider most internal links relevant initially
                    is_relevant = True 
                
                # Additional filter for news-like patterns if query terms are present and didn't match
                if query_terms and not is_relevant:
                    if any(pat in url_path_query for pat in ['/news', '/article', 'story', 'details', 'breaking', 'latest']) or \
                       re.search(r'[/]\d{4,}[/-]\d{1,2}[/-]\d{1,2}/', url_path_query): # Date pattern
                        is_relevant = True
                
                # Exclude common file types unless they are part of the query
                if is_relevant and not re.search(r'\.(jpeg|jpg|gif|png|css|js|pdf|zip|xml|svg|webp|mp3|mp4|woff|ttf|eot|ico)(\?.*)?$', parsed_absolute_url.path, re.IGNORECASE):
                    links.add(absolute_url)

            except ValueError: # Handle invalid URLs from urljoin/urlparse
                continue
        
        return list(links)
    except Exception as e:
        print(f"Error extracting links from {base_url_str}: {e}")
        return []


def extract_shopping_product_details(html_content: str, url: str) -> dict:
    """
    Placeholder for extracting product details from e-commerce sites.
    This needs to be implemented with specific CSS selectors or XPath per site.
    Crawl4AI's JsonCssExtractionStrategy would be good here if you define schemas.
    """
    print(f"Attempting to extract shopping details for {url}. (This function is a placeholder and needs specific selectors per site)")
    soup = BeautifulSoup(html_content, 'lxml')
    data = {
        "url": url,
        "name": "Product Name Not Found",
        "price": "Price Not Found",
        "images": [], # List of image URLs
        "features": [] # List of feature strings
    }
    # --- YOU NEED TO ADD SITE-SPECIFIC SELECTORS HERE ---
    # Example (very generic, will likely NOT work):
    name_tag = soup.find('h1', id='title') or soup.find('h1', class_='product-title') 
    if name_tag:
        data['name'] = name_tag.get_text(strip=True)

    # For price:
    # price_tag = soup.find(class_=re.compile(r'price|amount', re.I))
    # if price_tag: data['price'] = price_tag.get_text(strip=True)

    # For images:
    # for img_tag in soup.select('img.product-image, div.product-gallery img'): # Example selectors
    #    if img_tag.get('src'): data['images'].append(urljoin(url, img_tag.get('src')))
    
    # For features:
    # feature_list = soup.select('ul.features-list li, div.product-specs li') # Example selectors
    # data['features'] = [li.get_text(strip=True) for li in feature_list]
    
    if data['name'] == "Product Name Not Found":
        return {"url": url, "error": "Could not extract structured product data. Site-specific selectors needed."}
    return data
