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
# CORS: allow your website to call this API
# ---------------------------------------------------------
origins = [
    "https://voyadecir.com",
    "https://www.voyadecir.com",
    "https://voyadecir-site.onrender.com"  # your static site on Render
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
# OLD form-style translate (keep)
# ---------------------------------------------------------
@app.post("/translate")
async def translate_form(
    text: str = Form(...),
    target_lang: str = Form("es"),
):
    try:
        translated = translate_text(text, target_lang)
        return {"original": text, "translated": translated, "target_lang": target_lang}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ---------------------------------------------------------
# NEW JSON translate – this is what your website calls
# ---------------------------------------------------------
@app.post("/api/translate")
async def translate_json(request: Request):
    data = await request.json()
    text = (data.get("text") or "").strip()
    target_lang = data.get("target_lang", "es")

    if not text:
        return JSONResponse(status_code=400, content={"error": "No text provided."})

    try:
        translated = translate_text(text, target_lang)
        return {
            "original_text": text,
            "translated_text": translated,
            "target_lang": target_lang,
        }
    except Exception as e:
        # if translation blows up, at least return something
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "hint": "Translator raised an error on the server."
            },
        )

# ---------------------------------------------------------
# PDF upload (kept)
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
# Local run
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("ai_translator.api:app", host="0.0.0.0", port=port, reload=True)
