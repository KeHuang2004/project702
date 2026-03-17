from typing import Any, Dict, List, Tuple
import numpy as np


from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    TokenTextSplitter,
)
from langchain_experimental.text_splitter import SemanticChunker

from ..Embed import Embedder



class SplitterFactory:
    def __init__(
        self,
        segmentation_strategy: str,
        chunk_length: int,
        overlap_count: int,
        embedding_model: str,
    ):
        self.segmentation_strategy = segmentation_strategy
        self.chunk_length = chunk_length
        self.overlap_count = overlap_count
        self.embedding_model = embedding_model

    def split_text(self, text: str) -> Tuple[List[Dict[str, Any]], int]:
        if self.segmentation_strategy == "recursive_character":
            chunks = self._recursive_character_split(text)
        elif self.segmentation_strategy == "token_text":
            chunks = self._token_text_split(text)
        elif self.segmentation_strategy == "SemanticChunker":
            chunks = self._semantic_split(text)
        else:
            raise ValueError(f"不支持的分割策略: {self.segmentation_strategy}")

        chunk_infos = []
        current_pos = 0
        for i, chunk_text in enumerate(chunks):
            start_pos = text.find(chunk_text, current_pos)
            if start_pos == -1:
                start_pos = current_pos
            end_pos = start_pos + len(chunk_text)
            chunk_infos.append(
                {
                    "chunk_index": i,
                    "start_position": start_pos,
                    "end_position": end_pos,
                    "chunk_text": chunk_text,
                }
            )
            current_pos = start_pos + len(chunk_text) - self.overlap_count
            if current_pos < 0:
                current_pos = 0
        return chunk_infos, len(chunks)

    def _recursive_character_split(self, text: str) -> List[str]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_length,
            chunk_overlap=self.overlap_count,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )
        return splitter.split_text(text)

    def _token_text_split(self, text: str) -> List[str]:
        splitter = TokenTextSplitter(
            chunk_size=self.chunk_length,
            chunk_overlap=self.overlap_count,
        )
        return splitter.split_text(text)

    def _semantic_split(self, text: str) -> List[str]:
        embedder = Embedder(self.embedding_model)

        class LocalEmbeddings:
            """让 SemanticChunker 能使用我们的 Embedder"""

            def embed_documents(self, docs: List[str]) -> List[List[float]]:
                return embedder.embed(docs)

        embeddings = LocalEmbeddings()
        splitter = SemanticChunker(
            embeddings=embeddings,
            buffer_size=self.overlap_count,
            min_chunk_size=self.chunk_length,
        )
        return splitter.split_text(text)
