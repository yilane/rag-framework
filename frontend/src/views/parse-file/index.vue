<template>
  <div
    style="width: 96%; height: calc(90vh - 56px); overflow-y: auto; overflow-x: hidden; padding: 24px; background-color: #f5f7fa; display: flex; flex-direction: column;">

    <div style="display: flex; width: 100%; flex: 1; gap: 20px;">
      <!-- 左侧：配置部分 -->
      <div style="width: 25%; min-width: 300px; max-width: 350px;">
        <el-card style="width: 100%; height: calc(90vh - 104px); overflow-y: auto; overflow-x: hidden;" shadow="hover">
          <div style="display: flex; flex-direction: column; gap: 24px;">
            <div>
              <!-- 添加文件选择 -->
              <div>
                <div style="margin-bottom: 8px; font-size: 14px;">上传文档</div>
                <el-upload 
                  class="upload-demo" 
                  action="#" 
                  :auto-upload="false" 
                  :on-change="handleFileChange"
                  :before-upload="checkFileType"
                  accept=".pdf,.doc,.docx,.pptx,.ppt,.xlsx,.xls,.html,.htm,.epub,.md,.txt,.jpg,.jpeg,.png,.bmp,.tiff,.webp">
                  <el-button type="primary">选择文件</el-button>
                  <template #tip>
                    <div class="el-upload__tip">
                      支持多种格式：PDF、Word、图片、Markdown等，智能解析无需选择
                    </div>
                  </template>
                </el-upload>
                <div style="margin-top: 8px; color: #909399;" v-if="!selectedFile">未选择任何文件</div>
                <div style="margin-top: 8px; color: #606266;" v-else>已选择: {{ selectedFile.name }}</div>
              </div>



              <div style="margin-top: 16px;">
                <el-button type="primary" style="width: 100%;" @click="handleStartParse" :loading="processingParse"
                  :disabled="!selectedFile">
                  智能解析文档
                </el-button>
              </div>

              <!-- 状态提示 -->
              <div v-if="parseStatus" :class="[
                'parse-status',
                {
                  'success': parseStatus.includes('完成'),
                  'error': parseStatus.includes('错误'),
                  'info': parseStatus.includes('处理中'),
                  'warning': parseStatus.includes('警告')
                }
              ]">
                {{ parseStatus }}
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 右侧：文档预览部分 -->
      <div style="flex: 1; min-width: 0; max-width: calc(100% - 370px);">
        <el-card shadow="hover"
          style="width: 95%; height: calc(90vh - 104px); display: flex; flex-direction: column; overflow-x: hidden;">
          <template #header>
            <div class="flex justify-between items-center">
              <el-button-group>
                <el-button :type="activeTab === 'preview' ? 'primary' : 'default'" 
                          :plain="activeTab === 'management'"
                          @click="activeTab = 'preview'">
                  解析结果
                </el-button>
                <el-button :type="activeTab === 'management' ? 'primary' : 'default'"
                          :plain="activeTab === 'preview'"
                          @click="activeTab = 'management'">
                  文档记录
                </el-button>
              </el-button-group>
            </div>
          </template>

          <!-- 预览内容 -->
          <div v-if="activeTab === 'preview'" style="display: flex; flex-direction: column; flex: 1; overflow: hidden; height: 100%;">
            <div v-if="parsedContent"
              style="width: 100%; text-align: left; display: flex; flex-direction: column; height: 100%; overflow: auto;">
              <!-- 文档信息卡片 -->
              <div
                style="margin-bottom: 16px; padding: 12px; border-radius: 4px; background-color: #f7f7f7; border: 1px solid #e4e7ed;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <h4 style="margin: 0 0 8px 0; font-size: 15px; font-weight: 500; color: #303133;">文档信息</h4>
                  <el-button size="small" type="primary" icon="Download" @click="handleExportResult" v-if="parsedContent && filteredContent && filteredContent.length > 0">
                    导出markdown
                  </el-button>
                </div>
                <div style="color: #606266; font-size: 14px; line-height: 1.6;">
                  <div class="doc-info-grid">
                    <div class="doc-info-item">
                      <span class="info-label">文件名:</span>
                      <span class="info-value">{{ parsedContent.metadata?.filename || 'N/A' }}</span>
                    </div>
                    <div class="doc-info-item">
                      <span class="info-label">总页数:</span>
                      <span class="info-value">{{ parsedContent.metadata?.total_pages || 'N/A' }}</span>
                    </div>
                    <div class="doc-info-item">
                      <span class="info-label">内容数量:</span>
                      <span class="info-value">{{ filteredContent?.length || 0 }} 项</span>
                    </div>
                    <div class="doc-info-item">
                      <span class="info-label">解析方法:</span>
                      <span class="info-value">{{ parsedContent.metadata?.parsing_method || 'N/A' }}</span>
                    </div>
                    <div class="doc-info-item">
                      <span class="info-label">处理时间:</span>
                      <span class="info-value">{{ parsedContent.metadata?.timestamp ? formatDate(parsedContent.metadata.timestamp) : 'N/A' }}</span>
                    </div>
                    <div class="doc-info-item" v-if="parsedContent.metadata?.marker_stats?.images_detected > 0">
                      <span class="info-label">图片检测:</span>
                      <span class="info-value">{{ parsedContent.metadata.marker_stats.images_detected }} 张图片已解析</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 文档内容 -->
              <div class="content-container" style="
                  flex: 1; 
                  overflow-y: auto !important; 
                  padding: 0 4px; 
                  height: calc(100% - 120px) !important;
                  display: block !important;
                  min-height: 200px;
                ">
                <!-- Markdown显示模式切换 -->
                <div v-if="hasMarkdownContent" class="markdown-mode-tabs" style="margin-bottom: 16px; border-bottom: 1px solid #e4e7ed; padding-bottom: 8px;">
                  <el-radio-group v-model="markdownDisplayMode" size="small">
                    <el-radio-button label="rendered">渲染视图</el-radio-button>
                    <el-radio-button label="source">源码视图</el-radio-button>
                  </el-radio-group>
                </div>
                <!-- 内容分页控件 -->
                <div class="pagination-controls" v-if="filteredContent && filteredContent.length > pageSize">
                  <el-pagination
                    v-model:current-page="currentPage"
                    :page-size="pageSize"
                    layout="prev, pager, next"
                    :total="filteredContent.length"
                    @current-change="handlePageChange"
                    class="pagination"
                  />
                </div>
                
                <!-- 显示分页内容 -->
                <div class="content-items space-y-3">
                  <div v-for="(item, index) in paginatedContent" :key="index" class="content-block bg-white rounded border">
                    <div class="type-indicator" :class="`type-${item.type}`">
                      {{ getContentTypeText(item.type) }} - 第{{ item.page }}页
                      <span v-if="item.metadata" class="content-metadata">{{ item.metadata }}</span>
                    </div>
                    <div v-if="item.title" class="content-title">
                      {{ item.title }}
                    </div>
                    <div v-if="item.type === 'table'" class="table-content">
                      <div v-html="formatTableContent(item.content)"></div>
                    </div>
                    <div v-else-if="item.type === 'image'" class="image-content">
                      <img :src="item.content" alt="文档图片" class="doc-image" />
                    </div>
                    <div v-else-if="item.type === 'code'" class="code-content">
                      <pre class="code-block"><code>{{ item.content }}</code></pre>
                    </div>
                    <div v-else-if="item.type === 'list'" class="list-content">
                      <ul v-if="Array.isArray(item.content)">
                        <li v-for="(listItem, idx) in item.content" :key="idx">{{ listItem }}</li>
                      </ul>
                      <div v-else v-html="formatListContent(item.content)"></div>
                    </div>
                    <div v-else-if="item.type === 'image_text'" class="image-content">
                      <div class="image-text-heading">图像内容识别</div>
                      <div class="image-text-content">{{ item.content }}</div>
                      <div v-if="item.metadata" class="image-metadata">{{ item.metadata }}</div>
                    </div>
                    <div v-else-if="item.type === 'markdown'" class="markdown-content">
                      <!-- 渲染模式：显示格式化的markdown -->
                      <div v-if="markdownDisplayMode === 'rendered'" class="markdown-rendered" v-html="renderMarkdown(item.content)"></div>
                      <!-- 源码模式：显示原始markdown文本 -->
                      <div v-else class="markdown-source">
                        <pre class="markdown-code"><code>{{ item.content }}</code></pre>
                      </div>
                    </div>
                    <div v-else class="text-content">
                      {{ item.content }}
                    </div>
                    <div v-if="item.confidence !== undefined" class="confidence-indicator">
                      <div class="confidence-label">置信度:</div>
                      <el-progress 
                        :percentage="Math.round(item.confidence * 100)" 
                        :color="getConfidenceColor(item.confidence)"
                        :stroke-width="8"
                        :show-text="true"
                        :format="(percentage) => `${percentage}%`"
                        class="confidence-bar"
                      />
                    </div>
                    <div class="action-buttons" v-if="item.type !== 'image'">
                      <el-button type="primary" size="small" text @click="copyContent(item)">
                        <el-icon><Document /></el-icon> 复制内容
                      </el-button>
                    </div>
                  </div>
                </div>
                
                <!-- 空结果提示 -->
                <div v-if="parsedContent && (!filteredContent || filteredContent.length === 0)" class="empty-result">
                  <el-empty description="没有找到markdown内容">
                    <template #description>
                      <div>
                        <p>没有找到可显示的markdown内容</p>
                        <p class="empty-hint">文档解析完成，但没有生成markdown格式的内容</p>
                      </div>
                    </template>
                  </el-empty>
                </div>
                
                <!-- 加载中提示 -->
                <div v-if="isLoading" class="loading-indicator">
                  <el-skeleton :rows="5" animated />
                </div>
              </div>
            </div>

            <!-- 未选择文档时的提示 -->
            <div v-else
              style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%; overflow-y: auto; flex: 1;">
              <el-empty description="上传并解析文件后将在此处显示结果" />
            </div>
          </div>

          <!-- 文档记录模块 -->
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
                <el-table-column label="页数" width="80" align="center">
                  <template #default="{ row }">
                    {{ row.metadata?.total_pages || 'N/A' }}
                  </template>
                </el-table-column>
                <el-table-column label="内容数" width="80" align="center">
                  <template #default="{ row }">
                    {{ row.metadata?.total_elements || 'N/A' }}
                  </template>
                </el-table-column>
                <el-table-column label="解析方式" width="100" align="center">
                  <template #default="{ row }">
                    {{ row.metadata?.parsing_method || 'N/A' }}
                  </template>
                </el-table-column>
                <el-table-column label="创建时间" width="180" align="center">
                  <template #default="{ row }">
                    {{ row.metadata?.timestamp ? formatDate(row.metadata.timestamp) : 'N/A' }}
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="120" align="center">
                  <template #default="{ row }">
                    <el-button link type="primary" @click="handleViewDocument(row)">查看</el-button>
                    <el-button link type="danger" @click="handleDeleteDocument(row)">删除</el-button>
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
        <el-icon class="mr-2">
          <CircleClose />
        </el-icon>
        <span>{{ previewErrorMessage }}</span>
        <el-icon class="ml-4 cursor-pointer" @click="previewError = false">
          <Close />
        </el-icon>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { Document, VideoPlay, CircleClose, Close, Download, Search, ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiUrls, apiBaseUrl } from '@/config/api'
