#!/usr/bin/env python3
"""
CRDC Report Scraper - Download Final Reports from InsideCotton

Usage:
    # Preview what would be downloaded (dry run)
    python scripts/scrape_crdc.py --years 2022 2023 2024 --dry-run
    
    # Download to data/raw
    python scripts/scrape_crdc.py --years 2022 2023 2024 --output data/raw
    
    # Limit number of reports
    python scripts/scrape_crdc.py --years 2024 --limit 5 --output data/raw
"""

import argparse
import csv
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag.ingest_lib.discover import collect_reports, ReportMetadata
from rag.ingest_lib.download import download_reports


def save_metadata_csv(reports: list, output_path: str):
    """Save report metadata to CSV file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'title', 'year', 'project_code', 'author', 'publisher', 
            'date_issued', 'abstract', 'category', 'subject', 
            'pdf_url', 'source_page', 'filename'
        ])
        writer.writeheader()
        
        for report in reports:
            writer.writerow({
                'title': report.title,
                'year': report.year,
                'project_code': report.project_code or '',
                'author': report.author or '',
                'publisher': report.publisher or '',
                'date_issued': report.date_issued or '',
                'abstract': report.abstract or '',
                'category': report.category or '',
                'subject': report.subject or '',
                'pdf_url': report.pdf_url,
                'source_page': report.source_page,
                'filename': report.get_filename()
            })
    
    print(f"[info] Saved metadata to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape CRDC Final Reports from InsideCotton"
    )
    parser.add_argument(
        '--years', 
        type=int, 
        nargs='+', 
        default=[2022, 2023, 2024],
        help='Years to scrape (default: 2022 2023 2024)'
    )
    parser.add_argument(
        '--output', 
        type=str, 
        default='data/raw',
        help='Output directory for PDFs (default: data/raw)'
    )
    parser.add_argument(
        '--limit', 
        type=int, 
        default=None,
        help='Limit number of reports to download'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Preview what would be downloaded without downloading'
    )
    parser.add_argument(
        '--metadata-csv',
        type=str,
        default='data/metadata/scraped_reports.csv',
        help='Path to save metadata CSV'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("CRDC Report Scraper")
    print("=" * 60)
    print(f"Years: {args.years}")
    print(f"Output: {args.output}")
    print(f"Limit: {args.limit or 'None'}")
    print(f"Dry run: {args.dry_run}")
    print("=" * 60)
    
    # Step 1: Discover reports
    print("\n[Step 1] Discovering reports...")
    reports = collect_reports(
        years=args.years,
        limit=args.limit
    )
    
    print(f"\n[info] Found {len(reports)} reports")
    
    if not reports:
        print("[warn] No reports found!")
        return
    
    # Display what we found
    print("\n[info] Reports found:")
    print("-" * 60)
    for i, report in enumerate(reports, 1):
        print(f"{i:3d}. [{report.year}] {report.title[:50]}...")
        print(f"     -> {report.get_filename()}")
    print("-" * 60)
    
    # Save metadata CSV
    save_metadata_csv(reports, args.metadata_csv)
    
    # Step 2: Download (if not dry run)
    if args.dry_run:
        print("\n[dry-run] Skipping download. Run without --dry-run to download.")
    else:
        print(f"\n[Step 2] Downloading {len(reports)} PDFs to {args.output}...")
        downloaded = download_reports(
            reports=reports,
            download_dir=args.output
        )
        print(f"\n[done] Downloaded {len(downloaded)} / {len(reports)} files")
    
    print("\n[complete] Scraping finished!")


if __name__ == "__main__":
    main()
