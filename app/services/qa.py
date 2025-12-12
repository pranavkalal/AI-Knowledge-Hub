"""
End-to-end QA pipeline: embed query -> retrieve -> (optional) rerank -> build prompt -> call LLM.
Returns the generated answer and normalized source list for the API layer.
"""

from time import perf_counter
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
        total_start = perf_counter()
        qv = self.emb.embed_query(q)

        # 2) retrieve top-k (be graceful if the store doesn't support extra kwargs)
        settings = resolve_retrieval_settings(filters)

        store_filters = {}
        if settings.year_min is not None:
            store_filters["year_min"] = settings.year_min
        if settings.year_max is not None:
            store_filters["year_max"] = settings.year_max

        rerank_topn = None
        if hasattr(self.rerank, "topn"):
            try:
                rerank_topn = int(getattr(self.rerank, "topn"))
            except (TypeError, ValueError):
                rerank_topn = None
        candidate_limit = max(k * 5, rerank_topn if rerank_topn else 0)
        if candidate_limit <= 0:
            candidate_limit = k * 5

        overfetch = candidate_limit
        query_kwargs = {"k": overfetch}
        if mode is not None:
            query_kwargs["mode"] = mode
        if store_filters:
            query_kwargs["filters"] = store_filters

        ann_start = perf_counter()
        try:
            hits = self.store.query(qv, **query_kwargs)
        except TypeError:
            # Older stores: only accept (vector, k)
            hits = self.store.query(qv, k=overfetch)
        ann_ms = (perf_counter() - ann_start) * 1000.0

        # 4) stitch metadata before reranking
        stitch_start = perf_counter()
        stitched_hits = prepare_hits(hits, self.store, settings, limit=candidate_limit)
        print(f"[qa.debug] candidates_before_rerank={len(stitched_hits)}")
        stitch_ms = (perf_counter() - stitch_start) * 1000.0

        # 5) optional rerank
        do_rerank = True if rerank is None else bool(rerank)
        rerank_ms = 0.0
        final_hits = stitched_hits
        if do_rerank:
            try:
                rerank_start = perf_counter()
                final_hits = self.rerank.rerank(q, stitched_hits)
                rerank_ms = getattr(self.rerank, "last_run_ms", (perf_counter() - rerank_start) * 1000.0)
            except Exception:
                # If reranker explodes, limp along with the original ranking
                final_hits = stitched_hits
        
        # 6) limit to requested k after rerank
        hits = final_hits[:k]
        print(
            f"[qa.debug] after_rerank={len(final_hits)} final_k={len(hits)}"
        )

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

        total_ms = (perf_counter() - total_start) * 1000.0
        rerank_batches = getattr(self.rerank, "last_batches", 0) if do_rerank else 0
        print(
            f"[qa.timing] ANN={ann_ms:.1f}ms stitch={stitch_ms:.1f}ms rerank={rerank_ms:.1f}ms "
            f"total={total_ms:.1f}ms rerank_batches={rerank_batches}"
        )

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

    async def stream(
        self,
        question: str,
        k: int = 6,
        temperature: float = 0.2,
        max_tokens: int = 600,
        *,
        mode: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        rerank: Optional[bool] = None
    ):
        """
        Yields events:
        - {"type": "sources", "data": [...]}
        - {"type": "token", "token": "..."}
        - {"type": "usage", "data": {...}}
        """
        q = (question or "").strip()
        if not q:
            yield {"type": "error", "message": "empty_question"}
            return

        # Reuse retrieval logic (copy-paste for now to avoid refactoring risk)
        # In a real refactor, extract retrieval into _retrieve()
        
        # 1) embed query
        qv = self.emb.embed_query(q)

        # 2) retrieve top-k
        settings = resolve_retrieval_settings(filters)
        store_filters = {}
        if settings.year_min is not None: store_filters["year_min"] = settings.year_min
        if settings.year_max is not None: store_filters["year_max"] = settings.year_max

        rerank_topn = None
        if hasattr(self.rerank, "topn"):
            try:
                rerank_topn = int(getattr(self.rerank, "topn"))
            except (TypeError, ValueError):
                rerank_topn = None
        candidate_limit = max(k * 5, rerank_topn if rerank_topn else 0)
        if candidate_limit <= 0: candidate_limit = k * 5

        overfetch = candidate_limit
        query_kwargs = {"k": overfetch}
        if mode is not None: query_kwargs["mode"] = mode
        if store_filters: query_kwargs["filters"] = store_filters

        try:
            hits = self.store.query(qv, **query_kwargs)
        except TypeError:
            hits = self.store.query(qv, k=overfetch)

        # 4) stitch
        stitched_hits = prepare_hits(hits, self.store, settings, limit=candidate_limit)

        # 5) rerank
        do_rerank = True if rerank is None else bool(rerank)
        final_hits = stitched_hits
        if do_rerank:
            try:
                final_hits = self.rerank.rerank(q, stitched_hits)
            except Exception:
                final_hits = stitched_hits
        
        # 6) limit
        hits = final_hits[:k]

        if not hits:
            yield {"type": "token", "token": "I couldn’t find relevant passages in the current corpus for that question."}
            return

        # Format sources
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
            if rel_path: citation.setdefault("rel_path", rel_path)
            
            # Construct local URL if missing
            if not citation.get("url") and (citation.get("filename") or citation.get("rel_path")):
                fname = citation.get("filename") or citation.get("rel_path")
                citation["url"] = f"/api/pdf/{fname}"
                
            citations.append(citation)

        # Yield sources first
        yield {"type": "sources", "data": citations}

        # Call LLM stream
        user = build_user_prompt(q, "\n\n".join(lines))
        
        if hasattr(self.llm, "chat_stream"):
            for token in self.llm.chat_stream(SYSTEM, user, temperature, max_tokens):
                yield {"type": "token", "token": token}
        else:
            # Fallback to sync
            ans, usage = self.llm.chat(SYSTEM, user, temperature, max_tokens)
            yield {"type": "token", "token": ans}
            yield {"type": "usage", "data": usage}
