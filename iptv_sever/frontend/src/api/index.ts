import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    if (error.response) {
      // 如果响应有 data，返回 data，否则返回错误信息
      const errorData = error.response.data
      if (errorData && typeof errorData === 'object') {
        return Promise.reject({
          message: errorData.detail || errorData.message || '请求失败',
          detail: errorData.detail,
          status: error.response.status,
        })
      }
      return Promise.reject({
        message: `请求失败 (${error.response.status})`,
        status: error.response.status,
      })
    }
    if (error.request) {
      return Promise.reject({
        message: '网络错误，无法连接到服务器',
      })
    }
    return Promise.reject({
      message: error.message || '未知错误',
    })
  }
)

export default api

