<template>
  <div class="chunk-embedding-page">
    <div class="page-header">
      <div class="title-group">
        <el-button type="text" @click="goBack">返回文件列表</el-button>
        <h2>文本块嵌入</h2>
      </div>
      <div class="actions">
        <el-button @click="selectAll">全选全部 ({{ total }})</el-button>
        <el-button @click="clearSelection" :disabled="selectedIds.length === 0">清空选择</el-button>
        <el-button type="primary" @click="embedSelected" :disabled="selectedIds.length === 0" :loading="embeddingLoading">
          执行嵌入 ({{ selectedIds.length }})
        </el-button>
      </div>
    </div>

    <el-card class="list-card">
      <template #header>
        <div class="card-header">
          <span>知识库：{{ kbId }}</span>
          <span>共 {{ total }} 条</span>
        </div>
      </template>

      <el-table
        ref="tableRef"
        :data="items"
        style="width: 100%"
        height="60vh"
        @selection-change="onSelectionChange"
        :row-key="row => row.id"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="scope">
            <el-tag :type="statusType(scope.row.status)">
              {{ statusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_index" label="Chunk Index" width="140" />
        <el-table-column label="所属文件" min-width="200">
          <template #default="scope">
            <span>{{ getFileName(scope.row.file_id) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="内容预览(前20字)" min-width="260">
          <template #default="scope">
            <div class="preview-box">{{ previewText(scope.row.chunk_text) }}</div>
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
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getKnowledgeBaseAttributes, getChunkAttributesForIds, getFileAttributesForIds, embedChunks } from '@/api/knowledge'

const route = useRoute()
const router = useRouter()
const kbId = ref(route.params.kbId)

const tableRef = ref(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const items = ref([])
const selectedIds = ref([])
const embeddingLoading = ref(false)
const allChunkIds = ref([])
const fileNameMap = ref({})

const normalizeItems = (data) => {
  const items = Array.isArray(data?.items)
    ? data.items
    : data && typeof data === 'object'
      ? [data]
      : []
  return items
}

const statusText = (status) => {
  const s = (status || '').toString().toLowerCase()
  if (!s) return '未知'
  if (s === 'splitted') return '已切分'
  if (s === 'processing') return '处理中'
  if (s === 'completed') return '已完成'
  if (s === 'failed') return '失败'
  return status
}

const statusType = (status) => {
  const s = (status || '').toString().toLowerCase()
  if (s === 'splitted' || s === 'completed') return 'success'
  if (s === 'processing') return 'warning'
  if (s === 'failed') return 'danger'
  return 'info'
}

const previewText = (text) => {
  if (!text) return ''
  const raw = String(text)
  return raw.slice(0, 20)
}

const getFileName = (fileId) => {
  if (!fileId) return '未知文件'
  return fileNameMap.value[fileId] || `文件 ${fileId}`
}

const loadChunkIds = async () => {
  const res = await getKnowledgeBaseAttributes(kbId.value, ['chunks_list'])
  const ids = res?.data?.chunks_list || []
  allChunkIds.value = Array.isArray(ids) ? ids : []
  total.value = allChunkIds.value.length
}

const loadFileNames = async (fileIds) => {
  const uniqueIds = Array.from(new Set(fileIds.filter(Boolean)))
  const missing = uniqueIds.filter(id => !fileNameMap.value[id])
  if (missing.length === 0) return

  const res = await getFileAttributesForIds(missing, ['filename'])
  const data = res?.data || null
  const items = normalizeItems(data)
  items.forEach((item, idx) => {
    const fileId = missing[idx]
    if (fileId != null) {
      fileNameMap.value[fileId] = item?.filename || `文件 ${fileId}`
    }
  })
}

const syncSelection = async () => {
  await nextTick()
  if (!tableRef.value) return
  tableRef.value.clearSelection()
  items.value.forEach(row => {
    if (selectedIds.value.includes(row.id)) {
      tableRef.value.toggleRowSelection(row, true)
    }
  })
}

const loadChunks = async () => {
  try {
    const start = (page.value - 1) * pageSize.value
    const end = start + pageSize.value
    const pageIds = allChunkIds.value.slice(start, end)

    if (pageIds.length === 0) {
      items.value = []
      await syncSelection()
      return
    }

    const resp = await getChunkAttributesForIds(pageIds, [
      'id',
      'file_id',
      'knowledge_base_id',
      'chunk_text',
      'chunk_index',
      'status',
      'created_at'
    ])

    const data = resp?.data || null
    const chunkItems = normalizeItems(data)
    items.value = chunkItems

    const fileIds = chunkItems.map(i => i.file_id).filter(Boolean)
    if (fileIds.length > 0) {
      await loadFileNames(fileIds)
    }

    await syncSelection()
  } catch (e) {
    ElMessage.error('加载文本块失败：' + (e.message || '未知错误'))
  }
}

const onSelectionChange = (rows) => {
  const currentIds = items.value.map(i => i.id)
  const selectedCurrent = (rows || []).map(r => r.id)
  selectedIds.value = selectedIds.value
    .filter(id => !currentIds.includes(id))
    .concat(selectedCurrent)
}

const selectAll = async () => {
  selectedIds.value = [...allChunkIds.value]
  await syncSelection()
}

const clearSelection = async () => {
  selectedIds.value = []
  await syncSelection()
}

const embedSelected = async () => {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请至少选择一个文本块')
    return
  }
  try {
    embeddingLoading.value = true
    const resp = await embedChunks(selectedIds.value)
    if (resp?.success) {
      ElMessage.success(`嵌入完成：${resp.data?.processed || selectedIds.value.length} 条`)
      await loadChunks()
    } else {
      ElMessage.error('嵌入失败')
    }
  } catch (e) {
    ElMessage.error('嵌入失败：' + (e.message || '未知错误'))
  } finally {
    embeddingLoading.value = false
  }
}

const goBack = () => {
  router.push({ name: 'KnowledgeFiles', params: { id: kbId.value } })
}

onMounted(async () => {
  if (!kbId.value) {
    ElMessage.error('缺少知识库ID')
    router.push('/home/knowledge_base')
    return
  }
  await loadChunkIds()
  await loadChunks()
})
</script>

<style scoped>
.chunk-embedding-page {
  padding: 24px;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}
.page-header .actions {
  display: flex;
  gap: 12px;
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
.list-card {
  border-radius: 8px;
}
.card-header {
  display: flex;
  justify-content: space-between;
}
.pagination {
  display: flex;
  justify-content: center;
  padding: 16px 0;
}
</style>
