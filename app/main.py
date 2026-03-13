import os
import json
import uuid
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .crawler import get_internal_links, detect_video
from .pdf_utils import process_page, merge_pdfs, create_zip

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/output", StaticFiles(directory="output"), name="output")

@app.get("/")
async def read_root():
    return FileResponse("templates/index.html")

@app.get("/api/scan")
async def scan(url: str = Query(...)):
    async def event_stream():
        yield f"data: {json.dumps({'status': 'info', 'message': f'Crawling target website...'})}\n\n"
        
        links = get_internal_links(url, limit=8)
        
        yield f"data: {json.dumps({'status': 'crawled', 'count': len(links), 'links': links})}\n\n"
        
        pages_data = []
        pdf_paths = []
        
        output_dir = "output/pdfs"
        os.makedirs(output_dir, exist_ok=True)
        
        for idx, link in enumerate(links):
            yield f"data: {json.dumps({'status': 'processing_page', 'url': link, 'index': idx, 'total': len(links)})}\n\n"
            
            pdf_path, thumb_path, html_content = await process_page(link, output_dir)
            
            video_detected = detect_video(html_content) if html_content else False
            
            pdf_url = "/" + pdf_path.replace("\\", "/") if pdf_path else None
            thumb_url = "/" + thumb_path.replace("\\", "/") if thumb_path else None
            
            if pdf_path:
                pdf_paths.append(pdf_path)
                
            page_info = {
                "url": link,
                "video": video_detected,
                "pdf": pdf_url,
                "thumb": thumb_url
            }
            pages_data.append(page_info)
            
            yield f"data: {json.dumps({'status': 'page_done', 'index': idx, 'page': page_info})}\n\n"
            
        yield f"data: {json.dumps({'status': 'info', 'message': 'Merging PDFs and creating ZIP archive...'})}\n\n"
        
        merge_dir = "output/merged"
        os.makedirs(merge_dir, exist_ok=True)
        job_id = str(uuid.uuid4())
        
        merged_pdf = os.path.join(merge_dir, f"{job_id}_merged.pdf")
        zip_file = os.path.join(merge_dir, f"{job_id}_all.zip")
        
        merge_pdfs(pdf_paths, merged_pdf)
        create_zip(pdf_paths, zip_file)
        
        merged_url = "/" + merged_pdf.replace("\\", "/") if os.path.exists(merged_pdf) else None
        zip_url = "/" + zip_file.replace("\\", "/") if os.path.exists(zip_file) else None
            
        yield f"data: {json.dumps({'status': 'complete', 'pages': pages_data, 'merged_pdf': merged_url, 'zip_file': zip_url})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")