/**
 * 统一错误处理工具
 * 根据后端API的HTTPException返回格式 {detail: "错误信息"} 进行优化
 */

import { ElMessage, ElNotification } from 'element-plus'

/**
 * 从错误对象中提取错误信息
 * @param {Error} error - 错误对象
 * @param {string} defaultMessage - 默认错误信息
 * @returns {string} 错误信息
 */
export function extractErrorMessage(error, defaultMessage = '操作失败') {
  // 优先级：
  // 1. 后端返回的 detail 字段（HTTPException 格式）
  // 2. 后端返回的 message 字段（其他格式）
  // 3. axios 错误信息
  // 4. 默认错误信息
  
  if (error?.response?.data) {
    const data = error.response.data
    
    // FastAPI HTTPException 格式
    if (data.detail) {
      return data.detail
    }
    
    // 其他可能的格式
    if (data.message) {
      return data.message
    }
    
    // 如果 data 是字符串
    if (typeof data === 'string') {
      return data
    }
  }
  
  // axios 网络错误等
  if (error?.message) {
    return error.message
  }
  
  // 最后的默认值
  return defaultMessage
}

/**
 * 显示错误消息（简短提示）
 * @param {Error|string} error - 错误对象或错误信息
 * @param {string} defaultMessage - 默认错误信息
 */
export function showErrorMessage(error, defaultMessage = '操作失败') {
  const message = typeof error === 'string' ? error : extractErrorMessage(error, defaultMessage)
  
  ElMessage({
    message: message,
    type: 'error',
    duration: 5000,
    showClose: true
  })
}

/**
 * 显示错误通知（详细信息）
 * @param {Error|string} error - 错误对象或错误信息
 * @param {string} title - 通知标题
 * @param {string} defaultMessage - 默认错误信息
 */
export function showErrorNotification(error, title = '操作失败', defaultMessage = '请稍后重试') {
  const message = typeof error === 'string' ? error : extractErrorMessage(error, defaultMessage)
  
  ElNotification({
    title: title,
    message: message,
    type: 'error',
    duration: 8000,
    showClose: true
  })
}

/**
 * 获取HTTP状态码
 * @param {Error} error - 错误对象
 * @returns {number|null} HTTP状态码
 */
export function getErrorStatus(error) {
  return error?.response?.status || null
}

/**
 * 判断是否为特定的HTTP错误
 * @param {Error} error - 错误对象
 * @param {number} statusCode - HTTP状态码
 * @returns {boolean}
 */
export function isHttpError(error, statusCode) {
  return getErrorStatus(error) === statusCode
}

/**
 * 格式化错误信息，包含状态码
 * @param {Error} error - 错误对象
 * @param {string} operation - 操作名称
 * @returns {string} 格式化的错误信息
 */
export function formatErrorMessage(error, operation = '操作') {
  const status = getErrorStatus(error)
  const message = extractErrorMessage(error)
  
  if (status) {
    return `${operation}失败 (${status}): ${message}`
  } else {
    return `${operation}失败: ${message}`
  }
}

/**
 * 错误处理的通用方法
 * @param {Error} error - 错误对象
 * @param {Object} options - 配置选项
 * @param {string} options.operation - 操作名称
 * @param {string} options.defaultMessage - 默认错误信息
 * @param {boolean} options.showMessage - 是否显示消息提示
 * @param {boolean} options.showNotification - 是否显示通知
 * @param {Function} options.onError - 自定义错误处理函数
 * @returns {string} 错误信息
 */
export function handleError(error, options = {}) {
  const {
    operation = '操作',
    defaultMessage = '请稍后重试',
    showMessage = true,
    showNotification = false,
    onError = null
  } = options
  
  console.error(`${operation}错误:`, error)
  
  const errorMessage = formatErrorMessage(error, operation)
  
  if (showNotification) {
    showErrorNotification(error, `${operation}失败`, defaultMessage)
  } else if (showMessage) {
    showErrorMessage(error, errorMessage)
  }
  
  if (onError && typeof onError === 'function') {
    onError(error, errorMessage)
  }
  
  return errorMessage
}

/**
 * 常见HTTP状态码的中文描述
 */
export const HTTP_STATUS_MESSAGES = {
  400: '请求参数错误',
  401: '未授权访问',
  403: '禁止访问',
  404: '资源不存在',
  405: '请求方法不允许',
  408: '请求超时',
  409: '资源冲突',
  413: '请求体过大',
  422: '请求参数验证失败',
  429: '请求过于频繁',
  500: '服务器内部错误',
  502: '网关错误',
  503: '服务不可用',
  504: '网关超时'
}

/**
 * 根据HTTP状态码获取友好的错误描述
 * @param {number} status - HTTP状态码
 * @returns {string} 错误描述
 */
export function getStatusMessage(status) {
  return HTTP_STATUS_MESSAGES[status] || `HTTP错误 ${status}`
} 