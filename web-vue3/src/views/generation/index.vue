<template>
  <div style="width: 96%; height: calc(90vh - 56px); overflow-y: auto; overflow-x: hidden; padding: 24px; background-color: #f5f7fa; display: flex; flex-direction: column;">
    <div style="display: flex; width: 100%; flex: 1; gap: 20px;">
      <!-- 左侧：对话配置 -->
      <div style="width: 25%; min-width: 300px; max-width: 350px;">
        <el-card style="width: 100%; height: calc(90vh - 104px); overflow-x: hidden;" shadow="hover">
          <div style="display: flex; flex-direction: column; gap: 8px;">
            <!-- 搜索结果文件选择 -->
            <div style="margin-bottom: 8px;">
              <div style="margin-bottom: 4px; font-size: 14px; color: #606266;">搜索结果文件</div>
              <el-select v-model="selectedFile" style="width: 100%;" placeholder="选择搜索结果文件...">
                <el-option
                  v-for="file in searchFiles"
                  :key="file.id"
                  :label="file.name"
                  :value="file.id"
                />
              </el-select>
            </div>

            <template v-if="selectedFile">
              <!-- 问题输入 -->
              <div style="margin-bottom: 8px;">
                <div style="margin-bottom: 4px; font-size: 14px; color: #606266;">问题</div>
                <el-input
                  v-model="query"
                  type="textarea"
                  :rows="4"
                  placeholder="请输入您的问题..."
                  resize="none"
                />
              </div>

              <!-- 提供商选择 -->
              <div style="margin-bottom: 8px;">
                <div style="margin-bottom: 4px; font-size: 14px; color: #606266;">提供商</div>
                <el-select v-model="provider" style="width: 100%;" placeholder="选择提供商...">
                  <el-option
                    v-for="(modelList, p) in models"
                    :key="p"
                    :label="p"
                    :value="p"
                  />
                </el-select>
              </div>

              <!-- 模型选择 -->
              <div v-if="provider" style="margin-bottom: 8px;">
                <div style="margin-bottom: 4px; font-size: 14px; color: #606266;">模型</div>
                <el-select v-model="modelName" style="width: 100%;" placeholder="选择模型...">
                  <el-option
                    v-for="(name, id) in models[provider]"
                    :key="id"
                    :label="id === 'deepseek-v3' ? 'DeepSeek V3' : 
                           id === 'deepseek-r1' ? 'DeepSeek R1' : name"
                    :value="id"
                  />
                </el-select>
              </div>

              <!-- API密钥输入 -->
              <div v-if="['openai', 'deepseek'].includes(provider)" style="margin-bottom: 8px;">
                <div style="margin-bottom: 4px; font-size: 14px; color: #606266;">API密钥</div>
                <el-input
                  v-model="apiKey"
                  type="password"
                  placeholder="请输入API密钥..."
                  show-password
                />
              </div>

              <!-- 思维链显示选项 -->
              <div v-if="provider === 'deepseek' && modelName === 'deepseek-r1'" style="margin-bottom: 8px;">
                <el-checkbox v-model="showReasoning">显示思维链过程</el-checkbox>
              </div>

              <!-- 生成按钮 -->
              <el-button
                type="primary"
                :loading="generating"
                @click="handleGenerate"
                style="width: 100%;"
              >
                {{ generating ? '生成中...' : '生成' }}
              </el-button>

              <!-- 状态信息 -->
              <div v-if="status" 
                class="status-message"
                :class="{
                  'error': status.includes('错误') || status.includes('失败'),
                  'success': status.includes('完成') || status.includes('成功'),
                  'info': !status.includes('错误') && !status.includes('失败') && !status.includes('完成') && !status.includes('成功')
                }">
                {{ status }}
              </div>
            </template>
          </div>
        </el-card>
      </div>
      
      <!-- 右侧：搜索上下文和生成结果 -->
      <div style="flex: 1; min-width: 0; max-width: calc(100% - 370px);">
        <el-card style="width: 95%; height: calc(90vh - 104px); display: flex; flex-direction: column; overflow-x: hidden;" shadow="hover">
          <template #header>
            <div style="font-size: 16px; font-weight: 500; color: #303133;">
              {{ selectedFile ? '搜索上下文' : '生成内容' }}
            </div>
          </template>
          
          <template v-if="selectedFile">
            <!-- 搜索上下文 -->
            <div style="flex: 1; overflow-y: auto;">
              <template v-if="searchResults.length > 0">
                <div v-for="(result, idx) in searchResults" :key="idx" 
                     style="padding: 16px; margin-bottom: 12px; border-radius: 4px; background-color: #f9f9f9; border: 1px solid #e4e7ed;">
                  <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-size: 13px; color: #606266;">
                      匹配度: {{ (result.score * 100).toFixed(1) }}%
                    </span>
                    <div style="font-size: 13px; color: #606266;">
                      <div>来源: {{ result.metadata.source }}</div>
                      <div>页码: {{ result.metadata.page }}</div>
                    </div>
                  </div>
                  <p style="font-size: 14px; color: #303133; white-space: pre-wrap;">{{ result.text }}</p>
                </div>
              </template>
              <el-empty v-else description="暂无搜索结果，请先执行搜索" />
            </div>

            <!-- 生成结果 -->
            <div v-if="response" style="margin-top: 16px; padding: 16px; background-color: #f9f9f9; border-radius: 4px;">
              <div style="font-size: 16px; font-weight: 500; color: #303133; margin-bottom: 12px;">生成结果</div>
              <p style="white-space: pre-wrap; font-size: 14px; line-height: 1.6; color: #303133;">{{ response }}</p>
            </div>
          </template>
          
          <!-- 空状态 -->
          <template v-else>
            <div style="">
              <el-empty description="请选择搜索结果文件开始生成" :image-size="120">
                <template #image>
                  <el-icon style="font-size: 60px;"><Document /></el-icon>
                </template>
              </el-empty>
            </div>
          </template>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { apiBaseUrl } from '@/config/api'

