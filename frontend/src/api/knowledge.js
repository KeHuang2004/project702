import request from '@/utils/request'

// ==================== 知识库相关API ====================

/**
 * 获取知识库文件处理状态
 * 注意：api.md 中没有专门的处理状态API，使用知识库详情API获取文件状态
 * @param {string|number} kbId - 知识库ID
 * @returns {Promise} 处理状态信息
 */

// 知识库统计接口已移除；前端用多个 GET 自行汇总


export function getProcessingStatus(kbId) {
  console.log('🔍 获取知识库处理状态，ID:', kbId)

  if (!kbId) {
    const error = new Error('知识库ID不能为空')
    console.error('❌ 参数验证失败:', error.message)
    return Promise.reject(error)
  }
  // 使用 files_list + 按文件ID拉取状态
  return getKnowledgeBaseAttributes(kbId, ['files_list']).then(async res => {
    const ids = res?.data?.files_list || []
    const fileStatuses = await Promise.all((ids || []).map(fid =>
      getFileAttributes(fid, ['filename', 'status', 'file_size']).then(r => ({
        fileId: fid,
        fileName: r?.data?.filename || '',
        status: r?.data?.status || 'completed',
        progress: (r?.data?.status || '').toLowerCase() === 'completed' ? 100 : 0,
        chunksCount: 0,
        errorMessage: ''
      })).catch(() => ({
        fileId: fid,
        fileName: '',
        status: 'failed',
        progress: 0,
        chunksCount: 0,
        errorMessage: '获取状态失败'
      }))
    ))

    const processingStatusResponse = {
      success: true,
      message: '获取处理状态成功',
      data: {
        knowledge_base_id: kbId,
        total_files: ids.length,
        fileStatuses
      }
    }
    console.log('🔄 转换后的处理状态响应:', processingStatusResponse)
    return processingStatusResponse
  }).catch(error => {
    console.error('❌ 获取处理状态失败:', error)
    throw new Error('获取处理状态失败: ' + (error.message || '未知错误'))
  })
}

/**
 * 提交知识库创建完成
 * 注意：api.md 中没有专门的提交API，这里只是更新知识库状态或获取详情确认
 * @param {Object} data - 提交数据
 * @param {string|number} data.knowledge_base_id - 知识库ID
 * @returns {Promise} 提交结果
 */
export function submitKnowledgeBase(data) {
  console.log('🚀 提交知识库创建完成，数据:', data)

  if (!data || !data.knowledge_base_id) {
    const error = new Error('知识库ID不能为空')
    console.error('❌ 参数验证失败:', error.message)
    return Promise.reject(error)
  }

  const kbId = data.knowledge_base_id

  // api.md 中没有专门的提交API，后端已移除 /knowledge-bases/{id} 单条 GET。
  // 改为请求列表并在前端筛选出指定 ID 的项以确认存在与状态。
  return getKnowledgeBaseList().then(response => {
    console.log('📋 知识库列表响应（用于提交确认）:', response)

    const kb = (response?.data?.knowledge_bases || []).find(k => String(k.id) === String(kbId))
    if (kb) {
      // 返回提交成功的格式
      return {
        success: true,
        message: '知识库创建完成',
        data: {
          id: response.data.id,
          name: response.data.name,
          description: response.data.description,
          document_count: response.data.document_count || 0,
          total_size: response.data.total_size || 0,
          created_at: response.data.created_at,
          updated_at: response.data.updated_at,
          status: 'completed'
        }
      }
      }

    throw new Error('知识库不存在或无法访问')
  }).catch(error => {
    console.error('❌ 提交知识库失败:', error)
    throw new Error('提交知识库失败: ' + (error.message || '未知错误'))
  })
}

// ==================== api.md 中已有的API函数（确保完整性） ====================

/**
 * 获取知识库列表 - 已存在，确保参数完整
 */
