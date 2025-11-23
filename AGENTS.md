# AGENTS.md — Voyadecir (Codex Instructions)

## Mission
Build Voyadecir into a bilingual (EN/ES) translation + Bills & Mail Helper product and reach ~$6k MRR ASAP.
Primary differentiator: immigrant-focused OCR → translation → plain-language explanation for bills/USPS/mail.

## Core Principles
1. **Redundancy everywhere.**
   - Every critical capability must have a fallback:
     - OCR: Azure primary, local/other OCR backup.
     - LLM: Azure OpenAI primary, alternate model/provider backup when available.
     - Storage: primary DB + snapshot/export fallback.
     - Agents: supervisor + retry + graceful degradation.
     - Frontend & apps: cached last-known-good behavior when services fail.

2. **Ship revenue surface area first.**
   - Fix OCR → unify web hub → pricing gates → promote → then expand agents/apps.

3. **Minimalist Voyadecir UI.**
   - Black/white aesthetic, sans-serif, clean spacing.
   - No analytics by default unless explicitly requested.

## Repos / Stack
### Frontend
- Static HTML/CSS/JS site hosted on Render.
- Domain: voyadecir.com (and www).
- Pages currently include translate + mail/bills (to be merged).

### Backend
- FastAPI on Render via Docker.
- OCR + translation endpoints.
- Environment-driven config.

### Azure
- Azure OpenAI for LLM.
- **Azure Document Intelligence Read OCR (primary OCR engine).**
- Azure Functions for OCR routing / mailbills parsing (current failure area). :contentReference[oaicite:1]{index=1}  

## Setup (Codex cloud task)
1. `pip install -r requirements.txt`
2. Install system deps:
   - `tesseract-ocr`
   - `tesseract-ocr-eng`
   - `tesseract-ocr-spa`
   - `poppler-utils`
   - `imagemagick`
3. Export env vars (see below).
4. Run tests: `pytest -q` (if present).
5. Run API: `uvicorn ai_translator.api:app --host 0.0.0.0 --port 8000`

## Env Vars
### Azure OpenAI
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION` (use latest supported)

### Azure OCR (Document Intelligence Read)
- `AZURE_DI_ENDPOINT`
- `AZURE_DI_API_KEY`
- `AZURE_DI_API_VERSION` (v4.0 GA)
- `AZURE_DI_MODEL=prebuilt-read`

### App Flags
- `OFFLINE_MODE=false`
- `HTTP_TIMEOUT_SECONDS=15`

## Run Commands
- API dev: `uvicorn ai_translator.api:app --reload`
- API prod-like: `uvicorn ai_translator.api:app --host 0.0.0.0 --port $PORT`
- Tests: `pytest`

## Style / Safety Rules
- Do not expose keys in frontend or commits.
- Do not add trackers.
- Keep EN/ES autodetect + manual toggle.
- Preserve Dockerfile + requirements completeness.
- Add retry, timeout, fallback handling for every external call.

## What Codex should prioritize
Follow TASKS.md strictly. Do not start P1 until P0 is complete and stable.
