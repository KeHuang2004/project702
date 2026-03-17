<template>
  <div class="file-delete-panel">
    <el-card class="list-card">
      <template #header>
        <div class="card-header">
          <span>选择要删除的文件</span>
          <span>已选 {{ selectedIds.length }} / {{ files.length }}</span>
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
      </el-table>

      <div class="footer-bar">
        <el-button @click="handleClose">取消</el-button>
        <el-button
          type="danger"
          :loading="deleting"
          :disabled="selectedIds.length === 0"
          @click="startDelete"
        >
          删除文件
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getKnowledgeBaseAttributes, getFileAttributesForIds, deleteFiles } from '@/api/knowledge'

const props = defineProps({
  kbId: {
    type: [String, Number],
    required: true
  }
})

const emit = defineEmits(['close', 'done'])

const files = ref([])
const selectedIdSet = ref(new Set())
const selectedIds = computed(() => Array.from(selectedIdSet.value))
const deleting = ref(false)
const tableRef = ref(null)
const searchKeyword = ref('')

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

const loadFiles = async () => {
  const res = await getKnowledgeBaseAttributes(props.kbId, ['files_list'])
  const ids = res?.data?.files_list || []
  if (!Array.isArray(ids) || ids.length === 0) {
    files.value = []
    selectedIds.value = []
    return
  }

  const attrRes = await getFileAttributesForIds(ids, ['filename'])
  const data = attrRes?.data || null
  const items = Array.isArray(data?.items) ? data.items : data && typeof data === 'object' ? [data] : []
  files.value = items.map((item, idx) => ({
    id: ids[idx],
    filename: item.filename || ''
  }))

  selectedIdSet.value = new Set()
  await syncSelectionForFilter()
}

const startDelete = async () => {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请选择要删除的文件')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedIds.value.length} 个文件吗？此操作不可恢复。`,
      '批量删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    deleting.value = true
    const response = await deleteFiles(selectedIds.value)
    if (response && response.success) {
      ElMessage.success('删除成功')
      emit('done')
    } else {
      ElMessage.error('删除失败: ' + (response?.message || '未知错误'))
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.message || '未知错误'))
    }
  } finally {
    deleting.value = false
  }
}

const handleClose = () => {
  emit('close')
}

onMounted(loadFiles)

watch(() => searchKeyword.value, () => {
  syncSelectionForFilter()
})
</script>

<style scoped>
.file-delete-panel {
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

.toolbar {
  margin-bottom: 12px;
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