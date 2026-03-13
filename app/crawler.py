import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def get_internal_links(base_url, limit=10):
    visited = set()
    links = []

    try:
        r = requests.get(base_url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        domain = urlparse(base_url).netloc
        
        # Always include base_url
        visited.add(base_url)
        links.append(base_url)

        for a in soup.find_all("a", href=True):
            if len(links) >= limit:
                break
                
            url = urljoin(base_url, a["href"])
            url = url.split('#')[0]

            if not url.startswith('http'):
                continue
                
            exts = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.zip', '.mp4', '.avi', '.css', '.js']
            if any(url.lower().endswith(ext) for ext in exts):
                continue

            if urlparse(url).netloc == domain and url not in visited:
                visited.add(url)
                links.append(url)

    except Exception as e:
        print(f"Error crawling {base_url}: {e}")

    return links

def detect_video(html_content):
    if not html_content:
        return False
        
    soup = BeautifulSoup(html_content, "html.parser")

    if soup.find("video"):
        return True
        
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "").lower()
        if "youtube" in src or "vimeo" in src:
            return True

    return False