from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path
import tempfile
import subprocess

from ai_translator.utils.health import check_health
from ai_translator.translate.client import translate_text

app = FastAPI(
    title="AI Translator API",
    description="Translate text or PDF content into your target language using AI. 🚀",
    version="1.0.0",
)

# ---------------------------------------------------------
# CORS – allow your site(s)
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
# helper: run a system command
# ---------------------------------------------------------
def run_cmd(cmd: list[str]):
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
        )
        ok = proc.returncode == 0
        return ok, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return False, "", str(e)

# ---------------------------------------------------------
# root
# ---------------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "🎉 Welcome to the AI Translator API!",
        "status": "live",
        "endpoints": [
            "/translate",
            "/api/translate",
            "/translate-pdf",
            "/translate-image",
            "/health",
        ],
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
# form translate (keep)
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
# JSON translate – website uses this
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
# PDF upload → pdftoppm → tesseract → translate
# ---------------------------------------------------------
@app.post("/translate-pdf")
async def translate_pdf(file: UploadFile, target_lang: str = Form("es")):
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "input.pdf"
        with open(pdf_path, "wb") as f:
            f.write(await file.read())

        # PDF → PNG (first page)
        png_prefix = Path(tmpdir) / "page"
        ok, out, err = run_cmd([
            "/usr/bin/pdftoppm",
            str(pdf_path),
            str(png_prefix),
            "-png",
            "-f", "1",
            "-singlefile",
        ])
        if not ok:
            return JSONResponse(
                status_code=500,
                content={"error": "pdftoppm failed", "stderr": err},
            )

        png_path = Path(tmpdir) / "page.png"
        if not png_path.exists():
            return JSONResponse(
                status_code=500,
                content={"error": "PDF converted but page.png not found."},
            )

        # OCR with tesseract
        txt_out = Path(tmpdir) / "out"
        ok, out, err = run_cmd([
            "/usr/bin/tesseract",
            str(png_path),
            str(txt_out),
            "-l", "eng+spa",
        ])
        if not ok:
            return JSONResponse(
                status_code=500,
                content={"error": "tesseract failed", "stderr": err},
            )

        txt_file = Path(str(txt_out) + ".txt")
        if not txt_file.exists():
            return JSONResponse(
                status_code=500,
                content={"error": "tesseract did not produce text file."},
            )

        source_text = txt_file.read_text(encoding="utf-8", errors="ignore").strip()
        if not source_text:
            return JSONResponse(
                status_code=200,
                content={"warning": "OCR succeeded but no text found in PDF."},
            )

        translated = translate_text(source_text, target_lang)
        return {
            "source_text": source_text,
            "translated_text": translated,
            "target_lang": target_lang,
        }

# ---------------------------------------------------------
# Image upload → tesseract directly → translate
# (simplified to avoid ImageMagick issues)
# ---------------------------------------------------------
@app.post("/translate-image")
async def translate_image(file: UploadFile, target_lang: str = Form("es")):
    """
    1. save image
    2. run tesseract directly on it
    3. translate text
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = Path(tmpdir) / file.filename
        with open(img_path, "wb") as f:
            f.write(await file.read())

        # try OCR
        txt_out = Path(tmpdir) / "imgout"
        ok, out, err = run_cmd([
            "/usr/bin/tesseract",
            str(img_path),
            str(txt_out),
            "-l", "eng+spa",
        ])

        if not ok:
            # try again with just english
            ok2, out2, err2 = run_cmd([
                "/usr/bin/tesseract",
                str(img_path),
                str(txt_out),
                "-l", "eng",
            ])
            if not ok2:
                # return friendly message instead of 500
                return JSONResponse(
                    status_code=200,
                    content={
                        "warning": "Image received but OCR could not read it.",
                        "stderr": err2 or err,
                    },
                )

        txt_file = Path(str(txt_out) + ".txt")
        if not txt_file.exists():
            return JSONResponse(
                status_code=200,
                content={"warning": "OCR ran but no text file was produced."},
            )

        source_text = txt_file.read_text(encoding="utf-8", errors="ignore").strip()
        if not source_text:
            return JSONResponse(
                status_code=200,
                content={"warning": "OCR ran but found no text in the image."},
            )

        # translate the text we found
        try:
            translated = translate_text(source_text, target_lang)
        except Exception as e:
            return JSONResponse(
                status_code=200,
                content={
                    "warning": "OCR worked, but translation failed.",
                    "source_text": source_text,
                    "error": str(e),
                },
            )

        return {
            "source_text": source_text,
            "translated_text": translated,
            "target_lang": target_lang,
        }

# ---------------------------------------------------------
# local run
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("ai_translator.api:app", host="0.0.0.0", port=port, reload=True)
