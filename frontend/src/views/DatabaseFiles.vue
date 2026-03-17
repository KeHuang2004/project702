<template>
  <div class="database-files-container">
    <!-- 侧边栏 -->
    <div class="sidebar">
      <!-- 知识库信息 -->
      <div class="database-info">
        <h3>{{ database.name || '知识库' }}</h3>
        <p class="description">{{ database.description || '暂无描述' }}</p>
        <div class="stats">
          <div class="stat-item">
            <span class="label">文件数量:</span>
            <span class="value">{{ fileCount }}</span>
          </div>
          <div class="stat-item">
            <span class="label">总大小:</span>
            <span class="value">{{ totalSize }}</span>
          </div>
        </div>
      </div>

      <!-- 操作按钮 - 纵向排列 -->
      <div class="sidebar-actions">
        <el-button
          type="primary"
          @click="showUploadDialog = true"
          class="action-button"
        >
          <el-icon><Plus /></el-icon>
          添加文档
        </el-button>

        <!-- 新增：知识库检索按钮 -->
        <el-button
          type="success"
          @click="goToRetrieve"
          class="action-button"
        >
          <el-icon><Search /></el-icon>
          知识库检索
        </el-button>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <div class="file-manager-wrapper">
        <FileManager
          ref="fileManagerRef"
          :key="fileManagerKey"
          :kb-id="kbId"
          @open-split="handleOpenSplit"
          @open-delete="handleOpenDelete"
          @open-embed="handleOpenEmbed"
        />
      </div>
    </div>

    <el-dialog
      v-model="showSplitDialog"
      title="文本块切分"
      width="900px"
      class="split-dialog"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
    >
      <ChunkSplitPanel
        :kb-id="kbId"
        @close="handleSplitClose"
        @done="handleSplitDone"
      />
    </el-dialog>

    <!-- 上传对话框 -->
    <el-dialog
      v-model="showUploadDialog"
      title="上传文档到知识库"
      width="800px"
      :before-close="handleDialogClose"
      class="upload-dialog"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
    >
      <div class="upload-wizard">
        <div class="step-content">
          <FileUploadStep
            v-model:files="uploadFiles"
            :knowledge-base-id="kbId"
            @next="handleUploadComplete"
            @prev="handleUploadClose"
          />
        </div>
      </div>
    </el-dialog>

    <el-dialog
      v-model="showDeleteDialog"
      title="删除文件"
      width="900px"
      class="delete-dialog"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
    >
      <FileDeletePanel
        :kb-id="kbId"
        @close="handleDeleteClose"
        @done="handleDeleteDone"
      />
    </el-dialog>

    <el-dialog
      v-model="showEmbedDialog"
      title="文本块嵌入"
      width="1000px"
      class="embed-dialog"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
    >
      <ChunkEmbeddingPanel
        :kb-id="kbId"
        @close="handleEmbedClose"
        @done="handleEmbedDone"
      />
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import FileManager from '@/components/FileManager.vue'
import FileUploadStep from '@/components/FileUploadStep.vue'
import ChunkSplitPanel from '@/components/ChunkSplitPanel.vue'
import FileDeletePanel from '@/components/FileDeletePanel.vue'
import ChunkEmbeddingPanel from '@/components/ChunkEmbeddingPanel.vue'
import { getKnowledgeBaseDetail, getKnowledgeBaseAttributes, fetchLatestDocumentPdf } from '@/api/knowledge'

// 路由相关
const route = useRoute()
const router = useRouter()
const kbId = computed(() => route.params.id)

// 响应式数据
const database = ref({
  name: '',
  description: ''
})
const files = ref([])
const fileCountValue = ref(0)
const totalSizeValue = ref(0)
const showUploadDialog = ref(false)
const showSplitDialog = ref(false)
const showDeleteDialog = ref(false)
const showEmbedDialog = ref(false)
const prefillLoading = ref(false)

// 上传相关
const uploadFiles = ref([])
const fileManagerRef = ref(null)
const fileManagerKey = ref(0) // 用于强制刷新FileManager组件
const LATEST_DOCS_UPLOAD_SEED_KEY = 'latest-docs-upload-seed'

