from __future__ import annotations

from io import BytesIO
from typing import List

# Requires: reportlab
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def _wrap_lines(text: str, max_chars: int) -> List[str]:
    """
    Super simple word-wrap that works well enough for plain-text PDFs.
    """
    if not text:
        return []

    words = text.replace("\r\n", "\n").replace("\r", "\n").split()
    lines: List[str] = []
    current: List[str] = []

    for w in words:
        tentative = (" ".join(current + [w])).strip()
        if len(tentative) <= max_chars:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]

    if current:
        lines.append(" ".join(current))

    # Preserve some paragraph breaks (basic)
    # If you want exact newlines preserved, we can upgrade this later.
    return lines


def build_translated_pdf_bytes(
    original_text: str,
    translated_text: str,
    target_lang: str,
    source_filenames: List[str] | None = None,
) -> bytes:
    """
    Generates a clean, readable PDF with:
      - a header
      - the translated text
      - an optional appendix of the original OCR text (for transparency)
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    width, height = LETTER

    left = 0.75 * inch
    right = 0.75 * inch
    top = 0.85 * inch
    bottom = 0.75 * inch

    usable_width = width - left - right

    # Rough char-per-line estimate for Helvetica 11 (good enough)
    # If you want pixel-perfect wrapping, we can measure stringWidth instead.
    max_chars = 95

    def new_page():
        c.showPage()

    def draw_header(title: str, subtitle: str | None = None):
        c.setFont("Helvetica-Bold", 15)
        c.drawString(left, height - top, title)

        y = height - top - 18
        if subtitle:
            c.setFont("Helvetica", 10)
            c.drawString(left, y, subtitle)
            y -= 14

        # divider
        c.setLineWidth(0.5)
        c.line(left, y, width - right, y)
        return y - 18

    def draw_paragraph_lines(lines: List[str], start_y: float) -> float:
        y = start_y
        c.setFont("Helvetica", 11)
        line_height = 14

        for line in lines:
            if y <= bottom:
                new_page()
                y = height - top
                c.setFont("Helvetica", 11)
            # clip overly long lines
            c.drawString(left, y, line[: int(max_chars * 1.2)])
            y -= line_height

        return y

    # -------- Page 1: translated --------
    sources = ""
    if source_filenames:
        sources = " • ".join([s for s in source_filenames if s])

    y = draw_header(
        title="Voyadecir — Translated Document",
        subtitle=f"Target language: {target_lang.upper()}   |   Source files: {sources}" if sources else f"Target language: {target_lang.upper()}",
    )

    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Translation")
    y -= 18

    translated_lines = _wrap_lines(translated_text or "", max_chars=max_chars)
    y = draw_paragraph_lines(translated_lines, y)

    # -------- Appendix: original OCR --------
    new_page()
    y = draw_header("Appendix — Original Extracted Text (OCR)")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Original OCR text")
    y -= 18

    original_lines = _wrap_lines(original_text or "", max_chars=max_chars)
    _ = draw_paragraph_lines(original_lines, y)

    c.save()
    return buf.getvalue()

