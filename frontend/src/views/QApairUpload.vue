<template>
	<div class="qapair-upload">
		<div class="step-card">
			<div class="card-header">
				<h2>上传 QApair 文件</h2>
				<p>仅支持 JSON 文件，文件中为问答对列表</p>
			</div>

			<div class="card-content">
				<div class="upload-area">
					<el-upload
						ref="uploadRef"
						class="upload-dragger"
						drag
						:multiple="true"
						:auto-upload="false"
						:on-change="handleChange"
						:on-remove="handleRemove"
						accept=".json"
					>
						<el-icon class="el-icon--upload">
							<UploadFilled />
						</el-icon>
						<div class="el-upload__text">
							将 JSON 文件拖到此处，或<em>点击选择</em>
						</div>
						<template #tip>
							<div class="el-upload__tip">支持多个 JSON 文件</div>
						</template>
					</el-upload>
				</div>

				<div v-if="fileList.length > 0" class="file-list">
					<h3>待上传 ({{ fileList.length }})</h3>
					<div class="file-items">
						<div v-for="f in fileList" :key="f.uid" class="file-item">
							<div class="file-name">{{ f.name }}</div>
							<el-button type="danger" link @click="removeFile(f)">移除</el-button>
						</div>
					</div>
				</div>
			</div>

			<div class="card-footer">
				<el-button @click="goBack" :disabled="uploading">返回</el-button>
				<el-button type="primary" @click="doUpload" :disabled="fileList.length===0" :loading="uploading">
					{{ uploading ? '上传中...' : '上传' }}
				</el-button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { uploadQApairFiles } from '@/api/qapair'

const router = useRouter()
const uploadRef = ref()
const fileList = ref([])
const uploading = ref(false)

const handleChange = (file, files) => {
	fileList.value = [...files]
}

const handleRemove = (file, files) => {
	fileList.value = [...files]
}

const removeFile = (file) => {
	uploadRef.value?.handleRemove(file)
}

const doUpload = async () => {
	if (!fileList.value.length) return
	try {
		uploading.value = true
		const rawFiles = fileList.value.map(f => f.raw)
		await uploadQApairFiles(rawFiles)
		ElMessage.success('上传成功')
		router.push('/QApair')
	} catch (e) {
		console.error(e)
		ElMessage.error('上传失败')
	} finally {
		uploading.value = false
	}
}

const goBack = () => {
	router.back()
}
</script>

<style scoped>
.qapair-upload {
	display: flex;
	justify-content: center;
	align-items: flex-start;
	min-height: 100%;
	padding: 2rem 1rem;
}

.step-card {
	background: rgba(255, 255, 255, 0.95);
	backdrop-filter: blur(10px);
	border-radius: 1rem;
	padding: 2rem;
	box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
	border: 1px solid rgba(255, 255, 255, 0.2);
	width: 100%;
	max-width: 700px;
}

.card-header {
	text-align: center;
	margin-bottom: 2rem;
	padding-bottom: 1rem;
	border-bottom: 1px solid rgba(229, 231, 235, 0.3);
}

.card-content { margin-bottom: 2rem; }
.upload-area { margin-bottom: 2rem; }
.upload-dragger { width: 100%; }

.file-list h3 { margin: 0 0 1rem 0; color: #1f2937; font-size: 1.1rem; }
.file-items { display: flex; flex-direction: column; gap: 8px; }
.file-item { display: flex; justify-content: space-between; align-items: center; padding: 10px; background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; }
.file-name { color: #374151; word-break: break-all; }

.card-footer { display: flex; justify-content: space-between; gap: 1rem; padding-top: 1rem; border-top: 1px solid rgba(229,231,235,0.3); }
</style>
