from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path
import tempfile

from ai_translator.utils.health import check_health
from ai_translator.translate.client import translate_text

# try to import OCR helpers, but don't die if not installed
try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None
    Image = None

# optional: PDF → images
try:
    from pdf2image import convert_from_path
except Exception:
    convert_from_path = None

app = FastAPI(
    title="AI Translator API",
    description="Translate text or PDF content into your target language using AI. 🚀",
    version="1.0.0",
)

# ---------------------------------------------------------
# CORS – allow your website
# ---------------------------------------------------------
origins = [
    "https://voyadecir.com",
    "https://www.voyadecir.com",
    "https://voyadecir-site.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# root
# ---------------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "🎉 Welcome to the AI Translator API!",
        "status": "live",
        "endpoints": ["/translate", "/api/translate", "/translate-pdf", "/translate-image", "/health"],
    }

# ---------------------------------------------------------
# health
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
# form translate (kept)
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
# JSON translate (used by your website)
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
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "hint": "Translator raised an error."},
        )

# ---------------------------------------------------------
# PDF upload → OCR → translate
# ---------------------------------------------------------
@app.post("/translate-pdf")
async def translate_pdf(file: UploadFile, target_lang: str = Form("es")):
    """
    1. Save uploaded PDF
    2. If pdf2image + tesseract available → OCR → translate
    3. Otherwise return a friendly message
    """
    # save temp
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        pdf_path = tmp.name

    if convert_from_path and pytesseract:
        # convert first page to image and OCR it
        try:
            images = convert_from_path(pdf_path, first_page=1, last_page=1)
            if images:
                text = pytesseract.image_to_string(images[0])
                translated = translate_text(text, target_lang)
                return {
                    "source_text": text,
                    "translated_text": translated,
                    "target_lang": target_lang,
                }
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": f"OCR failed: {str(e)}"},
            )
    # fallback
    return JSONResponse(
        status_code=200,
        content={
            "warning": "OCR not available on server. PDF received but not processed.",
            "filename": file.filename,
            "target_lang": target_lang,
        },
    )

# ---------------------------------------------------------
# Image upload → OCR → translate
# ---------------------------------------------------------
@app.post("/translate-image")
async def translate_image(file: UploadFile, target_lang: str = Form("es")):
    """
    1. Accept image (from camera or upload)
    2. OCR it with tesseract
    3. Translate text
    """
    if not (pytesseract and Image):
        return JSONResponse(
            status_code=200,
            content={
                "warning": "OCR not available on server.",
                "target_lang": target_lang,
            },
        )

    # save to temp and open
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(await file.read())
        img_path = tmp.name

    try:
        img = Image.open(img_path)
        text = pytesseract.image_to_string(img)
        translated = translate_text(text, target_lang)
        return {
            "source_text": text,
            "translated_text": translated,
            "target_lang": target_lang,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Image OCR failed: {str(e)}"},
        )

# ---------------------------------------------------------
# local run
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("ai_translator.api:app", host="0.0.0.0", port=port, reload=True)
