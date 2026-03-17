import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '', // 使用同源 + 代理
  withCredentials: false, // 是否携带cookie
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 在发送请求之前做些什么

    // 如果有 token，添加到请求头
    const token = localStorage.getItem('token') || sessionStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // 设置默认请求头
    if (!config.headers['Content-Type']) {
      config.headers['Content-Type'] = 'application/json'
    }

    return config
  },
  (error) => {
    // 对请求错误做些什么
    console.error('请求错误：', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    if (response.config?.responseType === 'blob' || response.config?.responseType === 'arraybuffer') {
      return response.data
    }
    // 2xx 范围内的状态码都会触发该函数
    const res = response.data

    // 如果后端返回的状态码不是200，则判断为错误
    if (res.code && res.code !== 200) {
      ElMessage.error(res.message || '请求失败')

      // 如果是401，表示token过期，需要重新登录
      if (res.code === 401) {
        // 清除token
        localStorage.removeItem('token')
        sessionStorage.removeItem('token')

        // 跳转到登录页面
        window.location.href = '/login'
      }

      return Promise.reject(new Error(res.message || '请求失败'))
    }

    // 将 HTTP 状态码附加到响应体，便于前端判定 201 Created 等情况
    try {
      if (res && typeof res === 'object') {
        res.httpStatus = response.status
        // 附加一个简化的 ok 标记
        res.ok = response.status >= 200 && response.status < 300
      }
    } catch (_) {
      // 忽略附加失败
    }

    return res
  },
  (error) => {
    // 超出 2xx 范围的状态码都会触发该函数
    console.error('响应错误：', error)

    let message = '请求失败'

    if (error.response) {
      // 请求已发出，但服务器响应的状态码不在 2xx 范围内
      const { status, data } = error.response

      switch (status) {
        case 400:
          message = data?.message || '请求参数错误'
          break
        case 401:
          message = '未授权，请重新登录'
          // 清除token
          localStorage.removeItem('token')
          sessionStorage.removeItem('token')
          // 跳转到登录页面
          setTimeout(() => {
            window.location.href = '/login'
          }, 1000)
          break
        case 403:
          message = '拒绝访问'
          break
        case 404:
          message = '请求资源不存在'
          break
        case 408:
          message = '请求超时'
          break
        case 500:
          message = '服务器内部错误'
          break
        case 502:
          message = '网关错误'
          break
        case 503:
          message = '服务不可用'
          break
        case 504:
          message = '网关超时'
          break
        default:
          message = data?.message || `连接错误${status}`
      }
    } else if (error.request) {
      // 请求已发出，但没有收到响应
      message = '网络连接异常'
    } else {
      // 发送请求时出了点问题
      message = error.message || '请求失败'
    }

    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default request
