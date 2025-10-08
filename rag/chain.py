# rag/chain.py
from typing import Dict, Any, List
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.documents import Document

from app.services.prompting import SYSTEM, build_user_prompt
from rag.langchain_adapters import PortsRetriever, RerankDecoratorRetriever, llm_port_runnable


def _format(x: Dict[str, Any]) -> Dict[str, Any]:
    q = x["question"]
    docs: List[Document] = x["docs"]
    temp = x.get("temperature", 0.2)
    max_toks = x.get("max_tokens", 600)

    lines, cites = [], []
    for i, d in enumerate(docs, 1):
        sid = f"S{i}"
        md = d.metadata or {}
        title = md.get("title") or md.get("name") or md.get("doc_id") or "Source"
        bits = []
        if md.get("doc_id"): bits.append(md["doc_id"])
        if md.get("year") is not None: bits.append(str(md["year"]))
        if md.get("page") is not None: bits.append(f"p.{md['page']}")
        header = f"[{sid}] {title}" + (f" ({', '.join(bits)})" if bits else "")
        text = d.page_content or ""
        snippet = (text[:240] + "…") if len(text) > 240 else text
        lines.append(f"{header}: {snippet}")
        cites.append({
            "sid": sid,
            "doc_id": md.get("doc_id"),
            "title": md.get("title"),
            "name": md.get("name"),
            "year": md.get("year"),
            "page": md.get("page"),
            "url": md.get("url"),
            "score": md.get("score"),
            "cosine": md.get("score"),
            "snippet": snippet
        })

    return {
        "system": SYSTEM,
        "user": build_user_prompt(q, "\n\n".join(lines)),
        "temperature": temp,
        "max_tokens": max_toks,
        "citations": cites
    }


def build_chain(emb, store, reranker, llm, *, k=6, mode="dense", filters=None, use_rerank=True):
    base = PortsRetriever(emb=emb, store=store, k=k, mode=mode, filters=(filters or {}))
    retriever = RerankDecoratorRetriever(base=base, reranker=reranker) if use_rerank else base

    pick = {
        "question": RunnableLambda(lambda x: x["question"]),
        "docs":     RunnableLambda(lambda x: x["question"]) | retriever,
        "temperature": RunnableLambda(lambda x: x.get("temperature", 0.2)),
        "max_tokens":  RunnableLambda(lambda x: x.get("max_tokens", 600)),
    }

    prepare = RunnableLambda(_format)
    llm_run = llm_port_runnable(llm)

    chain = (
        pick
        | prepare
        | {"llm": llm_run, "citations": RunnableLambda(lambda y: y["citations"])}
        | RunnableLambda(lambda z: {"answer": z["llm"]["answer"], "usage": z["llm"]["usage"], "citations": z["citations"]})
    )
    return chain
