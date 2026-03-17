import os
import numpy as np
import faiss
from ..Embed import Embedder


class Retriever:
    def __init__(self, faiss_index_path: str, embedding_model: str):
        self.index_path = os.path.join(faiss_index_path, "index.faiss")
        if not os.path.exists(self.index_path):
            raise FileNotFoundError(self.index_path)
        self.index = faiss.read_index(self.index_path)
        self.embedder = Embedder(embedding_model)

    def search(self, query: str, top_k: int):
        q = np.asarray(self.embedder.embed([query])[0], np.float32)[None, :]
        faiss.normalize_L2(q)
        distances, indices = self.index.search(q, top_k)
        return [
            (int(idx), float(dist))
            for dist, idx in zip(distances[0], indices[0])
            if idx >= 0
        ]
