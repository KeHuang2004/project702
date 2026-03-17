from ..Retrieve.retriever import Retriever


def retrieving(faiss_index_path: str, embedding_model: str, query: str, top_k: int):
    r = Retriever(
        faiss_index_path=faiss_index_path,
        embedding_model=embedding_model,
    )
    return r.search(query=query, top_k=top_k)
