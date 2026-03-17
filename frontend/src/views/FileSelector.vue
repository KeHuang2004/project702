<template>
  <div class="file-selector">
    <div class="selector-header">
      <h2>选择文献文件</h2>
      <p>请选择一篇文献进行要点提炼</p>
    </div>

    <div class="file-list">
      <el-table
        :data="files"
        style="width: 100%"
        @row-click="selectFile"
        :highlight-current-row="true"
      >
        <el-table-column prop="id" label="ID" width="80"></el-table-column>
        <el-table-column prop="filename" label="文件名"></el-table-column>
        <el-table-column prop="file_type" label="类型" width="100"></el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="scope">
            <el-button size="small" type="primary" @click="selectFile(scope.row)">选择</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="selector-footer">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="totalFiles"
        layout="prev, pager, next"
        @current-change="handlePageChange"
      />
      <el-button @click="cancel">取消</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const router = useRouter()
const files = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const totalFiles = ref(0)

const loadFiles = async (page = 1) => {
  try {
    // 获取所有文件
    const response = await request({
      url: '/api/v1/files',
      method: 'get'
    })
    console.log('获取所有文件响应:', response)
    if (response.success) {
      // 获取文件详情
      const fileIds = response.data.ids || []
      console.log('文件ID列表:', fileIds)
      totalFiles.value = fileIds.length
      // 分页
      const start = (page - 1) * pageSize.value
      const end = start + pageSize.value
      const pageIds = fileIds.slice(start, end)
      const detailedFiles = []
      for (const id of pageIds) {
        try {
          const detailResponse = await request({
            url: `/api/v1/files/${id}?attribute=filename,file_type`,
            method: 'get'
          })
          console.log(`文件 ${id} 详情响应:`, detailResponse)
          if (detailResponse.success) {
            detailedFiles.push({ id, ...detailResponse.data })
          }
        } catch (e) {
          console.error(`获取文件 ${id} 详情失败:`, e)
        }
      }
      console.log('详细文件列表:', detailedFiles)
      files.value = detailedFiles
    }
  } catch (error) {
    ElMessage.error('加载文件列表失败')
    console.error(error)
  }
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadFiles(page)
}

const selectFile = (file) => {
  // 存储选中的文件ID
  localStorage.setItem('selectedFileId', file.id)
  localStorage.setItem('selectedFileName', file.filename)
  // 设置模式为summary
  localStorage.setItem('appMode', 'summary')
  // 设置自动发送标志
  localStorage.setItem('autoSend', 'true')
  // 回到聊天界面
  router.push('/chat')
}

const cancel = () => {
  router.push('/chat')
}

onMounted(() => {
  loadFiles(1)
})
</script>

<style scoped>
.file-selector {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.selector-header {
  text-align: center;
  margin-bottom: 20px;
}

.selector-header h2 {
  margin-bottom: 10px;
}

.file-list {
  margin-bottom: 20px;
}

.selector-footer {
  text-align: center;
}
</style>