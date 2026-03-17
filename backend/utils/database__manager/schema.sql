-- 知识库数据库构建脚本

-- 创建知识库表
CREATE TABLE knowledge_bases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    files_list TEXT DEFAULT '[]',
    chunks_list TEXT DEFAULT '[]',
    total_size INTEGER DEFAULT 0 CHECK(total_size >= 0),
    created_at TEXT
);


-- 创建文件表
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_base_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,        -- 原始文件路径（必需）
    file_type TEXT,                 -- 文件类型 (txt, pdf, doc, etc.)
    file_size INTEGER,              -- 文件大小（字节）
    chunk_length INTEGER DEFAULT 0, -- 该文件的文本块长度
    overlap_count INTEGER DEFAULT 0, -- 该文件的文本块重叠长度
    segmentation_strategy TEXT,     -- 该文件的分割策略
    status TEXT DEFAULT 'pending',  -- 处理状态
    upload_at TEXT,                 -- 标记为 completed 的时间（北京时间文本）
    chunks_list TEXT DEFAULT '[]',  -- 已生成的 chunk ID 列表
    FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
);

-- 创建chunk表
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    knowledge_base_id INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    start_position INTEGER,
    end_position INTEGER,
    status TEXT,
    created_at TEXT,
    embed_at TEXT,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
);

-- 创建QApair表（存储最小实体为问答对）
CREATE TABLE qapairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL
);


-- 创建索引以提高查询性能
CREATE INDEX idx_files_kb_id ON files(knowledge_base_id);
CREATE INDEX idx_files_path ON files(file_path);
CREATE INDEX idx_chunks_file_id ON chunks(file_id);
CREATE INDEX idx_chunks_kb_id ON chunks(knowledge_base_id);
-- faiss_vector_id 字段已从 schema 中移除，取消对应索引

-- 数据库构建完成
SELECT 'Database created successfully!' as message;
