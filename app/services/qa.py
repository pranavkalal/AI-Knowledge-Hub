"""
End-to-end QA pipeline: embed query -> retrieve -> (optional) rerank -> build prompt -> call LLM.
Returns the generated answer and normalized source list for the API layer.
"""

from typing import Dict, List
from app.ports import EmbedderPort, VectorStorePort, RerankerPort, LLMPort
from app.services.prompting import SYSTEM, build_user_prompt

class QAPipeline:
    def __init__(self, emb: EmbedderPort, store: VectorStorePort, rerank: RerankerPort, llm: LLMPort):
        self.emb, self.store, self.rerank, self.llm = emb, store, rerank, llm

    def ask(self, question: str, k: int, temperature: float, max_tokens: int) -> Dict:
        """Main entry: returns dict with keys: answer, sources, usage."""
        # 1) embed query
        qv = self.emb.embed_query(question)
        # 2) retrieve top-k
        hits = self.store.query(qv, k=k)
        # 3) optional rerank
        hits = self.rerank.rerank(question, hits)

        # 4) format sources and build sid map
        srcs: List[Dict] = []
        lines: List[str] = []
        for i, h in enumerate(hits, 1):
            md = h.get("metadata", {})
            sid = f"S{i}"
            text = md.get("text", "") or ""
            snippet = (text[:240] + "…") if len(text) > 240 else text
            title = md.get("title") or md.get("doc_id") or md.get("id") or "Source"
            page_str = f", p.{md.get('page')}" if md.get("page") is not None else ""
            lines.append(f"[{sid}] {title} ({md.get('doc_id')}{page_str}): {snippet}")
            srcs.append({
                "sid": sid,
                "doc_id": md.get("doc_id"),
                "title": md.get("title"),
                "page": md.get("page"),
                "url": md.get("url"),
                "score": h.get("score"),
                "snippet": snippet
            })

        # 5) build prompt messages
        user = build_user_prompt(question, "\n\n".join(lines))

        # 6) call LLM
        answer, usage = self.llm.chat(SYSTEM, user, temperature, max_tokens)

        return {"answer": answer, "sources": srcs, "usage": usage}
