<template>
  <div style="width: 96%; height: calc(90vh - 56px); overflow-y: auto; overflow-x: hidden; padding: 24px; background-color: #f5f7fa; display: flex; flex-direction: column;">
    
    <div style="display: flex; width: 100%; flex: 1; gap: 20px;">
      <!-- 左侧：配置部分 -->
      <div style="width: 25%; min-width: 300px; max-width: 350px;">
        <el-card style="width: 100%; height: calc(90vh - 104px); overflow-y: auto; overflow-x: hidden;" shadow="hover">
          <div style="display: flex; flex-direction: column; gap: 24px;">
            <div>
              <!-- 文档选择部分 -->
              <div style="margin-bottom: 24px;">
                <div style="margin-bottom: 8px; font-size: 14px;">文档选择</div>
                <el-select 
                  v-model="chunkConfig.selectedDoc" 
                  placeholder="请选择文档" 
                  style="width: 100%; margin-bottom: 8px;"
                  :loading="loadingDocuments"
                >
                  <el-option
                    v-for="doc in loadedDocuments"
                    :key="doc.id"
                    :label="doc.displayName || doc.name"
                    :value="doc.id"
                  />
                </el-select>
                <div style="margin-top: 8px; color: #909399;" v-if="!chunkConfig.selectedDoc">未选择任何文档</div>
                <div style="margin-top: 8px; color: #606266;" v-else>已选择: {{ chunkConfig.selectedDoc }}</div>
              </div>
              
              <!-- 分块设置部分 -->
              <div style="margin-bottom: 24px;">
                <div style="margin-bottom: 8px; font-size: 14px;">分块方式</div>
                <el-select 
                  v-model="chunkConfig.mode" 
                  placeholder="请选择分块方式" 
                  style="width: 100%; margin-bottom: 16px;"
                >
                  <el-option label="按页分块" value="by_pages" />
                  <el-option label="固定大小" value="fixed_size" />
                  <el-option label="按段落" value="by_paragraphs" />
                  <el-option label="按句子" value="by_sentences" />
                </el-select>
                
                <div v-if="chunkConfig.mode === 'fixed_size'">
                  <div style="margin-bottom: 8px; font-size: 14px; color: #606266;">分块大小</div>
                  <el-input-number 
                    v-model="chunkConfig.chunkSize" 
                    :min="1000" 
                    :max="5000"
                    :step="100"
                    placeholder="请输入分块大小"
                    style="width: 100%; margin-bottom: 16px;"
                  >
                    <template #append>字符</template>
                  </el-input-number>
                  
                  <div style="margin-bottom: 8px; font-size: 14px; color: #606266;">重叠大小</div>
                  <el-input-number 
                    v-model="chunkConfig.overlapSize" 
                    :min="0" 
                    :max="100"
                    :step="10"
                    placeholder="请输入重叠大小"
                    style="width: 100%; margin-bottom: 16px;"
                  >
                    <template #append>字符</template>
                  </el-input-number>
                </div>
              </div>
              
              <!-- 开始处理按钮 -->
              <div style="margin-top: 16px; display: flex; justify-content: center;">
                <el-button type="primary" @click="handleStartChunk" :disabled="!chunkConfig.selectedDoc" :loading="processingChunk" style="width: 100%;">
                  开始处理
                </el-button>
              </div>
              
              <!-- 状态提示 -->
              <div v-if="chunkStatus" :class="[
                'chunk-status',
                {
                  'success': chunkStatus.includes('完成'),
                  'error': chunkStatus.includes('错误'),
                  'info': chunkStatus.includes('处理中'),
                  'warning': chunkStatus.includes('警告')
                }
              ]">
                {{ chunkStatus }}
              </div>
            </div>
          </div>
        </el-card>
      </div>
      
      <!-- 右侧：文件列表部分 -->
      <div style="flex: 1; min-width: 0; max-width: calc(100% - 370px);">
        <el-card shadow="hover" style="width: 95%; height: calc(90vh - 104px); display: flex; flex-direction: column; overflow-x: hidden;">
          <template #header>
            <div class="flex justify-between items-center">
              <el-button-group>
                <el-button :type="activeTab === 'preview' ? 'primary' : 'default'" 
                           :plain="activeTab === 'management'"
                           @click="activeTab = 'preview'">
                  文档预览
                </el-button>
                <el-button :type="activeTab === 'management' ? 'primary' : 'default'"
                           :plain="activeTab === 'preview'"
                           @click="activeTab = 'management'">
                  文档记录
                </el-button>
              </el-button-group>
            </div>
          </template>
          
          <!-- 预览模式 -->
          <div v-if="activeTab === 'preview'" style="display: flex; flex-direction: column; flex: 1; overflow: hidden; height: 100%;">
            <div v-if="loadedContent" style="width: 100%; text-align: left; display: flex; flex-direction: column; height: 100%; overflow: auto;">

              <!-- 文档信息 -->
              <div v-if="previewSubTab === 'content'" class="flex-1 overflow-auto">
                <!-- 文档内容标题 -->
                <div style="padding: 16px 20px; border-bottom: 1px solid #ebeef5; flex-shrink: 0;">
                  <h2 style="margin: 0; font-size: 20px; font-weight: 500; color: #303133;">文档内容</h2>
                </div>
                
                <!-- 文档信息卡片 -->
                <div style="padding: 16px 20px; border-bottom: 1px solid #ebeef5; background-color: #f5f7fa; flex-shrink: 0;">
                  <h3 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 500; color: #303133;">文档信息</h3>
                  <div style="color: #606266; font-size: 14px; line-height: 1.6;">
                    <p style="margin: 4px 0;">文件名: {{ loadedContent.filename || 'N/A' }}</p>
                    <p style="margin: 4px 0;">页数: {{ loadedContent.pageCount || 'N/A' }}</p>
                    <p style="margin: 4px 0;">分块数: {{ loadedContent.chunkCount || 'N/A' }}</p>
                    <p style="margin: 4px 0;">加载方法: {{ loadedContent.loadingMethod || 'N/A' }}</p>
                    <p style="margin: 4px 0;">分块方法: {{ loadedContent.mode || 'N/A' }}</p>
                    <p style="margin: 4px 0;">处理时间: {{ loadedContent.timestamp ? new Date(loadedContent.timestamp).toLocaleString() : 'N/A' }}</p>
                  </div>
                </div>

                <!-- 分块内容列表 -->
                <div 
                  class="chunks-container" 
                  style="
                    flex: 1; 
                    overflow-y: auto !important; 
                    padding-bottom: 20px; 
                    height: calc(100% - 220px) !important;
                    display: block !important;
                    min-height: 200px;
                  "
                >
                  <!-- 全局折叠控制 -->
                  <div style="display: flex; justify-content: flex-end; margin-bottom: 12px; padding: 16px 20px 0 20px;">
                    <el-button size="small" type="primary" plain @click="expandAllChunks">
                      <el-icon><ArrowDown /></el-icon> 展开全部
                    </el-button>
                    <el-button size="small" type="info" plain style="margin-left: 8px;" @click="collapseAllChunks">
                      <el-icon><ArrowUp /></el-icon> 折叠全部
                    </el-button>
                  </div>

                  <div class="chunk-list">
                    <div 
                      v-for="(chunk, index) in loadedContent.chunks" 
                      :key="chunk.id || index"
                      style="border-radius: 4px; overflow: hidden; border: 1px solid #e4e7ed; margin-bottom: 16px; background-color: #fff; position: relative;"
                    >
                      <div 
                        style="padding: 12px 16px; background-color: #f5f7fa; cursor: pointer; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e4e7ed;" 
                        :id="`chunk-${index}`"
                        @click="toggleChunk(index)"
                      >
                        <div style="font-size: 15px; font-weight: 500; color: #303133;">
                          分块 {{ index + 1 }}
                        </div>
                        <div class="flex items-center">
                          <span class="text-xs text-gray-500 mr-2" v-if="chunk.metadata">
                            页面: {{chunk.metadata.page_range || 'N/A'}} | 
                            字数: {{chunk.metadata.word_count || 'N/A'}}
                          </span>
                          <el-icon :style="{ transform: isChunkCollapsed(index) ? 'rotate(0deg)' : 'rotate(180deg)', transition: 'transform 0.3s' }">
                            <ArrowDown />
                          </el-icon>
                        </div>
                      </div>
                      <div 
                        v-show="!isChunkCollapsed(index)"
                        class="chunk-content"
                        :id="`chunk-content-${index}`"
                        ref="chunkContents"
                        @scroll="checkScrollPosition($event, index)"
                      >
                        <div>{{ typeof chunk === 'object' ? (chunk.content || chunk.text) : chunk }}</div>
                        <div v-if="hasMoreContent[index]" class="scroll-indicator">滚动查看更多</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 文档记录 -->
              <div v-else-if="previewSubTab === 'info'" class="flex flex-col w-full h-full">
                <h3 class="text-xl font-semibold mb-4">文档信息</h3>
                <div class="p-4 border rounded-lg bg-gray-50 w-full">
                  <div class="flex-grow">
                    <h4 class="font-medium text-lg">{{loadedContent.filename}}</h4>
                    <div class="text-sm text-gray-600 mt-2">
                      <p class="py-1">页数: {{loadedContent.pageCount || 'N/A'}}</p>
                      <p class="py-1">分块数: {{loadedContent.chunkCount || 'N/A'}}</p>
                      <p class="py-1">分块方法: {{loadedContent.mode || 'N/A'}}</p>
                      <p class="py-1">加载方法: {{loadedContent.loadingMethod || 'N/A'}}</p>
                      <p class="py-1">处理时间: {{loadedContent.timestamp ? new Date(loadedContent.timestamp).toLocaleString() : 'N/A'}}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 未选择文档时的提示 -->
            <div v-else style="display: flex; justify-content: center; align-items: center; height: 100%; overflow-y: auto; flex: 1;">
              <el-empty description="选择一个文档并创建块，以在此查看结果" />
            </div>
          </div>
          
          <!-- 管理模式 -->
          <div v-else style="flex: 1; display: flex; flex-direction: column; overflow-y: auto; overflow-x: hidden; height: 100%;">
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
                <el-table-column prop="pages" label="页数" width="80" align="center" />
                <el-table-column prop="chunks" label="块数" width="80" align="center" />
                <el-table-column prop="mode" label="处理方式" width="100" align="center">
                  <template #default="{ row }">
                    {{ getModeName(row.mode) }}
                  </template>
                </el-table-column>
                <el-table-column prop="uploadTime" label="创建时间" width="180" align="center" />
                <el-table-column label="操作" width="120" align="center">
                  <template #default="{ row }">
                    <el-button link type="primary" @click="handlePreview(row)">预览</el-button>
                    <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            
            <div style="display: flex; align-items: center; margin-top: 16px;">
              <span style="font-size: 14px; color: #606266;">Total {{ total }}</span>
              <el-select v-model="pageSize" size="small" style="width: 120px; margin: 0 8px;">
                <el-option label="10/page" :value="10" />
                <el-option label="20/page" :value="20" />
                <el-option label="50/page" :value="50" />
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

    <!-- 预览失败时的错误提示 -->
    <div v-if="previewError" class="absolute top-0 left-0 right-0 flex justify-center" style="z-index: 10;">
      <div class="bg-red-50 text-red-500 px-4 py-2 rounded-md flex items-center mt-2">
        <el-icon class="mr-2"><CircleClose /></el-icon>
        <span>{{ previewErrorMessage }}</span>
        <el-icon class="ml-4 cursor-pointer" @click="previewError = false"><Close /></el-icon>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted } from 'vue'
