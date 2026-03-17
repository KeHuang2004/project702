<template>
  <div class="file-upload-step">
    <div class="step-card">
      <div class="card-header">
          <h2>上传文件</h2>
        <p>支持 txt、pdf、doc、docx、rtf、md、xls、xlsx、csv、ppt、pptx、html、htm、json、xml，单文件大小不限（以服务器限制为准）</p>
      </div>

      <div class="card-content">
        <!-- 文件上传区域 -->
        <div class="upload-area">
          <el-upload
            ref="uploadRef"
            class="upload-dragger"
            drag
            :multiple="true"
            :auto-upload="false"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :before-upload="beforeUpload"
          >
            <el-icon class="el-icon--upload">
              <UploadFilled />
            </el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 txt、pdf、doc、docx、rtf、md、xls、xlsx、csv、ppt、pptx、html、htm、json、xml，单文件大小不限，文件数量不限
              </div>
            </template>
          </el-upload>
        </div>

        <!-- 已选文件列表 -->
        <div v-if="fileList.length > 0" class="file-list">
          <h3>已选择文件 ({{ fileList.length }})</h3>
          <div class="file-items">
            <div
              v-for="file in fileList"
              :key="file.uid"
              class="file-item"
            >
              <div class="file-info">
                <el-icon class="file-icon">
                  <Document v-if="file.name && file.name.toLowerCase().endsWith('.pdf')" />
                  <Edit v-else />
                </el-icon>
                <div class="file-details">
                  <div class="file-name">{{ file.name || '未知文件' }}</div>
                  <div class="file-size">{{ formatFileSize(file.size || 0) }}</div>

                  <!-- 修复：确保状态标签始终有有效的type值 -->
                  <div class="upload-status">
                    <el-tag
                      :type="getStatusType(file.uploadStatus)"
                      size="small"
                    >
                      {{ getStatusText(file.uploadStatus) }}
                    </el-tag>

                    <!-- 上传进度条 -->
                    <div v-if="file.uploadStatus === 'uploading'" class="progress-bar">
                      <el-progress
                        :percentage="file.uploadProgress || 0"
                        :stroke-width="4"
                        status="success"
                      />
                    </div>

                    <!-- 错误信息 -->
                    <div v-if="file.uploadStatus === 'error'" class="error-message">
                      {{ file.errorMessage || '上传失败' }}
                    </div>
                  </div>
                </div>
              </div>

              <el-button
                type="danger"
                size="small"
                text
                :disabled="isUploading"
                @click="removeFile(file)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </div>

        <!-- 上传进度提示 -->
        <div v-if="isUploading" class="upload-progress">
          <el-alert
            title="正在上传文件，请稍候..."
            type="info"
            :closable="false"
            show-icon
          >
            <template #default>
              <p>文件上传过程中请勿关闭页面</p>
            </template>
          </el-alert>
        </div>
      </div>

      <div class="card-footer">
        <el-button @click="handlePrev" size="large" :disabled="isUploading">
          关闭
        </el-button>
        <el-button
          type="primary"
          @click="handleNext"
          size="large"
          :disabled="fileList.length === 0 || isUploading"
          :loading="isUploading"
        >
          {{ uploadFinished ? '完成' : (isUploading ? '上传中...' : '上传文件') }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Document, Edit, Delete } from '@element-plus/icons-vue'
import request from '@/utils/request'

// Props
const props = defineProps({
  knowledgeBaseId: {
    type: [Number, String],
    required: true
  },
  files: {
    type: Array,
    default: () => []
  },
  chunkSettings: {
    type: Object,
    required: false,
    default: () => ({})
  }
})

// Emits
const emit = defineEmits(['update:files', 'next', 'prev'])

// 响应式数据
const uploadRef = ref()
const fileList = ref([])
const isUploading = ref(false)
const isInitializing = ref(false) // 初始化阶段无需触发轮询
const uploadFinished = ref(false)

// 计算属性
const allFilesUploaded = computed(() => {
  return fileList.value.length > 0 &&
    fileList.value.every(file => file.uploadStatus === 'success')
})

// 修复：防止递归调用的状态类型函数
const getStatusType = (status) => {
  if (!status || status === '') return 'info'

  const types = {
    'waiting': 'info',
    'uploading': 'warning',
    'uploading_pending': 'warning',
    'uploaded': 'success',
    'success': 'success',
    'error': 'danger'
  }

  return types[status] || 'info'
}

const getStatusText = (status) => {
  if (!status || status === '') return '等待上传'

  const texts = {
    'waiting': '等待上传',
    'uploading': '上传中',
    'uploading_pending': '文件处理中',
    'uploaded': '上传成功',
    'success': '上传成功',
    'error': '上传失败'
  }

  return texts[status] || '等待上传'
}

const formatFileSize = (size) => {
  if (!size || size === 0) return '0 B'
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB'
  return (size / 1024 / 1024).toFixed(1) + ' MB'
}