export function getKnowledgeBaseList(params = {}) {
  console.log('🔍 获取知识库ID列表')
  return request({
    url: '/api/v1/knowledge-bases',
    method: 'get',
    params: { ...params }
  }).then(response => {
    console.log('📊 知识库ID列表响应:', response)
    return response
  }).catch(error => {
    console.error('❌ 获取知识库ID列表失败:', error)
    throw error
  })
}

// 获取知识库单字段
export function getKnowledgeBaseAttribute(kbId, attr) {
  if (!attr) return Promise.reject(new Error('缺少属性名'))
  return request({
    url: `/api/v1/knowledge-bases/${kbId}?attribute=${encodeURIComponent(attr)}`,
    method: 'get'
  })
}

// 获取知识库多个字段：attr 可为数组或逗号分隔字符串
export function getKnowledgeBaseAttributes(kbId, attrs) {
  if (!attrs || (Array.isArray(attrs) && attrs.length === 0)) {
    return Promise.reject(new Error('缺少属性名'))
  }
  const attrParam = Array.isArray(attrs) ? attrs.join(',') : String(attrs)
  return request({
    url: `/api/v1/knowledge-bases/${kbId}?attribute=${encodeURIComponent(attrParam)}`,
    method: 'get'
  })
}

// 获取多个知识库的多个字段
export function getKnowledgeBaseAttributesForIds(ids, attrs) {
  if (!ids || (Array.isArray(ids) && ids.length === 0)) {
    return Promise.reject(new Error('缺少知识库ID'))
  }
  if (!attrs || (Array.isArray(attrs) && attrs.length === 0)) {
    return Promise.reject(new Error('缺少属性名'))
  }
  const idsParam = Array.isArray(ids) ? ids.join(',') : String(ids)
  const attrParam = Array.isArray(attrs) ? attrs.join(',') : String(attrs)
  return request({
    url: `/api/v1/knowledge-bases/${encodeURIComponent(idsParam)}?attribute=${encodeURIComponent(attrParam)}`,
    method: 'get'
  })
}

// 获取知识库基础信息（按要求逐字段 attr 调用）
export async function getKnowledgeBaseBasics(kbId) {
  const attrs = ['name', 'description', 'total_size', 'created_at']
  const res = await getKnowledgeBaseAttributes(kbId, attrs)
  const data = res?.data || {}
  return { id: kbId, ...data }
}

// 获取知识库基础信息列表，支持分页
export async function getKnowledgeBaseListWithBasics(page = 1, pageSize = 6) {
  const res = await getKnowledgeBaseList()
  const allIds = res?.data?.ids || []
  
  // 按ID降序排序（ID越大越新）
  const sortedIds = [...allIds].sort((a, b) => b - a)
  
  // 计算当前页的ID
  const start = (page - 1) * pageSize
  const end = start + pageSize
  const pageIds = sortedIds.slice(start, end)
  
  if (pageIds.length === 0) {
    return { items: [], total: allIds.length, page, pageSize }
  }
  
  // 获取当前页的属性
  const attrs = ['name', 'description', 'total_size', 'created_at']
  const resAttrs = await getKnowledgeBaseAttributesForIds(pageIds, attrs)
  const data = resAttrs?.data || null
  let items = []
  if (Array.isArray(data?.items)) {
    items = data.items
  } else if (data && typeof data === 'object') {
    items = [data]
  }

  const itemsWithIds = items.map((item, idx) => ({
    id: pageIds[idx],
    ...item
  }))
  
  return { items: itemsWithIds, total: allIds.length, page, pageSize }
}

/**
 * 获取知识库详情：GET /knowledge-bases/<id>
 */
export function getKnowledgeBaseDetail(kbId) {
  console.log('🔍 获取知识库详情，ID:', kbId)
  return request({
    url: `/api/v1/knowledge-bases/${kbId}`,
    method: 'get'
  }).then(response => {
    if (response && response.success) return response
    throw new Error(response?.message || '获取知识库详情失败')
  }).catch(error => {
    console.error('❌ 获取知识库详情失败:', error)
    throw error
  })
}

