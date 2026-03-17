<script setup>
import { ref, onMounted, computed, watch, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, View, Delete, Search, Download } from '@element-plus/icons-vue'
import { getKnowledgeBaseAttributes, getFileAttributesForIds, downloadFile } from '@/api/knowledge'
import { useRouter } from 'vue-router'



const router = useRouter()

// Props
const props = defineProps({
  kbId: {
    type: [String, Number],
    required: true
  }
})

// Emits
const emit = defineEmits(['upload', 'open-split', 'open-delete', 'open-embed'])

// 响应式数据
const loading = ref(false)
const allFiles = ref([]) // 存储当前页文件
const files = ref([]) // 存储过滤后的文件
const tableRef = ref(null)
const pagination = ref({
  page: 1,
  page_size: 10,
  total: 0,
  pages: 0
})
const currentPage = ref(1)
const pageSize = ref(10)
const showDetailDialog = ref(false)
const selectedFile = ref(null)
const isMounted = ref(false)
const searchKeyword = ref('')
const isSearching = ref(false)
const searchIds = ref([])
const searchLoading = ref(false)
// 表格区域高度：占满容器剩余空间，保证分页可见
const tableHeight = '100%'

// 展示的总页数（为空时显示为 1 页，避免出现 0 页的尴尬显示）
const totalPagesDisplay = computed(() => {
  const p = pagination.value?.pages || 0
  return p > 0 ? p : 1
})

// 展示行（含占位行），保证每页固定 10 行空间
const displayRows = computed(() => {
  const rows = Array.isArray(files.value) ? [...files.value] : []
  const pad = Math.max(0, pageSize.value - rows.length)
  if (pad > 0) {
    for (let i = 0; i < pad; i++) {
      rows.push({ __placeholder: true, id: `ph-${i}` })
    }
  }
  return rows
})

// 计算属性
const totalFiles = computed(() => {
  return files.value.length
})

const fetchAllFileIds = async () => {
  const kbAttrsRes = await getKnowledgeBaseAttributes(props.kbId, ['files_list'])
  const ids = kbAttrsRes?.data?.files_list || []
  return Array.isArray(ids) ? ids : []
}

const fetchMatchedIdsByName = async (keyword) => {
  const ids = await fetchAllFileIds()
  if (!Array.isArray(ids) || ids.length === 0) return []

  const resAttrs = await getFileAttributesForIds(ids, ['filename'])
  const data = resAttrs?.data || null
  const items = Array.isArray(data?.items)
    ? data.items
    : data && typeof data === 'object'
      ? [data]
      : []

  const lowerKeyword = keyword.trim().toLowerCase()
  const matched = []
  items.forEach((item, idx) => {
    const name = (item?.filename || '').toLowerCase()
    if (lowerKeyword && name.includes(lowerKeyword)) {
      matched.push(ids[idx])
    }
  })

  return matched
}

const handleSearch = async () => {
  if (!props.kbId || !isMounted.value) return

  const keyword = searchKeyword.value.trim()
  if (!keyword) {
    await handleClearSearch()
    return
  }

  try {
    searchLoading.value = true
    const matchedIds = await fetchMatchedIdsByName(keyword)
    searchIds.value = matchedIds
    isSearching.value = true
    currentPage.value = 1
    await getFiles()
  } catch (error) {
    console.error('搜索文件失败:', error)
    ElMessage.error('搜索失败: ' + (error.message || '未知错误'))
  } finally {
    searchLoading.value = false
  }
}

const handleClearSearch = async () => {
  searchKeyword.value = ''
  isSearching.value = false
  searchIds.value = []
  currentPage.value = 1
  await getFiles()
}

