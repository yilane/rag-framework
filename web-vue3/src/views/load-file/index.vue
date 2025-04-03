<template>
  <div style="width: 96%; height: calc(90vh - 56px); overflow-y: auto; overflow-x: hidden; padding: 24px; background-color: #f5f7fa; display: flex; flex-direction: column;">
    
    <div style="display: flex; width: 100%; flex: 1; gap: 20px;">
      <!-- 左侧：上传和配置部分 -->
      <div style="width: 25%; min-width: 300px; max-width: 350px;">
        <el-card style="width: 100%; height: calc(90vh - 104px); overflow-y: auto; overflow-x: hidden;" shadow="hover">
          <div style="display: flex; flex-direction: column; gap: 24px;">
            <div>
              <div style="margin-bottom: 8px;font-size: 14px;">上传 PDF</div>
              <el-upload
                class="upload-demo"
                action="#"
                :auto-upload="false"
                :on-change="handleFileChange"
                accept=".pdf,.doc,.docx,.txt"
              >
                <el-button type="primary">选择文件</el-button>
              </el-upload>
              <div style="margin-top: 8px; color: #909399;" v-if="!selectedFile">未选择任何文件</div>
              <div style="margin-top: 8px; color: #606266;" v-else>已选择: {{ selectedFile.name }}</div>
            </div>
            
            <div>
              <div style="margin-bottom: 8px;font-size: 14px;">加载方法</div>
              <el-select v-model="loadingMethod" style="width: 100%; margin-bottom: 16px;">
                <el-option
                  v-for="option in loadingOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
              
              <!-- Unstructured策略选项 -->
              <div v-if="loadingMethod === 'unstructured'" style="margin-bottom: 16px;">
                <div style="margin-bottom: 8px;">Unstructured策略</div>
                <el-select v-model="unstructuredStrategy" style="width: 100%; margin-bottom: 16px;">
                  <el-option label="Fast" value="fast" />
                  <el-option label="High Resolution" value="hi_res" />
                  <el-option label="OCR Only" value="ocr_only" />
                </el-select>
                
                <div style="margin-bottom: 8px;">分块策略</div>
                <el-select v-model="chunkingStrategy" style="width: 100%; margin-bottom: 16px;">
                  <el-option label="Basic" value="basic" />
                  <el-option label="By Title" value="by_title" />
                </el-select>
                
                <!-- Basic分块策略的具体选项 -->
                <div v-if="chunkingStrategy === 'basic'" style="margin-bottom: 16px;">
                  <el-form label-width="140px">
                    <el-form-item label="最大字符数">
                      <el-input-number 
                        v-model="chunkingOptions.maxCharacters" 
                        :min="100" 
                        :max="10000"
                        style="width: 100%;"
                      />
                    </el-form-item>
                    <el-form-item label="新块阈值">
                      <el-input-number 
                        v-model="chunkingOptions.newAfterNChars" 
                        :min="100" 
                        :max="10000"
                        style="width: 100%;"
                      />
                    </el-form-item>
                    <el-form-item label="合并小于N字符">
                      <el-input-number 
                        v-model="chunkingOptions.combineTextUnderNChars" 
                        :min="100" 
                        :max="5000"
                        style="width: 100%;"
                      />
                    </el-form-item>
                    <el-form-item label="重叠字符数">
                      <el-input-number 
                        v-model="chunkingOptions.overlap" 
                        :min="0" 
                        :max="1000"
                        style="width: 100%;"
                      />
                    </el-form-item>
                    <el-form-item label="全部重叠">
                      <el-switch v-model="chunkingOptions.overlapAll" />
                    </el-form-item>
                  </el-form>
                </div>
                
                <!-- By Title分块策略的具体选项 -->
                <div v-if="chunkingStrategy === 'by_title'" style="margin-bottom: 16px;">
                  <el-form label-width="140px">
                    <el-form-item label="合并小于N字符">
                      <el-input-number 
                        v-model="chunkingOptions.combineTextUnderNChars" 
                        :min="100" 
                        :max="5000"
                        style="width: 100%;"
                      />
                    </el-form-item>
                    <el-form-item label="多页节">
                      <el-switch v-model="chunkingOptions.multiPageSections" />
                    </el-form-item>
                  </el-form>
                </div>
              </div>
              
              <el-button type="primary" style="width: 100%;" @click="handleLoadFile">
                加载文档
              </el-button>
            </div>
          </div>
        </el-card>
      </div>
      
      <!-- 右侧：文档预览和管理部分 -->
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
              <div style="padding: 16px 20px; border-bottom: 1px solid #ebeef5; flex-shrink: 0;">
                <h2 style="margin: 0; font-size: 20px; font-weight: 500; color: #303133;">文档内容</h2>
              </div>
              
              <!-- 文档信息卡片 -->
              <div style="padding: 16px 20px; border-bottom: 1px solid #ebeef5; background-color: #f5f7fa; flex-shrink: 0;">
                <h3 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 500; color: #303133;">文档信息</h3>
                <div style="color: #606266; font-size: 14px; line-height: 1.6;">
                  <p style="margin: 4px 0;">文件名: {{ effectiveContent.filename || 'N/A' }}</p>
                  <p style="margin: 4px 0;">页数: {{ effectiveContent.total_pages || 'N/A' }}</p>
                  <p style="margin: 4px 0;">分块数: {{ effectiveContent.total_chunks || 'N/A' }}</p>
                  <p style="margin: 4px 0;">加载方法: {{ effectiveContent.loading_method || 'N/A' }}</p>
                  <p style="margin: 4px 0;">分块方法: {{ effectiveContent.chunking_method || 'N/A' }}</p>
                  <p style="margin: 4px 0;">处理时间: {{ effectiveContent.timestamp ? new Date(effectiveContent.timestamp).toLocaleString() : 'N/A' }}</p>
                </div>
              </div>
              
              <!-- 分块内容 -->
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
                <!-- 使用hasChunks计算属性判断 -->
                <template v-if="hasChunks">
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
                      v-for="(chunk, index) in effectiveContent.chunks" 
                      :key="index"
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
                        <el-icon :style="{ transform: isChunkCollapsed(index) ? 'rotate(0deg)' : 'rotate(180deg)', transition: 'transform 0.3s' }">
                          <ArrowDown />
                        </el-icon>
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
                </template>
                
                <!-- 处理直接返回的content字符串 -->
                <template v-else-if="effectiveContent && effectiveContent.content">
                  <div class="chunk-list">
                    <div style="border-radius: 4px; overflow: hidden; border: 1px solid #e4e7ed; margin-bottom: 16px; background-color: #fff;">
                      <div class="content-block">
                        {{ effectiveContent.content }}
                      </div>
                    </div>
                  </div>
                </template>
                
                <!-- 没有可识别的内容格式时 -->
                <template v-else>
                  <div class="chunk-list">
                    <el-empty description="没有可显示的分块内容" />
                    
                    <!-- 调试信息 -->
                    <div style="margin-top: 20px; padding: 16px; background-color: #f8f8f8; border-radius: 4px; border: 1px dashed #dcdfe6;">
                      <h4 style="margin-top: 0; margin-bottom: 8px; font-size: 14px; color: #606266;">返回的数据结构：</h4>
                      <pre style="margin: 0; white-space: pre-wrap; font-size: 12px; color: #606266; overflow: auto; max-height: 200px;">{{ JSON.stringify(loadedContent, null, 2) }}</pre>
                    </div>
                  </div>
                </template>
              </div>
            </div>
            <div v-else-if="previewUrl" style="display: flex; justify-content: center; align-items: center; padding: 20px; overflow-y: auto; flex: 1;">
              <img 
                :src="previewUrl" 
                alt="Document Preview" 
                style="max-width: 100%; max-height: 80vh; border-radius: 4px; box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);"
              />
            </div>
            <div v-else style="display: flex; justify-content: center; align-items: center; height: 100%; overflow-y: auto; flex: 1;">
              <el-empty description="上传并加载文件，或选择现有文档，在此查看结果" />
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
              <el-table :data="filteredFiles" style="width: 100%;" border height="100%" :show-overflow-tooltip="true">
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
                <el-table-column prop="loadingMethod" label="加载方法" width="100" align="center" />
                <el-table-column prop="chunkingMethod" label="分块方法" width="100" align="center" />
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Document, ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import { apiUrls } from '@/config/api'
import { get, upload, del, download } from '@/utils/request'

