from pathlib import Path
import os
from typing import List

import numpy as np
import faiss

from ..Split.files_loader import FileLoader
from ..Split.splitter_factory import SplitterFactory
from ..Embed import Embedder


def storing(
    files,
    faiss_index_path,
    embedding_model,
    segmentation_strategy,
    chunk_length,
    overlap_count,
):
    Path(faiss_index_path).mkdir(parents=True, exist_ok=True)
    loader = FileLoader()
    texts = [loader.load_file(f["file_path"]) for f in files]
    file_ids = [f["file_id"] for f in files]
    splitter = SplitterFactory(
        segmentation_strategy, chunk_length, overlap_count, embedding_model
    )

    all_chunk_infos, file_chunk_counts = [], []
    for text in texts:
        chunk_infos, chunk_count = splitter.split_text(text)
        all_chunk_infos.extend(chunk_infos)
        file_chunk_counts.append(chunk_count)

    # 将所有 chunk 文本提取出来
    chunk_texts: List[str] = [chunk["chunk_text"] for chunk in all_chunk_infos]

    # 固定批大小为 10：每 10 个 chunk 发送一次嵌入请求，最后不足 20 个按一批处理
    BATCH_SIZE = 20

    # 嵌入器（按模型名路由到对应端点）
    embedder = Embedder(embedding_model)

    # 增量构建 FAISS 索引：如存在旧索引则在其尾部追加，否则新建
    index_path = os.path.join(faiss_index_path, "index.faiss")
    index = None
    dim_existing = None
    start_id = 0
    if os.path.exists(index_path):
        try:
            index = faiss.read_index(index_path)
            dim_existing = int(index.d)
            start_id = int(index.ntotal)
        except Exception as e:
            # 加载旧索引失败则抛错，避免覆盖
            raise RuntimeError(f"读取已有索引失败: {e}")

    dim = None
    next_id = start_id
    all_ids: List[int] = []

    for i in range(0, len(chunk_texts), BATCH_SIZE):
        batch_texts = chunk_texts[i : i + BATCH_SIZE]
        if not batch_texts:
            continue

        # 批量请求嵌入
        vecs = np.asarray(embedder.embed(batch_texts), dtype=np.float32)
        if vecs.ndim != 2 or vecs.shape[0] != len(batch_texts):
            raise ValueError("嵌入返回形状异常，无法继续构建索引")

        # 归一化向量（内积检索）
        faiss.normalize_L2(vecs)

        # 初始化/校验索引维度
        if dim is None:
            dim = int(vecs.shape[1])
            if dim_existing is not None and dim_existing != dim:
                raise ValueError(
                    f"索引维度不一致：已有 {dim_existing}，新增 {dim}，请确认知识库嵌入模型一致"
                )
            if index is None:
                index = faiss.IndexIDMap(faiss.IndexFlatIP(dim))

        # 为当前批生成连续 ID，并增量加入索引
        ids = np.arange(next_id, next_id + len(batch_texts), dtype="int64")
        index.add_with_ids(vecs, ids)
        all_ids.extend(ids.tolist())
        next_id += len(batch_texts)

    # 若本次没有任何向量（例如空文件），避免写入空索引
    if index is not None and len(all_ids) > 0:
        faiss.write_index(index, index_path)

    chunk_indices = all_ids

    file_results, offset = [], 0
    for file_id, chunk_count in zip(file_ids, file_chunk_counts):
        file_chunks = all_chunk_infos[offset : offset + chunk_count]
        file_chunk_indices = chunk_indices[offset : offset + chunk_count]
        chunks = []
        for info, idx in zip(file_chunks, file_chunk_indices):
            chunks.append(
                {
                    "chunk_text": info["chunk_text"],
                    "chunk_index": idx,
                    "start_position": info["start_position"],
                    "end_position": info["end_position"],
                    "file_id": file_id,
                }
            )
        file_results.append(
            {"file_id": file_id, "chunk_count": chunk_count, "chunks": chunks}
        )
        offset += chunk_count

    return {"file_results": file_results}
