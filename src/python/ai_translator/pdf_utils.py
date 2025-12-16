from __future__ import annotations

from io import BytesIO
from typing import List, Optional, Tuple

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics


# REQUIRED: exact short disclaimer on every PDF page (per your instruction)
PDF_FOOTER_DISCLAIMER = (
    "Disclaimer: Voyadecir is for informational translation only and is not HIPAA- or FERPA-compliant. "
    "Do not upload personal health information (PHI) or student education records. Not legal, medical, or financial advice."
)


def _wrap_text(text: str, font_name: str, font_size: int, max_width: float) -> List[str]:
    """
    Basic word-wrap using ReportLab font metrics.
    """
    if not text:
        return [""]

    words = text.replace("\r\n", "\n").replace("\r", "\n").split()
    lines: List[str] = []
    current: List[str] = []

    def line_width(s: str) -> float:
        return pdfmetrics.stringWidth(s, font_name, font_size)

    for w in words:
        # Preserve simple paragraph breaks by treating \n as hard breaks
        if "\n" in w:
            parts = w.split("\n")
            for i, part in enumerate(parts):
                if part:
                    test = (" ".join(current + [part])).strip()
                    if test and line_width(test) <= max_width:
                        current.append(part)
                    else:
                        if current:
                            lines.append(" ".join(current))
                        current = [part]
                if i < len(parts) - 1:
                    # hard break
                    if current:
                        lines.append(" ".join(current))
                    lines.append("")  # blank line between paragraphs
                    current = []
            continue

        test = (" ".join(current + [w])).strip()
        if not test:
            continue

        if line_width(test) <= max_width:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]

    if current:
        lines.append(" ".join(current))

    return lines


def _draw_footer(c: canvas.Canvas, page_w: float, page_h: float) -> None:
    """
    Footer disclaimer on every page.
    """
    c.saveState()
    c.setFont("Helvetica", 8)

    margin_x = 0.65 * inch
    footer_y = 0.45 * inch

    # Wrap footer into up to 2 lines if needed
    max_w = page_w - (2 * margin_x)
    lines = _wrap_text(PDF_FOOTER_DISCLAIMER, "Helvetica", 8, max_w)
    if len(lines) > 2:
        # Be defensive: keep it readable, not a 9-line legal brick at the bottom
        lines = lines[:2]

    # Draw from bottom up
    y = footer_y
    for line in reversed(lines):
        c.drawString(margin_x, y, line)
        y += 9

    c.restoreState()


def _new_page(c: canvas.Canvas, page_w: float, page_h: float) -> None:
    """
    Finish current page with footer, then start a new page.
    """
    _draw_footer(c, page_w, page_h)
    c.showPage()


def build_translated_pdf_bytes(
    original_text: str,
    translated_text: str,
    target_lang: str = "es",
    source_filenames: Optional[List[str]] = None,
) -> bytes:
    """
    Create a PDF containing:
      - Title + metadata
      - Translated text
      - Original text (for verification)

    Always stamps disclaimer at bottom of EVERY page.
    Returns raw PDF bytes.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)

    page_w, page_h = LETTER
    margin_x = 0.75 * inch
    top_y = page_h - 0.85 * inch
    bottom_limit = 1.10 * inch  # keep space for footer + breathing room

    title_font = ("Helvetica-Bold", 16)
    h2_font = ("Helvetica-Bold", 12)
    body_font = ("Helvetica", 10)

    def draw_heading(text: str, y: float) -> float:
        c.setFont(title_font[0], title_font[1])
        c.drawString(margin_x, y, text)
        return y - 22

    def draw_subheading(text: str, y: float) -> float:
        c.setFont(h2_font[0], h2_font[1])
        c.drawString(margin_x, y, text)
        return y - 16

    def draw_paragraph(text: str, y: float, font_name: str, font_size: int) -> float:
        c.setFont(font_name, font_size)
        max_w = page_w - (2 * margin_x)
        lines = _wrap_text(text, font_name, font_size, max_w)

        line_h = font_size + 3
        for line in lines:
            if y <= bottom_limit:
                _new_page(c, page_w, page_h)
                y = top_y
                c.setFont(font_name, font_size)

            # Blank line support
            if line == "":
                y -= line_h
                continue

            c.drawString(margin_x, y, line)
            y -= line_h

        return y

    # -----------------------
    # Page 1 header
    # -----------------------
    y = top_y
    y = draw_heading("Voyadecir — Translated Document", y)

    # Small metadata line
    c.setFont("Helvetica", 9)
    src_label = ""
    if source_filenames:
        safe_list = [s for s in source_filenames if s]
        if safe_list:
            src_label = "Source files: " + ", ".join(safe_list[:6]) + ("…" if len(safe_list) > 6 else "")

    meta = f"Target language: {target_lang.upper()}   {src_label}".strip()
    if meta:
        c.drawString(margin_x, y, meta)
        y -= 16

    y -= 6

    # -----------------------
    # Translated section
    # -----------------------
    y = draw_subheading("Translation", y)
    y = draw_paragraph(translated_text or "", y, body_font[0], body_font[1])

    y -= 10

    # -----------------------
    # Original section
    # -----------------------
    y = draw_subheading("Original Text (for verification)", y)
    y = draw_paragraph(original_text or "", y, body_font[0], body_font[1])

    # Final footer + finish
    _draw_footer(c, page_w, page_h)
    c.save()

    return buf.getvalue()
