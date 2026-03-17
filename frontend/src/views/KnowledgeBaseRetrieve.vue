<template>
  <div class="knowledge-retrieve">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <el-button type="text" @click="goBack" class="back-button">
          <el-icon><ArrowLeft /></el-icon>
          返回知识库
        </el-button>
        <div class="title-section">
          <h2>知识库检索</h2>
          <p class="subtitle" v-if="loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            正在加载知识库信息...
          </p>
          <p class="subtitle" v-else>{{ kbName }}</p>
          <p class="description" v-if="kbDescription && !loading">{{ kbDescription }}</p>
        </div>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="retrieve-container">
      <!-- 左侧配置面板 -->
      <div class="config-panel">
        <el-card class="config-card">
          <template #header>
            <div class="card-header">
              <el-icon><Setting /></el-icon>
              <span>检索配置</span>
            </div>
          </template>

          <!-- 查询输入 -->
          <div class="config-item">
            <label class="config-label">查询内容：</label>
            <el-input
              v-model="retrieveForm.query"
              type="textarea"
              :rows="4"
              placeholder="请输入要检索的内容..."
              class="query-input"
              @keydown.ctrl.enter="performRetrieve"
            />
          </div>

          <!-- Top K - 滑块 + 输入框 -->
          <div class="config-item">
            <label class="config-label">返回数量 (Top K)：</label>
            <div class="slider-input-container">
              <el-slider
                v-model="retrieveForm.top_k"
                :min="1"
                :max="maxTopK"
                :step="1"
                show-stops
                class="config-slider"
                @input="validateTopK"
              />
              <el-input-number
                v-model="retrieveForm.top_k"
                :min="1"
                :max="maxTopK"
                :step="1"
                size="small"
                class="config-input-number"
                @change="validateTopK"
              />
            </div>
          </div>

          <!-- 相似度阈值 - 滑块 + 输入框 -->
          <div class="config-item">
            <label class="config-label">相似度阈值：</label>
            <div class="slider-input-container">
              <el-slider
                v-model="retrieveForm.score_threshold"
                :min="0.01"
                :max="1"
                :step="0.01"
                show-stops
                class="config-slider"
                @input="validateScoreThreshold"
              />
              <el-input-number
                v-model="retrieveForm.score_threshold"
                :min="0.01"
                :max="1"
                :step="0.01"
                :precision="2"
                size="small"
                class="config-input-number"
                @change="validateScoreThreshold"
              />
            </div>
          </div>

          <!-- 检索按钮 -->
          <el-button
            type="primary"
            :loading="retrieving"
            @click="performRetrieve"
            class="retrieve-button"
            :disabled="!retrieveForm.query.trim()"
          >
            <el-icon v-if="!retrieving"><Search /></el-icon>
            {{ retrieving ? '检索中...' : '开始检索' }}
          </el-button>

          <!-- 统计信息 -->
          <div v-if="hasSearched" class="retrieve-stats">
            <el-divider />
            <div class="stats-info">
              <p>
                <el-icon><InfoFilled /></el-icon>
                检索结果：{{ retrieveResults.length }} 个文档片段
              </p>
              <p>
                <el-icon><InfoFilled /></el-icon>
                用时：{{ retrieveTime }} 秒
              </p>
              <el-button
                v-if="retrieveResults.length > 0"
                type="text"
                size="small"
                @click="exportResults"
              >
                <el-icon><Download /></el-icon>
                导出结果
              </el-button>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 右侧结果面板 -->
      <div class="results-panel">
        <!-- 空状态 -->
        <div v-if="!hasSearched" class="empty-state">
          <el-empty
            :image-size="100"
            description="请在左侧输入查询内容并点击检索"
          />
        </div>

        <!-- 检索中状态 -->
        <div v-else-if="retrieving" class="loading-state">
          <div class="loading-content">
            <el-icon class="is-loading loading-icon"><Loading /></el-icon>
            <p>正在检索相关文档...</p>
          </div>
        </div>

        <!-- 无结果状态 -->
        <div v-else-if="hasSearched && retrieveResults.length === 0" class="no-results">
          <el-empty
            :image-size="100"
            description="未找到相关内容"
          >
            <template #description>
              <div class="no-results-tips">
                <p>未找到匹配的内容，请尝试：</p>
                <ul>
                  <li>调整查询关键词</li>
                  <li>降低相似度阈值</li>
                  <li>增加返回数量</li>
                </ul>
              </div>
            </template>
          </el-empty>
        </div>

        <!-- 结果列表 -->
        <div v-else class="results-list">
          <el-card
            v-for="(result, index) in retrieveResults"
            :key="`${result.chunk_id}-${index}`"
            class="result-card"
            shadow="hover"
          >
            <!-- 结果头部 -->
            <template #header>
              <div class="result-header">
                <div class="result-meta">
                  <el-tag :type="getScoreType(result.reranked_score)" class="score-tag">
                    重排分: {{ (Number.isFinite(result.reranked_score) ? (result.reranked_score * 100).toFixed(1) : '--') }}%
                  </el-tag>
                  <el-tag type="info" class="score-tag subtle">
                    检索分: {{ (Number.isFinite(result.retrieved_score) ? (result.retrieved_score * 100).toFixed(1) : '--') }}%
                  </el-tag>
                  <span class="result-index">#{{ index + 1 }}</span>
                </div>
                <div class="file-info">
                  <el-icon><Document /></el-icon>
                  <span>
                    {{ result.file_name || '未知文件' }}
                    <template v-if="result.file_type"> ({{ result.file_type }})</template>
                  </span>
                </div>
              </div>
            </template>

            <!-- 结果内容 -->
            <div class="chunk-content">
              <div class="chunk-text">{{ result.chunk_text }}</div>

              <!-- 元数据 -->
              <div class="metadata-section">
                <el-divider content-position="left">元数据</el-divider>
                <div class="metadata-grid">
                  <div class="meta-item">
                    <span class="meta-label">文本块ID:</span>
                    <span class="meta-value">{{ result.chunk_id }}</span>
                  </div>
                  <div class="meta-item">
                    <span class="meta-label">文件ID:</span>
                    <span class="meta-value">{{ result.file_id }}</span>
                  </div>
                  <div class="meta-item">
                    <span class="meta-label">块索引:</span>
                    <span class="meta-value">{{ result.chunk_index }}</span>
                  </div>
                  <div class="meta-item">
                    <span class="meta-label">起始-结束:</span>
                    <span class="meta-value">{{ result.start_position }} - {{ result.end_position }}</span>
                  </div>
                  <div class="meta-item">
                    <span class="meta-label">创建时间:</span>
                    <span class="meta-value">{{ result.created_at || '—' }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 操作按钮 -->
            <template #footer>
              <div class="result-actions">
                <el-button
                  type="text"
                  size="small"
                  @click="copyChunkText(result.chunk_text)"
                >
                  <el-icon><CopyDocument /></el-icon>
                  复制文本
                </el-button>
                <el-button
                  type="text"
                  size="small"
                  @click="viewFileDetail(result.file_id)"
                >
                  <el-icon><View /></el-icon>
                  查看文件
                </el-button>
              </div>
            </template>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, Setting, Search, InfoFilled, Loading,
  Download, Document, CopyDocument, View
} from '@element-plus/icons-vue'
import { retrieveChunks, getKnowledgeBaseDetail, getKnowledgeBaseAttributes, getChunkAttributesForIds, getFileAttributesForIds } from '@/api/knowledge'

