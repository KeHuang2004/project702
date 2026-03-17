<template>
  <div class="batch-delete-page">
    <div class="page-header">
      <el-button type="text" @click="goBack" class="back-button">
        <el-icon><ArrowLeft /></el-icon>
        返回文件列表
      </el-button>
      <h2>批量删除文件</h2>
    </div>

    <el-card class="panel" v-loading="loading">
      <template #header>
        <div class="panel-header">
          <span>选择要删除的文件</span>
        </div>
      </template>

      <div v-if="fileOptions.length === 0" class="empty-state">
        <el-empty description="当前知识库暂无文件" />
      </div>

      <div v-else class="selector-area">
        <div class="toolbar">
          <el-checkbox
            :indeterminate="isIndeterminate"
            :model-value="isAllSelected"
            @change="toggleSelectAll"
          >
            全选
          </el-checkbox>

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

        <el-select
          v-model="selectedIds"
          multiple
          filterable
          collapse-tags
          collapse-tags-tooltip
          placeholder="请选择文件"
          class="file-select"
        >
          <el-option
            v-for="option in filteredOptions"
            :key="option.id"
            :label="option.filename"
            :value="option.id"
          />
        </el-select>

        <div class="selected-preview" v-if="selectedFiles.length > 0">
          <div class="preview-title">已选文件：</div>
          <div class="preview-list">
            <span class="preview-item" v-for="item in selectedFiles" :key="item.id">
              {{ item.filename }}
            </span>
          </div>
        </div>

        <div class="actions">
          <el-button @click="goBack">取消</el-button>
          <el-button
            type="danger"
            :disabled="selectedIds.length === 0"
            :loading="deleting"
            @click="confirmDelete"
          >
            删除选中文件
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Search } from '@element-plus/icons-vue'
import { getKnowledgeBaseAttributes, getFileAttributesForIds, deleteFiles } from '@/api/knowledge'

const route = useRoute()
const router = useRouter()
const kbId = computed(() => route.params.kbId)

const loading = ref(false)
const deleting = ref(false)
const fileOptions = ref([])
const searchKeyword = ref('')
const selectedIds = ref([])

const filteredOptions = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return fileOptions.value
  return fileOptions.value.filter(item => (item.filename || '').toLowerCase().includes(keyword))
})

const selectedFiles = computed(() => {
  const set = new Set(selectedIds.value)
  return fileOptions.value.filter(item => set.has(item.id))
})

const isAllSelected = computed(() => {
  return fileOptions.value.length > 0 && selectedIds.value.length === fileOptions.value.length
})

const isIndeterminate = computed(() => {
  return selectedIds.value.length > 0 && selectedIds.value.length < fileOptions.value.length
})

const toggleSelectAll = (val) => {
  if (val) {
    selectedIds.value = fileOptions.value.map(item => item.id)
  } else {
    selectedIds.value = []
  }
}

const loadFiles = async () => {
  if (!kbId.value) return
  try {
    loading.value = true
    const res = await getKnowledgeBaseAttributes(kbId.value, ['files_list'])
    const ids = res?.data?.files_list || []
    if (!Array.isArray(ids) || ids.length === 0) {
      fileOptions.value = []
      selectedIds.value = []
      return
    }

    const attrRes = await getFileAttributesForIds(ids, ['filename'])
    const data = attrRes?.data || null
    const items = Array.isArray(data?.items) ? data.items : data && typeof data === 'object' ? [data] : []

    fileOptions.value = items.map((item, idx) => ({
      id: ids[idx],
      filename: item?.filename || `未命名文件 ${ids[idx]}`
    }))
    selectedIds.value = []
  } catch (error) {
    console.error('获取文件列表失败:', error)
    ElMessage.error('获取文件列表失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const confirmDelete = async () => {
  if (selectedIds.value.length === 0) return

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
      ElMessage.success('批量删除成功')
      await loadFiles()
    } else {
      ElMessage.error('批量删除失败: ' + (response?.message || '未知错误'))
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除文件出错:', error)
      ElMessage.error('批量删除失败: ' + (error.message || '未知错误'))
    }
  } finally {
    deleting.value = false
  }
}

const goBack = () => {
  router.push({
    name: 'KnowledgeFiles',
    params: { id: kbId.value }
  })
}

onMounted(loadFiles)
</script>

<style scoped>
.batch-delete-page {
  padding: 24px;
  background: #f5f7fa;
  min-height: 100vh;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.panel {
  max-width: 880px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.selector-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-input {
  max-width: 320px;
}

.file-select {
  width: 100%;
}

.selected-preview {
  background: #f8f9fb;
  border-radius: 6px;
  padding: 12px;
}

.preview-title {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}

.preview-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preview-item {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  color: #303133;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
