let pagesData = [];
let currentConvertingUrl = "";

function startConversion() {
    const urlInput = document.getElementById("urlInput");
    const url = urlInput.value.trim();
    if (!url) return;
    
    pagesData = [];
    document.getElementById("pagesCount").textContent = `(0)`;
    
    const pageList = document.getElementById("pageList");
    // Show loading state including progress bar in left pane
    pageList.innerHTML = `
        <div class="empty-state">
            <div class="spinner" style="border-width: 3px; width: 32px; height: 32px;"></div>
            <p id="progressStatus" style="margin-top: 16px; font-weight: 500; font-size: 14px;">Scanning website...</p>
            <div class="progress-container" style="width: 80%; max-width: 250px;">
                <div class="progress-bar" id="progressBar"></div>
            </div>
            <div class="progress-text" id="progressText">Initializing...</div>
        </div>
    `;
    
    document.getElementById("rightPane").style.display = "none";
    document.getElementById("bottomActions").style.display = "none";
    
    const es = new EventSource(`/api/scan?url=${encodeURIComponent(url)}`);
    
    es.onmessage = function(event) {
        const data = JSON.parse(event.data);
        const status = document.getElementById("progressStatus");
        const progressBar = document.getElementById("progressBar");
        const progressText = document.getElementById("progressText");
        
        if (data.status === "info") {
            if (status) status.textContent = data.message;
        } 
        else if (data.status === "crawled") {
            if (status) status.textContent = `Found ${data.count} pages. Generating PDFs...`;
            document.getElementById("pagesCount").textContent = `(${data.count})`;
            
            // initialize list with empty status
            pagesData = data.links.map(link => ({ url: link, status: 'pending' }));
            // We shouldn't render yet because we want to keep the progress bar visible in the left pane until it's done?
            // Actually, we can move the progress bar somewhere else, or just keep it at the top of the list!
            const listHtml = `
                <div style="padding: 16px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; margin-bottom: 8px;">
                    <p id="progressStatus" style="font-weight: 500; font-size: 13px; color: #3b82f6;">Generating PDFs...</p>
                    <div class="progress-container">
                        <div class="progress-bar" id="progressBar"></div>
                    </div>
                    <div class="progress-text" id="progressText">Starting conversion...</div>
                </div>
                <div id="actualList"></div>
            `;
            pageList.innerHTML = listHtml;
            renderActualList();
        }
        else if (data.status === "processing_page") {
            const pct = Math.round((data.index / data.total) * 100);
            if (progressBar) progressBar.style.width = `${pct}%`;
            if (progressText) progressText.textContent = `Processing ${data.index + 1} of ${data.total}`;
            if (status) status.textContent = `Converting page to PDF...`;
            
            // Mark current item as processing in visual
            document.querySelectorAll('.page-item').forEach(el => el.classList.remove('processing'));
            const item = document.getElementById(`page-item-${data.index}`);
            if (item) {
                item.classList.add('processing');
                item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
        else if (data.status === "page_done") {
            pagesData[data.index] = data.page;
            renderActualList();
            
            // Auto select the first successfully generated PDF
            if (data.index === 0 && data.page.pdf) {
                selectPage(0);
            }
        }
        else if (data.status === "complete") {
            if (progressBar) progressBar.style.width = `100%`;
            if (progressText) progressText.textContent = `Complete!`;
            if (status) {
                status.textContent = `Merging finished!`;
                status.style.color = '#16a34a';
            }
            
            es.close();
            
            pagesData = data.pages;
            renderActualList();
            
            const bottomActions = document.getElementById("bottomActions");
            bottomActions.style.display = "flex";
            
            const mergedBtn = document.getElementById("downloadMergedBtn");
            const zipBtn = document.getElementById("downloadZipBtn");
            
            if (data.merged_pdf) {
                mergedBtn.href = data.merged_pdf;
                mergedBtn.style.display = "flex";
            } else {
                mergedBtn.style.display = "none";    
            }
            
            if (data.zip_file) {
                zipBtn.href = data.zip_file;
                zipBtn.style.display = "flex";
            } else {
                zipBtn.style.display = "none";
            }
            
            // Remove progress header if desired, but waiting/keeping it is fine.
        }
    };
    
    es.onerror = function() {
        es.close();
        if (pagesData.length === 0 || !pagesData[0].pdf) {
            pageList.innerHTML = `
                <div class="empty-state">
                    <i class="ph ph-warning-circle" style="color: #ef4444;"></i>
                    <p>Connection lost or error occurred.</p>
                </div>
            `;
        }
    };
}

function getPageNameFromUrl(url) {
    try {
        const urlObj = new URL(url);
        let path = urlObj.pathname;
        if (path === '/' || path === '') return 'Home Page';
        
        const segments = path.split('/').filter(s => s.length > 0);
        let lastSegment = segments[segments.length - 1] || 'Page';
        
        lastSegment = lastSegment.replace(/\.[^/.]+$/, "");
        
        return lastSegment.split(/[-_]+/).map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
        
    } catch {
        return 'Web Page';
    }
}

function renderActualList() {
    const actualList = document.getElementById("actualList");
    if (!actualList) return;
    
    actualList.innerHTML = "";
    
    pagesData.forEach((p, index) => {
        const pageTitle = getPageNameFromUrl(p.url);
        const hasVideo = p.video;
        const hasPdf = p.pdf !== undefined && p.pdf !== null;
        
        const isPending = p.status === 'pending';
        
        const actualIconClass = hasVideo ? 'ph-video-camera' : (isPending ? 'ph-hourglass' : 'ph-file-text');
        
        const div = document.createElement("div");
        div.className = "page-item";
        div.onclick = () => { if (!isPending) selectPage(index); };
        div.id = `page-item-${index}`;
        
        if (isPending) {
            div.style.opacity = "0.6";
        }
        
        let statusHtml = '';
        if (isPending) {
            statusHtml = `<span class="status-badge" style="background: #e2e8f0; color: #475569;">Waiting</span>`;
        } else if (hasPdf && p.pdf) {
            statusHtml = `<span class="status-badge">Ready</span>`;
        } else {
            statusHtml = `<span class="status-badge failed">Failed</span>`;
        }
        
        let videoHtml = '';
        if (hasVideo) {
             videoHtml = `<div style="display:flex; align-items:center; gap:4px; font-size:11px; font-weight:600; color:#eab308; margin-top:4px;"><i class="ph ph-film-strip"></i> 🎥 Video detected</div>`;
        }
        
        div.innerHTML = `
            <div class="page-icon">
                <i class="ph ${actualIconClass}"></i>
            </div>
            <div class="page-details">
                <div class="page-title">${pageTitle}</div>
                <div class="page-url">${p.url}</div>
                ${statusHtml}
                ${videoHtml}
            </div>
        `;
        
        actualList.appendChild(div);
    });
}

function selectPage(index) {
    const p = pagesData[index];
    if (!p) return;
    
    document.querySelectorAll('.page-item').forEach(el => el.classList.remove('active'));
    document.getElementById(`page-item-${index}`)?.classList.add('active');
    
    document.getElementById("rightPane").style.display = "flex";
    
    document.getElementById("detailTitle").textContent = getPageNameFromUrl(p.url);
    document.getElementById("detailUrl").textContent = p.url;
    
    const downloadBtn = document.getElementById("downloadBtn");
    const previewFrame = document.getElementById("previewFrame");
    const loadingOverlay = document.getElementById("loadingOverlay");
    const analysisSummary = document.getElementById("analysisSummary");
    
    if (p.pdf) {
        downloadBtn.style.display = "flex";
        downloadBtn.href = p.pdf;
        // Ensure the button explicitly forces download instead of opening in new tab
        downloadBtn.setAttribute("download", getPageNameFromUrl(p.url) + ".pdf");
        
        previewFrame.src = p.pdf;
        loadingOverlay.style.display = "none";
        
        if (p.video) {
            analysisSummary.textContent = "Page successfully converted. Video content was detected and may not be fully interactive in the PDF format.";
        } else {
            analysisSummary.textContent = "Page successfully converted to standard PDF format with high quality text and image retention.";
        }
    } else {
        downloadBtn.style.display = "none";
        previewFrame.src = "";
        loadingOverlay.style.display = "none";
        analysisSummary.textContent = "Could not convert page content due to an error during crawling or PDF generation.";
        
        previewFrame.srcdoc = `
            <html><body style="display:flex; justify-content:center; align-items:center; height:100%; font-family:sans-serif; color:#64748b;">
                Failed to load preview for this page.
            </body></html>
        `;
    }
}