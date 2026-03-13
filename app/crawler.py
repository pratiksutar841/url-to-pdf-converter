import os
import asyncio
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def normalize_url(url):
    """Normalize URL by removing trailing slashes and fragments."""
    parsed = urlparse(url)
    path = parsed.path.rstrip('/')
    if not path:
        path = '/'
    # Rebuild URL without fragment
    return f"{parsed.scheme}://{parsed.netloc}{path}{'?' + parsed.query if parsed.query else ''}"

def get_internal_links(base_url, limit=10):
    visited = set()
    links = []

    # Normalize the base URL
    base_url = normalize_url(base_url)
    
    # Always include base_url
    visited.add(base_url)
    links.append(base_url)

    print(f"Starting crawl for: {base_url}")

    try:
        with sync_playwright() as p:
            print("Launching browser for link extraction...")
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-dev-shm-usage', '--no-sandbox', '--disable-setuid-sandbox']
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                ignore_https_errors=True
            )
            page = context.new_page()
            
            # Use domcontentloaded for faster link scanning
            print(f"Navigating to {base_url}...")
            try:
                page.goto(base_url, wait_until="domcontentloaded", timeout=20000)
                # Wait just a tiny bit for any immediate JS redirects or link generation
                page.wait_for_timeout(2000)
            except Exception as e:
                print(f"Navigation warning for {base_url}: {e}")
            
            # Get links from the rendered page
            print("Extracting links from page content...")
            content = page.content()
            soup = BeautifulSoup(content, "html.parser")
            browser.close()
            print("Crawl browser closed.")

        domain = urlparse(base_url).netloc
        
        for a in soup.find_all("a", href=True):
            if len(links) >= limit:
                break
                
            url = urljoin(base_url, a["href"])
            url = normalize_url(url)

            if not url.startswith('http'):
                continue
                
            exts = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.zip', '.mp4', '.avi', '.css', '.js', '.svg', '.woff', '.woff2']
            if any(url.lower().endswith(ext) for ext in exts):
                continue

            if urlparse(url).netloc == domain and url not in visited:
                visited.add(url)
                links.append(url)
                print(f"Found internal link: {url}")

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