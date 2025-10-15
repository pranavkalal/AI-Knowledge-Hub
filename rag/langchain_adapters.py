"""
Backwards-compatibility module for legacy imports.

PortsRetriever and RerankDecoratorRetriever now live under rag.retrievers.
Importing from rag.langchain_adapters will continue to work, but new code should
depend on rag.retrievers directly.
"""

from __future__ import annotations

from warnings import warn

from rag.retrievers import PortsRetriever, RerankDecoratorRetriever

__all__ = ["PortsRetriever", "RerankDecoratorRetriever"]

warn(
    "rag.langchain_adapters is deprecated; import from rag.retrievers instead.",
    DeprecationWarning,
    stacklevel=2,
)
