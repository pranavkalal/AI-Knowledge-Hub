# rag/extract/parse_pdf.py
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
import datetime
import os

# New deps:
# pip install pymupdf pdfplumber pytesseract Pillow
import fitz  # PyMuPDF
import pdfplumber
from PIL import Image
import io
import pytesseract

# Keep this constant in sync with chunker
PAGE_BREAK = "\n\n----- PAGE BREAK -----\n\n"


@dataclass
class ParsedPDF:
    text: str
    meta: Dict[str, str]


#  Helpers 
def _page_text_pymupdf(doc: fitz.Document, page_idx: int) -> str:
    """
    Extract text with layout from a page using PyMuPDF.
    'text' preserves reading order better than pypdf.
    """
    page = doc.load_page(page_idx)
    # 'text' is a good default. 'blocks' or 'dict' can be used for finer control.
    return page.get_text("text")


def _tables_pdfplumber(pdf_path: str) -> Dict[int, List[List[List[str]]]]:
    """
    Extract tables per page as a list of 2D tables (rows -> cells).
    Returns {page_index: [table1_rows, table2_rows, ...]}.
    """
    tables_by_page: Dict[int, List[List[List[str]]]] = {}
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_tables: List[List[List[str]]] = []
            try:
                tables = page.extract_tables()
                for tbl in tables or []:
                    # Normalize cells to strings
                    norm = [[(c if c is not None else "").strip() for c in row] for row in tbl]
                    # keep only tables with at least one non-empty cell
                    if any(any(cell for cell in row) for row in norm):
                        page_tables.append(norm)
            except Exception:
                pass
            if page_tables:
                tables_by_page[i] = page_tables
    return tables_by_page


def _markdown_table(rows: List[List[str]]) -> str:
    """
    Convert a 2D array to GitHub-style Markdown table.
    If first row looks like a header, use it; otherwise synthesize headers.
    """
    if not rows:
        return ""
    header = rows[0]
    body = rows[1:] if len(rows) > 1 else []
    if not any(cell.strip() for cell in header):
        # synthesize
        n = max(len(r) for r in rows)
        header = [f"Col {i+1}" for i in range(n)]
        body = rows

    # pad ragged rows
    width = max(len(header), *(len(r) for r in body)) if body else len(header)

    def pad(row): return row + [""] * (width - len(row))

    header = pad(header)
    body = [pad(r) for r in body]

    out = []
    out.append("| " + " | ".join(header) + " |")
    out.append("| " + " | ".join(["---"] * width) + " |")
    for r in body:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def _rasterize_page(doc: fitz.Document, page_idx: int, dpi: int = 300) -> Image.Image:
    page = doc.load_page(page_idx)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return img


def _ocr_image(img: Image.Image, lang: str = "eng") -> str:
    try:
        return pytesseract.image_to_string(img, lang=lang)
    except Exception:
        return ""


def _should_ocr_page(native_text: str) -> bool:
    """
    Heuristic: OCR page if native text is very sparse (e.g., scanned page).
    """
    # Count alphanumerics; if too low, likely image-based page
    alnum = sum(ch.isalnum() for ch in native_text)
    return alnum < 80  # tweakable threshold


def _extract_image_ocr_regions(doc: fitz.Document, page_idx: int, max_dim: int = 200) -> str:
    """
    OCR embedded images on a page that are large enough to contain text.
    Returns concatenated OCR text for those images.
    """
    page = doc.load_page(page_idx)
    text_chunks: List[str] = []
    for img_ref in page.get_images(full=True):
        xref = img_ref[0]
        try:
            base_image = doc.extract_image(xref)
            img_bytes = base_image["image"]
            img = Image.open(io.BytesIO(img_bytes))
            # Skip very small graphics (icons)
            if max(img.size) < max_dim:
                continue
            text_chunks.append(_ocr_image(img))
        except Exception:
            continue
    return "\n".join(t for t in text_chunks if t.strip())


# Main API 
def parse_pdf(pdf_path: str, extra_meta: Optional[Dict[str, str]] = None) -> ParsedPDF:
    """
    Multi-stage extractor:
      1) PyMuPDF text
      2) pdfplumber tables -> Markdown tables
      3) OCR fallback for image-only pages + OCR of large embedded images
    """
    # Base metadata
    stat = os.stat(pdf_path)
    meta: Dict[str, str] = {
        "filename": os.path.basename(pdf_path),
        "path": pdf_path,
        "size_bytes": str(stat.st_size),
        "mtime": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "extractor": "pymupdf+pdfplumber+tesseract",
        "dpi": "300",
    }
    if extra_meta:
        meta.update({k: str(v) for k, v in extra_meta.items() if v is not None})

    # 1) Native text per page
    doc = fitz.open(pdf_path)
    native_text_by_page = [(_page_text_pymupdf(doc, i) or "").strip() for i in range(len(doc))]

    # 2) Tables (once, using pdfplumber)
    tables_by_page = _tables_pdfplumber(pdf_path)  # {page_idx: [table_rows, ...]}

    # Provenance collectors
    ocr_pages: List[int] = []
    table_pages: List[int] = []
    table_count_total = 0

    # 3) Compose page text with OCR/table augmentation
    pages_out: List[str] = []

    for i in range(len(doc)):
        parts: List[str] = []
        ntxt = native_text_by_page[i]
        did_ocr = False
        had_table = False

        # include native text if present
        if ntxt:
            parts.append(ntxt)

        # attach tables as Markdown so the downstream cleaner doesn't flatten them
        if i in tables_by_page:
            for t in tables_by_page[i]:
                md = _markdown_table(t)
                if md:
                    parts.append(md)
                    had_table = True
                    table_count_total += 1

        # decide whether to OCR the whole page
        if _should_ocr_page(ntxt):
            try:
                img = _rasterize_page(doc, i, dpi=300)
                ocr_txt = _ocr_image(img)
                if ocr_txt.strip():
                    parts.append(ocr_txt)
                    did_ocr = True
            except Exception:
                pass

        # Also OCR large embedded images (captures charts/figures with labels)
        try:
            img_ocr = _extract_image_ocr_regions(doc, i)
            if img_ocr.strip():
                parts.append(img_ocr)
                did_ocr = True or did_ocr
        except Exception:
            pass

        if did_ocr:
            ocr_pages.append(i)
        if had_table:
            table_pages.append(i)

        page_text = "\n\n".join(p for p in parts if p and p.strip())
        pages_out.append(page_text)

    doc.close()

    # Build final text with hard page boundaries
    full_text = PAGE_BREAK.join(pages_out).strip()

    # Transparent provenance in meta
    total_pages = len(pages_out)
    ocr_page_count = len(ocr_pages)
    table_page_count = len(set(table_pages))

    meta.update({
        "total_pages": str(total_pages),
        "ocr_page_count": str(ocr_page_count),
        "ocr_pages": ",".join(map(str, ocr_pages)) if ocr_pages else "",
        "ocr_ratio": f"{(ocr_page_count / max(1, total_pages)):.3f}",
        "table_page_count": str(table_page_count),
        "table_pages": ",".join(map(str, sorted(set(table_pages)))) if table_pages else "",
        "table_count": str(table_count_total),
    })

    return ParsedPDF(text=full_text, meta=meta)