// 页面状态
const activeTab = ref('preview')
const selectedFile = ref(null)
const previewUrl = ref('')
const loadedContent = ref(null)
const loading = ref(false)
const loadingStatus = ref('')
const activeCollapse = ref(['info']) // 默认展开文档信息
const collapsedChunks = ref({}) // 存储折叠状态的对象
const chunkContents = ref([]) // 引用分块内容元素
const hasMoreContent = ref({}) // 跟踪哪些分块有更多内容需要滚动

// 加载方式选项
const loadingOptions = [
  { label: 'PyMuPDF', value: 'pymupdf' },
  { label: 'PyPDF', value: 'pypdf' },
  { label: 'Unstructured', value: 'unstructured' }
]
const loadingMethod = ref('pymupdf')

// Unstructured加载配置
const unstructuredStrategy = ref('fast')
const chunkingStrategy = ref('basic')
const chunkingOptions = ref({
  maxCharacters: 4000,
  newAfterNChars: 3000,
  combineTextUnderNChars: 500,
  overlap: 200,
  overlapAll: false,
  multiPageSections: false
})

// 文件列表相关
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(3)
const fileList = ref([
  {
    id: 1,
    name: '产品说明书.pdf',
    pages: '15',
    chunks: '11',
    loadingMethod: 'pymupdf',
    chunkingMethod: 'loaded',
    type: 'PDF',
    size: '2.5MB',
    uploadTime: '2024-04-02 10:00:00',
    status: '成功'
  },
  {
    id: 2,
    name: '技术文档.docx',
    pages: '20',
    chunks: '15',
    loadingMethod: 'unstructured',
    chunkingMethod: 'basic',
    type: 'Word',
    size: '1.8MB',
    uploadTime: '2024-04-02 09:30:00',
    status: '处理中'
  },
  {
    id: 3,
    name: '用户手册.pdf',
    pages: '8',
    chunks: '5',
    loadingMethod: 'pymupdf',
    chunkingMethod: 'loaded',
    type: 'PDF',
    size: '3.2MB',
    uploadTime: '2024-04-02 08:15:00',
    status: '成功'
  }
])

