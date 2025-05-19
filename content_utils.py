import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from readability import Document # from readability-lxml
from typing import List, Dict, Optional, Set

def get_main_content_from_html(html_content: str, base_url: str) -> str:
    if not html_content:
        return ""
    try:
        doc = Document(html_content, url=base_url)
        title = doc.title()
        content_html = doc.summary(html_partial=True)

        soup = BeautifulSoup(content_html, 'lxml')
        # Try to remove some common boilerplate patterns if Readability missed them
        for selector in ['nav', 'footer', 'aside', '.sidebar', '#sidebar', '.comments', '#comments', '.related-posts']:
            for s in soup.select(selector):
                s.decompose()

        cleaned_text = soup.get_text(separator='\n', strip=True)
        cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text)

        # Prepend title if content seems substantial
        if len(cleaned_text.strip()) > 100: # Arbitrary threshold for "substantial"
             return f"# {title}\n\n{cleaned_text.strip()}"
        elif title and len(title) > 10: # If content is short but title exists
            return f"# {title}\n\n(Content extracted was very short or primarily boilerplate)"
        return cleaned_text.strip() # Return even if short, filtering happens later
    except Exception as e:
        print(f"Error processing HTML with Readability for {base_url}: {e}")
        return f"(Error processing content for {base_url})"

def extract_relevant_internal_links(
    html_content: str, 
    base_url_str: str, 
    query_terms: Optional[List[str]], 
    max_links_to_return: int = 3 # Reduced default
) -> List[str]:
    links: Set[str] = set()
    if not html_content:
        return list(links)

    try:
        base_url_obj = urlparse(base_url_str)
        soup = BeautifulSoup(html_content, 'lxml')

        for a_tag in soup.find_all('a', href=True):
            if len(links) >= max_links_to_return:
                break

            href_attr = a_tag.get('href')
            if not href_attr or href_attr.startswith('#') or href_attr.startswith('javascript:') or href_attr.startswith('mailto:') or href_attr.startswith('tel:'):
                continue

            try:
                absolute_url = urljoin(base_url_str, href_attr)
                parsed_absolute_url = urlparse(absolute_url)

                if parsed_absolute_url.scheme not in ['http', 'https'] or parsed_absolute_url.netloc != base_url_obj.netloc:
                    continue 

                if re.search(r'\.(jpeg|jpg|gif|png|css|js|pdf|zip|xml|svg|webp|mp3|mp4|woff|ttf|eot|ico|gz|tgz)(\?.*)?$', parsed_absolute_url.path, re.IGNORECASE):
                    continue # Skip common file types

                is_relevant = False
                link_text = a_tag.get_text(separator=' ').lower().strip()
                url_path_query_lower = (parsed_absolute_url.path + parsed_absolute_url.query).lower()

                if query_terms: # If query terms are provided, link must be relevant
                    is_relevant = any(term in link_text or term in url_path_query_lower for term in query_terms)
                    if not is_relevant: # Check for news patterns if keywords didn't match
                        if any(pat in url_path_query_lower for pat in ['/news', '/article', 'story', 'details', 'breaking', 'latest']) or \
                           re.search(r'[/]\d{4,}[/-]\d{1,2}[/-]\d{1,2}/', url_path_query_lower):
                            is_relevant = True
                else: # No query terms (e.g., direct site exploration from '.') - be more permissive for internal links
                    is_relevant = True 

                if is_relevant:
                    links.add(absolute_url)

            except ValueError: 
                continue

        return list(links)
    except Exception as e:
        print(f"Error extracting links from {base_url_str}: {e}")
        return []

def extract_shopping_product_details(html_content: str, url: str) -> dict:
    print(f"Attempting to extract shopping details for {url}. (This function is a placeholder and needs specific selectors per site)")
    # This function needs to be implemented with site-specific selectors
    # For now, it will return a placeholder or try a very generic extraction
    soup = BeautifulSoup(html_content, 'lxml')
    data = {
        "url": url,
        "name": soup.title.string if soup.title else "Product Name Not Found",
        "price": "Price Not Found",
        "images": [urljoin(url, img['src']) for img in soup.find_all('img', src=True)[:2]], # Get first 2 images
        "features": [p.get_text(strip=True) for p in soup.find_all('p')[:5]] # Get first 5 paragraphs as features
    }
    if data['name'] == "Product Name Not Found" and not data['features']:
         return {"url": url, "error": "Could not extract structured product data. Site-specific selectors needed."}
    return data
