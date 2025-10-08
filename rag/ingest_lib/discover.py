import re
import time
import urllib.parse
from dataclasses import dataclass
from typing import Iterable, List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup
from urllib.parse import urldefrag, urljoin

@dataclass(frozen=True)
class Link:
    url: str
    source_page: str
    year: Optional[int] = None
    title: Optional[str] = None

HTML_HEADERS = {
    # pretend to be a normal browser so InsideCotton stops being precious
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def _guess_year(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"(19|20)\d{2}", text)
    if not m:
        return None
    y = int(m.group(0))
    return y if 1900 <= y <= 2099 else None

def _fetch_soup(url: str, timeout: int) -> Optional[BeautifulSoup]:
    try:
        base, _frag = urldefrag(url)
        r = requests.get(base, headers=HTML_HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code in (415, 406, 405):
            # retry once, some pages misbehave with content negotiation
            r = requests.get(base, headers=HTML_HEADERS, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"[discover][skip] {url} -> {e}")
        return None

def collect_pdf_links(
    seed_urls: Iterable[str],
    include_patterns: List[str],
    exclude_patterns: List[str],
    years: Optional[Iterable[int]],
    timeout: int,
    user_agent: str,  # kept for config compatibility
) -> List[Link]:
    # compile filters
    inc_res = [re.compile(p, re.I) for p in (include_patterns or [r"\.pdf$"])]
    exc_res = [re.compile(p, re.I) for p in (exclude_patterns or [])]
    years_set = set(years) if years else None

    seen: Set[str] = set()
    out: List[Link] = []

    def included(txt: str) -> bool:
        return any(rx.search(txt) for rx in inc_res)

    def excluded(txt: str) -> bool:
        return any(rx.search(txt) for rx in exc_res)

    for seed in seed_urls:
        soup = _fetch_soup(seed, timeout)
        if not soup:
            continue

        seed_year = _guess_year(seed)

        # collect anchors from the seed page
        anchors = soup.find_all("a", href=True)
        for a in anchors:
            href = urljoin(seed, a["href"].strip())
            label = a.get_text(strip=True) or ""
            text_for_filters = f"{label} {href}"

            if excluded(text_for_filters):
                continue

            # Case 1: direct PDF on listing
            if href.lower().endswith(".pdf") and included(text_for_filters):
                candidate_url = href
                title = label or None
            else:
                # Case 2: second hop to detail page, find a link ending with .pdf
                inner = _fetch_soup(href, timeout)
                if not inner:
                    continue
                candidate_url = None
                inner_a = inner.find_all("a", href=True)
                for a2 in inner_a:
                    href2 = urljoin(href, a2["href"].strip())
                    if href2.lower().endswith(".pdf") and included(f"{a2.get_text(strip=True)} {href2}"):
                        candidate_url = href2
                        break
                if not candidate_url:
                    continue
                title = label or None  # keep listing title if we have it

            if candidate_url in seen:
                continue
            seen.add(candidate_url)

            yr = _guess_year(label) or _guess_year(candidate_url) or seed_year
            if years_set and yr and yr not in years_set:
                continue

            out.append(Link(url=candidate_url, source_page=seed, year=yr, title=title))

        # politeness
        time.sleep(0.2)

    return out
