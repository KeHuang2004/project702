<template>
  <div class="chat-interface">
    <div class="chat-container">
      <!-- 左侧聊天列表 -->
      <div class="chat-sidebar">
        <div class="sidebar-header">
          <h2 class="sidebar-title">智能对话</h2>
          <el-button
            type="primary"
            @click="newChat"
            :loading="isCreatingChat"
            class="new-chat-btn"
          >
            <el-icon><Plus /></el-icon>
            创建新会话
          </el-button>
          <div class="search-wrapper">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索会话"
              clearable
              class="search-chat-input"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <!-- 搜索结果将直接在下方的历史会话列表中显示，移除独立下拉 -->
          </div>
        </div>

  <!-- 聊天列表：始终显示，但内容由 filteredChatList 控制，实现搜索即过滤列表 -->
  <div class="chat-list">
          <div
            v-for="chat in filteredChatList"
            :key="chat.id"
            class="chat-item"
            :class="{ active: currentChat?.id === chat.id }"
            @click="selectChat(chat)"
          >
            <div class="chat-content">
              <div class="chat-title" :title="chat.title">{{ chat.title }}</div>
              <div class="chat-time">{{ formatTime(chat.created_at) }}</div>
            </div>
            <div class="chat-actions">
              <el-dropdown trigger="click" @command="handleChatAction">
                <el-button text size="small" class="action-btn">
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item :command="`edit-${chat.id}`">
                      <el-icon><Edit /></el-icon>
                      重命名
                    </el-dropdown-item>
                    <el-dropdown-item :command="`delete-${chat.id}`" divided>
                      <el-icon><Delete /></el-icon>
                      删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </div>
      </div>

      <!-- 主聊天区域 -->
      <div class="chat-main">
        <!-- 欢迎页面 -->
        <div v-if="!currentChat" class="chat-welcome">
          <div class="welcome-content welcome-center-offset">
            <div class="welcome-icon">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <h2>智能对话中心</h2>
            <p>请点击“创建新会话”以创建新的会话以开始聊天，或选择一个旧会话以继续聊天。</p>
            
          </div>
        </div>

        <!-- 聊天内容区 -->
        <div v-else class="chat-content">
          <!-- 聊天头部 -->
          <div class="chat-header">
            <div class="header-boxes">
              <div class="title-box">
                <div class="chat-title-display">
                  <span>
                    {{ currentChat.title }}
                  </span>
                </div>
              </div>

              <!-- 模型选择已移除，模型由后端配置统一管理 -->
              <!-- 模式由顶部全局模式栏控制（通过 provide/inject） -->

            </div>
          </div>

          <!-- 消息区域 -->
          <div class="messages-container" ref="messagesContainer">
            <!-- 使用ChatMessage组件 -->
            <ChatMessage
              v-for="message in currentChatMessages"
              :key="message.id"
              :message="message"
              :avatar-config="avatarConfig"
            />

            <!-- 流式响应消息（只渲染正文，剔除<think>段） -->
            <div v-if="isLoading" class="streaming-message">
              <ChatMessage
                v-if="stream.content"
                :message="{
                  id: 'streaming',
                  role: 'assistant',
                  content: stream.content,
                  created_at: new Date().toISOString()
                }"
                :avatar-config="avatarConfig"
              />

              <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>

            <!-- 移除加载气泡，仅保留三点打字指示（上方） -->
          </div>

          <!-- 输入区域 -->
          <div class="input-area">
            <div class="input-container">
              <div class="input-wrapper">
                <div v-if="isSummaryMode" class="summary-fixed-prompt">
                  请帮我对
                  <span class="summary-file-name">{{ selectedFileName || '未选择文件' }}</span>
                  这个文件进行要点提炼。
                </div>
                <el-input
                  v-else
                  v-model="inputMessage"
                  type="textarea"
                  :rows="1"
                  :autosize="{ minRows: 1, maxRows: 6 }"
                  placeholder="输入消息... (Ctrl+Enter 发送)"
                  @keydown="handleKeydown"
                  :disabled="isLoading"
                  resize="none"
                  class="message-input"
                />
                <div class="input-actions">
                  <el-button
                    type="primary"
                    @click="sendMessage"
                    :disabled="!canSendMessage"
                    :loading="isLoading"
                    class="send-btn"
                  >
                    发送
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 重命名对话框 -->
    <el-dialog
      v-model="showRenameDialog"
      title="重命名对话"
      width="400px"
      @close="cancelRename"
    >
      <el-form @submit.prevent="confirmRename">
        <el-form-item>
          <el-input
            v-model="renameTitle"
            placeholder="请输入新的对话标题"
            @keyup.enter="confirmRename"
            ref="renameInput"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelRename">取消</el-button>
        <el-button type="primary" @click="confirmRename" :loading="isRenaming">
          确认
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed, watch, inject } from 'vue'
import {
  Plus, MoreFilled, Edit, Delete, ChatDotRound, Search
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { chatAPI } from '@/api/chat'
import ChatMessage from '@/components/ChatMessage.vue'
import { useRouter, useRoute } from 'vue-router'

// 响应式数据
const chatList = ref([])
const currentChat = ref(null)
const inputMessage = ref('')
const isLoading = ref(false)
const isCreatingChat = ref(false)
const messagesContainer = ref(null)
// 流式状态：拆分思考与可见正文
// 简化后的流状态：仅保留渲染内容，统一在单气泡中 Markdown 渲染
const stream = ref({ content: '' })
// 自定义头像配置（可改为你的图片/文本/颜色）
const avatarConfig = ref({
  size: 36,
  user: {
  // 保持用户头像为默认图标与配色（不指定图片）
  },
  assistant: {
  src: '/image.png'
  },
  colors: {
    userBg: '#4f46e5',
    userColor: '#ffffff',
    assistantBg: '#f3f4f6',
    assistantColor: '#6b7280'
  }
})
const isEditingTitle = ref(false)
const editingTitle = ref('')
const titleInput = ref(null)
const showRenameDialog = ref(false)
const renameTitle = ref('')
const renamingChatId = ref(null)
const isRenaming = ref(false)
const renameInput = ref(null)
// 生成模型选择已移除，模型由后端配置统一管理
const searchKeyword = ref('')
// 使用 App 提供的全局模式
const ragMode = inject('appMode', ref('generate'))

const selectedKbId = ref(localStorage.getItem('selectedRagKbId') || '')
const selectedReviewKbId = ref(localStorage.getItem('selectedReviewKbId') || '')
const selectedFileName = ref(localStorage.getItem('selectedFileName') || '')
const isSummaryMode = computed(() => ragMode.value === 'summary')
const isLiteratureReviewMode = computed(() => ragMode.value === 'literature-review')
const summaryPrompt = computed(() => {
  const fileName = selectedFileName.value || '未选择文件'
  return `请帮我对 ${fileName} 这个文件进行要点提炼。`
})
const canSendMessage = computed(() => {
  if (isLoading.value) return false
  if (isSummaryMode.value) return Boolean(localStorage.getItem('selectedFileId'))
  if (ragMode.value === 'rag') return Boolean(selectedKbId.value && inputMessage.value.trim())
  if (isLiteratureReviewMode.value) return Boolean(selectedReviewKbId.value && inputMessage.value.trim())
  return Boolean(inputMessage.value.trim())
})

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const replayAssistantMessage = async (content) => {
  const text = String(content || '')
  if (!text) return ''

  const chunks = text.match(/.{1,4}/gs) || [text]
  for (const chunk of chunks) {
    stream.value.content += chunk
    await nextTick()
    scrollToBottom()
    const hasPausePunctuation = /[，。！？；：,.!?;:]/.test(chunk)
    await sleep(hasPausePunctuation ? 160 : 90)
  }

  return text
}

const goToKnowledge = () => {
  router.push('/home/knowledge_base')
}

const goToQApair = () => {
  router.push('/QApair')
}

const goToSystemOverview = () => {
  router.push('/statistic')
}

const router = useRouter()
const route = useRoute()

// 移除冗余的 QApair 管理入口（由顶栏与首页统一入口）

// 计算属性
const currentChatMessages = computed(() => currentChat.value?.messages || [])

const filteredChatList = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return chatList.value
  return chatList.value.filter(chat => (chat.title || '').toLowerCase().includes(keyword))
})

