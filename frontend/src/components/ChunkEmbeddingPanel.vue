<template>
  <div class="chunk-embedding-panel">
    <el-card class="list-card">
      <template #header>
        <div class="card-header">
          <span>选择要嵌入的文本块</span>
          <div class="header-actions">
            <span>已选 {{ selectedIds.length }} / {{ total }}</span>
            <el-button size="small" @click="selectAll">全选全部</el-button>
            <el-button size="small" @click="clearSelection" :disabled="selectedIds.length === 0">清空选择</el-button>
          </div>
        </div>
      </template>

      <el-table
        ref="tableRef"
        :data="filteredChunks"
        style="width: 100%"
        height="50vh"
        :row-key="row => row.id"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column label="内容预览(前20字)" min-width="260">
          <template #default="scope">
            <el-tooltip
              v-if="scope.row.chunk_text"
              :content="scope.row.chunk_text"
              placement="top"
              :show-after="200"
            >
              <div class="preview-box">{{ previewText(scope.row.chunk_text) }}</div>
            </el-tooltip>
            <div v-else class="preview-box">—</div>
          </template>
        </el-table-column>
        <el-table-column prop="file_name" label="所属文件" min-width="200">
          <template #header>
            <div class="filter-header">
              <span>所属文件</span>
              <el-input
                v-model="filters.fileName"
                placeholder="过滤"
                clearable
                size="small"
              />
            </div>
          </template>
          <template #default="scope">
            <el-tooltip
              v-if="scope.row.file_name"
              :content="scope.row.file_name"
              placement="top"
              :show-after="200"
            >
              <span class="file-name" tabindex="0">{{ scope.row.file_name }}</span>
            </el-tooltip>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_index" label="Chunk Index" width="140">
          <template #header>
            <div class="filter-header">
              <span>Chunk Index</span>
              <el-input
                v-model="filters.chunkIndex"
                placeholder="过滤"
                clearable
                size="small"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="140">
          <template #header>
            <div class="filter-header">
              <span>状态</span>
              <el-select v-model="filters.status" placeholder="过滤" clearable size="small">
                <el-option label="已切分" value="splitted" />
                <el-option label="嵌入中" value="embedding" />
                <el-option label="重新嵌入中" value="re-embedding" />
                <el-option label="已嵌入" value="embedded" />
                <el-option label="失败" value="failed" />
              </el-select>
            </div>
          </template>
          <template #default="scope">
            <el-tag :type="statusType(scope.row.status)">
              {{ statusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next, jumper"
          @current-change="loadChunks"
        />
      </div>

      <div class="footer-bar">
        <div v-if="embedding" class="embed-progress">
          已完成 {{ embedDone }} / {{ embedTotal }}
        </div>
        <div class="footer-actions">
          <el-button @click="handleClose">取消</el-button>
          <el-button
            v-if="embedFinished"
            type="primary"
            @click="handleDone"
          >
            完成
          </el-button>
          <el-button
            v-else
            type="primary"
            :loading="embedding"
            :disabled="selectedIds.length === 0"
            @click="startEmbedding"
          >
            {{ embedButtonText }}
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { getKnowledgeBaseAttributes, getChunkAttributesForIds, getFileAttributesForIds } from '@/api/knowledge'

const props = defineProps({
  kbId: {
    type: [String, Number],
    required: true
  }
})

const emit = defineEmits(['close', 'done'])

const chunks = ref([])
const chunkIds = ref([])
const selectedIdSet = ref(new Set())
const selectedIds = computed(() => Array.from(selectedIdSet.value))
const tableRef = ref(null)
const filters = ref({
  fileName: '',
  chunkIndex: '',
  status: ''
})
const embedding = ref(false)
const streamAbort = ref(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const selectedStatusMap = ref(new Map())
const embedTotal = ref(0)
const embedDone = ref(0)
const embedFinished = ref(false)

const hasReselection = computed(() => {
  if (selectedIds.value.length === 0) return false
  return selectedIds.value.some(id => {
    const mapped = selectedStatusMap.value.get(id)
    const status = (mapped || '').toLowerCase()
    if (status) return status !== 'splitted'
    const target = chunks.value.find(item => item.id === id)
    const fallback = (target?.status || '').toLowerCase()
    return fallback ? fallback !== 'splitted' : false
  })
})

const embedButtonText = computed(() => (hasReselection.value ? '重新嵌入' : '执行嵌入'))

const statusText = (status) => {
  const s = (status || '').toString().toLowerCase()
  if (!s) return '未知'
  if (s === 'splitted') return '已切分'
  if (s === 'processing') return '处理中'
  if (s === 'completed') return '已完成'
  if (s === 'embedding') return '嵌入中'
  if (s === 're-embedding') return '重新嵌入中'
  if (s === 'embedded') return '已嵌入'
  if (s === 'failed') return '失败'
  return status
}

const statusType = (status) => {
  const s = (status || '').toString().toLowerCase()
  if (s === 'splitted' || s === 'completed' || s === 'embedded') return 'success'
  if (s === 'processing' || s === 'embedding' || s === 're-embedding') return 'warning'
  if (s === 'failed') return 'danger'
  return 'info'
}

const previewText = (text) => {
  if (!text) return ''
  return String(text).slice(0, 20)
}

const filteredChunks = computed(() => {
  const nameKeyword = filters.value.fileName.trim().toLowerCase()
  const idxKeyword = filters.value.chunkIndex.trim().toLowerCase()
  const statusFilter = (filters.value.status || '').toLowerCase()

  return chunks.value.filter(item => {
    const nameOk = !nameKeyword || (item.file_name || '').toLowerCase().includes(nameKeyword)
    const idxOk = !idxKeyword || String(item.chunk_index ?? '').toLowerCase().includes(idxKeyword)
    const statusOk = !statusFilter || (item.status || '').toLowerCase() === statusFilter
    return nameOk && idxOk && statusOk
  })
})

const syncSelectionForFilter = async () => {
  await nextTick()
  if (!tableRef.value) return
  tableRef.value.clearSelection()
  filteredChunks.value.forEach(row => {
    if (selectedIdSet.value.has(row.id)) {
      tableRef.value.toggleRowSelection(row, true)
    }
  })
}

const onSelectionChange = (rows) => {
  const selectedOnPage = new Set((rows || []).map(r => r.id))
  const filteredIds = new Set(filteredChunks.value.map(r => r.id))
  const next = new Set(selectedIdSet.value)

  filteredIds.forEach(id => {
    if (selectedOnPage.has(id)) {
      next.add(id)
    } else {
      next.delete(id)
    }
  })

  selectedIdSet.value = next
  if (embedFinished.value) {
    embedFinished.value = false
  }
  const map = new Map(selectedStatusMap.value)
  chunks.value.forEach(item => {
    if (selectedIdSet.value.has(item.id)) {
      map.set(item.id, item.status)
    }
  })
  selectedStatusMap.value = map
}

const normalizeItems = (data) => {
  const items = Array.isArray(data?.items)
    ? data.items
    : data && typeof data === 'object'
      ? [data]
      : []
  return items
}

const ensureChunkIds = async () => {
  if (chunkIds.value.length > 0) return
  const kbRes = await getKnowledgeBaseAttributes(props.kbId, ['chunks_list'])
  const ids = kbRes?.data?.chunks_list || []
  chunkIds.value = Array.isArray(ids) ? ids : []
  total.value = chunkIds.value.length
}

const loadChunks = async () => {
  try {
    await ensureChunkIds()

    if (!Array.isArray(chunkIds.value) || chunkIds.value.length === 0) {
      chunks.value = []
      selectedIdSet.value = new Set()
      return
    }

    const start = (page.value - 1) * pageSize.value
    const end = start + pageSize.value
    const pageIds = chunkIds.value.slice(start, end)
    if (pageIds.length === 0) {
      chunks.value = []
      selectedIdSet.value = new Set()
      return
    }

    const chunkRes = await getChunkAttributesForIds(pageIds, [
      'id',
      'file_id',
      'chunk_text',
      'chunk_index',
      'status'
    ])

    const chunkItems = normalizeItems(chunkRes?.data || null)
    const fileIds = chunkItems.map(i => i.file_id).filter(Boolean)
    let fileNameMap = {}

    if (fileIds.length > 0) {
      const fileRes = await getFileAttributesForIds(fileIds, ['filename'])
      const fileItems = normalizeItems(fileRes?.data || null)
      fileItems.forEach((item, idx) => {
        const fileId = fileIds[idx]
        if (fileId != null) {
          fileNameMap[fileId] = item?.filename || `文件 ${fileId}`
        }
      })
    }

    chunks.value = chunkItems.map(item => ({
      ...item,
      file_name: fileNameMap[item.file_id] || (item.file_id ? `文件 ${item.file_id}` : '—')
    }))
    await syncSelectionForFilter()
  } catch (e) {
    ElMessage.error('加载文本块失败：' + (e.message || '未知错误'))
  }
}

const selectAll = async () => {
  await ensureChunkIds()
  selectedIdSet.value = new Set(chunkIds.value)
  await syncSelectionForFilter()
}

const clearSelection = async () => {
  selectedIdSet.value = new Set()
  selectedStatusMap.value = new Map()
  await syncSelectionForFilter()
}

const stopStream = () => {
  if (streamAbort.value) {
    streamAbort.value.abort()
    streamAbort.value = null
  }
}

const fetchSelectedChunkPayloads = async (ids) => {
  const payloads = []
  const batchSize = 500
  for (let i = 0; i < ids.length; i += batchSize) {
    const batchIds = ids.slice(i, i + batchSize)
    const chunkRes = await getChunkAttributesForIds(batchIds, ['id', 'file_id', 'chunk_index'])
    const chunkItems = normalizeItems(chunkRes?.data || null)
    chunkItems.forEach(item => {
      payloads.push({
        chunk_id: item.id,
        chunk_index: item.chunk_index,
        file_id: item.file_id
      })
    })
  }
  return payloads
}

const runEmbeddingBatch = async (payloadItems) => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  const controller = new AbortController()
  streamAbort.value = controller

  const response = await fetch(`${baseUrl}/api/v1/chunks/embedding`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ items: payloadItems }),
    signal: controller.signal
  })

  if (!response.ok || !response.body) {
    throw new Error('嵌入流连接失败')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''

    for (const part of parts) {
      const line = part.split('\n').find(l => l.startsWith('data:'))
      if (!line) continue
      const data = line.replace(/^data:\s*/, '')
      try {
        const payload = JSON.parse(data || '{}')
        if (payload.event === 'chunk' && payload.chunk) {
          const target = chunks.value.find(c => c.id === payload.chunk.chunk_id)
          if (target && payload.chunk.status) {
            target.status = payload.chunk.status
          }
          embedDone.value += 1
        }

        if (payload.event === 'error') {
          embedDone.value += 1
        }

        if (payload.event === 'done') {
          return
        }
      } catch (e) {
        console.error('解析嵌入流失败:', e)
      }
    }
  }
}