// 获取文件列表：按 files_list 排序分页后，批量拉取当前页属性
const getFiles = async () => {
  if (!props.kbId || !isMounted.value) return

  try {
    loading.value = true
    console.log('🔍 获取知识库文件（files_list + 多属性），ID:', props.kbId)

    // 1) 拉取 files_list 或使用搜索结果
    const ids = isSearching.value ? [...searchIds.value] : await fetchAllFileIds()
    console.log('📋 files_list:', ids)

    if (!Array.isArray(ids) || ids.length === 0) {
      allFiles.value = []
      files.value = []
      pagination.value = {
        page: 1,
        page_size: pageSize.value,
        total: 0,
        pages: 0
      }
      return
    }

    // 2) 排序并分页（ID 越大越新）
    const sortedIds = [...ids].sort((a, b) => b - a)
    const total = sortedIds.length
    const pages = Math.ceil(total / pageSize.value) || 0

    if (pages > 0 && currentPage.value > pages) {
      currentPage.value = pages
    }
    if (pages === 0) {
      currentPage.value = 1
    }

    const startIndex = (currentPage.value - 1) * pageSize.value
    const endIndex = startIndex + pageSize.value
    const pageIds = sortedIds.slice(startIndex, endIndex)

    pagination.value = {
      page: currentPage.value,
      page_size: pageSize.value,
      total,
      pages
    }

    if (pageIds.length === 0) {
      allFiles.value = []
      files.value = []
      return
    }

    // 3) 批量获取当前页属性
    const attrs = ['filename', 'file_size', 'file_type', 'status', 'segmentation_strategy', 'upload_at', 'knowledge_base_id']
    const resAttrs = await getFileAttributesForIds(pageIds, attrs)
    const data = resAttrs?.data || null
    const items = Array.isArray(data?.items)
      ? data.items
      : data && typeof data === 'object'
        ? [data]
        : []

    allFiles.value = items.map((item, idx) => ({
      id: pageIds[idx],
      ...item
    }))
    files.value = allFiles.value

    console.log(`✅ 获取到 ${total} 个属于当前知识库的文件；当前第${currentPage.value}/${pages || 1}页`)
  } catch (error) {
    console.error('💥 获取文件列表出错:', error)
    if (isMounted.value) {
      ElMessage.error('获取文件列表失败: ' + (error.message || '未知错误'))
      allFiles.value = []
      files.value = []
      pagination.value = {
        page: 1,
        page_size: pageSize.value,
        total: 0,
        pages: 0
      }
    }
  } finally {
    if (isMounted.value) {
      loading.value = false
    }
  }
}

// 刷新文件列表
const refreshFiles = async () => {
  if (!isMounted.value) return
  await getFiles()
}

// 获取文件统计信息
const getFileStats = () => {
  if (!isMounted.value || !Array.isArray(files.value)) {
    return { count: 0, size: '0 B' }
  }

  let totalSize = 0
  files.value.forEach(file => {
    const fileSize = parseInt(file.file_size || 0)
    totalSize += fileSize
  })

  return {
    count: files.value.length,
    size: formatFileSize(totalSize)
  }
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B'

  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return parseFloat((bytes / Math.pow(1024, i)).toFixed(2)) + ' ' + sizes[i]
}

// 获取文件图标类
const getFileIconClass = (fileType) => {
  switch (fileType?.toLowerCase()) {
    case 'pdf':
      return 'pdf-icon'
    case 'docx':
    case 'doc':
      return 'word-icon'
    case 'txt':
      return 'text-icon'
    case 'md':
      return 'markdown-icon'
    case 'ipynb':
      return 'notebook-icon'
    case 'pptx':
    case 'ppt':
      return 'powerpoint-icon'
    default:
      return 'default-icon'
  }
}

// 获取文件类型标签样式
const getFileTypeTag = (fileType) => {
  switch (fileType?.toLowerCase()) {
    case 'pdf':
      return 'success'
    case 'docx':
    case 'doc':
      return 'primary'
    case 'txt':
      return 'info'
    case 'md':
      return 'warning'
    case 'ipynb':
      return 'danger'
    case 'pptx':
    case 'ppt':
      return ''
    default:
      return ''
  }
}

const isSegmentationUnset = (strategy) => strategy === null || typeof strategy === 'undefined' || strategy === ''

const getSegmentationLabel = (strategy) => {
  if (isSegmentationUnset(strategy)) return '暂未切分'
  const normalized = String(strategy).toLowerCase()
  const mapping = {
    'recursive_character': '递归字符',
    'token': '固定长度',
    'semantic': '语义分割',
    'recursivecharactertextsplitter': '递归字符',
    'tokentextsplitter': '固定长度',
    'semanticchunker': '语义分割'
  }
  return mapping[normalized] || strategy
}