// 初始化数据
onMounted(async () => {
  await loadChatList()
  console.log('聊天界面已加载')
  selectedKbId.value = localStorage.getItem('selectedRagKbId') || ''
  selectedReviewKbId.value = localStorage.getItem('selectedReviewKbId') || ''
  if (isSummaryMode.value) {
    selectedFileName.value = localStorage.getItem('selectedFileName') || ''
    inputMessage.value = summaryPrompt.value
  }
})

// 加载对话列表
const loadChatList = async () => {
  try {
    const response = await chatAPI.getChatList()
    if (response.success && response.data?.sessions) {
      chatList.value = response.data.sessions
      await applyRouteSelection(route.params.chatTitle)
    }
  } catch (error) {
    console.error('加载对话列表失败:', error)
    ElMessage.error('加载对话列表失败')
  }
}

// 选择对话并加载消息
const selectChat = async (chat, options = {}) => {
  const { updateRoute = true } = options
  try {
    if (updateRoute) {
      updateChatRoute(chat)
    }
    currentChat.value = chat
    const response = await chatAPI.getChatDetail(chat.id)
    if (response.success && response.data) {
      // 更新当前对话的完整信息（包含消息）
      currentChat.value = {
        ...response.data,
        messages: response.data.messages || []
      }
      // 更新列表中对应的对话信息
      const index = chatList.value.findIndex(c => c.id === chat.id)
      if (index > -1) {
        chatList.value[index] = { ...response.data }
      }
      await nextTick()
      scrollToBottom()
      searchKeyword.value = ''
    }
  } catch (error) {
    console.error('加载对话详情失败:', error)
    ElMessage.error('加载对话详情失败')
  }
}

