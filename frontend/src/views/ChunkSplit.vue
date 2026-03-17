<template>
  <div class="chunk-split-page">
    <ChunkSplitPanel :kb-id="kbId" @done="handleDone" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import ChunkSplitPanel from '@/components/ChunkSplitPanel.vue'

const route = useRoute()
const kbId = route.params.kbId

const handleDone = () => {
  ElMessage.success('切分完成')
}
</script>

<style scoped>
.chunk-split-page {
  padding: 24px;
}
</style>
