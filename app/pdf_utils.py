import os
import uuid
import zipfile
import asyncio
from playwright.sync_api import sync_playwright
from PyPDF2 import PdfMerger

def process_page_sync(url: str, output_dir: str):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    page_id = str(uuid.uuid4())
    pdf_filename = f"{page_id}.pdf"
    pdf_filepath = os.path.join(output_dir, pdf_filename)
    
    thumb_filename = f"{page_id}.jpg"
    thumb_filepath = os.path.join(output_dir, thumb_filename)
    
    html_content = ""
    
    try:
        with sync_playwright() as p:
            print(f"Launching browser to generate PDF for {url}...")
            # Use a more modern chromium build and some flags
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-dev-shm-usage', 
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            # Use a high-quality User-Agent
            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                ignore_https_errors=True
            )
            
            page = context.new_page()
            
            # Extra evasion: Remove 'webdriver' from navigator
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Use screen media for accurate PDF
            page.emulate_media(media="screen")
            
            # Use networkidle to wait for images and scripts to finish loading
            print(f"Loading page: {url}")
            try:
                # Try to wait for networkidle, but if it's a "chatty" site, it might timeout
                page.goto(url, wait_until="networkidle", timeout=40000)
            except Exception as nav_e:
                print(f"Primary navigation (networkidle) for {url} failed or timed out. Falling back to domcontentloaded. Error: {nav_e}")
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(5000) # Give it 5 extra seconds for fonts/scripts
                except Exception as fallback_e:
                    print(f"Fallback navigation also failed for {url}: {fallback_e}")
            
            print(f"Capturing PDF for {url}...")
            # Generate PDF with pixel-to-pixel accuracy
            page.pdf(
                path=pdf_filepath, 
                format="A4", 
                print_background=True,
                margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"},
                prefer_css_page_size=False # We want standard A4 but screen representation
            )
            
            # Generate thumbnail
            page.screenshot(path=thumb_filepath, type="jpeg", quality=40)
            
            # Get HTML content
            html_content = page.content()
            
            browser.close()
            print(f"PDF generation complete for {url}")
            
        return pdf_filepath, thumb_filepath, html_content
    except Exception as e:
        error_msg = f"Error processing {url}: {str(e)}"
        print(error_msg)
        # Log error to file
        log_path = os.path.join(os.getcwd(), "playwright_error.log")
        with open(log_path, "a") as f:
            f.write(error_msg + "\n")
        return None, None, None

async def process_page(url: str, output_dir: str):
    # Run sync Playwright in a separate thread to prevent asyncio event loop conflicts
    # which are common when streaming responses in FastAPI
    return await asyncio.to_thread(process_page_sync, url, output_dir)

def merge_pdfs(pdf_paths, output_filepath):
    try:
        if not pdf_paths:
            return None
        merger = PdfMerger()
        for pdf in pdf_paths:
            if pdf and os.path.exists(pdf):
                merger.append(pdf)
        merger.write(output_filepath)
        merger.close()
        return output_filepath
    except Exception as e:
        print(f"Error merging PDFs: {e}")
        return None

def create_zip(file_paths, output_filepath):
    try:
        if not file_paths:
            return None
        with zipfile.ZipFile(output_filepath, 'w') as zipf:
            for file in file_paths:
                if file and os.path.exists(file):
                    zipf.write(file, os.path.basename(file))
        return output_filepath
    except Exception as e:
        print(f"Error creating ZIP: {e}")
        return None