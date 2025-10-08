# ui/streamlit_app.py
import os, requests, streamlit as st

API_BASE = os.environ.get("COTTON_API_BASE", "http://localhost:8000/api")

st.set_page_config(page_title="Cotton Knowledge Hub — Prototype", layout="wide")
st.title("Cotton Knowledge Hub — Prototype")
st.caption(f"API base: {API_BASE}")

def ping_api():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

with st.sidebar:
    st.header("Settings")
    k = st.slider("Top K", 1, 20, 8)
    mode = st.selectbox("Retrieval mode", ["dense", "bm25", "hybrid"], index=0)
    rerank = st.toggle("Rerank (cross-encoder)", value=False)
    y1, y2 = st.columns(2)
    year_min = y1.number_input("Year min", value=2019, step=1, format="%d")
    year_max = y2.number_input("Year max", value=2025, step=1, format="%d")
    if st.button("Ping API"):
        st.json(ping_api())

tabs = st.tabs(["Ask (generation)", "Search (debug)"])

# -------- Ask --------
with tabs[0]:
    st.subheader("Ask a question")
    q = st.text_input("e.g., What environmental outcomes were reported in 2023?")
    ask_go = st.button("Ask", type="primary")
    if ask_go and q.strip():
        payload = {
            "question": q.strip(),  # <-- standardize on 'question'
            "k": int(k),
            "mode": mode,
            "rerank": bool(rerank),
            "filters": {"year_min": int(year_min), "year_max": int(year_max)},
        }
        try:
            with st.spinner("Thinking…"):
                r = requests.post(f"{API_BASE}/ask", json=payload, timeout=120)
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            st.error(f"/ask failed: {e}")
            st.stop()

        answer = data.get("answer") or "(no answer)"
        citations = data.get("citations", [])

        st.markdown("### Answer")
        st.write(answer)

        st.markdown("### Citations")
        if not citations:
            st.info("No citations returned.")
        for i, c in enumerate(citations, 1):
            with st.container(border=True):
                title = c.get("title") or "(untitled)"
                page = c.get("page", "—")
                doc_id = c.get("doc_id","")
                span = c.get("span","")
                score = c.get("score", None)
                head = f"**{i}. {title}** · page {page}"
                if score is not None:
                    head += f" · score {round(score,3)}"
                st.markdown(head)
                if span:
                    st.write(span[:1200] + ("…" if len(span) > 1200 else ""))
                st.caption(f"`doc_id: {doc_id}`")

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

    def hit_search(q, k, neighbors, per_doc, contains, year_min, year_max):
        params = {"q": q, "k": k, "neighbors": neighbors, "per_doc": per_doc}
        if contains: params["contains"] = contains
        if year_min: params["year_min"] = int(year_min)
        if year_max: params["year_max"] = int(year_max)
        r = requests.get(f"{API_BASE}/search", params=params, timeout=60)
        r.raise_for_status()
        return r.json()

    if go and query.strip():
        try:
            with st.spinner("Searching…"):
                data = hit_search(query.strip(), k, neighbors, per_doc, contains, year_min, year_max)
        except Exception as e:
            st.error(f"/search failed: {e}")
            st.stop()

        results = data.get("results", [])
        st.caption(f"{len(results)} results")
        if not results:
            st.warning("No results.")
            with st.expander("Raw response"):
                st.json(data)
        for i, h in enumerate(results, 1):
            with st.container(border=True):
                title = h.get("title") or "(untitled)"
                year = h.get("year") or "—"
                st.markdown(f"**{i}. {title}** · {year}")
                text = h.get("preview") or ""
                st.write(text[:1200] + ("…" if len(text) > 1200 else ""))
                c1, c2, c3 = st.columns(3)
                c1.caption(f"doc_id: `{h.get('doc_id','')}`")
                c2.caption(f"score: {round(h.get('score', 0.0), 3)}")
                c3.caption(f"chunk: `{h.get('chunk_id','')}`")