const filteredFiles = computed(() => {
  return fileList.value.filter(file => 
    file.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

// 添加文档列表获取函数和mounted钩子
onMounted(() => {
  fetchDocuments()
})

// 获取文档列表
const fetchDocuments = async () => {
  try {
    loading.value = true
    const data = await get(apiUrls.documents.list, { type: 'loaded' })
    fileList.value = data.documents.map(doc => ({
      id: doc.name,
      name: doc.name,
      pages: doc.metadata?.total_pages || '0',
      chunks: doc.metadata?.total_chunks || '0',
      loadingMethod: doc.metadata?.loading_method || 'pymupdf',
      chunkingMethod: doc.metadata?.chunking_method || 'loaded',
      type: doc.metadata?.file_type || '未知',
      size: doc.metadata?.file_size || 'N/A',
      uploadTime: doc.metadata?.timestamp ? new Date(doc.metadata.timestamp).toLocaleString() : 'N/A',
      status: '成功'
    }))
    total.value = fileList.value.length
  } catch (error) {
    console.error('获取文档列表失败:', error)
    ElMessage.error('获取文档列表失败')
  } finally {
    loading.value = false
  }
}

// 处理文件变化
const handleFileChange = (file) => {
  selectedFile.value = file.raw
  console.log('File selected:', selectedFile.value)
}

// 修改文件加载方法，对接真实API
const handleLoadFile = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  // 重置预览状态
  loadedContent.value = null
  previewUrl.value = ''
  loading.value = true
  loadingStatus.value = '正在加载文档...'
  
  try {
    // 构建提交数据
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('loading_method', loadingMethod.value)
    
    // 如果是unstructured方法，添加额外配置
    if (loadingMethod.value === 'unstructured') {
      formData.append('strategy', unstructuredStrategy.value)
      formData.append('chunking_strategy', chunkingStrategy.value)
      formData.append('chunking_options', JSON.stringify(chunkingOptions.value))
    }
    
    // 使用封装的upload方法
    const result = await upload(apiUrls.files.load, formData)
    console.log('API返回数据:', result)
    
    // 直接使用API返回的数据结构
    loadedContent.value = result
    
    ElMessage.success('文档加载成功')
    
    // 刷新文档列表
    fetchDocuments()
    
    // 切换到预览标签
    activeTab.value = 'preview'
    
  } catch (error) {
    console.error('加载文档出错:', error)
    ElMessage.error('文档加载失败: ' + (error.message || '未知错误'))
    loadedContent.value = null
  } finally {
    loading.value = false
    loadingStatus.value = ''
  }
}

// 修改预览方法，从API获取文档内容
const handlePreview = async (file) => {
  // 重置预览状态
  loadedContent.value = null
  previewUrl.value = ''
  loading.value = true
  
  try {
    // 使用封装的get方法获取文档内容
    const result = await get(apiUrls.documents.get(file.id))
    console.log('API预览返回数据:', result)
    
    // 检查返回结果是否有效
    if (!result) {
      throw new Error('返回数据为空')
    }
    
    // 直接使用API返回的数据结构
    loadedContent.value = result
    
    // 切换到预览标签
    activeTab.value = 'preview'
    
    // 确保DOM更新后滚动到顶部
    nextTick(() => {
      const previewContainer = document.querySelector('.el-card__body > div[style*="overflow: auto"]')
      if (previewContainer) {
        previewContainer.scrollTop = 0
      }
    })
    
    ElMessage.success(`预览文件: ${file.name}`)
  } catch (error) {
    console.error('预览文件出错:', error)
    
    // 如果API调用失败，尝试获取PDF预览图像
    try {
      const blob = await download(apiUrls.documents.preview(file.id))
      previewUrl.value = URL.createObjectURL(blob)
    } catch (previewError) {
      console.error('获取预览图像失败:', previewError)
      ElMessage.error('无法加载文档预览')
      previewUrl.value = '' // 不使用占位图，直接显示无预览内容
    }
  } finally {
    loading.value = false
  }
}

// 修改删除方法，对接真实API
const handleDelete = (file) => {
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
      loading.value = true
      // 使用封装的del方法
      await del(apiUrls.documents.delete(file.id))
      
      // 从列表中移除
      fileList.value = fileList.value.filter(item => item.id !== file.id)
      total.value = fileList.value.length
      
      // 如果当前正在预览该文件，清除预览
      if (loadedContent.value && loadedContent.value.file_name === file.name) {
        loadedContent.value = null
        previewUrl.value = ''
      }
      
      ElMessage.success('删除成功')
    } catch (error) {
      console.error('删除文件失败:', error)
    } finally {
      loading.value = false
    }
  }).catch(() => {
    // 用户取消删除
  })
}

