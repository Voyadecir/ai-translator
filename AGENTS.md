# AGENTS.md — Voyadecir (Codex Instructions, Updated)

## Mission
Ship Voyadecir as a bilingual (EN/ES) Translate + Bills & Mail Helper product.
Target: **$6k MRR ASAP** by shipping revenue-surface first.

Primary differentiator: immigrant-focused OCR → translation → plain-language explanation for bills/USPS/mail.

---

## Core Principles
1. **Redundancy everywhere**
   - OCR: Azure primary, local fallback
   - LLM: Azure primary, fallback model if available
   - Storage: primary + export/snapshot
   - Agents: retries + graceful degradation

2. **Ship revenue surface area first**
   - P0 only until stable in production.

3. **Minimalist Voyadecir UI**
   - black/white, sans-serif, clean spacing
   - privacy-first, no analytics by default

---

## Stack
### Frontend
- Static HTML/CSS/JS on Render
- Domain: voyadecir.com (+ www)
- **Unified hub page** (Translate + Bills/Mail in one)

### Backend
- FastAPI on Render via Docker
- Endpoints:
  - /api/translate
  - /api/mailbills/parse (calls Azure OCR first, fallback local)

### Azure
- Azure OpenAI for LLM
- Azure Document Intelligence Read OCR (primary)
- Azure Functions for OCR routing / mailbills parsing

---

## Dev Setup (Codex cloud tasks)
1. Install deps: `pip install -r requirements.txt`
2. System deps in Dockerfile:
   - tesseract-ocr (+ eng + spa)
   - poppler-utils
   - imagemagick
3. Export env vars (see below).
4. Run API:  
   `uvicorn ai_translator.api:app --host 0.0.0.0 --port 8000`

---

## Env Vars
### Azure OpenAI
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_API_KEY
- AZURE_OPENAI_DEPLOYMENT
- AZURE_OPENAI_API_VERSION

### Azure OCR
- AZURE_DI_ENDPOINT
- AZURE_DI_API_KEY
- AZURE_DI_API_VERSION
- AZURE_DI_MODEL=prebuilt-read

### App Flags
- OFFLINE_MODE=false
- HTTP_TIMEOUT_SECONDS=15
- OCR_CONFIDENCE_THRESHOLD=0.75 (optional)
- DEBUG_OCR=false (optional)

---

## Guardrails for Codex
**Codex must follow TASKS.md strictly.**

Allowed scope right now:
- P0-A OCR stabilization + tests
- P0-B unified hub merge + paywall scaffolding
- reliability refactors (timeouts, retries, fallback)
- UI polish only in service of P0

Not allowed yet:
- P1 mobile apps
- deep agents beyond scaffolding mentioned in P0
- marketing agents suite
- new heavy dependencies without explicit instruction

---

## Style Rules
- No secrets in frontend.
- Keep EN/ES autodetect + manual toggle.
- Use small, typed functions (Pydantic v2).
- Tenacity retries for all external calls.
- Add tests when fixing bugs.
