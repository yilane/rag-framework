<template>
  <div style="width: 96%; height: calc(90vh - 56px); overflow-y: auto; overflow-x: hidden; padding: 24px; background-color: #f5f7fa; display: flex; flex-direction: column;">
    
    <div style="display: flex; width: 100%; flex: 1; gap: 20px;">
      <!-- 左侧：配置部分 -->
      <div style="width: 25%; min-width: 300px; max-width: 350px;">
        <el-card style="width: 100%; height: calc(90vh - 104px); overflow-y: auto; overflow-x: hidden;" shadow="hover">
          <div style="display: flex; flex-direction: column; gap: 24px;">
            <div>
              <!-- 嵌入配置 -->
              <div style="margin-bottom: 24px;">
                <!-- 文档选择 -->
                <div style="margin-bottom: 16px;">
                  <div style="margin-bottom: 8px; font-size: 14px; color: #606266;">选择文档</div>
                  <div style="margin-bottom: 8px; font-size: 12px; color: #909399;">
                    可用文档数量: {{ availableDocs.length }}
                  </div>
                  <el-select 
                    v-model="selectedDoc" 
                    placeholder="请选择文档" 
                    style="width: 100%;"
                    :loading="loadingDocuments"
                  >
                    <el-option
                      v-for="doc in availableDocs"
                      :key="doc.id"
                      :label="`${doc.name} (${doc.type})`"
                      :value="doc.name"
                    />
                  </el-select>
                </div>
                
                <!-- 提供商选择 -->
                <div style="margin-bottom: 16px;">
                  <div style="margin-bottom: 8px; font-size: 14px; color: #606266;">嵌入提供商</div>
                  <el-select 
                    v-model="embeddingConfig.provider" 
                    placeholder="请选择嵌入提供商" 
                    style="width: 100%;"
                  >
                    <el-option label="OpenAI" value="openai" />
                    <el-option label="Bedrock" value="bedrock" />
                    <el-option label="HuggingFace" value="huggingface" />
                  </el-select>
                </div>
                
                <!-- 模型选择 -->
                <div style="margin-bottom: 16px;">
                  <div style="margin-bottom: 8px; font-size: 14px; color: #606266;">嵌入模型</div>
                  <el-select 
                    v-model="embeddingConfig.model" 
                    placeholder="请选择嵌入模型" 
                    style="width: 100%;"
                  >
                    <el-option
                      v-for="model in currentModelOptions"
                      :key="model.value"
                      :label="model.label"
                      :value="model.value"
                    />
                  </el-select>
                </div>
                
                <!-- 开始处理按钮 -->
                <div style="margin-top: 16px; display: flex; justify-content: center;">
                  <el-button 
                    type="primary" 
                    style="width: 100%;" 
                    @click="handleStartEmbedding"
                    :disabled="!selectedDoc"
                  >
                    生成嵌入
                  </el-button>
                </div>
                
                <!-- 状态信息 -->
                <div v-if="statusMessage" class="status-message" 
                  :class="statusMessage.includes('错误') || statusMessage.includes('失败') ? 'error-message' : 'success-message'"
                  style="margin-top: 16px; padding: 12px; border-radius: 4px; font-size: 14px;">
                  {{ statusMessage }}
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </div>
      
      <!-- 右侧：文件列表部分 -->
      <div style="flex: 1; min-width: 0; max-width: calc(100% - 370px);">
        <el-card shadow="hover" style="width: 95%; height: calc(90vh - 104px); display: flex; flex-direction: column; overflow-x: hidden;">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <el-button-group>
                <el-button :type="activeTab === 'preview' ? 'primary' : 'default'" 
                           :plain="activeTab === 'management'"
                           @click="activeTab = 'preview'">
                  文档预览
                </el-button>
                <el-button :type="activeTab === 'management' ? 'primary' : 'default'"
                           :plain="activeTab === 'preview'"
                           @click="activeTab = 'management'">
                  文档管理
                </el-button>
              </el-button-group>
            </div>
          </template>
          
          <!-- 预览模式 -->
          <div v-if="activeTab === 'preview'" style="display: flex; flex-direction: column; flex: 1; overflow: hidden; height: 100%;">
            <div v-if="embeddings && embeddings.length > 0" class="preview-container">
              <!-- 文档内容标题 -->
              <div style="padding: 16px 20px; border-bottom: 1px solid #ebeef5; flex-shrink: 0;">
                <h2 style="margin: 0; font-size: 20px; font-weight: 500; color: #303133;">嵌入结果</h2>
              </div>
              
              <!-- 嵌入内容列表 -->
              <div class="content-items" style="padding: 20px; overflow-y: auto; max-height: calc(100vh - 220px);">
                <div 
                  v-for="(embedding, index) in embeddings" 
                  :key="index"
                  style="border-radius: 4px; overflow: hidden; border: 1px solid #e4e7ed; margin-bottom: 16px; background-color: #fff; position: relative; padding: 16px;"
                >
                  <div style="font-weight: 500; font-size: 14px; color: #606266; margin-bottom: 8px;">
                    块 {{ embedding.metadata?.chunk_id || index + 1 }} / {{ embedding.metadata?.total_chunks || embeddings.length }}
                  </div>
                  <div style="font-size: 12px; color: #909399; margin-bottom: 8px;">
                    文档: {{ embedding.metadata?.filename || embedding.metadata?.document_name || 'N/A' }} | 
                    页码: {{ embedding.metadata?.page_number || 'N/A' }} | 
                    页面范围: {{ embedding.metadata?.page_range || 'N/A' }}
                  </div>
                  <div style="font-size: 12px; color: #909399; margin-bottom: 12px;">
                    模型: {{ embedding.metadata?.embedding_model || 'N/A' }} | 
                    提供商: {{ embedding.metadata?.embedding_provider || 'N/A' }} | 
                    维度: {{ embedding.metadata?.vector_dimension || 'N/A' }} |
                    时间: {{ embedding.metadata?.embedding_timestamp ? new Date(embedding.metadata.embedding_timestamp).toLocaleString() : 'N/A' }}
                  </div>
                  <div style="margin-top: 8px;">
                    <div style="font-weight: 500; color: #303133; font-size: 13px; margin-bottom: 4px;">内容:</div>
                    <div style="color: #606266; font-size: 13px; line-height: 1.5; white-space: pre-wrap;">{{ embedding.metadata?.content || 'N/A' }}</div>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="empty-container">
              <el-empty description="选择一个文档并生成嵌入或查看现有嵌入" />
            </div>
          </div>
          
          <!-- 管理模式 -->
          <div v-else style="flex: 1; display: flex; flex-direction: column; overflow: hidden; height: 100%;">
            <el-input
              v-model="searchQuery"
              placeholder="搜索文件..."
              style="width: 100%; margin-bottom: 16px;"
              clearable
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            
            <div style="flex: 1; overflow-y: auto; overflow-x: hidden; height: calc(100% - 60px);">
              <el-table 
                :data="filteredFiles" 
                style="width: 100%;" 
                border 
                height="100%" 
                :show-overflow-tooltip="true"
                v-loading="loading"
              >
                <el-table-column label="文件名" min-width="200">
                  <template #default="{ row }">
                    <div style="display: flex; align-items: center;">
                      <el-icon style="margin-right: 8px;"><Document /></el-icon>
                      <span>{{ row.name }}</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="嵌入模型" min-width="180" align="center">
                  <template #default="{ row }">
                    {{ row.metadata?.embedding_model || 'N/A' }}
                  </template>
                </el-table-column>
                <el-table-column label="提供商" width="120" align="center">
                  <template #default="{ row }">
                    {{ row.metadata?.embedding_provider || 'N/A' }}
                  </template>
                </el-table-column>
                <el-table-column label="向量维度" width="100" align="center">
                  <template #default="{ row }">
                    {{ row.metadata?.vector_dimension || 'N/A' }}
                  </template>
                </el-table-column>
                <el-table-column label="处理时间" min-width="150" align="center">
                  <template #default="{ row }">
                    {{ row.metadata?.embedding_timestamp ? new Date(row.metadata.embedding_timestamp).toLocaleString() : '未知' }}
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="150" align="center" fixed="right">
                  <template #default="{ row }">
                    <el-button link type="primary" @click="handleViewEmbedding(row)">查看</el-button>
                    <el-button link type="danger" @click="handleDeleteEmbedding(row)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            
            <div style="display: flex; align-items: center; margin-top: 16px;">
              <span style="font-size: 14px; color: #606266;">共 {{ total }} 条</span>
              <el-select v-model="pageSize" size="small" style="width: 120px; margin: 0 8px;">
                <el-option label="10条/页" :value="10" />
                <el-option label="20条/页" :value="20" />
                <el-option label="50条/页" :value="50" />
              </el-select>
              <div style="margin-left: auto;">
                <el-pagination
                  layout="prev, pager, next"
                  :total="total"
                  :page-size="pageSize"
                  v-model:current-page="currentPage"
                  small
                />
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 进度对话框 -->
    <el-dialog
      v-model="progressVisible"
      title="嵌入进度"
      width="500px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
    >
      <el-progress 
        :percentage="progress" 
        :status="progressStatus"
        :stroke-width="15"
      />
      <div style="margin-top: 16px; text-align: center; color: #909399;">
        {{ progressText }}
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleCancel">取消</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Document, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { apiBaseUrl } from '@/config/api' // 引入API基础URL

