<template>
  <div class="space-y-4">
    <!-- 顶部操作栏 -->
    <div class="flex justify-between items-center">
      <div class="flex space-x-4">
        <el-button type="primary" @click="handleUpload">
          <el-icon class="mr-1"><Upload /></el-icon>上传文档
        </el-button>
        <el-button @click="handleBatchDelete" :disabled="!selectedDocuments.length">
          <el-icon class="mr-1"><Delete /></el-icon>批量删除
        </el-button>
      </div>
      <div class="flex space-x-4">
        <el-input
          v-model="searchQuery"
          placeholder="搜索文档..."
          class="w-64"
          clearable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
    </div>

    <!-- 文档列表 -->
    <el-card>
      <el-table
        v-loading="loading"
        :data="documents"
        @selection-change="handleSelectionChange"
        style="width: 100%"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="name" label="文档名称" min-width="200">
          <template #default="{ row }">
            <div class="flex items-center">
              <el-icon class="mr-2"><Document /></el-icon>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="120" />
        <el-table-column prop="size" label="大小" width="120" />
        <el-table-column prop="uploadTime" label="上传时间" width="180" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.status === 'processed' ? 'success' : 'warning'">
              {{ row.status === 'processed' ? '已处理' : '处理中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button type="primary" link @click="handlePreview(row)">
                预览
              </el-button>
              <el-button type="primary" link @click="handleEdit(row)">
                编辑
              </el-button>
              <el-button type="danger" link @click="handleDelete(row)">
                删除
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="flex justify-end mt-4">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 上传对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传文档"
      width="500px"
    >
      <el-upload
        class="upload-demo"
        drag
        action="/api/upload"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        :before-upload="beforeUpload"
        multiple
        :file-list="fileList"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 PDF、Word、Excel、TXT 等格式文件
          </div>
        </template>
      </el-upload>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="uploadDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitUpload">
            确认上传
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Document, Upload, Delete, Search, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 状态变量
const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const selectedDocuments = ref([])
const uploadDialogVisible = ref(false)
const fileList = ref([])

// 模拟数据
const documents = ref([
  {
    id: 1,
    name: '产品说明书.pdf',
    type: 'PDF',
    size: '2.5MB',
    uploadTime: '2024-04-02 10:00:00',
    status: 'processed'
  },
  {
    id: 2,
    name: '技术文档.docx',
    type: 'Word',
    size: '1.8MB',
    uploadTime: '2024-04-02 09:30:00',
    status: 'processing'
  },
  {
    id: 3,
    name: '用户手册.pdf',
    type: 'PDF',
    size: '3.2MB',
    uploadTime: '2024-04-02 08:15:00',
    status: 'processed'
  }
])

// 方法
const handleUpload = () => {
  uploadDialogVisible.value = true
}

const handleBatchDelete = () => {
  ElMessageBox.confirm(
    `确定要删除选中的 ${selectedDocuments.value.length} 个文档吗？`,
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    // TODO: 调用删除API
    ElMessage.success('删除成功')
  })
}

const handleSelectionChange = (selection) => {
  selectedDocuments.value = selection
}

const handlePreview = (row) => {
  // TODO: 实现预览功能
  console.log('预览文档:', row)
}

const handleEdit = (row) => {
  // TODO: 实现编辑功能
  console.log('编辑文档:', row)
}

const handleDelete = (row) => {
  ElMessageBox.confirm(
    '确定要删除该文档吗？',
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    // TODO: 调用删除API
    ElMessage.success('删除成功')
  })
}

const handleSizeChange = (val) => {
  pageSize.value = val
  // TODO: 重新加载数据
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  // TODO: 重新加载数据
}

const handleUploadSuccess = (response) => {
  ElMessage.success('上传成功')
  uploadDialogVisible.value = false
  fileList.value = []
  // TODO: 刷新文档列表
}

const handleUploadError = () => {
  ElMessage.error('上传失败')
}

const beforeUpload = (file) => {
  // TODO: 添加文件类型和大小限制
  return true
}

const submitUpload = () => {
  // TODO: 实现上传逻辑
  uploadDialogVisible.value = false
}
</script>

<style scoped>
.upload-demo {
  width: 100%;
}
</style> 