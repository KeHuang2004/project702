import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // 默认进入 问答页面（Chat）
    { path: '/', redirect: '/chat' },

    // 系统概览页面（原 DatabaseOverview），路由改名为 /statistic
    {
      path: '/statistic',
      name: 'Statistic',
      component: () => import('@/views/DatabaseOverview.vue')
    },

    // 知识库主页（原 /database/management）
    {
      path: '/home/knowledge_base',
      name: 'KnowledgeHome',
      component: () => import('@/views/DatabaseManagement.vue')
    },

    // 知识库创建（原 /database/create）
    {
      path: '/knowledge_base/create',
      name: 'KnowledgeCreate',
      component: () => import('@/views/CreateKnowledge.vue')
    },

    // 查看知识库下文件（原 /database/:id/files）
    {
      path: '/knowledge_base/:id/files',
      name: 'KnowledgeFiles',
      component: () => import('@/views/DatabaseFiles.vue')
    },

    // 文件详情（原 /database/:kbId/file/:fileId）
    {
      // 重命名为更语义化的 chunks 路径；fileId 从 query 中读取（兼容旧别名已删除）
      path: '/knowledge_base/:kbId/file/chunks',
      name: 'FileDetail',
      component: () => import('@/views/FileDetail.vue'),
      props: route => ({
        kbId: route.params.kbId,
        // 兼容：从 query 中读取 fileId（如果没有则为 null）
        fileId: route.query.fileId || null
      })
    },

    // 知识库检索（原 /database/:kbId/retrieve）
    {
      path: '/knowledge_base/:kbId/retrieve',
      name: 'KnowledgeBaseRetrieve',
      component: () => import('@/views/KnowledgeBaseRetrieve.vue'),
      meta: { title: '知识库检索', requiresAuth: true }
    },

    // 文本块嵌入页面
    {
      path: '/knowledge_base/:kbId/chunks/embed',
      name: 'ChunkEmbedding',
      component: () => import('@/views/ChunkEmbedding.vue'),
      meta: { title: '文本块嵌入' }
    },


  // AI 对话
  { path: '/chat/:chatTitle?', name: 'ChatInterface', component: () => import('@/views/ChatInterface.vue') },
  { path: '/file-selector', name: 'FileSelector', component: () => import('@/views/FileSelector.vue') },

    // QApair 管理与上传（兼容旧小写路径）
    { path: '/QApair', name: 'QApairManagement', component: () => import('@/views/QApairManagement.vue'), alias: ['/qapairs'] },
    { path: '/QApair/upload', name: 'QApairUpload', component: () => import('@/views/QApairUpload.vue'), alias: ['/qapairs/upload'] },
  { path: '/QApair/:id', name: 'QApairDetail', component: () => import('@/views/QApairDetail.vue') },

  ]
})

export default router
