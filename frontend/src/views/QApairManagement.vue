<template>
  <div class="qapair-management">
    <!-- 顶部标题栏，与知识库管理风格一致 -->
    <div class="header-bar">
      <div class="header-left">
        <h2 class="page-title">微调语料库管理</h2>
      </div>
      <div class="header-right">
        <el-button @click="fetchList">刷新</el-button>
      </div>
      <div class="header-center">
        <el-input
          v-model="searchText"
          placeholder="搜索问答对"
          class="search-input"
          clearable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="goToUpload" class="upload-btn">
          上传微调语料
        </el-button>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="content">
      <div v-if="loading" class="loading">
        <el-skeleton :rows="4" animated />
      </div>

      <div v-else class="grid">
        <div
          v-for="item in pagedItems"
          :key="item.id"
          class="card"
        >
          <!-- 卡片头部：左侧图标 + 右侧查看链接（与知识库卡片风格一致） -->
          <div class="card-header">
            <div class="qa-icon">
              <el-icon><Document /></el-icon>
            </div>
            <div class="card-actions">
              <el-button link size="small" class="view-link" @click.stop="openDetail(item.id)">查看</el-button>
            </div>
          </div>
          <!-- 主体内容：显示问题摘要 -->
          <div class="card-content">
            <div class="id">#{{ item.id }}</div>
            <div class="title" :title="item.question">{{ truncate(item.question) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 美化的分页组件（与知识库一致，空列表时也显示） -->
    <div class="pagination-container">
      <div class="pagination-wrapper">
        <!-- 左侧统计信息 -->
        <div class="pagination-info">
          <div class="info-item">
            <span class="info-label">共</span>
            <span class="info-value">{{ pagination.total }}</span>
            <span class="info-label">个问答对</span>
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
          <el-pagination
            v-model:current-page="pagination.page"
            :page-size="pagination.pageSize"
            :total="pagination.total"
            layout="prev, pager, next, jumper"
            @current-change="handleCurrentChange"
            class="custom-pagination"
            :hide-on-single-page="false"
          />
        </div>

        <!-- 右侧快速跳转（可选） -->
        <div class="pagination-actions">
          <el-button :disabled="pagination.page <= 1" @click="jumpToPage(1)" size="small" class="jump-button">
            首页
          </el-button>
          <el-button :disabled="pagination.page >= pagination.pages" @click="jumpToPage(pagination.pages)" size="small" class="jump-button">
            末页
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Document } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { listQApairs } from '@/api/qapair'

const router = useRouter()

const items = ref([]) // {id, question, answer}
const loading = ref(false)
const searchText = ref('')
// 分页数据（每页9条，3列x3行，与知识库风格一致）
const pagination = ref({
  page: 1,
  pageSize: 9,
  total: 0,
  pages: 0
})

const filteredItems = computed(() => {
  const kw = (searchText.value || '').toLowerCase().trim()
  if (!kw) return items.value
  return items.value.filter(n => (n.question || '').toLowerCase().includes(kw) || String(n.id).includes(kw))
})

// 当前页切片
const pagedItems = computed(() => {
  const start = (pagination.value.page - 1) * pagination.value.pageSize
  const end = start + pagination.value.pageSize
  return filteredItems.value.slice(start, end)
})

const fetchList = async () => {
  loading.value = true
  try {
    const res = await listQApairs()
    const all = (res.data.items || []).slice().sort((a,b) => a.id - b.id)
    items.value = all
  } catch (e) {
    console.error(e)
    ElMessage.error('获取列表失败')
  } finally {
    // 更新分页统计
    pagination.value.total = filteredItems.value.length
    pagination.value.pages = Math.max(1, Math.ceil(pagination.value.total / pagination.value.pageSize))
    if (pagination.value.page > pagination.value.pages) pagination.value.page = pagination.value.pages

    loading.value = false
  }
}

const openDetail = (id) => {
  router.push(`/QApair/${id}`)
}

const goToUpload = () => {
  router.push('/QApair/upload')
}

onMounted(() => {
  fetchList()
})

// 监听搜索变化，回到第一页
watch(searchText, () => {
  pagination.value.page = 1
})

// 监听过滤结果变化，更新分页统计
watch(filteredItems, () => {
  pagination.value.total = filteredItems.value.length
  pagination.value.pages = Math.max(1, Math.ceil(pagination.value.total / pagination.value.pageSize))
  if (pagination.value.page > pagination.value.pages) pagination.value.page = pagination.value.pages
})

const handleCurrentChange = (newPage) => {
  pagination.value.page = newPage
}

// 快速跳转
const jumpToPage = (page) => {
  if (page >= 1 && page <= pagination.value.pages && page !== pagination.value.page) {
    pagination.value.page = page
  }
}

const truncate = (text, maxLen = 60) => {
  if (!text) return ''
  const t = String(text)
  return t.length > maxLen ? t.slice(0, maxLen) + '…' : t
}

// 删除入口已移至详情页；列表不再提供删除按钮
</script>

<style scoped>
.qapair-management {
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
.header-left { display: flex; align-items: center; }
.page-title { margin: 0; font-weight: 600; color: #1f2937; }
.header-right { display: flex; align-items: center; gap: 1rem; }
.header-center { position: absolute; left: 50%; transform: translateX(-50%); display: flex; align-items: center; gap: 1rem; }
.search-input { width: 300px; }
.upload-btn { padding: 0.75rem 1.5rem; border-radius: 0.5rem; font-weight: 500; }

.content { flex: 1; padding: 2rem; overflow-y: auto; }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.25rem; }
.card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  padding: 1.75rem; /* 与知识库卡片保持一致 */
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  cursor: default;
  border: 1px solid rgba(229, 231, 235, 0.5);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  position: relative;
}
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.qa-icon {
  width: 3.5rem;
  height: 3.5rem;
  background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%); /* 绿色-青色渐变，与知识库略有区分 */
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.5rem;
}
.card-actions { display: flex; align-items: center; }
.card:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(0,0,0,0.15); }
.card-content { margin-bottom: 1rem; }
.card .id { font-size: 12px; color: #6b7280; margin-bottom: 0.25rem; }
.card .title { font-size: 1.125rem; font-weight:600; color:#1f2937; overflow:hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 文字链接样式的“查看” */
.view-link {
  padding: 0;
  color: #3b82f6;
  font-weight: 500;
}
.view-link:hover {
  text-decoration: underline;
}

.pagination-container {
  padding: 1.5rem 2rem;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(229, 231, 235, 0.5);
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
}

.pagination-wrapper { display: flex; justify-content: space-between; align-items: center; max-width: 1200px; margin: 0 auto; gap: 2rem; }
.pagination-info { display: flex; align-items: center; gap: 1rem; color: #6b7280; font-size: 0.875rem; }
.info-item { display: flex; align-items: center; gap: 0.25rem; }
.info-label { color: #9ca3af; }
.info-value { font-weight: 600; color: #374151; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); background-clip: text; -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.info-divider { width: 1px; height: 1rem; background: linear-gradient(to bottom, transparent, #d1d5db, transparent); }
.pagination-controls { flex: 1; display: flex; justify-content: center; }
.pagination-actions { display: flex; gap: 0.5rem; }
.jump-button { padding: 0.5rem 1rem; border-radius: 0.5rem; font-size: 0.875rem; transition: all 0.2s; background: rgba(255, 255, 255, 0.8); border: 1px solid rgba(229, 231, 235, 0.8); color: #6b7280; }
.jump-button:hover:not(:disabled) { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-color: transparent; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3); }
.jump-button:disabled { opacity: 0.5; cursor: not-allowed; }

/* 自定义分页组件样式（与知识库一致） */
.custom-pagination :deep(.el-pagination) { display: flex; align-items: center; gap: 0.5rem; }
.custom-pagination :deep(.el-pager li) { background: rgba(255, 255, 255, 0.8); border: 1px solid rgba(229, 231, 235, 0.8); border-radius: 0.5rem; margin: 0 0.25rem; transition: all 0.2s; color: #6b7280; }
.custom-pagination :deep(.el-pager li:hover) { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-color: transparent; transform: translateY(-1px); }
.custom-pagination :deep(.el-pager li.is-active) { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-color: transparent; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3); }
.custom-pagination :deep(.btn-prev),
.custom-pagination :deep(.btn-next) { background: rgba(255, 255, 255, 0.8); border: 1px solid rgba(229, 231, 235, 0.8); border-radius: 0.5rem; color: #6b7280; transition: all 0.2s; }
.custom-pagination :deep(.btn-prev:hover),
.custom-pagination :deep(.btn-next:hover) { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-color: transparent; transform: translateY(-1px); }
.custom-pagination :deep(.btn-prev:disabled),
.custom-pagination :deep(.btn-next:disabled) { opacity: 0.5; cursor: not-allowed; }

@media (max-width: 768px) {
  .pagination-container { padding: 1rem; }
  .pagination-wrapper { flex-direction: column; gap: 0.75rem; }
  .pagination-info { flex-direction: column; text-align: center; gap: 0.5rem; }
  .pagination-actions { flex-direction: column; width: 100%; }
  .jump-button { width: 100%; }
}
</style>
