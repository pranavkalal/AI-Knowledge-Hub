#!/usr/bin/env python3
"""
A/B Test: Fixed-Size vs Semantic Chunking

Compares the two chunking strategies on sample documents and reports:
- Chunk count
- Average chunk size (tokens)
- Boundary preservation (% chunks ending with sentence/paragraph)
- Token distribution (std dev)
"""

import sys
from pathlib import Path
from typing import List, Dict
import statistics

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rag.segment.chunker import chunk_text, get_tokenizer
from rag.segment.semantic_chunker import chunk_text_semantic


def analyze_chunks(chunks: List[Dict], label: str) -> Dict:
    """Analyze chunk quality metrics."""
    if not chunks:
        return {"label": label, "count": 0}
    
    token_sizes = [c["token_end"] - c["token_start"] for c in chunks]
    texts = [c["text"] for c in chunks]
    
    # Check boundary preservation
    ends_with_sentence = sum(1 for t in texts if t.rstrip().endswith(('.', '!', '?')))
    ends_with_paragraph = sum(1 for t in texts if t.endswith('\n\n'))
    
    return {
        "label": label,
        "count": len(chunks),
        "avg_tokens": statistics.mean(token_sizes),
        "std_tokens": statistics.stdev(token_sizes) if len(token_sizes) > 1 else 0,
        "min_tokens": min(token_sizes),
        "max_tokens": max(token_sizes),
        "sentence_boundary_pct": (ends_with_sentence / len(chunks)) * 100,
        "paragraph_boundary_pct": (ends_with_paragraph / len(chunks)) * 100,
    }


def compare_chunking(text: str, max_tokens: int = 896, overlap: int = 128):
    """Compare fixed-size vs semantic chunking on a text sample."""
    tokenizer = get_tokenizer()
    
    # Fixed-size chunking
    fixed_chunks = list(chunk_text(text, max_tokens, overlap, tokenizer=tokenizer))
    fixed_stats = analyze_chunks(fixed_chunks, "Fixed-Size")
    
    # Semantic chunking
    semantic_chunks = list(chunk_text_semantic(text, max_tokens, overlap, tokenizer=tokenizer))
    semantic_stats = analyze_chunks(semantic_chunks, "Semantic")
    
    return fixed_stats, semantic_stats


def print_comparison(fixed: Dict, semantic: Dict):
    """Print side-by-side comparison."""
    print("\n" + "="*70)
    print(f"{'Metric':<30} {'Fixed-Size':<20} {'Semantic':<20}")
    print("="*70)
    
    metrics = [
        ("Chunk Count", "count", "d"),
        ("Avg Tokens", "avg_tokens", ".1f"),
        ("Std Dev Tokens", "std_tokens", ".1f"),
        ("Min Tokens", "min_tokens", "d"),
        ("Max Tokens", "max_tokens", "d"),
        ("Sentence Boundary %", "sentence_boundary_pct", ".1f"),
        ("Paragraph Boundary %", "paragraph_boundary_pct", ".1f"),
    ]
    
    for label, key, fmt in metrics:
        fixed_val = fixed.get(key, 0)
        semantic_val = semantic.get(key, 0)
        print(f"{label:<30} {fixed_val:<20{fmt}} {semantic_val:<20{fmt}}")
    
    print("="*70)
    
    # Highlight improvements
    if semantic["sentence_boundary_pct"] > fixed["sentence_boundary_pct"]:
        improvement = semantic["sentence_boundary_pct"] - fixed["sentence_boundary_pct"]
        print(f"✅ Semantic chunking preserves {improvement:.1f}% more sentence boundaries")
    
    if semantic["std_tokens"] < fixed["std_tokens"]:
        print(f"✅ Semantic chunking has more consistent chunk sizes (lower std dev)")


def main():
    """Run A/B test on sample text."""
    # Sample text (you can replace with actual PDF text)
    sample_text = """
# Cotton Yield Optimization in Australia

## Introduction

Australian cotton production has seen significant improvements over the past decade. This report examines the key factors contributing to yield optimization.

## Water Management

Efficient water use is critical for sustainable cotton farming. Recent studies show that drip irrigation can reduce water consumption by up to 30% while maintaining yield levels.

### Irrigation Techniques

1. Drip irrigation systems
2. Furrow irrigation optimization
3. Soil moisture monitoring

The implementation of precision agriculture technologies has enabled farmers to make data-driven decisions about irrigation timing and volume.

## Pest Management

Integrated pest management (IPM) strategies have proven effective in reducing chemical inputs while maintaining crop health. Key components include:

- Regular field scouting
- Biological control agents
- Targeted pesticide application

## Conclusion

The combination of advanced water management and IPM practices has led to a 15% increase in average yields across the cotton belt. Future research will focus on climate adaptation strategies.
    """.strip()
    
    print("Running A/B Test: Fixed-Size vs Semantic Chunking")
    print(f"Sample text length: {len(sample_text)} characters")
    
    fixed_stats, semantic_stats = compare_chunking(sample_text)
    print_comparison(fixed_stats, semantic_stats)
    
    print("\n📊 Recommendation:")
    if semantic_stats["sentence_boundary_pct"] > 70:
        print("✅ Semantic chunking shows strong boundary preservation.")
        print("   Consider adopting for production use.")
    else:
        print("⚠️  Further tuning may be needed for optimal results.")


if __name__ == "__main__":
    main()
