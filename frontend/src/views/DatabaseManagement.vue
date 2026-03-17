<template>
  <div class="database-management">

    <div class="header-bar">
      <div class="header-left">
        <h2 class="page-title">知识库管理</h2>
      </div>
      <div class="header-right">
        <el-button @click="refreshData" class="refresh-btn">
          <el-icon>
            <Refresh />
          </el-icon>
          刷新
        </el-button>
      </div>
      <div class="header-center">
        <el-input v-model="searchText" placeholder="知识库搜索" class="search-input" clearable @input="handleSearch">
          <template #prefix>
            <el-icon>
              <Search />
            </el-icon>
          </template>
        </el-input>
        <el-button @click="openLatestDocDialog" class="latest-doc-btn">
          <el-icon>
            <Download />
          </el-icon>
          <span class="create-text">获取最新文档</span>
        </el-button>
        <el-button type="primary" @click="createDatabase" class="create-btn">
          <el-icon>
            <Plus />
          </el-icon>
          <span class="create-text">创建知识库</span>
        </el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="3" animated />
    </div>

    <!-- 知识库卡片网格 -->
    <div class="content-area" v-else>
      <div class="database-grid" v-if="filteredDatabases.length > 0">
  <div v-for="database in pagedDatabases" :key="database.id" class="database-card" @click="openDatabase(database)">
          <!-- 卡片图标 -->
          <div class="card-header">
            <div class="database-icon">
              <el-icon>
                <Folder />
              </el-icon>
            </div>
            <!-- 右上角操作菜单 -->
            <div class="card-menu" @click.stop>
              <el-dropdown trigger="click" placement="bottom-end" popper-class="database-dropdown">
                <el-button link size="small" class="menu-trigger" @click.stop>
                  <el-icon>
                    <MoreFilled />
                  </el-icon>
                </el-button>

                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="editDatabase(database)">
                      <el-icon class="menu-icon">
                        <Edit />
                      </el-icon>
                      <span>编辑信息</span>
                    </el-dropdown-item>
                    <el-dropdown-item @click="deleteDatabase(database)" divided class="delete-item">
                      <el-icon class="menu-icon">
                        <Delete />
                      </el-icon>
                      <span>删除知识库</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
        </el-dropdown>
      </div>
          </div>

          <!-- 卡片标题和描述 -->
          <div class="card-content">
            <h3 class="database-title" :title="database.name">
              {{ database.name }}
            </h3>
            <p class="database-description" :title="database.description">
              {{ database.description || '暂无描述' }}
            </p>

            <!-- 状态标签 -->
            <div class="status-tags">
              <el-tag :type="getStatusType(database.status || 'active')" size="small">
                {{ getStatusText(database.status || 'active') }}
              </el-tag>
            </div>
          </div>

          <!-- 卡片底部信息 -->
          <div class="card-footer">
            <div class="footer-info">
              <span class="update-time">
                创建时间：{{ database.created_at || '—' }}
              </span>
              <div class="card-stats">
                <!-- <span class="stat-item">
                  {{ database.document_count || 0 }} 文档
                </span> -->
                <span class="stat-item">
                  {{ formatFileSize(database.total_size || 0) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="!loading" class="empty-state">
        <el-empty :description="searchText ? '未找到匹配的知识库' : '暂无知识库，创建第一个知识库开始使用吧'">
          <el-button v-if="!searchText" type="primary" @click="createDatabase" size="large">
            <el-icon>
              <Plus />
            </el-icon>
            创建知识库
          </el-button>
          <el-button v-else @click="clearSearch" size="large">
            清空搜索
          </el-button>
        </el-empty>
      </div>
    </div>

    <!-- 美化的分页组件 -->
    <div class="pagination-container">
      <div class="pagination-wrapper">
        <!-- 左侧统计信息 -->
        <div class="pagination-info">
          <div class="info-item">
            <span class="info-label">共</span>
            <span class="info-value">{{ pagination.total }}</span>
            <span class="info-label">个知识库</span>
          </div>
          <div class="info-divider"></div>
          <div class="info-item">
            <span class="info-label">第</span>
            <span class="info-value">{{ pagination.page }}</span>
            <span class="info-label">页，共</span>
            <span class="info-value">{{ pagination.pages }}</span>
            <span class="info-label">页</span>
          </div>
        </div>

        <!-- 中间分页控件 -->
        <div class="pagination-controls">
          <el-pagination v-model:current-page="pagination.page" :page-size="pagination.pageSize"
            :total="pagination.total" layout="prev, pager, next, jumper" @current-change="handleCurrentChange"
            class="custom-pagination" :hide-on-single-page="false" />
        </div>

        <!-- 右侧快速跳转 -->
        <div class="pagination-actions">
          <el-button :disabled="pagination.page <= 1" @click="jumpToPage(1)" size="small" class="jump-button">
            <el-icon>
              <DArrowLeft />
            </el-icon>
            首页
          </el-button>
          <el-button :disabled="pagination.page >= pagination.pages" @click="jumpToPage(pagination.pages)" size="small"
            class="jump-button">
            末页
            <el-icon>
              <DArrowRight />
            </el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="showLatestDocDialog"
      title="获取最新文档"
      width="760px"
      :close-on-click-modal="false"
    >
      <el-form label-position="top" class="latest-doc-form">
        <el-form-item label="文档来源站点">
          <el-input
            v-model="latestDocForm.url"
            class="latest-doc-url-input"
            :placeholder="DEFAULT_SHIP_RESEARCH_URL"
            readonly
          />
          <div class="latest-doc-hint">
            当前固定从中国船舶研究“当期目录”页面抓取文章。
          </div>
        </el-form-item>
        <el-form-item label="爬取数量">
          <el-input-number
            v-model="latestDocForm.count"
            :min="1"
            :max="10"
            :step="1"
            step-strictly
            class="latest-doc-count-input"
          />
          <div class="latest-doc-hint">
            可选范围 1-10，默认 3。
          </div>
        </el-form-item>
      </el-form>

      <div v-if="crawlErrorMessage" class="crawl-error-message">
        {{ crawlErrorMessage }}
      </div>

      <div v-if="crawledFiles.length > 0" class="crawl-result-section">
        <div class="result-title">爬取结果（{{ crawledFiles.length }}）</div>
        <div class="result-grid">
          <div v-for="(item, idx) in crawledFiles" :key="`${item.download_url}-${idx}`" class="result-card">
            <div class="result-select">
              <el-checkbox
                :model-value="isCrawledItemSelected(idx)"
                @change="(checked) => toggleCrawledSelection(idx, checked)"
              >
                选择上传
              </el-checkbox>
            </div>
            <div class="result-name" :title="item.name">{{ item.name || '未命名文档' }}</div>
            <div class="result-meta">
              <span v-if="item.doi">DOI：{{ item.doi }}</span>
              <span>日期：{{ item.date || '未知' }}</span>
              <span>大小：{{ item.size || '未知' }}</span>
            </div>
            <div class="result-actions">
              <el-button type="primary" plain size="small" @click="previewCrawledItem(item)">
                预览
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <el-empty v-else-if="hasCrawledOnce && !crawlLoading" description="未抓取到可展示的文档" :image-size="72" />

      <template #footer>
        <div class="latest-doc-footer">
          <el-button @click="showLatestDocDialog = false">取消</el-button>
          <el-button
            v-if="selectedCrawledFiles.length > 0"
            type="success"
            plain
            @click="openUploadTargetDialog"
          >
            上传知识库（{{ selectedCrawledFiles.length }}）
          </el-button>
          <el-button type="primary" :loading="crawlLoading" @click="startCrawl">开始爬取</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showUploadTargetDialog"
      title="选择上传目标知识库"
      width="560px"
      :close-on-click-modal="false"
    >
      <el-form label-position="top">
        <el-form-item label="目标知识库">
          <el-select
            v-model="selectedUploadKbId"
            placeholder="请选择知识库"
            filterable
            style="width: 100%"
            :loading="uploadKbOptionsLoading"
          >
            <el-option
              v-for="item in uploadKbOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
          <div class="latest-doc-hint">
            默认已选“最新研究库”，你也可以切换到其他知识库。
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="latest-doc-footer">
          <el-button @click="showUploadTargetDialog = false">取消</el-button>
          <el-button
            type="primary"
            :loading="uploadToKbLoading"
            @click="goToTargetKbUpload"
          >
            下一步
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search,
  Plus,
  Download,
  Folder,
  Refresh,
  MoreFilled,
  Edit,
  Delete,
  DArrowLeft,
  DArrowRight
} from '@element-plus/icons-vue'
import {
  getKnowledgeBaseList,
  getKnowledgeBaseAttributesForIds,
  updateKnowledgeBase,
  deleteKnowledgeBase,
  crawlLatestDocuments,
} from '@/api/knowledge'

const router = useRouter()
const route = useRoute()

// 响应式数据
const searchText = ref('')
const databases = ref([])
const loading = ref(false)
const searchMatchedIds = ref([])
const showLatestDocDialog = ref(false)
const latestDocForm = ref({
  source_type: 'ship-research',
  url: 'https://ship-research.com/article/current',
  count: 3,
})
const crawlLoading = ref(false)
const uploadToKbLoading = ref(false)
const crawledFiles = ref([])
const crawlErrorMessage = ref('')
const hasCrawledOnce = ref(false)
const showUploadTargetDialog = ref(false)
const uploadKbOptionsLoading = ref(false)
const uploadKbOptions = ref([])
const selectedUploadKbId = ref(null)
const selectedCrawledIndexes = ref([])
const DEFAULT_SHIP_RESEARCH_URL = 'https://ship-research.com/article/current'
const TARGET_KB_NAME = '最新研究库'
const LATEST_DOCS_UPLOAD_SEED_KEY = 'latest-docs-upload-seed'

const selectedCrawledFiles = computed(() => {
  if (!Array.isArray(crawledFiles.value) || crawledFiles.value.length === 0) {
    return []
  }

  return selectedCrawledIndexes.value
    .map((idx) => crawledFiles.value[idx])
    .filter((item) => !!item)
})

const isCrawledItemSelected = (index) => selectedCrawledIndexes.value.includes(index)

const toggleCrawledSelection = (index, checked) => {
  const next = new Set(selectedCrawledIndexes.value)
  if (checked) {
    next.add(index)
  } else {
    next.delete(index)
  }
  selectedCrawledIndexes.value = Array.from(next).sort((a, b) => a - b)
}

// 分页数据（前端分页，每页6条）
const pagination = ref({
  page: 1,
  pageSize: 6, // 固定每页6条
  total: 0,
  pages: 0
})

// 搜索处理：有搜索时获取所有数据，无搜索时按分页获取
const handleSearch = () => {
  // 立即重置到第一页，并重新获取数据
  pagination.value.page = 1
  fetchKnowledgeBases()
}

// 获取知识库列表（按ID排序后分页获取属性）
const fetchKnowledgeBases = async () => {
  try {
    loading.value = true

    // 1) 获取所有知识库ID
    const res = await getKnowledgeBaseList()
    const allIds = res?.data?.ids || []

    // 2) 按ID降序排序（ID越大越新）
    const sortedIds = [...allIds].sort((a, b) => b - a)

    // 3) 根据搜索与分页决定本次请求的ID列表
    const isSearching = !!(searchText.value && searchText.value.trim())
    const start = (pagination.value.page - 1) * pagination.value.pageSize
    const end = start + pagination.value.pageSize

    if (isSearching) {
      const keyword = searchText.value.trim().toLowerCase()

      // 先获取用于匹配的字段
      const matchAttrs = ['name', 'description']
      const matchRes = sortedIds.length
        ? await getKnowledgeBaseAttributesForIds(sortedIds, matchAttrs)
        : { data: { items: [] } }
      const matchData = matchRes?.data || null
      const matchItems = Array.isArray(matchData?.items)
        ? matchData.items
        : matchData && typeof matchData === 'object'
          ? [matchData]
          : []

      const matchedIds = []
      matchItems.forEach((item, idx) => {
        const name = (item?.name || '').toLowerCase()
        const description = (item?.description || '').toLowerCase()
        if (name.includes(keyword) || description.includes(keyword)) {
          matchedIds.push(sortedIds[idx])
        }
      })

      searchMatchedIds.value = matchedIds

      pagination.value.total = matchedIds.length
      pagination.value.pages = Math.max(1, Math.ceil(pagination.value.total / pagination.value.pageSize))
      if (pagination.value.page > pagination.value.pages) {
        pagination.value.page = pagination.value.pages
      }

      const pageIds = matchedIds.slice(start, end)
      if (!pageIds.length) {
        databases.value = []
        return
      }

      const attrs = ['name', 'description', 'total_size', 'created_at']
      const resAttrs = await getKnowledgeBaseAttributesForIds(pageIds, attrs)
      const data = resAttrs?.data || null
      const items = Array.isArray(data?.items)
        ? data.items
        : data && typeof data === 'object'
          ? [data]
          : []

      databases.value = items.map((item, idx) => ({
        id: pageIds[idx],
        ...item
      }))
      return
    }

    searchMatchedIds.value = []

    const pageIds = sortedIds.slice(start, end)
    pagination.value.total = sortedIds.length
    pagination.value.pages = Math.max(1, Math.ceil(pagination.value.total / pagination.value.pageSize))
    if (pagination.value.page > pagination.value.pages) {
      pagination.value.page = pagination.value.pages
    }

    if (!pageIds.length) {
      databases.value = []
      return
    }

    // 4) 批量获取当前页的属性
    const attrs = ['name', 'description', 'total_size', 'created_at']
    const resAttrs = await getKnowledgeBaseAttributesForIds(pageIds, attrs)
    const data = resAttrs?.data || null
    const items = Array.isArray(data?.items)
      ? data.items
      : data && typeof data === 'object'
        ? [data]
        : []

    // 5) 绑定ID
    databases.value = items.map((item, idx) => ({
      id: pageIds[idx],
      ...item
    }))

  } catch (error) {
    console.error('❌ 获取知识库列表失败:', error)
    databases.value = []
    pagination.value.total = 0
    ElMessage.error('获取知识库列表失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 搜索与分页在 fetchKnowledgeBases 中完成
const filteredDatabases = computed(() => databases.value)
const pagedDatabases = computed(() => databases.value)

// 状态相关
const getStatusType = (status) => {
  const statusMap = {
    'active': 'success',
    'processing': 'warning',
    'error': 'danger',
    'pending': 'info',
    'completed': 'success'
  }
  return statusMap[status] || 'success'
}

const getStatusText = (status) => {
  const statusMap = {
    'active': '正常',
    'processing': '处理中',
    'error': '错误',
    'pending': '待处理',
    'completed': '已完成'
  }
  return statusMap[status] || '正常'
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 页面操作
const createDatabase = () => {
  router.push('/knowledge_base/create')
}

const openLatestDocDialog = () => {
  latestDocForm.value.source_type = 'ship-research'
  latestDocForm.value.url = DEFAULT_SHIP_RESEARCH_URL
  latestDocForm.value.count = 3
  crawledFiles.value = []
  selectedCrawledIndexes.value = []
  crawlErrorMessage.value = ''
  hasCrawledOnce.value = false
  showLatestDocDialog.value = true
}

const startCrawl = async () => {
  latestDocForm.value.source_type = 'ship-research'
  latestDocForm.value.url = DEFAULT_SHIP_RESEARCH_URL
  const parsedCount = Number(latestDocForm.value.count)
  const safeCount = Number.isFinite(parsedCount)
    ? Math.min(10, Math.max(1, Math.floor(parsedCount)))
    : 3
  latestDocForm.value.count = safeCount

  try {
    crawlLoading.value = true
    crawlErrorMessage.value = ''

    const response = await crawlLatestDocuments({
      url: latestDocForm.value.url,
      source_type: latestDocForm.value.source_type,
      count: safeCount,
    })

    const items = response?.data?.items || []
    crawledFiles.value = Array.isArray(items) ? items : []
    selectedCrawledIndexes.value = []
    hasCrawledOnce.value = true

    ElMessage.success(`爬取完成，共 ${crawledFiles.value.length} 条`)
  } catch (error) {
    console.error('爬取文档失败:', error)
    crawledFiles.value = []
    hasCrawledOnce.value = true
    crawlErrorMessage.value = '抓取失败，请稍后重试'
    ElMessage.error('爬取失败')
  } finally {
    crawlLoading.value = false
  }
}

const previewCrawledItem = (item) => {
  const articleId = (item?.article_id || '').trim()
  const previewUrl = (item?.preview_url || '').trim() || (articleId
    ? `https://ship-research.com/cn/article/pdf/preview/${articleId}.pdf`
    : '')

  if (!previewUrl) {
    ElMessage.warning('该文档没有可用预览地址')
    return
  }

  window.open(previewUrl, '_blank', 'noopener,noreferrer')
}

const buildPreviewUrl = (item) => {
  const articleId = String(item?.article_id || '').trim()
  const fromItem = String(item?.preview_url || '').trim()
  if (fromItem) {
    return fromItem
  }
  if (!articleId) {
    return ''
  }
  return `https://ship-research.com/cn/article/pdf/preview/${articleId}.pdf`
}

const resolveLatestResearchKbId = async () => {
  const normalized = await loadUploadKbOptions()

  const exact = normalized.find((kb) => kb.name === TARGET_KB_NAME)
  if (exact?.id) {
    return exact.id
  }

  const fuzzy = normalized.find((kb) => kb.name.includes('最新研究'))
  if (fuzzy?.id) {
    return fuzzy.id
  }

  throw new Error(`未找到目标知识库：${TARGET_KB_NAME}`)
}

const loadUploadKbOptions = async () => {
  uploadKbOptionsLoading.value = true
  try {
    const listRes = await getKnowledgeBaseList()
    const ids = listRes?.data?.ids || []
    if (!ids.length) {
      uploadKbOptions.value = []
      return []
    }

    const attrsRes = await getKnowledgeBaseAttributesForIds(ids, ['name'])
    const data = attrsRes?.data || null
    const items = Array.isArray(data?.items)
      ? data.items
      : data && typeof data === 'object'
        ? [data]
        : []

    const normalized = items.map((item, idx) => ({
      id: ids[idx],
      name: String(item?.name || '').trim() || `知识库 ${ids[idx]}`,
    }))

    uploadKbOptions.value = normalized
    return normalized
  } finally {
    uploadKbOptionsLoading.value = false
  }
}

const openUploadTargetDialog = async () => {
  if (!selectedCrawledFiles.value.length) {
    ElMessage.warning('请先勾选要上传的文章')
    return
  }

  try {
    const options = await loadUploadKbOptions()
    if (!options.length) {
      ElMessage.warning('当前没有可用知识库')
      return
    }

    const latestKbId = await resolveLatestResearchKbId().catch(() => null)
    selectedUploadKbId.value = latestKbId || options[0].id
    showUploadTargetDialog.value = true
  } catch (error) {
    console.error('加载知识库列表失败:', error)
    ElMessage.error(`加载知识库失败：${error?.message || '未知错误'}`)
  }
}

const goToTargetKbUpload = async () => {
  const targetKbId = Number(selectedUploadKbId.value)
  if (!targetKbId) {
    ElMessage.warning('请先选择目标知识库')
    return
  }

  if (!selectedCrawledFiles.value.length) {
    ElMessage.warning('请先勾选要上传的文章')
    return
  }

  try {
    uploadToKbLoading.value = true
    const seed = {
      targetKbId,
      source: 'latest-docs',
      createdAt: Date.now(),
      items: selectedCrawledFiles.value.map((item) => ({
        name: item?.name || '',
        article_id: item?.article_id || '',
        preview_url: buildPreviewUrl(item),
      })).filter((item) => item.preview_url),
    }

    if (!seed.items.length) {
      ElMessage.warning('没有可用的预览文件可上传')
      return
    }

    sessionStorage.setItem(LATEST_DOCS_UPLOAD_SEED_KEY, JSON.stringify(seed))

    showUploadTargetDialog.value = false
    showLatestDocDialog.value = false
    router.push({
      path: `/knowledge_base/${targetKbId}/files`,
      query: {
        openUpload: '1',
        prefillLatestDocs: '1',
      },
    })
  } catch (error) {
    console.error('准备上传跳转失败:', error)
    ElMessage.error(`准备上传失败：${error?.message || '未知错误'}`)
  } finally {
    uploadToKbLoading.value = false
  }
}

const openDatabase = (database) => {
  router.push(`/knowledge_base/${database.id}/files`)
}

const editDatabase = async (database) => {
  try {
    // 创建输入对话框获取新的名称
    const { value: newName } = await ElMessageBox.prompt(
      '请输入新的知识库名称',
      '编辑知识库名称',
      {
        confirmButtonText: '下一步',
        cancelButtonText: '取消',
        inputValue: database.name,
        inputValidator: (value) => {
          if (!value || !value.trim()) {
            return '知识库名称不能为空'
          }
          return true
        }
      }
    )

    // 创建输入对话框获取新的描述
    const { value: newDescription } = await ElMessageBox.prompt(
      '请输入新的知识库描述（可选）',
      '编辑知识库描述',
      {
        confirmButtonText: '保存',
        cancelButtonText: '取消',
        inputValue: database.description || '',
        inputType: 'textarea'
      }
    )

    const updateData = {
      name: newName.trim(),
      description: (newDescription || '').trim()
    }

    console.log('开始更新知识库(分字段):', database.id, '数据:', updateData)

    // 单次调用内部按字段拆分为多个 attr 请求
    const response = await updateKnowledgeBase(database.id, updateData)

    if (response && response.success) {
      ElMessage.success('知识库更新成功')
      await fetchKnowledgeBases()
    } else {
      throw new Error(response?.message || '更新失败')
    }

  } catch (error) {
    if (error !== 'cancel') {
      console.error('编辑知识库失败:', error)
      ElMessage.error('编辑知识库失败: ' + (error.message || '未知错误'))
    }
  }
}



const deleteDatabase = async (database) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除知识库 "${database.name}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )

    console.log('开始删除知识库:', database.id)
    await deleteKnowledgeBase(database.id)
    ElMessage.success('删除成功')
    await fetchKnowledgeBases()

  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败: ' + (error.message || '未知错误'))
    }
  }
}

const refreshData = () => {
  console.log('手动刷新数据')
  fetchKnowledgeBases()
}


const clearSearch = () => {
  searchText.value = ''
}


const handleSizeChange = (newSize) => {
  console.log('分页大小变更(忽略，固定为6):', newSize)
}

const handleCurrentChange = (newPage) => {
  console.log('页码变更:', newPage)
  pagination.value.page = newPage
  fetchKnowledgeBases()
}

// 快速跳转页面
const jumpToPage = (page) => {
  if (page >= 1 && page <= pagination.value.pages && page !== pagination.value.page) {
    pagination.value.page = page
    fetchKnowledgeBases()
  }
}

// 已移除顶部的“知识库概览 / 我的知识库”按钮，相关切换逻辑不再需要

// 监听过滤结果与每页条数变化，实时更新总数和总页数，并保证页码有效
watch([() => pagination.value.pageSize, searchText], () => {
  const isSearching = !!(searchText.value && searchText.value.trim())
  if (!isSearching) return
  pagination.value.total = searchMatchedIds.value.length
  pagination.value.pages = Math.max(1, Math.ceil(pagination.value.total / pagination.value.pageSize))
  if (pagination.value.page > pagination.value.pages) {
    pagination.value.page = pagination.value.pages
  }
})

// 搜索变化时回到第一页
watch(searchText, () => {
  pagination.value.page = 1
})

// 页面初始化
onMounted(() => {
  console.log('数据库管理页面已加载')
  fetchKnowledgeBases()
})
</script>

<style scoped>
.database-management {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.header-bar {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(229, 231, 235, 0.5);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
}

.header-left {
  display: flex;
  align-items: center;
}

.page-title {
  margin: 0;
  font-weight: 600;
  color: #1f2937;
}

.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 1rem;
  align-items: center;
}

/* 已移除顶部标签按钮的样式 */

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.search-input {
  width: 300px;
}

.create-btn,
.refresh-btn,
.latest-doc-btn {
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-weight: 500;
}

.latest-doc-btn {
  color: #334155;
  border: 1px solid rgba(148, 163, 184, 0.5);
  background: rgba(255, 255, 255, 0.85);
}

.latest-doc-btn:hover {
  color: #0f172a;
  border-color: rgba(100, 116, 139, 0.8);
  background: #ffffff;
}

.latest-doc-form {
  margin-top: 8px;
}

.latest-doc-url-input {
  width: 100%;
}

.latest-doc-source-select {
  width: 190px;
}

.latest-doc-hint {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: #64748b;
}

.crawl-error-message {
  margin: 8px 0;
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #991b1b;
  font-size: 13px;
}

.crawl-result-section {
  margin-top: 8px;
}

.result-title {
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  max-height: 320px;
  overflow-y: auto;
}

.result-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px;
  background: #ffffff;
}

.result-select {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 6px;
}

.result-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #4b5563;
}

