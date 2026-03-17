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
            <el-button
              size="medium"
              :type="appModeValue === 'generate' ? 'primary' : 'default'"
              @click="appModeValue = 'generate'"
            >
              普通模式
            </el-button>
            <el-button
              size="medium"
              :type="appModeValue === 'rag' ? 'primary' : 'default'"
              class="rag-mode-btn"
              :disabled="!canSelectSummaryMode"
              @click="handleRagModeClick"
            >
              RAG 模式
            </el-button>
            <el-button
              size="medium"
              :type="appModeValue === 'literature-review' ? 'primary' : 'default'"
              class="review-mode-btn"
              :disabled="!canSelectSummaryMode"
              @click="handleLiteratureReviewModeClick"
            >
              文献综述
            </el-button>
            <el-button
              size="medium"
              :type="appModeValue === 'summary' ? 'primary' : 'default'"
              class="summary-mode-btn"
              :disabled="!canSelectSummaryMode"
              @click="handleSummaryModeClick"
            >
              要点提炼
            </el-button>
            <span
              v-if="appModeValue === 'rag' && selectedRagKbName"
              class="rag-selected-kb"
            >
              当前检索库：{{ selectedRagKbName }}
            </span>
            <span
              v-if="appModeValue === 'literature-review' && selectedReviewKbName"
              class="rag-selected-kb"
            >
              当前综述库：{{ selectedReviewKbName }}
            </span>
          </div>
        </div>

      <el-dialog
        v-model="summaryDialogVisible"
        title="要点提炼设置"
        width="640px"
        destroy-on-close
      >
        <div class="summary-dialog-body">
          <div class="summary-row">
            <div class="summary-row-label">请选择需要要点提炼文件所属的知识库</div>
            <el-input
              v-model="kbSearchKeyword"
              placeholder="搜索知识库名称"
              clearable
              class="summary-search-input"
            />
            <el-select
              v-model="summarySelection.kbId"
              placeholder="未选择"
              clearable
              filterable
              class="summary-select"
              @change="handleKbChange"
            >
              <el-option
                v-for="kb in pagedKbOptions"
                :key="kb.id"
                :label="kb.name"
                :value="kb.id"
              />
            </el-select>
            <el-pagination
              v-if="filteredKbOptions.length > kbPageSize"
              v-model:current-page="kbPage"
              :page-size="kbPageSize"
              :total="filteredKbOptions.length"
              layout="prev, pager, next"
              small
              class="summary-pagination"
            />
          </div>

          <div class="summary-row">
            <div class="summary-row-label">请选择需要提炼要点的文件</div>
            <el-input
              v-model="fileSearchKeyword"
              placeholder="搜索文件名称"
              clearable
              class="summary-search-input"
              :disabled="!summarySelection.kbId"
            />
            <el-select
              v-model="summarySelection.fileId"
              placeholder="未选择"
              clearable
              filterable
              class="summary-select"
              popper-class="summary-file-select-popper"
              :disabled="!summarySelection.kbId"
            >
              <el-option
                v-for="file in filteredFileOptions"
                :key="file.id"
                :label="file.name"
                :value="file.id"
              />
            </el-select>
          </div>
        </div>

        <template #footer>
          <el-button @click="summaryDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="summarySaving" @click="confirmSummaryMode">确认</el-button>
        </template>
      </el-dialog>

      <el-dialog
        v-model="ragDialogVisible"
        title="RAG 模式设置"
        width="640px"
        destroy-on-close
      >
        <div class="summary-dialog-body">
          <div class="summary-row">
            <div class="summary-row-label">请选择 RAG 检索使用的知识库</div>
            <el-input
              v-model="kbSearchKeyword"
              placeholder="搜索知识库名称"
              clearable
              class="summary-search-input"
            />
            <el-select
              v-model="ragSelection.kbId"
              placeholder="未选择"
              clearable
              filterable
              class="summary-select"
            >
              <el-option
                v-for="kb in pagedKbOptions"
                :key="kb.id"
                :label="kb.name"
                :value="kb.id"
              />
            </el-select>
            <el-pagination
              v-if="filteredKbOptions.length > kbPageSize"
              v-model:current-page="kbPage"
              :page-size="kbPageSize"
              :total="filteredKbOptions.length"
              layout="prev, pager, next"
              small
              class="summary-pagination"
            />
          </div>
        </div>

        <template #footer>
          <el-button @click="ragDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="ragSaving" @click="confirmRagMode">确认</el-button>
        </template>
      </el-dialog>

      <el-dialog
        v-model="reviewDialogVisible"
        title="文献综述设置"
        width="640px"
        destroy-on-close
      >
        <div class="summary-dialog-body">
          <div class="summary-row">
            <div class="summary-row-label">请选择文献综述使用的知识库</div>
            <el-input
              v-model="kbSearchKeyword"
              placeholder="搜索知识库名称"
              clearable
              class="summary-search-input"
            />
            <el-select
              v-model="reviewSelection.kbId"
              placeholder="未选择"
              clearable
              filterable
              class="summary-select"
            >
              <el-option
                v-for="kb in pagedKbOptions"
                :key="kb.id"
                :label="kb.name"
                :value="kb.id"
              />
            </el-select>
            <el-pagination
              v-if="filteredKbOptions.length > kbPageSize"
              v-model:current-page="kbPage"
              :page-size="kbPageSize"
              :total="filteredKbOptions.length"
              layout="prev, pager, next"
              small
              class="summary-pagination"
            />
          </div>
        </div>

        <template #footer>
          <el-button @click="reviewDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="reviewSaving" @click="confirmLiteratureReviewMode">确认</el-button>
        </template>
      </el-dialog>

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
import {
  getKnowledgeBaseList,
  getKnowledgeBaseAttributesForIds,
  getKnowledgeBaseAttributes,
  getFileAttributesForIds,
} from '@/api/knowledge'

