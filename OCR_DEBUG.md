# OCR_DEBUG.md — Azure-Primary OCR + Full Redundancy

## Goal
Fix the current Bills/Mail OCR failure and make OCR resilient.
Primary OCR engine: **Azure Document Intelligence Read OCR**.
Backup OCR engine: local Tesseract (or other open OCR) only on Azure failure/low confidence. :contentReference[oaicite:3]{index=3}  

## Current Symptom
Frontend shows:
> “Server error. Please check Azure Function logs, key/endpoints, and CORS.”

Azure Function logs at failure:
- CORS preflight succeeds.
- Route matches `api/mailbills/parse`.
- Function executes and **fails in ~77ms**.
- Later appears host drain/restart.
Interpretation: failure is inside function startup/logic (env vars, auth, parsing, missing deps), not CORS. :contentReference[oaicite:4]{index=4}  

## Debug Strategy (must implement)
### 1. Add /api/ocr-debug endpoint (FastAPI OR Azure Function mirror)
Endpoint accepts image/PDF upload and returns:
- stage-by-stage status
- preprocessing artifacts (temp images)
- raw OCR text (Azure + fallback)
- confidence scores
- which engine was used (azure_primary / fallback)

Return JSON like:
```json
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
  "text_preview": "..."
}
2. Validate Azure Function Configuration (most likely failure)

Because the function fails almost instantly:

-Check env vars exist in Function App configuration:

-AZURE_DI_ENDPOINT

-AZURE_DI_API_KEY

-AZURE_DI_API_VERSION

-Verify endpoint is the Document Intelligence resource, not Vision v3.2.

-Confirm API version is v4.0 GA. Microsoft Learn+2

3. Verify Function Auth Mode

Logs show:
AuthenticationScheme: WebJobsAuthLevel was not authenticated.
This often means:

-function is set to function auth but request has no key

-or host is probing with admin routes and failing benignly.
Action:

-Ensure HTTP trigger auth level is consistent with frontend usage:

-If public endpoint: authLevel=anonymous

-If protected: require function key and add it server-side, never client-side. 
GitHub

4. Request Parsing Checks (common 77ms failures)

-If using multipart, ensure:

-correct field name (file)

-size limits high enough

-content-type handling correct

-Log:

-content-type

-file size

-derived extension

-first bytes signature

5. Azure OCR Call (Document Intelligence Read)

-Required call pattern:

-POST analyze:

-{endpoint}/documentintelligence/documentModels/prebuilt-read:analyze?api-version=4.0

-headers: Ocp-Apim-Subscription-Key

-Poll operation URL until succeeded.

-Extract content, pages, words, confidences. 

6. Preprocessing Pipeline (before Azure)

-Even Azure benefits from clean inputs:

-If PDF:

-convert to images via poppler at 300 DPI

-Normalize:

-grayscale

-deskew

-adaptive threshold

-denoise

-mild sharpen

7. Fallback OCR (only when needed)

-Trigger fallback if:

-Azure call errors/timeouts

-confidence < threshold (ex: 0.75)
-Fallback steps:

-use same preprocessed image

-run Tesseract with:

--oem 3 --psm 6

-lang=eng+spa
-Return combined result:

-prefer Azure text when available

-supplement missing regions with fallback text.

8. Redundancy Requirements (non-negotiable)

-For OCR flow:

-retries (Azure): 2–3 tries exponential backoff

-circuit breaker: if Azure down, auto fallback

-cached last good template for same doc source

-graceful partial results instead of hard failure
For the broader product:

-every tool and agent must have retry + fallback + “partial OK” mode.

9. Acceptance Tests

-Add fixtures:

-photo from phone (skewed, low light)

-clean PDF bill

-USPS scan
-Pass criteria:

-≥90% word recall on clean docs

-≥75% usable extraction on phone photos

-never returns generic “server error” without stage info.