// 修复：防止递归的文件变化处理
const handleFileChange = (file, files) => {
  console.log('文件变化:', file.name, '文件数量:', files.length)

  // 防止在初始化时触发
  if (isInitializing.value) {
    console.log('初始化中，跳过文件变化处理')
    return
  }

  // 客户端不再强制限制文件大小与类型，大小与类型校验交由服务端处理

  const nameMap = new Set()
  const duplicates = []
  const deduped = []
  files.forEach(f => {
    const name = f?.name || f?.filename || ''
    if (name && nameMap.has(name)) {
      duplicates.push(name)
      return
    }
    if (name) {
      nameMap.add(name)
    }
    deduped.push(f)
  })

  if (duplicates.length > 0) {
    ElMessage.error(`已存在同名文件：${[...new Set(duplicates)].join('、')}`)
    files.splice(0, files.length, ...deduped)
  }

  // 关键修复：使用 nextTick 避免递归更新
  nextTick(() => {
    // 确保每个文件对象都有正确的状态属性
    files.forEach(f => {
      if (!f.uploadStatus) f.uploadStatus = 'waiting'
      if (typeof f.uploadProgress === 'undefined') f.uploadProgress = 0
      if (!f.errorMessage) f.errorMessage = ''
    })

    // 只有在文件数量真正改变时才更新
    if (fileList.value.length !== files.length) {
      fileList.value = [...files]
      updateModelFiles()
    }
  })
}

// 文件移除处理
const handleFileRemove = (file, files) => {
  console.log('移除文件:', file.name)
  fileList.value = [...files]
  updateModelFiles()
}
// 移除文件
const removeFile = (file) => {
  if (isUploading.value) {
    ElMessage.warning('文件上传中，无法删除')
    return
  }
  uploadRef.value?.handleRemove(file)
}

// 上传前验证
const beforeUpload = (file) => {
  console.log('文件验证:', {
    name: file.name,
    size: file.size,
    type: file.type,
    sizeInMB: (file.size / 1024 / 1024).toFixed(2)
  })

  // 客户端不再强制限制文件大小与类型

  // 检查文件名
  const invalidChars = /[<>:"/\\|?*]/
  if (invalidChars.test(file.name)) {
    ElMessage.error('文件名包含特殊字符，请重命名后再上传!')
    return false
  }

  console.log('文件验证通过:', file.name)
  return false // 阻止自动上传，我们手动控制
}

// 批量上传文件

const uploadAllFiles = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请至少选择一个文件')
    return false
  }

  console.log('检查知识库ID:', {
    knowledgeBaseId: props.knowledgeBaseId,
    type: typeof props.knowledgeBaseId,
    isValid: !!props.knowledgeBaseId
  })

  const kbId = Number.parseInt(String(props.knowledgeBaseId), 10)
  if (!kbId || Number.isNaN(kbId)) {
    ElMessage.error('知识库ID不存在，请重新创建知识库')
    return false
  }

  try {
    isUploading.value = true
    uploadFinished.value = false
    console.log('开始批量上传文件...')

    fileList.value.forEach(file => {
      file.uploadStatus = 'uploading'
      file.uploadProgress = 0
      file.errorMessage = ''
    })

    const filesToUpload = fileList.value.map(file => file.raw || file)
    const invalidFiles = filesToUpload.filter(file => !file || typeof file !== 'object' || !file.name)
    if (invalidFiles.length > 0) {
      throw new Error('存在无效的文件对象，请重新选择文件')
    }

    const baseUrl = (request?.defaults?.baseURL || '').replace(/\/$/, '')
    const formData = new FormData()
    filesToUpload.forEach(file => formData.append('files', file, file.name))

    const response = await fetch(`${baseUrl}/api/v1/files/${kbId}`, {
      method: 'POST',
      body: formData
    })

    if (!response.ok || !response.body) {
      throw new Error('上传流连接失败')
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
          if (payload.event === 'file' && payload.file) {
            const target = fileList.value.find(f => (f.name || f.filename) === payload.file.filename)
            if (target) {
              target.serverFileId = payload.file.file_id
              target.uploadStatus = 'success'
              target.uploadProgress = 100
              target.errorMessage = ''
            }
          }

          if (payload.event === 'error') {
            const target = fileList.value.find(f => (f.name || f.filename) === payload?.file?.filename)
            if (target) {
              target.uploadStatus = 'error'
              target.uploadProgress = 0
              target.errorMessage = payload.message || '上传失败'
            }
          }
        } catch (e) {
          console.error('解析上传流失败:', e)
        }
      }
    }

    // 将仍处于上传中的文件视为失败
    fileList.value.forEach(file => {
      if (file.uploadStatus === 'uploading') {
        file.uploadStatus = 'error'
        file.uploadProgress = 0
        file.errorMessage = file.errorMessage || '上传未完成'
      }
    })

    const failed = fileList.value.filter(f => f.uploadStatus === 'error')
    if (failed.length === 0) {
      uploadFinished.value = true
      ElMessage.success(`成功上传 ${fileList.value.length} 个文件`)
      updateModelFiles()
      return true
    }

    throw new Error(`有 ${failed.length} 个文件上传失败`)

  } catch (error) {
    console.error('文件上传失败:', error)

    // 标记所有文件为上传失败
    fileList.value.forEach(file => {
      file.uploadStatus = 'error'
      file.uploadProgress = 0
      file.errorMessage = error.message || '上传失败'
    })

    let errorMessage = '文件上传失败: '
    if (error.response) {
      const { status, data } = error.response
      if (status === 400) {
        errorMessage += data?.message || '请求参数错误'
      } else if (status === 404) {
        errorMessage += '知识库不存在'
      } else if (status === 413) {
        errorMessage += '文件过大'
      } else if (status === 415) {
        errorMessage += '不支持的文件格式'
      } else if (status === 500) {
        errorMessage += '服务器内部错误，请稍后重试'
      } else {
        errorMessage += data?.message || `HTTP ${status} 错误`
      }
    } else {
      errorMessage += error.message || '未知错误'
    }

    ElMessage.error(errorMessage)
    return false
  } finally {
    isUploading.value = false
  }
}

