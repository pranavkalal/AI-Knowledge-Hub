"""
Simple wrapper to use OpenAI's tiktoken for chunking.
Alternative to transformers-based tokenizer.
"""
import logging
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_tiktoken_encoder() -> Any:
    """Get OpenAI's tiktoken encoder (cl100k_base)."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        logger.info("Loaded OpenAI tiktoken encoder: cl100k_base")
        return enc
    except ImportError:
        logger.error("tiktoken not installed. Run: pip install tiktoken")
        raise

# Make it compatible with HF tokenizer interface
class TiktokenWrapper:
    """Wrapper to make tiktoken compatible with transformers tokenizer interface."""
    def __init__(self):
        self.encoder = get_tiktoken_encoder()
    
    def encode(self, text: str, add_special_tokens=False):
        return self.encoder.encode(text)
    
    def decode(self, tokens):
        return self.encoder.decode(tokens)
    
    @property
    def model_max_length(self):
        return 10**6  # Arbitrary large number