import { handleError, extractErrorMessage } from '@/utils/errorHandler'

// 状态变量
const processingParse = ref(false)
const parseStatus = ref('')
const parsedContent = ref(null)
const previewError = ref(false)
const previewErrorMessage = ref('获取预览内容失败')
const selectedFile = ref(null)
const docName = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const isLoading = ref(false)
const activeTab = ref('preview')
const searchQuery = ref('')
const loading = ref(false)
const total = ref(0)
const files = ref([]) // 存储已解析的文档列表
const markdownDisplayMode = ref('rendered') // markdown显示模式：rendered（渲染）或 source（源码）

// 过滤后的文件列表
const filteredFiles = computed(() => {
  if (!searchQuery.value) return files.value
  const query = searchQuery.value.toLowerCase()
  return files.value.filter(file => 
    (file.name.toLowerCase().includes(query)) || 
    (file.metadata?.filename && file.metadata.filename.toLowerCase().includes(query)) ||
    (file.metadata?.parsing_method && file.metadata.parsing_method.toLowerCase().includes(query))
  )
})

// 处理文件变化
const handleFileChange = (file) => {
  selectedFile.value = file.raw
  if (selectedFile.value) {
    // 设置文档名称（移除扩展名）
    docName.value = selectedFile.value.name.replace(/\.\w+$/, '')
    console.log('选择的文件:', selectedFile.value.name, '文档名:', docName.value)
    
    // 清除之前的解析结果
    parsedContent.value = null
    parseStatus.value = ''
    
    // 显示文件选择成功的提示
    ElMessage({
      message: `已选择文件: ${selectedFile.value.name}`,
      type: 'success',
      duration: 2000
    })
  }
}

