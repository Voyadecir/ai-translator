from __future__ import annotations

from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path
import tempfile
import subprocess

from ai_translator.utils.health import check_health
from ai_translator.translate.client import translate_text  # async in new client.py

app = FastAPI(
    title="AI Translator API",
    description="Translate text or PDF content into your target language using AI. 🚀",
    version="1.2.0",
)

# ---------------------------------------------------------
# CORS – allow your sites to call this API
# ---------------------------------------------------------
origins = [
    "https://voyadecir.com",
    "https://www.voyadecir.com",
    "https://voyadecir-site.onrender.com",
    # add your Azure Functions host later if needed, e.g.:
    # "https://voyadecir-ai-functions.azurewebsites.net",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# helper to run system commands
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
        "version": "1.2.0",
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
# form-style translate (kept)  ← now awaits async translate_text
# ---------------------------------------------------------
@app.post("/translate")
async def translate_form(
    text: str = Form(...),
    target_lang: str = Form("es"),
):
    try:
        translated = await translate_text(text, target_lang)
        return {"original": text, "translated": translated, "target_lang": target_lang}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ---------------------------------------------------------
# JSON translate – this is what your website calls  ← awaits too
# ---------------------------------------------------------
@app.post("/api/translate")
async def translate_json(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    text = (data.get("text") or "").strip()
    target_lang = (data.get("target_lang") or "es").strip()

    if not text:
        return JSONResponse(status_code=400, content={"error": "No text provided."})

    try:
        translated = await translate_text(text, target_lang)
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
# PDF upload → pdftoppm → tesseract → translate  ← awaits at the end
# ---------------------------------------------------------
@app.post("/translate-pdf")
async def translate_pdf(file: UploadFile, target_lang: str = Form("es")):
    """
    Uses the tools Render says you have:
    - /usr/bin/pdftoppm to convert first page → PNG
    - /usr/bin/tesseract to OCR that PNG
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "input.pdf"
        # read file once
        pdf_bytes = await file.read()
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        # PDF → PNG (first page only)
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

        # translate the OCR text (async)
        translated = await translate_text(source_text, target_lang)
        return {
            "source_text": source_text,
            "translated_text": translated,
            "target_lang": target_lang,
        }


# ---------------------------------------------------------
# IMAGE upload – SAFE STUB (always 200)
# ---------------------------------------------------------
@app.post("/translate-image")
async def translate_image(file: UploadFile, target_lang: str = Form("es")):
    """
    For now we just accept the image and return a friendly message.
    This avoids 500 errors while we finish real image OCR.
    """
    return {
        "warning": "Image received ✅ — image OCR is not enabled on the server yet.",
        "filename": file.filename,
        "target_lang": target_lang,
    }


# ---------------------------------------------------------
# local run
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("ai_translator.api:app", host="0.0.0.0", port=port, reload=True)
