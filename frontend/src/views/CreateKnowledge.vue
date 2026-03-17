<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'

// 组件导入
import BasicInfoStep from '../components/BasicInfoStep.vue'

// 路由
const router = useRouter()

// 响应式数据
const currentStep = ref(0)
const knowledgeBaseId = ref(null)

// 表单数据
const basicInfo = reactive({
  name: '',
  description: ''
})

// 方法
const nextStep = () => {
  if (currentStep.value < 1) {
    currentStep.value++
  }
}

// 修复：正确处理知识库ID
const handleBasicInfoNext = (kbId) => {
  console.log('接收到知识库ID:', kbId, typeof kbId)

  // 严格验证知识库ID
  if (!kbId) {
    console.error('知识库ID为空:', kbId)
    ElMessage.error('创建知识库失败，未获取到知识库ID')
    return
  }

  // 检查是否是对象（错误情况）
  if (typeof kbId === 'object') {
    console.error('接收到对象而非ID:', kbId)
    ElMessage.error('创建知识库失败，返回数据格式错误')
    return
  }

  // 确保ID是有效的字符串或数字
  const validId = String(kbId).trim()
  if (!validId || validId === 'undefined' || validId === 'null') {
    console.error('知识库ID无效:', validId)
    ElMessage.error('创建知识库失败，获取到无效的知识库ID')
    return
  }

  knowledgeBaseId.value = validId
  console.log('设置知识库ID成功:', knowledgeBaseId.value, typeof knowledgeBaseId.value)

  router.push(`/knowledge_base/${validId}/files`)
}

const handleBack = async () => {
  router.push('/statistic')
}

// 添加错误处理
const handleBasicInfoCancel = () => {
  router.push('/knowledge')
}
</script>

<template>
  <div class="create-knowledge-page">
    <div class="page-header">
      <el-button
        :icon="ArrowLeft"
        @click="handleBack"
        class="back-button"
      >
        返回
      </el-button>
      <h1>创建知识库</h1>
    </div>

    <div class="steps-container">
      <div class="step-content-wrapper">
        <div class="step-content">
          <BasicInfoStep
            v-model:basicInfo="basicInfo"
            @next="handleBasicInfoNext"
            @cancel="handleBasicInfoCancel"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.create-knowledge-page {
  padding: 2.5rem 3rem;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.page-header h1 {
  margin: 0;
  font-size: 1.8rem;
  font-weight: 600;
  color: #1f2937;
}

.back-button {
  border: none;
  color: #6b7280;
}

.steps-container {
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.steps-indicator {
  padding: 2rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.step-content-wrapper {
  min-height: 60vh;
}

.step-content {
  height: 100%;
}
</style>
