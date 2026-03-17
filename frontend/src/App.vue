<template>
  <div id="app">
    <el-container class="app-container">
      <!-- 顶部导航 - 在首页时隐藏 -->
      <el-header class="app-header" v-if="showHeader">
        <div class="header-content">
          <div class="logo">
            <span class="logo-text">基于成熟智能模型的船舶结构安全性能人机交互系统</span>
          </div>
          <!-- 中间的导航按钮（固定居中） -->
          <div class="nav-buttons">
            <el-button
              :type="activeTab === 'database' ? 'primary' : ''"
              :class="{ 'active-button': activeTab === 'database' }"
              @click="goToDatabase"
              class="nav-button"
            >
              知识库
            </el-button>
            <el-button
              :type="activeTab === 'qapair' ? 'primary' : ''"
              :class="{ 'active-button': activeTab === 'qapair' }"
              @click="goToQApair"
              class="nav-button"
            >
              微调语料库
            </el-button>
            <el-button
              :type="activeTab === 'chat' ? 'primary' : ''"
              :class="{ 'active-button': activeTab === 'chat' }"
              @click="goToChat"
              class="nav-button"
            >
              智能对话
            </el-button>
            <el-button
              :type="activeTab === 'overview' ? 'primary' : ''"
              :class="{ 'active-button': activeTab === 'overview' }"
              @click="goToSystemOverview"
              class="nav-button"
            >
              系统概览
            </el-button>
          </div>
          
        </div>
      </el-header>

        <!-- 模式选择栏：位于中间导航下方的固定窗口 -->
        <div v-if="route.path.startsWith('/chat')" class="mode-bar">
          <div class="mode-bar-inner">
            <div class="mode-label">模式选择：</div>
            <el-radio-group v-model="appModeValue" size="medium">
              <el-radio-button label="generate">普通模式</el-radio-button>
              <el-radio-button label="rag">RAG 模式</el-radio-button>
            </el-radio-group>
            <el-button type="primary" size="medium" @click="goToSummaryMode">要点提炼</el-button>
            <el-button type="primary" size="medium" @click="goToLiteratureMode">文献综述</el-button>
          </div>
        </div>

      <!-- 主要内容区域 -->
      <el-main class="app-main" :class="{ 'homepage-main': !showHeader }">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, watch, computed, provide } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const activeTab = ref('database')

// 全局模式（'generate' | 'rag'）
const appModeValue = ref(localStorage.getItem('appMode') || 'generate')

// 持久化模式并提供给子组件
watch(appModeValue, (v) => {
  try { localStorage.setItem('appMode', v) } catch (e) { /* ignore */ }
})
provide('appMode', appModeValue)

// 计算是否显示顶部导航
const showHeader = computed(() => {
  // 首页 /statistic 不显示顶部导航，其余页面显示
  return route.path !== '/statistic'
})

// 监听路由变化，同步更新 activeTab
watch(() => route.path, (newPath) => {
  console.log('路由变化:', newPath)
  if (newPath === '/statistic') {
    activeTab.value = 'overview'
  } else if (newPath.startsWith('/home/knowledge_base') || newPath.startsWith('/knowledge_base')) {
    activeTab.value = 'database'
  } else if (newPath.startsWith('/QApair')) {
    activeTab.value = 'qapair'
  } else if (newPath.startsWith('/chat')) {
    activeTab.value = 'chat'
  }
}, { immediate: true })

const goToDatabase = () => {
  console.log('点击知识库按钮')
  activeTab.value = 'database'
  router.push('/home/knowledge_base').then(() => {
    console.log('成功跳转到知识库页面')
  }).catch(err => {
    console.error('跳转失败:', err)
  })
}

const goToChat = () => {
  console.log('点击智能对话按钮')
  activeTab.value = 'chat'
  router.push('/chat').then(() => {
    console.log('成功跳转到智能对话页面')
  }).catch(err => {
    console.error('跳转失败:', err)
  })
}

const goToQApair = () => {
  console.log('点击微调语料库按钮')
  activeTab.value = 'qapair'
  router.push('/QApair').catch(err => {
    console.error('跳转失败:', err)
  })
}

const goToSystemOverview = () => {
  console.log('点击系统概览按钮')
  activeTab.value = 'overview'
  router.push('/statistic').catch(err => {
    console.error('跳转失败:', err)
  })
}

const goToSummaryMode = () => {
  router.push('/file-selector')
}

const goToLiteratureMode = () => {
  // 暂不实现
  ElMessage.info('文献综述功能暂未实现')
}

 
</script>

<style scoped>
.app-container {
  height: 100vh;
}

.app-header {
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  padding: 0;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 0 24px;
}

.header-content {
  position: relative; /* 使绝对定位的 nav-buttons 居中 */
}

.logo-text {
  font-size: 20px;
  font-weight: bold;
  color: #1f2937;
}

/* 中间导航按钮样式 */
.nav-buttons {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 12px;
  align-items: center;
}

.nav-button {
  padding: 8px 24px;
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.3s ease;
  min-width: 120px; /* 三个按钮大小一致 */
}

/* 非激活状态的按钮样式 */
.nav-button:not(.active-button) {
  background: transparent;
  border: 1px solid #d1d5db;
  color: #6b7280;
}

.nav-button:not(.active-button):hover {
  background: #f9fafb;
  border-color: #9ca3af;
  color: #374151;
  transform: translateY(-2px) scale(1.02); /* 悬停放大/浮起效果 */
  box-shadow: 0 6px 18px rgba(0,0,0,0.08);
}

/* 激活按钮悬停时也有轻微浮起效果 */
.active-button:hover {
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 6px 18px rgba(59, 130, 246, 0.25);
}

/* 激活状态的按钮样式 */
.active-button {
  background: #3b82f6 !important;
  border-color: #3b82f6 !important;
  color: white !important;
}

 

.app-main {
  padding: 0;
  background: #f9fafb;
}

.homepage-main {
  padding: 0;
  background: transparent;
}

.mode-bar {
  background: #ffffff;
  border-bottom: 1px solid #e6edf6;
  padding: 10px 0;
  box-shadow: 0 2px 8px rgba(16,24,40,0.03);
}
.mode-bar-inner {
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: flex-start;
}
.mode-label {
  color: #6b7280;
  font-weight: 600;
  margin-right: 6px;
}
</style>
