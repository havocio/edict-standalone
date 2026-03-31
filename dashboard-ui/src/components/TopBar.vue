<template>
  <div class="topbar">
    <div class="topbar-logo">🏛️ 军机处</div>
    <div class="topbar-sub">{{ regimeName }}</div>
    <div class="topbar-spacer"></div>
    <div class="topbar-stats">
      <div class="stat-item">
        <div class="stat-num">{{ taskStore.stats.total }}</div>
        <div class="stat-label">总任务</div>
      </div>
      <div class="stat-item">
        <div class="stat-num" style="color:#3498db">{{ taskStore.stats.running }}</div>
        <div class="stat-label">进行中</div>
      </div>
      <div class="stat-item">
        <div class="stat-num" style="color:var(--green)">{{ taskStore.stats.done }}</div>
        <div class="stat-label">已完成</div>
      </div>
    </div>
    <button class="refresh-btn" @click="refresh">⟳ 刷新</button>
    <button class="theme-toggle" @click="themeStore.toggle" :title="themeStore.isDark ? '切换浅色模式' : '切换深色模式'">
      {{ themeStore.isDark ? '☀️' : '🌙' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useThemeStore } from '../stores/theme'
import { useTaskStore } from '../stores/task'

const themeStore = useThemeStore()
const taskStore = useTaskStore()
const regimeName = ref('制度看板')

async function refresh() {
  await taskStore.loadTasks()
}

onMounted(async () => {
  try {
    const r = await fetch('/api/regimes')
    const data = await r.json()
    if (data?.current) {
      regimeName.value = data.current.name
    }
  } catch (e) {
    console.log('无法加载制度信息')
  }
})
</script>

<style scoped>
.topbar {
  position: sticky; top: 0; z-index: 100;
  display: flex; align-items: center; gap: 16px;
  padding: 14px 28px;
  background: var(--topbar-bg);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
}
.topbar-logo { font-size: 22px; letter-spacing: 2px; color: var(--gold); font-weight: 700; }
.topbar-sub  { font-size: 12px; color: var(--text-dim); margin-left: -8px; }
.topbar-spacer { flex: 1; }
.topbar-stats { display: flex; gap: 20px; }
.stat-item { text-align: center; }
.stat-num  { font-size: 20px; font-weight: 700; color: var(--gold); line-height:1; }
.stat-label{ font-size: 11px; color: var(--text-dim); margin-top: 2px; }
.refresh-btn {
  padding: 7px 16px; border-radius: 8px;
  background: rgba(200,169,110,.12); border: 1px solid var(--border);
  color: var(--gold); font-size: 13px; cursor: pointer;
  transition: var(--transition);
}
.refresh-btn:hover { background: rgba(200,169,110,.22); }
.theme-toggle {
  padding: 6px 12px; border-radius: 8px;
  background: transparent; border: 1px solid var(--border);
  color: var(--text-dim); font-size: 13px; cursor: pointer;
  transition: var(--transition);
  margin-left: 8px;
}
.theme-toggle:hover { background: rgba(200,169,110,.12); color: var(--gold); }
</style>