const route = useRoute()
const router = useRouter()

// 页面参数
const kbId = ref(route.params.kbId)
const kbName = ref('知识库') // 初始值
const kbDescription = ref('') // 添加描述字段

// 检索表单（嵌入模型由后端配置管理）
const retrieveForm = reactive({
  query: '',
  top_k: 10,
  score_threshold: 0.5
})

// 允许的 Top K 上限（根据知识库实际文本块数量动态设置）
const maxTopK = ref(50)
const totalChunks = ref(0)

// 状态管理
const retrieving = ref(false)
const hasSearched = ref(false)
const retrieveResults = ref([])
const retrieveTime = ref(null)
const loading = ref(false) // 添加页面加载状态

// 验证 Top K 值
const validateTopK = (value) => {
  const upper = maxTopK.value || 1
  if (value < 1) {
    retrieveForm.top_k = 1
    ElMessage.warning('返回数量不能小于1')
  } else if (value > upper) {
    retrieveForm.top_k = upper
    ElMessage.warning(`返回数量不能大于当前知识库的文本块总数（${upper}）`)
  }
}

// 验证相似度阈值
const validateScoreThreshold = (value) => {
  if (value < 0.01) {
    retrieveForm.score_threshold = 0.01
    ElMessage.warning('相似度阈值不能小于0.01')
  } else if (value > 1) {
    retrieveForm.score_threshold = 1
    ElMessage.warning('相似度阈值不能大于1')
  }
}

