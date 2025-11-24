# OCR_STABILIZATION.md — Azure-Primary OCR (Post-Fix Hardening)

## Purpose
OCR works. This file defines how we make it **reliable, high-quality, and market-ready**.

Primary OCR: **Azure Document Intelligence Read (prebuilt-read)**  
Fallback OCR: **Tesseract** only if Azure fails or confidence is low.

---

## Required Behavior (non-negotiable)

1. **Stage logging for every request**
Return JSON with:
- engine_used: azure_primary | fallback
- confidence: 0–1
- stages: upload_parse / pdf_to_image / preprocess / azure_call / fallback_call / extraction
- user_facing_error: short EN/ES message if failure

2. **Retries**
- Azure OCR analyze call: 2–3 retries
- exponential backoff
- timeout safe

3. **Fallback rules**
Fallback only if:
- Azure errors or times out
- confidence < 0.75 (configurable ENV)

4. **Preprocessing**
For PDFs:
- poppler convert to images at 300 DPI

For phone photos:
- grayscale
- deskew
- adaptive threshold
- denoise
- mild sharpen

5. **Quality warnings**
If confidence low or scan artifacts detected:
- return warning + retake tips
- bilingual (EN/ES)

6. **No generic failures**
Never return “server error” without stage+reason.

---

## Environment Variables (Azure Functions + Render)
- AZURE_DI_ENDPOINT
- AZURE_DI_API_KEY
- AZURE_DI_API_VERSION (v4.0 GA)
- AZURE_DI_MODEL=prebuilt-read

Optional:
- OCR_CONFIDENCE_THRESHOLD=0.75
- DEBUG_OCR=false

---

## Acceptance Tests
Fixtures:
1. Clean PDF bill
2. Skewed phone photo bill (shadow + tilt)
3. USPS letter scan

Pass criteria:
- ≥90% word recall on clean docs
- ≥75% usable extraction on phone photos
- stage errors visible on any failure
- fallback triggers correctly

---

## Codex Work Scope
Codex may:
- refactor OCR pipeline for quality/reliability
- add tests + fixtures
- improve preprocessing
- improve stage errors + warnings

Codex must NOT:
- add unrelated features
- change UI aesthetic
- introduce new deps without updating Dockerfile + requirements