// 计算属性 - 修复版本
const fileCount = computed(() => {
  const count = Number(fileCountValue.value) || 0
  console.log('当前知识库文件数量:', count)
  return count
})

const totalSize = computed(() => {
  const totalBytes = Number(totalSizeValue.value) || 0
  console.log('当前知识库总大小(bytes):', totalBytes)
  return formatFileSize(totalBytes)
})

// 方法
const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 加载知识库详情 - 修复版本
const loadKnowledgeBaseDetail = async () => {
  try {
    console.log('开始加载知识库详情，kbId:', kbId.value)
    const response = await getKnowledgeBaseDetail(kbId.value)
    console.log('知识库详情响应:', response)

    if (response.success && response.data) {
      database.value = {
        name: response.data.name || '',
        description: response.data.description || ''
      }
    }
  } catch (error) {
    console.error('获取知识库详情失败:', error)
    ElMessage.error('获取知识库信息失败')
  }
}

// 加载文件统计：仅取 files_list 与 total_size
const loadFiles = async () => {
  try {
    console.log('开始加载文件统计（files_list + total_size）kbId:', kbId.value)
    const kbAttrsRes = await getKnowledgeBaseAttributes(kbId.value, ['files_list', 'total_size'])
    const ids = kbAttrsRes?.data?.files_list || []
    const totalSizeBytes = parseInt(kbAttrsRes?.data?.total_size || 0, 10) || 0
    console.log('files_list IDs:', ids)

    fileCountValue.value = Array.isArray(ids) ? ids.length : 0
    totalSizeValue.value = totalSizeBytes
    files.value = []
  } catch (error) {
    console.error('获取文件列表失败:', error)
    files.value = []
    fileCountValue.value = 0
    totalSizeValue.value = 0
  }
}

// 刷新整个界面数据 - 增强版本
const refreshPageData = async () => {
  console.log('开始刷新页面数据...')
  try {
    // 显示加载提示
    const loadingMessage = ElMessage({
      message: '正在刷新数据...',
      type: 'info',
      duration: 0, // 不自动关闭
      showClose: true
    })

    // 并行加载知识库详情和文件列表
    await Promise.all([
      loadKnowledgeBaseDetail(),
      loadFiles()
    ])

    // 强制刷新 FileManager 组件
    fileManagerKey.value += 1

    // 等待下一个 tick 确保组件重新渲染
    await nextTick()

    // 如果 FileManager 组件暴露了刷新方法，调用它
    if (fileManagerRef.value) {
      if (fileManagerRef.value.refreshFiles) {
        await fileManagerRef.value.refreshFiles()
      } else if (fileManagerRef.value.getFiles) {
        await fileManagerRef.value.getFiles()
      }
    }

    // 关闭加载提示
    loadingMessage.close()

    console.log('页面数据刷新完成')
    console.log('当前知识库文件:', files.value)
    ElMessage.success('数据已刷新')
  } catch (error) {
    console.error('刷新页面数据失败:', error)
    ElMessage.error('刷新数据失败，请重试')
  }
}

const handleOpenSplit = () => {
  showSplitDialog.value = true
}

const handleOpenDelete = () => {
  showDeleteDialog.value = true
}

const handleOpenEmbed = () => {
  showEmbedDialog.value = true
}

const sanitizePdfName = (name, fallbackId) => {
  const base = String(name || '').trim() || `article-${fallbackId || Date.now()}`
  const safe = base.replace(/[\\/:*?"<>|]/g, '_')
  return safe.toLowerCase().endsWith('.pdf') ? safe : `${safe}.pdf`
}

const buildPreviewUrl = (item) => {
  const articleId = String(item?.article_id || '').trim()
  const fromItem = String(item?.preview_url || '').trim()
  if (fromItem) {
    return fromItem
  }
  if (!articleId) {
    return ''
  }
  return `https://ship-research.com/cn/article/pdf/preview/${articleId}.pdf`
}

const loadLatestDocsSeed = () => {
  const raw = sessionStorage.getItem(LATEST_DOCS_UPLOAD_SEED_KEY)
  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw)
  } catch (e) {
    sessionStorage.removeItem(LATEST_DOCS_UPLOAD_SEED_KEY)
    return null
  }
}

