# rag/ingest_lib/parse_docling.py
"""
Multi-modal PDF parsing using Docling (IBM).
Extracts text, images, tables, and bounding boxes for deep linking.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions

logger = logging.getLogger(__name__)


@dataclass
class ParsedElement:
    """Represents a parsed element from a PDF."""
    type: str  # "text", "table", "image"
    text: str
    page: int
    bbox: Optional[tuple[float, float, float, float]]  # (x, y, width, height)
    image_path: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class ParsedPDFMultiModal:
    """Container for multi-modal PDF parsing results."""
    elements: List[ParsedElement]
    full_text: str
    metadata: Dict


def parse_pdf_multimodal(
    pdf_path: str,
    output_dir: str = "data/assets",
    extract_images: bool = True,
    extract_tables: bool = True,
) -> ParsedPDFMultiModal:
    """
    Parse PDF with Docling to extract text, images, tables, and bounding boxes.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save extracted images
        extract_images: Whether to extract and save images
        extract_tables: Whether to extract tables as markdown
    
    Returns:
        ParsedPDFMultiModal with elements, full_text, and metadata
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    # Create output directory for images
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Configure Docling pipeline
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True  # Enable OCR for scanned PDFs
    pipeline_options.do_table_structure = extract_tables
    
    # Initialize converter
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    
    logger.info(f"Parsing PDF with Docling: {pdf_path}")
    
    try:
        # Convert PDF
        result = converter.convert(str(pdf_path))
        doc = result.document
        
        elements: List[ParsedElement] = []
        full_text_parts: List[str] = []
        
        # Iterate through document elements
        for item, level in doc.iterate_items():
            # Get page number and bbox if available
            page_num = None
            bbox = None
            
            if hasattr(item, 'prov') and item.prov:
                prov = item.prov[0]  # First provenance
                page_num = getattr(prov, 'page_no', None)
                if hasattr(prov, 'bbox'):
                    # Convert bbox to tuple (x, y, width, height)
                    bbox_obj = prov.bbox
                    bbox = (
                        bbox_obj.l,  # left (x)
                        bbox_obj.t,  # top (y)
                        bbox_obj.r - bbox_obj.l,  # width
                        bbox_obj.b - bbox_obj.t,  # height
                    )
            
            # Handle different element types
            if item.label == "text" or item.label == "paragraph":
                text = item.text.strip()
                if text:
                    elements.append(ParsedElement(
                        type="text",
                        text=text,
                        page=page_num or 1,
                        bbox=bbox,
                    ))
                    full_text_parts.append(text)
            
            elif item.label == "table" and extract_tables:
                # Export table to markdown
                try:
                    table_md = item.export_to_markdown()
                    if table_md:
                        elements.append(ParsedElement(
                            type="table",
                            text=table_md,
                            page=page_num or 1,
                            bbox=bbox,
                            metadata={"format": "markdown"}
                        ))
                        full_text_parts.append(table_md)
                except Exception as e:
                    logger.warning(f"Failed to export table: {e}")
            
            elif item.label == "picture" and extract_images:
                # Save image and create text description
                try:
                    if hasattr(item, 'image') and item.image:
                        # Generate unique image filename
                        image_filename = f"{pdf_path.stem}_p{page_num}_{item.self_ref}.png"
                        image_path = output_path / image_filename
                        
                        # Save image
                        item.image.save(str(image_path))
                        
                        # Create caption (you could use BLIP/CLIP here for auto-captioning)
                        caption = f"[Image on page {page_num}]"
                        
                        elements.append(ParsedElement(
                            type="image",
                            text=caption,
                            page=page_num or 1,
                            bbox=bbox,
                            image_path=str(image_path),
                            metadata={"filename": image_filename}
                        ))
                        full_text_parts.append(caption)
                except Exception as e:
                    logger.warning(f"Failed to save image: {e}")
        
        # Combine full text
        full_text = "\n\n".join(full_text_parts)
        
        # Extract metadata
        metadata = {
            "filename": pdf_path.name,
            "path": str(pdf_path),
            "num_pages": len(set(e.page for e in elements if e.page)),
            "num_elements": len(elements),
            "num_images": sum(1 for e in elements if e.type == "image"),
            "num_tables": sum(1 for e in elements if e.type == "table"),
        }
        
        logger.info(
            f"Parsed {pdf_path.name}: {metadata['num_elements']} elements "
            f"({metadata['num_images']} images, {metadata['num_tables']} tables)"
        )
        
        return ParsedPDFMultiModal(
            elements=elements,
            full_text=full_text,
            metadata=metadata,
        )
    
    except Exception as e:
        logger.error(f"Failed to parse PDF {pdf_path}: {e}")
        raise


def elements_to_records(
    parsed: ParsedPDFMultiModal,
    doc_id: str,
    extra_meta: Optional[Dict] = None,
) -> List[Dict]:
    """
    Convert parsed elements to records for chunking/embedding.
    
    Each element becomes a record with bbox and page metadata.
    """
    records = []
    extra_meta = extra_meta or {}
    
    for idx, element in enumerate(parsed.elements, start=1):
        record = {
            "id": f"{doc_id}_elem{idx:04d}",
            "doc_id": doc_id,
            "text": element.text,
            "page": element.page,
            "element_type": element.type,
        }
        
        # Add bbox if available
        if element.bbox:
            record["bbox"] = list(element.bbox)  # Convert tuple to list for JSON
        
        # Add image path if available
        if element.image_path:
            record["image_path"] = element.image_path
        
        # Add element metadata
        if element.metadata:
            record["element_metadata"] = element.metadata
        
        # Add extra metadata
        for key, value in extra_meta.items():
            if key not in record and value is not None:
                record[key] = value
        
        records.append(record)
    
    return records
