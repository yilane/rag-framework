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
                <div style="margin-bottom: 8px; font-size: 14px;">上传 PDF</div>
                <el-upload class="upload-demo" action="#" :auto-upload="false" :on-change="handleFileChange"
                  accept=".pdf,.doc,.docx,.txt">
                  <el-button type="primary">选择文件</el-button>
                </el-upload>
                <div style="margin-top: 8px; color: #909399;" v-if="!selectedFile">未选择任何文件</div>
                <div style="margin-top: 8px; color: #606266;" v-else>已选择: {{ selectedFile.name }}</div>
              </div>

              <!-- 加载工具选择 -->
              <div style="margin-top: 16px;">
                <div style="margin-bottom: 8px; font-size: 14px;">加载工具</div>
                <el-select v-model="loadingMethod" style="width: 100%;">
                  <el-option label="PyMuPDF" value="pymupdf" />
                  <el-option label="PyPDF" value="pypdf" />
                  <el-option label="Unstructured" value="unstructured" />
                  <el-option label="PDF Plumber" value="pdfplumber" />
                </el-select>
              </div>

              <!-- 解析选项 -->
              <div style="margin-top: 16px;">
                <div style="margin-bottom: 8px; font-size: 14px;">解析选项</div>
                <el-select v-model="parsingOption" style="width: 100%;">
                  <el-option label="全部文本" value="all_text" />
                  <el-option label="按页解析" value="by_pages" />
                  <el-option label="按标题解析" value="by_titles" />
                  <el-option label="文本和表格" value="text_and_tables" />
                </el-select>
              </div>

              <div style="margin-top: 16px;">
                <el-button type="primary" style="width: 100%;" @click="handleStartParse" :loading="processingParse"
                  :disabled="!selectedFile">
                  解析文件
                </el-button>
              </div>

              <div v-if="parseStatus" style="margin-top: 16px; padding: 12px; border-radius: 4px; font-size: 14px;"
                :class="parseStatus.includes('错误') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'">
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
              <span class="font-medium">解析结果</span>
            </div>
          </template>

          <!-- 预览内容 -->
          <div style="display: flex; flex-direction: column; flex: 1; overflow: hidden; height: 100%;">
            <div v-if="parsedContent"
              style="width: 100%; text-align: left; display: flex; flex-direction: column; height: 100%; overflow: auto;">
              <!-- 文档信息卡片 -->
              <div
                style="margin-bottom: 16px; padding: 12px; border-radius: 4px; background-color: #f7f7f7; border: 1px solid #e4e7ed;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <h4 style="margin: 0 0 8px 0; font-size: 15px; font-weight: 500; color: #303133;">文档信息</h4>
                  <el-button size="small" type="primary" icon="Download" @click="handleExportResult" v-if="parsedContent && parsedContent.content && parsedContent.content.length > 0">
                    导出结果
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
                      <span class="info-value">{{ parsedContent.content?.length || 0 }} 项</span>
                    </div>
                    <div class="doc-info-item">
                      <span class="info-label">解析方法:</span>
                      <span class="info-value">{{ parsedContent.metadata?.parsing_method || 'N/A' }}</span>
                    </div>
                    <div class="doc-info-item">
                      <span class="info-label">处理时间:</span>
                      <span class="info-value">{{ parsedContent.metadata?.timestamp ? formatDate(parsedContent.metadata.timestamp) : 'N/A' }}</span>
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
                <!-- 内容分页控件 -->
                <div class="pagination-controls" v-if="parsedContent && parsedContent.content && parsedContent.content.length > pageSize">
                  <el-pagination
                    v-model:current-page="currentPage"
                    :page-size="pageSize"
                    layout="prev, pager, next"
                    :total="parsedContent.content.length"
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
                    <div v-else class="text-content">
                      {{ item.content }}
                    </div>
                    <div v-if="item.confidence !== undefined" class="confidence-indicator">
                      <div class="confidence-label">置信度:</div>
                      <el-progress 
                        :percentage="item.confidence * 100" 
                        :status="getConfidenceStatus(item.confidence)"
                        :stroke-width="8"
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
                <div v-if="parsedContent && parsedContent.content && parsedContent.content.length === 0" class="empty-result">
                  <el-empty description="没有找到解析结果">
                    <template #description>
                      <div>
                        <p>没有找到解析结果</p>
                        <p class="empty-hint">请尝试更改解析选项或使用其他加载工具</p>
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
        </el-card>
      </div>
    </div>

    <!-- 进度对话框 -->
    <el-dialog v-model="progressVisible" title="解析进度" width="500px" :close-on-click-modal="false"
      :close-on-press-escape="false">
      <el-progress :percentage="progress" :status="progressStatus" :stroke-width="15" />
      <div style="margin-top: 16px; text-align: center; color: #909399;">
        {{ progressText }}
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleCancel">取消</el-button>
        </span>
      </template>
    </el-dialog>

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
import { Document, VideoPlay, CircleClose, Close, Download } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiUrls, apiBaseUrl } from '@/config/api'