const prefillUploadFilesFromLatestDocs = async () => {
  const seed = loadLatestDocsSeed()
  const targetKbId = Number(kbId.value)
  if (!seed || Number(seed.targetKbId) !== targetKbId) {
    return
  }

  const items = Array.isArray(seed.items) ? seed.items : []
  if (!items.length) {
    sessionStorage.removeItem(LATEST_DOCS_UPLOAD_SEED_KEY)
    return
  }

  prefillLoading.value = true
  const prepared = []
  const failedNames = []
  for (let i = 0; i < items.length; i += 1) {
    const item = items[i] || {}
    const previewUrl = buildPreviewUrl(item)
    if (!previewUrl) {
      failedNames.push(item?.name || `第${i + 1}篇`)
      continue
    }

    try {
      const blob = await fetchLatestDocumentPdf(previewUrl)
      const articleId = String(item?.article_id || '').trim()
      const filename = sanitizePdfName(item?.name, articleId || i + 1)
      const file = new File([blob], filename, { type: 'application/pdf' })
      prepared.push({
        uid: `latest-doc-${Date.now()}-${i}`,
        name: file.name,
        size: file.size,
        raw: file,
        uploadStatus: 'waiting',
        uploadProgress: 0,
        errorMessage: '',
      })
    } catch (e) {
      failedNames.push(item?.name || `第${i + 1}篇`)
    }
  }

  sessionStorage.removeItem(LATEST_DOCS_UPLOAD_SEED_KEY)
  uploadFiles.value = prepared

  if (prepared.length > 0) {
    ElMessage.success(`已自动载入 ${prepared.length} 个待上传文件`)
  }
  if (failedNames.length > 0) {
    ElMessage.warning(`有 ${failedNames.length} 个文件载入失败，可在上传页手动补充`) 
  }
  prefillLoading.value = false
}

const maybeOpenUploadFromRoute = async () => {
  const shouldOpen = String(route.query.openUpload || '') === '1'
  if (!shouldOpen) {
    return
  }

  showUploadDialog.value = true
  const shouldPrefill = String(route.query.prefillLatestDocs || '') === '1'
  if (shouldPrefill) {
    await prefillUploadFilesFromLatestDocs()
  }

  const nextQuery = { ...route.query }
  delete nextQuery.openUpload
  delete nextQuery.prefillLatestDocs
  router.replace({ path: route.path, query: nextQuery })
}

// 处理对话框关闭
const handleDialogClose = (done) => {
  resetUploadState()
  done()
}

const handleUploadClose = () => {
  resetUploadState()
  showUploadDialog.value = false
}

// 重置上传状态
const resetUploadState = () => {
  uploadFiles.value = []
}

// 上传完成回调
const handleUploadComplete = async () => {
  showUploadDialog.value = false
  resetUploadState()
  await refreshPageData()
}

const handleSplitClose = () => {
  showSplitDialog.value = false
}

const handleSplitDone = async () => {
  showSplitDialog.value = false
  await refreshPageData()
}

const handleDeleteClose = () => {
  showDeleteDialog.value = false
}

const handleDeleteDone = async () => {
  showDeleteDialog.value = false
  await refreshPageData()
}

const handleEmbedClose = () => {
  showEmbedDialog.value = false
}

const handleEmbedDone = async () => {
  showEmbedDialog.value = false
  await refreshPageData()
}


// 跳转到检索页面
const goToRetrieve = () => {
  router.push({
    name: `KnowledgeBaseRetrieve`, // 确保路由名称正确
    params: { kbId: kbId.value },
    query: {
      kbName: database.value.name // 传递知识库名称
    }
  })
}


// 生命周期
onMounted(() => {
  console.log('DatabaseFiles 组件挂载，kbId:', kbId.value)
  if (kbId.value) {
    loadKnowledgeBaseDetail()
    loadFiles()
    maybeOpenUploadFromRoute()
  }
})

