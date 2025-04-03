<script setup>
import { HomeFilled, Setting, Monitor } from '@element-plus/icons-vue'
</script>

<template>
  <router-view />
</template>

<style>
html,
body {
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
}

#app {
  height: 100%;
  width: 100%;
}

.logo {
  font-family: 'Roboto', 'Arial', sans-serif;
  font-size: 28px;
  font-weight: 700;
  color: #409EFF;
  text-decoration: none;
  letter-spacing: 0.5px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  height: 100%;
  white-space: nowrap;
  overflow: visible;
}

.logo:hover {
  opacity: 0.9;
}
</style>