// 可用文档列表
const availableDocs = ref([])
const loadingDocuments = ref(false)
const selectedDoc = ref('')

// 模型选项映射
const modelOptionsMap = {
  openai: [
    { label: 'text-embedding-3-large', value: 'text-embedding-3-large' },
    { label: 'text-embedding-3-small', value: 'text-embedding-3-small' },
    { label: 'text-embedding-ada-002', value: 'text-embedding-ada-002' }
  ],
  bedrock: [
    { label: 'cohere.embed-english-v3', value: 'cohere.embed-english-v3' },
    { label: 'cohere.embed-multilingual-v3', value: 'cohere.embed-multilingual-v3' }
  ],
  huggingface: [
    { label: 'sentence-transformers/all-mpnet-base-v2', value: 'sentence-transformers/all-mpnet-base-v2' },
    { label: 'all-MiniLM-L6-v2', value: 'all-MiniLM-L6-v2' },
    { label: 'google-bert/bert-base-uncased', value: 'google-bert/bert-base-uncased' },
    { label: 'BAAI/bge-small-zh-v1.5', value: 'BAAI/bge-small-zh-v1.5' }
  ]
}

// 状态变量
const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const progressVisible = ref(false)
const progress = ref(0)
const progressStatus = ref('')
const progressText = ref('')
const activeTab = ref('preview')
const previewUrl = ref('')

