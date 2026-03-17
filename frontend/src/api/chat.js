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

  // 发送消息（普通响应）
  sendMessage(sessionId, data) {
    return request({
      url: `/api/v1/chat/${sessionId}`,
      method: 'post',
      data,
    })
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
