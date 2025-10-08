"""
End-to-end QA pipeline: embed query -> retrieve -> (optional) rerank -> build prompt -> call LLM.
Returns the generated answer and normalized source list for the API layer.
"""

from typing import Dict, List, Optional, Any
from app.ports import EmbedderPort, VectorStorePort, RerankerPort, LLMPort
from app.services.prompting import SYSTEM, build_user_prompt


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
        query_kwargs = {"k": k}
        if mode is not None:
            query_kwargs["mode"] = mode
        if filters:
            query_kwargs["filters"] = filters

        try:
            hits = self.store.query(qv, **query_kwargs)
        except TypeError:
            # Older stores: only accept (vector, k)
            hits = self.store.query(qv, k=k)

        # 3) optional rerank
        do_rerank = True if rerank is None else bool(rerank)
        if do_rerank:
            try:
                hits = self.rerank.rerank(q, hits)
            except Exception:
                # If reranker explodes, limp along with the original ranking
                pass

        # 4) format sources and build context lines for the prompt
        if not hits:
            # no retrieval = don't pay LLM tax
            return {
                "answer": "I couldn’t find relevant passages in the current corpus for that question.",
                "sources": [],
                "usage": {"retrieved": 0},
            }

        srcs: List[Dict[str, Any]] = []
        lines: List[str] = []

        for i, h in enumerate(hits, 1):
            md = h.get("metadata", {}) if isinstance(h, dict) else {}
            sid = f"S{i}"

            text = md.get("text") or md.get("chunk") or ""
            snippet = (text[:240] + "…") if len(text) > 240 else text

            title = md.get("title") or md.get("doc_id") or md.get("id") or "Source"
            doc_id = md.get("doc_id") or md.get("id") or ""
            page = md.get("page")
            page_str = f", p.{page}" if page is not None else ""

            lines.append(f"[{sid}] {title} ({doc_id}{page_str}): {snippet}")

            srcs.append({
                "sid": sid,
                "doc_id": doc_id,
                "title": md.get("title"),
                "page": page,
                "url": md.get("url"),
                "score": h.get("score"),
                # keep 'snippet' key; API layer maps snippet->span for UI
                "snippet": snippet,
            })

        # 5) build prompt messages
        user = build_user_prompt(q, "\n\n".join(lines))

        # 6) call LLM
        answer, usage = self.llm.chat(SYSTEM, user, temperature, max_tokens)

        return {"answer": answer, "sources": srcs, "usage": usage}
