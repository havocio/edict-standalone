<template>
  <div class="app" :data-theme="themeStore.theme">
    <TopBar />
    <div class="main">
      <SideBar />
      <ContentArea />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useThemeStore } from './stores/theme'
import { useTaskStore } from './stores/task'
import TopBar from './components/TopBar.vue'
import SideBar from './components/SideBar.vue'
import ContentArea from './components/ContentArea.vue'

const themeStore = useThemeStore()
const taskStore = useTaskStore()

// 初始化加载任务
taskStore.loadTasks()
</script>

<style scoped>
.app {
  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
}
.main {
  display: flex;
  height: calc(100vh - 57px);
}
</style>