// 创建新对话
const newChat = async () => {
  isCreatingChat.value = true
  try {
    const response = await chatAPI.createChat()
      if (response.success && response.data) {
      const newChatData = {
        ...response.data,
        messages: []
      }
      if (!newChatData.title) {
        newChatData.title = '新会话'
      }
      // 添加到列表顶部
      chatList.value.unshift(newChatData)
      await selectChat(newChatData)
    }
  } catch (error) {
    console.error('创建对话失败:', error)
    ElMessage.error('创建对话失败')
  } finally {
    isCreatingChat.value = false
  }
}

// 发送消息：后端始终返回完整响应，前端自行做伪流式展示
const sendMessage = async () => {
  if (isLoading.value) return
  if (isSummaryMode.value && !localStorage.getItem('selectedFileId')) {
    ElMessage.warning('请先在要点提炼中选择文件')
    return
  }

  const message = isSummaryMode.value ? summaryPrompt.value : inputMessage.value.trim()
  if (!message) return

  if (!isSummaryMode.value) {
    inputMessage.value = ''
  }
  isLoading.value = true
  stream.value = { content: '' }

  try {
    // 如果没有当前对话，创建新对话
    if (!currentChat.value) {
      await newChat()
    }

    // 添加用户消息到界面
    const userMessage = {
      id: Date.now(), // 临时ID，后端会返回真实ID
      role: 'user',
      content: message,
      created_at: new Date().toISOString()
    }
    currentChat.value.messages.push(userMessage)

    // 滚动到底部
    await nextTick()
    scrollToBottom()

    {
      if (ragMode.value === 'rag' && !selectedKbId.value) {
        ElMessage.warning('请选择用于检索的知识库')
        isLoading.value = false
        return
      }
      if (isLiteratureReviewMode.value && !selectedReviewKbId.value) {
        ElMessage.warning('请选择用于文献综述的知识库')
        isLoading.value = false
        return
      }

      const selectedFileId = localStorage.getItem('selectedFileId')
      const payload = {
        query: message,
        mode: ragMode.value === 'rag'
          ? 'rag'
          : (isSummaryMode.value ? 'summary' : (isLiteratureReviewMode.value ? 'literature-review' : 'normal')),
        file_id: isSummaryMode.value && selectedFileId ? Number(selectedFileId) : undefined,
        kb_id: ragMode.value === 'rag'
          ? Number(selectedKbId.value)
          : (isLiteratureReviewMode.value ? Number(selectedReviewKbId.value) : undefined),
      }
      const response = await chatAPI.sendMessage(currentChat.value.id, payload)
      const reply = response?.data?.reply || null
      const replyContent = reply?.content || ''
      await replayAssistantMessage(replyContent)
      currentChat.value.messages.push({
        id: reply?.id || Date.now() + 1,
        role: 'assistant',
        content: replyContent,
        created_at: reply?.created_at || new Date().toISOString(),
      })
      await nextTick()
      scrollToBottom()
      stream.value.content = ''
      isLoading.value = false
      if (isSummaryMode.value) {
        inputMessage.value = summaryPrompt.value
      }
    }
  } catch (error) {
    console.error('发送消息失败:', error)
    ElMessage.error('发送消息失败，请重试')
    isLoading.value = false
    stream.value = { content: '' }
    if (isSummaryMode.value) {
      inputMessage.value = summaryPrompt.value
    }
  }
}

