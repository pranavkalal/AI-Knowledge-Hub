# ui/streamlit_app.py
import json
import os
import time
from typing import Any, Dict, Iterable, Optional

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Cotton Knowledge Hub — Prototype", layout="wide")
st.title("Cotton Knowledge Hub — Prototype")


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
FASTAPI_DOCS = f"{FASTAPI_BASE}/docs"

st.caption(f"FastAPI docs: [{FASTAPI_DOCS}]({FASTAPI_DOCS})")


@st.cache_data(ttl=30)
def ping_api(base: str) -> Dict[str, Any]:
    try:
        resp = requests.get(f"{base}/health", timeout=10)
        resp.raise_for_status()
        info = resp.json()
        info["status_code"] = resp.status_code
        return info
    except Exception as exc:
        return {"ok": False, "error": str(exc), "status_code": None}


def format_latency(start_time: float) -> str:
    return f"{(time.time() - start_time) * 1000:.0f} ms"


with st.sidebar:
    st.header("Settings")
    st.caption(f"Backend: `{FASTAPI_BASE}`")
    health = ping_api(FASTAPI_BASE)
    status = "✅ OK" if health.get("ok") else "⚠️ Down"
    st.markdown(f"**API status:** {status}")
    version = health.get("version") or health.get("build") or "unknown"
    st.caption(f"Backend version: {version}")

    k = st.slider("Top K", 1, 20, 8)
    mode = st.selectbox("Retrieval mode", ["dense", "bm25", "hybrid"], index=0)
    rerank = st.toggle("Rerank (cross-encoder)", value=False)
    y1, y2 = st.columns(2)
    year_min = y1.number_input("Year min", value=2019, step=1, format="%d")
    year_max = y2.number_input("Year max", value=2025, step=1, format="%d")

    if st.button("Refresh health"):
        ping_api.clear()  # type: ignore[attr-defined]
        st.rerun()

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
    ask_go = st.button("Ask", type="primary")

    if ask_go and q.strip():
        payload = {
            "question": q.strip(),
            "k": int(k),
            "mode": mode,
            "rerank": bool(rerank),
            "filters": {"year_min": int(year_min), "year_max": int(year_max)},
        }
        try:
            with st.spinner("Thinking…"):
                start = time.time()
                resp = requests.post(f"{FASTAPI_BASE}/ask", json=payload, timeout=120)
                resp.raise_for_status()
                latency = format_latency(start)
                data = resp.json()
        except Exception as exc:
            st.error(f"/ask failed: {exc}")
            st.stop()

        answer = data.get("answer") or "(no answer)"
        citations = data.get("citations", [])

        st.markdown("### Answer")
        st.write(answer)
        st.caption(f"Latency: {latency}")

        st.markdown("### Citations")
        if not citations:
            st.info("No citations returned.")
        else:
            _render_citations(citations)

        with st.expander("Raw response"):
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
        resp = requests.get(f"{base}/search", params=params, timeout=60)
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