.result-actions {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}

.full-width-select {
  width: 100%;
}

.latest-doc-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.create-text {
  margin-left: 0.5rem;
}

.loading-container {
  padding: 2rem;
  flex: 1;
}

.content-area {
  flex: 1;
  padding: 2rem;
  /* 不在卡片区域内部滚动；使用分页控制显示内容 */
  overflow-y: visible;
}

.database-grid {
  display: grid;
  /* 固定三列布局：每行 3 个卡片，配合 pagination.pageSize=6 可展示两行 */
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
}

.database-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  padding: 1.75rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  cursor: pointer;
  border: 1px solid rgba(229, 231, 235, 0.5);
}

.database-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.database-icon {
  width: 3.5rem;
  height: 3.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.75rem;
}

.card-menu {
  opacity: 0;
  transition: opacity 0.2s;
}

.database-card:hover .card-menu {
  opacity: 1;
}

.card-content {
  margin-bottom: 1rem;
}

.database-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 0.5rem 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.database-description {
  color: #6b7280;
  font-size: 0.875rem;
  margin: 0 0 1rem 0;
  line-height: 1.4;
  display: -webkit-box;
  line-clamp: 2;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.status-tags {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.card-footer {
  border-top: 1px solid rgba(229, 231, 235, 0.5);
  padding-top: 1rem;
}

.footer-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.update-time {
  font-size: 0.75rem;
  color: #9ca3af;
}

.card-stats {
  display: flex;
  gap: 1rem;
}

.stat-item {
  font-size: 0.75rem;
  color: #6b7280;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 400px;
}

/* 美化的分页样式 */
.pagination-container {
  padding: 1.5rem 2rem;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(229, 231, 235, 0.5);
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
}

.pagination-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1600px;
  margin: 0 auto;
  gap: 2rem;
}

.pagination-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  color: #6b7280;
  font-size: 0.875rem;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.info-label {
  color: #9ca3af;
}

.info-value {
  font-weight: 600;
  color: #374151;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.info-divider {
  width: 1px;
  height: 1rem;
  background: linear-gradient(to bottom, transparent, #d1d5db, transparent);
}

.pagination-controls {
  flex: 1;
  display: flex;
  justify-content: center;
}

.pagination-actions {
  display: flex;
  gap: 0.5rem;
}

.jump-button {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  transition: all 0.2s;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(229, 231, 235, 0.8);
  color: #6b7280;
}

.jump-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.jump-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 自定义分页组件样式 */
.custom-pagination :deep(.el-pagination) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.custom-pagination :deep(.el-pagination__total) {
  color: #6b7280;
  font-size: 0.875rem;
  margin-right: 1rem;
}

.custom-pagination :deep(.el-pagination__sizes) {
  margin-right: 1rem;
}

.custom-pagination :deep(.el-select .el-select__wrapper) {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(229, 231, 235, 0.8);
  border-radius: 0.5rem;
  box-shadow: none;
  transition: all 0.2s;
}

.custom-pagination :deep(.el-select .el-select__wrapper:hover) {
  border-color: #667eea;
}

.custom-pagination :deep(.el-pager li) {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(229, 231, 235, 0.8);
  border-radius: 0.5rem;
  margin: 0 0.25rem;
  transition: all 0.2s;
  color: #6b7280;
}

.custom-pagination :deep(.el-pager li:hover) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
  transform: translateY(-1px);
}

.custom-pagination :deep(.el-pager li.is-active) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.custom-pagination :deep(.btn-prev),
.custom-pagination :deep(.btn-next) {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(229, 231, 235, 0.8);
  border-radius: 0.5rem;
  color: #6b7280;
  transition: all 0.2s;
}

.custom-pagination :deep(.btn-prev:hover),
.custom-pagination :deep(.btn-next:hover) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
  transform: translateY(-1px);
}