// 状态变量
const selectedFile = ref('')
const provider = ref('')
const modelName = ref('')
const apiKey = ref('')
const models = ref({})
const generating = ref(false)
const response = ref('')
const status = ref('')
const query = ref('')
const searchResults = ref([])
const searchFiles = ref([])
const showReasoning = ref(true)

// 加载可用模型列表和搜索结果文件列表
onMounted(async () => {
  try {
    // 获取模型列表
    const modelsResponse = await axios.get(`${apiBaseUrl}/generation/models`)
    models.value = modelsResponse.data.models

    // 获取搜索结果文件列表
    const filesResponse = await axios.get(`${apiBaseUrl}/search-results`)
    searchFiles.value = filesResponse.data.files
  } catch (error) {
    console.error('获取数据失败:', error)
    ElMessage.error('获取数据失败')
  }
})

// 监听搜索结果文件变化
watch(selectedFile, async (newFile) => {
  if (!newFile) {
    query.value = ''
    searchResults.value = []
    return
  }

  try {
    const response = await axios.get(`${apiBaseUrl}/search-results/${newFile}`)
    query.value = response.data.query
    searchResults.value = response.data.results
  } catch (error) {
    console.error('加载搜索结果失败:', error)
    ElMessage.error('加载搜索结果失败')
  }
})

// 生成处理
const handleGenerate = async () => {
  if (!provider.value || !modelName.value) {
    ElMessage.warning('请选择生成模型')
    return
  }

  if (!query.value || searchResults.value.length === 0) {
    ElMessage.warning('请输入问题并确保有搜索结果')
    return
  }

  generating.value = true
  status.value = ''

  try {
    const res = await axios.post(`${apiBaseUrl}/generate`, {
      query: query.value,
      provider: provider.value,
      model_name: modelName.value,
      search_results: searchResults.value,
      api_key: apiKey.value || null,
      show_reasoning: showReasoning.value
    })

    response.value = res.data.response
    status.value = `生成完成！结果已保存至: ${res.data.saved_filepath}`
    ElMessage.success('生成完成')
  } catch (error) {
    console.error('生成失败:', error)
    status.value = `生成失败: ${error.message}`
    ElMessage.error('生成失败')
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
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

/* 卡片内容区域 */
:deep(.el-card__body) {
  padding: 16px;
  height: 100%;
  overflow-y: auto;
}

:deep(.el-slider__runway) {
  margin: 16px 0;
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

/* 状态信息样式 */
.status-message {
  margin-top: 16px;
  padding: 12px;
  border-radius: 4px;
  font-size: 14px;
  text-align: center;
}

.status-message.success {
  background-color: #f0f9eb;
  border: 1px solid #e1f3d8;
  color: #67c23a;
}

.status-message.error {
  background-color: #fef0f0;
  border: 1px solid #fde2e2;
  color: #f56c6c;
}

.status-message.info {
  background-color: #f4f4f5;
  border: 1px solid #e9e9eb;
  color: #909399;
}
</style> 