const startEmbedding = async () => {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请至少选择一个文本块')
    return
  }
  try {
    embedding.value = true
    embedFinished.value = false
    stopStream()
    embedDone.value = 0

    await ensureChunkIds()
    const selectedIdList = Array.from(selectedIdSet.value)
    embedTotal.value = selectedIdList.length
    const batchSize = 500
    for (let i = 0; i < selectedIdList.length; i += batchSize) {
      const batchIds = selectedIdList.slice(i, i + batchSize)
      const batchItems = await fetchSelectedChunkPayloads(batchIds)
      if (!batchItems || batchItems.length === 0) {
        continue
      }
      await runEmbeddingBatch(batchItems)
      stopStream()
    }

    embedding.value = false
    embedFinished.value = true
    ElMessage.success('嵌入完成')
  } catch (e) {
    embedding.value = false
    ElMessage.error('嵌入失败：' + (e.message || '未知错误'))
  }
}

const handleDone = () => {
  embedFinished.value = false
  embedDone.value = 0
  embedTotal.value = 0
  emit('done')
}

const handleClose = () => {
  stopStream()
  embedDone.value = 0
  embedTotal.value = 0
  embedFinished.value = false
  emit('close')
}

onMounted(loadChunks)

watch(() => filters.value, () => {
  syncSelectionForFilter()
}, { deep: true })

onBeforeUnmount(() => {
  stopStream()
})
</script>

<style scoped>
.chunk-embedding-panel {
  display: flex;
  flex-direction: column;
}

.list-card :deep(.el-card__body) {
  padding-bottom: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.footer-bar {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: 12px;
}

.embed-progress {
  color: #4b5563;
  font-size: 13px;
  display: flex;
  align-items: center;
}

.pagination {
  display: flex;
  justify-content: center;
  padding: 12px 0 0;
}


.preview-box {
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 6px;
  padding: 6px 10px;
  color: #374151;
  font-size: 13px;
  line-height: 1.4;
  min-height: 32px;
  display: flex;
  align-items: center;
}

.file-name {
  display: inline-block;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
