# Voyadecir — Deployment Guide (Static Site + API)

Minimalist bilingual (EN/ES) static site + FastAPI backend on Render.
Goal: unified Translate + Bills/Mail hub, plus Azure-first OCR + Azure OpenAI.

---

## What’s Live Right Now
**Two Render services:**
1. **Static site**: `voyadecir-site`  
   - Hosts the HTML/CSS/JS site (Home, unified Translate/Bills/Mail page, About, Contact, Privacy, Terms).
   - Domain: `voyadecir.com` and `www.voyadecir.com` (SSL active).

2. **API**: `ai-translator`  
   - FastAPI app running in Docker.
   - Public endpoint used by the website:
     - `POST https://ai-translator-i5jb.onrender.com/api/translate`
     - (Bills/Mail OCR endpoint may call Azure OCR first, fallback local OCR).

---

## Deploy / Update Static Site (Render)
1. Render → **Static Site** → connect GitHub repo.
2. **Build Command:** none  
3. **Publish Directory:** `/`
4. Push to `main` → Render auto-deploys.

**Unified page note:**  
Translate + Bills/Mail now live on a **single hub page** (no longer separate translate.html + mail-bills.html). Any embeds or links should point to that hub.

---

## Deploy / Update API (Render Docker)
1. Render → **Web Service** → connect GitHub repo.
2. Repo **must include a Dockerfile** at root.
3. Render auto-builds on push to `main`.

**Dockerfile must start Uvicorn like:**
```bash
uvicorn ai_translator.api:app --host 0.0.0.0 --port $PORT

## Required Backend Dependencies

### requirements.txt must include:
- fastapi
- uvicorn[standard]
- httpx
- pydantic>=2
- python-multipart
- tenacity

### System deps (installed in Dockerfile via apt):
- tesseract-ocr
- poppler-utils
- imagemagick

These enable local OCR fallback.

---

## Environment Variables (Render → API Service)

### Azure OpenAI (LLM)
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_API_KEY
- AZURE_OPENAI_DEPLOYMENT
- AZURE_OPENAI_API_VERSION

### Azure OCR (Document Intelligence Read) — PRIMARY OCR
- AZURE_DI_ENDPOINT
- AZURE_DI_API_KEY
- AZURE_DI_API_VERSION
- AZURE_DI_MODEL=prebuilt-read

### App Settings
- OFFLINE_MODE=false
- OPENAI_MODEL=gpt-4o-mini  *(only if using non-Azure fallback)*
- HTTP_TIMEOUT_SECONDS=15

Important: never put keys in frontend code.

---

## CORS

Backend must allow:
- https://voyadecir.com
- https://www.voyadecir.com

If adding new frontends (mobile, staging), update CORS accordingly.

---

## Build / Deploy Flow
1. Push to GitHub `main`
2. Render auto-deploys:
   - Static site updates instantly
   - API rebuilds Docker image
3. If dependencies changed:
   - Render → Clear build cache → Deploy

---

## Known Gotchas (do not repeat history)
- Missing `httpx` in requirements breaks deploys.
- Missing Dockerfile breaks deploys.
- OCR failures often come from missing Azure env vars or wrong Azure OCR endpoint.
- Don’t blame CORS unless preflight is failing. If preflight succeeds and function dies fast, it’s inside the function.

---

## What’s Still Pending (P0)
- Formspree contact wiring (if not already done).
- Email capture.
- Pricing gates (Free vs Pro) on unified hub.
- OCR stabilization per OCR_DEBUG.md.

That’s it. Keep it boring, keep it stable, ship faster.
