<template>
  <div class="file-detail">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <el-button type="text" @click="goBack" class="back-button">
          <el-icon><ArrowLeft /></el-icon>
          返回知识库
        </el-button>
        <div class="title-section">
          <h2>文件详情</h2>
          <!-- <p class="subtitle" v-if="loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            正在加载文件信息...
          </p>
          <p class="subtitle" v-else-if="fileDetail.filename">{{ fileDetail.filename }}</p>
          <p class="description" v-if="fileDetail.file_type && !loading">
            {{ getFileTypeDescription(fileDetail.file_type) }} · {{ formatFileSize(fileDetail.file_size) }}
          </p> -->
        </div>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="file-detail-container" v-loading="loading">
      <!-- 左侧概览信息 -->
      <div class="overview-panel">
        <el-card class="overview-card">
          <template #header>
            <div class="card-header">
              <el-icon><InfoFilled /></el-icon>
              <span>文件概览</span>
            </div>
          </template>

          <!-- 文件基本信息 -->
          <div class="file-info-section">
            <div class="info-item">
              <span class="info-label">文件名:</span>
              <span class="info-value" :title="fileDetail.filename">
                {{ truncateFileName(fileDetail.filename) }}
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">文件类型:</span>
              <el-tag :type="getFileTypeTagType(fileDetail.file_type)" size="small">
                {{ (fileDetail.file_type || '').toUpperCase() }}
              </el-tag>
            </div>
            <div class="info-item">
              <span class="info-label">文件大小:</span>
              <span class="info-value">{{ formatFileSize(fileDetail.file_size) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">处理状态:</span>
              <el-tag :type="getStatusTagType(fileDetail.status)" size="small">
                {{ getStatusText(fileDetail.status) }}
              </el-tag>
            </div>
            <div class="info-item">
              <span class="info-label">分割策略:</span>
              <span
                class="info-value"
                :class="{ muted: isSegmentationUnset(fileDetail.segmentation_strategy) }"
              >
                {{ getSegmentationStrategyText(fileDetail.segmentation_strategy) }}
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">分块长度:</span>
              <span class="info-value">{{ fileDetail.chunk_length != null ? fileDetail.chunk_length : '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">重叠长度:</span>
              <span class="info-value">{{ fileDetail.overlap_count != null ? fileDetail.overlap_count : '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">文本块数量:</span>
              <span class="info-value">{{ chunkCount }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">上传时间:</span>
              <span class="info-value">{{ fileDetail.upload_at || '-' }}</span>
            </div>
          </div>

          <el-divider />

          <!-- 操作按钮 -->
          <div class="action-section">
            <!-- <el-button
              type="primary"
              :icon="Search"
              @click="goToRetrieve"
              class="action-button"
            >
              在知识库中检索
            </el-button> -->
            <el-button
              type="default"
              :icon="Download"
              @click="exportChunks"
              :disabled="!chunks.items || chunks.items.length === 0"
              class="action-button"
            >
              导出文本块
            </el-button>
            <!-- <el-button
              type="info"
              :icon="Refresh"
              @click="refreshFileDetail"
              class="action-button"
            >
              刷新数据
            </el-button> -->
          </div>
        </el-card>
      </div>

      <!-- 右侧详细内容 -->
      <div class="content-panel">
        <!-- 错误信息显示 -->
        <el-alert
          v-if="fileDetail.status === 'error' && fileDetail.error_message"
          title="处理错误"
          :description="fileDetail.error_message"
          type="error"
          show-icon
          :closable="false"
          class="error-alert"
        />

        <!-- 文本块列表 -->
        <div class="chunks-section">
          <div class="chunks-header">
            <h3>文档内容块 ({{ displayedChunks.length }}/{{ chunks.total }})</h3>
            <div class="header-actions">
              <el-input
                v-model="searchKeyword"
                placeholder="搜索内容..."
                :prefix-icon="Search"
                clearable
                class="search-input"
                @input="filterChunks"
              />
              <el-select v-model="sortBy" @change="sortChunks" class="sort-select">
                <el-option label="按序号排序" value="index" />
                <el-option label="按长度排序" value="length" />
                <el-option label="按位置排序" value="position" />
              </el-select>
            </div>
          </div>

          <!-- 文本块为空状态 -->
          <div v-if="!chunks.items || chunks.items.length === 0" class="empty-chunks">
            <el-empty
              :image-size="100"
              description="暂无文本块数据"
            />
          </div>

          <!-- 文本块列表 -->
          <div v-else class="chunks-list">
            <el-card
              v-for="(chunk, index) in paginatedChunks"
              :key="chunk.id"
              class="chunk-card"
              shadow="hover"
            >
              <template #header>
                <div class="chunk-header">
                  <div class="chunk-meta">
                    <el-tag type="info" size="small" class="chunk-index">
                      #{{ chunk.chunk_index + 1 }}
                    </el-tag>
                    <span class="chunk-info">
                      ID: {{ chunk.id }}
                    </span>
                    <span class="chunk-info">
                      长度: {{ chunk.chunk_text ? chunk.chunk_text.length : 0 }}
                    </span>
                    <span class="chunk-info">
                      状态: {{ getChunkStatusText(chunk.status) }}
                    </span>
                    <span class="chunk-info" v-if="chunk.start_position !== undefined">
                      位置: {{ chunk.start_position }}-{{ chunk.end_position }}
                    </span>
                  </div>
                  <div class="chunk-actions">
                    <el-button
                      type="text"
                      size="small"
                      :icon="CopyDocument"
                      @click="copyChunkContent(chunk.chunk_text)"
                    >
                      复制
                    </el-button>
                    <el-button
                      type="text"
                      size="small"
                      :icon="View"
                      @click="viewChunkDetail(chunk)"
                    >
                      详情
                    </el-button>
                  </div>
                </div>
              </template>

              <!-- 文本内容 -->
              <div class="chunk-content">
                <div
                  class="chunk-text"
                  :class="{ 'chunk-text-collapsed': !chunk.expanded }"
                >
                  {{ chunk.chunk_text }}
                </div>
                <el-button
                  v-if="chunk.chunk_text && chunk.chunk_text.length > 300"
                  type="text"
                  size="small"
                  @click="toggleChunkExpand(chunk)"
                  class="expand-button"
                >
                  {{ chunk.expanded ? '收起' : '展开全部' }}
                </el-button>

                <!-- 元数据信息 -->
                <div class="metadata-info">
                  <el-divider content-position="left">元数据</el-divider>
                  <div class="metadata-items">
                    <div class="meta-item" v-if="chunk.faiss_vector_id">
                      <span class="meta-label">向量ID:</span>
                      <span class="meta-value">{{ chunk.faiss_vector_id ? chunk.faiss_vector_id.substring(0, 8) + '...' : '未嵌入' }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </el-card>
          </div>

          <!-- 分页 -->
          <div v-if="displayedChunks.length > pageSize" class="pagination-container">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :total="displayedChunks.length"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleSizeChange"
              @current-change="handleCurrentChange"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 文本块详情对话框 -->
    <el-dialog
      v-model="chunkDetailVisible"
      title="文本块详情"
      width="70%"
      :before-close="handleCloseChunkDetail"
    >
      <div v-if="selectedChunk" class="chunk-detail-dialog">
        <div class="detail-meta">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="块ID">{{ selectedChunk.id }}</el-descriptions-item>
            <el-descriptions-item label="索引">{{ selectedChunk.chunk_index + 1 }}</el-descriptions-item>
            <el-descriptions-item label="字符数">{{ selectedChunk.chunk_text ? selectedChunk.chunk_text.length : 0 }}</el-descriptions-item>
            <el-descriptions-item label="文件ID">{{ selectedChunk.file_id }}</el-descriptions-item>
            <el-descriptions-item label="知识库ID">{{ selectedChunk.knowledge_base_id }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ getChunkStatusText(selectedChunk.status) }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ selectedChunk.created_at || '-' }}</el-descriptions-item>
            <el-descriptions-item label="开始位置" v-if="selectedChunk.start_position !== undefined">
              {{ selectedChunk.start_position }}
            </el-descriptions-item>
            <el-descriptions-item label="结束位置" v-if="selectedChunk.end_position !== undefined">
              {{ selectedChunk.end_position }}
            </el-descriptions-item>
            <el-descriptions-item label="向量ID" v-if="selectedChunk.faiss_vector_id">
              {{ selectedChunk.faiss_vector_id }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
        <div class="detail-content">
          <h4>完整内容:</h4>
          <div class="full-content">{{ selectedChunk.chunk_text }}</div>
        </div>
      </div>
      <template #footer>
        <el-button @click="chunkDetailVisible = false">关闭</el-button>
        <el-button type="primary" @click="copyChunkContent(selectedChunk.chunk_text)">
          复制内容
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, InfoFilled, Loading, Search, Download,
  CopyDocument, View, Refresh
} from '@element-plus/icons-vue'
import { getFileDetail, getChunkAttributesForIds } from '@/api/knowledge'

const route = useRoute()
const router = useRouter()

// 页面参数
const kbId = ref(route.params.kbId)
// fileId 现在可能来自 query（如 ?fileId=123），兼容旧的 params
const fileId = ref(route.params.fileId || route.query.fileId || null)

// 数据状态
const loading = ref(false)
const fileDetail = ref({})
const chunks = ref({ items: [], total: 0 })

// 搜索和排序
const searchKeyword = ref('')
const sortBy = ref('index')
const filteredChunks = ref([])
const displayedChunks = ref([])

// 分页
const currentPage = ref(1)
const pageSize = ref(20)

// 对话框
const chunkDetailVisible = ref(false)
const selectedChunk = ref(null)

const totalCharacters = computed(() => {
  if (!chunks.value.items) return 0
  return chunks.value.items.reduce((sum, chunk) => sum + (chunk.chunk_text ? chunk.chunk_text.length : 0), 0)
})

const averageLength = computed(() => {
  if (!chunks.value.items || chunks.value.items.length === 0) return 0
  return Math.round(totalCharacters.value / chunks.value.items.length)
})

const chunkCount = computed(() => {
  if (fileDetail.value && Array.isArray(fileDetail.value.chunks_list)) {
    return fileDetail.value.chunks_list.length
  }
  if (chunks.value && typeof chunks.value.total === 'number') {
    return chunks.value.total
  }
  return 0
})

const paginatedChunks = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return displayedChunks.value.slice(start, end)
})

const loadChunksByIds = async (chunkIds) => {
  if (!Array.isArray(chunkIds) || chunkIds.length === 0) {
    chunks.value = { items: [], total: 0 }
    displayedChunks.value = []
    return
  }

  const attrs = [
    'id',
    'file_id',
    'knowledge_base_id',
    'chunk_text',
    'chunk_index',
    'start_position',
    'end_position',
    'created_at',
    'embed_at',
    'status'
  ]

  try {
    const res = await getChunkAttributesForIds(chunkIds, attrs)
    const data = res?.data || null
    const items = Array.isArray(data?.items)
      ? data.items
      : data && typeof data === 'object'
        ? [data]
        : []

    const itemMap = new Map()
    items.forEach(item => {
      if (item?.id != null) {
        itemMap.set(item.id, item)
      }
    })

    const ordered = chunkIds
      .map(id => itemMap.get(id))
      .filter(Boolean)
      .map(item => ({ ...item, expanded: false }))

    chunks.value = { items: ordered, total: ordered.length }
    displayedChunks.value = [...ordered]
    filterChunks()
  } catch (error) {
    console.error('获取文本块列表失败:', error)
    chunks.value = { items: [], total: 0 }
    displayedChunks.value = []
  }
}

// 加载文件详情
const loadFileDetail = async () => {
  try {
    loading.value = true
    console.log('开始加载文件详情，kbId:', kbId.value, 'fileId:', fileId.value)

    const response = await getFileDetail(fileId.value)
    console.log('文件详情响应:', response)

    if (response.success && response.data) {
      fileDetail.value = response.data
      const chunkIds = fileDetail.value.chunks_list || []
      await loadChunksByIds(chunkIds)

      // 初始化展开状态
      console.log('文件详情加载成功:', fileDetail.value)
    } else {
      console.error('获取文件详情失败:', response.message)
      ElMessage.error('获取文件详情失败')
    }
  } catch (error) {
    console.error('获取文件详情失败:', error)
    ElMessage.error('获取文件详情失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 刷新文件详情
// const refreshFileDetail = async () => {
//   await loadFileDetail()
//   ElMessage.success('文件详情已刷新')
// }

// 返回知识库页面
const goBack = () => {
  router.push({
  path: `/knowledge_base/${kbId.value}/files`
  })
}

// 跳转到检索页面
// const goToRetrieve = () => {
//   router.push({
//     path: `/knowledge_base/${kbId.value}/retrieve`,
//     query: {
//       kbName: fileDetail.value.filename,
//       fileId: fileId.value
//     }
//   })
// }

// 截断文件名显示
const truncateFileName = (filename) => {
  if (!filename) return '-'
  if (filename.length <= 30) return filename
  return filename.substring(0, 27) + '...'
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

// 获取文件类型描述
const getFileTypeDescription = (type) => {
  const typeMap = {
    'pdf': 'PDF 文档',
    'docx': 'Word 文档',
    'txt': '文本文件',
    'md': 'Markdown 文档',
    'html': 'HTML 文档'
  }
  return typeMap[type] || type?.toUpperCase() || '未知类型'
}

// 获取文件类型标签类型
const getFileTypeTagType = (type) => {
  const typeMap = {
    'pdf': 'danger',
    'docx': 'primary',
    'txt': 'info',
    'md': 'success',
    'html': 'warning'
  }
  return typeMap[type] || 'info'
}

// 获取状态标签类型
const getStatusTagType = (status) => {
  const normalized = (status || '').toString().toLowerCase()
  const statusMap = {
    'completed': 'success',
    'splitted': 'success',
    'uploaded': 'success',
    'embedded': 'success',
    'pending': 'info',
    'uploading': 'warning',
    'uploading_pending': 'warning',
    'splitting': 'warning',
    're-splitting': 'warning',
    'processing': 'warning',
    'embedding': 'warning',
    're-embedding': 'warning',
    'error': 'danger',
    'failed': 'danger',
    'file_not_found': 'danger'
  }
  return statusMap[normalized] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const normalized = (status || '').toString().toLowerCase()
  const statusMap = {
    'completed': '完成',
    'splitted': '已切分',
    'uploaded': '已上传',
    'embedded': '已嵌入',
    'pending': '待处理',
    'uploading': '上传中',
    'uploading_pending': '等待上传',
    'splitting': '切分中',
    're-splitting': '重新切分中',
    'processing': '处理中',
    'embedding': '嵌入中',
    're-embedding': '重新嵌入中',
    'failed': '失败',
    'file_not_found': '文件缺失'
  }
  return statusMap[normalized] || '处理中'
}

const getChunkStatusText = (status) => {
  const normalized = (status || '').toString().toLowerCase()
  const statusMap = {
    'splitted': '已切分',
    'completed': '完成',
    'embedding': '嵌入中',
    'embedded': '已嵌入',
    're-embedding': '重新嵌入中',
    'failed': '失败'
  }
  return statusMap[normalized] || '—'
}

const isSegmentationUnset = (strategy) => strategy === null || typeof strategy === 'undefined' || strategy === ''

// 获取分割策略文本
const getSegmentationStrategyText = (strategy) => {
  if (isSegmentationUnset(strategy)) return '暂未切分'
  const normalized = String(strategy).toLowerCase()
  const strategyMap = {
    'recursive_character': '递归字符分割',
    'recursivecharactertextsplitter': '递归字符分割',
    'token': '固定长度分割',
    'token_based': '固定长度分割',
    'tokentextsplitter': '固定长度分割',
    'semantic': '语义分割',
    'semanticchunker': '语义分割'
  }
  return strategyMap[normalized] || strategy
}

// 过滤文本块
const filterChunks = () => {
  if (!searchKeyword.value.trim()) {
    displayedChunks.value = [...chunks.value.items]
  } else {
    const keyword = searchKeyword.value.toLowerCase()
    displayedChunks.value = chunks.value.items.filter(chunk =>
      chunk.chunk_text?.toLowerCase().includes(keyword)
    )
  }
  currentPage.value = 1 // 搜索后重置到第一页
  sortChunks()
}

// 排序文本块
const sortChunks = () => {
  if (sortBy.value === 'index') {
    displayedChunks.value.sort((a, b) => a.chunk_index - b.chunk_index)
  } else if (sortBy.value === 'length') {
    displayedChunks.value.sort((a, b) => {
      const aLen = a.chunk_text ? a.chunk_text.length : 0
      const bLen = b.chunk_text ? b.chunk_text.length : 0
      return bLen - aLen
    })
  } else if (sortBy.value === 'position') {
    displayedChunks.value.sort((a, b) => (a.start_position || 0) - (b.start_position || 0))
  }
}


// 切换文本块展开状态
const toggleChunkExpand = (chunk) => {
  chunk.expanded = !chunk.expanded
}

// 复制文本块内容
const copyChunkContent = async (content) => {
  if (!content) {
    ElMessage.warning('内容为空')
    return
  }

  try {
    await navigator.clipboard.writeText(content)
    ElMessage.success('内容已复制到剪贴板')
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败')
  }
}

// 查看文本块详情
const viewChunkDetail = (chunk) => {
  selectedChunk.value = chunk
  chunkDetailVisible.value = true
}

// 关闭文本块详情对话框
const handleCloseChunkDetail = () => {
  chunkDetailVisible.value = false
  selectedChunk.value = null
}

// 导出文本块
const exportChunks = () => {
  if (!chunks.value.items || chunks.value.items.length === 0) return

  const exportData = {
    file: {
      id: fileDetail.value.id,
      filename: fileDetail.value.filename,
      file_type: fileDetail.value.file_type,
      file_size: fileDetail.value.file_size,
      chunk_count: chunkCount.value,
      file_hash: fileDetail.value.file_hash
    },
    export_time: new Date().toISOString(),
    chunks: chunks.value.items.map(chunk => ({
      id: chunk.id,
      chunk_index: chunk.chunk_index,
      content: chunk.chunk_text,
      start_position: chunk.start_position,
      end_position: chunk.end_position,
      faiss_vector_id: chunk.faiss_vector_id,
      file_id: chunk.file_id,
      knowledge_base_id: chunk.knowledge_base_id,
      created_at: chunk.created_at
    })),
      statistics: {
        total_chunks: chunks.value.total,
        total_characters: totalCharacters.value,
        average_length: averageLength.value
      }
    }

  const blob = new Blob([JSON.stringify(exportData, null, 2)], {
    type: 'application/json'
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${fileDetail.value.filename.replace(/\.[^/.]+$/, "")}_文本块_${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('文本块数据已导出')
}

// 分页处理
const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
}

const handleCurrentChange = (page) => {
  currentPage.value = page
}

// 监听搜索关键词变化
watch(searchKeyword, () => {
  filterChunks()
})

// 监听排序方式变化
watch(sortBy, () => {
  sortChunks()
})

onMounted(() => {
  console.log('文件详情页面加载，kbId:', kbId.value, 'fileId:', fileId.value)
  loadFileDetail()
})
</script>

<style scoped>
.file-detail {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #f5f7fa;
}

/* 页面头部 */
.page-header {
  background: white;
  padding: 16px 24px;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-button {
  font-size: 14px;
  color: #606266;
  padding: 8px 12px;
}

.back-button:hover {
  color: #409eff;
  background: #f0f9ff;
}

.title-section h2 {
  margin: 0;
  color: #303133;
  font-size: 20px;
  font-weight: 600;
}

.subtitle {
  margin: 4px 0 0 0;
  color: #909399;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.description {
  margin: 4px 0 0 0;
  color: #606266;
  font-size: 13px;
  max-width: 900px; /* 适配大屏，减少换行 */
}

/* 主容器 */
.file-detail-container {
  flex: 1;
  display: flex;
  gap: 24px;
  padding: 24px;
  overflow: hidden;
}

/* 左侧概览面板 */
.overview-panel {
  width: 320px;
  flex-shrink: 0;
}

.overview-card {
  position: sticky;
  top: 0;
  height: fit-content;
  max-height: calc(100vh - 120px);
  overflow-y: auto;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #303133;
}

/* 文件信息区域 */
.file-info-section,
.chunk-config-section {
  margin-bottom: 16px;
}

.section-title {
  margin: 0 0 12px 0;
  color: #303133;
  font-size: 14px;
  font-weight: 600;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
}

.info-label {
  color: #909399;
  font-weight: 500;
  flex-shrink: 0;
  margin-right: 8px;
}

.info-value {
  color: #303133;
  font-weight: 500;
  text-align: right;
  word-break: break-all;
  flex: 1;
  max-width: 150px;
}

.info-value.muted {
  color: #909399;
}

/* 统计信息 */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}

.stat-item {
  text-align: center;
  padding: 12px 8px;
  background: #f8f9fb;
  border-radius: 6px;
}

.stat-number {
  font-size: 16px;
  font-weight: 700;
  color: #409eff;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 11px;
  color: #909399;
  line-height: 1.2;
}

/* 操作区域 */
.action-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-button {
  width: 100%;
  height: 36px;
}

/* 右侧内容面板 */
.content-panel {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}

.error-alert {
  margin-bottom: 16px;
}

/* 文本块区域 */
.chunks-section {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.chunks-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;
}

.chunks-header h3 {
  margin: 0;
  color: #303133;
  font-size: 18px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-input {
  width: 200px;
}

.sort-select {
  width: 140px;
}

/* 空状态 */
.empty-chunks {
  padding: 60px 20px;
  text-align: center;
}

/* 文本块列表 */
.chunks-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chunk-card {
  border-radius: 8px;
  transition: all 0.3s;
}

.chunk-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.chunk-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.chunk-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.chunk-index {
  font-weight: 600;
}

.chunk-info {
  font-size: 12px;
  color: #909399;
}

.chunk-actions {
  display: flex;
  gap: 8px;
}

/* 文本内容 */
.chunk-content {
  margin-top: 12px;
}

.chunk-text {
  line-height: 1.6;
  color: #303133;
  background: #f8f9fb;
  padding: 16px;
  border-radius: 6px;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
}

.chunk-text-collapsed {
  max-height: 150px;
  overflow: hidden;
  position: relative;
}

.chunk-text-collapsed::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 40px;
  background: linear-gradient(transparent, #f8f9fb);
}

.expand-button {
  margin-top: 8px;
  color: #409eff;
}

/* 元数据信息 */
.metadata-info {
  margin-top: 16px;
}

.metadata-items {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.meta-item {
  display: flex;
  font-size: 12px;
}

.meta-label {
  color: #909399;
  margin-right: 8px;
  font-weight: 500;
}

.meta-value {
  color: #303133;
  font-weight: 500;
  word-break: break-all;
}

/* 分页 */
.pagination-container {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

/* 详情对话框 */
.chunk-detail-dialog {
  max-height: 60vh;
  overflow-y: auto;
}

.detail-meta {
  margin-bottom: 20px;
}

.detail-content h4 {
  margin: 0 0 12px 0;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
}

.full-content {
  background: #f8f9fb;
  padding: 16px;
  border-radius: 6px;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #303133;
  max-height: 400px;
  overflow-y: auto;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .file-detail-container {
    flex-direction: column;
    gap: 16px;
  }

  .overview-panel {
    width: 100%;
    order: 1;
  }

  .content-panel {
    order: 0;
  }
}

@media (max-width: 768px) {
  .file-detail-container {
    padding: 16px;
  }

  .page-header {
    padding: 12px 16px;
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .chunks-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    flex-direction: column;
  }

  .search-input,
  .sort-select {
    width: 100%;
  }

  .chunk-meta {
    justify-content: flex-start;
  }

  .chunk-actions {
    margin-top: 8px;
  }

  .metadata-items {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 480px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .title-section h2 {
    font-size: 18px;
  }

  .chunks-header h3 {
    font-size: 16px;
  }
}

/* 加载状态优化 */
.el-skeleton {
  padding: 20px;
}

/* 高亮样式优化 */
mark {
  background-color: #ffeb3b !important;
  color: #333 !important;
  padding: 2px 4px !important;
  border-radius: 2px !important;
  font-weight: 500;
}

/* 滚动条样式 */
.overview-card::-webkit-scrollbar,
.content-panel::-webkit-scrollbar,
.full-content::-webkit-scrollbar {
  width: 6px;
}

.overview-card::-webkit-scrollbar-track,
.content-panel::-webkit-scrollbar-track,
.full-content::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.overview-card::-webkit-scrollbar-thumb,
.content-panel::-webkit-scrollbar-thumb,
.full-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.overview-card::-webkit-scrollbar-thumb:hover,
.content-panel::-webkit-scrollbar-thumb:hover,
.full-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 动画效果 */
.chunk-card {
  animation: fadeInUp 0.3s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 打印样式 */
@media print {
  .page-header,
  .overview-panel,
  .chunk-actions,
  .header-actions,
  .pagination-container {
    display: none;
  }

  .file-detail-container {
    padding: 0;
    gap: 0;
  }

  .chunks-section {
    box-shadow: none;
    padding: 0;
  }

  .chunk-card {
    break-inside: avoid;
    box-shadow: none;
    border: 1px solid #ddd;
    margin-bottom: 16px;
  }
}

/* 深色主题支持 */
@media (prefers-color-scheme: dark) {
  .file-detail {
    background-color: #1a1a1a;
    color: #e4e7ed;
  }

  .chunk-text {
    background: #2d2d2d;
    color: #e4e7ed;
  }

  .full-content {
    background: #2d2d2d;
    color: #e4e7ed;
  }
}
</style>