// 辅助计算属性，获取有效的文档内容
const effectiveContent = computed(() => {
  if (!loadedContent.value) return null
  
  // 如果有filepath字段，可能是API返回的JSON结构
  if (loadedContent.value.filepath && loadedContent.value.loaded_content) {
    const loaded = loadedContent.value.loaded_content
    return {
      filename: loaded.filename || '',
      total_pages: loaded.total_pages || 0,
      total_chunks: loaded.total_chunks || 0,
      loading_method: loaded.loading_method || '',
      chunking_method: loaded.chunking_method || '',
      timestamp: loaded.timestamp || '',
      chunks: Array.isArray(loaded.chunks) ? loaded.chunks : []
    }
  }
  
  // 优先使用顶层的属性
  if (loadedContent.value.chunks && Array.isArray(loadedContent.value.chunks) && loadedContent.value.chunks.length > 0) {
    return {
      chunks: loadedContent.value.chunks,
      filename: loadedContent.value.filename || '',
      total_pages: loadedContent.value.total_pages || 0,
      total_chunks: loadedContent.value.total_chunks || 0,
      loading_method: loadedContent.value.loading_method || '',
      chunking_method: loadedContent.value.chunking_method || '',
      timestamp: loadedContent.value.timestamp || ''
    }
  }
  
  // 检查loaded_content
  if (loadedContent.value.loaded_content) {
    const loaded = loadedContent.value.loaded_content
    if (loaded.chunks && Array.isArray(loaded.chunks) && loaded.chunks.length > 0) {
      return {
        chunks: loaded.chunks,
        filename: loaded.filename || '',
        total_pages: loaded.total_pages || 0,
        total_chunks: loaded.total_chunks || 0,
        loading_method: loaded.loading_method || '',
        chunking_method: loaded.chunking_method || '',
        timestamp: loaded.timestamp || ''
      }
    }
  }
  
  // 如果找不到chunks但有content
  if (loadedContent.value.content) {
    return {
      content: loadedContent.value.content,
      filename: loadedContent.value.filename || '',
      total_pages: loadedContent.value.total_pages || 0,
      total_chunks: 1,
      loading_method: loadedContent.value.loading_method || '',
      chunking_method: loadedContent.value.chunking_method || '',
      timestamp: loadedContent.value.timestamp || ''
    }
  }
  
  // 最后返回原始数据
  return loadedContent.value
})