const router = useRouter()
const route = useRoute()
const activeTab = ref('database')

// 全局模式（'generate' | 'rag' | 'summary'）
const appModeValue = ref(localStorage.getItem('appMode') || 'generate')
const selectedRagKbName = ref(localStorage.getItem('selectedRagKbName') || '')
const selectedReviewKbName = ref(localStorage.getItem('selectedReviewKbName') || '')

const summaryDialogVisible = ref(false)
const summarySaving = ref(false)
const ragDialogVisible = ref(false)
const ragSaving = ref(false)
const reviewDialogVisible = ref(false)
const reviewSaving = ref(false)
const ragSelection = ref({
  kbId: null,
})
const reviewSelection = ref({
  kbId: null,
})
const summarySelection = ref({
  kbId: null,
  fileId: null,
})

const kbOptions = ref([])
const fileOptions = ref([])

const kbSearchKeyword = ref('')
const fileSearchKeyword = ref('')
const kbPage = ref(1)
const kbPageSize = 8

const filteredKbOptions = computed(() => {
  const keyword = kbSearchKeyword.value.trim().toLowerCase()
  if (!keyword) return kbOptions.value
  return kbOptions.value.filter((item) => (item.name || '').toLowerCase().includes(keyword))
})

const pagedKbOptions = computed(() => {
  const start = (kbPage.value - 1) * kbPageSize
  return filteredKbOptions.value.slice(start, start + kbPageSize)
})

const filteredFileOptions = computed(() => {
  const keyword = fileSearchKeyword.value.trim().toLowerCase()
  if (!keyword) return fileOptions.value
  return fileOptions.value.filter((item) => (item.name || '').toLowerCase().includes(keyword))
})

// 持久化模式并提供给子组件
watch(appModeValue, (v) => {
  try { localStorage.setItem('appMode', v) } catch (e) { /* ignore */ }
})
provide('appMode', appModeValue)

watch(kbSearchKeyword, () => {
  kbPage.value = 1
})

// 计算是否显示顶部导航
const showHeader = computed(() => {
  // 首页 /statistic 不显示顶部导航，其余页面显示
  return route.path !== '/statistic'
})

