<template>
  <div class="homepage-overview">
    <!-- 应用标题区域 -->
    <div class="app-title-section">
      <div class="title-container">
        <div class="app-logo">
          <el-icon class="logo-icon"><DataAnalysis /></el-icon>
        </div>
  <h1 class="app-title">基于成熟智能模型的船舶结构安全性能人机交互系统</h1>
      </div>
    </div>

    <!-- 主要功能区域 - 三个等宽卡片 -->
    <div class="main-function-row">
      <div class="function-card action-function" @click="goToDatabase">
        <div class="action-icon-wrapper knowledge-base-gradient">
          <el-icon class="action-icon"><FolderOpened /></el-icon>
        </div>
        <h3 class="action-title">查看知识库</h3>
        <p class="action-description">管理和浏览您的知识库内容</p>
        <div class="action-arrow">
          <el-icon><ArrowRight /></el-icon>
        </div>
      </div>

        <div class="function-card action-function" @click="goToQApairs">
          <div class="action-icon-wrapper qapair-gradient">
            <el-icon class="action-icon"><Files /></el-icon>
          </div>
          <h3 class="action-title">微调语料库</h3>
          <p class="action-description">管理和浏览微调语料问答对文件</p>
          <div class="action-arrow">
            <el-icon><ArrowRight /></el-icon>
          </div>
        </div>

      <div class="function-card action-function" @click="goToChat">
        <div class="action-icon-wrapper ai-chat-gradient">
          <el-icon class="action-icon"><ChatDotRound /></el-icon>
        </div>
  <h3 class="action-title">智能对话</h3>
        <p class="action-description">与智能助手进行问答对话</p>
        <div class="action-arrow">
          <el-icon><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- 统计信息区域 -->
    <div class="stats-container" v-loading="loading">
      <div class="stats-header">
        <h2 class="stats-title">
          <el-icon><PieChart /></el-icon>
          知识库概览
        </h2>
        <el-button @click="refreshData" class="refresh-btn">
          <el-icon class="refresh-icon" :class="{ 'is-rotating': loading }">
            <Refresh />
          </el-icon>
          刷新数据
        </el-button>
      </div>

      <!-- 统计数据卡片 -->
      <div class="stats-grid">
        <!-- 知识库总数 -->
        <div class="stat-card gradient-blue">
          <div class="stat-icon-wrapper">
            <el-icon class="stat-icon"><Files /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">
              <CountTo
                :startVal="0"
                :endVal="statistics.knowledge_base_count"
                :duration="1500"
              />
            </div>
            <div class="stat-label">知识库总数</div>
            <div class="stat-trend">
              <el-icon><TrendCharts /></el-icon>
              <span>活跃管理中</span>
            </div>
          </div>
        </div>

        <!-- 文档总数 -->
        <div class="stat-card gradient-green">
          <div class="stat-icon-wrapper">
            <el-icon class="stat-icon"><Document /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">
              <CountTo
                :startVal="0"
                :endVal="statistics.document_count"
                :duration="1800"
              />
            </div>
            <div class="stat-label">文档总数</div>
            <div class="stat-trend">
              <el-icon><CircleCheckFilled /></el-icon>
              <span>已索引完成</span>
            </div>
          </div>
        </div>

        <!-- 存储空间 -->
        <div class="stat-card gradient-purple">
          <div class="stat-icon-wrapper">
            <el-icon class="stat-icon"><Coin /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">
              {{ formatStorageSize(statistics.knowledge_size) }}
            </div>
            <div class="stat-label">存储空间</div>
            <div class="stat-trend">
              <el-icon><UploadFilled /></el-icon>
              <span>累计使用</span>
            </div>
          </div>
        </div>

        <!-- 平均文档数 -->
        <div class="stat-card gradient-orange">
          <div class="stat-icon-wrapper">
            <el-icon class="stat-icon"><DataLine /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">
              {{ averageDocuments }}
            </div>
            <div class="stat-label">平均文档数</div>
            <div class="stat-trend">
              <el-icon><Histogram /></el-icon>
              <span>每个知识库</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 系统状态 -->
      <div class="system-status-card">
        <h3 class="status-title">
          <el-icon><Monitor /></el-icon>
          系统状态
        </h3>
        <div class="system-status">
          <div class="status-item">
            <span class="status-label">服务状态</span>
            <el-tag type="success">运行正常</el-tag>
          </div>
          <div class="status-item">
            <span class="status-label">API响应</span>
            <el-tag>{{ responseTime }}ms</el-tag>
          </div>
          <div class="status-item">
            <span class="status-label">数据版本</span>
            <el-tag>v1.0.0</el-tag>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  DataAnalysis, Refresh, FolderOpened, Files, Document,
  Coin, DataLine, PieChart, InfoFilled,
  TrendCharts, CircleCheckFilled, UploadFilled, Histogram,
  Monitor, ChatDotRound, ArrowRight
} from '@element-plus/icons-vue'
import { getKnowledgeBaseAttributesForIds, getKnowledgeBaseList } from '@/api/knowledge'
import CountTo from '@/components/CountTo.vue'

