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
# helper: run system command
# ---------------------------------------------------------
def run_cmd(cmd: list[str]):
    """Run a system command and return (ok, stdout, stderr)."""
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
# form translate (kept for compatibility)
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
# JSON translate – used by your website
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
    """
    1. Save PDF to temp
    2. Use /usr/bin/pdftoppm to convert first page to PNG
    3. Use /usr/bin/tesseract to OCR the PNG
    4. Translate OCR text
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "input.pdf"
        with open(pdf_path, "wb") as f:
            f.write(await file.read())

        # convert PDF → PNG (first page)
        png_prefix = Path(tmpdir) / "page"
        ok, out, err = run_cmd(
            [
                "/usr/bin/pdftoppm",
                str(pdf_path),
                str(png_prefix),
                "-png",
                "-f",
                "1",
                "-singlefile",
            ]
        )
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
        ok, out, err = run_cmd(
            [
                "/usr/bin/tesseract",
                str(png_path),
                str(txt_out),
                "-l",
                "eng+spa",
            ]
        )
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
# Image upload → magick (optional) → tesseract → translate
# ---------------------------------------------------------
@app.post("/translate-image")
async def translate_image(file: UploadFile, target_lang: str = Form("es")):
    """
    1. Save image
    2. Try to normalize to PNG using /usr/bin/magick
    3. OCR with tesseract
    4. Translate
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = Path(tmpdir) / file.filename
        with open(raw_path, "wb") as f:
            f.write(await file.read())

        # normalize to png
        png_path = Path(tmpdir) / "input.png"
        ok, _, _ = run_cmd(
            [
                "/usr/bin/magick",
                str(raw_path),
                str(png_path),
            ]
        )
        if not ok:
            # maybe it was already png
            png_path = raw_path

        # OCR
        txt_out = Path(tmpdir) / "imgout"
        ok, out, err = run_cmd(
            [
                "/usr/bin/tesseract",
                str(png_path),
                str(txt_out),
                "-l",
                "eng+spa",
            ]
        )
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
                content={"warning": "OCR succeeded but no text found in image."},
            )

        translated = translate_text(source_text, target_lang)
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
