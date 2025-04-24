<template>
  <el-container class="h-screen">
    <el-aside width="256px" class="bg-gray-800 fixed left-0 top-0 h-screen">
      <div class="p-4">
        <div class="flex items-center justify-center mb-6">
          <div class="logo">RAG System</div>
        </div>
      </div>
      <el-menu
        :default-active="route.path"
        class="border-none"
        background-color="#1f2937"
        text-color="#fff"
        active-text-color="#409eff"
        router
      >
        <el-menu-item 
          v-for="item in menuItems" 
          :key="item.path"
          :index="'/' + item.path"
        >
          <el-icon>
            <component :is="item.meta.icon" />
          </el-icon>
          <span>{{ item.meta.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container class="ml-64">
      <el-header class="bg-white border-b flex items-center px-4" style="height: 60px;">
        <h2 class="text-title flex items-center">
          {{ route.meta.title }}
          <el-button
            class="ml-4 refresh-btn"
            type="info"
            :icon="Refresh"
            text
            @click="refreshCurrentPage"
            title="刷新当前页面"
          />
        </h2>
      </el-header>
      <router-view />
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const menuItems = computed(() => {
  return router.options.routes[0].children
})

const refreshCurrentPage = () => {
  window.location.reload()
}
</script>

<style scoped>
.el-aside {
  background-color: #1f2937;
}

.el-menu {
  border-right: none;
}

.el-menu-item {
  height: 50px;
  line-height: 50px;
}

.el-menu-item .el-icon {
  margin-right: 8px;
}

.logo {
  font-family: 'Roboto', 'Arial', sans-serif;
  font-size: 28px;
  font-weight: 700;
  color: #409EFF;
  text-decoration: none;
  letter-spacing: 1px;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  height: 100%;
  white-space: nowrap;
  overflow: visible;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.1);
}

.text-title {
  margin: 0;
  font-size: 18px;
  color: #303133;
  font-weight: 500;
  display: flex;
  align-items: center;
  height: 60px;
}

.refresh-btn {
  padding: 4px 8px;
  color: #606266;
  font-size: 20px;
}

.refresh-btn :deep(.el-icon) {
  font-size: 20px;
}

.refresh-btn:hover {
  color: #409EFF;
  background: transparent;
}
</style> 