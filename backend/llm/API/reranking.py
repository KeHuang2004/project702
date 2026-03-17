from ..Rerank.reranker import Reranker


def reranking(query: str, retrieved_chunks: list[str]):
    r = Reranker()
    return r.rerank(query, retrieved_chunks)
