# rag/ingest_lib/discover.py
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class Link:
    url: str
    source_page: str
    title: Optional[str] = None
    year: Optional[int] = None

def collect_pdf_links(seed_urls: List[str], include_patterns: List[str], exclude_patterns: List[str], years: Optional[List[int]] = None, timeout: int = 20, user_agent: str = "CRDC-Ingest") -> List[Link]:
    links = []
    headers = {"User-Agent": user_agent}
    
    for url in seed_urls:
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            print(f"[debug] crawling {url}, status={resp.status_code}, len={len(resp.text)}")
            
            links_found = soup.find_all("a", href=True)
            print(f"[debug] found {len(links_found)} links on page")
            
            for a in links_found:
                href = a["href"]
                if not href.startswith("http"):
                    href = requests.compat.urljoin(url, href)
                
                # Check if it's a direct PDF
                if any(re.search(p, href) for p in include_patterns):
                    print(f"[debug] found direct PDF {href}")
                    links.append(Link(url=href, source_page=url, title=a.get_text(strip=True)))
                    continue

                # If not PDF, and not excluded, treat as detail page
                if any(re.search(p, href) for p in exclude_patterns):
                    print(f"[debug] rejected {href} (excluded)")
                    continue
                
                # Visit detail page
                print(f"[debug] visiting detail page {href}")
                try:
                    resp_detail = requests.get(href, headers=headers, timeout=timeout)
                    if resp_detail.status_code != 200:
                        continue
                    soup_detail = BeautifulSoup(resp_detail.text, "html.parser")
                    
                    # Find PDFs on detail page
                    for a_detail in soup_detail.find_all("a", href=True):
                        href_detail = a_detail["href"]
                        if not href_detail.startswith("http"):
                            href_detail = requests.compat.urljoin(href, href_detail)
                            
                        if any(re.search(p, href_detail) for p in include_patterns):
                             # Check exclusion on the PDF link itself
                            if any(re.search(p, href_detail) for p in exclude_patterns):
                                continue
                                
                            print(f"[debug] found PDF on detail page: {href_detail}")
                            # Use detail page title if PDF link text is generic
                            title = a_detail.get_text(strip=True)
                            if len(title) < 5 or "download" in title.lower():
                                title = soup_detail.title.string if soup_detail.title else ""
                            
                            links.append(Link(url=href_detail, source_page=href, title=title))
                            # Stop after finding one PDF per detail page? Or get all? 
                            # Let's get all but maybe limit?
                            
                except Exception as e:
                    print(f"[warn] failed to crawl detail {href}: {e}")
                
        except Exception as e:
            print(f"[warn] failed to crawl {url}: {e}")
            
    return links
