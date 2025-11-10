from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path

from ai_translator.utils.health import check_health
from ai_translator.translate.client import translate_text  # your original import

app = FastAPI(
    title="AI Translator API",
    description="Translate text or PDF content into your target language using AI. 🚀",
    version="1.0.0",
)

# ---------------------------------------------------------
# CORS – allow your website to call this API
# ---------------------------------------------------------
origins = [
    "https://voyadecir.com",
    "https://www.voyadecir.com",
    "https://voyadecir-site.onrender.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Root
# ---------------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "🎉 Welcome to the AI Translator API!",
        "status": "live",
        "docs": "/docs",
        "endpoints": ["/translate", "/api/translate", "/translate-pdf", "/health"],
    }

# ---------------------------------------------------------
# Health
# ---------------------------------------------------------
@app.get("/health")
def health_check():
    health = check_health()
    return {
        "tesseract": str(health.tesseract_path),
        "poppler": str(health.poppler_path),
        "magick": str(health.magick_path),
        "internet_ok": health.internet_ok,
        "openai_key_present": health.openai_key_present,
    }

# ---------------------------------------------------------
# OLD: form version (keep)
# ---------------------------------------------------------
@app.post("/translate")
async def translate_form(
    text: str = Form(...),
    target_lang: str = Form("es"),
):
    try:
        result = translate_text(text, target_lang)
        return {"original": text, "translated": result, "target_lang": target_lang}
    except Exception as e:
        # return a friendly error
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "hint": "Form endpoint failed."},
        )

# ---------------------------------------------------------
# NEW: JSON version for your website
# ---------------------------------------------------------
@app.post("/api/translate")
async def translate_json(request: Request):
    """
    Expected JSON:
    {
      "text": "Hello world",
      "target_lang": "es"
    }
    """
    data = await request.json()
    text = data.get("text", "").strip()
    target_lang = data.get("target_lang", "es")

    if not text:
        return JSONResponse(status_code=400, content={"error": "No text provided."})

    try:
        # try your real translator first
        translated = translate_text(text, target_lang)
        return {
            "original_text": text,
            "translated_text": translated,
            "target_lang": target_lang,
        }
    except Exception as e:
        # if your real translator breaks, send back a dummy translation
        # so the front-end still works
        fallback = f"[fallback {target_lang}] {text}"
        return {
            "original_text": text,
            "translated_text": fallback,
            "target_lang": target_lang,
            "warning": f"Translator raised: {str(e)}"
        }

# ---------------------------------------------------------
# PDF upload (as you had it)
# ---------------------------------------------------------
@app.post("/translate-pdf")
async def translate_pdf(file: UploadFile, target_lang: str = Form("es")):
    pdf_dir = Path("pdfs")
    pdf_dir.mkdir(exist_ok=True)
    temp_path = pdf_dir / file.filename

    with open(temp_path, "wb") as f:
        f.write(await file.read())

    return {
        "file": file.filename,
        "target_lang": target_lang,
        "status": "Uploaded successfully",
    }

# ---------------------------------------------------------
# Run locally
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("ai_translator.api:app", host="0.0.0.0", port=port, reload=True)