// 键盘事件处理
const handleKeydown = (event) => {
  if (event.ctrlKey && event.key === 'Enter') {
    sendMessage()
  }
}

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 解析流式 chunk：剔除 <think>...</think> 段，仅保留正文
const stripInThink = { value: false }
const processStreamChunk = (chunk) => {
  let text = String(chunk)
  while (text.length > 0) {
    const lower = text.toLowerCase()
    if (stripInThink.value) {
      const endIdx = lower.indexOf('</think>')
      if (endIdx >= 0) {
        text = text.slice(endIdx + '</think>'.length)
        stripInThink.value = false
        continue
      } else {
        return
      }
    } else {
      const startIdx = lower.indexOf('<think>')
      if (startIdx >= 0) {
        stream.value.content += text.slice(0, startIdx)
        text = text.slice(startIdx + '<think>'.length)
        stripInThink.value = true
        continue
      } else {
        stream.value.content += text
        return
      }
    }
  }
}

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

// 开始编辑标题
const startEditTitle = () => {
  if (!currentChat.value) return
  isEditingTitle.value = true
  editingTitle.value = currentChat.value.title
  nextTick(() => {
    if (titleInput.value) {
      titleInput.value.focus()
      titleInput.value.select()
    }
  })
}

// 完成编辑标题
const finishEditTitle = async () => {
  if (!editingTitle.value.trim()) {
    cancelEditTitle()
    return
  }

  try {
    const response = await chatAPI.updateChatTitle(currentChat.value.id, editingTitle.value.trim())
    if (response.success && response.data) {
      // 更新当前对话标题
      currentChat.value.title = response.data.title
      currentChat.value.updated_at = response.data.updated_at

      // 更新列表中的标题
      const chatInList = chatList.value.find(c => c.id === currentChat.value.id)
      if (chatInList) {
        chatInList.title = response.data.title
        chatInList.updated_at = response.data.updated_at
      }

      ElMessage.success('标题更新成功')
    }
  } catch (error) {
    console.error('更新标题失败:', error)
    ElMessage.error('更新标题失败')
  } finally {
    isEditingTitle.value = false
    editingTitle.value = ''
  }
}

// 取消编辑标题
const cancelEditTitle = () => {
  isEditingTitle.value = false
  editingTitle.value = ''
}

// 处理对话操作
const handleChatAction = (command) => {
  const [action, chatId] = command.split('-')
  const chat = chatList.value.find(c => c.id === parseInt(chatId))

  if (!chat) return

  switch (action) {
    case 'edit':
      showRenameDialog.value = true
      renameTitle.value = chat.title
      renamingChatId.value = chat.id
      nextTick(() => {
        if (renameInput.value) {
          renameInput.value.focus()
          renameInput.value.select()
        }
      })
      break
    case 'delete':
      deleteChat(chat)
      break
  }
}

// 确认重命名
const confirmRename = async () => {
  if (!renameTitle.value.trim()) {
    ElMessage.warning('请输入标题')
    return
  }

  isRenaming.value = true
  try {
    const response = await chatAPI.updateChatTitle(renamingChatId.value, renameTitle.value.trim())
    if (response.success && response.data) {
      // 更新列表中的对话
      const chat = chatList.value.find(c => c.id === renamingChatId.value)
      if (chat) {
        chat.title = response.data.title
        chat.updated_at = response.data.updated_at
      }

      // 如果是当前对话，也要更新
      if (currentChat.value && currentChat.value.id === renamingChatId.value) {
        currentChat.value.title = response.data.title
        currentChat.value.updated_at = response.data.updated_at
        updateChatRoute(currentChat.value, { replace: true })
      }

      ElMessage.success('重命名成功')
      showRenameDialog.value = false
    }
  } catch (error) {
    console.error('重命名失败:', error)
    ElMessage.error('重命名失败')
  } finally {
    isRenaming.value = false
  }
}

// 取消重命名
const cancelRename = () => {
  showRenameDialog.value = false
  renameTitle.value = ''
  renamingChatId.value = null
}

