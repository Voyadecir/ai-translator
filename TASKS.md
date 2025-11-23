# TASKS.md — Voyadecir Priority Backlog

## P0 — Fix OCR + ship unified revenue web hub (NOW)
### P0-A: OCR Reliability (blocking)
1. Implement OCR_DEBUG.md plan.
2. Make **Azure Document Intelligence Read OCR** the primary OCR engine. :contentReference[oaicite:2]{index=2}  
3. Add automatic fallback to local Tesseract OCR only if Azure OCR fails or confidence is low.
4. Add structured error reporting:
   - return stage + reason (upload parse / Azure call / fallback / extraction)
   - never show raw “server error” to user.
5. Add retries + exponential backoff for Azure OCR calls.
6. Add confidence scoring and low-quality scan warnings.

### P0-B: Unified Web Hub + Monetization
1. Merge translate.html + mail-bills.html into ONE page:
   - Tabbed or card sections:
     a) Quick Translate (text input)
     b) Bills & Mail Helper (upload PDF/image)
     c) Learn/FAQ + trust/privacy
2. Implement free vs Pro gates:
   - **Free**
     - Text translate: unlimited (soft cap ok)
     - Bills/Mail: 1 page, summary only, watermark or “preview”
   - **Pro**
     - multipage OCR
     - full explanation + next steps
     - saved history
3. Add “Upgrade to Pro” CTA tied to Bills/Mail results.
4. Wire contact form (Formspree).
5. Add email capture (footer or modal).
6. Add 3 SEO blocks on unified page:
   - Bills Helper page section
   - USPS/Mail Helper section
   - FAQ schema section
7. Mobile responsiveness + accessibility pass.

## P1 — Mobile Apps (immediately after P0)
1. Android app (Kotlin), store-ready:
   - Minimal Voyadecir styling
   - Screens: Translate Text, Bills/Mail Upload, Settings/Privacy
   - Calls same API endpoints
   - Multipart uploads
   - Robust offline/error states + cached last known result
2. iOS app (SwiftUI), store-ready:
   - Same features and structure
3. Shared:
   - central API base URL config
   - privacy/terms links
   - redundancy in network calls (retry + fallback messaging)
4. Defer native in-app purchases until Pro stabilizes on web.

## P2 — Homepage Bilingual Chatbot
1. Floating widget matching Voyadecir style.
2. Auto detect EN/ES from user input; respond in same language.
3. Backend `/api/chat` endpoint on Render that calls Azure OpenAI.
4. Streaming responses.
5. Redundant model routing: Azure primary, backup model if Azure is down.

## P3 — Deep Agent MVP for Bills & Mail Helper
1. Add `agents/` module:
   - ocr_tool (Azure primary + fallback)
   - doc_classifier
   - field_extractor
   - translator_tool
   - explainer_tool
   - orchestrator (stateful deep agent)
2. Store templates + schemas:
   - SQLite + local vector index (FAISS/Chroma)
3. Add “human review → save template” admin flow.
4. Redundant execution:
   - retry per tool
   - fallback per tool
   - graceful partial results.

## P4 — Research Agent (nationwide doc templates)
1. Collect public utility + USPS/mail examples.
2. Extract layouts + key fields.
3. Add novelty detector for unseen formats.
4. Weekly scheduled runs with summaries.

## P5 — Marketing Agents Suite
1. SEO content draft agent.
2. Social post generator (EN/ES).
3. Outreach personalization agent.
4. Competitor monitor agent.
5. Analytics summary agent.
6. Supervisor agent to coordinate marketing sub-agents.

### Global Acceptance Criteria
- All P0 items stable in production before P1 starts.
- Every external dependency has retry + fallback behavior.
- No secrets in frontend.
- UI remains minimalist Voyadecir brand.
