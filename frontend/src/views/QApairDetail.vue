<template>
  <div class="overlay" @click.self="close">
    <div class="modal">
      <div class="modal-header">
        <div class="title">QApair #{{ id }}</div>
        <!-- 顶部中间：查看/编辑 两个按钮，样式与顶栏一致 -->
        <div class="sub-nav-buttons">
          <el-button
            :type="!isEditing ? 'primary' : ''"
            :class="['sub-nav-button', { 'active-button': !isEditing }]"
            @click="switchToView"
          >查看</el-button>
          <el-button
            :type="isEditing ? 'primary' : ''"
            :class="['sub-nav-button', { 'active-button': isEditing }]"
            @click="switchToEdit"
          >编辑</el-button>
        </div>
        <div class="header-actions">
          <template v-if="isEditing">
            <el-button type="success" size="small" @click="onSave">保存</el-button>
            <el-button type="default" plain size="small" @click="cancelEdit">取消</el-button>
          </template>
          <el-button type="danger" plain size="small" @click="onDelete">删除</el-button>
          <el-button circle @click="close" title="关闭">✕</el-button>
        </div>
      </div>
      <div class="modal-body">
        <div class="box">
          <div class="box-title">问题</div>
          <div v-if="!isEditing" class="box-content markdown" v-html="renderedQuestion"></div>
          <div v-else class="box-content">
            <el-input
              v-model="editQuestion"
              type="textarea"
              :autosize="{ minRows: 8 }"
              placeholder="请输入问题（支持 Markdown，但此处为原文编辑）"
            />
          </div>
        </div>
        <div class="box">
          <div class="box-title">答案</div>
          <div v-if="!isEditing" class="box-content markdown" v-html="renderedAnswer"></div>
          <div v-else class="box-content">
            <el-input
              v-model="editAnswer"
              type="textarea"
              :autosize="{ minRows: 8 }"
              placeholder="请输入答案（支持 Markdown，但此处为原文编辑）"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getQApairById, deleteQApairById, updateQApairById } from '@/api/qapair'
import { marked } from 'marked'
import hljs from 'highlight.js'

const route = useRoute()
const router = useRouter()
const id = computed(() => Number(route.params.id))

const question = ref('')
const answer = ref('')
const isEditing = ref(false)
const editQuestion = ref('')
const editAnswer = ref('')

marked.setOptions({
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  }
})

const renderedQuestion = computed(() => marked.parse(question.value || ''))
const renderedAnswer = computed(() => marked.parse(answer.value || ''))

const load = async () => {
  try {
    const res = await getQApairById(id.value)
    const item = res.data.item
    if (!item) throw new Error('未找到数据')
    question.value = item.question || ''
    answer.value = item.answer || ''
    if (isEditing.value) {
      // 若刷新时仍在编辑模式，同步编辑数据
      editQuestion.value = question.value
      editAnswer.value = answer.value
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载失败')
    close()
  }
}

const close = () => {
  router.back()
}

onMounted(load)
watch(() => route.params.id, load)

const onDelete = async () => {
  try {
    await ElMessageBox.confirm(`确认删除 QApair #${id.value} 吗？`, '提示', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  try {
    await deleteQApairById(id.value)
    ElMessage.success('删除成功')
    close()
  } catch (e) {
    console.error(e)
    ElMessage.error('删除失败')
  }
}

const startEdit = () => { // 向后兼容（外部可能复用）
  editQuestion.value = question.value
  editAnswer.value = answer.value
  isEditing.value = true
}

const cancelEdit = () => {
  isEditing.value = false
}

const onSave = async () => {
  const q = (editQuestion.value || '').trim()
  const a = (editAnswer.value || '').trim()
  if (!q) {
    ElMessage.warning('question 不能为空')
    return
  }
  try {
    const res = await updateQApairById(id.value, { question: q, answer: a })
    const item = res.data?.item
    // 优先使用后端返回的实体，否则采用本地提交值
    question.value = item?.question ?? q
    answer.value = item?.answer ?? a
    isEditing.value = false
    ElMessage.success('保存成功')
  } catch (e) {
    console.error(e)
    ElMessage.error('保存失败')
  }
}

// 新的切换方法：顶部中间的“查看/编辑”按钮
const switchToView = () => {
  isEditing.value = false
}
const switchToEdit = () => {
  if (!isEditing.value) {
    editQuestion.value = question.value
    editAnswer.value = answer.value
  }
  isEditing.value = true
}
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  width: min(1100px, 94vw);
  height: min(80vh, 800px);
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
  position: relative; /* 以便中间绝对定位 */
}
.header-actions { display: flex; align-items: center; gap: 8px; }
.modal-header .title { font-weight: 600; }
.modal-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 12px;
  height: 100%;
}
.box { display: flex; flex-direction: column; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }
.box-title { font-weight: 600; background: #f9fafb; padding: 8px 12px; border-bottom: 1px solid #e5e7eb; }
.box-content { padding: 12px; overflow: auto; height: 100%; }

/* 顶部中间的子导航按钮，复用顶栏样式 */
.sub-nav-buttons {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 12px;
  align-items: center;
}
.sub-nav-button {
  padding: 6px 20px;
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.3s ease;
  min-width: 96px;
}
.sub-nav-button:not(.active-button) {
  background: transparent;
  border: 1px solid #d1d5db;
  color: #6b7280;
}
.sub-nav-button:not(.active-button):hover {
  background: #f9fafb;
  border-color: #9ca3af;
  color: #374151;
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 6px 18px rgba(0,0,0,0.08);
}
.active-button {
  background: #3b82f6 !important;
  border-color: #3b82f6 !important;
  color: #fff !important;
}

/* markdown 基础样式 */
.markdown :deep(pre) { background:#0b1021; color:#e6e6e6; padding:12px; border-radius:6px; overflow:auto }
.markdown :deep(code) { background:#f5f5f5; padding:2px 4px; border-radius:4px }
.markdown :deep(h1), .markdown :deep(h2), .markdown :deep(h3) { margin: 0.5em 0; }
.markdown :deep(p) { line-height: 1.6; }
.markdown :deep(ul), .markdown :deep(ol){ padding-left: 1.2em; }
</style>