// 加载知识库详情
const loadKnowledgeBaseDetail = async () => {
  console.log('开始加载知识库详情，kbId:', kbId.value)
  const response = await getKnowledgeBaseDetail(kbId.value)
  console.log('知识库详情响应:', response)

  if (response.success && response.data) {
    const data = response.data
    kbName.value = data.name || '知识库'
    kbDescription.value = data.description || ''
    console.log('知识库名称已更新:', kbName.value)
  } else {
    console.error('获取知识库详情失败:', response.message)
    ElMessage.error('获取知识库信息失败')
  }
}

// 加载知识库文本块以设定 Top K 上限（改为 chunks_list 长度）
const loadKnowledgeBaseStats = async () => {
  console.log('开始加载知识库文本块数量，kbId:', kbId.value)
  const res = await getKnowledgeBaseAttributes(kbId.value, ['chunks_list'])
  const ids = res?.data?.chunks_list || []
  const total = Array.isArray(ids) ? ids.length : 0
  totalChunks.value = total
  maxTopK.value = total > 0 ? total : 1
  if (retrieveForm.top_k > maxTopK.value) {
    retrieveForm.top_k = maxTopK.value
  }
  console.log('文本块总数:', totalChunks.value, 'Top K 上限:', maxTopK.value)
}

// 返回知识库页面
const goBack = () => {
  router.push({
  path: `/knowledge_base/${kbId.value}/files`
  })
}

// 执行检索
const performRetrieve = async () => {
  if (!retrieveForm.query.trim()) {
    ElMessage.warning('请输入查询内容')
    return
  }

  // 检索前再次验证参数
  validateTopK(retrieveForm.top_k)
  validateScoreThreshold(retrieveForm.score_threshold)

  try {
    retrieving.value = true
    hasSearched.value = false
    retrieveResults.value = []

    const startTime = Date.now()

    console.log('执行检索，参数:', {
      kb_id: kbId.value,
      query: retrieveForm.query,
      top_k: retrieveForm.top_k,
      score_threshold: retrieveForm.score_threshold
    })

    const response = await retrieveChunks(
      kbId.value,
      {
        query: retrieveForm.query,
        top_k: retrieveForm.top_k,
        threshold: retrieveForm.score_threshold,
      }
    )

    const endTime = Date.now()
    retrieveTime.value = ((endTime - startTime) / 1000).toFixed(2)

    if (response.success) {
      const baseResults = (response.data && response.data.results) ? response.data.results : []
      const chunkIds = baseResults.map(r => r.chunk_id).filter(Boolean)

      if (chunkIds.length > 0) {
        const chunkRes = await getChunkAttributesForIds(chunkIds, [
          'id',
          'file_id',
          'chunk_index',
          'chunk_text',
          'start_position',
          'end_position',
          'created_at'
        ])

        const chunkData = chunkRes?.data || null
        const chunkItems = Array.isArray(chunkData?.items)
          ? chunkData.items
          : chunkData && typeof chunkData === 'object'
            ? [chunkData]
            : []

        const chunkMap = new Map()
        chunkItems.forEach(item => {
          if (item?.id != null) {
            chunkMap.set(item.id, item)
          }
        })

        const fileIds = chunkItems.map(i => i.file_id).filter(Boolean)
        let fileNameMap = {}
        if (fileIds.length > 0) {
          const fileRes = await getFileAttributesForIds(fileIds, ['filename', 'file_type'])
          const fileData = fileRes?.data || null
          const fileItems = Array.isArray(fileData?.items)
            ? fileData.items
            : fileData && typeof fileData === 'object'
              ? [fileData]
              : []
          fileItems.forEach((item, idx) => {
            const fid = fileIds[idx]
            if (fid != null) {
              fileNameMap[fid] = {
                filename: item?.filename || `文件 ${fid}`,
                file_type: item?.file_type || ''
              }
            }
          })
        }

        retrieveResults.value = baseResults.map(r => {
          const chunk = chunkMap.get(r.chunk_id) || {}
          const fileMeta = fileNameMap[chunk.file_id] || {}
          return {
            chunk_id: r.chunk_id,
            retrieved_score: r.retrieved_score,
            reranked_score: r.reranked_score,
            file_id: chunk.file_id,
            file_name: fileMeta.filename,
            file_type: fileMeta.file_type,
            chunk_index: chunk.chunk_index,
            chunk_text: chunk.chunk_text,
            start_position: chunk.start_position,
            end_position: chunk.end_position,
            created_at: chunk.created_at,
          }
        })
      } else {
        retrieveResults.value = []
      }
      hasSearched.value = true
      ElMessage.success(`检索完成，找到 ${retrieveResults.value.length} 个相关结果`)
    } else {
      ElMessage.error(response.message || '检索失败')
      hasSearched.value = true // 即使失败也设置为已搜索，显示无结果状态
    }
  } catch (error) {
    console.error('检索失败:', error)
    ElMessage.error('检索失败: ' + (error.message || '未知错误'))
    retrieveResults.value = []
    hasSearched.value = true
  } finally {
    retrieving.value = false
  }
}

