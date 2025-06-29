<template>
  <div
    style="width: 96%; height: calc(90vh - 56px); overflow-y: auto; overflow-x: hidden; padding: 24px; background-color: #f5f7fa; display: flex; flex-direction: column;">

    <div style="display: flex; width: 100%; flex: 1; gap: 20px;">
      <!-- 左侧：配置部分 -->
      <div style="width: 25%; min-width: 300px; max-width: 350px;">
        <el-card style="width: 100%; height: calc(90vh - 104px); overflow-x: hidden;" shadow="hover">
          <div style="display: flex; flex-direction: column; gap: 8px;">

            <!-- 嵌入文件 -->
            <div style="margin-bottom: 8px;">
              <div style="margin-bottom: 4px; font-size: 14px; color: #606266;">嵌入文件</div>
              <el-select v-model="embeddingFile" placeholder="选择嵌入文件" style="width: 100%;">
                <el-option label="选择文件..." value="" disabled></el-option>
                <el-option v-for="file in embeddedFiles" :key="file.name" :label="file.displayName"
                  :value="file.name" />
              </el-select>
            </div>

            <!-- 向量数据库 -->
            <div style="margin-bottom: 8px;">
              <div style="margin-bottom: 4px; font-size: 14px; color: #606266;">向量数据库</div>
              <el-select v-model="selectedProvider" style="width: 100%;" @change="handleProviderChange">
                <el-option v-for="provider in providers" :key="provider.id" :label="provider.name"
                  :value="provider.id" />
              </el-select>
            </div>

            <!-- 索引模式 -->
            <div style="margin-bottom: 8px;">
              <div style="margin-bottom: 4px; font-size: 14px; color: #606266;">索引模式</div>
              <el-select v-model="indexConfig.indexType" style="width: 100%;">
                <el-option v-for="mode in availableIndexModes" :key="mode" :label="mode.toUpperCase()" :value="mode" />
              </el-select>
            </div>

            <!-- 建立索引按钮 -->
            <div style="margin-top: 8px; margin-bottom: 16px;">
              <el-button type="primary" style="width: 100%;" @click="handleStartIndexing" :loading="loading"
                :disabled="!embeddingFile">
                建立索引
              </el-button>
            </div>

            <!-- 集合组（集合选择框和相关按钮） -->
            <div style="margin-top: 8px; border-top: 1px dashed #DCDFE6; padding-top: 16px;">

              <!-- 集合选择 -->
              <div style="margin-bottom: 8px;">
                <div style="margin-bottom: 4px; font-size: 14px; color: #606266;">集合</div>
                <el-select v-model="selectedCollection" placeholder="选择集合" style="width: 100%;">
                  <el-option label="选择集合..." value="" disabled></el-option>
                  <el-option v-for="collection in collections" :key="collection.id"
                    :label="`${collection.name} (${collection.count} 文档)`" :value="collection.id" />
                </el-select>
              </div>

              <!-- 集合操作按钮 -->
              <div style="display: flex; justify-content: center; margin-top: 8px; gap: 8px;">
                <el-button type="primary" style="width: 45%;" @click="handleDisplayCollection"
                  :disabled="!selectedCollection">
                  显示集合
                </el-button>

                <el-button type="danger" style="width: 45%;" @click="handleDeleteCollection"
                  :disabled="!selectedCollection">
                  删除集合
                </el-button>
              </div>
            </div>

            <!-- 状态信息 -->
            <div v-if="indexStatus" style="margin-top: 16px; padding: 12px; border-radius: 4px; font-size: 14px;"
              :class="indexStatus.includes('错误') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'">
              {{ indexStatus }}
            </div>
          </div>
        </el-card>
      </div>

      <!-- 右侧：索引信息部分 -->
      <div style="flex: 1; min-width: 0; max-width: calc(100% - 370px);">
        <el-card shadow="hover"
          style="width: 95%; height: calc(90vh - 104px); display: flex; flex-direction: column; overflow-x: hidden;">
          <template #header>
            <div class="flex justify-between items-center">
              <span class="font-medium">索引信息</span>
            </div>
          </template>

          <div style="display: flex; flex-direction: column; flex: 1; overflow: hidden; height: 100%;">
            <!-- 预览内容 -->
            <div
              style="width: 100%; text-align: left; display: flex; flex-direction: column; height: 100%; overflow: auto;">
              <!-- 右侧：索引信息部分 -->
              <div v-if="previewContent"
                style="padding: 16px; border-radius: 4px; background-color: #f7f7f7; border: 1px solid #e4e7ed; flex: 0 0 auto; width: calc(100% - 32px); margin: 0 auto;">
                <div style="padding: 0 0 10px 0; border-bottom: 1px solid #ebeef5;">
                  <h4 style="margin: 0; font-size: 16px; font-weight: 500; color: #303133;">索引结果</h4>
                </div>
                <div style="color: #606266; font-size: 13px; line-height: 1.5; margin-top: 12px;">
                  <div class="doc-info-compact">
                    <div class="info-item">
                      <span class="info-label">数据库:</span>
                      <span class="info-value">{{ indexingResult?.database || indexConfig.database }}</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">索引模型:</span>
                      <span class="info-value">{{ indexingResult?.index_mode || indexConfig.indexType }}</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">集合名称:</span>
                      <span class="info-value">{{ indexingResult?.collection_name || '未定义' }}</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">向量总数:</span>
                      <span class="info-value">{{ indexingResult?.total_vectors || totalVectors }} 个</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">索引大小:</span>
                      <span class="info-value">{{ indexingResult?.index_size || '未知' }}</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">处理时间:</span>
                      <span class="info-value">{{ indexingResult?.processing_time ? `${indexingResult.processing_time}s`
                        : '未知'
                        }}</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">创建时间:</span>
                      <span class="info-value">{{ formatDate(indexingResult?.created_at) }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 未选择内容时的提示 -->
              <div v-if="!previewContent && !loading">
                <el-empty description="尚未创建或选择索引" :image-size="120">
                  <template #image>
                    <el-icon style="font-size: 60px; color: #909399;">
                      <Document />
                    </el-icon>
                  </template>
                  <template #description>
                    <div style="text-align: center;">
                      <p style="margin: 8px 0; font-size: 16px; color: #606266;">尚未创建或选择索引</p>
                      <p style="margin: 8px 0; font-size: 14px; color: #909399;">
                        请在左侧选择嵌入文件并建立索引<br>或从已有集合中选择一个进行查看
                      </p>
                    </div>
                  </template>
                </el-empty>
              </div>

              <!-- 加载中提示 -->
              <div v-if="loading"
                style="display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 40px 0;">
                <el-skeleton :rows="8" animated style="width: 100%;" />
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Document, Delete, Plus, RefreshRight } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { apiBaseUrl } from '@/config/api'
import { handleError } from '@/utils/errorHandler'

