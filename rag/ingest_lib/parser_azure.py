# rag/ingest_lib/parser_azure.py
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

@dataclass
class PageObject:
    page_number: int
    text: str
    width: float
    height: float
    bboxes: List[Dict[str, Any]] = field(default_factory=list)

class AzureParser:
    def __init__(self):
        self.endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        if not self.endpoint or not self.key:
            raise ValueError("Missing Azure Document Intelligence credentials")

        # Initialize with specific preview API version for Markdown support
        self.client = DocumentIntelligenceClient(
            endpoint=self.endpoint, 
            credential=AzureKeyCredential(self.key),
            api_version="2023-10-31-preview"
        )

    def parse(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Parse PDF and return list of page objects using Markdown format.
        """
        with open(pdf_path, "rb") as f:
            # Strict requirement: output_content_format="markdown"
            # We do NOT use fallback. If this fails, it should error out.
            poller = self.client.begin_analyze_document(
                "prebuilt-layout", 
                body=f,
                content_type="application/octet-stream",
                output_content_format="markdown"
            )
            
            result = poller.result()

        pages_output = []
        
        # Result content is the full markdown text
        full_content = result.content
        
        for page in result.pages:
            # 1. Extract Markdown text for this page using spans
            page_text_parts = []
            if page.spans:
                for span in page.spans:
                    # span has offset and length
                    if span.offset + span.length <= len(full_content):
                        page_text_parts.append(full_content[span.offset : span.offset + span.length])
            
            page_text = "".join(page_text_parts)
            
            # 2. Extract lines and bboxes (polygons)
            lines_data = []
            if page.lines:
                for line in page.lines:
                    # line.polygon is a list of coordinates
                    lines_data.append({
                        "text": line.content,
                        "polygon": line.polygon
                    })

            # 3. Construct Page Object
            # Ensure page_number is 1-indexed from Azure response
            page_obj = PageObject(
                page_number=page.page_number, 
                text=page_text,
                width=page.width,
                height=page.height,
                bboxes=lines_data
            )
            
            pages_output.append(asdict(page_obj))
            
        return pages_output