// 状态变量
const progressVisible = ref(false)
const progress = ref(0)
const progressStatus = ref('')
const progressText = ref('')
const processingParse = ref(false)
const parseStatus = ref('')
const parsedContent = ref(null)
const previewError = ref(false)
const previewErrorMessage = ref('获取预览内容失败')
const selectedFile = ref(null)
const loadingMethod = ref('pymupdf')
const parsingOption = ref('all_text')
const docName = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const isLoading = ref(false)

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
  
  // 显示进度对话框
  progressVisible.value = true
  progress.value = 0
  progressStatus.value = ''
  progressText.value = '正在解析文件...'
  
  try {
    // 构建FormData对象
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('loading_method', loadingMethod.value)
    formData.append('parsing_option', parsingOption.value)
    
    // 模拟进度动画
    const progressTimer = startProgressAnimation()
    
    // 发送API请求
    try {
      const response = await fetch(`${apiBaseUrl}/parse`, {
        method: 'POST',
        body: formData
      })
      
      clearInterval(progressTimer)
      
      if (!response.ok) {
        const errorText = await response.text()
        let errorMessage = `HTTP错误! 状态码: ${response.status}`
        try {
          const errorJson = JSON.parse(errorText)
          if (errorJson.message) {
            errorMessage = errorJson.message
          }
        } catch (e) {
          // 如果响应不是JSON格式，使用默认错误信息
          console.error('解析错误响应失败:', e)
        }
        throw new Error(errorMessage)
      }
      
      const data = await response.json()
      console.log('解析响应数据:', data)
      
      // 处理不同API响应结构
      if (data.parsed_content) {
        // 适配ParseFile.jsx中使用的数据结构
        parsedContent.value = {
          metadata: data.parsed_content.metadata || {},
          content: data.parsed_content.content || []
        }
      } else {
        // 直接使用返回的数据结构
        parsedContent.value = data
      }
      
      // 确保内容数组存在
      if (!parsedContent.value.content) {
        parsedContent.value.content = []
      }
      
      // 处理内容数据，确保每项都有页码
      parsedContent.value.content = parsedContent.value.content.map(item => {
        if (!item.page && item.page !== 0) {
          item.page = 1 // 默认页码
        }
        return item
      })
      
      // 按页码排序内容
      parsedContent.value.content.sort((a, b) => a.page - b.page)
      
      // 完成进度
      progress.value = 100
      progressStatus.value = 'success'
      progressText.value = '解析完成'
      
      setTimeout(() => {
        progressVisible.value = false
        parseStatus.value = '解析处理完成'
        processingParse.value = false
        isLoading.value = false
        
        // 显示解析结果统计
        const contentCount = parsedContent.value.content.length
        const pageCount = parsedContent.value.metadata?.total_pages || '未知'
        
        ElMessage({
          message: `文件解析完成，共 ${contentCount} 个内容项，${pageCount} 页`,
          type: 'success',
          duration: 3000
        })
      }, 1000)
    } catch (error) {
      clearInterval(progressTimer)
      console.error('解析错误:', error)
      
      progressStatus.value = 'exception'
      progressText.value = `错误: ${error.message}`
      
      setTimeout(() => {
        progressVisible.value = false
      }, 2000)
      
      parseStatus.value = `错误: ${error.message}`
      processingParse.value = false
      isLoading.value = false
      previewError.value = true
      previewErrorMessage.value = `解析失败: ${error.message}`
      ElMessage.error(`解析失败: ${error.message}`)
    }
  } catch (error) {
    console.error('处理错误:', error)
    parseStatus.value = `错误: ${error.message}`
    processingParse.value = false
    progressVisible.value = false
    isLoading.value = false
  }
}