// 数据库和索引模式的配置
const dbConfigs = {
  pinecone: {
    modes: ['standard', 'hybrid'],
    name: 'Pinecone'
  },
  milvus: {
    modes: ['flat', 'ivf_flat', 'ivf_sq8', 'hnsw'],
    name: 'Milvus'
  },
  qdrant: {
    modes: ['hnsw', 'custom'],
    name: 'Qdrant'
  },
  weaviate: {
    modes: ['hnsw', 'flat'],
    name: 'Weaviate'
  },
  chroma: {
    modes: ['hnsw', 'standard'],
    name: 'Chroma'
  },
  faiss: {
    modes: ['flat', 'ivf', 'hnsw'],
    name: 'FAISS'
  }
}

// 嵌入文件和集合
const embeddingFile = ref('')
const embeddedFiles = ref([])
const collections = ref([])
const selectedCollection = ref('')
const providers = ref([])
const selectedProvider = ref('milvus')
const indexingResult = ref(null)

// 获取当前数据库可用的索引模式
const availableIndexModes = computed(() => {
  return dbConfigs[selectedProvider.value]?.modes || []
})

// 状态变量
const loading = ref(false)
const processingIndex = ref(false)
const indexStatus = ref('')
const loadedDocuments = ref([])
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const activeTab = ref('preview')
const previewUrl = ref('')

// 索引配置
const indexConfig = ref({
  database: 'milvus',
  indexType: 'flat',
  metric: 'cosine',
  batchSize: 1000,
  concurrency: 4,
})

// 监听提供商变化，自动选择模式
watch(() => selectedProvider.value, (newProvider) => {
  indexConfig.value.database = newProvider
  if (dbConfigs[newProvider] && dbConfigs[newProvider].modes.length > 0) {
    indexConfig.value.indexType = dbConfigs[newProvider].modes[0]
  }
})

// 模拟数据
const files = ref([
  {
    id: 1,
    name: '产品说明书.pdf',
    type: 'PDF',
    vectors: 15,
    indexed: 0,
    status: 'ready'
  },
  {
    id: 2,
    name: '技术文档.docx',
    type: 'Word',
    vectors: 8,
    indexed: 0,
    status: 'ready'
  },
  {
    id: 3,
    name: '用户手册.pdf',
    type: 'PDF',
    vectors: 20,
    indexed: 0,
    status: 'ready'
  }
])

