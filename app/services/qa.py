"""
End-to-end QA pipeline: embed query -> retrieve -> (optional) rerank -> build prompt -> call LLM.
Returns the generated answer and normalized source list for the API layer.
"""

from typing import Dict, List, Optional, Any
from app.ports import EmbedderPort, VectorStorePort, RerankerPort, LLMPort
from app.services.prompting import SYSTEM, build_user_prompt
from app.services.formatting import format_citation, format_metadata, format_snippet
from rag.retrieval.utils import (
    resolve_retrieval_settings,
    prepare_hits,
)


class QAPipeline:
    def __init__(self, emb: EmbedderPort, store: VectorStorePort, rerank: RerankerPort, llm: LLMPort):
        self.emb, self.store, self.rerank, self.llm = emb, store, rerank, llm

    def ask(
        self,
        question: str,
        k: int = 6,
        temperature: float = 0.2,
        max_tokens: int = 600,
        *,
        mode: Optional[str] = None,           # "dense" | "bm25" | "hybrid" (store may ignore)
        filters: Optional[Dict[str, Any]] = None,  # e.g., {"year_min": 2019, "year_max": 2025}
        rerank: Optional[bool] = None         # True to force, False to skip, None = default behavior
    ) -> Dict:
        """
        Returns dict with keys: answer, sources, usage
        - sources is a list of dicts with: sid, doc_id, title, page, url, score, snippet
        """
        q = (question or "").strip()
        if not q:
            return {"answer": "", "sources": [], "usage": {"error": "empty_question"}}

        # 1) embed query
        qv = self.emb.embed_query(q)

        # 2) retrieve top-k (be graceful if the store doesn't support extra kwargs)
        settings = resolve_retrieval_settings(filters)

        store_filters = {}
        if settings.year_min is not None:
            store_filters["year_min"] = settings.year_min
        if settings.year_max is not None:
            store_filters["year_max"] = settings.year_max

        overfetch = max(k * 5, 50)
        query_kwargs = {"k": overfetch}
        if mode is not None:
            query_kwargs["mode"] = mode
        if store_filters:
            query_kwargs["filters"] = store_filters

        try:
            hits = self.store.query(qv, **query_kwargs)
        except TypeError:
            # Older stores: only accept (vector, k)
            hits = self.store.query(qv, k=overfetch)

        # 3) optional rerank
        do_rerank = True if rerank is None else bool(rerank)
        if do_rerank:
            try:
                hits = self.rerank.rerank(q, hits)
            except Exception:
                # If reranker explodes, limp along with the original ranking
                pass

        # 4) format sources and build context lines for the prompt
        hits = prepare_hits(hits, self.store, settings, limit=k)

        if not hits:
            # no retrieval = don't pay LLM tax
            return {
                "answer": "I couldn’t find relevant passages in the current corpus for that question.",
                "sources": [],
                "usage": {"retrieved": 0},
            }

        lines = []
        citations = []
        for idx, hit in enumerate(hits, start=1):
            md = hit.get("metadata", {}) if isinstance(hit, dict) else {}
            sid = f"S{idx}"
            snippet = format_snippet(md.get("preview") or md.get("text") or "", settings.max_snippet_chars)

            title = md.get("title") or md.get("doc_id") or "Source"
            meta_suffix = format_metadata(md)
            line = f"[{sid}] {title}{f' {meta_suffix}' if meta_suffix else ''}: {snippet}"
            lines.append(line)

            citation = format_citation(hit)
            citation["sid"] = sid
            citation.setdefault("url", md.get("url"))
            citation.setdefault("source_url", md.get("source_url"))
            rel_path = md.get("rel_path") or md.get("filename")
            if rel_path:
                citation.setdefault("rel_path", rel_path)
            citations.append(citation)

        user = build_user_prompt(q, "\n\n".join(lines))
        answer, usage = self.llm.chat(SYSTEM, user, temperature, max_tokens)

        if citations:
            formatted_sources = []
            for cit in citations:
                label = cit.get("sid") or ""
                title = cit.get("title") or cit.get("doc_id") or "Source"
                year = cit.get("year")
                page = cit.get("page")
                doc_id = cit.get("doc_id")
                url = cit.get("url")

                bits = []
                if year is not None:
                    bits.append(str(year))
                if page is not None:
                    bits.append(f"p.{page}")
                if doc_id:
                    bits.append(doc_id)

                suffix = f" ({', '.join(bits)})" if bits else ""
                line = f"{label} — {title}{suffix}"
                if url:
                    line = f"{line} — {url}"
                formatted_sources.append(line)

            answer = f"{answer.strip()}\n\nSources:\n" + "\n".join(f"- {line}" for line in formatted_sources)

        return {"answer": answer, "sources": citations, "usage": usage}
