# rag/extract/cleaners.py
import re, unicodedata
from typing import List

# --- 1) Unicode + whitespace normalisation ---
CTRL = "".join(map(chr, list(range(0,9)) + [11,12] + list(range(14,32)) + [127]))
CTRL_RE = re.compile(f"[{re.escape(CTRL)}]")
WS_RE = re.compile(r"[ \t\u00A0]+")

def normalize_unicode(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = CTRL_RE.sub("", s)
    s = WS_RE.sub(" ", s)
    return s

# --- 2) Hyphenation + broken lines ---
# join "water-\nuse" -> "wateruse" only if next char is lowercase (avoid real hyphens)
HYPHEN_JOIN = re.compile(r"(\w)-\n([a-z])")
# merge single newlines inside paragraphs; keep blank lines as paragraph breaks
INLINE_NL = re.compile(r"(?<!\n)\n(?!\n)")

def fix_hyphenation_and_lines(s: str) -> str:
    s = HYPHEN_JOIN.sub(r"\1\2", s)
    s = INLINE_NL.sub(" ", s)
    return s

# --- 3) Headers/footers, page furniture ---
PAGE_FURNITURE = re.compile(
    r"""^(
           page\s*\d+(\s*/\s*\d+)?            # "Page 3" or "3/12"
         | \d+\s+of\s+\d+                     # "2 of 4"
         | ^_{3,}$ | ^-{3,}$ | ^—{3,}$        # rule lines
       )$""",
    re.IGNORECASE | re.VERBOSE,
)

def strip_page_furniture(text: str) -> str:
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            out.append("")
