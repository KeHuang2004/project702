<template>
  <div class="file-uploader">
    <div 
      class="upload-area"
      :class="{ 'dragover': isDragOver }"
      @drop="handleDrop"
      @dragover.prevent="isDragOver = true"
      @dragleave="isDragOver = false"
      @dragenter.prevent
      @click="triggerFileInput"
    >
      <input
        ref="fileInput"
        type="file"
        multiple
        accept=".txt,.pdf,.doc,.docx,.rtf,.md,.xls,.xlsx,.csv,.ppt,.pptx,.html,.htm,.json,.xml"
        @change="handleFileSelect"
        style="display: none"
      >
      
      <div class="upload-content">
        <el-icon class="upload-icon"><Upload /></el-icon>
        <div class="upload-text">
          <p class="primary-text">点击上传文件或拖拽文件到此处</p>
          <p class="secondary-text">支持 txt、pdf、doc、docx、rtf、md、xls、xlsx、csv、ppt、pptx、html、htm、json、xml 格式</p>
        </div>
      </div>
    </div>

    <!-- 文件列表 -->
    <div v-if="fileList.length > 0" class="file-list">
      <div class="file-list-header">
        <span>已选择 {{ fileList.length }} 个文件</span>
        <el-button text @click="clearFiles">清空</el-button>
      </div>
      
      <div class="file-items">
        <div 
          v-for="(file, index) in fileList" 
          :key="index"
          class="file-item"
        >
          <div class="file-info">
            <el-icon class="file-icon"><Document /></el-icon>
            <div class="file-details">
              <span class="file-name">{{ file.name }}</span>
              <span class="file-size">{{ formatFileSize(file.size) }}</span>
            </div>
          </div>
          <el-button 
            text 
            type="danger" 
            @click="removeFile(index)"
            class="remove-btn"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, defineEmits, defineProps } from 'vue'

const props = defineProps({
  files: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['files-selected'])

const fileInput = ref(null)
const isDragOver = ref(false)
const fileList = ref([...props.files])

const triggerFileInput = () => {
  fileInput.value.click()
}

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files)
  addFiles(files)
}

const handleDrop = (event) => {
  event.preventDefault()
  isDragOver.value = false
  const files = Array.from(event.dataTransfer.files)
  addFiles(files)
}

const addFiles = (files) => {
  const validFiles = files.filter(file => {
    const validTypes = ['.txt', '.pdf', '.doc', '.docx', '.rtf', '.md', '.xls', '.xlsx', '.csv', '.ppt', '.pptx', '.html', '.htm', '.json', '.xml']
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase()
    return validTypes.includes(fileExtension)
  })

  fileList.value.push(...validFiles)
  emit('files-selected', fileList.value)
}

const removeFile = (index) => {
  fileList.value.splice(index, 1)
  emit('files-selected', fileList.value)
}

const clearFiles = () => {
  fileList.value = []
  emit('files-selected', fileList.value)
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<style scoped>
.file-uploader {
  width: 100%;
}

.upload-area {
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #f9fafb;
}

.upload-area:hover,
.upload-area.dragover {
  border-color: #3b82f6;
  background: #eff6ff;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.upload-icon {
  font-size: 48px;
  color: #6b7280;
}

.primary-text {
  font-size: 16px;
  font-weight: 500;
  color: #374151;
  margin: 0;
}

.secondary-text {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

.file-list {
  margin-top: 24px;
}

.file-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 500;
}

.file-items {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
  background: white;
}

.file-item:last-child {
  border-bottom: none;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-icon {
  font-size: 20px;
  color: #ef4444;
}

.file-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.file-size {
  font-size: 12px;
  color: #6b7280;
}

.remove-btn {
  padding: 4px;
}
</style>