import { Document, Search, VideoPlay, ArrowDown, ArrowUp, CircleClose, Close, Setting } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { apiUrls, apiBaseUrl } from '@/config/api'

// 状态变量
const loading = ref(false)
const loadingDocuments = ref(false)
const processingChunk = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const activeTab = ref('preview')
const previewUrl = ref('')
const loadedContent = ref(null)
const collapsedChunks = ref({}) // 存储折叠状态的对象
const chunkContents = ref([]) // 引用分块内容元素
const hasMoreContent = ref({}) // 跟踪哪些分块有更多内容需要滚动
const loadedDocuments = ref([]) // 已加载的文档列表
const chunkStatus = ref('') // 分块处理状态信息
const previewSubTab = ref('content')
const configTab = ref('document')
const previewError = ref(false)
const previewErrorMessage = ref('获取预览内容失败')
const retryCount = ref(0)
const maxRetries = 3
const debugMode = ref(false) // 是否开启调试模式
const apiLogs = ref([]) // API调用日志
const maxLogs = 10 // 最大保存的日志数量

// 分块配置
const chunkConfig = ref({
  selectedDoc: '',
  chunkSize: 1000,
  overlapSize: 50,
  mode: 'by_pages' // 默认值从by_paragraph更改为by_pages
})

// 分块选项列表
const chunkingOptions = [
  { value: 'by_pages', label: '按页分块' },
  { value: 'fixed_size', label: '固定大小' },
  { value: 'by_paragraphs', label: '按段落' },
  { value: 'by_sentences', label: '按句子' },
]

