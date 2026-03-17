### 1. 获取知识库列表

**接口地址**: `GET /api/v1/knowledge-bases`

**功能描述**: 获取所有的知识库列表，每个知识库展示其name，discripstion，create_date，document_count，total_size支持关键词搜索、分页查询和获取最近使用的知识库

**返回示例**:
```json

{

  "success": true,

  "message": "获取知识库列表成功",

  "data": {
### 2. 获取单个知识库详情（已移除）
**接口说明**: 后端已移除通过路径参数获取单条知识库的接口（`GET /api/v1/knowledge-bases/{kb_id}`）。

若需要获取单个知识库详情，请调用 `GET /api/v1/knowledge-bases` 获取列表后在客户端筛选出对应 `id` 的项。

        "id": 1,

        "name": "技术文档库",
### 4. 更新知识库

**接口地址**: `PUT /api/v1/knowledge-bases`

**功能描述**: 更新指定知识库的名称和描述（仅允许更新 name 和 description）。

注意：更新接口不再通过 URL 路径参数接收 ID。必须在请求体中提供 `kb_id` 或 `id` 字段来指定要更新的知识库。

请求示例：
```bash
PUT /api/v1/knowledge-bases

Content-Type: application/json

{
	"kb_id": 2,
	"name": "产品文档库v2",
	"description": "更新后的产品文档库描述"
}
```
### 2. 获取单个知识库详情
**接口地址**: `GET /api/v1/knowledge-bases/{kb_id}`

### 5. 删除知识库

**接口地址**: `DELETE /api/v1/knowledge-bases`

**功能描述**: 删除指定的知识库及其所有相关数据。

注意：删除接口不再通过 URL 路径参数接收 ID。必须在请求体中提供 `kb_id` 或 `id` 字段来指定要删除的知识库。

请求示例：
```bash
DELETE /api/v1/knowledge-bases

Content-Type: application/json

{
	"kb_id": 2
}
```

**成功响应**:
```json
{
	"success": true,
	"message": "知识库删除成功",
	"data": null
}
```
      
      "updated_at": "2024-01-15T14:30:00Z",
        
      "total_size": 123456,

    },

    }

  }

}

```

### 3. 创建知识库

  

**接口地址**: `POST /api/v1/knowledge-bases`

  

**功能描述**: 创建新的知识库，输入名称、描述，选择embedding模型

**请求示例**：
```bash

POST /api/v1/knowledge-bases

  

{

  "name": "产品文档库",

  "description": "存储产品相关文档和帮助信息",

  "embedding_model": "text-embedding-ada-002",
  
}

```

### 4. 更新知识库

  

**接口地址**: `PUT /api/v1/knowledge-bases/{kb_id}`

  

**功能描述**: 更新指定知识库的名称和描述

**请求示例**：
```bash

PUT /api/v1/knowledge-bases/2

Content-Type: application/json

  

{

  "name": "产品文档库v2",

  "description": "更新后的产品文档库描述",

}

```

### 5. 删除知识库

  

**接口地址**: `DELETE /api/v1/knowledge-bases/{kb_id}`

  

**功能描述**: 删除指定的知识库及其所有相关数据

  
**成功响应**:
```json

{

  "success": true,

  "message": "知识库删除成功",

  "data": null

}

```

### 6.获取单个知识库的所有文件

**接口地址**: `GET /api/v1/knowledge-bases/{kb_id}/files`

**功能描述**: 获取某知识库所有的文件，展示所有文档名称、分段策略、块长度、重叠长度、大小、类型、上传时间。



**返回示例**:
```json

{

  "success": true,

  "message": "获取知识库详情成功",

  "data": {

    "id": 1,

    "name": "技术文档库",

    "description": "存储技术相关文档",
    
    "files": [

      {

        "id": 1,

        "filename": "技术文档.pdf",

        "file_type": "pdf",

        "file_size": 2048576,
        
        "segmentation_strategy":"语义分割",
        
        "chunk_length":512,
        
	    "overlap_length":1024,

        "created_at": "2024-01-01T10:00:00Z",

      }
	],

  }

}
```

### 7. 获取单个文件详情

  

**接口地址**: `GET /api/v1/knowledge-bases/{kb_id}/files/{file_id}`

  

**功能描述**: 获取指定文件的详细信息


**返回示例**:
```json

{

  "success": true,

  "message": "获取文件详情成功",

  "data": {

    "id": 1,

    "filename": "技术文档.pdf",

    "file_type": "pdf",

    "file_size": 2048576,
    
    "segmentation_strategy":"语义分割",
        
    "chunk_length":512,
        
	"overlap_length":1024,

    "created_at": "2024-01-01T10:00:00Z",

    "chunks": {

      "items": [

        {

          "id": 1,

          "content": "这是文档的第一段内容...",

          "chunk_index": 0,

          "token_count": 150,

        }

      ],

     "total": 15

    },

  }

}

```

### 8. 上传文件

  

**接口地址**: `POST /api/v1/knowledge-bases/{kb_id}/files`

  

**功能描述**: 上传文件到指定知识库


**请求示例**



```bash

# 使用JavaScript FormData

const formData = new FormData();

formData.append('file', fileInput.files[0]);

formData.append('knowledge_base_id', '1');

  

fetch('POST /api/v1/knowledge-bases/{kb_id}/files', {

  method: 'POST',

  body: formData

});

```

**成功响应**:
```json

{

  "success": true,

  "message": "文件上传成功",

  "data": {

    "id": 2,

    "filename": "新文档.pdf",

    "file_size": 1024768,

    "status": "pending",

    "created_at": "2024-01-16T10:00:00Z",


  }

}

```

  
### 9. 删除文件

  

**接口地址**: `DELETE /api/v1/knowledge-bases/{kb_id}/files/{file_id}`

  

**功能描述**: 删除指定文件

**成功响应**:
```json

{

  "success": true,

  "message": "文件删除成功",

  "data": null

}

```
