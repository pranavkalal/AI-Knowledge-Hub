from __future__ import annotations

import re
from typing import Any

GRAPH_RAG_ROLES = {
    "entity_extraction",
    "relationship_extraction",
    "graph_cleaning",
    "graph_validation",
    "query_routing",
    "retrieval",
    "reranking",
    "final_answer_generation",
    "answer_verification",
    "coding_tooling",
    "multimodal_document_understanding",
}


def classify_model(record: dict[str, Any]) -> dict[str, Any]:
    """Add rule-based GraphRAG classification fields to a normalized record."""

    # Adapters can provide cost as strings or invalid values; normalize before
    # any recommendation logic uses those fields.
    record["estimated_cost_input"] = _nonnegative_price(record.get("estimated_cost_input"))
    record["estimated_cost_output"] = _nonnegative_price(record.get("estimated_cost_output"))

    text = _combined_text(record)
    roles: set[str] = set(record.get("graph_rag_roles") or [])
    strengths: list[str] = list(record.get("strengths") or [])
    weaknesses: list[str] = list(record.get("weaknesses") or [])
    notes: list[str] = []

    context_window = _to_int(record.get("context_window"))
    parameter_billions = parameter_size_to_billions(record.get("parameter_size"))
    modalities = {str(item).lower() for item in record.get("modalities") or []}
    local_available = bool(record.get("local_available"))
    api_available = bool(record.get("api_available"))

    if _is_router_record(record):
        # Routers help with query routing, but they are not directly comparable
        # to individual LLMs for GraphRAG generation or extraction work.
        record["model_type"] = "api_router"
        record["hardware_fit"] = "api_only"
        record["graph_rag_roles"] = ["query_routing"]
        record["strengths"] = _unique_nonempty(strengths + ["Routes API requests across models instead of representing one fixed LLM."])
        record["weaknesses"] = _unique_nonempty(weaknesses + ["Not a real single LLM, so benchmark and cost comparisons should use the routed model actually selected."])
        record["hardware_score"] = score_hardware(record)
        record["cost_score"] = score_cost(record)
        record["graph_rag_score"] = 2
        record["recommendation"] = "monitor"
        record["classification_notes"] = [
            "This is an API router/meta-model entry, not one specific LLM.",
            "GraphRAG score 2/5: useful to know about for routing, but not suitable as a direct model comparison row.",
            explain_hardware_score(record),
            explain_cost_score(record),
        ]
        return record

    if has_insufficient_decision_metadata(record):
        # Keep low-information rows visible but out of "test now" decisions
        # until cost or context data becomes available.
        record["hardware_fit"] = normalize_hardware_fit(record.get("hardware_fit")) or infer_hardware_fit(record)
        record["graph_rag_roles"] = sorted(roles)
        record["strengths"] = _unique_nonempty(strengths)
        record["weaknesses"] = _unique_nonempty(
            weaknesses
            + [
                "Input cost, output cost, and context window are all unknown, so the model is not ready for comparison.",
            ]
        )
        record["hardware_score"] = score_hardware(record)
        record["cost_score"] = score_cost(record)
        record["graph_rag_score"] = 1
        record["recommendation"] = "ignore_for_now"
        record["classification_notes"] = [
            "Ignored because input cost, output cost, and context window are all unknown.",
            "GraphRAG score 1/5: not enough metadata for a useful model-selection decision.",
            explain_hardware_score(record),
            explain_cost_score(record),
        ]
        return record

    # The following signals map model metadata to GraphRAG pipeline roles.
    if _has_any(text, ["embedding", "sentence-transformer", "sentence transformer"]) or "embeddings" in modalities:
        roles.add("retrieval")
        strengths.append("Useful for vector retrieval and semantic indexing.")

    if _has_any(text, ["rerank", "reranker", "cross-encoder"]):
        roles.add("reranking")
        strengths.append("Useful for reranking retrieved chunks or graph neighborhoods.")

    if context_window >= 128_000:
        roles.add("final_answer_generation")
        roles.add("graph_validation")
        strengths.append("Long context window supports synthesis over large retrieved subgraphs.")

    if local_available and (parameter_billions is None or parameter_billions <= 8):
        roles.update({"entity_extraction", "query_routing", "graph_cleaning"})
        strengths.append("Good candidate for local, privacy-preserving extraction and preprocessing.")

    if _has_any(text, ["reason", "thinking", "code", "coding", "math", "agent", "tool"]):
        roles.update({"relationship_extraction", "graph_validation", "answer_verification", "coding_tooling"})
        strengths.append("Reasoning/coding signals make it promising for validation and relationship extraction.")

    if _has_any(text, ["vision", "image", "multimodal"]) or {"image", "audio", "multimodal"} & modalities:
        roles.add("multimodal_document_understanding")
        strengths.append("Multimodal support can help parse image-heavy documents before graph construction.")

    record["hardware_fit"] = normalize_hardware_fit(record.get("hardware_fit")) or infer_hardware_fit(record)

    if api_available and not local_available:
        # Hosted-only models are still useful, but their hardware fit is about
        # API access rather than local GPU size.
        record["hardware_fit"] = "api_only"
        if context_window >= 32_000 or _has_any(text, ["claude", "gpt", "gemini", "deepseek", "reason"]):
            roles.update({"final_answer_generation", "graph_validation"})
            strengths.append("API availability makes it easy to test for final synthesis or validation.")

    if not roles and api_available:
        roles.add("final_answer_generation")
        notes.append("Assigned a conservative final-answer role because the model is API-accessible.")

    record["graph_rag_roles"] = sorted(roles)
    record["strengths"] = _unique_nonempty(strengths)
    record["weaknesses"] = _unique_nonempty(weaknesses or _default_weaknesses(record, roles))
    record["hardware_score"] = score_hardware(record)
    record["cost_score"] = score_cost(record)
    record["graph_rag_score"] = score_graphrag(record)
    record["recommendation"] = recommend(record)
    record["classification_notes"] = notes + _why_notes(record, roles)
    return record


