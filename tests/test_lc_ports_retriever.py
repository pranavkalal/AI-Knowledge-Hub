from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.langchain_adapters import PortsRetriever


class FakeStore:
    def __init__(self):
        self.meta = {
            "docA_chunk0000": {
                "id": "docA_chunk0000",
                "doc_id": "docA",
                "chunk_index": 0,
                "text": "Introduction to irrigation advances.",
                "title": "Doc A",
                "year": 2023,
                "page": 2,
            },
            "docA_chunk0001": {
                "id": "docA_chunk0001",
                "doc_id": "docA",
                "chunk_index": 1,
                "text": "Methods and results for soil moisture sensing.",
                "title": "Doc A",
                "year": 2023,
                "page": 3,
            },
            "docB_chunk0000": {
                "id": "docB_chunk0000",
                "doc_id": "docB",
                "chunk_index": 0,
                "text": "Banana fibre blends improve sustainability metrics.",
                "title": "Doc B",
                "year": 2022,
                "page": 5,
            },
            "docC_chunk0000": {
                "id": "docC_chunk0000",
                "doc_id": "docC",
                "chunk_index": 0,
                "text": "Historical practices recorded in 2010.",
                "title": "Doc C",
                "year": 2010,
                "page": 1,
            },
        }
        self.results = [
            {"id": "docA_chunk0001", "score": 0.92, "metadata": self.meta["docA_chunk0001"]},
            {"id": "docB_chunk0000", "score": 0.87, "metadata": self.meta["docB_chunk0000"]},
            {"id": "docA_chunk0000", "score": 0.85, "metadata": self.meta["docA_chunk0000"]},
            {"id": "docC_chunk0000", "score": 0.72, "metadata": self.meta["docC_chunk0000"]},
        ]

    def search_raw(self, query: str, top_k: int = 10):
        return self.results[:top_k]

    def get_meta_map(self):
        return self.meta

    def get_metadata(self, chunk_id: str):
        return self.meta.get(chunk_id)


def test_ports_retriever_stitches_neighbors():
    store = FakeStore()
    retriever = PortsRetriever(store=store, top_k=1, neighbors=1)

    docs = retriever._get_relevant_documents("irrigation")
    assert len(docs) == 1

    doc = docs[0]
    assert "Introduction to irrigation advances." in doc.page_content
    assert "Methods and results for soil moisture sensing." in doc.page_content
    assert doc.metadata["doc_id"] == "docA"
    assert doc.metadata["chunk_indices"] == [0, 1]


def test_ports_retriever_respects_filters():
    store = FakeStore()

    # Keyword filter should surface docB only
    retriever_kw = PortsRetriever(store=store, top_k=3, neighbors=0, contains=["banana"])
    docs_kw = retriever_kw._get_relevant_documents("sustainability")
    assert len(docs_kw) == 1
    assert docs_kw[0].metadata["doc_id"] == "docB"

    # Year range filter excludes docC (2010)
    retriever_year = PortsRetriever(store=store, top_k=3, neighbors=0, year_range=(2020, 2025))
    docs_year = retriever_year._get_relevant_documents("history")
    doc_ids = {d.metadata["doc_id"] for d in docs_year}
    assert "docA" in doc_ids
    assert "docC" not in doc_ids
