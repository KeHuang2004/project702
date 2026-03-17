import request from '@/utils/request'

export const chatAPI = {
  // 获取对话列表
  getChatList() {
    return request({
      url: '/api/v1/chat',
      method: 'get'
    })
  },

  // 获取单个会话信息（包含消息）
  getChatDetail(sessionId) {
    return request({
      url: `/api/v1/chat/${sessionId}`,
      method: 'get'
    })
  },

  // 创建新对话
  createChat(title = null) {
    const data = title ? { title } : {}
    return request({
      url: '/api/v1/chat',
      method: 'post',
      data
    })
  },

  // 发送消息（流式响应）
  async sendMessageStream(sessionId, data, onMessage) {
    try {
      const response = await fetch(`http://127.0.0.1:11550/api/v1/chat/${sessionId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          // 处理缓冲区中最后一段未处理的数据
          if (buffer) {
            const lines = buffer.split('\n')
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6).trim()
                if (data) onMessage(data)
              }
            }
            buffer = ''
          }
          break
        }

        // 累加数据并逐行处理，防止分块截断一行
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n')
        // 保留最后一个不完整行到缓冲区
        buffer = parts.pop() || ''

        for (const line of parts) {
          const trimmed = line.trim()
          if (!trimmed) continue
          if (trimmed.startsWith('data: ')) {
            const data = trimmed.slice(6).trim() // 移除 'data: '
            if (data) onMessage(data)
          }
        }
      }
    } catch (error) {
      console.error('流式请求失败:', error)
      throw error
    }
  },

  // 更新对话标题
  updateChatTitle(sessionId, title) {
    return request({
      url: `/api/v1/chat/${sessionId}`,
      method: 'put',
      data: { title }
    })
  },

  // 删除对话
  deleteChat(sessionId) {
    return request({
      url: `/api/v1/chat/${sessionId}`,
      method: 'delete'
    })
  }
}
