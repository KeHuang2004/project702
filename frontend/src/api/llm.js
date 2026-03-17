import request from '@/utils/request'

/**
 * 文本生成（流式）：用于 RAG 管线的抽取与最终重写
 * 逐行返回 "data: {json}"，最后 "data: [DONE]"
 * @param {string} prompt 提示词
 * @param {(data:string)=>void} onMessage 回调，入参为每行的 JSON 字符串（不含 'data: ' 前缀）
 */
const BASE = import.meta.env.VITE_API_BASE_URL || ''

export async function generateStream(prompt, onMessage) {
  const response = await fetch(`${BASE}/api/v1/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt })
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      if (buffer) {
        const lines = buffer.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim()
            if (data) onMessage(data)
          }
        }
        buffer = ''
      }
      break
    }
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n')
    buffer = parts.pop() || ''
    for (const line of parts) {
      const trimmed = line.trim()
      if (!trimmed) continue
      if (trimmed.startsWith('data: ')) {
        const data = trimmed.slice(6).trim()
        if (data) onMessage(data)
      }
    }
  }
}