// 删除对话
const deleteChat = async (chat) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除对话"${chat.title}"吗？此操作无法撤销。`,
      '删除对话',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    const response = await chatAPI.deleteChat(chat.id)
    if (response.success) {
      // 从列表中移除
      const index = chatList.value.findIndex(c => c.id === chat.id)
      if (index > -1) {
        chatList.value.splice(index, 1)
      }

      // 如果删除的是当前对话，清除当前对话
      if (currentChat.value && currentChat.value.id === chat.id) {
        currentChat.value = null
        updateChatRoute(null)
      }

      ElMessage.success('对话删除成功')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除对话失败:', error)
      ElMessage.error('删除对话失败')
    }
  }
}

const normalizeRouteTitle = (rawTitle) => {
  if (!rawTitle) return ''
  const value = Array.isArray(rawTitle) ? rawTitle[0] : rawTitle
  try {
    return decodeURIComponent(value)
  } catch (error) {
    return value
  }
}

const updateChatRoute = (chat, options = {}) => {
  const { replace = false } = options
  const targetPath = chat ? `/chat/${encodeURIComponent(chat.title)}` : '/chat'
  const currentPath = router.currentRoute.value.fullPath
  if (currentPath === targetPath) return
  const navigate = replace ? router.replace : router.push
  navigate(targetPath).catch((err) => {
    if (!err || err.name === 'NavigationDuplicated' || err.message?.includes('Avoided redundant navigation')) {
      return
    }
    console.error('路由切换失败:', err)
  })
}

const applyRouteSelection = async (rawTitle) => {
  const targetTitle = normalizeRouteTitle(rawTitle)
  searchKeyword.value = ''
  if (!targetTitle) {
    currentChat.value = null
    return
  }
  if (currentChat.value && currentChat.value.title === targetTitle) {
    return
  }
  const match = chatList.value.find(chat => chat.title === targetTitle)
  if (match) {
    await selectChat(match, { updateRoute: false })
  } else {
    currentChat.value = null
    updateChatRoute(null, { replace: true })
  }
}

watch(
  () => route.params.chatTitle,
  async (newTitle) => {
    if (!chatList.value.length) {
      return
    }
    await applyRouteSelection(newTitle)
  }
)

watch(
  () => ragMode.value,
  (mode) => {
    if (mode === 'summary') {
      selectedFileName.value = localStorage.getItem('selectedFileName') || ''
      inputMessage.value = summaryPrompt.value
    } else if (mode === 'rag') {
      selectedKbId.value = localStorage.getItem('selectedRagKbId') || ''
      if (!selectedKbId.value) {
        ElMessage.warning('请先点击顶部 RAG 模式按钮并选择知识库')
      }
      if (!isLoading.value) {
        inputMessage.value = ''
      }
    } else if (mode === 'literature-review') {
      selectedReviewKbId.value = localStorage.getItem('selectedReviewKbId') || ''
      if (!selectedReviewKbId.value) {
        ElMessage.warning('请先点击顶部文献综述按钮并选择知识库')
      }
      if (!isLoading.value) {
        inputMessage.value = ''
      }
    } else if (!isLoading.value) {
      inputMessage.value = ''
    }
  }
)

// 之前的下拉搜索处理已移除（搜索结果现在直接在左侧列表中显示），保留空位以便未来扩展
</script>

<style scoped>
.chat-interface {
  height: 100%;
  display: flex;
  overflow: hidden;
  background: #f5f5f5;
}

.chat-container {
  display: flex;
  width: 100%;
  height: 100%;
}

/* 侧边栏样式 */
.chat-sidebar {
  width: 300px;
  background: #ffffff;
  border-right: 1px solid #e5e5e5;
  display: flex;
  flex-direction: column;
  height: 100%;
}


.sidebar-header {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px 20px 20px 20px;
  border-bottom: 1px solid #e5e5e5;
  background: #ffffff;
}

.sidebar-title {
  margin: 0;
  font-weight: 600;
  color: #1f2937;
  letter-spacing: 0.02em;
}

/* 新对话按钮 */
.new-chat-btn {
  width: 100%;
  height: 40px;
  background: #4f46e5;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  color: white;
  transition: background-color 0.2s;
}

.new-chat-btn:hover {
  background: #4338ca;
}

.search-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;
}

.search-chat-input {
  width: 100%;
}

.search-chat-input :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(229, 231, 235, 0.8);
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
  transition: all 0.2s ease;
}

.search-chat-input :deep(.el-input__wrapper:hover),
.search-chat-input :deep(.el-input__wrapper.is-focus) {
  border-color: #667eea;
  box-shadow: 0 6px 18px rgba(102, 126, 234, 0.18);
}

.search-results {
  max-height: 260px;
  overflow-y: auto;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.12);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.search-result-item {
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(248, 250, 252, 0.9);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.search-result-item:hover {
  background: rgba(102, 126, 234, 0.12);
}

.search-result-item.active {
  background: rgba(102, 126, 234, 0.18);
  border: 1px solid rgba(102, 126, 234, 0.4);
}

.result-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-time {
  font-size: 12px;
  color: #6b7280;
}

.search-empty {
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
}

/* 对话列表 */
.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  background: #ffffff;
}

.chat-list::-webkit-scrollbar {
  width: 6px;
}

.chat-list::-webkit-scrollbar-track {
  background: #f5f5f5;
}

.chat-list::-webkit-scrollbar-thumb {
  background: #e9ecf0;
  border-radius: 3px;
}

.chat-item {
  padding: 12px 20px;
  margin: 2px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chat-item:hover {
  background: #f1f4f7;
}

.chat-item.active {
  background: #dde9f7;
}

.chat-title {
  font-size: 14px;
  font-weight: 500;
  color: #000000;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-item.active .chat-title {
  color: #1f2937;
  font-weight: 600;
}

.chat-time {
  font-size: 12px;
  color: #7e848d;
}

.chat-actions {
  opacity: 0;
  transition: opacity 0.2s;
}

.chat-item:hover .chat-actions {
  opacity: 1;
}

.action-btn {
  color: #6b7280;
  padding: 4px;
  border-radius: 4px;
}

.action-btn:hover {
  background: #f3f4f6;
  color: #374151;
}

/* 主聊天区域 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  height: 100%;
}

/* 欢迎页面 */
.chat-welcome {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
}

.welcome-content {
  text-align: center;
  max-width: 500px;
  padding: 40px;
}

/* 让欢迎内容相对于整页居中：抵消侧边栏宽度的一半 */
.welcome-center-offset {
  /* 向左平移以抵消侧边栏，向上平移使视觉位置略高于正中心 */
  transform: translate(-150px, -40px);
}

.welcome-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 24px;
  background: #f3f4f6;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  font-size: 24px;
}

.welcome-content h2 {
  font-size: 28px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #1f2937;
}

.welcome-content p {
  font-size: 16px;
  color: #6b7280;
  line-height: 1.6;
}

/* 聊天内容区域 */
.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-header {
  padding: 16px 24px;
  border-bottom: 1px solid #e5e5e5;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-boxes {
  display: flex;
  gap: 16px;
  align-items: center;
  flex: 1;
  border: 1px solid #e5e7eb; /* 外层大框 */
  background: #fff;
  padding: 10px 12px;
  border-radius: 10px;
}

.title-box {
  padding: 6px 8px; /* 去掉内框边框，只保留外层大框 */
  min-width: 240px;
}

.model-box {
  margin-left: auto; /* 靠右 */
  padding: 4px 6px; /* 去掉内框边框，只保留外层大框 */
}

.chat-title-display {
  font-size: 16px; /* 与模型选择字体一致 */
  font-weight: 600;
  color: #1f2937;
}

.model-select-el {
  min-width: 320px;
  font-size: 16px;
}

.chat-title-display:hover {
  color: #4f46e5;
}

.title-input {
  flex: 1;
}

.edit-title-btn {
  color: #6b7280;
  padding: 8px;
  border-radius: 6px;
}

.edit-title-btn:hover {
  color: #4f46e5;
  background: #f3f4f6;
}

/* 消息区域 */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: #fafafa;
}

.streaming-message .think-live {
  margin: 8px 0 4px 48px; /* 对齐助手头像后的文本区域 */
  background: #f5f5f5;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px 10px;
}
.think-live-label {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 4px;
}
.think-live-content :deep(pre) { background:#0b1021; color:#e6e6e6; padding:10px; border-radius:6px; overflow:auto }
.think-live-content :deep(code) { background:#f5f5f5; padding:2px 4px; border-radius:4px }
.think-collapsed { margin: 6px 0 4px 48px; font-size: 12px; color: #6b7280; }

.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track {
  background: transparent;
}

.messages-container::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

/* 流式消息样式 */
.streaming-message {
  position: relative;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  margin-left: 48px;
  margin-top: -10px;
  padding: 8px 16px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #9ca3af;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1.2);
    opacity: 1;
  }
}

/* 加载消息样式 */
/* 移除加载气泡相关样式 */

/* 输入区域 */
.input-area {
  padding: 20px 24px;
  background: #ffffff;
  border-top: 1px solid #e5e5e5;
}

.input-container {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #d1d5db;
  transition: border-color 0.2s;
}

.input-container:focus-within {
  border-color: #4f46e5;
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 8px;
}

.summary-fixed-prompt {
  flex: 1;
  min-height: 44px;
  border: 1px solid #dbe2ea;
  border-radius: 10px;
  background: #f8fbff;
  color: #374151;
  padding: 10px 12px;
  line-height: 1.6;
}

.summary-file-name {
  color: #1d4ed8;
  font-weight: 700;
  background: #e7efff;
  border-radius: 6px;
  padding: 2px 8px;
}

/* 文本输入框 */
.message-input {
  flex: 1;
}

.message-input :deep(.el-textarea__inner) {
  border: none;
  background: transparent;
  padding: 8px 12px;
  font-size: 14px;
  line-height: 1.5;
  color: #374151;
  resize: none;
  box-shadow: none;
}

.message-input :deep(.el-textarea__inner):focus {
  box-shadow: none;
  outline: none;
}

.message-input :deep(.el-textarea__inner)::placeholder {
  color: #9ca3af;
}

/* 按钮区域 */
.input-actions {
  display: flex;
  align-items: flex-end;
}

.send-btn {
  background: #4f46e5;
  border: none;
  border-radius: 8px;
  padding: 8px 20px;
  font-weight: 500;
  color: white;
  transition: background-color 0.2s;
  height: 36px;
}

.send-btn:hover {
  background: #4338ca;
}

.send-btn.is-disabled {
  background: #e5e7eb;
  color: #9ca3af;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chat-sidebar {
    width: 280px;
  }
  /* 调整抵消距离为侧边栏一半（280/2），同时保持向上位移 */
  .welcome-center-offset { transform: translate(-140px, -40px); }

  .sidebar-header {
    padding: 16px;
  }

  .welcome-content {
    padding: 24px 20px;
  }

  .welcome-content h2 {
    font-size: 24px;
  }

  .messages-container {
    padding: 16px;
  }

  .input-area {
    padding: 16px;
  }

  .chat-header {
    padding: 12px 20px;
  }
}

@media (max-width: 640px) {
  .chat-sidebar {
    width: 260px;
  }

  .chat-item {
    padding: 10px 16px;
    margin: 2px 8px;
  }

  .welcome-content h2 {
    font-size: 20px;
  }
  /* 调整抵消距离为侧边栏一半（260/2），同时保持向上位移 */
  .welcome-center-offset { transform: translate(-130px, -36px); }
}

/* 对话框美化 */
.el-dialog {
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
}

.el-dialog__header {
  background: #ffffff;
  border-bottom: 1px solid #e5e5e5;
  border-radius: 12px 12px 0 0;
  padding: 20px 24px;
}

.el-dialog__title {
  font-weight: 600;
  color: #1f2937;
}

.el-dialog__body {
  padding: 24px;
}

.el-dialog__footer {
  padding: 16px 24px 24px;
  border-top: 1px solid #e5e5e5;
}

/* Element Plus 组件样式覆盖 */
.el-button--primary {
  background-color: #4f46e5;
  border-color: #4f46e5;
}

.el-button--primary:hover {
  background-color: #4338ca;
  border-color: #4338ca;
}

.el-button--primary:focus {
  background-color: #4338ca;
  border-color: #4338ca;
}

.el-dropdown-menu {
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.el-dropdown-menu__item {
  color: #374151;
}

.el-dropdown-menu__item:hover {
  background-color: #f9fafb;
}

.el-dropdown-menu__item--divided {
  border-top-color: #e5e7eb;
}

/* 输入框聚焦状态 */
.el-input__wrapper {
  transition: all 0.2s;
}

.el-input.is-focus .el-input__wrapper {
  box-shadow: 0 0 0 1px #4f46e5 inset;
}

/* 加载状态样式调整 */
.el-loading-mask {
  background-color: rgba(255, 255, 255, 0.7);
}

/* 滚动条美化 - 针对Webkit内核浏览器 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

/* 消息时间戳样式 */
.message-time {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
}

/* 确保长文本正确换行 */
.chat-title {
  word-break: break-word;
  line-height: 1.4;
}

/* 优化移动端体验 */
@media (max-width: 480px) {
  .chat-sidebar {
    width: 100%;
    position: fixed;
    left: -100%;
    transition: left 0.3s ease;
    z-index: 1000;
  }

  .chat-sidebar.open {
    left: 0;
  }

  .chat-main {
    width: 100%;
  }

  .welcome-content h2 {
    font-size: 22px;
  }

  .welcome-content {
    padding: 20px;
  }

  .messages-container {
    padding: 12px;
  }

  .input-area {
    padding: 12px;
  }

  .input-wrapper {
    gap: 8px;
    padding: 6px;
  }

  .send-btn {
    padding: 6px 16px;
    height: 32px;
    font-size: 14px;
  }
}

/* 深色模式支持（可选） */
@media (prefers-color-scheme: dark) {
  .chat-interface {
    background: #1f2937;
  }

  .chat-sidebar {
    background: #374151;
    border-right-color: #4b5563;
  }

  .sidebar-header {
    background: #374151;
    border-bottom-color: #4b5563;
  }

  .sidebar-header h3 {
    color: #f9fafb;
  }

  .chat-main {
    background: #1f2937;
  }

  .chat-welcome {
    background: #1f2937;
  }

  .welcome-content h2 {
    color: #f9fafb;
  }

  .welcome-content p {
    color: #d1d5db;
  }

  .chat-content {
    background: #1f2937;
  }

  .chat-header {
    background: #374151;
    border-bottom-color: #4b5563;
  }

  .chat-title-display {
    color: #f9fafb;
  }

  .messages-container {
    background: #111827;
  }

  .input-area {
    background: #374151;
    border-top-color: #4b5563;
  }

  .input-container {
    background: #1f2937;
    border-color: #4b5563;
  }

  .chat-item {
    color: #d1d5db;
  }

  .chat-item:hover {
    background: #4b5563;
  }

  .chat-item.active {
    background: #1e40af;
    border-left-color: #3b82f6;
  }

  .chat-title {
    color: #f3f4f6;
  }

  .chat-time {
    color: #9ca3af;
  }
}

/* 动画效果 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(-100%);
}

/* 选中文本的颜色 */
::selection {
  background: #dbeafe;
  color: #1e40af;
}

::-moz-selection {
  background: #dbeafe;
  color: #1e40af;
}

/* 确保布局稳定性 */
.chat-container {
  min-height: 0; /* 防止flex子元素溢出 */
}

.messages-container {
  min-height: 0; /* 防止flex子元素溢出 */
}

/* 优化按钮间距 */
.input-actions .el-button + .el-button {
  margin-left: 8px;
}

/* 确保对话框居中 */
.el-dialog {
  margin-top: 5vh !important;
  margin-bottom: 5vh !important;
}

/* 优化表单输入框 */
.el-form-item {
  margin-bottom: 16px;
}

.el-form-item:last-child {
  margin-bottom: 0;
}

/* 确保图标对齐 */
.el-icon {
  vertical-align: middle;
}

/* 优化按钮加载状态 */
.el-button.is-loading {
  pointer-events: none;
}

/* 确保文本不会被意外选中 */
.chat-item,
.sidebar-header,
.chat-header {
  user-select: none;
}

/* 允许消息内容被选中 */
.message-text {
  user-select: text;
}

/* 优化输入框占位符 */
.el-input__inner::placeholder,
.el-textarea__inner::placeholder {
  color: #9ca3af;
  opacity: 1;
}

/* 确保圆角一致性 */
.el-button {
  border-radius: 6px;
}

.el-input__wrapper {
  border-radius: 6px;
}

/* 优化焦点状态的可访问性 */
.el-button:focus-visible,
.el-input:focus-visible,
.chat-item:focus-visible {
  outline: 2px solid #4f46e5;
  outline-offset: 2px;
}

/* 确保消息区域的最小高度 */
.messages-container {
  min-height: 200px;
}

/* 优化空状态显示 */
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #9ca3af;
}

.empty-state .el-icon {
  font-size: 48px;
  margin-bottom: 16px;
  color: #d1d5db;
}
</style>
