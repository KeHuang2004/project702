<template>
  <div class="chunk-split-panel">
    <el-card class="settings-card">
      <template #header>
        <div class="card-header">
          <span>切分参数</span>
        </div>
      </template>
      <div class="settings-grid">
        <div class="setting-item">
          <span class="setting-label">策略</span>
          <el-select v-model="settings.strategy" style="width: 220px">
            <el-option label="递归字符分割" value="recursive_character" />
            <el-option label="固定长度分割" value="token_text" />
            <el-option label="语义分割" value="SemanticChunker" />
          </el-select>
        </div>
        <div class="setting-item">
          <span class="setting-label">块长度</span>
          <el-input-number v-model="settings.chunkSize" :min="64" :max="4000" :step="64" />
        </div>
        <div class="setting-item">
          <span class="setting-label">重叠长度</span>
          <el-input-number v-model="settings.chunkOverlap" :min="0" :max="1000" :step="16" />
        </div>
      </div>
    </el-card>

    <el-card class="list-card">
      <template #header>
        <div class="card-header">
          <span>选择文件（默认全选）</span>
          <span>
            已选 {{ selectedIds.length }} / {{ files.length }}
          </span>
        </div>
      </template>

      <div class="toolbar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索文件名"
          clearable
          class="search-input"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <el-table
        ref="tableRef"
        :data="filteredFiles"
        style="width: 100%"
        height="50vh"
        :row-key="row => row.id"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="filename" label="文件名" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="scope">
            <el-tag :type="statusType(scope.row.status)">{{ statusText(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div class="footer-bar">
        <div class="split-progress" v-if="splitting">
          切分 {{ selectedIds.length }} 个，完成 {{ doneCount }} 个
        </div>
        <div class="footer-actions">
          <el-button @click="handleClose">取消</el-button>
          <el-button
            type="primary"
            :loading="splitting"
            :disabled="selectedIds.length === 0"
            @click="handlePrimary"
          >
            {{ splitButtonText }}
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getKnowledgeBaseAttributes, getFileAttributesForIds } from '@/api/knowledge'

const props = defineProps({
  kbId: {
    type: [String, Number],
    required: true
  }
})

const emit = defineEmits(['close', 'done'])

const settings = ref({
  strategy: 'recursive_character',
  chunkSize: 512,
  chunkOverlap: 50
})

const files = ref([])
const selectedIdSet = ref(new Set())
const selectedIds = computed(() => Array.from(selectedIdSet.value))
const pendingIds = ref([])
const splitting = ref(false)
const splitFinished = ref(false)
const tableRef = ref(null)
const searchKeyword = ref('')
const streamAbort = ref(null)
const dragSelecting = ref(false)
const dragSelectChecked = ref(false)
let tableBodyEl = null
let onBodyMouseDown = null
let onBodyMouseOver = null
let onDocMouseUp = null

const hasResplitSelection = computed(() => selectedIds.value.some(id => {
  const target = files.value.find(item => item.id === id)
  const status = (target?.status || '').toLowerCase()
  return status === 'splitted' || status === 'splitting'
}))

const splitButtonText = computed(() => {
  if (splitFinished.value) return '完成'
  return hasResplitSelection.value ? '重新切分' : '切分'
})

const doneCount = computed(() => selectedIds.value.filter(id => {
  const target = files.value.find(item => item.id === id)
  const status = (target?.status || '').toLowerCase()
  return status === 'splitted'
}).length)

const statusType = (status) => {
  const s = (status || '').toLowerCase()
  if (s === 'splitted') return 'success'
  if (s === 're-splitting') return 'warning'
  if (s === 'splitting') return 'warning'
  if (s === 'failed') return 'danger'
  return 'info'
}

const statusText = (status) => {
  const s = (status || '').toLowerCase()
  if (s === 're-splitting') return '重新切分中'
  if (s === 'splitting') return '切分中'
  if (s === 'splitted') return '已切分'
  if (s === 'uploaded') return '已上传'
  if (s === 'failed') return '失败'
  return '待处理'
}


const filteredFiles = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return files.value
  return files.value.filter(item => (item.filename || '').toLowerCase().includes(keyword))
})

const syncSelectionForFilter = async () => {
  await nextTick()
  if (!tableRef.value) return
  tableRef.value.clearSelection()
  filteredFiles.value.forEach(row => {
    if (selectedIdSet.value.has(row.id)) {
      tableRef.value.toggleRowSelection(row, true)
    }
  })
}

const onSelectionChange = (rows) => {
  const selectedOnPage = new Set((rows || []).map(r => r.id))
  const filteredIds = new Set(filteredFiles.value.map(r => r.id))
  const next = new Set(selectedIdSet.value)

  filteredIds.forEach(id => {
    if (selectedOnPage.has(id)) {
      next.add(id)
    } else {
      next.delete(id)
    }
  })

  selectedIdSet.value = next
}

