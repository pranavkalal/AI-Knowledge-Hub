# rag/ingest_lib/discover.py
"""
CRDC Report Scraper - Discovers and extracts metadata from insidecotton.com

Strategy:
1. Crawl search pages with pagination
2. Extract report detail URLs
3. Visit /node/{id}/full pages for structured metadata
4. Return ReportMetadata with title, year, project_code, pdf_url
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import List, Optional
from dataclasses import dataclass
from urllib.parse import urljoin, unquote
import time


@dataclass
class ReportMetadata:
    """Structured metadata for a CRDC report."""
    title: str
    pdf_url: str
    source_page: str
    year: Optional[int] = None
    project_code: Optional[str] = None  # Alternative Title like "CRDC2012"
    author: Optional[str] = None
    publisher: Optional[str] = None
    date_issued: Optional[str] = None
    abstract: Optional[str] = None
    copyright: Optional[str] = None
    category: Optional[str] = None
    subject: Optional[str] = None
    
    def get_filename(self) -> str:
        """Generate a clean filename from metadata."""
        if self.title:
            # Use the title, sanitized
            safe_title = sanitize_filename(self.title)
            return f"{safe_title}.pdf"
        elif self.year and self.project_code:
            return f"{self.year}_{self.project_code}_Report.pdf"
        else:
            # Fallback: extract from PDF URL
            return sanitize_filename(unquote(self.pdf_url.split("/")[-1]))


def sanitize_filename(name: str) -> str:
    """Convert string to a safe filename."""
    # Remove/replace unsafe characters
    safe = re.sub(r'[<>:"/\\|?*]', '', name)
    safe = re.sub(r'\s+', '_', safe.strip())
    # Limit length
    if len(safe) > 150:
        safe = safe[:150]
    return safe


class CRDCScraper:
    """Scraper for CRDC Final Reports from insidecotton.com"""
    
    BASE_URL = "https://www.insidecotton.com"
    
    # Year category IDs from the website
    YEAR_CATEGORIES = {
        2024: "2024+Final+Reports+%28266423%29",
        2023: "2023+Final+Reports+%28266358%29",
        2022: "2022+Final+Reports+%28249069%29",
        2021: "2021+Final+Reports+%28249068%29",
        2020: "2020+Final+Reports+%28249067%29",
    }
    
    def __init__(self, timeout: int = 30, user_agent: str = "CRDC-Knowledge-Hub/0.1"):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
    
    def scrape_years(self, years: List[int], limit: Optional[int] = None) -> List[ReportMetadata]:
        """Scrape reports for specified years."""
        all_reports = []
        
        for year in years:
            if year not in self.YEAR_CATEGORIES:
                print(f"[warn] No category ID for year {year}, skipping")
                continue
            
            print(f"[info] Scraping {year} Final Reports...")
            reports = self._scrape_year(year, limit=limit)
            all_reports.extend(reports)
            
            if limit and len(all_reports) >= limit:
                all_reports = all_reports[:limit]
                break
        
        return all_reports
    
    def _scrape_year(self, year: int, limit: Optional[int] = None) -> List[ReportMetadata]:
        """Scrape all reports for a single year."""
        category = self.YEAR_CATEGORIES[year]
        reports = []
        seen_urls = set()
        page = 0
        max_pages = 10  # Safety limit
        consecutive_empty = 0
        
        while page < max_pages:
            url = f"{self.BASE_URL}/search?search_api_fulltext=&category={category}&page={page}"
            print(f"[debug] Fetching search page: {url}")
            
            try:
                resp = self.session.get(url, timeout=self.timeout)
                resp.raise_for_status()
            except Exception as e:
                print(f"[error] Failed to fetch {url}: {e}")
                break
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Find report links on this page
            report_links = self._extract_report_links(soup, year)
            
            # Filter out already seen URLs
            new_links = [link for link in report_links if link not in seen_urls]
            
            if not new_links:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    print(f"[debug] No new reports found for 2 pages, stopping")
                    break
                page += 1
                continue
            
            consecutive_empty = 0
            
            for link in new_links:
                if limit and len(reports) >= limit:
                    return reports
                
                seen_urls.add(link)
                
                # Visit Full Details page to get metadata
                metadata = self._scrape_detail_page(link, year)
                if metadata:
                    reports.append(metadata)
                
                # Be polite - delay between requests
                time.sleep(0.5)
            
            page += 1
            time.sleep(1)  # Delay between pages
        
        return reports
    
    def _extract_report_links(self, soup: BeautifulSoup, year: int) -> List[str]:
        """Extract links to report detail pages from search results."""
        links = []
        
        # Exclude common non-report pages
        exclude_patterns = [
            "/search", "/categories", "/user", "/node/", "/sites/", 
            "#", "javascript:", "/rss", "/authors", "/subjects", 
            "/contact-us", "/about", "/privacy", "/terms", "/login",
            "/register", "/help", "/faq"
        ]
        
        # Find all links that look like report pages
        for a in soup.find_all("a", href=True):
            href = a["href"]
            
            # Skip non-report links
            if any(skip in href.lower() for skip in exclude_patterns):
                continue
            
            # Skip external links
            if href.startswith("http") and self.BASE_URL not in href:
                continue
            
            # Must be a content page URL (slug format with at least one hyphen)
            if re.match(r'^/[a-z0-9]+-[a-z0-9-]+$', href):
                full_url = urljoin(self.BASE_URL, href)
                if full_url not in links:
                    links.append(full_url)
        
        print(f"[debug] Found {len(links)} potential report links")
        return links
    
    def _scrape_detail_page(self, url: str, year: int) -> Optional[ReportMetadata]:
        """Scrape metadata from a report page and its Full Details page."""
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as e:
            print(f"[error] Failed to fetch detail page {url}: {e}")
            return None
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Extract title from the ORIGINAL detail page
        title = None
        h1 = soup.find("h1")
        if h1:
            h1_text = h1.get_text(strip=True)
            if h1_text and h1_text.lower() != "inside cotton":
                title = h1_text
        
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title:
                title = og_title.get("content", "").strip()
        
        if not title:
            title_tag = soup.find("title")
            if title_tag:
                raw_title = title_tag.get_text(strip=True)
                if "|" in raw_title:
                    title = raw_title.split("|")[0].strip()
                elif " - Inside Cotton" in raw_title:
                    title = raw_title.replace(" - Inside Cotton", "").strip()
        
        if not title or title.lower() == "inside cotton":
            slug = url.rstrip("/").split("/")[-1]
            if slug and slug != "full":
                title = slug.replace("-", " ").title()
        
        # Find the /node/{id}/full link
        full_details_link = None
        for a in soup.find_all("a", href=True):
            if "/node/" in a["href"] and "/full" in a["href"]:
                full_details_link = urljoin(self.BASE_URL, a["href"])
                break
        
        # Initialize metadata fields
        metadata = {
            "project_code": None,
            "author": None,
            "publisher": None,
            "date_issued": None,
            "abstract": None,
            "copyright": None,
            "category": None,
            "subject": None,
        }
        pdf_url = None
        
        # Visit /full page for rich metadata
        if full_details_link:
            try:
                resp_full = self.session.get(full_details_link, timeout=self.timeout)
                resp_full.raise_for_status()
                soup_full = BeautifulSoup(resp_full.text, "html.parser")
                
                # Extract PDF link
                for a in soup_full.find_all("a", href=True):
                    href = a["href"]
                    if "/sites/default/files/" in href and ".pdf" in href.lower():
                        pdf_url = urljoin(self.BASE_URL, href)
                        break
                
                # Parse metadata from the Full Details page
                # The metadata is in label-value pairs in the page content
                page_text = soup_full.get_text()
                
                # Field mapping: label text -> dict key
                field_map = {
                    "Alternative Title": "project_code",
                    "Author": "author",
                    "Publisher": "publisher",
                    "Date Issued": "date_issued",
                    "Abstract": "abstract",
                    "Copyright": "copyright",
                    "Categories": "category",
                    "Subject": "subject",
                }
                
                # Try to extract using field-specific elements or text parsing
                for label, key in field_map.items():
                    # Look for divs with field classes
                    field_elem = soup_full.find("div", class_=lambda c: c and f"field--name-field-{key.replace('_', '-')}" in c.lower() if c else False)
                    if field_elem:
                        metadata[key] = field_elem.get_text(strip=True)
                    else:
                        # Fall back to text parsing
                        value = self._extract_field_value(page_text, label)
                        if value:
                            metadata[key] = value
                
            except Exception as e:
                print(f"[warn] Failed to fetch full details page: {e}")
        
        # If no PDF from /full, try the original page
        if not pdf_url:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/sites/default/files/" in href and ".pdf" in href.lower():
                    pdf_url = urljoin(self.BASE_URL, href)
                    break
        
        if not pdf_url:
            print(f"[warn] No PDF found on {url}")
            return None
        
        # Use Alternative Title as project_code if it looks like a code
        project_code = metadata.get("project_code")
        if project_code:
            # Validate it looks like a project code (e.g., CRDC2012, CSD2201)
            if not re.match(r'^[A-Z]{2,10}\d{2,6}$', project_code):
                # Try to extract code from it
                match = re.search(r'([A-Z]{2,5}\d{4})', project_code)
                if match:
                    project_code = match.group(1)
        
        # If no project code from Alt Title, try extracting from title
        if not project_code and title:
            match = re.search(r'\b([A-Z]{2,5}\d{4})\b', title)
            if match:
                project_code = match.group(1)
        
        print(f"[found] {title[:50]}..." if title and len(title) > 50 else f"[found] {title}")
        
        return ReportMetadata(
            title=title or "Unknown Report",
            pdf_url=pdf_url,
            source_page=url,
            year=year,
            project_code=project_code,
            author=metadata.get("author"),
            publisher=metadata.get("publisher"),
            date_issued=metadata.get("date_issued"),
            abstract=metadata.get("abstract"),
            copyright=metadata.get("copyright"),
            category=metadata.get("category"),
            subject=metadata.get("subject"),
        )
    
    def _extract_field_value(self, text: str, label: str) -> Optional[str]:
        """Extract field value from page text given a label."""
        # Split text into lines and find label
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        for i, line in enumerate(lines):
            if line == label and i + 1 < len(lines):
                # The next non-empty line should be the value
                value = lines[i + 1]
                # Skip if it looks like another label
                if value in ["Alternative Title", "Author", "Publisher", "Date Issued", 
                            "Abstract", "Copyright", "Categories", "Subject", 
                            "Files in this item", "Hide Full Details"]:
                    continue
                return value
        return None


def collect_reports(years: List[int], limit: Optional[int] = None, 
                    timeout: int = 30, user_agent: str = "CRDC-Knowledge-Hub/0.1") -> List[ReportMetadata]:
    """
    Main entry point: Collect CRDC Final Reports for specified years.
    
    Args:
        years: List of years to scrape (e.g., [2022, 2023, 2024])
        limit: Maximum number of reports to collect (None = no limit)
        timeout: Request timeout in seconds
        user_agent: User agent string for requests
    
    Returns:
        List of ReportMetadata objects
    """
    scraper = CRDCScraper(timeout=timeout, user_agent=user_agent)
    return scraper.scrape_years(years, limit=limit)


# Legacy function for backwards compatibility
def collect_pdf_links(seed_urls: List[str], include_patterns: List[str], 
                      exclude_patterns: List[str], **kwargs) -> List[ReportMetadata]:
    """Legacy interface - use collect_reports() instead."""
    print("[warn] collect_pdf_links is deprecated, use collect_reports()")
    # Try to extract years from seed URLs
    years = []
    for url in seed_urls:
        for year in [2020, 2021, 2022, 2023, 2024]:
            if str(year) in url:
                years.append(year)
                break
    
    if not years:
        years = [2022, 2023, 2024]  # Default
    
    return collect_reports(years=list(set(years)), limit=kwargs.get("limit"))
