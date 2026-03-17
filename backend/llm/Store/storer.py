import os
import numpy as np
import faiss
from ..Embed import Embedder


class Storer:
    def __init__(self, faiss_index_path: str, embedding_model: str):
        os.makedirs(faiss_index_path, exist_ok=True)
        self.index_path = os.path.join(faiss_index_path, "index.faiss")
        self.embedder = Embedder(embedding_model)

    def add_chunks(self, chunks):
        x = np.asarray(self.embedder.embed(chunks), np.float32)
        x /= np.linalg.norm(x, axis=1, keepdims=True)
        dim = x.shape[1]
        index = faiss.IndexIDMap(faiss.IndexFlatIP(dim))
        ids = np.arange(0, x.shape[0], dtype="int64")
        index.add_with_ids(x, ids)
        faiss.write_index(index, self.index_path)
        return ids.tolist(), dim