// 模拟数据
const files = ref([])

// 更新总数
total.value = files.value.length

// 过滤后的文件列表
const filteredFiles = computed(() => {
  if (!searchQuery.value) return files.value
  return files.value.filter(file => 
    file.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

// 处理方式名称映射
const getModeName = (mode) => {
  const modes = {
    paragraph: '按段落',
    sentence: '按句子',
    fixed: '固定大小',
    by_pages: '按页分块',
    by_paragraphs: '按段落',
    by_sentences: '按句子',
    fixed_size: '固定大小'
  }
  return modes[mode] || mode
}

const handleCancel = () => {
  // progressVisible.value = false
  // progress.value = 0
  // progressStatus.value = ''
  // progressText.value = ''
}

// 获取已加载的文档列表
const fetchLoadedDocuments = async () => {
  loadingDocuments.value = true
  try {
    // 获取已加载（但未分块）的文档列表
    const url = `${apiBaseUrl}/documents?type=loaded`
    console.log('请求已加载文档列表URL:', url)
    
    const response = await axios.get(url)
    console.log('获取到的已加载文档列表:', response.data)
    
    if (response.data && Array.isArray(response.data.documents)) {
      // 处理接收到的数据
      loadedDocuments.value = response.data.documents.map(doc => {
        // 确保文档显示名称友好
        const displayName = doc.name.replace(/\.json$/, '')
        return {
          ...doc,
          name: displayName, 
          displayName: displayName.replace(/_pymupdf_\d+$/, ''), // 移除时间戳后缀，使显示更简洁
          originalName: doc.name // 保留原始名称以备使用
        }
      })
      
      console.log('处理后的已加载文档列表:', loadedDocuments.value)
    } else {
      console.warn('获取已加载文档列表: 响应格式不符合预期', response.data)
      loadedDocuments.value = []
    }
    
    // 记录API调用
    logApiCall('GET', url, {}, response.data)
    
    // 获取已分块的文档列表
    await fetchChunkedDocuments()
  } catch (error) {
    console.error('获取文档列表失败:', error)
    
    if (error.response) {
      console.error(`HTTP错误 ${error.response.status}: ${JSON.stringify(error.response.data)}`)
    }
    
    // 记录API调用错误
    logApiCall('GET', `${apiBaseUrl}/documents?type=loaded`, {}, null, error)
    
    ElMessage.error('获取文档列表失败')
    loadedDocuments.value = []
  } finally {
    loadingDocuments.value = false
  }
}

// 获取已分块的文档列表
const fetchChunkedDocuments = async () => {
  loading.value = true
  try {
    const response = await axios.get(`${apiBaseUrl}/documents?type=chunked`)
    
    if (!response.data || !Array.isArray(response.data.documents)) {
      console.error('无效的已分块文档数据:', response.data)
      return
    }
    
    console.log('获取到的分块文档列表:', response.data.documents)
    
    // 获取每个文档的详细信息 - 使用Promise.all并行处理
    const chunkedDocsWithDetails = await Promise.all(
      response.data.documents.map(async (doc) => {
        try {
          // 移除.json扩展名(如果有)，并编码文件名
          const docId = doc.name.replace(/\.json$/, '')
          const encodedId = encodeURIComponent(docId)
          
          // 构建详情请求URL
          const detailUrl = `${apiBaseUrl}/documents/${encodedId}.json?type=chunked`
          console.log(`请求文档详情URL: ${detailUrl}`)
          
          const detailResponse = await axios.get(detailUrl)
          console.log(`文档详情 ${doc.name}:`, detailResponse.data)
          
          return {
            id: doc.id || doc.name,
            name: doc.name,
            type: doc.type || 'PDF',
            size: doc.size || 'N/A',
            pages: detailResponse.data.total_pages || 0,
            chunks: detailResponse.data.total_chunks || 0,
            mode: detailResponse.data.chunking_method || 'N/A',
            uploadTime: detailResponse.data.timestamp ? new Date(detailResponse.data.timestamp).toLocaleString() : 'N/A',
            status: 'completed'
          }
        } catch (error) {
          console.error(`获取文档详情失败: ${doc.name}`, error)
          
          if (error.response) {
            console.error(`HTTP错误 ${error.response.status}: ${JSON.stringify(error.response.data)}`)
          }
          
          return {
            id: doc.id || doc.name,
            name: doc.name,
            type: doc.type || 'PDF',
            size: doc.size || 'N/A',
            pages: 0,
            chunks: 0,
            mode: 'N/A',
            uploadTime: new Date().toLocaleString(),
            status: error.response?.status === 404 ? 'pending' : 'failed'
          }
        }
      })
    )
    
    console.log('最终分块文档列表:', chunkedDocsWithDetails)
    files.value = chunkedDocsWithDetails
    total.value = files.value.length
  } catch (error) {
    console.error('获取已处理文档列表失败:', error)
    
    if (error.response) {
      console.error(`HTTP错误 ${error.response.status}: ${JSON.stringify(error.response.data)}`)
    }
    
    ElMessage.error('获取已处理文档列表失败')
  } finally {
    loading.value = false
  }
}

// 记录API调用信息的方法
const logApiCall = (method, url, params, response = null, error = null) => {
  // 仅在调试模式下记录
  if (!debugMode.value) return
  
  // 创建日志条目
  const logEntry = {
    id: Date.now(),
    timestamp: new Date().toLocaleTimeString(),
    method,
    url,
    params: JSON.stringify(params, null, 2),
    success: !error,
    response: response ? JSON.stringify(response, null, 2) : null,
    error: error ? (error.response?.data || error.message || JSON.stringify(error)) : null
  }
  
  // 添加到日志列表最前面
  apiLogs.value.unshift(logEntry)
  
  // 限制日志数量
  if (apiLogs.value.length > maxLogs) {
    apiLogs.value = apiLogs.value.slice(0, maxLogs)
  }
  
  console.log(`API ${method} ${url}:`, { params, response, error })
}

// 清除日志
const clearApiLogs = () => {
  apiLogs.value = []
}

// 启动分块处理
const handleStartChunk = async () => {
  if (!chunkConfig.value.selectedDoc) {
    chunkStatus.value = '错误: 请先选择一个文档'
    return
  }
  
  processingChunk.value = true
  chunkStatus.value = '正在处理中...'
  // progress.value = 0
  // progressStatus.value = ''
  // progressText.value = '正在处理文件...'
  
  try {
    // 确保docId使用正确的格式
    const selectedDoc = loadedDocuments.value.find(doc => doc.id === chunkConfig.value.selectedDoc)
    if (!selectedDoc) {
      processingChunk.value = false
      throw new Error('找不到选中的文档')
    }
    
    const docId = selectedDoc.id
    
    // 构建请求参数
    const params = {
      doc_id: docId,
      chunking_option: chunkConfig.value.mode
    }
    
    if (chunkConfig.value.mode === 'fixed_size') {
      params.chunk_size = chunkConfig.value.chunkSize || 1000
      params.overlap_size = chunkConfig.value.overlapSize || 0
    }
    
    console.log('分块处理参数:', params)
    
    // 发送分块处理请求
    // progress.value = 10
    // progressText.value = '正在向服务器发送请求...'
    
    const url = `${apiBaseUrl}/chunk`
    const response = await axios.post(url, params, {
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: 60000
    })
    
    console.log('分块处理响应:', response.data)
    
    // 更新进度
    // progress.value = 90
    // progressText.value = '文档分块完成，正在获取分块结果...'
    
    // 等待1秒，让后端有时间处理完成
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 设置完成状态
    // progress.value = 100
    // progressStatus.value = 'success'
    // progressText.value = '处理完成'
    
    // 处理完成后的操作
    setTimeout(() => {
      // progress.value = 0 // 隐藏进度条
      
      if (response.data && response.data.output_file) {
        handlePreviewById(response.data.output_file)
      } else if (response.data && response.data.chunked_doc_id) {
        handlePreviewById(response.data.chunked_doc_id)
      } else {
        const guessedFile = `${docId.replace('.json', '')}_${chunkConfig.value.mode}.json`
        handlePreviewById(guessedFile)
      }
      
      // 刷新文档列表
      fetchChunkedDocuments()
      
      chunkStatus.value = '分块处理完成'
      processingChunk.value = false
      if (response.data && response.data.total_chunks) {
        ElMessage.success(`文档分块处理成功，共${response.data.total_chunks}个分块`)
      } else {
        ElMessage.success('文档分块处理完成')
      }
    }, 1000)
    
    logApiCall('POST', url, params, response.data)
  } catch (error) {
    processingChunk.value = false
    console.error('分块处理失败:', error)
    
    // progress.value = 0
    // progressStatus.value = 'exception'
    // progressText.value = error.response?.data?.detail || error.message || '未知错误'
    
    chunkStatus.value = `错误: 分块处理失败 - ${error.response?.data?.detail || error.message || '未知错误'}`
    ElMessage.error(`分块处理失败: ${error.response?.data?.detail || error.message || '未知错误'}`)
    
    logApiCall('POST', `${apiBaseUrl}/chunk`, chunkConfig.value.selectedDoc ? {
      doc_id: chunkConfig.value.selectedDoc,
      chunking_option: chunkConfig.value.mode
    } : {}, null, error)
  } finally {
    // processingChunk.value = false
  }
}

// 根据ID预览文档
const handlePreviewById = async (docId, isRetry = false) => {
  try {
    // 清除之前的错误状态，设置初始重试计数
    if (!isRetry) {
      retryCount.value = 0
      previewError.value = false
      previewErrorMessage.value = '获取预览内容失败'
    }
    
    // 显示当前尝试次数
    console.log(`预览尝试 ${retryCount.value + 1}/${maxRetries + 1}`)
    
    // 移除.json扩展名(如果有)
    const cleanId = docId.replace('.json', '')
    
    // 构建请求URL - 对文件名进行编码，并使用正确的查询参数格式
    const encodedId = encodeURIComponent(cleanId)
    const requestUrl = `${apiBaseUrl}/documents/${encodedId}.json?type=chunked`
    console.log('请求预览URL:', requestUrl)
    
    // 发起请求获取分块内容
    const response = await axios.get(requestUrl)
    console.log('预览文档响应:', response.data)
    
    // 空内容检查
    if (!response.data) {
      throw new Error('获取的数据为空')
    }
    
    // 处理分块内容并格式化数据
    loadedContent.value = {
      filename: response.data.filename,
      pageCount: response.data.total_pages || 0,
      chunkCount: response.data.total_chunks || 0,
      mode: response.data.chunking_method || 'N/A',
      loadingMethod: response.data.loading_method || 'N/A',
      timestamp: response.data.timestamp,
      chunks: Array.isArray(response.data.chunks) 
        ? response.data.chunks.map((chunk, index) => ({
            id: chunk.metadata?.chunk_id || `chunk-${index + 1}`,
            content: typeof chunk === 'string' ? chunk : chunk.content || chunk.text || '',
            metadata: chunk.metadata || {
              page_range: chunk.metadata?.page_range || 'N/A',
              word_count: chunk.metadata?.word_count || 'N/A',
              chunk_id: chunk.metadata?.chunk_id || `chunk-${index + 1}`
            }
          }))
        : []
    }
    
    // 取消错误状态
    previewError.value = false
    
    // 默认展开所有分块
    if (loadedContent.value.chunks && loadedContent.value.chunks.length > 0) {
      loadedContent.value.chunks.forEach((_, index) => {
        collapsedChunks.value[index] = false
      })
    }
    
    // 等待DOM更新后检查分块内容是否需要滚动
    nextTick(() => {
      checkAllChunksScrollable()
    })
  } catch (error) {
    console.error('获取预览内容失败:', error)
    
    // 处理错误情况
    if (error.response && error.response.status === 404) {
      // 404错误处理 - 文件可能还在处理中
      console.warn('文件未找到，可能处理尚未完成')
      
      if (retryCount.value < maxRetries) {
        // 增加重试计数并设置提示
        retryCount.value++
        previewErrorMessage.value = `获取预览内容失败 (404): 文件可能正在准备中，正在重试 (${retryCount.value}/${maxRetries})...`
        previewError.value = true
        
        // 显示更详细的错误信息
        console.log(`请求URL: ${apiBaseUrl}/documents/${encodeURIComponent(docId.replace('.json', ''))}.json?type=chunked`)
        console.log(`错误状态: ${error.response.status} ${error.response.statusText}`)
        
        // 2秒后重试
        setTimeout(() => {
          handlePreviewById(docId, true)
        }, 2000)
        return
      } else {
        // 达到最大重试次数
        previewErrorMessage.value = `获取预览内容失败 (404): 文件不存在或处理未完成。请确认文件名正确并且已完成分块处理。`
        // 显示可用的文档列表，帮助用户选择正确的文件
        fetchChunkedDocuments()
      }
    } else if (error.response) {
      // 其他HTTP错误
      previewErrorMessage.value = `获取预览内容失败 (${error.response.status}): ${error.response.data?.message || '未知错误'}`
    } else if (error.request) {
      // 网络错误
      previewErrorMessage.value = '获取预览内容失败: 网络请求未得到响应，请检查API服务是否正常运行'
    } else {
      // 其他错误
      previewErrorMessage.value = `获取预览内容失败: ${error.message || '未知错误'}`
    }
    
    // 显示错误状态
    previewError.value = true
    ElMessage.error(previewErrorMessage.value)
  }
}

// 预览文档
const handlePreview = async (row) => {
  try {
    // 清除之前的错误状态
    previewError.value = false
    previewErrorMessage.value = '获取预览内容失败'
    retryCount.value = 0
    
    // 直接显示预览标签页
    activeTab.value = 'preview'
    previewSubTab.value = 'content'
    
    // 开始加载预览内容
    await handlePreviewById(row.name)
    ElMessage.success(`预览文件: ${row.name}`)
  } catch (error) {
    console.error('预览文件失败:', error)
    previewError.value = true
    ElMessage.error(`预览文件失败: ${error.message || '未知错误'}`)
  }
}

// 删除文档
const handleDelete = async (row) => {
  ElMessageBox.confirm(
    '确定要删除该文件吗？',
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      // 处理文档ID
      const docId = row.name.replace('.json', '')
      const encodedId = encodeURIComponent(docId)
      await axios.delete(`${apiBaseUrl}/documents/${encodedId}?type=chunked`)
      
      // 从列表中移除
      const index = files.value.findIndex(item => item.id === row.id)
      if (index !== -1) {
        files.value.splice(index, 1)
        total.value = files.value.length
      }
      
      // 如果当前正在预览该文件，清除预览
      if (loadedContent.value && loadedContent.value.filename === row.name) {
        loadedContent.value = null
        previewUrl.value = ''
      }
      
      ElMessage.success('删除成功')
    } catch (error) {
      console.error('删除文件失败:', error)
      ElMessage.error('删除文件失败')
    }
  }).catch(() => {})
}

const handleSizeChange = (size) => {
  pageSize.value = size
}

const handleCurrentChange = (page) => {
  currentPage.value = page
}

// 检查分块内容是否需要滚动
const checkScrollPosition = (event, index) => {
  const { target } = event
  // 如果内容高度大于容器高度，显示滚动指示器
  hasMoreContent.value[index] = target.scrollHeight > target.clientHeight && 
                              target.scrollHeight - target.scrollTop - target.clientHeight > 10
}

// 判断分块是否已折叠
const isChunkCollapsed = (index) => {
  return collapsedChunks.value[index] === true
}

// 切换分块的折叠状态
const toggleChunk = (index) => {
  collapsedChunks.value[index] = !collapsedChunks.value[index]
  if (!collapsedChunks.value[index]) {
    // 展开时检查是否可滚动
    nextTick(() => {
      const el = document.getElementById(`chunk-content-${index}`)
      if (el) {
        hasMoreContent.value[index] = el.scrollHeight > el.clientHeight
      }
    })
  }
}

// 在内容更新后检查所有分块是否可滚动
const checkAllChunksScrollable = () => {
  nextTick(() => {
    if (!hasChunks.value) return
    
    const chunkElements = document.querySelectorAll('.chunk-content')
    chunkElements.forEach((el, index) => {
      hasMoreContent.value[index] = el.scrollHeight > el.clientHeight
    })
  })
}

// 折叠所有分块
const collapseAllChunks = () => {
  if (!hasChunks.value) return
  
  loadedContent.value.chunks.forEach((_, index) => {
    collapsedChunks.value[index] = true
  })
}

// 展开所有分块
const expandAllChunks = () => {
  if (!hasChunks.value) return
  
  loadedContent.value.chunks.forEach((_, index) => {
    collapsedChunks.value[index] = false
  })
  
  // 检查所有分块的滚动状态
  nextTick(() => {
    checkAllChunksScrollable()
  })
}

// 检查是否有分块
const hasChunks = computed(() => {
  return loadedContent.value && 
         loadedContent.value.chunks && 
         loadedContent.value.chunks.length > 0
})

// 监听loadedContent变化，检查可滚动性
watch(() => loadedContent.value, () => {
  if (loadedContent.value) {
    collapsedChunks.value = {} // 重置折叠状态
    nextTick(() => {
      checkAllChunksScrollable()
    })
  }
})

// 页面加载时获取文档列表
onMounted(() => {
  fetchLoadedDocuments()
})

// 监听分块方法变化，仅在特定模式下显示分块大小输入
watch(() => chunkConfig.value.mode, (newMode) => {
  if (newMode === 'fixed_size') {
    // 为固定大小模式设置默认值
    chunkConfig.value.chunkSize = 1000
  }
})
</script>

<style scoped>
.upload-demo {
  display: inline-block;
}

/* 修改分块内容样式 */
.chunk-content {
  color: #303133;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  padding: 16px;
  background-color: #fff;
  max-height: 400px !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
  scrollbar-width: auto !important; /* Firefox */
  scrollbar-color: #909399 #fff !important; /* Firefox */
  position: relative;
}

/* Webkit浏览器的滚动条样式 */
.chunk-content::-webkit-scrollbar {
  width: 10px !important;
  height: 0 !important; /* 隐藏水平滚动条 */
  display: block !important;
  visibility: visible !important;
}

.chunk-content::-webkit-scrollbar-thumb {
  background: #909399 !important;
  border-radius: 5px !important;
  border: 2px solid #fff !important;
}

.chunk-content::-webkit-scrollbar-track {
  background: #fff !important;
  border-radius: 5px !important;
  visibility: visible !important;
  display: block !important;
}

.chunk-content::-webkit-scrollbar-corner {
  background: #f5f7fa !important;
}

/* 滚动内容的高度指示器 */
.scroll-indicator {
  position: absolute;
  right: 8px;
  bottom: 8px;
  background-color: rgba(64, 158, 255, 0.1);
  color: #409eff;
  padding: 4px 8px;
  font-size: 12px;
  border-radius: 4px;
  border: 1px solid rgba(64, 158, 255, 0.2);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
  z-index: 1;
}

/* 确保分块容器可以正常滚动（仅垂直方向滚动） */
.chunks-container {
  position: relative;
  overflow-y: auto !important;
  overflow-x: hidden !important;
  height: calc(100% - 220px) !important;
  scrollbar-width: auto !important; /* Firefox */
  scrollbar-color: #909399 #f5f7fa !important; /* Firefox */
  padding: 0 20px;
  min-height: 200px;
  max-height: 100% !important;
}

.chunk-list {
  padding: 0 0 20px 0;
  min-height: 100px;
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

.el-card, 
.el-table,
.el-table__body,
.el-table__header,
.el-table__body-wrapper,
.el-table .cell,
.el-scrollbar,
.el-scrollbar__wrap,
.el-scrollbar__view {
  overflow-x: hidden !important;
  max-width: 100% !important;
}

/* 更新媒体查询以确保适应小屏幕 */
@media (max-width: 768px) {
  .chunks-container {
    padding: 12px;
    overflow-x: hidden !important;
  }
  
  .chunk-content {
    max-height: 250px;
    overflow-x: hidden !important;
  }
}

.bg-red-100 {
  background-color: #fef2f2;
}

.bg-green-100 {
  background-color: #f0fdf4;
}

.text-red-700 {
  color: #dc2626;
}

.text-green-700 {
  color: #15803d;
}

.chunk-status {
  margin-top: 16px;
  padding: 12px;
  border-radius: 4px;
  font-size: 14px;
  transition: all 0.3s ease;
}

.chunk-status.success {
  background-color: #f0fdf4;
  color: #15803d;
  border: 1px solid #dcfce7;
}

.chunk-status.error {
  background-color: #fef2f2;
  color: #dc2626;
  border: 1px solid #fee2e2;
}

.chunk-status.info {
  background-color: #f0f9ff;
  color: #0369a1;
  border: 1px solid #e0f2fe;
}

.chunk-status.warning {
  background-color: #fffbeb;
  color: #d97706;
  border: 1px solid #fef3c7;
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
  height: 0 !important; /* 隐藏水平滚动条 */
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
</style> 