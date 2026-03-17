<template>
  <div class="chunk-settings-step">
    <div class="step-card">
      <div class="card-header">
        <h2>分段设置</h2>
        <p>配置文档分段策略和参数</p>
      </div>

      <div class="card-content">
        <el-form
          ref="formRef"
          :model="localSettings"
          :rules="rules"
          label-width="120px"
          size="large"
        >
          <el-form-item label="分段策略" prop="strategy">
            <el-select
              v-model="localSettings.strategy"
              placeholder="请选择分段策略"
              style="width: 100%"
              @change="handleStrategyChange"
            >
              <el-option
                v-for="strategy in strategies"
                :key="strategy.value"
                :label="strategy.label"
                :value="strategy.value"
              >
                <div class="custom-option">
                  <div class="option-title">{{ strategy.label }}</div>
                  <div class="option-desc">{{ strategy.description }}</div>
                </div>
              </el-option>
            </el-select>
          </el-form-item>

          <el-form-item label="块长度" prop="chunkSize">
            <el-input-number
              v-model="localSettings.chunkSize"
              :min="500"
              :max="8000"
              :step="100"
              style="width: 100%"
              controls-position="right"
              @change="updateSettings"
            />
            <div class="form-tip">
              建议范围：500-8000，较小的块长度有助于提高检索精度
            </div>
          </el-form-item>

          <el-form-item label="重叠长度" prop="chunkOverlap">
            <el-input-number
              v-model="localSettings.chunkOverlap"
              :min="300"
              :max="1500"
              :step="50"
              style="width: 100%"
              controls-position="right"
              @change="updateSettings"
            />
            <div class="form-tip">
              建议范围：200-1500，有助于保持上下文连贯性
            </div>
          </el-form-item>
        </el-form>

        <!-- 策略说明 -->
        <div class="strategy-info">
          <h3>当前选择：{{ getCurrentStrategyInfo().label }}</h3>
          <p class="strategy-desc">{{ getCurrentStrategyInfo().description }}</p>
          <div class="strategy-features">
            <h4>适用场景：</h4>
            <ul>
              <li v-for="feature in getCurrentStrategyInfo().features" :key="feature">
                {{ feature }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div class="card-footer">
        <el-button @click="handlePrev" size="large">上一步</el-button>
        <el-button type="primary" @click="handleNext" size="large">下一步</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  settings: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['update:settings', 'next', 'prev'])

const formRef = ref()

// 创建本地响应式数据
const localSettings = reactive({
  strategy: 'recursive_character',
  chunkSize: 1000,
  chunkOverlap: 200
})

const strategies = [
  {
    value: 'recursive_character',
    label: '递归字符分割',
    description: '按字符递归分割，优先保持段落完整性',
    features: [
      '自动识别段落、句子边界',
      '保持文本结构完整性',
      '适用于大部分文档类型',
      '推荐用于通用场景'
    ]
  },
  {
    value: 'token_text',
    label: '固定长度分割',
    description: '按固定Token长度分割，确保块大小一致',
    features: [
      '严格控制每块的Token数量',
      '分割结果大小一致',
      '适用于有严格长度要求的场景',
      '可能会截断句子'
    ]
  },
  {
    value: 'SemanticChunker',
    label: '语义分割',
    description: '基于语义相似性分割，保持主题连贯性',
    features: [
      '基于语义相似性分割',
      '保持主题和概念完整',
      '分割质量较高',
      '处理速度相对较慢'
    ]
  }
]

const rules = {
  strategy: [
    { required: true, message: '请选择分段策略', trigger: 'change' }
  ],
  chunkSize: [
    { required: true, message: '请输入块长度', trigger: 'blur' },
    { type: 'number', min: 100, max: 4000, message: '块长度范围：100-4000', trigger: 'blur' }
  ],
  chunkOverlap: [
    { required: true, message: '请输入重叠长度', trigger: 'blur' },
    { type: 'number', min: 0, message: '重叠长度不能小于0', trigger: 'blur' }
  ]
}

const getCurrentStrategyInfo = () => {
  return strategies.find(s => s.value === localSettings.strategy) || strategies[0]
}

const updateSettings = () => {
  emit('update:settings', { ...localSettings })
}

const handleStrategyChange = (value) => {
  // 根据不同策略调整默认参数
  switch (value) {
    case 'recursive_character':
      localSettings.chunkSize = 1000
      localSettings.chunkOverlap = 200
      break
    case 'token_text':
      localSettings.chunkSize = 512
      localSettings.chunkOverlap = 50
      break
    case 'SemanticChunker':
      localSettings.chunkSize = 800
      localSettings.chunkOverlap = 100
      break
  }
  updateSettings()
}

const handleNext = async () => {
  try {
    await formRef.value.validate()
    emit('next')
  } catch (error) {
    ElMessage.error('请完善分段设置')
  }
}

const handlePrev = () => {
  emit('prev')
}

// 监听 props 变化，同步到本地数据
watch(() => props.settings, (newSettings) => {
  Object.assign(localSettings, newSettings)
}, { immediate: true, deep: true })
</script>

<style scoped>
.chunk-settings-step {
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
  width: 100%;
  max-width: 700px;
}

.card-header {
  text-align: center;
  margin-bottom: 2rem;
}

.card-header h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 0.5rem 0;
}

.card-header p {
  color: #6b7280;
  margin: 0;
}

.custom-option {
  margin: 0.5rem 0;
}

.option-title {
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 0.25rem;
}

.option-desc {
  font-size: 0.875rem;
  color: #6b7280;
}

.form-tip {
  font-size: 0.75rem;
  color: #6b7280;
  margin-top: 0.5rem;
  line-height: 1.4;
}

.strategy-info {
  margin-top: 2rem;
  padding: 1.5rem;
  background: rgba(59, 130, 246, 0.05);
  border-radius: 0.75rem;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.strategy-info h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 0.5rem 0;
}

.strategy-desc {
  color: #6b7280;
  margin: 0 0 1rem 0;
  line-height: 1.5;
}

.strategy-features h4 {
  font-size: 1rem;
  font-weight: 500;
  color: #374151;
  margin: 0 0 0.5rem 0;
}

.strategy-features ul {
  margin: 0;
  padding-left: 1.5rem;
}

.strategy-features li {
  color: #6b7280;
  margin-bottom: 0.25rem;
  line-height: 1.4;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 2rem;
}
</style>
