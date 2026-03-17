import request from '@/utils/request'

// 获取全量问答对列表（按 id 升序）
export function listQApairs() {
  return request({
    url: '/api/v1/qapairs',
    method: 'get'
  })
}

// 按 id 获取单条问答对
export function getQApairById(id) {
  return request({
    url: `/api/v1/qapairs/${id}`,
    method: 'get'
  })
}

// 上传 JSON 文件（多个），服务端解析并批量入库
export function uploadQApairFiles(files) {
  const form = new FormData()
  files.forEach(f => form.append('files', f))
  return request({
    url: '/api/v1/qapairs',
    method: 'post',
    data: form,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 按 id 删除问答对
export function deleteQApairById(id) {
  return request({
    url: `/api/v1/qapairs/${id}`,
    method: 'delete'
  })
}

// 按 id 更新问答对
export function updateQApairById(id, data) {
  return request({
    url: `/api/v1/qapairs/${id}`,
    method: 'put',
    data
  })
}