/**
 * 创建知识库 - 已存在，确保URL和参数正确
 */
export function createKnowledgeBase(data) {
  console.log('🚀 创建知识库，数据:', data)
  return request({
    url: '/api/v1/knowledge-bases', // 按照 api.md: POST /api/v1/knowledge-bases
    method: 'post',
    data: {
      name: data.name,
      description: data.description
    }
  }).then(response => {
    console.log('✅ 创建知识库成功:', response)
    return response
  }).catch(error => {
    console.error('❌ 创建知识库失败:', error)
    throw error
  })
}

/**
 * 单字段更新知识库：PUT /knowledge-bases/<id>?attribute=<field>，Body为新值
 */
export function updateKnowledgeBaseField(kbId, attr, value) {
  if (!attr) {
    return Promise.reject(new Error('缺少更新字段'))
  }
  return request({
    url: `/api/v1/knowledge-bases/${kbId}?attribute=${encodeURIComponent(attr)}`,
    method: 'put',
    data: value
  })
}

/**
 * 更新知识库：支持多字段一次性提交
 */
export async function updateKnowledgeBase(kbId, data) {
  console.log('🔄 更新知识库（多字段一次请求）ID:', kbId, '数据:', data)
  const payload = data || {}
  const attrs = Object.keys(payload)
  if (attrs.length === 0) {
    throw new Error('无可更新字段')
  }
  return request({
    url: `/api/v1/knowledge-bases/${kbId}?attribute=${encodeURIComponent(attrs.join(','))}`,
    method: 'put',
    data: payload
  })
}

/**
 * 删除知识库 - 已存在，确保URL正确
 */
export function deleteKnowledgeBase(kbId) {
  console.log('🗑️ 删除知识库，ID:', kbId)
  return request({
  url: `/api/v1/knowledge-bases/${kbId}`, // 按后端要求使用路径参数
  method: 'delete'
  }).then(response => {
    console.log('✅ 删除知识库成功:', response)
    return response
  }).catch(error => {
    console.error('❌ 删除知识库失败:', error)
    throw error
  })
}

export function deleteKnowledgeBases(kbIds) {
  if (!kbIds || (Array.isArray(kbIds) && kbIds.length === 0)) {
    return Promise.reject(new Error('缺少知识库ID'))
  }
  const idsParam = Array.isArray(kbIds) ? kbIds.join(',') : String(kbIds)
  console.log('🗑️ 批量删除知识库:', idsParam)
  return request({
    url: `/api/v1/knowledge-bases/${idsParam}`,
    method: 'delete'
  }).then(response => {
    console.log('✅ 批量删除知识库成功:', response)
    return response
  }).catch(error => {
    console.error('❌ 批量删除知识库失败:', error)
    throw error
  })
}

/**
 * 获取知识库的所有文件 - 已存在，确保URL正确
 */
export function getKnowledgeBaseFiles(kbId, params = {}) {
  console.log('📁 获取知识库文件列表，ID:', kbId, '参数:', params)
  return request({
    url: `/api/v1/files/${kbId}`, // 按照 api.md: GET /api/v1/files/{kb_id}
    method: 'get',
    params: {
      ...params
    }
  }).then(response => {
    console.log('📊 文件列表API响应:', response)
    return response
  }).catch(error => {
    console.error('❌ 获取文件列表失败:', error)
    throw error
  })
}

/**
 * 获取单个文件详情 - 已存在，确保URL正确
 */
export function getFileDetail(fileId) {
  console.log('📄 获取文件详情:', { fileId })
  return request({
    url: `/api/v1/files/${fileId}`,
    method: 'get'
  }).then(response => {
    console.log('📋 文件详情API响应:', response)
    return response
  }).catch(error => {
    console.error('❌ 获取文件详情失败:', error)
    throw error
  })
}

