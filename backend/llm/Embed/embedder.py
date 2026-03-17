import requests
from typing import List
from config import Config


class Embedder:
    def __init__(self, embedding_model: str):
        # 使用固定的 embedding 模型名（由启动脚本统一设置为 'embedding__model'）
        cfg = getattr(Config, "EMBEDDING_SERVE", {})
        host = getattr(Config, "VLLM_HOST", "127.0.0.1")
        port = int(cfg.get("port", 0) or 0)
        self.endpoint = f"http://{host}:{port}/v1/embeddings"
        self._model_name = "embedding__model"

    def embed(self, texts: List[str]) -> List[List[float]]:
        payload = {"model": self._model_name, "input": texts}
        r = requests.post(self.endpoint, json=payload)
        return [
            d["embedding"] for d in sorted(r.json()["data"], key=lambda x: x["index"])
        ]
