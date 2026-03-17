import { defineStore } from 'pinia'
import { databaseApi } from '@/api/database'

export const useDatabaseStore = defineStore('database', {
  state: () => ({
    databases: [],
    currentDatabase: null,
    files: []
  }),

  actions: {
    async fetchDatabases() {
      try {
        this.databases = await databaseApi.getDatabases()
        return this.databases
      } catch (error) {
        console.error('获取知识库列表失败:', error)
        return []
      }
    },

    async createDatabase(databaseData) {
      try {
        const newDatabase = await databaseApi.createDatabase(databaseData)
        this.databases.push(newDatabase)
        return newDatabase
      } catch (error) {
        console.error('创建知识库失败:', error)
        throw error
      }
    },

    async uploadFiles(databaseId, files) {
      try {
        const result = await databaseApi.uploadFiles(databaseId, files)
        return result
      } catch (error) {
        console.error('上传文件失败:', error)
        throw error
      }
    },

    async getDatabase(id) {
      try {
        this.currentDatabase = await databaseApi.getDatabase(id)
        return this.currentDatabase
      } catch (error) {
        console.error('获取知识库详情失败:', error)
        throw error
      }
    },

    async getDatabaseFiles(databaseId) {
      try {
        this.files = await databaseApi.getDatabaseFiles(databaseId)
        return this.files
      } catch (error) {
        console.error('获取文件列表失败:', error)
        return []
      }
    },

    async deleteFile(_databaseId, fileId) {
      try {
        await databaseApi.deleteFile(fileId)
        this.files = this.files.filter(file => file.id !== fileId)
      } catch (error) {
        console.error('删除文件失败:', error)
        throw error
      }
    }
  }
})
