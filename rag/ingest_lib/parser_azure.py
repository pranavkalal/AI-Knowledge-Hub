# rag/ingest_lib/parser_azure.py
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

@dataclass
class ParsedDoc:
    text: str
    meta: Dict[str, Any] = field(default_factory=dict)
    tables: List[Dict[str, Any]] = field(default_factory=list)

def parse_pdf(pdf_path: str, extra_meta: Optional[Dict[str, Any]] = None) -> ParsedDoc:
    """
    Parse a PDF using Azure Document Intelligence (Layout model).
    """
    endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    if not endpoint or not key:
        raise ValueError("Missing Azure Document Intelligence credentials (AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT, AZURE_DOCUMENT_INTELLIGENCE_KEY)")

    client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    with open(pdf_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-layout", document=f)
        result = poller.result()

    # Extract text
    full_text = result.content

    # Extract tables
    tables = []
    for table in result.tables:
        t_data = {
            "row_count": table.row_count,
            "column_count": table.column_count,
            "cells": []
        }
        for cell in table.cells:
            t_data["cells"].append({
                "row_index": cell.row_index,
                "column_index": cell.column_index,
                "content": cell.content,
            })
        tables.append(t_data)

    # Metadata
    meta = extra_meta or {}
    meta["filename"] = os.path.basename(pdf_path)
    meta["page_count"] = len(result.pages)
    
    return ParsedDoc(text=full_text, meta=meta, tables=tables)