// 向量化配置
const embeddingConfig = ref({
  provider: 'openai',
  model: 'text-embedding-3-small'
})

// 根据当前选择的提供商获取对应的模型选项
const currentModelOptions = computed(() => {
  return modelOptionsMap[embeddingConfig.value.provider] || []
})

// 监听提供商变化，自动选择该提供商下的第一个模型
watch(() => embeddingConfig.value.provider, (newProvider) => {
  if (modelOptionsMap[newProvider] && modelOptionsMap[newProvider].length > 0) {
    embeddingConfig.value.model = modelOptionsMap[newProvider][0].value
  }
})

// 嵌入数据
const embeddings = ref(null)
const embeddedDocs = ref([])
const statusMessage = ref('')

// 页面加载时获取文档列表
onMounted(() => {
  fetchAvailableDocs()
  fetchEmbeddedDocs()
})

// 获取可用文档列表
const fetchAvailableDocs = async () => {
  loadingDocuments.value = true
  
  try {
    const response = await axios.get(`${apiBaseUrl}/documents?type=all`)
    console.log('获取文档列表响应:', response.data)
    
    if (response.data && Array.isArray(response.data.documents)) {
      availableDocs.value = response.data.documents
    } else {
      console.error('文档格式不正确:', response.data)
      availableDocs.value = []
    }
  } catch (error) {
    console.error('获取文档列表失败:', error)
    availableDocs.value = []
  } finally {
    loadingDocuments.value = false
  }
}