// 检查分块内容是否需要滚动
const checkScrollPosition = (event, index) => {
  const { target } = event
  // 如果内容高度大于容器高度，显示滚动指示器
  hasMoreContent.value[index] = target.scrollHeight > target.clientHeight && 
                              target.scrollHeight - target.scrollTop - target.clientHeight > 10
}

// 在内容更新后检查所有分块是否可滚动
const checkAllChunksScrollable = () => {
  nextTick(() => {
    if (!effectiveContent.value?.chunks) return
    
    const chunkElements = document.querySelectorAll('.chunk-content')
    chunkElements.forEach((el, index) => {
      hasMoreContent.value[index] = el.scrollHeight > el.clientHeight
    })
  })
}

// 监听loadedContent变化，检查可滚动性
watch(() => loadedContent.value, () => {
  if (loadedContent.value) {
    collapsedChunks.value = {} // 重置折叠状态
    nextTick(() => {
      checkAllChunksScrollable()
    })
  }
})

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

// 判断分块是否已折叠
const isChunkCollapsed = (index) => {
  return collapsedChunks.value[index] === true
}

// 折叠所有分块
const collapseAllChunks = () => {
  if (!effectiveContent.value?.chunks) return
  
  effectiveContent.value.chunks.forEach((_, index) => {
    collapsedChunks.value[index] = true
  })
}

// 展开所有分块
const expandAllChunks = () => {
  if (!effectiveContent.value?.chunks) return
  
  effectiveContent.value.chunks.forEach((_, index) => {
    collapsedChunks.value[index] = false
  })
  
  // 检查所有分块的滚动状态
  nextTick(() => {
    checkAllChunksScrollable()
    
    // 确保容器可滚动
    const container = document.querySelector('.chunks-container')
    if (container) {
      // 添加一点延迟，确保DOM更新完成
      setTimeout(() => {
        container.scrollTop = 0
        
        // 如果内容高度超过容器高度，显示滚动指示器
        if (container.scrollHeight > container.clientHeight) {
          console.log('Content exceeds container height, scrolling enabled')
        }
      }, 100)
    }
  })
}

// 在预览部分的模板中加强判断
const hasChunks = computed(() => {
  return effectiveContent.value && 
         effectiveContent.value.chunks && 
         Array.isArray(effectiveContent.value.chunks) && 
         effectiveContent.value.chunks.length > 0
})
</script>

<style scoped>
.upload-demo {
  display: inline-block;
}

/* 自定义滚动条样式 */
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
  border-top: 1px solid #f0f0f0;
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