// 获取状态类型
const getStatusType = (status) => {
  const s = (status || '').toLowerCase()
  if (s === 'uploaded' || s === 'splitted' || s === 'completed' || s === 'embedded') return 'success'
  if (s === 're-splitting') return 'warning'
  if (s === 'embedding') return 'warning'
  if (s === 'failed' || s === 'file_not_found') return 'danger'
  return 'warning'
}

// 获取状态文本
const getStatusText = (status) => {
  const s = (status || '').toLowerCase()
  if (s === 're-splitting') return '重新切分中'
  if (s === 'uploading') return '上传中'
  if (s === 'uploaded') return '已上传'
  if (s === 'splitting') return '切分中'
  if (s === 'splitted') return '已切分'
  if (s === 'embedding') return '嵌入中'
  if (s === 'embedded') return '已嵌入'
  if (s === 'completed') return '完成'
  if (s === 'failed') return '失败'
  if (s === 'file_not_found') return '文件缺失'
  return '处理中'
}

// 查看文件详情
// 在 FileManager.vue 的 script 部分更新以下方法
const viewFileDetail = (file) => {
  console.log('查看文件详情:', file)
  // 新路由将 fileId 通过 query 传递
  router.push({
    name: 'FileDetail',
    params: {
      kbId: props.kbId
    },
    query: {
      fileId: file.id
    }
  })
}

const handleDownload = async (file) => {
  try {
    if (!file || !file.id) {
      ElMessage.error('缺少文件ID')
      return
    }

    const blob = await downloadFile(file.id)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = file.filename || `file_${file.id}`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('下载文件失败:', error)
    ElMessage.error('下载失败: ' + (error.message || '未知错误'))
  }
}



const goToSplit = () => {
  emit('open-split')
}

const goToBatchDelete = () => {
  emit('open-delete')
}

const goToEmbed = () => {
  emit('open-embed')
}

const handleCurrentChange = (newPage) => {
  if (!isMounted.value) return

  currentPage.value = newPage
  // 重新请求当前页
  getFiles()
}

// 更新分页显示（占位保留，当前页数据由接口直接返回）
const updatePaginatedFiles = () => {
  if (!Array.isArray(files.value)) return
  console.log(`📋 当前页: 第${currentPage.value}页，每页${pageSize.value}个`)
}

// 监听知识库ID变化
watch(() => props.kbId, (newKbId) => {
  if (newKbId && isMounted.value) {
    console.log('🔄 知识库ID变化:', newKbId)

    // 重置状态
    allFiles.value = []
    files.value = []
    pagination.value = {
      page: 1,
      page_size: 10,
      total: 0,
      pages: 0
    }
    currentPage.value = 1
    pageSize.value = 10
    searchKeyword.value = ''
    isSearching.value = false
    searchIds.value = []

    // 获取新的文件列表
    nextTick(() => {
      getFiles()
    })
  }
}, { immediate: false })

// 暴露方法给父组件
defineExpose({
  refreshFiles,
  getFiles,
  getFileStats
})

// 组件挂载时获取数据
onMounted(async () => {
  isMounted.value = true

  if (props.kbId) {
    await nextTick()
    getFiles()
  }
})

// 组件卸载前清理
onBeforeUnmount(() => {
  isMounted.value = false

  // 清理状态
  loading.value = false
  showDetailDialog.value = false
  selectedFile.value = null
  allFiles.value = []
  files.value = []
  pagination.value = null

  console.log('🧹 FileManager 组件已清理')
})
</script>

