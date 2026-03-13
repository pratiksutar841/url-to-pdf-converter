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
            # Add some args to make chromium more stable and accurate
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-dev-shm-usage', '--no-sandbox']
            )
            context = browser.new_context(viewport={'width': 1280, 'height': 800})
            page = context.new_page()
            
            # IMPORTANT: Emulate screen media to ensure the PDF looks exactly like the website on screen, not a print preview!
            page.emulate_media(media="screen")
            
            # Navigate to the page - use domcontentloaded to avoid hanging on slow external resources
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                # Wait a little extra bit for dynamic content and images to load
                page.wait_for_timeout(3000)
            except Exception as nav_e:
                print(f"Navigation timeout/error (continuing anyway as page might be partially loaded): {nav_e}")
            
            # Generate PDF with accurate representation
            page.pdf(
                path=pdf_filepath, 
                format="A4", 
                print_background=True,
                margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"}
            )
            
            # Generate thumbnail
            page.screenshot(path=thumb_filepath, type="jpeg", quality=40)
            
            # Get HTML content for video detection
            html_content = page.content()
            
            browser.close()
            
        return pdf_filepath, thumb_filepath, html_content
    except Exception as e:
        error_msg = f"Error processing {url}: {str(e)}"
        print(error_msg)
        # Log error to file for debugging
        with open("playwright_error.log", "a") as f:
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