// 监听路由变化
watch(() => kbId.value, (newKbId) => {
  console.log('路由变化，新的 kbId:', newKbId)
  if (newKbId) {
    loadKnowledgeBaseDetail()
    loadFiles()
    // 重置 fileManagerKey 以强制刷新组件
    fileManagerKey.value += 1
    maybeOpenUploadFromRoute()
  }
}, { immediate: true })

// 暴露刷新方法给外部使用（可选）
defineExpose({
  refreshPageData
})
</script>

<style scoped>
.database-files-container {
  display: flex;
  height: 100%;
  background-color: #f5f7fa;
}

/* 侧边栏样式 - 修复版本 */
.sidebar {
  width: 280px;
  min-width: 280px;
  background: white;
  border-right: 1px solid #e4e7ed;
  padding: 24px;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  gap: 24px;
  overflow-y: auto;
}

.database-info {
  flex-shrink: 0;
}

.database-info h3 {
  margin: 0 0 12px 0;
  color: #303133;
  font-size: 1.3em;
  font-weight: 600;
  line-height: 1.2;
  word-break: break-word;
}

.database-info .description {
  color: #606266;
  font-size: 0.9em;
  line-height: 1.5;
  margin-bottom: 20px;
  word-wrap: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #f8f9fa;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #dee2e6;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-item .label {
  color: #6c757d;
  font-size: 0.9em;
  font-weight: 500;
}

.stat-item .value {
  color: #212529;
  font-weight: 600;
  font-size: 0.9em;
}

/* 侧边栏操作按钮样式 - 修复版本 */
.sidebar-actions {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-top: auto; /* 将按钮推到底部 */
  width: 100%;
}

.action-button {
  width: 100%;
  height: 44px;
  display: flex;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.action-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.action-button .el-icon {
  font-size: 16px;
}

/* 确保Element Plus按钮内容居中对齐 */
.action-button :deep(.el-button__content) {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
}

/* 主按钮样式 */
.action-button.el-button--primary {
  background: linear-gradient(135deg, #409eff, #66b3ff);
  border: none;
}

.action-button.el-button--primary:hover {
  background: linear-gradient(135deg, #337ecc, #5aa3e6);
}

/* 成功按钮样式 */
.action-button.el-button--success {
  background: linear-gradient(135deg, #409eff, #66b3ff);
  border: none;
}

.action-button.el-button--success:hover {
  background: linear-gradient(135deg, #337ecc, #5aa3e6);
}

/* 主内容区样式 */
.main-content {
  flex: 1;
  padding: 20px;
  overflow: hidden;
  min-width: 0;
}

.file-manager-wrapper {
  height: 100%;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

/* 上传对话框样式 */
.upload-dialog {
  --el-dialog-border-radius: 12px;
}

.upload-wizard {
  min-height: 500px;
  display: flex;
  flex-direction: column;
}

/* 步骤指示器 */
.steps-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 30px;
  padding: 20px 0;
  border-bottom: 1px solid #e4e7ed;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  position: relative;
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #ddd;
  color: #666;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  transition: all 0.3s ease;
}

.step-item.active .step-number {
  background: #409eff;
  color: white;
}

.step-item.completed .step-number {
  background: #67c23a;
  color: white;
}

.step-title {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.step-item.active .step-title {
  color: #409eff;
}

.step-item.completed .step-title {
  color: #67c23a;
}

.step-line {
  width: 80px;
  height: 2px;
  background: #ddd;
  margin: 0 20px;
  transition: all 0.3s ease;
}

.step-line.completed {
  background: #67c23a;
}

/* 步骤内容 */
.step-content {
  flex: 1;
  overflow-y: auto;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .sidebar {
    width: 260px;
    min-width: 260px;
    padding: 20px;
  }

  .upload-dialog {
    width: 95% !important;
  }
}

@media (max-width: 768px) {
  .database-files-container {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
    min-width: auto;
    height: auto;
    border-right: none;
    border-bottom: 1px solid #e4e7ed;
  }

  .sidebar-actions {
    flex-direction: row;
    gap: 12px;
  }

  .upload-dialog {
    width: 98% !important;
    margin: 5px auto;
  }

  .steps-indicator {
    padding: 15px 10px;
  }

  .step-line {
    width: 40px;
    margin: 0 10px;
  }
}
</style>
