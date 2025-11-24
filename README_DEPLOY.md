# README_DEPLOY.md — Voyadecir Deployment Guide (Updated)

Minimalist bilingual static site + FastAPI backend on Render.  
Goal: one unified Translate + Bills/Mail hub with Azure-first OCR + Azure OpenAI.

---

## What’s Live Right Now
**Two Render services:**

1. **Static site**: `voyadecir-site`
   - Hosts Home, Unified Hub, About, Contact, Privacy, Terms.
   - Domain: voyadecir.com and www.voyadecir.com (SSL active).

2. **API**: `ai-translator`
   - FastAPI app in Docker.
   - Public endpoints:
     - `POST /api/translate`
     - `POST /api/mailbills/parse` (OCR → translate → explain)

---

## Deploy / Update Static Site (Render)
1. Render → Static Site → connect repo.
2. Build command: none
3. Publish dir: `/`
4. Push to `main` → auto-deploy.

**Unified hub note:**  
Translate + Bills/Mail are merged into ONE page.  
If any legacy links exist, redirect them to the hub.

---

## Deploy / Update API (Render Docker)
1. Render → Web Service → connect repo.
2. Repo must include Dockerfile at root.
3. Push to `main` → auto rebuild.

**Dockerfile start command (single line):**  
    uvicorn ai_translator.api:app --host 0.0.0.0 --port $PORT

---

## Required Backend Dependencies

### requirements.txt must include:
- fastapi
- uvicorn[standard]
- httpx
- pydantic>=2
- python-multipart
- tenacity

### System deps (Dockerfile via apt):
- tesseract-ocr
- tesseract-ocr-eng
- tesseract-ocr-spa
- poppler-utils
- imagemagick

---

## Environment Variables (Render → API Service)

### Azure OpenAI
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_API_KEY
- AZURE_OPENAI_DEPLOYMENT
- AZURE_OPENAI_API_VERSION

### Azure OCR (Document Intelligence Read)
- AZURE_DI_ENDPOINT
- AZURE_DI_API_KEY
- AZURE_DI_API_VERSION
- AZURE_DI_MODEL=prebuilt-read

### App Settings
- OFFLINE_MODE=false
- HTTP_TIMEOUT_SECONDS=15
- OCR_CONFIDENCE_THRESHOLD=0.75 (optional)
- DEBUG_OCR=false (optional)

Important: never put keys in frontend code.

---

## CORS
Backend must allow:
- https://voyadecir.com
- https://www.voyadecir.com

Update allowlist if adding staging/mobile.

---

## Build / Deploy Flow
1. Push to `main`
2. Render auto-deploys:
   - static updates immediately
   - API rebuilds Docker image
3. If dependencies change:
   - Clear build cache → Deploy

---

## Known Gotchas
- Missing `httpx` breaks deploys.
- Missing Dockerfile breaks deploys.
- If preflight succeeds and function dies fast, it’s internal, not CORS.
- OCR failures usually = missing/wrong Azure env vars or wrong DI endpoint.

---

## Still Pending (P0)
- OCR stabilization per OCR_STABILIZATION.md
- Unified hub merge + free/Pro gates
- Formspree contact wiring
- Email capture
- SEO blocks on hub

Keep it simple. Ship it. Then sell it.
