
"""Prototype router chain for multi-hop question handling."""

from __future__ import annotations

from typing import Any, Dict

from langchain_core.runnables import RunnableLambda

from app.services.qa import QAPipeline


def route_by_question_type(question: str) -> str:
    """Classify the question into a coarse category."""
    q = (question or "").lower()
    if any(tok in q for tok in ("statistic", "percentage", "how many", "number", "ratio")):
        return "statistic"
    if q.startswith("what is") or "define" in q:
        return "definition"
    if any(tok in q for tok in ("impact", "effect", "influence", "change")):
        return "impact"
    if "study" in q and "2021" in q:
        return "statistic"
    return "impact"


def build_router_chain(
    *,
    emb: Any,
    store: Any,
    reranker: Any,
    llm: Any,
    default_k: int,
    base_filters: Dict[str, Any],
    use_rerank: bool,
) -> RunnableLambda:
    """Return a runnable that routes questions to specialised subchains."""

    qa = QAPipeline(emb, store, reranker, llm)

    def _definition(inputs: Dict[str, Any]) -> Dict[str, Any]:
        question = inputs.get("question", "")
        answer, usage = llm.chat(
            "You summarise cotton R&D concepts succinctly.",
            f"""Provide a brief definition or overview for the following request:
{question}""",
            float(inputs.get("temperature", 0.2)),
            int(inputs.get("max_tokens", 400)),
        )
        return {"answer": answer, "citations": [], "usage": usage}

    def _qa_answer(inputs: Dict[str, Any], *, k: int, rerank: bool) -> Dict[str, Any]:
        out = qa.ask(
            question=inputs.get("question", ""),
            k=k,
            temperature=float(inputs.get("temperature", 0.2)),
            max_tokens=int(inputs.get("max_tokens", 600)),
            filters=base_filters,
            rerank=rerank,
        )
        return {"answer": out.get("answer", ""), "citations": out.get("sources", []), "usage": out.get("usage")}

    def _impact(inputs: Dict[str, Any]) -> Dict[str, Any]:
        return _qa_answer(inputs, k=default_k, rerank=use_rerank)

    def _statistic(inputs: Dict[str, Any]) -> Dict[str, Any]:
        return _qa_answer(inputs, k=max(default_k, 4), rerank=False)

    handlers = {
        "definition": _definition,
        "impact": _impact,
        "statistic": _statistic,
    }

    def _route(inputs: Dict[str, Any]) -> Dict[str, Any]:
        key = route_by_question_type(inputs.get("question", ""))
        handler = handlers.get(key, _impact)
        return handler(inputs)

    return RunnableLambda(_route)