const initDragSelect = async () => {
  await nextTick()
  if (!tableRef.value || !tableRef.value.$el) return

  tableBodyEl = tableRef.value.$el.querySelector('.el-table__body')
  if (!tableBodyEl) return

  onBodyMouseDown = (event) => {
    const cell = event.target.closest('td')
    if (!cell) return
    if (!cell.className.includes('el-table__column--selection')) return

    const checkbox = cell.querySelector('.el-checkbox__input')
    const isChecked = checkbox?.classList.contains('is-checked')
    dragSelecting.value = true
    dragSelectChecked.value = !isChecked
  }

  onBodyMouseOver = (event) => {
    if (!dragSelecting.value) return
    const rowEl = event.target.closest('tr')
    if (!rowEl) return

    const rowKey = rowEl.getAttribute('data-row-key')
    const rowId = rowKey ? Number(rowKey) : null
    const targetRow = rowId != null
      ? files.value.find(r => Number(r.id) === rowId)
      : null

    if (targetRow) {
      tableRef.value.toggleRowSelection(targetRow, dragSelectChecked.value)
    }
  }

  onDocMouseUp = () => {
    dragSelecting.value = false
  }

  tableBodyEl.addEventListener('mousedown', onBodyMouseDown)
  tableBodyEl.addEventListener('mouseover', onBodyMouseOver)
  document.addEventListener('mouseup', onDocMouseUp)
}

const destroyDragSelect = () => {
  if (tableBodyEl && onBodyMouseDown) {
    tableBodyEl.removeEventListener('mousedown', onBodyMouseDown)
  }
  if (tableBodyEl && onBodyMouseOver) {
    tableBodyEl.removeEventListener('mouseover', onBodyMouseOver)
  }
  if (onDocMouseUp) {
    document.removeEventListener('mouseup', onDocMouseUp)
  }
  tableBodyEl = null
  onBodyMouseDown = null
  onBodyMouseOver = null
  onDocMouseUp = null
}

const loadFiles = async () => {
  const res = await getKnowledgeBaseAttributes(props.kbId, ['files_list'])
  const ids = res?.data?.files_list || []
  if (!Array.isArray(ids) || ids.length === 0) {
    files.value = []
    selectedIdSet.value = new Set()
    return
  }

  const attrRes = await getFileAttributesForIds(ids, ['filename', 'status'])
  const data = attrRes?.data || null
  const items = Array.isArray(data?.items) ? data.items : data && typeof data === 'object' ? [data] : []
  files.value = items.map((item, idx) => ({
    id: ids[idx],
    filename: item.filename || '',
    status: item.status || ''
  }))

  selectedIdSet.value = new Set(files.value.map(row => row.id))
  await syncSelectionForFilter()
}

const stopStream = () => {
  if (streamAbort.value) {
    streamAbort.value.abort()
    streamAbort.value = null
  }
}

const startSplit = async () => {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请选择要切分的文件')
    return
  }
  try {
    splitting.value = true
    splitFinished.value = false
    pendingIds.value = [...selectedIds.value]
    stopStream()

    const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
    const controller = new AbortController()
    streamAbort.value = controller

    const response = await fetch(`${baseUrl}/api/v1/chunks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        file_ids: selectedIds.value,
        chunk_length: settings.value.chunkSize,
        chunk_overlap: settings.value.chunkOverlap,
        segmentation_strategy: settings.value.strategy
      }),
      signal: controller.signal
    })

    if (!response.ok || !response.body) {
      throw new Error('切分流连接失败')
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
          const list = Array.isArray(payload.files) ? payload.files : []
          list.forEach(item => {
            const target = files.value.find(f => f.id === item.id)
            if (target) target.status = item.status
          })

          if (payload.done) {
            stopStream()
            splitting.value = false
            splitFinished.value = true
            ElMessage.success('切分完成')
            return
          }
        } catch (e) {
          console.error('解析切分流失败:', e)
        }
      }
    }
  } catch (e) {
    splitting.value = false
    pendingIds.value = []
    ElMessage.error('切分失败：' + (e.message || '未知错误'))
  }
}

const handlePrimary = () => {
  if (splitFinished.value) {
    emit('done')
    return
  }
  startSplit()
}

const handleClose = () => {
  stopStream()
  splitFinished.value = false
  pendingIds.value = []
  emit('close')
}

onMounted(loadFiles)

onMounted(initDragSelect)

onBeforeUnmount(() => {
  stopStream()
  destroyDragSelect()
})

watch(() => searchKeyword.value, () => {
  syncSelectionForFilter()
})
</script>

<style scoped>
.chunk-split-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.setting-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.setting-label {
  width: 72px;
  color: #606266;
}

.toolbar {
  margin-bottom: 12px;
}

.footer-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.footer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.split-progress {
  color: #606266;
  font-size: 13px;
}

.search-input {
  width: 100%;
}

.footer-bar {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}
</style>
