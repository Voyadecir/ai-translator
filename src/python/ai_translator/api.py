from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path

from ai_translator.utils.health import check_health
from ai_translator.translate.client import translate_text

app = FastAPI(
    title="AI Translator API",
    description="Translate text or PDF content into your target language using AI. 🚀",
    version="1.0.0",
)

# ---------------------------------------------------------
# 1) CORS – let your website talk to this API
# ---------------------------------------------------------
# add here every domain that should be allowed to call the API
origins = [
    "https://voyadecir.com",
    "https://www.voyadecir.com",
    "https://voyadecir-site.onrender.com",  # keep this while you test on Render
    "http://localhost:8000",  # local testing (optional)
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
# Root route (homepage)
# ---------------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "🎉 Welcome to the AI Translator API!",
        "status": "live",
        "docs": "/docs",
        "usage": {
            "translate_text_form": "POST /translate with form-data {'text': 'Hello', 'target_lang': 'es'}",
            "translate_text_json": "POST /api/translate with JSON {'text': 'Hello', 'target_lang': 'es'}",
            "health_check": "GET /health",
        },
    }

# ---------------------------------------------------------
# Health check route
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
# 2) OLD/FORMS endpoint – keep this for compatibility
# ---------------------------------------------------------
@app.post("/translate")
async def translate_endpoint(
    text: str = Form(...),
    target_lang: str = Form("es"),
):
    """
    Translate text into the given target language (form-data version).
    """
    try:
        result = translate_text(text, target_lang)
        return {"original": text, "translated": result, "target_lang": target_lang}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "hint": "Check your API key or input text."},
        )

# ---------------------------------------------------------
# 3) NEW/JSON endpoint – what the website uses
# ---------------------------------------------------------
@app.post("/api/translate")
async def translate_json(request: Request):
    """
    JSON version for the static site:
    {
      "text": "Hello world",
      "source_lang": "en" (optional),
      "target_lang": "es"
    }
    """
    data = await request.json()
    text = data.get("text", "")
    target_lang = data.get("target_lang", "es")

    if not text.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "No text provided."},
        )

    try:
        translated = translate_text(text, target_lang)
        return {
            "original_text": text,
            "translated_text": translated,
            "target_lang": target_lang,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "hint": "Check your translation provider / API key."},
        )

# ---------------------------------------------------------
# PDF upload endpoint (optional)
# ---------------------------------------------------------
@app.post("/translate-pdf")
async def translate_pdf(file: UploadFile, target_lang: str = Form("es")):
    """
    Accepts a PDF upload and translates its text.
    (Right now just saves the file — you can hook in your PDF pipeline here.)
    """
    pdf_dir = Path("pdfs")
    pdf_dir.mkdir(exist_ok=True)
    temp_path = pdf_dir / file.filename

    # Save uploaded PDF
    with open(temp_path, "wb") as f:
      f.write(await file.read())

    return {
        "file": file.filename,
        "target_lang": target_lang,
        "status": "Uploaded successfully",
    }

# ---------------------------------------------------------
# Run (for local testing only)
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("ai_translator.api:app", host="0.0.0.0", port=port, reload=True)