// 启动进度动画
const startProgressAnimation = () => {
  return setInterval(() => {
    if (progress.value < 90) {
      progress.value += 5
      
      // 更新进度文本
      if (progress.value < 20) {
        progressText.value = '正在加载文件...'
      } else if (progress.value < 40) {
        progressText.value = '正在提取文本内容...'
      } else if (progress.value < 60) {
        progressText.value = '正在分析文档结构...'
      } else if (progress.value < 80) {
        progressText.value = '正在处理数据...'
      } else {
        progressText.value = '即将完成...'
      }
    }
  }, 200)
}

// 获取内容类型文本
const getContentTypeText = (type) => {
  const types = {
    'title': '标题',
    'text': '文本',
    'table': '表格',
    'image': '图片',
    'list': '列表',
    'code': '代码',
    'equation': '公式',
    'citation': '引用',
    'footnote': '脚注'
  }
  return types[type] || type
}

// 处理分页逻辑
const paginatedContent = computed(() => {
  if (!parsedContent.value || !parsedContent.value.content) {
    return []
  }
  
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return parsedContent.value.content.slice(start, end)
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

// 获取置信度状态
const getConfidenceStatus = (confidence) => {
  if (confidence >= 0.8) return 'success'
  if (confidence >= 0.5) return 'warning'
  return 'exception'
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
    progressVisible.value = false
    progress.value = 0
    progressStatus.value = ''
    progressText.value = ''
    parseStatus.value = '解析已取消'
    processingParse.value = false
    ElMessage.info('已取消解析过程')
  }).catch(() => { })
}

// 格式化表格内容
const formatTableContent = (content) => {
  if (!content) return '';
  
  // 检查是否已经是HTML格式
  if (content.startsWith('<table')) {
    return content;
  }
  
  // 处理Markdown风格的表格
  if (content.includes('|')) {
    const rows = content.trim().split('\n');
    let html = '<table class="parsed-table">';
    
    rows.forEach((row, rowIndex) => {
      // 跳过分隔行 (----)
      if (row.trim().replace(/[\-\|]/g, '') === '') {
        return;
      }
      
      const cells = row.split('|').filter(cell => cell.trim() !== '');
      
      if (cells.length > 0) {
        html += '<tr>';
        cells.forEach(cell => {
          const tag = rowIndex === 0 ? 'th' : 'td';
          html += `<${tag}>${cell.trim()}</${tag}>`;
        });
        html += '</tr>';
      }
    });
    
    html += '</table>';
    return html;
  }
  
  // 纯文本，按行分割
  return content.replace(/\n/g, '<br>');
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
  if (!parsedContent.value) {
    ElMessage.warning('没有可导出的内容')
    return
  }
  
  try {
    // 创建要导出的数据
    const exportData = {
      metadata: parsedContent.value.metadata,
      content: parsedContent.value.content
    }
    
    // 转换为JSON字符串
    const jsonString = JSON.stringify(exportData, null, 2)
    
    // 创建Blob
    const blob = new Blob([jsonString], { type: 'application/json' })
    
    // 创建下载链接
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${docName.value || 'document'}_parsed_result.json`
    
    // 触发下载
    document.body.appendChild(link)
    link.click()
    
    // 清理
    URL.revokeObjectURL(url)
    document.body.removeChild(link)
    
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('导出错误:', error)
    ElMessage.error(`导出失败: ${error.message}`)
  }
}

// 格式化列表内容
const formatListContent = (content) => {
  if (!content) return '';
  
  // 检查是否已经是HTML格式
  if (content.startsWith('<ul') || content.startsWith('<ol')) {
    return content;
  }
  
  // 处理纯文本列表
  if (typeof content === 'string' && content.includes('\n')) {
    const items = content.split('\n').filter(item => item.trim() !== '');
    let html = '<ul class="parsed-list">';
    
    items.forEach(item => {
      // 去除常见的列表标记
      const cleanItem = item.replace(/^[\s•\-\*\d+\.]+/, '').trim();
      if (cleanItem) {
        html += `<li>${cleanItem}</li>`;
      }
    });
    
    html += '</ul>';
    return html;
  }
  
  return content;
}

// 复制内容到剪贴板
const copyContent = (item) => {
  let content = '';
  
  if (item.type === 'table') {
    // 获取表格文本内容（不带HTML标签）
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = formatTableContent(item.content);
    content = tempDiv.textContent || tempDiv.innerText || item.content;
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

// 页面加载时执行
onMounted(() => {
  // 初始化逻辑
})
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