// 获取已嵌入文档列表
const fetchEmbeddedDocs = async () => {
  loading.value = true
  
  try {
    const response = await axios.get(`${apiBaseUrl}/list-embedded`)
    console.log('获取嵌入文档列表响应:', response.data)
    
    if (response.data && Array.isArray(response.data.documents)) {
      embeddedDocs.value = response.data.documents
      files.value = embeddedDocs.value
      total.value = files.value.length
    } else {
      console.error('嵌入文档格式不正确:', response.data)
      embeddedDocs.value = []
      files.value = []
      total.value = 0
    }
  } catch (error) {
    console.error('获取嵌入文档列表失败:', error)
    embeddedDocs.value = []
    files.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// 模拟数据
const files = ref([
  {
    id: 1,
    name: '产品说明书.pdf',
    type: 'PDF',
    chunks: 15,
    vectors: 0,
    status: 'ready'
  },
  {
    id: 2,
    name: '技术文档.docx',
    type: 'Word',
    chunks: 8,
    vectors: 0,
    status: 'ready'
  },
  {
    id: 3,
    name: '用户手册.pdf',
    type: 'PDF',
    chunks: 20,
    vectors: 0,
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

// 开始生成嵌入
const handleStartEmbedding = async () => {
  if (!selectedDoc.value) {
    ElMessage.warning('请先选择一个文档')
    return
  }
  
  // 调用嵌入API
  progressVisible.value = true
  progress.value = 0
  progressStatus.value = ''
  progressText.value = '正在处理文档嵌入...'
  statusMessage.value = '处理中...'
  
  try {
    // 发送嵌入请求
    const response = await axios.post(`${apiBaseUrl}/embed`, {
      documentId: selectedDoc.value,
      provider: embeddingConfig.value.provider,
      model: embeddingConfig.value.model
    })
    
    console.log('嵌入生成响应:', response.data)
    
    // 处理响应
    progress.value = 100
    progressStatus.value = 'success'
    progressText.value = '嵌入生成完成'
    
    // 设置嵌入结果
    embeddings.value = response.data.embeddings
    statusMessage.value = `嵌入生成成功! 保存到: ${response.data.filepath || ''}`
    
    // 刷新嵌入文档列表
    fetchEmbeddedDocs()
    
    // 自动切换到预览标签
    activeTab.value = 'preview'
    
    setTimeout(() => {
      progressVisible.value = false
      ElMessage.success('文档嵌入生成完成')
    }, 500)
  } catch (error) {
    console.error('嵌入处理失败:', error)
    progressStatus.value = 'exception'
    progressText.value = `处理失败: ${error.response?.data?.detail || error.message}`
    statusMessage.value = `错误: 生成嵌入失败 - ${error.response?.data?.detail || error.message}`
    
    setTimeout(() => {
      progressVisible.value = false
      ElMessage.error(`嵌入处理失败: ${error.response?.data?.detail || error.message}`)
    }, 2000)
  }
}

// 查看嵌入
const handleViewEmbedding = async (row) => {
  try {
    statusMessage.value = '加载嵌入中...'
    const response = await axios.get(`${apiBaseUrl}/embedded-docs/${row.name}`)
    
    embeddings.value = response.data.embeddings
    activeTab.value = 'preview'
    statusMessage.value = ''
    
    ElMessage.success(`已加载嵌入: ${row.name}`)
  } catch (error) {
    console.error('加载嵌入失败:', error)
    statusMessage.value = `错误: 加载嵌入失败 - ${error.message}`
    ElMessage.error(`加载嵌入失败: ${error.message}`)
  }
}

// 删除嵌入
const handleDeleteEmbedding = async (row) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除该嵌入文件吗？',
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const response = await axios.delete(`${apiBaseUrl}/embedded-docs/${row.name}`)
    
    statusMessage.value = '嵌入删除成功'
    await fetchEmbeddedDocs()
    
    // 如果当前正在预览这个嵌入，则清空预览
    if (embeddings.value && selectedDoc.value === row.name) {
      embeddings.value = null
    }
    
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除嵌入失败:', error)
      statusMessage.value = `错误: 删除嵌入失败 - ${error.message}`
      ElMessage.error(`删除失败: ${error.message}`)
    }
  }
}

const handleCancel = () => {
  ElMessageBox.confirm(
    '确定要取消嵌入过程吗？这将中断当前的处理。',
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    progressVisible.value = false
    progress.value = 0
    progressStatus.value = ''
    progressText.value = ''
    ElMessage.info('已取消嵌入过程')
  }).catch(() => {})
}

const handleSizeChange = (size) => {
  pageSize.value = size
}

const handleCurrentChange = (page) => {
  currentPage.value = page
}
</script>

<style scoped>
/* 预览容器 */
.preview-container {
  width: 100%;
  text-align: left;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: auto;
}

.preview-image {
  max-width: 90%;
  max-height: 70vh;
  margin: 0 auto;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

/* 空容器 */
.empty-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  overflow-y: auto;
  flex: 1;
}

/* 表格样式 */
.el-table {
  --el-table-border-color: #e4e7ed;
  --el-table-header-background-color: #f5f7fa;
}

/* 全局禁用水平滚动条 */
*::-webkit-scrollbar-horizontal {
  display: none !important;
  height: 0 !important;
  visibility: hidden !important;
}

::-webkit-scrollbar-corner {
  background: transparent !important;
  display: none !important;
}

/* Webkit浏览器的滚动条样式 */
::-webkit-scrollbar {
  width: 10px !important;
  height: 0 !important;
  display: block !important;
  visibility: visible !important;
}

::-webkit-scrollbar-thumb {
  background: #909399 !important;
  border-radius: 5px !important;
  border: 2px solid #fff !important;
}

::-webkit-scrollbar-track {
  background: #fff !important;
  border-radius: 5px !important;
  visibility: visible !important;
  display: block !important;
}

::-webkit-scrollbar-corner {
  background: #f5f7fa !important;
}
</style>

<style>
/* 全局滚动条样式，确保在Element Plus组件中也生效 */
.el-card__body {
  overflow-y: auto !important;
  overflow-x: hidden !important;
}

.el-table__body-wrapper::-webkit-scrollbar,
.el-scrollbar__wrap::-webkit-scrollbar {
  width: 12px !important;
  height: 0 !important;
  display: block !important;
}

/* 防止表格横向滚动 */
.el-table__body-wrapper,
.el-scrollbar__wrap {
  overflow-x: hidden !important;
}

.el-table {
  width: 100% !important;
  table-layout: fixed !important;
  overflow-x: hidden !important;
}

.el-table__inner-wrapper {
  overflow-x: hidden !important;
}

.el-table__body {
  width: 100% !important;
  overflow-x: hidden !important;
}

.el-table__header-wrapper,
.el-table__body-wrapper {
  overflow-x: hidden !important;
}

.el-table .cell {
  word-break: break-all !important;
  white-space: normal !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

/* Element滚动条样式，禁用水平滚动条 */
.el-scrollbar__bar.is-horizontal {
  display: none !important;
}

/* 状态消息样式 */
.status-message {
  margin-top: 16px;
  padding: 12px;
  border-radius: 4px;
  font-size: 14px;
}

.error-message {
  background-color: #fef0f0;
  color: #f56c6c;
  border: 1px solid #fde2e2;
}

.success-message {
  background-color: #f0f9eb;
  color: #67c23a;
  border: 1px solid #e1f3d8;
}
</style> 