// 获取文件多个字段：支持多属性查询
export function getFileAttributes(fileId, attrs) {
  if (!fileId) return Promise.reject(new Error('缺少文件ID'))
  if (!attrs || (Array.isArray(attrs) && attrs.length === 0)) {
    return Promise.reject(new Error('缺少属性名'))
  }
  const attrParam = Array.isArray(attrs) ? attrs.join(',') : String(attrs)
  return request({
    url: `/api/v1/files/${fileId}?attribute=${encodeURIComponent(attrParam)}`,
    method: 'get'
  })
}

// 获取多个文件的多个字段
export function getFileAttributesForIds(fileIds, attrs) {
  if (!fileIds || (Array.isArray(fileIds) && fileIds.length === 0)) {
    return Promise.reject(new Error('缺少文件ID'))
  }
  if (!attrs || (Array.isArray(attrs) && attrs.length === 0)) {
    return Promise.reject(new Error('缺少属性名'))
  }
  const idsParam = Array.isArray(fileIds) ? fileIds.join(',') : String(fileIds)
  const attrParam = Array.isArray(attrs) ? attrs.join(',') : String(attrs)
  return request({
    url: `/api/v1/files/${encodeURIComponent(idsParam)}?attribute=${encodeURIComponent(attrParam)}`,
    method: 'get'
  })
}

// 获取文本块多个字段：支持多属性查询
export function getChunkAttributes(chunkId, attrs) {
  if (!chunkId) return Promise.reject(new Error('缺少文本块ID'))
  if (!attrs || (Array.isArray(attrs) && attrs.length === 0)) {
    return Promise.reject(new Error('缺少属性名'))
  }
  const attrParam = Array.isArray(attrs) ? attrs.join(',') : String(attrs)
  return request({
    url: `/api/v1/chunks/${chunkId}?attribute=${encodeURIComponent(attrParam)}`,
    method: 'get'
  })
}

// 获取多个文本块的多个字段
export function getChunkAttributesForIds(chunkIds, attrs) {
  if (!chunkIds || (Array.isArray(chunkIds) && chunkIds.length === 0)) {
    return Promise.reject(new Error('缺少文本块ID'))
  }
  if (!attrs || (Array.isArray(attrs) && attrs.length === 0)) {
    return Promise.reject(new Error('缺少属性名'))
  }
  const idsParam = Array.isArray(chunkIds) ? chunkIds.join(',') : String(chunkIds)
  const attrParam = Array.isArray(attrs) ? attrs.join(',') : String(attrs)
  return request({
    url: `/api/v1/chunks/${encodeURIComponent(idsParam)}?attribute=${encodeURIComponent(attrParam)}`,
    method: 'get'
  })
}

export function deleteChunks(chunkIds) {
  if (!chunkIds || (Array.isArray(chunkIds) && chunkIds.length === 0)) {
    return Promise.reject(new Error('缺少文本块ID'))
  }
  const idsParam = Array.isArray(chunkIds) ? chunkIds.join(',') : String(chunkIds)
  console.log('🗑️ 批量删除文本块:', idsParam)
  return request({
    url: `/api/v1/chunks/${idsParam}`,
    method: 'delete'
  }).then(response => {
    console.log('✅ 批量删除文本块成功:', response)
    return response
  }).catch(error => {
    console.error('❌ 批量删除文本块失败:', error)
    throw error
  })
}

// 获取单个文件的状态，兼容旧签名保留知识库ID参数
export function getFileStatus(_kbId, fileId) {
  if (!fileId) {
    return Promise.reject(new Error('缺少文件ID'))
  }
  return getFileAttributes(fileId, ['status'])
}

/**
 * 上传文件到知识库 - 已存在，确保URL正确
 */
