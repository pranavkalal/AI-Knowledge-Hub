# rag/ingest_lib/parser_azure_read.py
"""
Azure Document Intelligence Read Parser.

Uses the prebuilt-read model for cost-effective document parsing.
Provides page-level text extraction with markdown format.

Cost: $1.50 per 1,000 pages (same as layout, but simpler API)
"""
import os
from typing import Dict, Any, List
from dataclasses import dataclass, field, asdict
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential


@dataclass
class PageObject:
    """Page-level document structure."""
    page_number: int
    text: str
    width: float
    height: float


class AzureReadParser:
    """
    Azure Document Intelligence Read parser.
    
    Provides clean markdown text extraction without bbox complexity.
    Optimized for LLM ingestion and RAG pipelines.
    """
    
    def __init__(self):
        self.endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        if not self.endpoint or not self.key:
            raise ValueError("Missing Azure Document Intelligence credentials")

        # Initialize with preview API version for Markdown support
        self.client = DocumentIntelligenceClient(
            endpoint=self.endpoint, 
            credential=AzureKeyCredential(self.key),
            api_version="2024-11-30"  # Latest stable API
        )

    def parse(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Parse PDF and return list of page objects.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of page dicts with: page_number, text, width, height
        """
        with open(pdf_path, "rb") as f:
            # Use prebuilt-read for cost-effective extraction
            # Markdown output format for LLM-ready text
            poller = self.client.begin_analyze_document(
                "prebuilt-read", 
                body=f,
                content_type="application/octet-stream",
                output_content_format="markdown"
            )
            
            result = poller.result()

        pages_output = []
        
        # Result content is the full markdown text
        full_content = result.content
        
        for page in result.pages:
            # Extract Markdown text for this page using spans
            page_text_parts = []
            if page.spans:
                for span in page.spans:
                    if span.offset + span.length <= len(full_content):
                        page_text_parts.append(
                            full_content[span.offset : span.offset + span.length]
                        )
            
            page_text = "".join(page_text_parts)
            
            # Construct Page Object (no bbox - simplified for page-level tracking)
            page_obj = PageObject(
                page_number=page.page_number, 
                text=page_text,
                width=page.width,
                height=page.height
            )
            
            pages_output.append(asdict(page_obj))
            
        return pages_output
