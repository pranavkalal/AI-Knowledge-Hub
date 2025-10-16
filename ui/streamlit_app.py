# ui/streamlit_app.py
import json
import os
import time
from typing import Any, Dict, Iterable, Optional

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Cotton Knowledge Hub — Prototype", layout="wide")
st.title("AI Knowledge Hub")

DEMO_QUERIES = [
    "What were the standout innovations shared at the 2024 Australian Cotton Conference?",
    "Which grower–industry partnerships are strengthening the cotton supply chain in 2023–24?",
    "How are northern cotton regions adapting water and soil practices for climate resilience?",
    "Summarise the workforce programs helping attract new talent into Australian cotton.",
]


@st.cache_resource
def resolve_api_base(default: Optional[str] = None) -> str:
    """
    Determine the active FastAPI base URL in priority order:
    1. Streamlit query param `api`
    2. Environment variable `FASTAPI_BASE` (fallback `COTTON_API_BASE`)
    3. Provided default or http://localhost:8000
    """
    params = st.query_params
    api_param = params.get("api")
    if api_param:
        if isinstance(api_param, list):
            return api_param[-1].rstrip("/")
        return str(api_param).rstrip("/")

    env_base = os.environ.get("FASTAPI_BASE") or os.environ.get("COTTON_API_BASE")
    if env_base:
        return env_base.rstrip("/")

    return (default or "http://localhost:8000").rstrip("/")


FASTAPI_BASE = resolve_api_base()
API_ROOT = FASTAPI_BASE.rstrip("/")
if API_ROOT.endswith("/api"):
    API_ROOT = API_ROOT[:-4]
API_PREFIX = "/api"


def api_url(path: str) -> str:
    path = path if path.startswith("/") else f"/{path}"
    return f"{API_ROOT}{API_PREFIX}{path}"


SWAGGER_UI = f"{API_ROOT}/docs"

st.caption(f"Open API Explorer: [{SWAGGER_UI}]({SWAGGER_UI})")