.custom-pagination :deep(.btn-prev:disabled),
.custom-pagination :deep(.btn-next:disabled) {
  opacity: 0.5;
  cursor: not-allowed;
}

.custom-pagination :deep(.el-pagination__jump) {
  color: #6b7280;
  font-size: 0.875rem;
  margin-left: 1rem;
}

.custom-pagination :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(229, 231, 235, 0.8);
  border-radius: 0.5rem;
  box-shadow: none;
  transition: all 0.2s;
}

.custom-pagination :deep(.el-input__wrapper:hover) {
  border-color: #667eea;
}

.custom-pagination :deep(.el-input__wrapper.is-focus) {
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .pagination-wrapper {
    flex-direction: column;
    gap: 1rem;
  }

  .pagination-info {
    order: 3;
  }

  .pagination-controls {
    order: 1;
  }

  .pagination-actions {
    order: 2;
  }
}

@media (max-width: 768px) {
  .header-bar {
    flex-direction: column;
    gap: 1rem;
    padding: 1rem;
  }

  .header-right {
    width: 100%;
    justify-content: space-between;
  }

  .search-input {
    width: 200px;
  }

  .database-grid {
    grid-template-columns: 1fr;
  }

  .content-area {
    padding: 1rem;
  }

  .pagination-container {
    padding: 1rem;
  }

  .pagination-wrapper {
    gap: 0.75rem;
  }

  .pagination-info {
    flex-direction: column;
    text-align: center;
    gap: 0.5rem;
  }

  .pagination-actions {
    flex-direction: column;
    width: 100%;
  }

  .jump-button {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .pagination-info .info-item {
    font-size: 0.75rem;
  }

  .custom-pagination :deep(.el-pagination) {
    justify-content: center;
    flex-wrap: wrap;
  }
}
</style>