def infer_hardware_fit(record: dict[str, Any]) -> str:
    # Hardware fit is a practical bucket for classroom/project planning, not a
    # precise deployment sizing calculator.
    if record.get("api_available") and not record.get("local_available"):
        return "api_only"
    if not record.get("local_available"):
        return "unknown"

    billions = parameter_size_to_billions(record.get("parameter_size"))
    if billions is None:
        return "unknown"
    if billions <= 8:
        return "laptop"
    if billions <= 14:
        return "desktop_gpu"
    if billions <= 34:
        return "workstation_gpu"
    return "server_gpu"


def normalize_hardware_fit(value: Any) -> str:
    fit = str(value or "").strip().lower()
    aliases = {
        "laptop_cpu": "laptop",
        "laptop_gpu": "laptop",
        "consumer_gpu": "desktop_gpu",
    }
    return aliases.get(fit, fit)


def score_graphrag(record: dict[str, Any]) -> int:
    score = 1
    roles = set(record.get("graph_rag_roles") or [])
    context_window = _to_int(record.get("context_window"))
    text = _combined_text(record)

    # Start from availability, role coverage, context length, and useful tags;
    # then cap the result to the dashboard's 1-5 scale.
    if roles:
        score += min(2, len(roles) // 2 + 1)
    if context_window >= 128_000:
        score += 1
    if record.get("local_available") or record.get("api_available"):
        score += 1
    if _has_any(text, ["reason", "code", "embedding", "rerank", "retrieval"]):
        score += 1
    if score_cost(record) <= 2 and not record.get("local_available"):
        score -= 1
    return max(1, min(5, score))


def score_hardware(record: dict[str, Any]) -> int:
    fit = normalize_hardware_fit(record.get("hardware_fit")) or infer_hardware_fit(record)
    return {
        "laptop": 5,
        "desktop_gpu": 4,
        "workstation_gpu": 3,
        "server_gpu": 2,
        "api_only": 3,
        "unknown": 1,
    }.get(str(fit), 1)


def score_cost(record: dict[str, Any]) -> int:
    if record.get("local_available"):
        return 5
    # Cost score uses the combined known input/output price per 1M tokens.
    # Unknown API pricing is treated as medium rather than excellent.
    input_cost = _nonnegative_price(record.get("estimated_cost_input"))
    output_cost = _nonnegative_price(record.get("estimated_cost_output"))
    known = [value for value in (input_cost, output_cost) if value is not None]
    if not known:
        return 3 if record.get("api_available") else 1
    combined = sum(known)
    if combined <= 1:
        return 5
    if combined <= 5:
        return 4
    if combined <= 20:
        return 3
    if combined <= 50:
        return 2
    return 1


def explain_cost_score(record: dict[str, Any]) -> str:
    if record.get("local_available"):
        return "Cost score 5/5: local model, so API token cost is treated as zero after hardware setup."
    input_cost = _nonnegative_price(record.get("estimated_cost_input"))
    output_cost = _nonnegative_price(record.get("estimated_cost_output"))
    if input_cost is None and output_cost is None:
        return f"Cost score {score_cost(record)}/5: price is unknown, so API models default to medium cost."
    combined = (input_cost or 0) + (output_cost or 0)
    return (
        f"Cost score {score_cost(record)}/5: about ${_money(input_cost)}/1M input tokens and "
        f"${_money(output_cost)}/1M output tokens; combined ${_money(combined)}/1M token pair."
    )


def explain_hardware_score(record: dict[str, Any]) -> str:
    fit = normalize_hardware_fit(record.get("hardware_fit")) or infer_hardware_fit(record)
    labels = {
        "laptop": "runs on a laptop-class local setup",
        "desktop_gpu": "needs a stronger desktop GPU",
        "workstation_gpu": "needs workstation-class GPU memory",
        "server_gpu": "needs server-class GPU resources",
        "api_only": "runs through an API, not local hardware",
        "unknown": "hardware need is unknown",
    }
    return f"Hardware score {score_hardware(record)}/5: {fit} means it {labels.get(fit, 'has an unclear hardware fit')}."


def explain_graphrag_score(record: dict[str, Any]) -> str:
    roles = set(record.get("graph_rag_roles") or [])
    context_window = _to_int(record.get("context_window"))
    signals = []
    if roles:
        signals.append(f"{len(roles)} GraphRAG role(s)")
    if context_window >= 128_000:
        signals.append("long context")
    if record.get("local_available") or record.get("api_available"):
        signals.append("available to run/test")
    if _has_any(_combined_text(record), ["reason", "code", "embedding", "rerank", "retrieval"]):
        signals.append("reasoning/retrieval tags")
    if score_cost(record) <= 2 and not record.get("local_available"):
        signals.append("cost penalty")
    return f"GraphRAG score {score_graphrag(record)}/5: based on {', '.join(signals) if signals else 'limited useful signals'}."


def recommend(record: dict[str, Any]) -> str:
    if has_insufficient_decision_metadata(record):
        return "ignore_for_now"
    graph_score = int(record.get("graph_rag_score") or 1)
    if graph_score >= 4:
        return "test_now"
    if graph_score >= 2:
        return "monitor"
    return "ignore_for_now"


def has_insufficient_decision_metadata(record: dict[str, Any]) -> bool:
    return (
        _nonnegative_price(record.get("estimated_cost_input")) is None
        and _nonnegative_price(record.get("estimated_cost_output")) is None
        and _to_int(record.get("context_window")) == 0
    )


def parameter_size_to_billions(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).lower()
    match = re.search(r"(\d+(?:\.\d+)?)\s*b", text)
    if match:
        return float(match.group(1))
    if "moe" in text:
        return None
    return None


def _combined_text(record: dict[str, Any]) -> str:
    fields = [
        record.get("model_name"),
        record.get("model_family"),
        record.get("model_type"),
        record.get("license"),
        " ".join(record.get("modalities") or []),
        " ".join(record.get("tags") or []),
        " ".join(record.get("strengths") or []),
        " ".join(record.get("notes") or [] if isinstance(record.get("notes"), list) else [str(record.get("notes") or "")]),
    ]
    raw = record.get("raw_metadata_json") or record.get("raw_metadata") or {}
    fields.append(str(raw))
    return " ".join(str(field or "") for field in fields).lower()


def _has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _to_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(float(str(value).replace(",", "")))
    except ValueError:
        return 0


def _to_float(value: Any) -> float | None:
    if value in (None, "", "unknown"):
        return None
    try:
        return float(str(value).replace("$", "").replace(",", ""))
    except ValueError:
        return None


def _nonnegative_price(value: Any) -> float | None:
    price = _to_float(value)
    if price is None or price < 0:
        return None
    return price


def _is_router_record(record: dict[str, Any]) -> bool:
    text = _combined_text(record)
    return (
        str(record.get("model_name") or "").lower() == "openrouter/auto"
        or str(record.get("model_type") or "").lower() == "api_router"
        or "auto router" in text
        or "meta-model" in text
        or '"tokenizer": "router"' in text
        or "'tokenizer': 'router'" in text
    )


def _unique_nonempty(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        clean = str(value).strip()
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result


def _default_weaknesses(record: dict[str, Any], roles: set[str]) -> list[str]:
    weaknesses = []
    if not record.get("license"):
        weaknesses.append("License is unknown and should be verified before production use.")
    if not roles:
        weaknesses.append("No strong GraphRAG role detected from available metadata.")
    if not record.get("context_window"):
        weaknesses.append("Context window is unknown.")
    return weaknesses


def _why_notes(record: dict[str, Any], roles: set[str]) -> list[str]:
    notes = [f"Detected GraphRAG roles: {', '.join(sorted(roles)) or 'none'}."]
    if record.get("context_window"):
        notes.append(f"Context window considered: {record['context_window']}.")
    if record.get("hardware_fit"):
        notes.append(f"Hardware fit inferred as {record['hardware_fit']}.")
    notes.append(explain_graphrag_score(record))
    notes.append(explain_hardware_score(record))
    notes.append(explain_cost_score(record))
    return notes


def _money(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value == 0:
        return "0"
    if value < 0.01:
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return f"{value:.2f}".rstrip("0").rstrip(".")