<template>
  <div class="file-manager" v-if="isMounted">
    <!-- <div class="file-manager-header">
      <h3>知识库文件</h3>
      <div class="kb-info" v-if="props.kbId">
        <el-tag size="small" type="info">知识库ID: {{ props.kbId }}</el-tag>
      </div>
    </div> -->

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>

    <!-- 空状态 -->
    <div v-else-if="!files || files.length === 0" class="empty-container">
      <el-empty :description="isSearching ? '未找到匹配文件' : '该知识库暂无文件'" />
    </div>

    <!-- 文件列表 -->
  <div v-else class="files-container">
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索文件名"
          clearable
          class="search-input"
          @keyup.enter="handleSearch"
          @clear="handleClearSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" :loading="searchLoading" @click="handleSearch">搜索</el-button>
        <el-button v-if="isSearching" @click="handleClearSearch">清除</el-button>
      </div>
      <!-- <div class="files-header">
        <span class="files-count">共 {{ totalFiles }} 个文件</span>
      </div> -->

      <div class="table-wrapper">
        <el-table
          ref="tableRef"
          :data="displayRows"
          stripe
          style="width: 100%"
          v-loading="loading"
          class="files-table"
          :height="tableHeight"
          :row-class-name="( { row } ) => row.__placeholder ? 'placeholder-row' : ''"
          :row-key="row => row.id"
        >
        <!-- 文件名列 -->
        <el-table-column prop="filename" label="文件名" min-width="200">
          <template #default="{ row }">
            <div class="file-info" v-if="!row.__placeholder">
              <el-icon class="file-icon" :class="getFileIconClass(row.file_type)">
                <Document />
              </el-icon>
              <el-tooltip
                v-if="row.filename"
                :content="row.filename"
                placement="top"
                :show-after="200"
              >
                <span class="file-name" tabindex="0">{{ row.filename }}</span>
              </el-tooltip>
              <span v-else class="file-name">—</span>
            </div>
            <div v-else class="placeholder-cell"></div>
          </template>
        </el-table-column>

        <!-- 文件类型列 -->
        <el-table-column prop="file_type" label="类型" width="80">
          <template #default="{ row }">
            <template v-if="!row.__placeholder">
              <el-tag :type="getFileTypeTag(row.file_type)" size="small" class="file-type-tag">
                {{ (row.file_type || '').toUpperCase() }}
              </el-tag>
            </template>
            <div v-else class="placeholder-cell"></div>
          </template>
        </el-table-column>

        <!-- 文件大小列 -->
        <el-table-column prop="file_size" label="大小" width="100">
          <template #default="{ row }">
            <span v-if="!row.__placeholder">{{ formatFileSize(row.file_size) }}</span>
            <span v-else class="placeholder-cell"></span>
          </template>
        </el-table-column>

        <!-- 知识库ID列（调试用） -->
        <el-table-column prop="knowledge_base_id" label="所属知识库" width="100" v-if="false">
          <template #default="{ row }">
            <el-tag size="small" :type="parseInt(row.knowledge_base_id) === parseInt(props.kbId) ? 'success' : 'danger'">
              {{ row.knowledge_base_id }}
            </el-tag>
          </template>
        </el-table-column>

        <!-- 分割策略列 -->
        <el-table-column prop="segmentation_strategy" label="分割策略" width="120">
          <template #default="{ row }">
            <span
              v-if="!row.__placeholder"
              :class="{ 'segmentation-muted': isSegmentationUnset(row.segmentation_strategy) }"
            >
              {{ getSegmentationLabel(row.segmentation_strategy) }}
            </span>
            <span v-else class="placeholder-cell"></span>
          </template>
        </el-table-column>

        <!-- 上传时间列 -->
        <el-table-column prop="upload_at" label="上传时间" width="200">
          <template #default="{ row }">
            <span v-if="!row.__placeholder">{{ row.upload_at || '未知' }}</span>
            <span v-else class="placeholder-cell"></span>
          </template>
        </el-table-column>

        <!-- 状态列 -->
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <template v-if="!row.__placeholder">
              <el-tag
                :type="getStatusType(row.status)"
                size="small"
                class="status-tag"
              >
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
            <div v-else class="placeholder-cell"></div>
          </template>
        </el-table-column>

        <!-- 在 FileManager.vue 的操作列中修改按钮样式 -->
      <el-table-column label="操作" width="260">
        <template #default="{ row }">
          <div class="action-buttons" v-if="!row.__placeholder">
            <el-button
              type="primary"
              size="small"
              @click="viewFileDetail(row)"
              class="action-btn"
              :icon="View"
            >
              详情
            </el-button>
            <el-button
              type="success"
              size="small"
              @click="handleDownload(row)"
              class="action-btn"
              :icon="Download"
            >
              下载
            </el-button>
          </div>
          <div v-else class="placeholder-cell"></div>
        </template>
      </el-table-column>

        </el-table>
      </div>

    <!-- 批量操作栏 -->
    <div v-if="files && files.length > 0" class="batch-actions">
      <div class="batch-info">批量操作</div>
      <div class="batch-buttons">
        <el-button
          type="primary"
          size="small"
          @click="goToSplit"
        >
          文本块切分
        </el-button>
        <el-button
          type="warning"
          size="small"
          @click="goToEmbed"
        >
          文本块嵌入
        </el-button>
        <el-button type="danger" size="small" @click="goToBatchDelete">
          <el-icon><Delete /></el-icon>
          删除文件
        </el-button>
      </div>
    </div>

    <!-- 分页：固定在容器底部 -->
  <div class="pagination-container">
        <span class="pages-total">共 {{ totalPagesDisplay }} 页</span>
        <el-pagination
          v-model:currentPage="currentPage"
      :page-size="pageSize"
          layout="prev, pager, next, jumper"
          :total="pagination?.total || 0"
      :hide-on-single-page="false"
          @current-change="handleCurrentChange"
          background
        />
      </div>
    </div>

    <!-- 文件详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      title="文件详情"
      width="800px"
      destroy-on-close
      class="detail-dialog"
    >
      <FileDetail
        v-if="selectedFile && showDetailDialog"
        :kb-id="kbId"
        :file="selectedFile"
        @close="showDetailDialog = false"
      />
    </el-dialog>
  </div>
