<template>
  <div
    style="width: 96%; height: calc(90vh - 56px); overflow-y: auto; overflow-x: hidden; padding: 24px; background-color: #f5f7fa; display: flex; flex-direction: column;">
    <div style="display: flex; width: 100%; flex: 1; gap: 20px;">
      <!-- 左侧：搜索配置部分 -->
      <div style="width: 25%; min-width: 300px; max-width: 350px;">
        <el-card style="width: 100%; height: calc(90vh - 104px); overflow-x: hidden;" shadow="hover">
          <div style="display: flex; flex-direction: column; gap: 8px;">
            <!-- Your Question -->
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

            <!-- Vector Database -->
            <div style="margin-bottom: 8px;">
              <div style="margin-bottom: 4px; font-size: 14px; color: #606266;">向量数据库</div>
              <el-select v-model="searchConfig.database" style="width: 100%;">
                <el-option
                  v-for="provider in providers"
                  :key="provider.id"
                  :label="provider.name"
                  :value="provider.id"
                />
              </el-select>
            </div>

            <!-- Collection -->
            <div style="margin-bottom: 8px;">
              <div style="margin-bottom: 4px; font-size: 14px; color: #606266;">集合</div>
              <el-select v-model="selectedCollection" style="width: 100%;">
                <el-option value="" disabled label="选择集合..." />
                <el-option
                  v-for="coll in collections"
                  :key="coll.id"
                  :label="`${coll.name} (${coll.count} 文档)`"
                  :value="coll.id"
                />
              </el-select>
            </div>

            <!-- Top K Results -->
            <div style="margin-bottom: 8px;">
              <div style="margin-bottom: 4px; font-size: 14px; color: #606266;">返回数量</div>
              <el-input-number
                v-model="searchConfig.topK"
                :min="1"
                :max="100"
                style="width: 100%;"
              />
            </div>

            <!-- Similarity Threshold -->
            <div style="margin-bottom: 8px;">
              <div style="margin-bottom: 4px; font-size: 14px; color: #606266;">
                相似度阈值: {{ (searchConfig.threshold * 100).toFixed(0) }}%
              </div>
              <el-slider
                v-model="searchConfig.threshold"
                :min="0"
                :max="1"
                :step="0.1"
              />
            </div>

            <!-- Minimum Word Count -->
            <div style="margin-bottom: 8px;">
              <div style="margin-bottom: 4px; font-size: 14px; color: #606266;">
                最小字数: {{ searchConfig.wordCountThreshold }} 字
              </div>
              <el-slider
                v-model="searchConfig.wordCountThreshold"
                :min="0"
                :max="500"
                :step="10"
              />
            </div>

            <!-- Save Search Results -->
            <div style="margin-bottom: 16px;">
              <el-checkbox v-model="searchConfig.saveResults">
                保存搜索结果
              </el-checkbox>
            </div>

            <!-- Search Button -->
            <div style="margin-top: 8px;">
              <el-button
                type="primary"
                style="width: 100%;"
                @click="handleSearch"
                :loading="searching"
              >
                {{ searching ? '搜索中...' : '搜索' }}
              </el-button>
            </div>

            <!-- Status Message -->
            <div v-if="status" 
              class="search-status"
              :class="{
                'error': status.includes('错误') || status.includes('失败'),
                'success': status.includes('完成') || status.includes('保存'),
                'info': !status.includes('错误') && !status.includes('失败') && !status.includes('完成') && !status.includes('保存')
              }">
              {{ status }}
            </div>
          </div>
        </el-card>
      </div>
      
      <!-- 右侧：搜索结果部分 -->
      <div style="flex: 1; min-width: 0; max-width: calc(100% - 370px);">
        <el-card shadow="hover" style="width: 95%; height: calc(90vh - 104px); display: flex; flex-direction: column; overflow-x: hidden;">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="font-size: 16px; font-weight: 500; color: #303133;">搜索结果</span>
              <el-button
                v-if="searchResults.length > 0"
                type="success"
                :icon="Document"
                @click="handleSaveResults"
              >
                保存搜索结果
              </el-button>
            </div>
          </template>
          
          <div style="display: flex; flex-direction: column; gap: 16px; padding: 4px; flex: 1; overflow: hidden;">
            <!-- 搜索结果展示区域 -->
            <div style="flex: 1; overflow-y: auto; overflow-x: hidden; min-height: 0;">
              <!-- 搜索结果列表 -->
              <div v-if="searchResults.length > 0" class="result-list">
                <div v-for="(result, index) in searchResults" :key="index" class="result-item">
                  <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                    <div style="font-weight: 500; color: #303133; font-size: 16px;">
                      <el-icon style="margin-right: 4px; vertical-align: middle;"><Document /></el-icon>
                      匹配片段 #{{ index + 1 }}
                    </div>
                    <div style="text-align: right;">
                      <div style="color: #909399; font-size: 14px; margin-bottom: 4px;">
                        相似度: {{ (result.score * 100).toFixed(1) }}%
                      </div>
                      <div style="color: #909399; font-size: 12px;">
                        <span>来源: {{ result.metadata?.source || '未知' }}</span>
                        <span style="margin-left: 8px;">页码: {{ result.metadata?.page || 'N/A' }}</span>
                      </div>
                    </div>
                  </div>
                  <div style="margin: 12px 0; color: #606266; font-size: 14px; line-height: 1.6; white-space: pre-wrap;">
                    {{ result.text }}
                  </div>
                  <el-divider v-if="index < searchResults.length - 1" />
                </div>
              </div>

              <!-- 未搜索时的提示 -->
              <div v-if="!searched && !searching" class="search-instructions">
                <el-empty 
                  description="开始您的语义搜索" 
                  :image-size="120"
                >
                  <template #image>
                    <el-icon style="font-size: 60px; color: #909399;"><Search /></el-icon>
                  </template>
                  <template #description>
                    <div style="text-align: center;">
                      <p style="margin: 8px 0; font-size: 16px; color: #606266;">开始您的语义搜索</p>
                      <p style="margin: 8px 0; font-size: 14px; color: #909399;">
                        您可以使用自然语言描述您的需求<br>系统将返回最相关的内容
                      </p>
                    </div>
                  </template>
                </el-empty>
              </div>

              <!-- 无搜索结果时的提示 -->
              <div v-if="searchResults.length === 0 && searched && !searching" class="search-instructions">
                <el-empty 
                  description="没有找到相关结果" 
                  :image-size="120"
                >
                  <template #image>
                    <el-icon style="font-size: 60px; color: #909399;"><Document /></el-icon>
                  </template>
                  <template #description>
                    <div style="text-align: center;">
                      <p style="margin: 8px 0; font-size: 16px; color: #606266;">没有找到相关结果</p>
                      <p style="margin: 8px 0; font-size: 14px; color: #909399;">
                        请尝试调整搜索条件或使用其他关键词
                      </p>
                    </div>
                  </template>
                </el-empty>
              </div>
              
              <!-- 加载中提示 -->
              <div v-if="searching" class="loading-container">
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
import { Document, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { apiBaseUrl } from '@/config/api'
import { handleError } from '@/utils/errorHandler'

// 状态变量
const searching = ref(false)
const searched = ref(false)
const query = ref('')
const searchResults = ref([])
const collections = ref([])
const providers = ref([])
const selectedCollection = ref('')
const status = ref('')

// 搜索配置
const searchConfig = ref({
  type: 'hybrid',
  threshold: 0.5,    // 相似度阈值设为50%
  database: 'milvus',
  topK: 3,
  reranking: false,
  rerankingModel: 'cross-encoder',
  wordCountThreshold: 30,    // 最小字数设为30
  saveResults: false
})

// 配置选项
const searchTypeOptions = [
  { label: '混合检索', value: 'hybrid' },
  { label: '向量检索', value: 'vector' },
  { label: '关键词检索', value: 'keyword' }
]

const databaseOptions = [
  { label: 'Milvus', value: 'milvus' },
  { label: 'Pinecone', value: 'pinecone' },
  { label: 'Weaviate', value: 'weaviate' },
  { label: 'Qdrant', value: 'qdrant' }
]

const rerankingModelOptions = [
  { label: 'Cross-Encoder', value: 'cross-encoder' },
  { label: 'Cohere Rerank', value: 'cohere' },
  { label: 'bge-reranker', value: 'bge-reranker' }
]

// 监听数据库变化，更新集合列表
watch(() => searchConfig.value.database, async (newProvider) => {
  if (newProvider) {
    await fetchCollections(newProvider)
  }
})

// 获取向量数据库providers列表
const fetchProviders = async () => {
  try {
    const response = await axios.get(`${apiBaseUrl}/providers`)
    if (response.data && Array.isArray(response.data.providers)) {
      providers.value = response.data.providers
    }
  } catch (error) {
    console.error('获取向量数据库列表失败:', error)
    handleError(error, { operation: '获取向量数据库列表' })
  }
}

// 获取集合列表
const fetchCollections = async (provider) => {
  try {
    const response = await axios.get(`${apiBaseUrl}/collections/${provider}`)
    if (response.data && response.data.collections) {
      collections.value = response.data.collections
    }
  } catch (error) {
    console.error('获取集合列表失败:', error)
    handleError(error, { operation: '获取集合列表' })
  }
}

// 处理搜索
const handleSearch = async () => {
  if (!query.value || !selectedCollection.value) {
    ElMessage.warning('请输入搜索内容并选择集合')
    return
  }

  searching.value = true
  searched.value = true
  searchResults.value = []
  status.value = ''

  try {
    const searchParams = {
      query: query.value,
      collection_id: selectedCollection.value,
      top_k: searchConfig.value.topK,
      threshold: searchConfig.value.threshold,
      word_count_threshold: searchConfig.value.wordCountThreshold,
      save_results: searchConfig.value.saveResults
    }

    const response = await axios.post(
      `${apiBaseUrl}/search?provider=${searchConfig.value.database}`,
      searchParams
    )

    if (response.data.results && response.data.results.results) {
      searchResults.value = response.data.results.results
      if (searchResults.value.length === 0) {
        status.value = '没有找到相关结果，请尝试调整搜索条件'
      } else if (searchConfig.value.saveResults && response.data.saved_filepath) {
        status.value = `搜索完成！结果已保存至: ${response.data.saved_filepath}`
      } else {
        status.value = '搜索完成！'
      }

      // 3秒后清除成功状态
      setTimeout(() => {
        if (status.value === '搜索完成！') {
          status.value = ''
        }
      }, 3000)

    } else {
      searchResults.value = []
      status.value = '没有找到相关结果，请尝试调整搜索条件'
    }
  } catch (error) {
    console.error('搜索错误:', error)
    const errorMessage = handleError(error, { operation: '搜索' })
    status.value = `搜索出错: ${errorMessage}`
  } finally {
    searching.value = false
  }
}

// 保存搜索结果
const handleSaveResults = async () => {
  if (!searchResults.value.length) {
    ElMessage.warning('没有可保存的搜索结果')
    return
  }

  try {
    const saveParams = {
      query: query.value,
      collection_id: selectedCollection.value,
      results: searchResults.value
    }

    const response = await axios.post(`${apiBaseUrl}/save-search`, saveParams)
    
    if (response.data.saved_filepath) {
      status.value = `结果已保存至: ${response.data.saved_filepath}`
    }
  } catch (error) {
    console.error('保存错误:', error)
    const errorMessage = handleError(error, { operation: '保存搜索结果' })
    status.value = `保存失败: ${errorMessage}`
  }
}

// 页面加载时获取数据
onMounted(async () => {
  await fetchProviders()
  if (searchConfig.value.database) {
    await fetchCollections(searchConfig.value.database)
  }
})
</script>

<style scoped>
/* 搜索指导样式 */
.search-instructions {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 24px;
}

/* 加载容器样式 */
.loading-container {
  padding: 16px;
}

/* 结果列表样式 */
.result-list {
  padding: 8px 16px;
}

.result-item {
  padding: 16px;
  margin-bottom: 16px;
  background-color: #fff;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
  transition: all 0.3s ease;
}

.result-item:hover {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
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

/* 状态信息样式 */
.search-status {
  margin-top: 16px;
  padding: 12px;
  border-radius: 4px;
  font-size: 14px;
  text-align: center;
}

.search-status.success {
  background-color: #f0f9eb;
  border: 1px solid #e1f3d8;
  color: #67c23a;
}

.search-status.error {
  background-color: #fef0f0;
  border: 1px solid #fde2e2;
  color: #f56c6c;
}

.search-status.info {
  background-color: #f4f4f5;
  border: 1px solid #e9e9eb;
  color: #909399;
}
</style> 