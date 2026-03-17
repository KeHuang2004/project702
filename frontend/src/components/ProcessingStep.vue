<template>
  <div class="processing-step">
    <div class="step-card">
      <div class="card-header">
        <h2>文档处理中</h2>
        <p>正在对上传的文件进行分段处理，请稍候...</p>
      </div>

      <div class="card-content">
        <!-- 基本信息摘要 -->
        <div class="info-summary">
          <h3>知识库信息</h3>
          <div class="summary-items">
            <div class="summary-item">
              <span class="summary-label">名称：</span>
              <span class="summary-value">{{ basicInfo.name }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">分段策略：</span>
              <span class="summary-value">{{ getStrategyLabel(chunkSettings.strategy) }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">分段大小：</span>
              <span class="summary-value">{{ chunkSettings.chunkSize }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">重叠长度：</span>
              <span class="summary-value">{{ chunkSettings.chunkOverlap }}</span>
            </div>
          </div>
        </div>

        <!-- 文件处理状态 -->
        <div class="files-section">
          <h3>文件处理状态 ({{ processedFiles.length }})</h3>
          <div class="files-list">
            <div
              v-for="file in processedFiles"
              :key="file.name || file.fileName"
              class="file-status-item"
            >
              <div class="file-info">
                <el-icon class="file-icon">
                  <Document v-if="file.name?.endsWith('.pdf')" />
                  <Edit v-else />
                </el-icon>
                <div class="file-details">
                  <div class="file-name">{{ file.name || file.fileName }}</div>
                  <div class="file-size">{{ formatFileSize(file.size || 0) }}</div>
                </div>
              </div>
              <div class="status-section">
                <el-tag :type="getProcessStatusType(file.status)" size="small">
                  {{ getProcessStatusText(file.status) }}
                </el-tag>
              </div>

              <!-- 错误信息 -->
              <div v-if="file.status === 'error'" class="error-message">
                <el-icon class="error-icon"><Warning /></el-icon>
                <span>{{ file.errorMessage || '处理失败' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 总体进度 -->
        <div class="overall-progress">
          <div class="progress-header">
            <h3>总体进度</h3>
            <span class="progress-text">
              {{ completedCount }} / {{ processedFiles.length }} 完成
            </span>
          </div>
          <el-progress
            :percentage="overallProgress"
            :stroke-width="8"
            :color="progressColor"
          />
          <div class="progress-stats">
            <span class="stat-item success">
              <el-icon><SuccessFilled /></el-icon>
              成功: {{ completedCount }}
            </span>
            <span v-if="processingCount > 0" class="stat-item processing">
              <el-icon><Loading /></el-icon>
              处理中: {{ processingCount }}
            </span>
            <span v-if="failedCount > 0" class="stat-item failed">
              <el-icon><CircleCloseFilled /></el-icon>
              失败: {{ failedCount }}
            </span>
          </div>
        </div>

        <!-- 处理失败重试选项 -->
        <div v-if="hasFailedFiles && !isProcessing" class="retry-section">
          <el-alert
            title="部分文件处理失败"
            type="warning"
            :closable="false"
            class="retry-alert"
          >
            <template #default>
              <p>有 {{ failedCount }} 个文件处理失败，你可以选择重试或跳过这些文件继续。</p>
            </template>
          </el-alert>
          <div class="retry-actions">
            <el-button @click="retryFailedFiles" type="warning" :loading="isRetrying">
              <el-icon><RefreshRight /></el-icon>
              重试失败文件
            </el-button>
            <el-button @click="skipFailedFiles" type="info">
              <el-icon><CircleClose /></el-icon>
              跳过失败文件
            </el-button>
          </div>
        </div>

        <!-- 处理中状态 -->
        <div v-if="isProcessing" class="processing-indicator">
          <el-icon class="rotating"><Loading /></el-icon>
          <span>正在处理文档，请耐心等待...</span>
        </div>
      </div>

      <div class="card-footer">
        <el-button @click="handlePrev" size="large" :disabled="isProcessing">
          上一步
        </el-button>
        <el-button
          type="primary"
          @click="handleSubmit"
          size="large"
          :disabled="!canProceed"
          :loading="isSubmitting"
        >
          {{ isSubmitting ? '提交中...' : '完成上传' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Document,
  Edit,
  Warning,
  SuccessFilled,
  Loading,
  CircleCloseFilled,
  RefreshRight,
  CircleClose
} from '@element-plus/icons-vue'
import { getProcessingStatus, startKnowledgeBaseProcessing } from '@/api/knowledge'

// Props
const props = defineProps({
  basicInfo: {
    type: Object,
    required: true
  },
  files: {
    type: Array,
    required: true
  },
  chunkSettings: {
    type: Object,
    required: true
  }
})

// Emits
const emit = defineEmits(['complete', 'prev'])

// 响应式数据
const processedFiles = ref([])
const isProcessing = ref(true)
const isSubmitting = ref(false)
const isRetrying = ref(false)
const processingTimer = ref(null)
const maxRetries = ref(3)
const currentRetry = ref(0)

// 计算属性
const completedCount = computed(() => {
  return processedFiles.value.filter(f => f.status === 'completed').length
})

const failedCount = computed(() => {
  return processedFiles.value.filter(f => f.status === 'error').length
})

const processingCount = computed(() => {
  return processedFiles.value.filter(f => f.status === 'processing').length
})

const hasFailedFiles = computed(() => failedCount.value > 0)

const overallProgress = computed(() => {
  if (processedFiles.value.length === 0) return 0
  return Math.round((completedCount.value / processedFiles.value.length) * 100)
})

const progressColor = computed(() => {
  if (failedCount.value > 0 && completedCount.value === 0) return '#f56c6c'
  if (overallProgress.value === 100) return '#67c23a'
  if (overallProgress.value >= 50) return '#409eff'
  return '#e6a23c'
})

const canProceed = computed(() => {
  return !isProcessing.value &&
         (completedCount.value > 0 || (hasFailedFiles.value && !isRetrying.value))
})

// 工具方法
const getStrategyLabel = (strategy) => {
  const labels = {
    'recursive_character': '递归字符分割',
    'token_text': '固定长度分割',
    'SemanticChunker': '语义分割'
  }
  return labels[strategy] || strategy
}

const getProcessStatusType = (status) => {
  const types = {
    'waiting': 'info',
    'pending': 'info',
    'processing': 'warning',
    'completed': 'success',
    'success': 'success',
    'error': 'danger',
    'failed': 'danger'
  }
  return types[status] || 'info'
}

const getProcessStatusText = (status) => {
  const texts = {
    'waiting': '等待处理',
    'pending': '等待处理',
    'processing': '处理中',
    'completed': '处理完成',
    'success': '处理完成',
    'error': '处理失败',
    'failed': '处理失败'
  }
  return texts[status] || '未知状态'
}

const formatFileSize = (size) => {
  if (!size || size === 0) return '0 B'
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB'
  return (size / 1024 / 1024).toFixed(1) + ' MB'
}

// 初始化处理文件列表
const initializeProcessedFiles = () => {
  console.log('初始化处理文件列表:', props.files)

  processedFiles.value = props.files.map(file => ({
    fileId: file.id || file.fileId || file.name,
    name: file.name,
    fileName: file.name,
    size: file.size || 0,
    status: 'completed',
    progress: 100,
    errorMessage: ''
  }))

  console.log('初始化后的处理文件:', processedFiles.value)
}

// 获取处理状态
const fetchProcessingStatus = async () => {
  // 防止重复调用
  if (fetchingStatus) {
    console.log('状态获取中，跳过本次调用')
    return
  }

  try {
    fetchingStatus = true
    console.log('获取处理状态，知识库ID:', props.basicInfo.id)

    if (!props.basicInfo.id) {
      console.error('知识库ID不存在')
      throw new Error('知识库ID不存在')
    }

    const response = await getProcessingStatus(props.basicInfo.id)
    console.log('处理状态响应:', response)

    if (response && response.data) {
      updateProcessingStatus(response.data)
    } else {
      console.warn('处理状态响应数据为空')
    }
  } catch (error) {
    console.error('获取处理状态失败:', error)

    // 增加重试机制
    if (currentRetry.value < maxRetries.value) {
      currentRetry.value++
      console.log(`重试获取状态 (${currentRetry.value}/${maxRetries.value})`)
      setTimeout(() => {
        if (isProcessing.value) {
          fetchProcessingStatus()
        }
      }, 5000) // 5秒后重试
      return
    }

    // 处理错误...
    if (error.response?.status === 404) {
      ElMessage.error('知识库不存在，请重新创建')
      emit('prev')
      return
    }

    processedFiles.value.forEach(file => {
      if (file.status === 'pending' || file.status === 'processing') {
        file.status = 'error'
        file.errorMessage = error.message || '获取处理状态失败'
      }
    })

    stopProcessingTimer()
    ElMessage.error('获取文件处理状态失败，请检查网络连接或重试')
  } finally {
    fetchingStatus = false
  }
}

// 更新处理状态
const updateProcessingStatus = (statusData) => {
  console.log('更新处理状态:', statusData)

  // 重置重试计数
  currentRetry.value = 0

  // 兼容不同的API响应格式
  let fileStatuses = []

  if (Array.isArray(statusData)) {
    fileStatuses = statusData
  } else if (statusData.fileStatuses) {
    fileStatuses = statusData.fileStatuses
  } else if (statusData.files) {
    fileStatuses = statusData.files
  } else if (statusData.data) {
    fileStatuses = Array.isArray(statusData.data) ? statusData.data : [statusData.data]
  }

  console.log('提取的文件状态列表:', fileStatuses)

  if (!Array.isArray(fileStatuses) || fileStatuses.length === 0) {
    console.warn('处理状态数据格式错误或为空:', statusData)
    return
  }

  // 记录状态变化
  let hasStatusChanges = false
  let hasUpdates = false

  processedFiles.value.forEach(file => {
    const serverStatus = fileStatuses.find(s => {
      if (s.fileId && file.fileId && s.fileId === file.fileId) return true
      const fileName = s.fileName || s.name || s.file_name
      return fileName === file.name
    })

    if (serverStatus) {
      const oldStatus = file.status
      const newStatus = normalizeStatus(serverStatus.status || serverStatus.processing_status || 'pending')

      // 只有状态真正改变时才更新
      if (oldStatus !== newStatus) {
        console.log(`文件 ${file.name} 状态变化: ${oldStatus} -> ${newStatus}`)
        file.status = newStatus
        hasStatusChanges = true
        hasUpdates = true
      }

      // 更新其他字段
      const oldProgress = file.progress
      const newProgress = serverStatus.progress || (newStatus === 'completed' ? 100 : 0)
      if (oldProgress !== newProgress) {
        file.progress = newProgress
        hasUpdates = true
      }

      const oldErrorMessage = file.errorMessage
      const newErrorMessage = serverStatus.errorMessage || serverStatus.error_message || serverStatus.error || ''
      if (oldErrorMessage !== newErrorMessage) {
        file.errorMessage = newErrorMessage
        hasUpdates = true
      }
    } else {
      console.log(`服务器未返回文件 ${file.name} 的状态`)
      // 如果文件还在等待中，标记为处理中
      if (file.status === 'pending') {
        console.log(`文件 ${file.name} 从 pending 变为 processing`)
        file.status = 'processing'
        hasStatusChanges = true
        hasUpdates = true
      }
    }
  })

  // 只有在有真实变化时才检查是否完成
  if (hasStatusChanges) {
    console.log('检测到状态变化，检查是否所有文件都处理完成')

    // 检查是否所有文件都处理完成
    const allProcessed = processedFiles.value.every(f =>
      f.status === 'completed' || f.status === 'error'
    )

    if (allProcessed && isProcessing.value) {
      console.log('所有文件处理完成')
      stopProcessingTimer()

      if (completedCount.value > 0) {
        ElMessage.success(`文档处理完成！成功处理 ${completedCount.value} 个文件`)
      }

      if (hasFailedFiles.value) {
        ElMessage.warning(`有 ${failedCount.value} 个文件处理失败`)
      }
    }
  } else if (!hasUpdates) {
    console.log('无状态变化，继续等待...')
  }
}

let fetchingStatus = false



// 标准化状态名称
const normalizeStatus = (status) => {
  if (!status) return 'pending'

  const statusLower = status.toLowerCase()

  if (statusLower === 'success' || statusLower === 'finished' || statusLower === 'done') {
    return 'completed'
  } else if (statusLower === 'failed' || statusLower === 'failure' || statusLower === 'fail') {
    return 'error'
  } else if (statusLower === 'running' || statusLower === 'in_progress') {
    return 'processing'
  }

  return status
}

// 启动处理状态轮询
const startProcessingTimer = () => {
  console.log('启动处理状态轮询')

  // 立即获取一次状态
  fetchProcessingStatus()

  // 更高频率轮询，降低前端延迟感知
  processingTimer.value = setInterval(() => {
    if (isProcessing.value && !fetchingStatus) {
      fetchProcessingStatus()
    }
  }, 1000)
}

// 显式启动后端处理
const triggerBackendProcessing = async () => {
  try {
    console.log('触发后端处理:', props.basicInfo.id, props.chunkSettings)
    await startKnowledgeBaseProcessing(props.basicInfo.id, props.chunkSettings)
  } catch (error) {
    console.error('触发后端处理失败:', error)
    ElMessage.error('启动处理失败，请重试')
    throw error
  }
}

// 停止处理状态轮询
const stopProcessingTimer = () => {
  if (processingTimer.value) {
    clearInterval(processingTimer.value)
    processingTimer.value = null
  }
  isProcessing.value = false
  console.log('停止处理状态轮询')
}

// 重试失败的文件
const retryFailedFiles = async () => {
  try {
    isRetrying.value = true

    const result = await ElMessageBox.confirm(
      `确定要重试 ${failedCount.value} 个处理失败的文件吗？`,
      '确认重试',
      {
        confirmButtonText: '确定重试',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    if (result) {
      // 重置失败文件的状态
      processedFiles.value.forEach(file => {
        if (file.status === 'error') {
          file.status = 'pending'
          file.progress = 0
          file.errorMessage = ''
        }
      })

      // 重新开始处理
      isProcessing.value = true
      currentRetry.value = 0
      startProcessingTimer()

      ElMessage.info('正在重新处理失败的文件...')
    }
  } catch {
    // 取消操作
  } finally {
    isRetrying.value = false
  }
}

// 跳过失败的文件
const skipFailedFiles = async () => {
  try {
    const result = await ElMessageBox.confirm(
      `确定要跳过 ${failedCount.value} 个处理失败的文件吗？跳过后这些文件将不会被包含在知识库中。`,
      '确认跳过',
      {
        confirmButtonText: '确定跳过',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    if (result) {
      // 移除失败的文件
      processedFiles.value = processedFiles.value.filter(f => f.status !== 'error')
      ElMessage.success('已跳过处理失败的文件')
    }
  } catch {
    // 取消操作
  }
}

// 处理上一步
const handlePrev = () => {
  emit('prev')
}

// 处理提交
const handleSubmit = async () => {
  if (completedCount.value === 0) {
    ElMessage.error('没有成功处理的文件，无法完成创建')
    return
  }

  try {
    isSubmitting.value = true

    const result = await ElMessageBox.confirm(
      `成功处理了 ${completedCount.value} 个文件${
        hasFailedFiles.value ? `，${failedCount.value} 个文件处理失败` : ''
      }。`,
      '确认完成',
      {
        confirmButtonText: '完成',
        cancelButtonText: '取消',
        type: 'success'
      }
    )

    if (result) {
      emit('complete')
    }
  } catch {
    // 取消操作
  } finally {
    isSubmitting.value = false
  }
}

// 生命周期
onMounted(() => {
  console.log('ProcessingStep 组件挂载')
  console.log('Props:', props)

  // 验证必要的props
  if (!props.basicInfo?.id) {
    ElMessage.error('知识库ID缺失，无法开始处理')
    emit('prev')
    return
  }

  if (!props.files || props.files.length === 0) {
    ElMessage.error('没有文件需要处理')
    emit('prev')
    return
  }

  // 新行为：不再自动触发后端处理，仅展示上传完成摘要
  initializeProcessedFiles()
  isProcessing.value = false
})

onUnmounted(() => {
  console.log('ProcessingStep 组件卸载')
  stopProcessingTimer()
})
</script>

<style scoped>
.processing-step {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  min-height: 100vh;
  padding: 2rem 1rem;
}

.step-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  padding: 2rem;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  max-width: 800px;
  width: 100%;
}

.card-header {
  text-align: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(229, 231, 235, 0.3);
}

.card-header h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 0.5rem;
}

.card-header p {
  color: #6b7280;
  margin: 0;
}

.card-content {
  margin-bottom: 2rem;
}

.info-summary {
  background: #f8fafc;
  border-radius: 0.5rem;
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.info-summary h3 {
  margin: 0 0 1rem 0;
  color: #1f2937;
  font-size: 1.1rem;
}

.summary-items {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.summary-item {
  display: flex;
  align-items: center;
}

.summary-label {
  font-weight: 500;
  color: #6b7280;
  margin-right: 0.5rem;
}

.summary-value {
  color: #1f2937;
}

.files-section {
  margin-bottom: 2rem;
}

.files-section h3 {
  margin: 0 0 1rem 0;
  color: #1f2937;
  font-size: 1.1rem;
}

.files-list {
  space-y: 1rem;
}

.file-status-item {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 1rem;
  margin-bottom: 1rem;
}

.file-info {
  display: flex;
  align-items: center;
  margin-bottom: 0.5rem;
}

.file-icon {
  font-size: 1.5rem;
  color: #6b7280;
  margin-right: 1rem;
}

.file-details {
  flex: 1;
}

.file-name {
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 0.25rem;
}

.file-size {
  font-size: 0.875rem;
  color: #6b7280;
}

.status-section {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.chunks-info {
  font-size: 0.875rem;
  color: #6b7280;
}

.progress-wrapper {
  margin-top: 0.5rem;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 0.25rem;
  color: #dc2626;
  font-size: 0.875rem;
  margin-top: 0.5rem;
}

.error-icon {
  color: #dc2626;
}

.overall-progress {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.progress-header h3 {
  margin: 0;
  color: #1f2937;
  font-size: 1.1rem;
}

.progress-text {
  color: #6b7280;
  font-size: 0.875rem;
}

.progress-stats {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
  justify-content: center;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
}

.stat-item.success {
  color: #16a34a;
}

.stat-item.processing {
  color: #ea580c;
}

.stat-item.failed {
  color: #dc2626;
}

.retry-section {
  margin-bottom: 2rem;
}

.retry-alert {
  margin-bottom: 1rem;
}

.retry-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.processing-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 2rem;
  color: #6b7280;
  font-size: 0.875rem;
}

.rotating {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.card-footer {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(229, 231, 235, 0.3);
}

@media (max-width: 768px) {
  .processing-step {
    padding: 1rem;
  }

  .step-card {
    padding: 1.5rem;
  }

  .summary-items {
    grid-template-columns: 1fr;
  }

  .card-footer {
    flex-direction: column;
  }

  .retry-actions {
    flex-direction: column;
  }

  .progress-stats {
    flex-direction: column;
    align-items: center;
  }
}
</style>
