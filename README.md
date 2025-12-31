# Voyadecir Backend — ai-translator

This repository contains the **backend API** for Voyadecir.

It is the **single source of intelligence** for:
- OCR orchestration
- translation
- document parsing
- explanations
- agent logic

---

## What This Repo Owns

- FastAPI application
- All document ingestion logic
- OCR routing (Azure primary, fallback only by rule)
- Language translation
- Plain-language explanations
- API responses consumed by all clients (web + future mobile)

If logic involves understanding, interpreting, or explaining documents,
it belongs here.

---

## What This Repo Does NOT Own

- UI rendering
- Styling or layout
- Client-side language detection
- Any secrets exposed to the frontend

---

## Architecture Rules (Non-Negotiable)

- All intelligence runs server-side
- No client-side LLM calls
- No duplicated logic across repos
- No silent failures
- No “best effort” OCR without confidence reporting

---

## OCR Behavior (Authoritative Pointer)

OCR rules are defined centrally in the meta repo:

voyadecir-meta/OCR_DEBUG.md

This repo must follow those rules exactly:
- Azure Document Intelligence Read is primary
- Fallback only on failure or low confidence
- Stage-based errors are mandatory
- Generic errors are forbidden

If there is any conflict, the meta repo wins.

---

## API Endpoints (Public)

- POST /api/translate
- POST /api/mailbills/parse

All clients (web and future mobile) use these endpoints.

---

## Deployment

- Hosted on Render as a Docker-based Web Service
- Push to main triggers rebuild
- Dockerfile at repo root is required

Startup command (single line):

uvicorn ai_translator.api:app --host 0.0.0.0 --port $PORT

---

## Environment Variables (Required)

Azure OCR:
- AZURE_DI_ENDPOINT
- AZURE_DI_API_KEY
- AZURE_DI_API_VERSION
- AZURE_DI_MODEL=prebuilt-read

Azure OpenAI:
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_API_KEY
- AZURE_OPENAI_DEPLOYMENT
- AZURE_OPENAI_API_VERSION

App Settings:
- OFFLINE_MODE=false
- HTTP_TIMEOUT_SECONDS=15
- OCR_CONFIDENCE_THRESHOLD=0.75 (optional)
- DEBUG_OCR=false (optional)

Never hardcode secrets.

---

## Source of Truth

Authoritative rules live in the meta repo:

- Architecture: voyadecir-meta/README.md
- AI rules: voyadecir-meta/AGENTS.md
- Priorities: voyadecir-meta/TASKS.md
- OCR behavior: voyadecir-meta/OCR_DEBUG.md

If this README conflicts with those, those win.