const canSelectSummaryMode = computed(() => {
  if (!route.path.startsWith('/chat')) return false
  const chatTitle = route.params.chatTitle
  if (Array.isArray(chatTitle)) return chatTitle.length > 0 && Boolean(chatTitle[0])
  return Boolean(chatTitle)
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

const handleSummaryModeClick = async () => {
  if (!canSelectSummaryMode.value) {
    ElMessage.warning('请先进入一个具体会话，再使用要点提炼模式')
    return
  }

  if (appModeValue.value === 'summary') {
    appModeValue.value = 'generate'
    localStorage.setItem('appMode', 'generate')
    localStorage.removeItem('selectedKbId')
    localStorage.removeItem('selectedKbName')
    localStorage.removeItem('selectedFileId')
    localStorage.removeItem('selectedFileName')
    localStorage.removeItem('autoSend')
    ElMessage.success('已退出要点提炼模式')
    return
  }

  await openSummaryDialog()
}

const handleRagModeClick = async () => {
  if (!canSelectSummaryMode.value) {
    ElMessage.warning('请先进入一个具体会话，再使用 RAG 模式')
    return
  }

  if (appModeValue.value === 'rag') {
    appModeValue.value = 'generate'
    localStorage.setItem('appMode', 'generate')
    localStorage.removeItem('selectedRagKbId')
    localStorage.removeItem('selectedRagKbName')
    selectedRagKbName.value = ''
    ElMessage.success('已退出 RAG 模式')
    return
  }

  await openRagDialog()
}

const handleLiteratureReviewModeClick = async () => {
  if (!canSelectSummaryMode.value) {
    ElMessage.warning('请先进入一个具体会话，再使用文献综述模式')
    return
  }

  if (appModeValue.value === 'literature-review') {
    appModeValue.value = 'generate'
    localStorage.setItem('appMode', 'generate')
    localStorage.removeItem('selectedReviewKbId')
    localStorage.removeItem('selectedReviewKbName')
    selectedReviewKbName.value = ''
    ElMessage.success('已退出文献综述模式')
    return
  }

  await openReviewDialog()
}

watch(
  () => canSelectSummaryMode.value,
  (enabled) => {
    if (!enabled && (appModeValue.value === 'summary' || appModeValue.value === 'rag' || appModeValue.value === 'literature-review')) {
      appModeValue.value = 'generate'
      localStorage.setItem('appMode', 'generate')
      localStorage.removeItem('selectedRagKbId')
      localStorage.removeItem('selectedRagKbName')
      localStorage.removeItem('selectedReviewKbId')
      localStorage.removeItem('selectedReviewKbName')
      selectedRagKbName.value = ''
      selectedReviewKbName.value = ''
    }
  }
)

const normalizeAttributeItems = (rawData) => {
  if (Array.isArray(rawData?.items)) return rawData.items
  if (rawData && typeof rawData === 'object') return [rawData]
  return []
}

const loadKnowledgeBaseOptions = async () => {
  const listRes = await getKnowledgeBaseList()
  const ids = listRes?.data?.ids || []
  if (!ids.length) {
    kbOptions.value = []
    return
  }

  const attrsRes = await getKnowledgeBaseAttributesForIds(ids, ['name'])
  const items = normalizeAttributeItems(attrsRes?.data)
  kbOptions.value = items
    .map((item, index) => ({
      id: ids[index],
      name: item?.name || `知识库 ${ids[index]}`,
    }))
    .filter((item) => item.id != null)
}

const loadFileOptionsByKb = async (kbId) => {
  if (!kbId) {
    fileOptions.value = []
    return
  }

  const kbRes = await getKnowledgeBaseAttributes(kbId, ['files_list'])
  const ids = kbRes?.data?.files_list || []
  if (!ids.length) {
    fileOptions.value = []
    return
  }

  const attrsRes = await getFileAttributesForIds(ids, ['filename'])
  const items = normalizeAttributeItems(attrsRes?.data)
  fileOptions.value = items
    .map((item, index) => ({
      id: ids[index],
      name: item?.filename || `文件 ${ids[index]}`,
    }))
    .filter((item) => item.id != null)
}

const openSummaryDialog = async () => {
  summaryDialogVisible.value = true
  summarySelection.value = {
    kbId: null,
    fileId: null,
  }
  fileOptions.value = []
  kbSearchKeyword.value = ''
  fileSearchKeyword.value = ''
  kbPage.value = 1

  try {
    await loadKnowledgeBaseOptions()
  } catch (error) {
    console.error('加载知识库选项失败:', error)
    ElMessage.error('加载知识库失败，请稍后重试')
  }
}

const openRagDialog = async () => {
  ragDialogVisible.value = true
  ragSelection.value = {
    kbId: null,
  }
  kbSearchKeyword.value = ''
  kbPage.value = 1

  try {
    await loadKnowledgeBaseOptions()
  } catch (error) {
    console.error('加载知识库选项失败:', error)
    ElMessage.error('加载知识库失败，请稍后重试')
  }
}

const openReviewDialog = async () => {
  reviewDialogVisible.value = true
  reviewSelection.value = {
    kbId: null,
  }
  kbSearchKeyword.value = ''
  kbPage.value = 1

  try {
    await loadKnowledgeBaseOptions()
  } catch (error) {
    console.error('加载知识库选项失败:', error)
    ElMessage.error('加载知识库失败，请稍后重试')
  }
}

const handleKbChange = async (kbId) => {
  summarySelection.value.fileId = null
  fileSearchKeyword.value = ''
  try {
    await loadFileOptionsByKb(kbId)
  } catch (error) {
    console.error('加载文件选项失败:', error)
    ElMessage.error('加载文件列表失败，请稍后重试')
  }
}

const confirmSummaryMode = async () => {
  if (!summarySelection.value.kbId) {
    ElMessage.warning('请先选择知识库')
    return
  }

  if (!summarySelection.value.fileId) {
    ElMessage.warning('请选择需要提炼要点的文件')
    return
  }

  const selectedFile = fileOptions.value.find((item) => item.id === summarySelection.value.fileId)
  const selectedKb = kbOptions.value.find((item) => item.id === summarySelection.value.kbId)
  if (!selectedFile) {
    ElMessage.warning('未找到选中文件，请重新选择')
    return
  }

  summarySaving.value = true
  try {
    localStorage.setItem('appMode', 'summary')
    localStorage.setItem('selectedKbId', String(summarySelection.value.kbId))
    localStorage.setItem('selectedKbName', selectedKb?.name || '')
    localStorage.setItem('selectedFileId', String(summarySelection.value.fileId))
    localStorage.setItem('selectedFileName', selectedFile.name)
    appModeValue.value = 'summary'

    summaryDialogVisible.value = false
    ElMessage.success('已切换到要点提炼模式')
    if (!route.path.startsWith('/chat')) {
      await router.push('/chat')
    }
  } finally {
    summarySaving.value = false
  }
}

const confirmRagMode = async () => {
  if (!ragSelection.value.kbId) {
    ElMessage.warning('请先选择知识库')
    return
  }

  const selectedKb = kbOptions.value.find((item) => item.id === ragSelection.value.kbId)
  ragSaving.value = true
  try {
    localStorage.setItem('appMode', 'rag')
    localStorage.setItem('selectedRagKbId', String(ragSelection.value.kbId))
    localStorage.setItem('selectedRagKbName', selectedKb?.name || '')
    selectedRagKbName.value = selectedKb?.name || ''
    appModeValue.value = 'rag'

    ragDialogVisible.value = false
    ElMessage.success('已切换到 RAG 模式')
    if (!route.path.startsWith('/chat')) {
      await router.push('/chat')
    }
  } finally {
    ragSaving.value = false
  }
}

const confirmLiteratureReviewMode = async () => {
  if (!reviewSelection.value.kbId) {
    ElMessage.warning('请先选择知识库')
    return
  }

  const selectedKb = kbOptions.value.find((item) => item.id === reviewSelection.value.kbId)
  reviewSaving.value = true
  try {
    localStorage.setItem('appMode', 'literature-review')
    localStorage.setItem('selectedReviewKbId', String(reviewSelection.value.kbId))
    localStorage.setItem('selectedReviewKbName', selectedKb?.name || '')
    selectedReviewKbName.value = selectedKb?.name || ''
    appModeValue.value = 'literature-review'

    reviewDialogVisible.value = false
    ElMessage.success('已切换到文献综述模式')
    if (!route.path.startsWith('/chat')) {
      await router.push('/chat')
    }
  } finally {
    reviewSaving.value = false
  }
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

.summary-mode-btn {
  margin-left: 4px;
}

.rag-mode-btn {
  margin-left: 4px;
}

.review-mode-btn {
  margin-left: 4px;
}

.rag-selected-kb {
  margin-left: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  background: #f2f8ff;
  color: #1f4f8a;
  border: 1px solid #d8e9ff;
  font-size: 12px;
  white-space: nowrap;
}

.summary-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.summary-row {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.summary-row-label {
  color: #374151;
  font-weight: 600;
}

.summary-search-input,
.summary-select {
  width: 100%;
}

.summary-pagination {
  display: flex;
  justify-content: flex-end;
}

:global(.summary-file-select-popper .el-select-dropdown__wrap) {
  max-height: 260px;
}
</style>
