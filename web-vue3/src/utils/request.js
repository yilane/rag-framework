import axios from 'axios'
import { ElMessage } from 'element-plus'
import { apiBaseUrl } from '@/config/api'

// 创建axios实例
const service = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000 // 请求超时时间
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    // 在发送请求之前做些什么
    // 例如添加token等
    // config.headers['Authorization'] = `Bearer ${getToken()}`
    return config
  },
  error => {
    // 对请求错误做些什么
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  response => {
    // 对响应数据做点什么
    const res = response.data
    
    // 如果返回的状态码不是200，则判断为错误
    if (response.status !== 200) {
      ElMessage({
        message: res.message || '网络错误',
        type: 'error',
        duration: 5 * 1000
      })
      
      return Promise.reject(new Error(res.message || '网络错误'))
    } else {
      return res
    }
  },
  error => {
    // 对响应错误做点什么
    console.error('响应错误:', error)
    const message = error.response?.data?.message || error.message || '网络错误'
    ElMessage({
      message: message,
      type: 'error',
      duration: 5 * 1000
    })
    return Promise.reject(error)
  }
)

// 封装GET请求
export function get(url, params) {
  return service({
    url,
    method: 'get',
    params
  })
}

// 封装POST请求
export function post(url, data) {
  return service({
    url,
    method: 'post',
    data
  })
}

// 封装PUT请求
export function put(url, data) {
  return service({
    url,
    method: 'put',
    data
  })
}

// 封装DELETE请求
export function del(url) {
  return service({
    url,
    method: 'delete'
  })
}

// 封装上传文件请求
export function upload(url, formData) {
  return service({
    url,
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 封装下载文件请求
export function download(url, params) {
  return service({
    url,
    method: 'get',
    params,
    responseType: 'blob'
  })
}

export default service 