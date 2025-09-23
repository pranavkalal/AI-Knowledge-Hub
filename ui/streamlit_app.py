# ui/streamlit_app.py
import os, requests, streamlit as st
API_BASE = os.environ.get("COTTON_API_BASE", "http://localhost:8000/api")

st.set_page_config(page_title="Cotton Knowledge Hub — Prototype", layout="wide")
st.title("Cotton Knowledge Hub — Prototype Search")
st.caption(f"API base: {API_BASE}")

with st.sidebar:
    st.header("Settings")
    k = st.slider("Top K", 1, 20, 8)
    neighbors = st.slider("Neighbor stitching", 0, 5, 2)
    per_doc = st.slider("Per-doc diversification", 1, 5, 2)
    contains = st.text_input("Must contain (optional)", help="Only return chunks that include this phrase")
    col_y1, col_y2 = st.columns(2)
    year_min = col_y1.number_input("Year min", value=2019, step=1, format="%d")
    year_max = col_y2.number_input("Year max", value=2025, step=1, format="%d")
    if st.button("Ping API"):
        try:
            r = requests.get(f"{API_BASE}/health", timeout=10)
            st.success(f"Health: {r.json()}")
        except Exception as e:
            st.error(f"Health check failed: {e}")

query = st.text_input("Ask a question (e.g., 'environmental outcomes 2023', 'Namoi MAR findings')")
go = st.button("Search")

def hit_api(q, k, neighbors, per_doc, contains, year_min, year_max):
    params = {"q": q, "k": k, "neighbors": neighbors, "per_doc": per_doc}
    if contains: params["contains"] = contains
    if year_min: params["year_min"] = int(year_min)
    if year_max: params["year_max"] = int(year_max)
    r = requests.get(f"{API_BASE}/search", params=params, timeout=60)
    r.raise_for_status()
    return r.json()

if go and query.strip():
    with st.spinner("Searching…"):
        data = hit_api(query.strip(), k, neighbors, per_doc, contains, year_min, year_max)
    results = data.get("results", [])
    st.caption(f"{len(results)} results")
    if not results:
        st.warning("No results. Try adjusting filters or Top K.")
        st.expander("Raw response").json(data)
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
            c3.caption(f"chunk: {h.get('chunk_id','')}")