// 更新父组件的文件列表
const updateModelFiles = () => {
  console.log('更新父组件文件列表，数量:', fileList.value.length)
  emit('update:files', [...fileList.value])
}

// 下一步处理
const handleNext = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请至少上传一个文件')
    return
  }

  if (uploadFinished.value) {
    emit('next')
    return
  }

  const waitingFiles = fileList.value.filter(f =>
    f.uploadStatus === 'waiting' || !f.uploadStatus
  )

  if (waitingFiles.length > 0) {
    const uploadSuccess = await uploadAllFiles()
    if (!uploadSuccess) return
  }

  if (allFilesUploaded.value) {
    uploadFinished.value = true
    emit('next')
  } else {
    ElMessage.error('请等待所有文件上传完成')
  }
}

// 上一步处理
const handlePrev = () => {
  emit('prev')
}

// 修复：防止递归的监听器
let isWatcherUpdating = false

watch(
  () => fileList.value,
  () => {
    if (!isWatcherUpdating && !isInitializing.value) {
      isWatcherUpdating = true
      nextTick(() => {
        updateModelFiles()
        isWatcherUpdating = false
      })
    }
  },
  { deep: true }
)

// 修复：初始化时防止递归
watch(
  () => props.files,
  (newFiles) => {
    if (newFiles && newFiles.length > 0 && !isWatcherUpdating) {
      isInitializing.value = true

      fileList.value = [...newFiles].map(file => ({
        ...file,
        uploadStatus: file.uploadStatus || 'waiting',
        uploadProgress: file.uploadProgress || 0,
        errorMessage: file.errorMessage || ''
      }))

      nextTick(() => {
        isInitializing.value = false
      })
    }
  },
  { immediate: true }
)

// 同步父组件传入的分段设置
// 分段设置已移除
</script>

<!-- template 和 style 部分保持不变 -->


<style scoped>
.file-upload-step {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  min-height: 100%;
  padding: 2rem 1rem;
}

.step-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  padding: 2rem;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  width: 100%;
  max-width: 700px;
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
  margin: 0 0 0.5rem 0;
}

.card-header p {
  color: #6b7280;
  margin: 0;
}

.card-content {
  margin-bottom: 2rem;
}

/* 分段设置信息显示 */
.chunk-settings-info {
  background: #f8fafc;
  border-radius: 0.5rem;
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.chunk-settings-info h3 {
  margin: 0 0 1rem 0;
  color: #1f2937;
  font-size: 1.1rem;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.setting-item {
  display: flex;
  align-items: center;
}

.setting-label {
  font-weight: 500;
  color: #6b7280;
  margin-right: 0.5rem;
}

.setting-value {
  color: #1f2937;
}

/* 上传区域样式 */
.upload-area {
  margin-bottom: 2rem;
}

.upload-dragger {
  width: 100%;
}

/* 文件列表样式 */
.file-list {
  margin-top: 2rem;
}

.file-list h3 {
  margin: 0 0 1rem 0;
  color: #1f2937;
  font-size: 1.1rem;
}

.file-items {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.file-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 1rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  transition: all 0.2s ease;
}

.file-item:hover {
  border-color: #d1d5db;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.file-info {
  display: flex;
  align-items: flex-start;
  flex: 1;
  gap: 1rem;
}

.file-icon {
  font-size: 1.5rem;
  color: #6b7280;
  margin-top: 0.25rem;
}

.file-details {
  flex: 1;
}

.file-name {
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 0.25rem;
  word-break: break-all;
}

.file-size {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.5rem;
}

.upload-status {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.progress-bar {
  width: 100%;
  margin-top: 0.5rem;
}

.error-message {
  color: #dc2626;
  font-size: 0.875rem;
  background: #fef2f2;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  border: 1px solid #fecaca;
}

/* 上传进度提示 */
.upload-progress {
  margin-top: 2rem;
}

/* 卡片底部 */
.card-footer {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(229, 231, 235, 0.3);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .file-upload-step {
    padding: 1rem;
  }

  .step-card {
    padding: 1.5rem;
  }

  .settings-grid {
    grid-template-columns: 1fr;
  }

  .card-footer {
    flex-direction: column;
  }

  .file-item {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
  }

  .file-info {
    flex-direction: column;
    gap: 0.5rem;
  }
}
</style>
