<template>
  <div class="chat-message" :class="message.role">
    <div v-if="message.role === 'assistant'" class="message-avatar">
      <el-avatar :size="32" class="assistant-avatar">
        <el-icon><Robot /></el-icon>
      </el-avatar>
    </div>
    
    <div class="message-content">
      <div class="message-bubble">
        <div class="message-text" v-html="formattedContent"></div>
        
        <!-- 知识库来源 -->
        <div v-if="message.sources && message.sources.length > 0" class="message-sources">
          <div class="sources-header">
            <el-icon><Document /></el-icon>
            <span>相关来源</span>
          </div>
          <div class="sources-list">
            <div 
              v-for="source in message.sources" 
              :key="source.id"
              class="source-item"
              @click="viewSource(source)"
            >
              <div class="source-info">
                <span class="source-filename">{{ source.filename }}</span>
                <span class="source-similarity">相似度: {{ (source.similarity * 100).toFixed(1) }}%</span>
              </div>
              <div class="source-preview">{{ source.content.substring(0, 100) }}...</div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="message-meta">
        <span class="message-time">{{ formatTime(message.timestamp) }}</span>
        <div v-if="message.role === 'assistant'" class="message-actions">
          <el-button text size="small" @click="copyMessage">
            <el-icon><Copy /></el-icon>
          </el-button>
          <el-button text size="small" @click="regenerateMessage">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineProps } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const formattedContent = computed(() => {
  // 简单的markdown渲染
  return props.message.content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>')
})

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  if (isNaN(date.getTime())) return timestamp

  const parts = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    hour12: false,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }).formatToParts(date)

  const map = Object.fromEntries(parts.map(p => [p.type, p.value]))
  const y = map.year
  const m = map.month
  const d = map.day
  const h = map.hour
  const mi = map.minute
  const s = map.second

  return `${y}年${parseInt(m,10)}月${parseInt(d,10)}日 ${h}时${mi}分${s}秒`
}

const copyMessage = async () => {
  try {
    await navigator.clipboard.writeText(props.message.content)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

const regenerateMessage = () => {
  // 重新生成消息的逻辑
  console.log('重新生成消息')
}

const viewSource = (source) => {
  // 查看知识库来源的逻辑
  console.log('查看来源:', source)
}
</script>

<style scoped>
.chat-message {
  display: flex;
  gap: 12px;
  max-width: 800px;
}

.chat-message.user {
  margin-left: auto;
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
}

.assistant-avatar {
  background: #3b82f6;
  color: white;
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-bubble {
  padding: 16px 20px;
  border-radius: 12px;
  margin-bottom: 8px;
}

.user .message-bubble {
  background: #3b82f6;
  color: white;
  margin-left: 60px;
}

.assistant .message-bubble {
  background: white;
  border: 1px solid #e5e7eb;
  margin-right: 60px;
}

.message-text {
  line-height: 1.6;
  white-space: pre-wrap;
}

.message-sources {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}

.sources-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  margin-bottom: 12px;
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-item {
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.source-item:hover {
  background: #f3f4f6;
}

.source-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.source-filename {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.source-similarity {
  font-size: 12px;
  color: #6b7280;
}

.source-preview {
  font-size: 13px;
  color: #6b7280;
  line-height: 1.4;
}

.message-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #9ca3af;
}

.user .message-meta {
  flex-direction: row-reverse;
}

.message-actions {
  display: flex;
  gap: 4px;
}
</style>
