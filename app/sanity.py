# End-to-end sanity: embed 3 toy docs, index, search.
import os
import numpy as np
from rich import print

# Keep the tokenizer from forking extra workers on macOS
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from rag.embed.sentence_xfmr import SentenceEmbedder
from store.faiss_store import FaissStore

DOCS = [
    {
        "id": "1",
        "text": (
            "In 2024, CRDC invested in three major projects focused on improving "
            "water-use efficiency in cotton farming. Techniques tested included "
            "drip irrigation systems, soil moisture sensors, and scheduling models "
            "to optimize watering patterns."
        ),
        "meta": {"year": 2024, "topic": "Water Efficiency"},
    },
    {
        "id": "2",
        "text": (
            "Research in 2024 examined integrated pest management (IPM) strategies. "
            "The study highlighted reduced pesticide applications by combining crop "
            "rotation, natural predators, and targeted chemical sprays."
        ),
        "meta": {"year": 2024, "topic": "Pest Management"},
    },
    {
        "id": "3",
        "text": (
            "A 2020 study explored soil salinity challenges in arid regions. "
            "The report showed that high salinity levels reduced cotton yields "
            "by up to 25%, with recommendations for gypsum treatment and improved drainage."
        ),
        "meta": {"year": 2020, "topic": "Soil Health"},
    },
    {
        "id": "4",
        "text": (
            "An economic analysis from 2023 investigated the profitability of adopting "
            "precision agriculture technologies. The findings suggested that farmers "
            "could save 15% on input costs and increase yields by using drone-based "
            "monitoring and variable-rate fertilization."
        ),
        "meta": {"year": 2023, "topic": "Economics"},
    },
]


def unwrap_hit(h: dict):
    """
    Support both result shapes:
    - NEW (recommended): {"rank", "id", "score", "doc": {"text", "meta", ...}}
    - OLD (flat):        {"id", "text", "meta", ...}
    """
    doc = h.get("doc", h)
    hid = h.get("id", doc.get("id", "?"))
    text = doc.get("text", "")
    meta = doc.get("meta", {})
    score = h.get("score")
    return hid, text, meta, score


def main():
    embedder = SentenceEmbedder()

    texts = [d["text"] for d in DOCS]
    # Convert to float32 to keep FAISS happy
    vecs = np.asarray(embedder.embed_texts(texts), dtype="float32")

    store = FaissStore(dim=vecs.shape[1])
    store.index_docs(vecs, DOCS)

    query = "Which 2024 projects focused on water use efficiency?"
    q_vec = np.asarray(embedder.embed_query(query), dtype="float32")
    hits = store.search(q_vec, top_k=3)

    print(f"\n[bold]QUERY:[/bold] {query}")
    print("[bold]TOP HITS:[/bold]")
    if not hits:
        print("- No results. Your index is empty or your query embedding failed.")
        return

    for h in hits:
        hid, text, meta, score = unwrap_hit(h)
        if score is not None:
            print(f"- {hid} | {text} | meta={meta} | score={score:.3f}")
        else:
            print(f"- {hid} | {text} | meta={meta}")


if __name__ == "__main__":
    main()

