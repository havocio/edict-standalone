<template>
  <div class="sidebar">
    <div class="sidebar-title">下旨</div>
    <div class="create-area">
      <textarea
        v-model="message"
        rows="4"
        placeholder="在此输入旨意…"
        @keydown.enter.prevent="handleEnter"
      ></textarea>
      <button class="send-btn" :disabled="!message.trim() || taskStore.polling" @click="send">
        {{ taskStore.polling ? '处理中…' : '⚡ 传旨' }}
      </button>
    </div>
    <div class="sidebar-title" style="margin-top:4px">旨意台账</div>
    <div class="task-list">
      <div v-if="taskStore.tasks.length === 0" class="empty">暂无旨意</div>
      <div
        v-for="task in taskStore.tasks"
        :key="task.id"
        class="task-item"
        :class="{ active: task.id === taskStore.activeId }"
        @click="taskStore.selectTask(task.id)"
      >
        <div class="task-item-top">
          <div class="task-item-id">{{ task.id }}</div>
          <span v-if="task.regime_id" class="task-regime">{{ regimeName(task.regime_id) }}</span>
        </div>
        <div class="task-item-title">{{ task.title }}</div>
        <span class="badge" :style="badgeStyle(task.state, task.regime_id)">
          {{ stateLabel(task.state, task.regime_id) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useTaskStore } from '../stores/task'
import { useRegimeStore } from '../stores/regime'

const taskStore = useTaskStore()
const regimeStore = useRegimeStore()
const message = ref('')

function handleEnter(e: KeyboardEvent) {
  if (!e.shiftKey) {
    send()
  }
}

async function send() {
  const msg = message.value.trim()
  if (!msg || taskStore.polling) return
  message.value = ''
  await taskStore.createTask(msg, regimeStore.currentId)
}

// ── 动态 badge 颜色（与 TaskDetail 同逻辑）─────────────────────────
const TERMINAL_COLORS: Record<string, [string, string]> = {
  Done:      ['rgba(39,174,96,.15)',   '#27ae60'],
  Cancelled: ['rgba(192,57,43,.15)',   '#c0392b'],
  Blocked:   ['rgba(192,57,43,.10)',   '#e74c3c'],
  Pending:   ['rgba(127,140,141,.2)',  '#7f8c8d'],
}
const STATE_PALETTE: [string, string][] = [
  ['rgba(200,169,110,.15)', '#c8a96e'],
  ['rgba(41,128,185,.15)',  '#2980b9'],
  ['rgba(142,68,173,.15)',  '#8e44ad'],
  ['rgba(230,126,34,.15)',  '#e67e22'],
  ['rgba(52,152,219,.15)',  '#3498db'],
  ['rgba(241,196,15,.15)',  '#e6b800'],
  ['rgba(26,188,156,.15)',  '#1abc9c'],
]
const TERMINAL_STATES = ['Cancelled', 'Blocked', 'Done', 'Pending']

function badgeStyle(state: string, regimeId?: string) {
  if (TERMINAL_COLORS[state]) {
    const [bg, color] = TERMINAL_COLORS[state]
    return { background: bg, color }
  }
  // 找该任务所属制度的主流程状态序列，确定颜色索引
  const rid = regimeId || regimeStore.currentId
  const regime = regimeStore.regimes.find(r => r.id === rid) || regimeStore.currentRegime
  const mainStates = regime
    ? regime.states.filter(s => !TERMINAL_STATES.includes(s))
    : []
  const idx = mainStates.indexOf(state)
  const [bg, color] = STATE_PALETTE[idx >= 0 ? idx % STATE_PALETTE.length : 0]
  return { background: bg, color }
}

function stateLabel(state: string, regimeId?: string): string {
  const SPECIAL: Record<string, string> = {
    Pending: '待处理', Done: '已完成', Cancelled: '已取消', Blocked: '已阻塞',
  }
  if (SPECIAL[state]) return SPECIAL[state]
  const rid = regimeId || regimeStore.currentId
  const regime = regimeStore.regimes.find(r => r.id === rid) || regimeStore.currentRegime
  if (!regime) return state
  const role = regime.roles.find(r => r.id === state.toLowerCase() || r.id === state)
  return role ? role.name : state
}

function regimeName(regimeId: string): string {
  const r = regimeStore.regimes.find(r => r.id === regimeId)
  return r ? r.name : regimeId
}
</script>

<style scoped>
.sidebar {
  width: 260px; min-width: 260px;
  background: var(--bg2);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  overflow: hidden;
}
.sidebar-title {
  padding: 16px 20px 10px;
  font-size: 11px; font-weight: 700; letter-spacing: 2px;
  color: var(--text-dim); text-transform: uppercase;
}
.create-area { padding: 0 16px 16px; }
.create-area textarea {
  width: 100%; padding: 10px 12px;
  background: var(--input-bg); border: 1px solid var(--border);
  border-radius: 8px; color: var(--text); font-size: 13px;
  resize: none; outline: none;
  transition: border-color var(--transition), background var(--transition);
  line-height: 1.6;
  font-family: inherit;
}
.create-area textarea:focus { border-color: var(--gold); }
.send-btn {
  margin-top: 8px; width: 100%;
  padding: 9px; border-radius: 8px;
  background: linear-gradient(135deg, var(--gold-dark), var(--gold));
  border: none; color: #1a1000; font-size: 14px; font-weight: 700;
  cursor: pointer; transition: var(--transition);
}
.send-btn:hover:not(:disabled) { filter: brightness(1.1); transform: translateY(-1px); }
.send-btn:active:not(:disabled) { transform: translateY(0); }
.send-btn:disabled { opacity: .5; cursor: not-allowed; transform: none; }

.task-list { flex: 1; overflow-y: auto; padding: 0 8px 12px; }
.empty { text-align:center; color:var(--text-dim); font-size:12px; padding:20px 0; }
.task-item {
  padding: 10px 12px; border-radius: 8px; cursor: pointer;
  margin-bottom: 4px; border: 1px solid transparent;
  transition: var(--transition);
}
.task-item:hover { background: var(--bg3); border-color: var(--border); }
.task-item.active { background: var(--bg3); border-color: var(--gold); }
.task-item-top { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.task-item-id   { font-size: 10px; color: var(--text-dim); font-family: monospace; }
.task-regime {
  font-size: 9px; color: var(--text-dim);
  background: var(--bg2); border: 1px solid var(--border);
  padding: 1px 5px; border-radius: 3px; flex-shrink: 0;
  max-width: 70px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.task-item-title { font-size: 13px; margin-top: 2px; line-height: 1.4; }
.badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 700; letter-spacing: .5px;
  margin-top: 4px;
}
</style>