st.markdown(
    """
    <style>
    .answer-text {
        font-size: 1.18rem;
        line-height: 1.7;
    }
    .answer-text ul {
        padding-left: 1.6rem;
    }
    .answer-text strong {
        font-weight: 600;
    }
    .citation-summary {
        font-size: 0.95rem;
    }
    [data-testid="stToolbar"] {
        visibility: hidden;
    }
    header[data-testid="stHeader"] {
        background: inherit;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=30)
def ping_api(base: str) -> Dict[str, Any]:
    try:
        url = api_url("/health")
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        info = resp.json()
        info["status_code"] = resp.status_code
        info.setdefault("ok", info.get("status", "") == "ok")
        return info
    except Exception as exc:
        return {"ok": False, "error": str(exc), "status_code": None}


def format_latency(start_time: float) -> str:
    return f"{(time.time() - start_time) * 1000:.0f} ms"


with st.sidebar:
    st.header("Settings")
    st.caption(f"Backend: `{FASTAPI_BASE}`")
    health = st.session_state.get('api_health')
    if health is None:
        health = ping_api(FASTAPI_BASE)
        st.session_state['api_health'] = health
    status_flag = health.get("ok")
    supports_streaming = bool(health.get("streaming"))
    status_label = "✅ Up" if status_flag else "⚠️ Down"
    st.markdown(f"**API status:** {status_label}")
    version = health.get("version") or health.get("build") or "unknown"
    st.caption(f"Backend version: {version}")

    k = st.slider("Top K", 1, 20, 8)
    mode = st.selectbox("Retrieval mode", ["dense", "bm25", "hybrid"], index=0)
    rerank = st.toggle("Rerank (cross-encoder)", value=False)
    y1, y2 = st.columns(2)
    year_min = y1.number_input("Year min", value=2019, step=1, format="%d")
    year_max = y2.number_input("Year max", value=2025, step=1, format="%d")

    if st.button("Check API health", use_container_width=True):
        ping_api.clear()  # type: ignore[attr-defined]
        latest = ping_api(FASTAPI_BASE)
        st.session_state["api_health"] = latest
        st.toast(
            f"Health check -> status code {latest.get('status_code')}, status {latest.get('status', 'unknown')}"
        )
        st.write(latest)

tabs = st.tabs(["Ask (generation)", "Search (debug)"])


def _render_citations(citations: Iterable[Dict[str, Any]]) -> None:
    for idx, citation in enumerate(citations, start=1):
        title = citation.get("title") or "(untitled)"
        year = citation.get("year")
        page = citation.get("page")
        span = citation.get("span", "")

        summary_bits = [title]
        if year not in (None, ""):
            summary_bits.append(str(year))
        if page not in (None, ""):
            summary_bits.append(f"p. {page}")
        summary = " — ".join(summary_bits)

        with st.expander(f"{idx}. {summary}", expanded=False):
            if span:
                truncated = span[:1200]
                st.write(truncated + ("…" if len(span) > len(truncated) else ""))

            links: list[str] = []
            pdf_href = citation.get("url")
            link_label = "Open PDF"
            if page:
                link_label += f" (p. {page})"
            resolved_pdf = pdf_href if isinstance(pdf_href, str) else None
            if resolved_pdf:
                resolved_pdf = resolved_pdf if resolved_pdf.startswith("http") else f"{API_ROOT}{resolved_pdf if resolved_pdf.startswith('/') else '/' + resolved_pdf}"
                links.append(f'<a href="{resolved_pdf}" target="_blank" rel="noopener">{link_label}</a>')
            source_href = citation.get("source_url")
            if isinstance(source_href, str) and source_href:
                links.append(f'<a href="{source_href}" target="_blank" rel="noopener">Source site</a>')
            if links:
                st.markdown(" · ".join(links), unsafe_allow_html=True)


# -------- Ask --------
with tabs[0]:
    st.subheader("Ask a question")
    if "ask_question" not in st.session_state:
        st.session_state["ask_question"] = ""

    st.caption("Need inspiration? Try one of these sample questions:")
    for idx in range(0, len(DEMO_QUERIES), 3):
        row = DEMO_QUERIES[idx : idx + 3]
        cols = st.columns(len(row))
        for offset, (col, sample) in enumerate(zip(cols, row)):
            if col.button(sample, key=f"demo_query_{idx}_{offset}"):
                st.session_state["ask_question"] = sample

    q = st.text_input("e.g., What environmental outcomes were reported in 2023?", key="ask_question")
    stream_mode = st.toggle(
        "Stream answer (experimental)",
        value=False,
        disabled=not supports_streaming,
        help="Enable LangChain streaming in runtime config" if not supports_streaming else None,
    )
    ask_go = st.button("Ask", type="primary")

    if ask_go and q.strip():
        payload = {
            "question": q.strip(),
            "k": int(k),
            "mode": mode,
            "rerank": bool(rerank),
            "filters": {"year_min": int(year_min), "year_max": int(year_max)},
        }
        answer_header = st.empty()
        answer_body = st.empty()
        citations_header = st.empty()
        citations_placeholder = st.container()
        latency_label = st.empty()
        raw_expander = st.expander("Raw response", expanded=False)

        try:
            if stream_mode:
                with st.spinner("Streaming…"):
                    start = time.time()
                    stream_params = {"stream": "true"}
                    resp = requests.post(
                        api_url("/ask"),
                        params=stream_params,
                        json=payload,
                        stream=True,
                        timeout=None,
                    )
                    resp.raise_for_status()

                    tokens: list[str] = []
                    final_payload: Dict[str, Any] = {}

                    for raw_line in resp.iter_lines(decode_unicode=True):
                        if not raw_line or not raw_line.startswith("data: "):
                            continue
                        packet = json.loads(raw_line[6:])
                        if packet.get("type") == "token":
                            tokens.append(packet.get("token", ""))
                            answer_body.markdown("".join(tokens))
                        elif packet.get("type") == "final":
                            final_payload = packet.get("output", {})

                    latency_label.caption(f"Latency: {format_latency(start)}")
                    data = final_payload or {}
            else:
                with st.spinner("Thinking…"):
                    start = time.time()
                    resp = requests.post(api_url("/ask"), json=payload, timeout=120)
                    resp.raise_for_status()
                    latency_label.caption(f"Latency: {format_latency(start)}")
                    data = resp.json()
        except Exception as exc:
            st.error(f"/ask failed: {exc}")
            st.stop()

        if isinstance(data, dict):
            answer = data.get("answer") or "(no answer)"
            citations = data.get("citations", [])
        else:
            answer = str(data)
            citations = []

        answer_header.markdown("### Answer")
        answer_body.markdown(f"<div class='answer-text'>{answer}</div>", unsafe_allow_html=True)

        citations_header.markdown("### Citations")
        if not citations:
            citations_placeholder.info("No citations returned.")
        else:
            with citations_placeholder:
                _render_citations(citations)

        with raw_expander:
            st.json(data)


# -------- Search (debug) --------
with tabs[1]:
    st.subheader("Retriever debug")
    contains = st.text_input("Must contain (optional)")
    neighbors = st.slider("Neighbor stitching", 0, 5, 2)
    per_doc = st.slider("Per-doc diversification", 1, 5, 2)
    query = st.text_input("Query (e.g., 'Namoi MAR findings')", key="search_q")
    go = st.button("Search", key="search_go")

    @st.cache_data(ttl=120, show_spinner=False)
    def hit_search(
        base: str,
        q: str,
        k_val: int,
        n_neighbors: int,
        per_doc_val: int,
        contains_text: str,
        ymin: Optional[int],
        ymax: Optional[int],
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"q": q, "k": k_val, "neighbors": n_neighbors, "per_doc": per_doc_val}
        if contains_text:
            params["contains"] = contains_text
        if ymin is not None:
            params["year_min"] = ymin
        if ymax is not None:
            params["year_max"] = ymax

        start = time.time()
        resp = requests.get(api_url("/search"), params=params, timeout=60)
        resp.raise_for_status()
        return {"payload": resp.json(), "latency": format_latency(start)}

    if go and query.strip():
        ymin = int(year_min) if year_min else None
        ymax = int(year_max) if year_max else None

        try:
            with st.spinner("Searching…"):
                result_bundle = hit_search(
                    FASTAPI_BASE,
                    query.strip(),
                    int(k),
                    int(neighbors),
                    int(per_doc),
                    contains.strip(),
                    ymin,
                    ymax,
                )
        except Exception as exc:
            st.error(f"/search failed: {exc}")
            st.stop()

        payload = result_bundle.get("payload", {})
        results = payload.get("results", [])
        st.caption(f"{len(results)} results · latency {result_bundle.get('latency', '—')}")

        if not results:
            st.warning("No results.")
        downloadable: list[Dict[str, Any]] = []

        for idx, hit in enumerate(results, start=1):
            with st.container(border=True):
                title = hit.get("title") or "(untitled)"
                year = hit.get("year") or "—"
                st.markdown(f"**{idx}. {title}** · {year}")
                preview = hit.get("preview") or ""
                snippet = preview[:1200]
                st.write(snippet + ("…" if len(preview) > len(snippet) else ""))
                links: list[str] = []
                pdf_href = hit.get("pdf_url")
                if isinstance(pdf_href, str) and pdf_href:
                    resolved = pdf_href if pdf_href.startswith("http") else f"{API_ROOT}{pdf_href if pdf_href.startswith('/') else '/' + pdf_href}"
                    page = hit.get("page")
                    label = "Download PDF"
                    if page:
                        label += f" (p. {page})"
                    links.append(f'<a href="{resolved}" target="_blank" rel="noopener">{label}</a>')
                source_href = hit.get("source_url")
                if isinstance(source_href, str) and source_href:
                    links.append(f'<a href="{source_href}" target="_blank" rel="noopener">Source site</a>')
                if links:
                    st.markdown(" · ".join(links), unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                c1.caption(f"doc_id: `{hit.get('doc_id', '')}`")
                c2.caption(f"page: {hit.get('page') or '—'}")
                faiss_val = hit.get("faiss_score")
                rerank_val = hit.get("rerank_score")
                if rerank_val is not None and faiss_val is not None:
                    c3.caption(f"rerank: {round(rerank_val, 3)} · faiss: {round(faiss_val, 3)}")
                elif rerank_val is not None:
                    c3.caption(f"rerank: {round(rerank_val, 3)}")
                else:
                    c3.caption(f"score: {round(hit.get('score', 0.0), 3)}")

            downloadable.append(
                {
                    "rank": idx,
                    "doc_id": hit.get("doc_id"),
                    "title": hit.get("title"),
                    "year": hit.get("year"),
                    "page": hit.get("page"),
                    "score": hit.get("score"),
                    "faiss_score": hit.get("faiss_score"),
                    "rerank_score": hit.get("rerank_score"),
                    "preview": hit.get("preview"),
                    "pdf_url": hit.get("pdf_url"),
                    "source_url": hit.get("source_url"),
                }
            )

        if results:
            json_bytes = json.dumps(downloadable, ensure_ascii=False, indent=2).encode("utf-8")
            csv_bytes = pd.DataFrame(downloadable).to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download results (JSON)",
                data=json_bytes,
                file_name="search_results.json",
                mime="application/json",
            )
            st.download_button(
                "Download results (CSV)",
                data=csv_bytes,
                file_name="search_results.csv",
                mime="text/csv",
            )

        with st.expander("Raw response"):
            st.json(payload)
