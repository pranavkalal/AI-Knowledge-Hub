
import os
import json
from typing import Any, Dict, List

import pytest

from app.factory import build_pipeline


@pytest.fixture()
def mini_corpus():
    return [
        {
            "doc_id": "docA",
            "title": "Cotton Water Study 2021",
            "year": 2021,
            "text": "In 2021 the Cotton Water Study examined irrigation efficiency in cotton farms.",
        },
        {
            "doc_id": "docB",
            "title": "Pest Impact Review 2020",
            "year": 2020,
            "text": "The 2020 review analysed pest pressure and its impact on yield and profitability.",
        },
        {
            "doc_id": "docC",
            "title": "Fiber Quality Benchmark",
            "year": 2019,
            "text": "Benchmarking fibre strength and staple length was the focus in 2019.",
        },
    ]


class StubEmbedderAdapter:
    last_query: str = ""

    def __init__(self, model_name: str = "stub"):
        pass

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [[float(len(t))] for t in texts]

    def embed_query(self, text: str) -> List[float]:
        StubEmbedderAdapter.last_query = text.lower()
        return [float(len(text))]


class StubStoreAdapter:
    corpus: List[Dict[str, Any]] = []

    def __init__(self, *args, **kwargs):
        pass

    def _as_hit(self, doc: Dict[str, Any], score: float) -> Dict[str, Any]:
        chunk_id = f"{doc['doc_id']}_chunk0001"
        meta = {
            "id": chunk_id,
            "doc_id": doc["doc_id"],
            "title": doc["title"],
            "year": doc["year"],
            "text": doc["text"],
            "preview": doc["text"],
        }
        return {"id": chunk_id, "score": score, "metadata": meta}

    def _rank_docs(self) -> List[Dict[str, Any]]:
        query = StubEmbedderAdapter.last_query
        hits = []
        for doc in self.corpus:
            score = 0.2
            if str(doc["year"]) in query:
                score = 1.0
            elif any(word in query for word in ("impact", "effect")) and "impact" in doc["title"].lower():
                score = 0.9
            hits.append(self._as_hit(doc, score))
        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits

    def query(self, query_vector: List[float], k: int) -> List[Dict[str, Any]]:
        return self._rank_docs()[:k]

    def search_raw(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        StubEmbedderAdapter.last_query = query.lower()
        return self._rank_docs()[:top_k]

    def get_meta_map(self) -> Dict[str, Dict[str, Any]]:
        return {f"{doc['doc_id']}_chunk0001": self._as_hit(doc, 1.0)["metadata"] for doc in self.corpus}

    def get_metadata(self, chunk_id: str) -> Dict[str, Any]:
        return self.get_meta_map().get(chunk_id, {})


class StubLLM:
    def __init__(self, model: str, **kwargs):
        self.model = model

    def chat(self, system: str, user: str, temperature: float, max_tokens: int):
        if "2021" in user or "cotton water" in user.lower():
            answer = "Cotton Water Study 2021 investigated irrigation efficiency."
        else:
            answer = "The pest impact review analysed yield changes."
        usage = {"prompt_tokens": 10, "completion_tokens": 6}
        return answer, usage


class StubReranker:
    def rerank(self, query: str, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return hits


@pytest.fixture()
def stub_environment(monkeypatch, tmp_path, mini_corpus):
    StubStoreAdapter.corpus = mini_corpus

    monkeypatch.setattr("app.adapters.embed_bge.BGEEmbeddingAdapter", StubEmbedderAdapter)
    monkeypatch.setattr("app.adapters.vector_faiss.FaissStoreAdapter", StubStoreAdapter)
    monkeypatch.setattr("app.adapters.llm_ollama.OllamaAdapter", StubLLM)
    monkeypatch.setattr("app.adapters.llm_openai.OpenAIAdapter", StubLLM)
    monkeypatch.setattr("app.adapters.rerank_noop.NoopReranker", StubReranker)
    monkeypatch.setattr("app.adapters.rerank_bge.BGERerankerAdapter", lambda model_name=None: StubReranker())

    def write_config(path, orchestrator: str):
        config = {
            "orchestrator": orchestrator,
            "embedder": {"adapter": "stub", "model": "stub", "normalize": False},
            "vector_store": {"adapter": "stub", "path": "ignore", "ids": "ignore", "meta": "ignore"},
            "reranker": {"adapter": "none"},
            "llm": {"adapter": "ollama", "model": "stub", "temperature": 0.2, "max_output_tokens": 256},
            "retrieval": {
                "k": 2,
                "mode": "dense",
                "rerank": False,
                "filters": {},
                "use_multiquery": False,
                "use_compression": False,
            },
            "langchain": {"trace": False, "stream": False},
        }
        path.write_text(json.dumps(config))

    native_cfg = tmp_path / "runtime_native.json"
    lang_cfg = tmp_path / "runtime_lang.json"
    write_config(native_cfg, "native")
    write_config(lang_cfg, "langchain")

    return native_cfg, lang_cfg


def extract_titles(result: Dict[str, Any]) -> set:
    titles = set()
    for source in result.get("sources", []):
        title = source.get("title")
        if title:
            titles.add(title)
    return titles


def test_pipeline_parity(stub_environment):
    native_cfg, lang_cfg = stub_environment

    native_pipeline = build_pipeline(native_cfg)
    lang_pipeline = build_pipeline(lang_cfg)

    question = "What was studied in 2021?"
    native_out = native_pipeline.ask(question=question, k=2)
    lang_out = lang_pipeline.ask(question=question, k=2)

    titles_native = extract_titles(native_out)
    titles_lang = extract_titles(lang_out)

    assert titles_native & titles_lang, "Expected overlap in cited documents between pipelines"
