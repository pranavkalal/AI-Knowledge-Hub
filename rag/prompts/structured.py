"""
Structured prompt helpers for the LangChain orchestration.

Centralises prompt templates, schema definitions, and helper utilities that
convert retrieval outputs into chat model inputs.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, ValidationError

SYSTEM_PROMPT = (
    "You are an expert research assistant for the Cotton Research and Development Corporation (CRDC). "
    "Your goal is to provide comprehensive, accurate answers based ONLY on the provided source documents. "
    "If the sources do not contain the answer, state that clearly. Do not hallucinate."
)

PROMPT_USER_INSTRUCTIONS = (
    "Synthesize the information from the provided source passages to answer the user's question. "
    "Structure your answer logically (e.g., use paragraphs for explanations, bullet points for lists). "
    "Every factual claim must be supported by an inline citation like [S1] referencing the source IDs."
)

STRUCTURED_FORMAT_INSTRUCTIONS = (
    "Return the answer in clear, well-structured Markdown.\n"
    "- Use headings (###) to organize complex topics.\n"
    "- Use bullet points for lists or key takeaways.\n"
    "- Ensure every factual claim is supported by an inline citation like [S1].\n"
    "- Do not use a fixed 'Summary/Key Points/Conclusion' structure unless it fits the question. Adapt your structure to best answer the query.\n"
    "Do not use JSON. Write natural text."
)

USER_PROMPT_TEMPLATE = (
    "Question:\n{question}\n\n"
    "Source Passages:\n{sources}\n\n"
    "Write the answer now. Follow the Rules and include inline [S#] citations."
)

CHAT_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            "{instructions}\n\nQuestion:\n{question}\n\nSource Passages:\n{sources_block}\n\n{format_instructions}",
        ),
    ]
)


def _normalize_page(value: Any) -> Optional[int]:
    if isinstance(value, list) and value:
        value = value[0]
    if value in (None, "", []):
        return None
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return None


class StructuredAnswer(BaseModel):
    summary: str = Field(..., description="3-5 sentence synthesis with inline citations.")
    key_points: List[str] = Field(
        ..., description="Bullet sentences with inline citations.", min_items=1
    )
    conclusion: str = Field(..., description="Closing sentence(s) with citations.")
    cited_sources: List[str] = Field(default_factory=list, description="Unique citation IDs.")

    class Config:
        arbitrary_types_allowed = True
        anystr_strip_whitespace = True


def prepare_prompt_state(data: Dict[str, Any]) -> Dict[str, Any]:
    question = str(data.get("question", "") or "").strip()
    docs: List[Document] = data.get("docs", [])
    temperature = float(data.get("temperature", 0.2))
    max_tokens = int(data.get("max_tokens", 600))
    k_raw = data.get("k")
    try:
        requested_k = int(k_raw) if k_raw is not None else len(docs) or 0
    except (TypeError, ValueError):
        requested_k = len(docs) or 0

    lines: List[str] = []
    citations: List[Dict[str, Any]] = []

    for idx, doc in enumerate(docs, start=1):
        sid = f"S{idx}"
        meta = doc.metadata or {}
        text = doc.page_content or ""
        max_snippet = meta.get("max_snippet_chars")
        try:
            max_snippet = int(max_snippet) if max_snippet is not None else None
        except (TypeError, ValueError):
            max_snippet = None
        if max_snippet is None or max_snippet <= 0:
            max_snippet = 1400
        snippet = text
        if len(snippet) > max_snippet:
            snippet = snippet[:max_snippet] + "…"

        title = meta.get("title") or meta.get("doc_id") or "Source"
        doc_id = meta.get("doc_id") or ""
        year = meta.get("year")
        page = _normalize_page(meta.get("page"))

        parts: List[str] = []
        if doc_id:
            parts.append(doc_id)
        if year not in (None, ""):
            parts.append(str(year))
        if page not in (None, ""):
            parts.append(f"p.{page}")
        suffix = f" ({', '.join(parts)})" if parts else ""

        lines.append(f"[{sid}] {title}{suffix}: {snippet}")

        citations.append(
            {
                "sid": sid,
                "doc_id": doc_id,
                "title": meta.get("title"),
                "year": year,
                "page": page,
                "score": meta.get("score"),
                "faiss_score": meta.get("faiss_score"),
                "rerank_score": meta.get("rerank_score"),
                "chunk_indices": meta.get("chunk_indices"),
                "cosine": meta.get("faiss_score"),
                "snippet": snippet,
                "url": meta.get("url"),
                "rel_path": meta.get("rel_path") or meta.get("filename"),
                "source_url": meta.get("source_url"),
                "filename": meta.get("filename"),
            }
        )

    sources_block = "\n".join(lines) if lines else "(no sources)"

    return {
        "question": question,
        "sources_block": sources_block,
        "citations": citations,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "instructions": PROMPT_USER_INSTRUCTIONS,
        "format_instructions": STRUCTURED_FORMAT_INSTRUCTIONS,
        "k": max(requested_k, len(citations)),
    }


def build_prompt_messages(state: Dict[str, Any]):
    format_instructions = state.get("format_instructions", STRUCTURED_FORMAT_INSTRUCTIONS)
    citation_ids = [str(c.get("sid")) for c in state.get("citations", []) if c.get("sid")]
    if citation_ids:
        format_instructions = (
            f"{format_instructions}\nAvailable citation IDs: {', '.join(citation_ids)}"
        )
    prompt_value = CHAT_PROMPT.invoke(
        {
            "instructions": state.get("instructions", PROMPT_USER_INSTRUCTIONS),
            "question": state.get("question", ""),
            "sources_block": state.get("sources_block", ""),
            "format_instructions": format_instructions,
        }
    )
    return prompt_value.to_messages()


def message_to_text(response: Any) -> str:
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
            else:
                parts.append(str(getattr(item, "text", item)))
        return "".join(parts)
    if hasattr(response, "dict"):
        try:
            return json.dumps(response.dict())
        except Exception:
            pass
    return str(response)


def extract_usage(response: Any) -> Dict[str, Any]:
    metadata = getattr(response, "response_metadata", {}) or {}
    for key in ("token_usage", "usage"):
        if key in metadata and metadata[key]:
            return dict(metadata[key])
    additional = getattr(response, "additional_kwargs", {}) if hasattr(response, "additional_kwargs") else {}
    usage = additional.get("usage")
    if usage:
        return dict(usage)
    return {}


def format_structured_answer(payload: StructuredAnswer) -> str:
    summary_block = payload.summary.strip()
    key_points_block = "\n".join(
        f"- {point.strip()}" for point in payload.key_points if point and str(point).strip()
    )
    conclusion_block = payload.conclusion.strip()

    sections: List[str] = []
    if summary_block:
        sections.append(f"Summary:\n{summary_block}")
    if key_points_block:
        sections.append(f"Key Points:\n{key_points_block}")
    if conclusion_block:
        sections.append(f"Conclusion:\n{conclusion_block}")
    return "\n\n".join(sections).strip()


__all__ = [
    "SYSTEM_PROMPT",
    "PROMPT_USER_INSTRUCTIONS",
    "STRUCTURED_FORMAT_INSTRUCTIONS",
    "USER_PROMPT_TEMPLATE",
    "CHAT_PROMPT",
    "StructuredAnswer",
    "ValidationError",
    "prepare_prompt_state",
    "build_prompt_messages",
    "message_to_text",
    "extract_usage",
    "format_structured_answer",
]
