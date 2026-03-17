<template>
  <div class="chat-message" :class="message.role">
    <div class="avatar" :class="message.role" :style="avatarWrapperStyle">
      <!-- 图片头像优先 -->
      <el-avatar v-if="avatarSrc" :size="avatarSize" :src="avatarSrc" />
      <!-- 文本头像次之 -->
      <el-avatar v-else-if="avatarText" :size="avatarSize" :style="avatarBgStyle">
        {{ avatarText }}
      </el-avatar>
      <!-- 默认图标头像 -->
      <el-avatar v-else :size="avatarSize" :style="avatarBgStyle">
        <el-icon><component :is="avatarIconComponent" /></el-icon>
      </el-avatar>
    </div>

    <div class="message-content">
      <div class="message-bubble" :class="message.role">
        <div class="message-text" v-html="formattedContent"></div>
      </div>
      <div class="message-meta">
        <span class="message-time">{{ formatTime(message.created_at) }}</span>
        <div v-if="message.role === 'assistant'" class="message-actions">
          <el-button text size="small" @click="copyMessage">
            <el-icon><CopyDocument /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ChatLineRound, User, CopyDocument } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import hljs from 'highlight.js'

// 配置marked
marked.setOptions({
  highlight: function(code, language) {
    if (language && hljs.getLanguage(language)) {
      try {
        return hljs.highlight(code, { language }).value
      } catch (err) {}
    }
    return hljs.highlightAuto(code).value
  },
  langPrefix: 'hljs language-',
  breaks: true,
  gfm: true
})

const props = defineProps({
  message: {
    type: Object,
    required: true
  },
  // 可选的头像配置
  avatarConfig: {
    type: Object,
    default: () => ({})
  }
})

const isAssistant = computed(() => props.message?.role === 'assistant')
const roleKey = computed(() => (isAssistant.value ? 'assistant' : 'user'))

// 尺寸
const avatarSize = computed(() => props.avatarConfig?.size ?? 32)

// 数据来源优先级：外部传入 avatarConfig.{role}.src -> message.avatar_url/avatar -> 无
const avatarSrc = computed(() => {
  const cfg = props.avatarConfig?.[roleKey.value]
  return cfg?.src || props.message?.avatar_url || props.message?.avatar || ''
})

// 文本头像（例如用户首字或简称）
const avatarText = computed(() => {
  const cfg = props.avatarConfig?.[roleKey.value]
  return cfg?.text || ''
})

// 图标组件（默认：助手-ChatLineRound；用户-User）
const avatarIconComponent = computed(() => (isAssistant.value ? ChatLineRound : User))

// 颜色：可通过 avatarConfig.colors 覆盖
const assistantBg = computed(() => props.avatarConfig?.colors?.assistantBg || '#f3f4f6')
const assistantColor = computed(() => props.avatarConfig?.colors?.assistantColor || '#6b7280')
const userBg = computed(() => props.avatarConfig?.colors?.userBg || '#4f46e5')
const userColor = computed(() => props.avatarConfig?.colors?.userColor || '#ffffff')

const avatarBgStyle = computed(() => ({
  background: isAssistant.value ? assistantBg.value : userBg.value,
  color: isAssistant.value ? assistantColor.value : userColor.value
}))

const avatarWrapperStyle = computed(() => ({
  width: `${avatarSize.value}px`,
  height: `${avatarSize.value}px`
}))

// 去除 <think>...</think> 段落，仅保留可见正文
const stripThink = (raw = '') => raw.replace(/<think>[\s\S]*?<\/think>/gi, '').replace(/<think>/gi, '').replace(/<\/think>/gi, '')

const formattedContent = computed(() => {
  if (props.message.role === 'assistant') {
    try {
      return marked.parse(stripThink(props.message.content || ''))
    } catch (error) {
      console.error('Markdown解析失败:', error)
      // 失败回退：优先显示正文，其次思考
      const fallback = stripThink(props.message.content || '')
      return fallback.replace(/\n/g, '<br>')
    }
  }
  // 用户消息：Markdown 渲染
  try {
    return marked.parse(props.message.content || '')
  } catch {
    return (props.message.content || '').replace(/\n/g, '<br>')
  }
})