export const uploadFilesToKnowledgeBase = async (knowledgeBaseId, files) => {
  try {
    console.log('API: 开始上传文件到知识库', {
      knowledgeBaseId,
      knowledgeBaseIdType: typeof knowledgeBaseId,
      filesCount: files.length
    })

    // 验证参数
    if (!knowledgeBaseId || knowledgeBaseId === 'undefined' || knowledgeBaseId === 'null') {
      throw new Error('知识库ID不能为空或无效')
    }

    if (!files || files.length === 0) {
      throw new Error('文件列表不能为空')
    }


    // 创建FormData
    const formData = new FormData()

    // 确保知识库ID是有效的数字或字符串
    const validKbId = String(knowledgeBaseId).trim()
    if (!validKbId || validKbId === 'undefined' || validKbId === 'null') {
      throw new Error('知识库ID格式无效')
    }

    console.log('使用的知识库ID:', validKbId)

  // 仅上传文件本身；kb_id 通过路径参数传递

    // 添加文件 - 使用 'files' 作为字段名（复数形式）
    files.forEach((file, index) => {
      console.log(`添加文件 ${index + 1}:`, {
        name: file.name,
        size: file.size,
        type: file.type
      })
      formData.append('files', file, file.name)
    })

    // 打印FormData内容进行调试
    console.log('FormData 内容:')
    for (let [key, value] of formData.entries()) {
      if (value instanceof File) {
        console.log(`${key}: File(${value.name}, ${value.size} bytes)`)
      } else {
        console.log(`${key}: ${value}`)
      }
    }

    // 发送请求
    const response = await request({
      url: `/api/v1/files/${validKbId}`,
      method: 'post',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.lengthComputable) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          console.log(`上传进度: ${percentCompleted}%`)
        }
      }
    })

    console.log('API: 文件上传响应', response)
    return response

  } catch (error) {
    console.error('API: 文件上传失败', error)

    // 处理不同类型的错误
    if (error.response) {
      // 服务器响应了错误状态码
      const { status, data } = error.response
      console.error('HTTP错误:', { status, data })

      if (status === 400) {
        // 400错误通常是参数问题
        const errorMsg = data?.message || data?.error || '请求参数错误'
        throw new Error(errorMsg)
      } else if (status === 404) {
        throw new Error('知识库不存在，请检查知识库ID')
      } else {
        throw new Error(data?.message || `服务器错误 (${status})`)
      }
    } else if (error.request) {
      // 请求发出但没有收到响应
      console.error('网络错误:', error.request)
      throw new Error('网络连接失败，请检查网络状态')
    } else {
      // 其他错误
      console.error('请求配置错误:', error.message)
      throw error
    }
  }
}

// 单文件顺序上传（已废弃，改为批量上传）

/**
 * 删除文件 - 已存在，确保URL正确
 */
export function deleteFile(fileId, deletePhysical = false) {
  console.log('🗑️ 删除文件:', { fileId, deletePhysical })
  return request({
    url: `/api/v1/files/${fileId}`,
    method: 'delete',
    params: {
      delete_physical: deletePhysical
    }
  }).then(response => {
    console.log('✅ 删除文件成功:', response)
    return response
  }).catch(error => {
    console.error('❌ 删除文件失败:', error)
    throw error
  })
}

export function deleteFiles(fileIds, deletePhysical = false) {
  if (!fileIds || (Array.isArray(fileIds) && fileIds.length === 0)) {
    return Promise.reject(new Error('缺少文件ID'))
  }
  const idsParam = Array.isArray(fileIds) ? fileIds.join(',') : String(fileIds)
  console.log('🗑️ 批量删除文件:', { fileIds: idsParam, deletePhysical })
  return request({
    url: `/api/v1/files/${idsParam}`,
    method: 'delete',
    params: {
      delete_physical: deletePhysical
    }
  }).then(response => {
    console.log('✅ 批量删除文件成功:', response)
    return response
  }).catch(error => {
    console.error('❌ 批量删除文件失败:', error)
    throw error
  })
}

