import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from readability import Document 
from typing import List, Dict, Optional, Set

# This file does not directly use MAX_CONCURRENT_SCRAPES from config,
# but if it needed other constants from config.py, it would be:
# from config import MIN_CONTENT_LENGTH_FOR_SUMMARY # For example

def get_main_content_from_html(html_content: str, base_url: str) -> str:
    if not html_content:
        return ""
    try:
        doc = Document(html_content, url=base_url)
        title = doc.title()
        content_html = doc.summary(html_partial=True)

        soup = BeautifulSoup(content_html, 'lxml')
        for selector in ['nav', 'footer', 'aside', '.sidebar', '#sidebar', '.comments', '#comments', '.related-posts', 'figure.wp-block-image.size-large', 'div.wp-block-image', 'div.gallery', '.ad', '[class*="advert"]', '[id*="advert"]']:
            for s in soup.select(selector):
                s.decompose()

        cleaned_text = soup.get_text(separator='\n', strip=True)
        cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text)

        if len(cleaned_text.strip()) > 100: 
             return f"# {title}\n\n{cleaned_text.strip()}"
        elif title and len(title) > 10: 
            return f"# {title}\n\n(Content extracted was very short or primarily boilerplate after cleaning)"
        return cleaned_text.strip() 
    except Exception as e:
        print(f"Error processing HTML with Readability for {base_url}: {e}")
        return f"(Error processing content for {base_url})"

def extract_relevant_internal_links(
    html_content: str, 
    base_url_str: str, 
    query_terms: Optional[List[str]], 
    max_links_to_return: int = 3 
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
                    continue 

                is_relevant = False
                link_text = a_tag.get_text(separator=' ').lower().strip()
                url_path_query_lower = (parsed_absolute_url.path + parsed_absolute_url.query).lower()

                if query_terms: 
                    is_relevant = any(term in link_text or term in url_path_query_lower for term in query_terms)
                    if not is_relevant: 
                        if any(pat in url_path_query_lower for pat in ['/news', '/article', 'story', 'details', 'breaking', 'latest']) or \
                           re.search(r'[/]\d{4,}[/-]\d{1,2}[/-]\d{1,2}/', url_path_query_lower):
                            is_relevant = True
                else: 
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
    # print(f"Attempting to extract shopping details for {url}. (This function is a placeholder and needs specific selectors per site)")
    soup = BeautifulSoup(html_content, 'lxml')
    data = {
        "url": url,
        "name": soup.title.string if soup.title else "Product Name Not Found",
        "price": "Price Not Found",
        "images": [urljoin(url, img['src']) for img in soup.find_all('img', src=True)[:2]], 
        "features": [p.get_text(strip=True) for p in soup.find_all('p')[:5]] 
    }
    if data['name'] == "Product Name Not Found" and not data['features']:
         return {"url": url, "error": "Could not extract structured product data. Site-specific selectors needed or Readability output was insufficient."}
    return data
