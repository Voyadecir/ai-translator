# TASKS.md — Voyadecir Priority Backlog (Updated)

## P0 — Stabilize OCR + Ship Unified Revenue Hub (RIGHT NOW)

### P0-A: OCR Stabilization & Quality (blocking)
Status: **Baseline OCR works in production. Now we harden + improve quality.**

1. ✅ Baseline Azure Document Intelligence Read OCR working end-to-end.
2. Make **Azure Document Intelligence Read OCR** the primary OCR engine.
3. Confirm fallback to local Tesseract only when:
   - Azure fails/timeouts, or
   - confidence < threshold (default 0.75).
4. Add structured stage-based errors for *every OCR request*:
   - stages: upload_parse / pdf_to_image / preprocess / azure_call / fallback_call / extraction
   - never return generic “server error” to users.
5. Add retries + exponential backoff for Azure OCR calls (Tenacity).
6. Add confidence scoring + warnings:
   - “scan is low quality” / “photo too dark” / “tilted image”
   - suggest retake tips in EN/ES.
7. Add preprocessing tuned for phone photos:
   - grayscale → deskew → adaptive threshold → denoise → sharpen
   - save debug artifacts when DEBUG_OCR=true.
8. Add acceptance tests + fixtures:
   - clean PDF bill
   - skewed phone photo bill
   - USPS letter/notice scan
   Pass criteria:
   - ≥90% word recall on clean docs
   - ≥75% usable extraction on phone photos
   - stage errors visible on failure.
9. Add lightweight usage logging (no PII):
   - file type, page count, confidence, engine_used
   - no raw text stored by default.

---

### P0-B: Unified Web Hub + Monetization
Goal: **One elegant page that sells the Bills & Mail Helper.**

1. Merge `translate.html` + `mail-bills.html` into ONE hub page:
   - Sections or tabs:
     a) Quick Translate (text)
     b) Bills & Mail Helper (PDF/image upload)
     c) Learn/FAQ + trust/privacy
2. Free vs Pro gates:
   - **Free**
     - Text translate: unlimited (soft cap ok)
     - Bills/Mail: 1 page, summary only, watermark or preview
   - **Pro**
     - multipage OCR
     - full explanation + next steps
     - saved history
3. Add “Upgrade to Pro” CTA tied to Bills/Mail results.
4. Wire contact form (Formspree).
5. Add email capture (footer or modal).
6. Add 3 SEO blocks on hub:
   - Bills Helper section
   - USPS/Mail Helper section
   - FAQ schema section
7. Mobile responsiveness + accessibility pass.

---

## P1 — Mobile Apps (after P0 is stable)
1. Android app (Kotlin), store-ready:
   - Minimal Voyadecir style
   - Translate Text, Bills/Mail Upload, Settings/Privacy
   - Calls same API endpoints
   - Robust offline/error states
2. iOS app (SwiftUI), store-ready:
   - same features + structure
3. Shared:
   - central API base URL config
   - privacy/terms links
   - retry + fallback messaging

---

## P2 — Homepage Bilingual Chatbot
1. Floating widget matching Voyadecir style.
2. Auto detect EN/ES; respond in same language.
3. Backend `/api/chat` endpoint on Render calling Azure OpenAI.
4. Streaming responses.
5. Redundant model routing (Azure primary, backup model if Azure down).

---

## P3 — Deep Agent MVP for Bills & Mail Helper
1. Add `agents/` module:
   - ocr_tool (Azure primary + fallback)
   - doc_classifier
   - field_extractor
   - translator_tool
   - explainer_tool
   - orchestrator (stateful deep agent)
2. Store templates + schemas:
   - SQLite + local vector index
3. Add “human review → save template” admin flow.
4. Redundant execution:
   - retry per tool
   - fallback per tool
   - graceful partial results

---

## P4 — Research Agent (doc templates)
1. Collect public utility + USPS examples.
2. Extract layouts + key fields.
3. Novelty detector for unseen formats.
4. Weekly scheduled runs with summaries.

---

## P5 — Marketing Agents Suite
1. SEO content draft agent.
2. Social post generator (EN/ES).
3. Outreach personalization agent.
4. Competitor monitor agent.
5. Analytics summary agent.
6. Supervisor agent coordinating sub-agents.

---

### Global Acceptance Criteria
- All P0 items stable in production before P1 starts.
- Every external dependency has retry + fallback behavior.
- No secrets in frontend.
- UI remains minimalist Voyadecir brand.
