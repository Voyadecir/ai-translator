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
