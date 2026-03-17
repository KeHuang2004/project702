-- 演示数据插入脚本

-- 注意：schema 中无 generation_model 与 faiss_index_path 字段，移除之
INSERT INTO knowledge_bases (name, description, total_size, created_at) 
VALUES 
    ('Python技术文档库', '存储Python相关的技术文档和教程', 0, '2024年01月15日10时00分00秒'),  -- 初始总大小为0
    ('机器学习知识库', '包含机器学习算法和实践案例', 0, '2024年01月10日09时30分00秒'),   -- 初始总大小为0
    ('公司内部文档库', '存储公司内部政策和流程文档', 0, '2023年12月20日08时45分00秒'); -- 初始总大小为0

INSERT INTO files (knowledge_base_id, filename, file_path, file_type, file_size, chunk_length, overlap_count, segmentation_strategy, status, upload_at, chunks_list) 
VALUES 
    -- Python技术文档库的文件
    (1, 'python_basics.txt', '/docs/python/python_basics.txt', 'txt', 15200, 64, 0, 'SemanticChunker', 'completed', '2024年01月15日11时00分00秒', '[]'),
    
    (1, 'python_advanced.txt', '/docs/python/python_advanced.txt', 'txt', 28400, 64, 1, 'SemanticChunker', 'completed', '2024年01月16日14时45分00秒', '[]'),
    
    (1, 'django_tutorial.pdf', '/docs/python/django_tutorial.pdf', 'pdf', 1568000, 128, 2, 'SemanticChunker', 'processing', NULL, '[]'),
    -- demo data removed
    '文件数量' as item,
    COUNT(*) as count
FROM files
UNION ALL
SELECT 
    'Chunk数量' as item,
    COUNT(*) as count
FROM chunks;

-- 显示每个知识库的详细统计
SELECT 
    kb.name as 知识库名称,
    COUNT(DISTINCT f.id) as 文件数量,
    COUNT(c.id) as Chunk数量,
    'N/A' as 嵌入模型
FROM knowledge_bases kb
LEFT JOIN files f ON kb.id = f.knowledge_base_id
LEFT JOIN chunks c ON kb.id = c.knowledge_base_id
GROUP BY kb.id, kb.name
ORDER BY kb.id;