/**
 * 下载文件
 * GET /api/v1/files/<file_id>/download
 */
export function downloadFile(fileId) {
  if (!fileId) {
    return Promise.reject(new Error('缺少文件ID'))
  }
  return request({
    url: `/api/v1/files/${fileId}/download`,
    method: 'get',
    responseType: 'blob'
  })
}

/**
 * 检索知识库文本块（新接口）
 * @param {number|string} kbId 路径参数：知识库ID
 * @param {{query:string, top_k?:number, threshold?:number}} body 请求体
 */
export function retrieveChunks(kbId, body) {
  console.log('检索文本块（POST 新接口）:', { kbId, body })

  const payload = {
    query: body?.query,
    top_k: body?.top_k ?? 5,
    threshold: body?.threshold ?? body?.score_threshold ?? 0.5,
  }

  return request({
    url: `/api/v1/knowledge-bases/${kbId}/retrieve`,
    method: 'post',
    data: payload,
  }).then(response => {
    console.log('文本块检索API响应:', response)
    return response
  }).catch(error => {
    console.error('❌ 检索文本块失败:', error)
    throw error
  })
}

// 获取文件的文本块状态统计
export function getChunkStatus(fileId) {
  return request({
    url: `/api/v1/chunks/status/${fileId}`,
    method: 'get'
  })
}

// 显式启动知识库文件处理（切分+嵌入）
export function startKnowledgeBaseProcessing(kbId, chunkSettings = {}) {
  console.log('启动知识库处理:', { kbId, chunkSettings })
  return request({
    url: `/api/v1/files/${kbId}/process`,
    method: 'post',
    data: {
      chunk_length: chunkSettings.chunkSize,
      chunk_overlap: chunkSettings.chunkOverlap,
      segmentation_strategy: chunkSettings.strategy,
    },
  })
}

// 新增：按文件ID切分文本块
export function splitChunksByFiles(fileIds, chunkSettings = {}) {
  if (!fileIds || (Array.isArray(fileIds) && fileIds.length === 0)) {
    return Promise.reject(new Error('缺少文件ID'))
  }
  const ids = Array.isArray(fileIds) ? fileIds : [fileIds]
  return request({
    url: '/api/v1/chunks',
    method: 'post',
    data: {
      file_ids: ids,
      chunk_length: chunkSettings.chunkSize,
      chunk_overlap: chunkSettings.chunkOverlap,
      segmentation_strategy: chunkSettings.strategy,
    }
  })
}

// 新增：列出文本块（支持跨知识库），默认 completed 排前
export function listChunks(params = {}) {
  const query = {
    kb_id: params.kbId ?? params.kb_id,
    status: params.status ?? 'completed',
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
  }
  return request({
    url: '/api/v1/chunks',
    method: 'get',
    params: query,
  })
}

// 新增：批量嵌入文本块
export function embedChunks(chunkIds, embeddingModel) {
  return request({
    url: '/api/v1/chunks/embed',
    method: 'post',
    data: {
      chunk_ids: Array.isArray(chunkIds) ? chunkIds : [],
      embedding_model: embeddingModel,
    },
  })
}

// 获取网页最新文档（简化抓取）
export function crawlLatestDocuments(payload = {}) {
  return request({
    url: '/api/v1/files/latest-docs',
    method: 'post',
    data: {
      url: payload.url,
      source_type: payload.source_type,
      count: payload.count,
      date: payload.date,
      date_range: payload.date_range,
    },
  })
}

export function fetchLatestDocumentPdf(previewUrl) {
  if (!previewUrl) {
    return Promise.reject(new Error('缺少预览链接'))
  }

  return request({
    url: '/api/v1/files/latest-docs/proxy',
    method: 'get',
    params: {
      url: previewUrl,
    },
    responseType: 'blob',
  })
}
