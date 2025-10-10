# ui/streamlit_app.py
import json
import os
import time
from typing import Any, Dict, Iterable, Optional

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Cotton Knowledge Hub — Prototype", layout="wide")
st.title("AI Knowledge Hub — Prototype")


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
        with st.container(border=True):
            title = citation.get("title") or "(untitled)"
            page = citation.get("page", "—")
            doc_id = citation.get("doc_id", "")
            span = citation.get("span", "")
            score = citation.get("score")

            header = f"**{idx}. {title}** · page {page}"
            if score is not None:
                header += f" · score {round(score, 3)}"
            st.markdown(header)

            if span:
                truncated = span[:1200]
                st.write(truncated + ("…" if len(span) > len(truncated) else ""))
            st.caption(f"`doc_id: {doc_id}`")


# -------- Ask --------
with tabs[0]:
    st.subheader("Ask a question")
    q = st.text_input("e.g., What environmental outcomes were reported in 2023?")
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
        answer_body.write(answer)

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
                c1, c2, c3 = st.columns(3)
                c1.caption(f"doc_id: `{hit.get('doc_id', '')}`")
                c2.caption(f"score: {round(hit.get('score', 0.0), 3)}")
                c3.caption(f"chunk: `{hit.get('chunk_id', '')}`")

            downloadable.append(
                {
                    "rank": idx,
                    "doc_id": hit.get("doc_id"),
                    "title": hit.get("title"),
                    "year": hit.get("year"),
                    "score": hit.get("score"),
                    "preview": hit.get("preview"),
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
