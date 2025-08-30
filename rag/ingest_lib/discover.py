import re, time, urllib.parse
from dataclasses import dataclass
from typing import Iterable, List, Optional, Set
import requests
from bs4 import BeautifulSoup

@dataclass
class Link:
    url: str
    source_page: str
    year: Optional[int] = None
    title: Optional[str] = None

def _guess_year(text: str) -> Optional[int]:
    m = re.search(r"(20[0-9]{2})", text)
    if not m:
        return None
    y = int(m.group(1))
    return y if 2000 <= y <= 2099 else None

def _fetch_soup(url: str, headers: dict, timeout: int) -> Optional[BeautifulSoup]:
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
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
    user_agent: str,
) -> List[Link]:
    headers = {"User-Agent": user_agent}
    seen: Set[str] = set()
    out: List[Link] = []
    years_set = set(years) if years else None

    excl_res = [re.compile(p, re.I) for p in exclude_patterns]

    def excluded(txt: str) -> bool:
        return any(rx.search(txt) for rx in excl_res)

    for seed in seed_urls:
        soup = _fetch_soup(seed, headers, timeout)
        if not soup:
            continue

        seed_year = _guess_year(seed)

        for a in soup.find_all("a", href=True):
            href = urllib.parse.urljoin(seed, a["href"])
            text = f"{a.get_text(strip=True)} {href}"

            if excluded(text):
                continue

            # Case 1: direct PDF on listing
            if href.lower().endswith(".pdf"):
                candidate_url = href
            else:
                # Case 2: second hop to detail page, find a link that includes ".pdf"
                inner = _fetch_soup(href, headers, timeout)
                if not inner:
                    continue
                candidate_url = None
                for a2 in inner.find_all("a", href=True):
                    if ".pdf" in a2["href"].lower():
                        candidate_url = urllib.parse.urljoin(href, a2["href"])
                        break
                if not candidate_url:
                    continue  # no pdf found on detail page

            if candidate_url in seen:
                continue
            seen.add(candidate_url)

            yr = _guess_year(text) or _guess_year(candidate_url) or seed_year
            if years_set and yr and yr not in years_set:
                continue

            title = a.get_text(strip=True) or None
            out.append(Link(url=candidate_url, source_page=seed, year=yr, title=title))

        time.sleep(0.2)

    return out
