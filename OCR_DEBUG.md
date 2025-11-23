# OCR_DEBUG.md — Azure-Primary OCR + Full Redundancy

## Goal
Fix the current Bills/Mail OCR failure and make OCR resilient.

Primary OCR engine: Azure Document Intelligence Read OCR  
Backup OCR engine: local Tesseract (or another open OCR) only when Azure fails or confidence is low.

Redundancy is mandatory across EVERYTHING:
- Website
- Mobile apps
- Chatbots
- AI agents
- Deep agents
- Storage
- External APIs
- Deploy pipelines

No single point of failure. Ever.

---

## Current Symptom
Frontend shows:
“Server error. Please check Azure Function logs, key/endpoints, and CORS.”

Azure Function logs during failure:
- CORS preflight succeeds.
- Route matches api/mailbills/parse.
- Function executes and fails in ~77ms.
- Host later drains/restarts.

Interpretation:
This is an internal Function failure (startup/config/parsing/dependency), not CORS.
When preflight succeeds and the function dies instantly, the bug is inside the Function.

---

## Most Likely Root Causes (based on log pattern)
1) Missing or wrong Azure OCR env vars in Function App:
   - AZURE_DI_ENDPOINT
   - AZURE_DI_API_KEY
   - AZURE_DI_API_VERSION
   - AZURE_DI_MODEL=prebuilt-read

2) Wrong endpoint:
   - Using Computer Vision or legacy DI endpoint instead of Document Intelligence Read.

3) Function auth mismatch:
   - Trigger set to function auth but request has no key.
   - Or auth blocks the real POST after OPTIONS succeeds.

4) Multipart parsing failure:
   - wrong form field name (file)
   - file too big
   - unsupported content-type
   - request body empty

5) Missing runtime dependency:
   - Function attempts local PDF/image conversion without poppler/imagemagick.

---

## Debug Strategy (must implement)

### 1) Add /api/ocr-debug endpoint (FastAPI OR Azure Function mirror)
Endpoint accepts image/PDF upload and returns:
- stage-by-stage status
- preprocessing artifacts (temp images)
- raw OCR text (Azure + fallback)
- confidence scores
- which engine was used (azure_primary / fallback)

Return JSON like:
{
  "engine_used": "azure_primary",
  "stages": {
    "upload_parse": "ok",
    "pdf_to_image": {"status":"ok","dpi":300},
    "preprocess": "ok",
    "azure_read_call": "ok",
    "fallback_call": "skipped"
  },
  "confidence": 0.91,
  "text_preview": "Light bill #12345 ... Due date 11/30/25 ..."
}

Must also:
- Log failures with explicit stage + reason.
- Never return a generic “server error” to the frontend.
- In debug mode, return saved temp images for inspection.

Example endpoint flow (pseudocode):
    stages = {}
    stages["upload_parse"] = "ok"
    raw_bytes = read_upload()
    type = detect_pdf_or_image(raw_bytes)
    if pdf:
        pages = pdf_to_images(dpi=300)
        stages["pdf_to_image"] = {"status":"ok","dpi":300}
    img = preprocess(pages_or_image)
    stages["preprocess"] = "ok"
    azure_text, azure_conf = azure_read_ocr(img)
    stages["azure_read_call"] = "ok"
    if azure_conf < 0.75 or azure_error:
        stages["fallback_call"] = "running"
        fallback_text = tesseract_ocr(img)
        stages["fallback_call"] = "ok"
        final_text = merge(azure_text, fallback_text)
        engine_used = "fallback"
    else:
        final_text = azure_text
        engine_used = "azure_primary"
    return {engine_used, stages, confidence, preview}

---

### 2) Validate Azure Function Configuration (most likely failure)
Because the function fails almost instantly, verify Function App settings:

Function App → Configuration → Application settings:
- AZURE_DI_ENDPOINT
- AZURE_DI_API_KEY
- AZURE_DI_API_VERSION
- AZURE_DI_MODEL=prebuilt-read

Endpoint MUST look like:
https://<resource-name>.cognitiveservices.azure.com/

API version should be current DI Read version (v4.0 GA).

---

### 3) Verify Function Auth Mode
Logs show:
AuthenticationScheme: WebJobsAuthLevel was not authenticated.

This often means:
- HTTP trigger is set to function auth but request has no key.
- Or host admin probes produced noise.

Action:
- If frontend calls Function directly, set HTTP trigger authLevel to anonymous.
- If protected, require a function key BUT only send it server-side (Render backend), never from browser.

Example function.json target:
    "authLevel": "anonymous"
    "methods": ["post","options"]
    "route": "mailbills/parse"

---

### 4) Request Parsing Checks (common 77ms failures)
If using multipart upload, ensure:
- field name is file
- size limits allow phone photos + PDFs
- content-type is supported (image/*, application/pdf)

Log these on every request:
- content-type
- file size
- filename extension guessed
- first bytes signature (magic bytes)

Example log fields:
    content_type = header("content-type")
    size_bytes = len(raw_bytes)
    filename = upload.filename
    magic = raw_bytes[0:12].hex()

---

## OCR Processing Pipeline

### 5) Azure Document Intelligence Read OCR (PRIMARY)
Required call flow:

1) POST analyze:
   {AZURE_DI_ENDPOINT}/documentintelligence/documentModels/prebuilt-read:analyze?api-version={AZURE_DI_API_VERSION}
   Headers:
   Ocp-Apim-Subscription-Key: {AZURE_DI_API_KEY}
   Body:
   raw file bytes (application/pdf or image/*)

2) Poll Operation-Location URL until status == "succeeded".

3) Extract:
- full content text
- pages
- words + confidences

Reliability rules:
- retries: 2–3
- exponential backoff
- timeout handling
- failover to fallback OCR on persistent failure

---

### 6) Preprocessing Pipeline (before Azure)
Azure works better with clean inputs.

If PDF:
- convert to images via poppler at 300 DPI

Normalize:
- grayscale
- deskew (fix tilted phone pics)
- adaptive threshold (remove shadows)
- denoise
- mild sharpen

Save preprocessed images in debug mode:
- /tmp/ocr_debug/preprocessed_page_1.png

---

### 7) Fallback OCR (SECONDARY ONLY)
Trigger fallback if:
- Azure call errors/timeouts
- confidence < threshold (default 0.75)

Fallback steps:
- use same preprocessed image
- run Tesseract with:
  --oem 3 --psm 6
  lang=eng+spa

Combine results:
- prefer Azure text
- patch missing low-confidence regions with fallback text

---

## Redundancy Requirements (non-negotiable)

OCR flow must include:
- retries + backoff for Azure
- circuit breaker to fallback OCR
- confidence scoring
- partial results allowed
- cached last-known-good templates per detected doc source
- never crash entire pipeline for one bad page

Entire product must include:
- retry logic
- fallback paths
- “partial OK” degradation
- clear stage-based errors

---

## Acceptance Tests
Add fixtures:
1) Phone photo bill (skewed, low light, shadow)
2) Clean PDF bill
3) USPS scan / notice

Pass criteria:
- ≥ 90% word recall on clean docs
- ≥ 75% usable extraction on phone photos
- never returns generic “server error” without stage info
- debug endpoint clearly shows where failures happen

---

## Codex Execution Order
1) Implement /api/ocr-debug + stage logging.
2) Fix Azure Function env vars/auth/parsing until Azure OCR works reliably.
3) Tune preprocessing for phone photos.
4) Add fallback thresholds + merged output logic.
5) Enforce redundancy patterns across every OCR-related call.
