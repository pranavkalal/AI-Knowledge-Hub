# rag/ingest_lib/chunk_bbox_mapper.py
"""
Utility to map chunk text to specific line bounding boxes.
This enables precise deep linking by associating chunks with only their relevant bboxes.
"""

from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def simplify_polygon(polygon: List[float]) -> List[float]:
    """
    Convert Azure polygon [x1, y1, x2, y2, x3, y3, x4, y4] to [x, y, width, height].
    Azure returns coordinates in inches; we convert to points (72 DPI).
    """
    if not polygon or len(polygon) < 4:
        return []
    
    xs = polygon[0::2]  # x1, x2, x3, x4
    ys = polygon[1::2]  # y1, y2, y3, y4
    
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    
    # Convert from inches to points (72 DPI)
    return [
        min_x * 72,
        min_y * 72,
        (max_x - min_x) * 72,
        (max_y - min_y) * 72
    ]


def find_matching_bboxes(
    chunk_text: str,
    page_bboxes: List[Dict],
    min_match_ratio: float = 0.3
) -> List[Dict]:
    """
    Find bboxes containing lines that appear in the chunk.
    Returns only relevant bboxes with simplified polygon format.
    
    Args:
        chunk_text: The text content of the chunk
        page_bboxes: List of {text, polygon} from Azure parser
        min_match_ratio: Minimum ratio of matching lines to include
        
    Returns:
        List of matching bboxes with simplified [x, y, w, h] format
    """
    if not chunk_text or not page_bboxes:
        return []
    
    chunk_lower = chunk_text.lower().strip()
    chunk_words = set(chunk_lower.split())
    
    matching = []
    
    for bbox_item in page_bboxes:
        line_text = bbox_item.get("text", "").lower().strip()
        if not line_text:
            continue
            
        # Check if this line appears in the chunk
        # Use word overlap for fuzzy matching
        line_words = set(line_text.split())
        if not line_words:
            continue
            
        # Calculate word overlap
        overlap = len(line_words & chunk_words)
        overlap_ratio = overlap / len(line_words) if line_words else 0
        
        # Also check for substring containment
        is_substring = line_text in chunk_lower or any(
            word in chunk_lower for word in line_words if len(word) > 3
        )
        
        if overlap_ratio >= min_match_ratio or is_substring:
            # Simplify the polygon to [x, y, w, h]
            polygon = bbox_item.get("polygon", [])
            simplified = simplify_polygon(polygon)
            
            if simplified:
                matching.append({
                    "text": bbox_item.get("text", ""),
                    "bbox": simplified
                })
    
    # If no matches found, return first few lines as fallback
    if not matching and page_bboxes:
        logger.debug("No bbox matches found, using first 3 lines as fallback")
        for bbox_item in page_bboxes[:3]:
            polygon = bbox_item.get("polygon", [])
            simplified = simplify_polygon(polygon)
            if simplified:
                matching.append({
                    "text": bbox_item.get("text", ""),
                    "bbox": simplified
                })
    
    return matching


def calculate_union_bbox(bboxes: List[Dict]) -> Optional[List[float]]:
    """
    Calculate the union bounding box from a list of simplified bboxes.
    Returns [x, y, width, height] that encompasses all input boxes.
    """
    if not bboxes:
        return None
    
    all_x1, all_y1, all_x2, all_y2 = [], [], [], []
    
    for item in bboxes:
        bbox = item.get("bbox", [])
        if len(bbox) >= 4:
            x, y, w, h = bbox
            all_x1.append(x)
            all_y1.append(y)
            all_x2.append(x + w)
            all_y2.append(y + h)
    
    if not all_x1:
        return None
    
    min_x = min(all_x1)
    min_y = min(all_y1)
    max_x = max(all_x2)
    max_y = max(all_y2)
    
    return [min_x, min_y, max_x - min_x, max_y - min_y]


def simplify_page_bboxes(page_bboxes: List[Dict]) -> List[Dict]:
    """
    Convert all page bboxes to simplified format for storage.
    Reduces storage size by ~60%.
    """
    simplified = []
    for bbox_item in page_bboxes:
        polygon = bbox_item.get("polygon", [])
        simple_bbox = simplify_polygon(polygon)
        if simple_bbox:
            simplified.append({
                "text": bbox_item.get("text", ""),
                "bbox": simple_bbox
            })
    return simplified