// 获取相似度标签类型
const getScoreType = (score) => {
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  return 'info'
}

// 复制文本
const copyChunkText = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('文本已复制到剪贴板')
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败')
  }
}

// 查看文件详情
const viewFileDetail = (fileId) => {
  // 新路由将 fileId 放到 query 中
  router.push({
    name: 'FileDetail',
    params: {
      kbId: kbId.value
    },
    query: {
      fileId: fileId
    }
  })
}


// 导出结果
const exportResults = () => {
  if (retrieveResults.value.length === 0) return

    const exportData = {
    knowledgeBase: {
      id: kbId.value,
      name: kbName.value
    },
    query: retrieveForm.query,
    timestamp: new Date().toISOString(),
    config: {
      top_k: retrieveForm.top_k,
      score_threshold: retrieveForm.score_threshold
    },
    results: retrieveResults.value,
    statistics: {
      total_results: retrieveResults.value.length,
      search_time: retrieveTime.value + 's'
    }
  }

  const blob = new Blob([JSON.stringify(exportData, null, 2)], {
    type: 'application/json'
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `知识库检索结果_${kbName.value}_${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('检索结果已导出')
}

onMounted(() => {
  console.log('知识库检索页面加载，知识库ID:', kbId.value)
  const init = async () => {
    loading.value = true
    try {
      await Promise.all([
        loadKnowledgeBaseDetail(),
        loadKnowledgeBaseStats()
      ])
    } catch (error) {
      console.error('初始化加载失败:', error)
      ElMessage.error('加载知识库信息失败')
    } finally {
      loading.value = false
    }
  }
  init()
})
</script>

<style scoped>
.knowledge-retrieve {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #f5f7fa;
}

/* 页面头部 */
.page-header {
  background: white;
  padding: 16px 24px;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-button {
  font-size: 14px;
  color: #606266;
  padding: 8px 12px;
}

.back-button:hover {
  color: #409eff;
  background: #f0f9ff;
}

.title-section h2 {
  margin: 0;
  color: #303133;
  font-size: 20px;
  font-weight: 600;
}

.subtitle {
  margin: 4px 0 0 0;
  color: #909399;
  font-size: 14px;
}

.description {
  margin: 4px 0 0 0;
  color: #606266;
  font-size: 13px;
  max-width: 600px;
}

/* 主容器 */
.retrieve-container {
  flex: 1;
  display: flex;
  gap: 28px;
  padding: 28px 32px;
  overflow: hidden;
  max-width: 1800px; /* 适配 2560px 宽屏 */
  margin: 0 auto;
}

/* 左侧配置面板 */
.config-panel {
  width: 420px;
  flex-shrink: 0;
}

.config-card {
  position: sticky;
  top: 0;
  height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #303133;
}

.config-item {
  margin-bottom: 20px;
}

.config-label {
  display: block;
  margin-bottom: 8px;
  color: #606266;
  font-size: 14px;
  font-weight: 500;
}

.query-input {
  width: 100%;
}

.full-width {
  width: 100%;
}

/* 嵌入模型显示 */
.model-display {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.model-input {
  width: 100%;
}

.model-input :deep(.el-input__inner) {
  background-color: #ffffff;
  border-color: #e4e7ed;
  color: #303133;
  font-weight: 500;
}

.model-input :deep(.el-input-group__prepend) {
  background-color: #409eff;
  color: white;
  border-color: #409eff;
}

.model-note {
  font-size: 12px;
  line-height: 1.2;
}

/* 滑块 + 输入框容器 */
.slider-input-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.config-slider {
  flex: 1;
}

.config-input-number {
  width: 80px;
  flex-shrink: 0;
}

/* 确保输入框数字组件样式统一 */
.config-input-number :deep(.el-input__inner) {
  text-align: center;
  font-weight: 600;
  color: #409eff;
}

.config-input-number :deep(.el-input-number__decrease),
.config-input-number :deep(.el-input-number__increase) {
  background: #f5f7fa;
  border-color: #dcdfe6;
}

.config-input-number :deep(.el-input-number__decrease):hover,
.config-input-number :deep(.el-input-number__increase):hover {
  background: #409eff;
  color: white;
}

.retrieve-button {
  width: 100%;
  height: 40px;
  font-size: 16px;
  font-weight: 600;
}

.retrieve-stats {
  margin-top: 16px;
}

.stats-info p {
  margin: 8px 0;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 14px;
}

/* 右侧结果面板 */
.results-panel {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}

.empty-state, .no-results {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
  background: white;
  border-radius: 8px;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
  background: white;
  border-radius: 8px;
}

.loading-content {
  text-align: center;
}

.loading-icon {
  font-size: 32px;
  color: #409eff;
  margin-bottom: 16px;
}

.loading-content p {
  margin: 8px 0;
  color: #606266;
}

.loading-detail {
  font-size: 12px;
  color: #909399;
}

.no-results-tips {
  text-align: left;
}

.no-results-tips ul {
  margin: 8px 0 0 20px;
  color: #909399;
}

/* 结果列表 */
.results-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-card {
  border-radius: 8px;
  transition: all 0.3s ease;
}

.result-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

/* 结果头部 */
.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.result-meta {
  display: flex;
  gap: 8px;
  align-items: center;
}

.score-tag {
  font-weight: 600;
}

.result-index {
  color: #909399;
  font-size: 12px;
  font-weight: 500;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #606266;
  font-size: 14px;
}

.page-info {
  color: #909399;
  font-size: 12px;
}

/* 文本内容 */
.chunk-content {
  line-height: 1.6;
}

.chunk-text {
  margin: 0 0 16px 0;
  color: #303133;
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 元数据 */
.metadata-section {
  margin-top: 16px;
}

.metadata-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.meta-item {
  display: flex;
  gap: 8px;
  font-size: 12px;
}

.meta-label {
  color: #909399;
  font-weight: 500;
}

.meta-value {
  color: #606266;
  font-family: 'Monaco', 'Consolas', monospace;
}

/* 操作按钮 */
.result-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .retrieve-container {
    flex-direction: column;
    gap: 16px;
  }

  .config-panel {
    width: 100%;
  }

  .metadata-grid {
    grid-template-columns: 1fr;
  }

  .slider-input-container {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .config-slider {
    width: 100%;
  }

  .config-input-number {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .retrieve-container {
    padding: 16px;
  }

  .result-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>
