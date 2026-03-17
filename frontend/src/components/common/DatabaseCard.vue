<template>
  <div class="database-card" @click="$emit('click', database)">
    <div class="card-header">
      <el-icon class="database-icon"><Folder /></el-icon>
      <div class="database-info">
        <h3 class="database-name">{{ database.name }}</h3>
        <p class="database-desc">{{ database.description }}</p>
      </div>
    </div>
    <div class="card-footer">
      <span class="file-count">{{ database.fileCount }} 个文件</span>
      <span class="update-time">{{ formatTime(database) }}</span>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

defineProps({
  database: {
    type: Object,
    required: true
  }
})

defineEmits(['click'])

const formatTime = (dbOrTime) => {
  // 兼容对象或直接传入时间值，优先使用后端提供的文本字段
  let time = ''
  if (dbOrTime && typeof dbOrTime === 'object') {
    time = dbOrTime.updated_at || dbOrTime.updatedAt || dbOrTime.created_at || dbOrTime.createdAt || dbOrTime.timestamp || ''
  } else {
    time = dbOrTime
  }

  if (!time && time !== 0) return ''
  return time
}
</script>

<style scoped>
.database-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.database-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  align-items: flex-start;
  margin-bottom: 12px;
}

.database-icon {
  font-size: 24px;
  color: #3b82f6;
  margin-right: 12px;
}

.database-name {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 4px 0;
}

.database-desc {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #9ca3af;
}
</style>