// 更新总数
total.value = files.value.length

// 过滤后的文件列表
const filteredFiles = computed(() => {
  if (!searchQuery.value) return files.value
  return files.value.filter(file =>
    file.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

// 预览内容状态
const previewContent = ref(null)
const totalVectors = computed(() => {
  return files.value.reduce((sum, file) => sum + file.vectors, 0)
})

// 格式化日期
const formatDate = (timestamp) => {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 方法
const getStatusType = (status) => {
  const types = {
    ready: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    ready: '待处理',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || '未知'
}

// 获取嵌入文件列表
const fetchEmbeddedFiles = async () => {
  
  try {
    const response = await axios.get(`${apiBaseUrl}/list-embedded`)
    if (response.data && Array.isArray(response.data.documents)) {
      embeddedFiles.value = response.data.documents.map(doc => ({
        ...doc,
        id: doc.name,
        displayName: doc.name
      }))
    } else {
      console.error('嵌入文件格式不正确:', response.data)
      embeddedFiles.value = []
    }
  } catch (error) {
    console.error('获取嵌入文件列表失败:', error)
    indexStatus.value = '错误: 加载嵌入文件失败'
  } finally {
  }
}

// 获取集合列表
const fetchCollections = async () => {
  try {
    const response = await axios.get(`${apiBaseUrl}/collections/${selectedProvider.value}`)
    if (response.data && response.data.collections) {
      collections.value = response.data.collections
    } else {
      collections.value = []
    }
  } catch (error) {
    console.error('获取集合列表失败:', error)
  } finally {
  }
}

// 获取提供商列表
const fetchProviders = async () => {
  try {
    const response = await axios.get(`${apiBaseUrl}/providers`)
    if (response.data && Array.isArray(response.data.providers)) {
      providers.value = response.data.providers
    } else {
      // 如果API不可用，使用本地配置
      providers.value = Object.keys(dbConfigs).map(key => ({
        id: key,
        name: dbConfigs[key].name || key
      }))
    }
  } catch (error) {
    console.error('获取提供商列表失败:', error)
    // 如果API不可用，使用本地配置
    providers.value = Object.keys(dbConfigs).map(key => ({
      id: key,
      name: dbConfigs[key].name || key
    }))
  }
}

// 提供商变更处理
const handleProviderChange = async (newProvider) => {
  indexConfig.value.database = newProvider
  await fetchCollections()
}

// 开始索引处理
const handleStartIndexing = async () => {
  if (!embeddingFile.value) {
    indexStatus.value = '错误: 请先选择一个嵌入文件'
    return
  }

  loading.value = true
  processingIndex.value = true
  indexStatus.value = '正在处理中...'

  try {
    // 构建请求参数
    const params = {
      fileId: embeddingFile.value,  // 使用文件ID
      vectorDb: selectedProvider.value,  // 向量数据库提供商
      indexMode: indexConfig.value.indexType  // 索引模式
    }

    console.log('索引处理参数:', params)

    // 发送索引处理请求
    const url = `${apiBaseUrl}/index`
    const response = await axios.post(url, params, {
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: 60000
    })

    console.log('索引处理响应:', response.data)

    // 等待1秒，让后端有时间处理完成
    await new Promise(resolve => setTimeout(resolve, 1000))

    // 处理完成后的操作
    indexStatus.value = '索引处理完成'

    // 3秒后清除成功状态
    setTimeout(() => {
      if (indexStatus.value === '索引处理完成') {
        indexStatus.value = ''
      }
    }, 3000)

    // 显示处理结果
    ElMessage.success('文档索引处理完成')
    loading.value = false

    // 刷新集合列表
    await fetchCollections()

    // 切换到预览模式并显示索引结果
    if (response.data) {
      indexingResult.value = {
        database: selectedProvider.value,
        collection_name: response.data.collection_name,
        total_vectors: response.data.total_vectors,
        index_size: formatSize(response.data.index_size || 0),
        index_mode: response.data.index_mode,
        processing_time: response.data.processing_time,
        created_at: new Date().toISOString()
      }
      previewContent.value = true
    }

  } catch (error) {
          loading.value = false
      console.error('索引处理失败:', error)
      const errorMessage = handleError(error, { operation: '索引处理' })
      indexStatus.value = `错误: 索引处理失败 - ${errorMessage}`
  } finally {
    processingIndex.value = false
  }
}

// 显示集合详情
const handleDisplayCollection = async () => {
  if (!selectedCollection.value) {
    ElMessage.warning('请先选择集合')
    return
  }

  try {
    const response = await axios.get(`${apiBaseUrl}/collections/${selectedProvider.value}/${selectedCollection.value}`)
    const data = response.data

    // 设置索引结果
    indexingResult.value = {
      database: selectedProvider.value,
      collection_name: data.name,
      total_vectors: data.num_entities || 0,
      index_size: formatSize(data.index_size || 0),
      index_mode: data.index_type || indexConfig.value.indexType,
      processing_time: data.processing_time,
      created_at: data.created_at
    }

    // 设置预览内容
    previewContent.value = true

    ElMessage.success('已加载集合信息')
  } catch (error) {
    console.error('获取集合详情失败:', error)
            const errorMessage = handleError(error, { operation: '获取集合详情' })
        indexStatus.value = '错误: ' + errorMessage
  } finally {
    
  }
}

// 删除集合
const handleDeleteCollection = () => {
  if (!selectedCollection.value) {
    ElMessage.warning('请先选择集合')
    return
  }

  ElMessageBox.confirm(
    `确定要删除集合 "${selectedCollection.value}" 吗？此操作不可恢复！`,
    '警告',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger'
    }
  ).then(async () => {
    try {
      await axios.delete(`${apiBaseUrl}/collections/${selectedProvider.value}/${selectedCollection.value}`)
      selectedCollection.value = ''
      await fetchCollections()
      previewContent.value = null
      indexingResult.value = null
      ElMessage.success('集合已删除')
    } catch (error) {
      console.error('删除集合失败:', error)
      const errorMessage = handleError(error, { operation: '删除集合' })
      indexStatus.value = '错误: ' + errorMessage
    } finally {
      
    }
  }).catch(() => { })
}

// 格式化文件大小
const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 页面加载时执行
onMounted(() => {
  fetchProviders()
  fetchEmbeddedFiles()
  fetchCollections()

  // 初始默认不显示预览内容
  previewContent.value = null
})
</script>

<style scoped>
/* 状态信息样式 */
.bg-red-100 {
  background-color: #fef0f0;
  border: 1px solid #fde2e2;
}

.text-red-700 {
  color: #f56c6c;
}

.bg-green-100 {
  background-color: #f0f9eb;
  border: 1px solid #e1f3d8;
}

.text-green-700 {
  color: #67c23a;
}

/* 卡片内容区域 */
:deep(.el-card__body) {
  padding: 16px;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden !important;
}

/* 表格样式 */
:deep(.el-table) {
  --el-table-border-color: #e4e7ed;
  --el-table-header-background-color: #f5f7fa;
  overflow-x: hidden !important;
}

:deep(.el-table__body-wrapper) {
  overflow-x: hidden !important;
}

:deep(.el-table__inner-wrapper) {
  overflow-x: hidden !important;
}

/* 滚动条样式 */
:deep(::-webkit-scrollbar) {
  width: 10px !important;
  height: 0 !important;
  display: block !important;
  visibility: visible !important;
}

:deep(::-webkit-scrollbar-thumb) {
  background: #909399 !important;
  border-radius: 5px !important;
  border: 2px solid #fff !important;
}

:deep(::-webkit-scrollbar-track) {
  background: #fff !important;
  border-radius: 5px !important;
  visibility: visible !important;
  display: block !important;
}

:deep(::-webkit-scrollbar-corner) {
  background: #f5f7fa !important;
}

/* 全局禁用水平滚动条 */
:deep(::-webkit-scrollbar-horizontal) {
  display: none !important;
  height: 0 !important;
  visibility: hidden !important;
}

/* 样式工具类 */
.flex {
  display: flex;
}

.justify-between {
  justify-content: space-between;
}

.items-center {
  align-items: center;
}

.font-medium {
  font-weight: 500;
  font-size: 16px;
  color: #303133;
}

/* 紧凑型索引信息样式 */
.doc-info-compact {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px 20px;
  margin-top: 10px;
}

.info-item {
  display: flex;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px dashed #ebeef5;
}

.info-label {
  color: #909399;
  margin-right: 8px;
  min-width: 75px;
  font-size: 13px;
}

.info-value {
  color: #303133;
  font-weight: 500;
  font-size: 13px;
}

/* 表单项样式 */
:deep(.el-form-item) {
  margin-bottom: 16px;
}

:deep(.el-form-item__label) {
  font-size: 14px;
  color: #606266;
  padding-bottom: 4px;
}

:deep(.el-select) {
  width: 100%;
}
</style>