// 检查文件类型
const checkFileType = (file) => {
  // 获取文件扩展名（全部转为小写）
  const extension = file.name.split('.').pop().toLowerCase()
  
  // 支持的文件类型列表
  const supportedTypes = {
    'pdf': 'PDF文档',
    'doc': 'Word文档',
    'docx': 'Word文档',
    'pptx': 'PowerPoint',
    'ppt': 'PowerPoint',
    'xlsx': 'Excel表格',
    'xls': 'Excel表格',
    'html': '网页文件',
    'htm': '网页文件',
    'epub': '电子书',
    'md': 'Markdown',
    'txt': '文本文件',
    'jpg': '图片',
    'jpeg': '图片',
    'png': '图片',
    'bmp': '图片',
    'tiff': '图片',
    'tif': '图片',
    'webp': '图片'
  }
  
  // 判断是否为支持的文件类型
  if (!supportedTypes[extension]) {
    ElMessage.error(`不支持的文件类型：${extension}，请上传PDF、Word、PowerPoint、Excel、图片、网页或文本文件`)
    return false
  }
  
  // 更新状态信息
  parseStatus.value = `已选择${supportedTypes[extension]}文件，将使用智能解析自动处理`
  
  return true
}



// 解析方法
const handleStartParse = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  // 设置状态
  processingParse.value = true
  parseStatus.value = '正在处理中...'
  parsedContent.value = null
  isLoading.value = true
  
  try {
    // 构建FormData对象
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('parsing_option', 'marker') // 统一使用marker智能解析
    
    // 发送API请求
    try {
      const response = await fetch(`${apiBaseUrl}/parse`, {
        method: 'POST',
        body: formData
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        let errorMessage = `HTTP错误! 状态码: ${response.status}`
        try {
          const errorJson = JSON.parse(errorText)
          if (errorJson.message) {
            errorMessage = errorJson.message
          }
        } catch (e) {
          console.error('解析错误响应失败:', e)
        }
        throw new Error(errorMessage)
      }
      
      const data = await response.json()
      console.log('解析响应数据:', data)
      
      // 处理不同API响应结构
      if (data.parsed_content) {
        parsedContent.value = {
          metadata: data.parsed_content.metadata || {},
          content: data.parsed_content.content || []
        }
      } else {
        parsedContent.value = data
      }
      
      // 确保内容数组存在
      if (!parsedContent.value.content) {
        parsedContent.value.content = []
      }
      
      // 处理内容数据，确保每项都有页码
      parsedContent.value.content = parsedContent.value.content.map(item => {
        if (!item.page && item.page !== 0) {
          item.page = 1
        }
        return item
      })
      
      // 按页码排序内容
      parsedContent.value.content.sort((a, b) => a.page - b.page)
      
      parseStatus.value = '解析处理完成'
      processingParse.value = false
      isLoading.value = false
      
      // 重置markdown显示模式为渲染模式
      markdownDisplayMode.value = 'rendered'
      
      // 3秒后清除成功状态并刷新文档列表
      setTimeout(() => {
        if (parseStatus.value === '解析处理完成') {
          parseStatus.value = ''
          // 刷新文档列表
          refreshDocumentList()
        }
      }, 3000)
      
    } catch (error) {
      console.error('解析错误:', error)
      const errorMessage = extractErrorMessage(error, '解析失败')
      parseStatus.value = `错误: ${errorMessage}`
      processingParse.value = false
      isLoading.value = false
      previewError.value = true
      previewErrorMessage.value = `解析失败: ${errorMessage}`
      handleError(error, { operation: '解析', showMessage: false })
    }
  } catch (error) {
    console.error('处理错误:', error)
    const errorMessage = extractErrorMessage(error, '处理失败')
    parseStatus.value = `错误: ${errorMessage}`
    processingParse.value = false
    isLoading.value = false
    handleError(error, { operation: '处理', showMessage: false })
  }
}

