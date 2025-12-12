import sys
import logging
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def diagnose_pdf(pdf_path):
    print(f"\n🔍 Diagnosing: {pdf_path}")
    
    # Configure pipeline
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    
    try:
        result = converter.convert(str(pdf_path))
        doc = result.document
        
        print("\n📊 Element Analysis:")
        print("-" * 50)
        
        label_counts = {}
        
        for item, level in doc.iterate_items():
            label = item.label
            label_counts[label] = label_counts.get(label, 0) + 1
            
            # Print details for potential image candidates
            if label.lower() in ['picture', 'figure', 'image', 'drawing', 'photo', 'chart', 'graphic']:
                print(f"Found candidate: '{label}'")
                print(f"  - Has image data? {hasattr(item, 'image') and item.image is not None}")
                if hasattr(item, 'image') and item.image:
                    print(f"  - Image size: {item.image.size}")
        
        print("\n📈 Label Summary:")
        for label, count in sorted(label_counts.items()):
            print(f"  - {label}: {count}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_images.py <path_to_pdf>")
        sys.exit(1)
    
    diagnose_pdf(sys.argv[1])
