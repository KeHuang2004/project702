import requests
from typing import List, Tuple
from requests import RequestException
from config import Config


class Reranker:
    def __init__(self):
        # 使用固定的 rerank 模型名 'rerank__model'，端点由配置的 port 拼接或由 RERANK_ENDPOINT 环境变量覆盖
        self.endpoint = getattr(Config, "RERANK_ENDPOINT", f"http://{getattr(Config,'VLLM_HOST','127.0.0.1')}:{getattr(Config,'RERANK_SERVE',{}).get('port',11510)}/v1/rerank")
        self.rerank_model = "rerank__model"

    def rerank(
        self, query: str, retrieved_chunks: List[str]
    ) -> List[Tuple[float, str]]:
        payload = {
            "model": self.rerank_model,
            "query": query,
            "documents": retrieved_chunks,
            "top_n": len(retrieved_chunks),
        }

        try:
            resp = requests.post(
                self.endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=getattr(Config, "API_TIMEOUT", 30),
            )
            resp.raise_for_status()
            data_json = resp.json()
            if "results" not in data_json:
                raise RequestException("Invalid rerank response: missing 'results'")
            data = data_json["results"]
        except Exception as e:
            raise RequestException(str(e))

        return [
            (float(item["relevance_score"]), item["document"]["text"]) for item in data
        ]