// 获取内容类型文本
const getContentTypeText = (type) => {
  const typeMap = {
    'text': '文本',
    'heading': '标题',
    'table': '表格',
    'image': '图像',
    'image_text': '图像文本',
    'list': '列表',
    'code': '代码',
    'error': '错误'
  }
  return typeMap[type] || type
}

// 检查是否有markdown内容
const hasMarkdownContent = computed(() => {
  if (!parsedContent.value || !parsedContent.value.content) {
    return false
  }
  return parsedContent.value.content.some(item => item.type === 'markdown')
})

// 过滤后的内容（只显示markdown类型）
const filteredContent = computed(() => {
  if (!parsedContent.value || !parsedContent.value.content) {
    return []
  }
  
  // 只显示markdown类型的内容，过滤掉图片元数据等辅助信息
  return parsedContent.value.content.filter(item => item.type === 'markdown')
})

// 处理分页逻辑
const paginatedContent = computed(() => {
  if (!filteredContent.value || filteredContent.value.length === 0) {
    return []
  }
  
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredContent.value.slice(start, end)
})

// 处理页面切换
const handlePageChange = (page) => {
  currentPage.value = page
  // 滚动到顶部
  const container = document.querySelector('.content-container')
  if (container) {
    container.scrollTop = 0
  }
}

// 获取置信度颜色
const getConfidenceColor = (confidence) => {
  if (confidence >= 0.8) return '#67C23A'      // 绿色 - 高置信度
  if (confidence >= 0.6) return '#409EFF'      // 蓝色 - 中等置信度  
  if (confidence >= 0.4) return '#E6A23C'      // 黄色 - 低置信度
  return '#F56C6C'                             // 红色 - 很低置信度
}

const handleCancel = () => {
  ElMessageBox.confirm(
    '确定要取消解析过程吗？这将中断当前的处理。',
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    parseStatus.value = '解析已取消'
    processingParse.value = false
    ElMessage.info('已取消解析过程')
  }).catch(() => { })
}

