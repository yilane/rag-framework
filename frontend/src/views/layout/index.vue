<template>
  <el-container class="layout-container">
    <el-aside width="256px" class="sidebar">
      <div class="sidebar-header">
        <div class="logo-container">
          <div class="logo">RAG Framework</div>
        </div>
      </div>
      <el-menu
        :default-active="route.path"
        class="sidebar-menu"
        background-color="#374151"
        text-color="#ffffff"
        active-text-color="#60a5fa"
        router
      >
        <el-menu-item 
          v-for="item in menuItems" 
          :key="item.path"
          :index="'/' + item.path"
          class="menu-item"
        >
          <el-icon>
            <component :is="item.meta.icon" />
          </el-icon>
          <span>{{ item.meta.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container class="main-container">
      <el-header class="main-header">
        <h2 class="page-title">
          {{ route.meta.title }}
          <el-button
            class="refresh-btn"
            type="info"
            :icon="Refresh"
            text
            @click="refreshCurrentPage"
            title="刷新当前页面"
          />
        </h2>
      </el-header>
      <el-main class="main-content">
        <router-view />
      </el-main>
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
.layout-container {
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  height: 100vh;
  background-color: #374151;
  z-index: 1000;
  border-right: 1px solid #e5e7eb;
  box-shadow: 2px 0 4px rgba(0, 0, 0, 0.1);
}

.sidebar-header {
  padding: 1rem;
  border-bottom: 1px solid #4b5563;
}

.logo-container {
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo {
  font-family: 'Inter', 'Roboto', 'Arial', sans-serif;
  font-size: 24px;
  font-weight: 700;
  color: #60a5fa;
  text-decoration: none;
  letter-spacing: 0.5px;
  white-space: nowrap;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.sidebar-menu {
  border-right: none;
  background-color: #374151;
}

.menu-item {
  height: 48px;
  line-height: 48px;
  margin: 4px 8px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.menu-item:hover {
  background-color: #4b5563 !important;
}

.menu-item.is-active {
  background-color: #1e40af !important;
  color: #ffffff !important;
}

.menu-item .el-icon {
  margin-right: 8px;
  font-size: 16px;
}

.main-container {
  margin-left: 256px;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-header {
  height: 60px;
  background-color: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  padding: 0 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.page-title {
  margin: 0;
  font-size: 18px;
  color: #1f2937;
  font-weight: 600;
  display: flex;
  align-items: center;
}

.refresh-btn {
  margin-left: 12px;
  padding: 6px 8px;
  color: #6b7280;
  font-size: 16px;
  border: none;
  background: transparent;
  transition: all 0.2s ease;
}

.refresh-btn:hover {
  color: #3b82f6;
  background-color: #f3f4f6;
}

.main-content {
  flex: 1;
  padding: 24px;
  background-color: #f9fafb;
  overflow-y: auto;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    width: 240px;
  }
  
  .main-container {
    margin-left: 240px;
  }
  
  .main-content {
    padding: 16px;
  }
}
</style> 