// 路由
const router = useRouter()

// 响应式数据
const loading = ref(false)
const statistics = ref({
  knowledge_base_count: 0,
  document_count: 0,
  knowledge_size: 0,
  statistics_chart_url: ''
})
const zoomLevel = ref(1)
const responseTime = ref(0)

// 计算属性
const averageDocuments = computed(() => {
  if (statistics.value.knowledge_base_count === 0) return 0
  return Math.round(statistics.value.document_count / statistics.value.knowledge_base_count)
})

// 主要功能按钮跳转
const goToDatabase = () => {
  router.push('/home/knowledge_base')
}

const goToChat = () => {
  router.push('/chat')
}

const goToQApairs = () => {
  router.push('/QApair')
}
// 获取统计数据
const fetchStatistics = async () => {
  loading.value = true
  const startTime = Date.now()

  try {
    // 1) 获取知识库ID列表
    const kbListRes = await getKnowledgeBaseList()
    const kbIds = kbListRes?.data?.ids || []
    const knowledge_base_count = kbIds.length

    // 若无知识库，直接清零
    if (kbIds.length === 0) {
      statistics.value = {
        knowledge_base_count,
        document_count: 0,
        knowledge_size: 0,
        statistics_chart_url: ''
      }
      responseTime.value = Date.now() - startTime
      return
    }

    // 2) 一次性获取多个知识库的 files_list 与 total_size
    const attrs = ['files_list', 'total_size']
    let kbAttrList = []
    try {
      const resAttrs = await getKnowledgeBaseAttributesForIds(kbIds, attrs)
      const data = resAttrs?.data || null
      const items = Array.isArray(data?.items)
        ? data.items
        : data && typeof data === 'object'
          ? [data]
          : []
      kbAttrList = items.map((item, idx) => ({
        id: kbIds[idx],
        files_list: Array.isArray(item?.files_list) ? item.files_list : [],
        total_size: parseInt(item?.total_size || 0, 10) || 0
      }))
    } catch (err) {
      console.error('获取知识库属性失败:', err)
      kbAttrList = kbIds.map(id => ({ id, files_list: [], total_size: 0 }))
    }

    // 3) 聚合文档数和总大小
    const document_count = kbAttrList.reduce((sum, kb) => sum + (kb.files_list?.length || 0), 0)
    const knowledge_size = kbAttrList.reduce((sum, kb) => sum + (kb.total_size || 0), 0)

    statistics.value = {
      knowledge_base_count,
      document_count,
      knowledge_size,
      statistics_chart_url: ''
    }

    responseTime.value = Date.now() - startTime
  } catch (error) {
    console.error('获取概览统计失败:', error)
  } finally {
    loading.value = false
  }
}

// 格式化存储大小
const formatStorageSize = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const index = Math.floor(Math.log(bytes) / Math.log(1024))
  const size = (bytes / Math.pow(1024, index)).toFixed(2)
  return `${size} ${units[index]}`
}

// 刷新数据
const refreshData = () => {
  fetchStatistics()
}

// 保留缩放状态变量以备后续扩展，但不再暴露词云相关操作

// 自动刷新
let refreshTimer = null

onMounted(() => {
  fetchStatistics()

  // 每30秒自动刷新一次
  refreshTimer = setInterval(() => {
    fetchStatistics()
  }, 30000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.homepage-overview {
  min-height: 100vh;
  background: linear-gradient(135deg, #9dcde4 0%, #5f6bcf 100%);
  padding: 40px 20px 20px;
}

/* 应用标题区域 */
.app-title-section {
  text-align: center;
  margin-bottom: 60px;
  padding: 40px 20px;
}

.title-container {
  max-width: 800px;
  margin: 0 auto;
}

.app-logo {
  margin-bottom: 20px;
}

.logo-icon {
  font-size: 80px;
  color: rgba(255, 255, 255, 0.9);
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2));
}

.app-title {
  font-size: 48px;
  font-weight: 800;
  color: rgb(255, 255, 255);
  margin: 0 0 16px 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  letter-spacing: 2px;
  background: linear-gradient(45deg, #1800b4, #01004d);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.app-subtitle {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
  font-weight: 300;
  letter-spacing: 1px;
}

/* 主要功能区域 - 三等分布局 */
.main-function-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr); /* 三列布局 */
  gap: 30px;
  max-width: 1200px;
  margin: 0 auto 60px;
}

@media (max-width: 768px) {
  .main-function-row {
    grid-template-columns: 1fr; /* 移动端单列展示 */
    max-width: 500px;
  }
}

.function-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 20px;
  padding: 30px;
  text-align: center;
  transition: all 0.4s ease;
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  min-height: 280px;
  display: flex;
  flex-direction: column;
}

