// 定义不同环境的配置
const config = {
  development: {
    baseUrl: 'http://localhost:8001'
  },
  production: {
    baseUrl: 'http://api.example.com'
  },
  test: {
    baseUrl: 'http://localhost:8001'
  }
};

// 使用 Vite 的环境变量确定当前环境
const env = import.meta.env.MODE || 'development';

// 导出基础URL
export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || config[env].baseUrl;

// 创建API接口路径
export const apiUrls = {
  // 文档相关接口
  documents: {
    // 获取文档列表
    list: `${apiBaseUrl}/documents`,
    // 根据ID获取文档
    get: (documentId) => `${apiBaseUrl}/documents/${documentId}.json`,
    // 获取文档预览
    preview: (documentId) => `${apiBaseUrl}/documents/${documentId}/preview`,
    // 删除文档
    delete: (documentId) => `${apiBaseUrl}/documents/${documentId}`
  },
  
  // 文件处理相关接口
  files: {
    // 加载文件
    load: `${apiBaseUrl}/load`,
    // 解析文件
    parse: `${apiBaseUrl}/parse`,
    // 分块文件
    chunk: `${apiBaseUrl}/chunk`,
    // 向量化文件
    embed: `${apiBaseUrl}/embed`,
    // 索引文件
    index: `${apiBaseUrl}/index`,
    // 搜索
    search: `${apiBaseUrl}/search`
  }
};

// 日志当前环境和基础URL
console.log('Current MODE:', env);
console.log('API Base URL:', apiBaseUrl);

export default {
  baseUrl: apiBaseUrl,
  urls: apiUrls
}; 