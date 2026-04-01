<template>
  <div class="topbar">
    <!-- Logo -->
    <div class="topbar-logo">🏛️ 军机处</div>

    <!-- 制度选择器 -->
    <div class="regime-selector" ref="selectorRef">
      <button
        class="regime-trigger"
        :class="{ active: dropdownOpen, switching: regimeStore.switching }"
        @click="toggleDropdown"
        :title="'当前制度：' + (regimeStore.currentRegime?.name || regimeStore.currentId)"
      >
        <span class="regime-trigger-name">
          {{ regimeStore.switching ? '切换中…' : (regimeStore.currentRegime?.name || regimeStore.currentId) }}
        </span>
        <span class="regime-trigger-era" v-if="regimeStore.currentRegime?.era">
          {{ regimeStore.currentRegime.era }}
        </span>
        <span class="regime-caret">{{ dropdownOpen ? '▲' : '▼' }}</span>
      </button>

      <!-- 下拉面板 -->
      <Transition name="dropdown">
        <div class="regime-dropdown" v-if="dropdownOpen">
          <div class="dropdown-header">选择制度流程</div>
          <div class="regime-list">
            <div
              v-for="regime in regimeStore.regimes"
              :key="regime.id"
              class="regime-item"
              :class="{ active: regime.id === regimeStore.currentId }"
              @click="selectRegime(regime.id)"
            >
              <div class="regime-item-header">
                <span class="regime-item-name">{{ regime.name }}</span>
                <span class="regime-item-era">{{ regime.era }}</span>
                <span class="regime-item-check" v-if="regime.id === regimeStore.currentId">✓</span>
              </div>
              <div class="regime-item-desc">{{ regime.description }}</div>
              <div class="regime-item-meta">
                <span class="meta-tag">{{ regime.role_count }} 个角色</span>
                <span class="meta-tag">{{ regime.state_count }} 个状态</span>
                <span v-for="tag in regime.tags.slice(0,2)" :key="tag" class="meta-tag tag-label">{{ tag }}</span>
              </div>
              <!-- 角色列表 -->
              <div class="regime-roles" v-if="regime.roles?.length">
                <span
                  v-for="role in regime.roles.slice(0, 6)"
                  :key="role.id"
                  class="role-chip"
                  :title="role.description"
                >
                  {{ role.icon }} {{ role.name }}
                </span>
                <span v-if="regime.roles.length > 6" class="role-more">+{{ regime.roles.length - 6 }}</span>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </div>

    <div class="topbar-spacer"></div>

    <!-- 统计 -->
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
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useThemeStore } from '../stores/theme'
import { useTaskStore } from '../stores/task'
import { useRegimeStore } from '../stores/regime'

const themeStore = useThemeStore()
const taskStore = useTaskStore()
const regimeStore = useRegimeStore()

const dropdownOpen = ref(false)
const selectorRef = ref<HTMLElement | null>(null)

function toggleDropdown() {
  dropdownOpen.value = !dropdownOpen.value
}

async function selectRegime(id: string) {
  dropdownOpen.value = false
  await regimeStore.switchRegime(id)
}

async function refresh() {
  await taskStore.loadTasks()
}

// 点击外部关闭下拉
function handleOutsideClick(e: MouseEvent) {
  if (selectorRef.value && !selectorRef.value.contains(e.target as Node)) {
    dropdownOpen.value = false
  }
}

onMounted(async () => {
  await regimeStore.loadRegimes()
  document.addEventListener('click', handleOutsideClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleOutsideClick)
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
.topbar-spacer { flex: 1; }
.topbar-stats { display: flex; gap: 20px; }
.stat-item { text-align: center; }
.stat-num  { font-size: 20px; font-weight: 700; color: var(--gold); line-height:1; }
.stat-label{ font-size: 11px; color: var(--text-dim); margin-top: 2px; }

/* 制度选择器 */
.regime-selector {
  position: relative;
}
.regime-trigger {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 14px; border-radius: 8px;
  background: rgba(200,169,110,.1); border: 1px solid var(--border);
  color: var(--text); font-size: 13px; cursor: pointer;
  transition: var(--transition);
  min-width: 140px;
}
.regime-trigger:hover, .regime-trigger.active {
  background: rgba(200,169,110,.2);
  border-color: var(--gold);
}
.regime-trigger.switching {
  opacity: 0.7; cursor: not-allowed;
}
.regime-trigger-name {
  font-weight: 700; color: var(--gold);
  white-space: nowrap;
}
.regime-trigger-era {
  font-size: 11px; color: var(--text-dim);
  background: rgba(200,169,110,.12);
  padding: 1px 6px; border-radius: 4px;
  white-space: nowrap;
}
.regime-caret {
  font-size: 10px; color: var(--text-dim); margin-left: auto;
}

/* 下拉面板 */
.regime-dropdown {
  position: absolute; top: calc(100% + 8px); left: 0;
  width: 360px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0,0,0,.35);
  overflow: hidden;
  z-index: 200;
}
.dropdown-header {
  padding: 12px 16px 8px;
  font-size: 11px; font-weight: 700; letter-spacing: 2px;
  color: var(--text-dim); text-transform: uppercase;
  border-bottom: 1px solid var(--border);
}
.regime-list {
  max-height: 480px; overflow-y: auto;
  padding: 6px;
}

.regime-item {
  padding: 12px 14px; border-radius: 8px; cursor: pointer;
  border: 1px solid transparent;
  transition: var(--transition);
  margin-bottom: 4px;
}
.regime-item:hover {
  background: var(--bg3);
  border-color: var(--border);
}
.regime-item.active {
  background: rgba(200,169,110,.1);
  border-color: var(--gold);
}

.regime-item-header {
  display: flex; align-items: center; gap: 8px; margin-bottom: 5px;
}
.regime-item-name {
  font-size: 15px; font-weight: 700; color: var(--text);
}
.regime-item-era {
  font-size: 11px; color: var(--text-dim);
  background: rgba(200,169,110,.12);
  padding: 1px 7px; border-radius: 4px;
}
.regime-item-check {
  margin-left: auto; color: var(--gold); font-weight: 700; font-size: 14px;
}
.regime-item-desc {
  font-size: 12px; color: var(--text-dim); line-height: 1.5;
  margin-bottom: 6px;
}
.regime-item-meta {
  display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 6px;
}
.meta-tag {
  font-size: 11px; padding: 1px 7px; border-radius: 4px;
  background: rgba(127,140,141,.15); color: var(--text-dim);
}
.tag-label {
  background: rgba(200,169,110,.12); color: var(--gold);
}
.regime-roles {
  display: flex; flex-wrap: wrap; gap: 4px;
}
.role-chip {
  font-size: 11px; padding: 2px 8px; border-radius: 4px;
  background: rgba(200,169,110,.08); color: var(--text-dim);
  border: 1px solid rgba(200,169,110,.15);
  cursor: default;
  transition: var(--transition);
}
.regime-item:hover .role-chip {
  border-color: rgba(200,169,110,.3); color: var(--text);
}
.role-more {
  font-size: 11px; padding: 2px 8px;
  color: var(--text-dim);
}

/* 按钮 */
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

/* 下拉动画 */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity .15s ease, transform .15s ease;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
