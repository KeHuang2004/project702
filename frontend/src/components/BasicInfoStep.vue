<template>
  <div class="basic-info-step">
    <div class="step-card">
      <div class="card-header">
        <h2>基本信息</h2>
        <p>请填写知识库的基本信息</p>
      </div>

      <div class="card-content">
        <el-form
          ref="formRef"
          :model="localFormData"
          :rules="formRules"
          label-position="top"
          class="info-form"
        >
          <el-form-item label="知识库名称" prop="name">
            <el-input
              v-model="localFormData.name"
              placeholder="请输入知识库名称"
              maxlength="50"
              show-word-limit
              @input="updateFormData"
            />
          </el-form-item>

          <el-form-item label="知识库描述" prop="description">
            <el-input
              v-model="localFormData.description"
              type="textarea"
              placeholder="请输入知识库描述（可选）"
              maxlength="200"
              show-word-limit
              :rows="4"
              resize="none"
              @input="updateFormData"
            />
          </el-form-item>

        </el-form>
      </div>

      <div class="card-footer">
        <el-button @click="handleCancel" size="large">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="handleNext"
          size="large"
          :loading="isSubmitting"
          :disabled="!localFormData.name.trim()"
        >
          {{ isSubmitting ? '创建中...' : '创建' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createKnowledgeBase } from '@/api/knowledge'

// Props
const props = defineProps({
  basicInfo: {
    type: Object,
    default: () => ({
      name: '',
      description: ''
    })
  }
})

// Emits
const emit = defineEmits(['update:basicInfo', 'next', 'cancel'])

// 响应式数据
const formRef = ref()
const isSubmitting = ref(false)

// 本地表单数据
const localFormData = reactive({
  name: '',
  description: ''
})

// 表单验证规则
const formRules = {
  name: [
    { required: true, message: '请输入知识库名称', trigger: 'blur' },
    { min: 2, max: 50, message: '名称长度在 2 到 50 个字符', trigger: 'blur' },
    {
      pattern: /^[\u4e00-\u9fa5a-zA-Z0-9_\-\s]+$/,
      message: '名称只能包含中文、英文、数字、下划线和横线',
      trigger: 'blur'
    }
  ],
  description: [
    { max: 200, message: '描述不能超过 200 个字符', trigger: 'blur' }
  ]
}

// 更新父组件数据
const updateFormData = () => {
  emit('update:basicInfo', { ...localFormData })
}

// 处理下一步
const handleNext = async () => {
  if (!formRef.value) {
    console.error('表单引用不存在')
    return
  }

  try {
    // 验证表单
    await formRef.value.validate()

    isSubmitting.value = true
    console.log('准备提交的数据:', localFormData)

    // 准备API请求数据
    const requestData = {
      name: localFormData.name.trim(),
      description: localFormData.description.trim()
    }

    console.log('发送到API的数据:', requestData)

    // 调用创建知识库API
    const response = await createKnowledgeBase(requestData)

    console.log('创建知识库API完整响应:', response)

    // 提取知识库ID - 根据实际API响应格式调整
    let knowledgeBaseId = null

    if (response) {
      // 尝试不同的可能字段名
      knowledgeBaseId = response.id ||
                       response.kb_id ||
                       response.knowledge_base_id ||
                       response.data?.id ||
                       response.data?.kb_id ||
                       response.data?.knowledge_base_id
    }

    console.log('提取的知识库ID:', knowledgeBaseId, typeof knowledgeBaseId)

    // 验证知识库ID
    if (!knowledgeBaseId) {
      console.error('API响应中未找到知识库ID，完整响应:', response)
      throw new Error('创建知识库成功，但未返回有效的知识库ID。请检查API响应格式。')
    }

    // 确保ID是字符串或数字
    const validId = String(knowledgeBaseId).trim()
    if (!validId || validId === 'undefined' || validId === 'null') {
      throw new Error('返回的知识库ID无效')
    }

    console.log('验证后的知识库ID:', validId)

    // 更新父组件的基本信息
    updateFormData()

    // 发出next事件，传递知识库ID
    emit('next', validId)

    ElMessage.success('知识库创建成功')

  } catch (error) {
    console.error('创建知识库失败:', error)

    let errorMessage = '创建知识库失败: '

    if (error.response) {
      const { status, data } = error.response
      console.error('HTTP错误详情:', { status, data })

      if (status === 400) {
        errorMessage += data?.message || data?.error || '请求参数错误，请检查输入信息'
      } else if (status === 409) {
        errorMessage += '知识库名称已存在，请选择其他名称'
      } else if (status === 500) {
        errorMessage += '服务器内部错误，请稍后重试'
      } else {
        errorMessage += data?.message || data?.error || `服务器错误 (${status})`
      }
    } else if (error.message?.includes('Network Error')) {
      errorMessage += '网络连接失败，请检查网络状态'
    } else {
      errorMessage += error.message || '未知错误'
    }

    ElMessage.error(errorMessage)
  } finally {
    isSubmitting.value = false
  }
}

// 处理取消
const handleCancel = () => {
  emit('cancel')
}

// 监听props变化
watch(
  () => props.basicInfo,
  (newInfo) => {
    if (newInfo) {
      Object.assign(localFormData, newInfo)
    }
  },
  { immediate: true, deep: true }
)

// 组件挂载时初始化
onMounted(() => {
  console.log('BasicInfoStep 组件挂载，初始数据:', localFormData)
})

// 暴露方法给父组件
defineExpose({
  resetForm: () => {
    formRef.value?.resetFields()
  },
  validateForm: () => {
    return formRef.value?.validate()
  }
})
</script>

<style scoped>
.basic-info-step {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  min-height: 100%;
}

.step-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  padding: 2rem;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  max-width: 900px;
  width: 100%;
}

.card-header {
  text-align: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(229, 231, 235, 0.3);
}

.card-header h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 0.5rem;
}

.card-header p {
  color: #6b7280;
  margin: 0;
}

.info-form {
  margin-bottom: 2rem;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

@media (max-width: 768px) {
  .step-card {
    margin: 1rem;
    padding: 1.5rem;
  }

  .card-footer {
    flex-direction: column;
  }
}
</style>