</template>

<style scoped>
.file-manager {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.file-manager-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.file-manager-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
  color: #303133;
}

.kb-info {
  display: flex;
  align-items: center;
}

.loading-container {
  padding: 20px;
  flex: 1;
}

.empty-container {
  padding: 60px 20px;
  text-align: center;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.files-container {
  width: 100%;
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  min-height: 0;
}

.search-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: center;
  padding: 12px 0 16px;
}

.search-input {
  width: 480px;
}

.files-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding: 0 5px;
}

.files-count {
  font-size: 14px;
  color: #606266;
}

.table-wrapper {
  flex: 1;
  min-height: 0;
}

.files-table {
  height: 100%;
}

.batch-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin: 8px 0 12px;
}

.batch-info {
  font-size: 13px;
  color: #606266;
}

.batch-buttons {
  display: flex;
  gap: 8px;
}

/* 占位行样式：浅色背景，禁用交互 */
.placeholder-row :deep(.el-table__cell) {
  background-color: #fafafa;
}

.placeholder-cell {
  height: 20px;
  opacity: 0.4;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-icon {
  font-size: 18px;
}

.pdf-icon {
  color: #f56c6c;
}

.word-icon {
  color: #409eff;
}

.text-icon {
  color: #67c23a;
}

.markdown-icon {
  color: #e6a23c;
}

.notebook-icon {
  color: #f56c6c;
}

.powerpoint-icon {
  color: #ff7300;
}

.default-icon {
  color: #909399;
}

.file-name {
  word-break: keep-all;
  white-space: nowrap;
  display: inline-block;
  max-width: 340px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
}

.file-type-tag {
  text-transform: uppercase;
}

.status-tag {
  min-width: 60px;
  text-align: center;
}

.segmentation-muted {
  color: #909399;
}

/* 操作按钮样式 - 横向排列 */
.action-buttons {
  display: flex;
  gap: 8px;
  justify-content: flex-start;
}

.action-button {
  padding: 6px 10px;
  display: flex;
  align-items: center;
}

.action-button .el-icon {
  margin-right: 4px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination-container {
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid #ebeef5;
}

.pages-total {
  font-size: 13px;
  color: #606266;
  padding-left: 4px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .action-buttons {
    flex-direction: column;
    gap: 5px;
  }

  .pagination-container {
    justify-content: center;
  }
}
</style>
