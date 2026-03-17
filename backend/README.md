
# 知识库后端 API 与数据库结构

本文档记录当前知识库后端提供的 API 列表，以及数据库表结构定义。

## API 列表（/api/v1）

### 知识库
- GET /knowledge-bases
- GET /knowledge-bases/<kb_id>
- POST /knowledge-bases
- PUT /knowledge-bases/<kb_id>
- DELETE /knowledge-bases/<kb_id>
- POST /knowledge-bases/<kb_id>/retrieve

### 文件
- GET /files
- GET /files/<file_id>
- PUT /files/<file_id>
- DELETE /files/<file_id>
- POST /files/<kb_id>
- GET /files/<file_id>/download
- POST /files/<kb_id>/process

### 文本块（Chunks）
- POST /chunks/retrieve/<kb_id>
- GET /chunks
- POST /chunks
- POST /chunks/embed
- POST /chunks/embedding
- GET /chunks/<chunk_id>
- PUT /chunks/<chunk_id>
- DELETE /chunks/<chunk_id>

### 聊天
- GET /chat
- POST /chat
- GET /chat/<session_id>
- PUT /chat/<session_id>
- DELETE /chat/<session_id>

### 问答对（QApairs）
- GET /qapairs
- POST /qapairs
- GET /qapairs/<qa_id>
- PUT /qapairs/<qa_id>
- DELETE /qapairs/<qa_id>

### 文本生成
- POST /generate

## 数据库表结构

### knowledge_bases
- id INTEGER PRIMARY KEY AUTOINCREMENT
- name TEXT UNIQUE NOT NULL
- description TEXT
- files_list TEXT DEFAULT '[]'
- chunks_list TEXT DEFAULT '[]'
- total_size INTEGER DEFAULT 0 CHECK(total_size >= 0)
- created_at TEXT

### files
- id INTEGER PRIMARY KEY AUTOINCREMENT
- knowledge_base_id INTEGER NOT NULL
- filename TEXT NOT NULL
- file_path TEXT NOT NULL
- file_type TEXT
- file_size INTEGER
- chunk_length INTEGER DEFAULT 0
- overlap_count INTEGER DEFAULT 0
- segmentation_strategy TEXT
- status TEXT DEFAULT 'pending'
- upload_at TEXT
- chunks_list TEXT DEFAULT '[]'
- FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE

### chunks
- id INTEGER PRIMARY KEY AUTOINCREMENT
- file_id INTEGER NOT NULL
- knowledge_base_id INTEGER NOT NULL
- chunk_text TEXT NOT NULL
- chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0)
- start_position INTEGER
- end_position INTEGER
- status TEXT
- created_at TEXT
- embed_at TEXT
- FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
- FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE

### qapairs
- id INTEGER PRIMARY KEY AUTOINCREMENT
- question TEXT NOT NULL
- answer TEXT NOT NULL

### 索引
- idx_files_kb_id ON files(knowledge_base_id)
- idx_files_path ON files(file_path)
- idx_chunks_file_id ON chunks(file_id)
- idx_chunks_kb_id ON chunks(knowledge_base_id)