// 格式化表格内容
const formatTableContent = (content) => {
  // 如果已经是HTML
  if (content.startsWith('<table') || content.includes('<table')) {
    return content;
  }
  
  // 将Markdown表格转换为HTML
  if (content.includes('|')) {
    let html = '<table class="md-table">';
    const rows = content.trim().split('\n');
    
    rows.forEach((row, index) => {
      // 跳过分隔行
      if (row.replace(/[\|\-\s]/g, '') === '') return;
      
      const isHeader = index === 0;
      const cells = row.split('|').slice(1, -1); // 去掉首尾的 |
      
      html += '<tr>';
      cells.forEach(cell => {
        if (isHeader) {
          html += `<th>${cell.trim()}</th>`;
        } else {
          html += `<td>${cell.trim()}</td>`;
        }
      });
      html += '</tr>';
    });
    
    html += '</table>';
    return html;
  }
  
  return `<pre>${content}</pre>`;
}

// 格式化数字(添加千位分隔符)
const formatNumber = (num) => {
  if (num === undefined || num === null) return 'N/A'
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 导出解析结果
const handleExportResult = () => {
  if (!filteredContent.value || filteredContent.value.length === 0) {
    ElMessage.warning('没有可导出的markdown内容')
    return
  }
  
  try {
    // 创建要导出的数据（只导出markdown内容）
    const exportData = {
      metadata: {
        ...parsedContent.value.metadata,
        content_type: 'markdown_only',
        exported_items: filteredContent.value.length
      },
      content: filteredContent.value
    }
    
    // 转换为JSON字符串
    const jsonString = JSON.stringify(exportData, null, 2)
    
    // 创建Blob
    const blob = new Blob([jsonString], { type: 'application/json' })
    
    // 创建下载链接
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${docName.value || 'document'}_markdown_content.json`
    
    // 触发下载
    document.body.appendChild(link)
    link.click()
    
    // 清理
    URL.revokeObjectURL(url)
    document.body.removeChild(link)
    
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('导出错误:', error)
    handleError(error, { operation: '导出' })
  }
}

// 格式化列表内容
const formatListContent = (content) => {
  // 检测是否已包含HTML列表标记
  if (content.includes('<ul>') || content.includes('<ol>')) {
    return content;
  }
  
  // 尝试转换普通文本为列表
  const lines = content.split('\n');
  let html = '<ul>';
  
  lines.forEach(line => {
    line = line.trim();
    if (line) {
      // 检测常见的列表项标记，如 - * •
      if (line.match(/^[\-\*\•\d+\.\s]+/)) {
        line = line.replace(/^[\-\*\•\d+\.\s]+/, '');
      }
      html += `<li>${line}</li>`;
    }
  });
  
  html += '</ul>';
  return html;
}

// 渲染markdown内容
const renderMarkdown = (content) => {
  if (!content) return ''
  
  // 基本的markdown渲染（简单实现）
  let rendered = content
    // 标题
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    // 粗体
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    // 斜体
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // 链接
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
    // 图片（支持base64和路径）
    .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, src) => {
      // 为图片添加加载错误处理和样式
      const imgClass = src.startsWith('data:image/') ? 'markdown-base64-image' : 'markdown-file-image';
      return `<img src="${src}" alt="${alt}" class="${imgClass}" style="max-width: 100%; height: auto; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';" /><div style="display:none; padding: 8px; background-color: #f5f5f5; border: 1px dashed #ccc; border-radius: 4px; text-align: center; color: #999;">图片加载失败: ${alt}</div>`;
    })
    // 行内代码
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // 换行
    .replace(/\n/g, '<br>')
  
  // 处理表格
  if (rendered.includes('|')) {
    const lines = rendered.split('<br>')
    let inTable = false
    let tableHtml = ''
    let processedLines = []
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()
      
      if (line.includes('|') && !line.startsWith('<')) {
        if (!inTable) {
          inTable = true
          tableHtml = '<table class="markdown-table"><thead>'
        }
        
        // 跳过分隔行
        if (line.replace(/[\|\-\s]/g, '') === '') continue
        
        const cells = line.split('|').slice(1, -1) // 去掉首尾的空元素
        const isFirstRow = i === 0 || !inTable
        
        if (isFirstRow && inTable) {
          tableHtml += '<tr>'
          cells.forEach(cell => {
            tableHtml += `<th>${cell.trim()}</th>`
          })
          tableHtml += '</tr></thead><tbody>'
        } else {
          tableHtml += '<tr>'
          cells.forEach(cell => {
            tableHtml += `<td>${cell.trim()}</td>`
          })
          tableHtml += '</tr>'
        }
      } else {
        if (inTable) {
          tableHtml += '</tbody></table>'
          processedLines.push(tableHtml)
          tableHtml = ''
          inTable = false
        }
        processedLines.push(line)
      }
    }
    
    if (inTable) {
      tableHtml += '</tbody></table>'
      processedLines.push(tableHtml)
    }
    
    rendered = processedLines.join('<br>')
  }
  
  return rendered
}

// 复制内容到剪贴板
const copyContent = (item) => {
  let content = '';
  
  if (item.type === 'table') {
    // 获取表格文本内容（不带HTML标签）
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = formatTableContent(item.content);
    content = tempDiv.textContent || tempDiv.innerText || item.content;
  } else if (item.type === 'markdown') {
    // 对于markdown，根据当前显示模式复制对应内容
    if (markdownDisplayMode.value === 'source') {
      content = item.content; // 复制原始markdown源码
    } else {
      // 复制渲染后的纯文本（去除HTML标签）
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = renderMarkdown(item.content);
      content = tempDiv.textContent || tempDiv.innerText || item.content;
    }
  } else {
    content = item.content;
  }
  
  // 使用Clipboard API
  navigator.clipboard.writeText(content).then(() => {
    ElMessage.success('内容已复制到剪贴板');
  }).catch(err => {
    console.error('复制失败:', err);
    ElMessage.error('复制失败，请手动选择并复制');
  });
}

// 获取已解析的文档列表
const fetchParsedDocuments = async () => {
  loading.value = true
  try {
    const response = await fetch(`${apiBaseUrl}/documents?type=parsed`)
    
    if (!response.ok) {
      throw new Error(`HTTP错误! 状态码: ${response.status}`)
    }
    
    const data = await response.json()
    console.log('获取到的已解析文档列表:', data)
    
    if (data && Array.isArray(data.documents)) {
      // 直接使用返回的文档列表数据
      files.value = data.documents
      total.value = files.value.length
    } else {
      files.value = []
      total.value = 0
    }
  } catch (error) {
    console.error('获取已解析文档列表失败:', error)
    ElMessage.error('获取已解析文档列表失败')
    files.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// 查看文档详情
const handleViewDocument = async (row) => {
  // 切换到预览标签页
  activeTab.value = 'preview'
  isLoading.value = true
  
  try {
    // 获取文档详情
    const docId = row.id || row.name.replace(/\.json$/, '')
    const encodedId = encodeURIComponent(docId)
    const response = await fetch(`${apiBaseUrl}/documents/${encodedId}.json?type=parsed`)
    
    if (!response.ok) {
      throw new Error(`HTTP错误! 状态码: ${response.status}`)
    }
    
    const data = await response.json()
    console.log('文档详情数据:', data)
    
    // 处理文档详情数据
    parsedContent.value = data
    
    // 确保内容数组存在
    if (!parsedContent.value.content) {
      parsedContent.value.content = []
    }
    
    // 处理内容数据，确保每项都有页码
    parsedContent.value.content = parsedContent.value.content.map(item => {
      if (!item.page && item.page !== 0) {
        item.page = 1
      }
      return item
    })
    
    // 按页码排序内容
    parsedContent.value.content.sort((a, b) => a.page - b.page)
    
    // 重置markdown显示模式为渲染模式
    markdownDisplayMode.value = 'rendered'
    
    ElMessage.success(`查看文档: ${row.metadata?.filename || row.name}`)
  } catch (error) {
    console.error('获取文档详情失败:', error)
    previewError.value = true
    const errorMessage = extractErrorMessage(error, '获取文档详情失败')
    previewErrorMessage.value = `获取文档详情失败: ${errorMessage}`
    handleError(error, { operation: '获取文档详情' })
  } finally {
    isLoading.value = false
  }
}

// 删除文档
const handleDeleteDocument = (row) => {
  ElMessageBox.confirm(
    '确定要删除该文档吗？此操作不可逆。',
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      const docId = row.id || row.name.replace(/\.json$/, '')
      const encodedId = encodeURIComponent(docId)
      const response = await fetch(`${apiBaseUrl}/documents/${encodedId}?type=parsed`, {
        method: 'DELETE'
      })
      
      if (!response.ok) {
        throw new Error(`HTTP错误! 状态码: ${response.status}`)
      }
      
      // 从列表中移除
      const index = files.value.findIndex(item => item.id === row.id || item.name === row.name)
      if (index !== -1) {
        files.value.splice(index, 1)
        total.value = files.value.length
      }
      
      // 如果当前正在预览该文件，清除预览
      if (parsedContent.value && parsedContent.value.metadata?.filename === row.metadata?.filename) {
        parsedContent.value = null
      }
      
      ElMessage.success('删除文档成功')
    } catch (error) {
      console.error('删除文档失败:', error)
      handleError(error, { operation: '删除文档' })
    }
  }).catch(() => {
    // 取消删除，不做任何操作
  })
}

// 页面加载时获取已解析文档列表
onMounted(() => {
  // 获取已解析文档列表
  fetchParsedDocuments()
})

// 在解析完成后刷新文档列表
const refreshDocumentList = () => {
  fetchParsedDocuments()
}
</script>

<style scoped>
/* 上传区域样式 */
.upload-demo {
  display: inline-block;
  width: 100%;
}

/* 修改内容样式 */
.content-container {
  position: relative;
  overflow-y: auto !important;
  overflow-x: hidden !important;
  scrollbar-width: auto !important;
  /* Firefox */
  scrollbar-color: #909399 #f5f7fa !important;
  /* Firefox */
  min-height: 200px;
  max-height: 100% !important;
}

.content-block {
  color: #303133;
  font-size: 14px;
  line-height: 1.6;
  padding: 16px;
  background-color: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  position: relative;
  transition: all 0.3s ease;
}

.content-block:hover {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.type-indicator {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
  font-weight: 500;
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background-color: #f5f7fa;
}

.type-title {
  background-color: #ecf5ff;
  color: #409eff;
}

.type-text {
  background-color: #f0f9eb;
  color: #67c23a;
}

.type-table {
  background-color: #fdf6ec;
  color: #e6a23c;
}

.type-image {
  background-color: #f5f5fa;
  color: #909399;
}

.content-title {
  font-size: 16px;
  font-weight: 600;
  margin: 8px 0 12px 0;
  color: #303133;
  border-left: 3px solid #409eff;
  padding-left: 8px;
  line-height: 1.4;
}

.text-content {
  white-space: pre-wrap;
  word-break: break-word;
  color: #606266;
  line-height: 1.8;
  font-size: 14px;
}

.table-content {
  overflow-x: auto;
  margin: 12px 0;
  border-radius: 4px;
  background-color: #fafafa;
}

.parsed-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 13px;
}

.parsed-table th,
.parsed-table td {
  padding: 8px 12px;
  border: 1px solid #dcdfe6;
}

.parsed-table th {
  background-color: #f5f7fa;
  font-weight: 600;
  color: #303133;
}

.parsed-table tr:nth-child(even) td {
  background-color: #fafafa;
}

.parsed-table tr:hover td {
  background-color: #ecf5ff;
}

.code-content {
  margin: 12px 0;
}

.code-block {
  background-color: #282c34;
  border-radius: 4px;
  padding: 16px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  overflow-x: auto;
  white-space: pre-wrap;
  color: #abb2bf;
  line-height: 1.6;
  border: 1px solid #3e4451;
}

.confidence-indicator {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: #f9f9f9;
  padding: 8px;
  border-radius: 4px;
}

.confidence-label {
  font-size: 12px;
  color: #909399;
  width: 60px;
}

.confidence-bar {
  flex: 1;
}

.pagination-controls {
  display: flex;
  justify-content: center;
  margin: 16px 0;
  padding: 8px 0;
  background-color: #f5f7fa;
  border-radius: 4px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.loading-indicator {
  padding: 20px;
  background: white;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.content-metadata {
  margin-left: 8px;
  font-size: 11px;
  opacity: 0.7;
  background-color: rgba(0, 0, 0, 0.05);
  padding: 1px 6px;
  border-radius: 10px;
}

.image-content {
  text-align: center;
  margin: 12px 0;
}

.doc-image {
  max-width: 100%;
  max-height: 400px;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.empty-result {
  padding: 24px;
  text-align: center;
}

/* Webkit浏览器的滚动条样式 */
.content-container::-webkit-scrollbar {
  width: 10px !important;
  height: 0 !important;
  /* 隐藏水平滚动条 */
  display: block !important;
  visibility: visible !important;
}

.content-container::-webkit-scrollbar-thumb {
  background: #909399 !important;
  border-radius: 5px !important;
  border: 2px solid #fff !important;
}

.content-container::-webkit-scrollbar-track {
  background: #fff !important;
  border-radius: 5px !important;
  visibility: visible !important;
  display: block !important;
}

.content-container::-webkit-scrollbar-corner {
  background: #f5f7fa !important;
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
  .content-container {
    padding: 12px;
    overflow-x: hidden !important;
  }
}

.empty-tips {
  margin-top: 24px;
  color: #909399;
  font-size: 14px;
  width: 80%;
  max-width: 400px;
}

.tip-item {
  display: flex;
  align-items: center;
  margin: 12px 0;
  padding: 10px 16px;
  background-color: #f5f7fa;
  border-radius: 6px;
  transition: all 0.3s;
}

.tip-item:hover {
  background-color: #ecf5ff;
  transform: translateY(-2px);
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.tip-icon {
  margin-right: 8px;
  font-size: 18px;
  color: #409eff;
}

.doc-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px 24px;
  margin-top: 8px;
}

.doc-info-item {
  display: flex;
  align-items: center;
}

.info-label {
  color: #909399;
  margin-right: 8px;
  min-width: 70px;
}

.info-value {
  color: #303133;
  font-weight: 500;
}

.content-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin: 16px 0;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px dashed #ebeef5;
}

.empty-hint {
  font-size: 13px;
  color: #909399;
  margin-top: 8px;
}

.parsed-list {
  margin: 0;
  padding-left: 20px;
}

.parsed-list li {
  margin-bottom: 8px;
  line-height: 1.5;
}

.list-content {
  line-height: 1.6;
}

/* 解析状态提示样式 */
.parse-status {
  margin-top: 16px;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 14px;
}

.success {
  background-color: #f0f9eb;
  color: #67c23a;
  border: 1px solid #e1f3d8;
}

.error {
  background-color: #fef0f0;
  color: #f56c6c;
  border: 1px solid #fde2e2;
}

.info {
  background-color: #f4f4f5;
  color: #909399;
  border: 1px solid #e9e9eb;
}

.warning {
  background-color: #fdf6ec;
  color: #e6a23c;
  border: 1px solid #faecd8;
}

.doc-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-gap: 8px;
}

.doc-info-item {
  display: flex;
  font-size: 13px;
}

.info-label {
  color: #909399;
  margin-right: 4px;
  flex-shrink: 0;
}

.info-value {
  color: #606266;
  word-break: break-all;
}

.content-block {
  margin-bottom: 16px;
  padding: 12px;
  border-radius: 6px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06);
  position: relative;
  background-color: #fff;
  border: 1px solid #ebeef5;
}

.type-indicator {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
  padding-bottom: 4px;
  border-bottom: 1px dashed #ebeef5;
}

.type-table {
  color: #409eff;
}

.type-image, .type-image_text {
  color: #67c23a;
}

.type-heading {
  color: #e6a23c;
}

.content-title {
  font-weight: bold;
  margin-bottom: 8px;
  font-size: 15px;
}

.content-metadata {
  float: right;
  font-style: italic;
  color: #c0c4cc;
}

.table-content {
  max-width: 100%;
  overflow-x: auto;
  margin: 8px 0;
  font-size: 14px;
  line-height: 1.5;
}

.image-content {
  margin: 12px 0;
}

.image-text-heading {
  font-weight: 500;
  color: #67c23a;
  margin-bottom: 8px;
  font-size: 14px;
}

.image-text-content {
  line-height: 1.5;
  white-space: pre-wrap;
  background-color: #f8f8f8;
  padding: 8px;
  border-radius: 4px;
  font-size: 14px;
}

.image-metadata {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  font-style: italic;
}

.doc-image {
  max-width: 100%;
  max-height: 300px;
  margin: 8px 0;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}

.code-content {
  margin: 8px 0;
}

.code-block {
  background-color: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-family: monospace;
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
  margin: 0;
}

.list-content ul {
  margin: 8px 0;
  padding-left: 20px;
}

.confidence-indicator {
  margin-top: 8px;
  display: flex;
  align-items: center;
}

.confidence-label {
  margin-right: 8px;
  font-size: 12px;
  color: #909399;
  width: 60px;
}

.confidence-bar {
  flex: 1;
}

.action-buttons {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}

.pagination-controls {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}

.empty-hint {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

/* Markdown显示模式样式 */
.markdown-mode-tabs {
  display: flex;
  justify-content: center;
  background-color: #f8f9fa;
  border-radius: 6px;
  padding: 8px;
}

.markdown-content {
  margin: 12px 0;
}

.markdown-rendered {
  line-height: 1.6;
  color: #333;
}

.markdown-rendered h1 {
  font-size: 24px;
  font-weight: bold;
  margin: 16px 0 12px 0;
  color: #2c3e50;
  border-bottom: 2px solid #3498db;
  padding-bottom: 8px;
}

.markdown-rendered h2 {
  font-size: 20px;
  font-weight: bold;
  margin: 14px 0 10px 0;
  color: #34495e;
  border-bottom: 1px solid #bdc3c7;
  padding-bottom: 6px;
}

.markdown-rendered h3 {
  font-size: 18px;
  font-weight: bold;
  margin: 12px 0 8px 0;
  color: #34495e;
}

.markdown-rendered strong {
  font-weight: bold;
  color: #2c3e50;
}

.markdown-rendered em {
  font-style: italic;
  color: #7f8c8d;
}

.markdown-rendered code {
  background-color: #f8f9fa;
  color: #e83e8c;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.9em;
}

.markdown-rendered a {
  color: #3498db;
  text-decoration: none;
}

.markdown-rendered a:hover {
  text-decoration: underline;
}

.markdown-rendered img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin: 8px 0;
}

.markdown-base64-image {
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
  padding: 4px;
  cursor: zoom-in;
}

.markdown-base64-image:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: scale(1.02);
  transition: all 0.3s ease;
}

.markdown-file-image {
  border: 1px solid #dee2e6;
  background-color: #ffffff;
}

.markdown-table {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  background-color: white;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.markdown-table th {
  background-color: #f8f9fa;
  color: #2c3e50;
  font-weight: 600;
  padding: 12px;
  text-align: left;
  border-bottom: 2px solid #dee2e6;
}

.markdown-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #dee2e6;
  color: #495057;
}

.markdown-table tr:nth-child(even) td {
  background-color: #f8f9fa;
}

.markdown-table tr:hover td {
  background-color: #e9ecef;
}

.markdown-source {
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  overflow: hidden;
}

.markdown-code {
  background-color: #2d3748;
  color: #e2e8f0;
  padding: 16px;
  margin: 0;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
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
  /* 隐藏水平滚动条 */
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