.function-card.action-function {
  cursor: pointer;
}

.function-card.action-function:hover {
  transform: translateY(-10px) scale(1.02);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.function-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
  transition: left 0.6s;
}

.function-card.action-function:hover::before {
  left: 100%;
}

/* 词云相关样式已移除 */

/* 主要功能按钮 */
.main-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 30px;
  max-width: 800px;
  margin: 0 auto 60px;
}

.action-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 20px;
  padding: 40px 30px;
  text-align: center;
  cursor: pointer;
  transition: all 0.4s ease;
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.action-card:hover {
  transform: translateY(-10px) scale(1.02);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.action-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
  transition: left 0.6s;
}

.action-card:hover::before {
  left: 100%;
}

.action-icon-wrapper {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
  position: relative;
  z-index: 1;
}

.knowledge-base-gradient {
  background: linear-gradient(135deg, #4c63d2 0%, #667eea 100%);
}

.ai-chat-gradient {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}

.qapair-gradient {
  background: linear-gradient(135deg, #ff7e5f 0%, #feb47b 100%);
}

.action-icon {
  font-size: 36px;
  color: white;
}

.action-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 12px 0;
}

.action-description {
  font-size: 16px;
  color: #666;
  margin: 0 0 20px 0;
  line-height: 1.5;
}

.action-arrow {
  position: absolute;
  bottom: 20px;
  right: 25px;
  color: #999;
  transition: all 0.3s;
}

.action-card:hover .action-arrow {
  color: #667eea;
  transform: translateX(5px);
}

/* 统计信息区域 */
.stats-container {
  max-width: 1400px;
  margin: 0 auto;
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding: 20px 30px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.stats-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 24px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
}

.refresh-icon {
  transition: transform 0.3s;
}

.refresh-icon.is-rotating {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 统计卡片网格 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
  margin-bottom: 30px;
}

.stat-card {
  position: relative;
  padding: 24px;
  border-radius: 16px;
  color: white;
  overflow: hidden;
  transition: transform 0.3s, box-shadow 0.3s;
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.2);
}

.gradient-blue {
  background: linear-gradient(135deg, #7f91e2 0%, #4c63d2 100%);
}

.gradient-green {
  background: linear-gradient(135deg, #63c586 0%, #2ca055 100%);
}

.gradient-purple {
  background: linear-gradient(135deg, #ad70c5 0%, #783496 100%);
}

.gradient-orange {
  background: linear-gradient(135deg, #ff9f43 0%, #ff6b6b 100%);
}

.stat-icon-wrapper {
  width: 70px;
  height: 70px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon {
  font-size: 36px;
  color: white;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 12px;
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  opacity: 0.8;
}

/* 可视化部分 */
.visualization-section {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 30px;
  margin-bottom: 30px;
  backdrop-filter: blur(10px);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid #f0f0f0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.section-actions {
  display: flex;
  gap: 12px;
}

.chart-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chart-wrapper {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  overflow: hidden;
}

.wordcloud-image {
  max-width: 100%;
  height: auto;
  transition: transform 0.3s ease;
  cursor: zoom-in;
}

.chart-info {
  display: flex;
  justify-content: center;
}

/* 系统状态卡片 */
.system-status-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 24px;
  backdrop-filter: blur(10px);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.status-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 20px 0;
  padding-bottom: 12px;
  border-bottom: 2px solid #f0f0f0;
}

.system-status {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
}

.status-label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .app-title {
    font-size: 32px;
  }

  .app-subtitle {
    font-size: 16px;
  }

  .main-actions {
    grid-template-columns: 1fr;
  }

  .main-function-row {
    grid-template-columns: 1fr;
    gap: 20px;
    margin-bottom: 40px;
  }

  .function-card {
    min-height: auto;
    padding: 25px;
  }

  .wordcloud-wrapper {
    min-height: 150px;
  }

  .wordcloud-image-compact {
    max-height: 150px;
  }

  .stats-header {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .system-status {
    grid-template-columns: 1fr;
  }
}
</style>
