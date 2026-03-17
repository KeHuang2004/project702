import { defineStore } from 'pinia'
import { chatApi } from '@/api/chat'

export const useChatStore = defineStore('chat', {
  state: () => ({
    chats: [],
    currentChat: null
  }),

  actions: {
    async getChats() {
      try {
        this.chats = await chatApi.getChats()
        return this.chats
      } catch (error) {
        console.error('获取聊天列表失败:', error)
        return []
      }
    },

    async createChat() {
      try {
        const newChat = {
          id: Date.now(),
          title: '新会话',
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date()
        }
        
        this.chats.unshift(newChat)
        this.currentChat = newChat
        return newChat
      } catch (error) {
        console.error('创建聊天失败:', error)
        throw error
      }
    },

    async sendMessage(chatId, content) {
      try {
        const response = await chatApi.sendMessage(chatId, content)
        return response
      } catch (error) {
        console.error('发送消息失败:', error)
        throw error
      }
    }
  }
})
