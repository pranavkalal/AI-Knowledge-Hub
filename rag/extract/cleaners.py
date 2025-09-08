# rag/extract/cleaners.py
import re, unicodedata

# 1) Unicode + whitespace
CTRL = "".join(map(chr, list(range(0,9)) + [11,12] + list(range(14,32)) + [127]))
CTRL_RE = re.compile(f"[{re.escape(CTRL)}]")
WS_RE = re.compile(r"[ \t\u00A0]+")

def normalize_unicode(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = CTRL_RE.sub("", s)
    s = WS_RE.sub(" ", s)
    return s

# 2) Page furniture like "1 of 4", "2 of 4", "Page 3"
PAGE_FURNITURE = re.compile(
    r"""^\s*(?:page\s*\d+(?:\s*/\s*\d+)?|\d+\s+of\s+\d+)\s*$""",
    re.IGNORECASE
)

RULE_LINE = re.compile(r"^\s*[-_—]{3,}\s*$")

def strip_page_furniture(text: str) -> str:
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            out.append("")     # keep blank lines (paragraph breaks)
            continue
        if PAGE_FURNITURE.match(line) or RULE_LINE.match(line):
            continue
        out.append(line)
    return "\n".join(out)

# 3) Hyphenation and broken lines
HYPHEN_JOIN = re.compile(r"(\w)-\n([a-z])")   # join water-\nuse -> wateruse
INLINE_NL   = re.compile(r"(?<!\n)\n(?!\n)")  # single newline inside a paragraph

def fix_hyphenation_and_lines(s: str) -> str:
    s = HYPHEN_JOIN.sub(r"\1\2", s)
    s = INLINE_NL.sub(" ", s)
    return s

# 4) Bullets/lists normalization
def normalize_bullets(text: str) -> str:
    # common bullet characters
    bullets = "•▪·●◦■□–-"
    norm = []
    for line in text.splitlines():
        s = line.lstrip()
        if not s:
            norm.append("")
            continue

        # if line starts with a bullet, normalize it
        if s[0] in bullets:
            s = "- " + s[1:].lstrip()

        # also replace inline bullets (e.g. "•", "▪", "·") with a dash
        s = re.sub(r"[•▪·]", "-", s)

        # roman numerals "(i)" or "(ii)" → dash
        s = re.sub(r"^\(?[ivxlcdm]+\)\s+", "- ", s, flags=re.I)

        norm.append(s)
    return "\n".join(norm)


# 5) Drop junk-only lines and compress blank gaps
ONLY_PUNCT = re.compile(r"^[\W_]{1,5}$")
MULTI_BLANKS = re.compile(r"\n{3,}")

def tidy_paragraphs(text: str) -> str:
    keep = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            keep.append("")
            continue
        if ONLY_PUNCT.match(s):
            continue
        keep.append(s)
    out = "\n".join(keep)
    out = MULTI_BLANKS.sub("\n\n", out)
    return out.strip()

def clean_document_text(text: str) -> str:
    text = normalize_unicode(text)
    text = strip_page_furniture(text)
    text = fix_hyphenation_and_lines(text)
    text = normalize_bullets(text)
    text = tidy_paragraphs(text)
    return text
# rag/extract/cleaners.py

HEADER_NOISE = re.compile(r'^(FINAL REPORT\s+TEMPLATE|CRDC ID:)', re.I)

def strip_page_furniture(text: str) -> str:
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            out.append("")  # preserve blank lines as paragraph breaks
            continue
        if PAGE_FURNITURE.match(line) or RULE_LINE.match(line) or HEADER_NOISE.match(line):
            continue
        out.append(line)
    return "\n".join(out)