// 格式化时间
const formatTime = (time) => {
  const date = new Date(time)
  const year = date.getFullYear()
  const month = date.getMonth() + 1
  const day = date.getDate()
  const hour = date.getHours()
  const minute = date.getMinutes()
  
  return `${year}年${month}月${day}日 ${hour.toString().padStart(2, '0')}时${minute.toString().padStart(2, '0')}分`
}

// 复制消息
const copyMessage = async () => {
  try {
    await navigator.clipboard.writeText(props.message.content)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败')
  }
}

</script>

<!-- 样式更新以适配自定义头像大小和背景 -->
<style scoped>
.chat-message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: flex-start;
}

.chat-message.user {
  flex-direction: row-reverse;
}

.avatar {
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 16px;
}

.message-content {
  flex: 1;
  max-width: calc(100% - 48px);
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 18px;
  word-wrap: break-word;
  position: relative;
  max-width: fit-content;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.message-bubble.user {
  background: #4f46e5;
  color: white;
  margin-left: auto;
  border-bottom-right-radius: 6px;
}

.message-bubble.assistant {
  background: white;
  color: #374151;
  border: 1px solid #e5e7eb;
  border-bottom-left-radius: 6px;
}

.message-text {
  line-height: 1.6;
  word-break: break-word;
}

.message-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
  padding: 0 4px;
}

.chat-message.user .message-meta {
  justify-content: flex-end;
}

.message-time {
  font-size: 12px;
  color: #9ca3af;
}

.message-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.chat-message:hover .message-actions {
  opacity: 1;
}

/* Markdown样式 */
.message-text :deep(h1),
.message-text :deep(h2),
.message-text :deep(h3),
.message-text :deep(h4),
.message-text :deep(h5),
.message-text :deep(h6) {
  margin: 16px 0 8px 0;
  font-weight: 600;
  line-height: 1.3;
}

.message-text :deep(h1) { font-size: 1.5em; }
.message-text :deep(h2) { font-size: 1.3em; }
.message-text :deep(h3) { font-size: 1.2em; }
.message-text :deep(h4) { font-size: 1.1em; }
.message-text :deep(h5) { font-size: 1em; }
.message-text :deep(h6) { font-size: 0.9em; }

.message-text :deep(p) {
  margin: 8px 0;
  line-height: 1.6;
}

.message-text :deep(ul),
.message-text :deep(ol) {
  margin: 8px 0;
  padding-left: 20px;
}

.message-text :deep(li) {
  margin: 4px 0;
  line-height: 1.5;
}

.message-text :deep(blockquote) {
  margin: 12px 0;
  padding: 8px 12px;
  border-left: 4px solid #e5e7eb;
  background: #f9fafb;
  color: #6b7280;
  font-style: italic;
}

.message-text :deep(code) {
  background: #f1f5f9;
  color: #e11d48;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.9em;
}

.message-text :deep(pre) {
  background: #1e293b;
  color: #f8fafc;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
  position: relative;
}

.message-text :deep(pre code) {
  background: transparent;
  color: inherit;
  padding: 0;
  border-radius: 0;
  font-size: 0.9em;
}

.message-text :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
  font-size: 0.9em;
}

.message-text :deep(th),
.message-text :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 8px 12px;
  text-align: left;
}

.message-text :deep(th) {
  background: #f9fafb;
  font-weight: 600;
}

.message-text :deep(a) {
  color: #4f46e5;
  text-decoration: none;
}

.message-text :deep(a:hover) {
  text-decoration: underline;
}

.message-text :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
  margin: 8px 0;
}

.message-text :deep(hr) {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 16px 0;
}

/* 已移除思考相关样式，保持简单渲染 */

/* 用户消息中的代码块样式调整 */
.message-bubble.user .message-text :deep(code) {
  background: rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.9);
}

.message-bubble.user .message-text :deep(pre) {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.message-bubble.user .message-text :deep(blockquote) {
  background: rgba(255, 255, 255, 0.1);
  border-left-color: rgba(255, 255, 255, 0.3);
  color: rgba(255, 255, 255, 0.9);
}
</style>
