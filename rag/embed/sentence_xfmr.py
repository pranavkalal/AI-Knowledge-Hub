
print("DEBUG: loading sentence_xfmr.py")
print("DEBUG: about to define SentenceEmbedder")
# Minimal embedder using Sentence-Transformers
from sentence_transformers import SentenceTransformer

class SentenceEmbedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(list(texts), normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode([text], normalize_embeddings=True)[0].tolist()
