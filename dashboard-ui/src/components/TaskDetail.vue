<template>
  <div class="fade-in">
    <!-- 任务标题卡 -->
    <div class="task-header">
      <div class="task-header-left">
        <div class="task-id-badge">{{ task.id }}</div>
        <div class="task-title">{{ task.title }}</div>
        <div v-if="task.content" class="task-content">
          {{ task.content.slice(0, 200) }}{{ task.content.length > 200 ? '…' : '' }}
        </div>
        <div class="task-meta">
          <span class="badge" :style="badgeStyle(task.state)">{{ stateLabel(task.state) }}</span>
          <span v-if="taskRegime" class="regime-tag">
            {{ taskRegime.name }}
            <span class="regime-era">{{ taskRegime.era }}</span>
          </span>
          <span class="meta-item">创建 {{ formatTime(task.created_at) }}</span>
          <span class="meta-item">更新 {{ formatTime(task.updated_at) }}</span>
        </div>
      </div>
      <div class="task-actions">
        <template v-if="task.state === 'Blocked'">
          <button class="action-btn unblock" @click="unblock">🔓 解除阻塞</button>
          <button class="action-btn cancel" @click="cancel">✕ 取消</button>
        </template>
        <template v-else-if="!isDone && !isCancelled">
          <button class="action-btn advance" @click="advance">⚡ 手动推进</button>
          <button class="action-btn cancel" @click="cancel">✕ 取消</button>
        </template>
      </div>
    </div>

    <!-- 状态流程（动态，按制度渲染） -->
    <div class="flow-track fade-in">
      <div class="section-title">流转路径</div>
      <div v-if="mainFlowStates.length" class="flow-steps">
        <div
          v-for="(s, i) in mainFlowStates"
          :key="s"
          class="flow-step"
          :class="{ done: isStateDone(i), active: isStateActive(i) }"
        >
          <div class="dot">{{ stateIcon(s) }}</div>
          <div class="label">{{ stateLabel(s) }}</div>
        </div>
      </div>
      <div v-else class="flow-empty">暂无流程信息</div>
    </div>

    <!-- 最终结果 -->
    <div v-if="task.result" class="result-card fade-in">
      <div class="result-title">📋 最终回奏</div>
      <div class="result-body">{{ task.result }}</div>
    </div>

    <!-- 进展日志 -->
    <div v-if="progressLog.length" class="progress-container fade-in">
      <div class="section-title">实时进展 ({{ progressLog.length }})</div>
      <div class="progress-list">
        <div v-for="p in progressLog" :key="p.time" class="progress-item">
          <div class="progress-header">
            <span class="progress-agent">{{ p.agent }}</span>
            <span class="progress-time">{{ formatTime(p.time) }}</span>
            <span v-if="p.tokens" class="progress-tokens">🔢 {{ p.tokens }} tokens</span>
          </div>
          <div class="progress-doing">{{ p.doing }}</div>
          <div v-if="p.todos?.length" class="progress-todos">
            <div v-for="t in p.todos" :key="t" class="progress-todo">• {{ t }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 流转日志 -->
    <div v-if="flowLog.length" class="log-container fade-in">
      <div class="section-title">流转日志 ({{ flowLog.length }})</div>
      <div class="log-list">
        <div v-for="f in flowLog" :key="f.time" class="log-item">
          <span class="log-time">{{ f.time?.slice(11, 19) || '' }}</span>
          <span class="log-arrow">{{ f.from || '—' }} → {{ f.to }}</span>
          <span class="log-agent">[{{ f.agent || '?' }}]</span>
          <span class="log-note">{{ f.note || '' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Task } from '../types'
import { useTaskStore } from '../stores/task'
import { useRegimeStore } from '../stores/regime'

const props = defineProps<{ task: Task }>()
const taskStore = useTaskStore()
const regimeStore = useRegimeStore()

// ── 找本任务所属制度 ─────────────────────────────────────────────────
// 优先用任务的 regime_id；没有 regime_id 的历史任务默认三省六部制
// 不能 fallback 当前制度，否则切换制度后历史任务流程会变形
const DEFAULT_REGIME_ID = 'san_sheng_liu_bu'
const taskRegime = computed(() => {
  const rid = props.task.regime_id || DEFAULT_REGIME_ID
  return regimeStore.regimes.find(r => r.id === rid) || null
})

// 非主流程状态（不在流转步骤轴上展示）
const SIDE_STATES = new Set(['Pending', 'Done', 'Cancelled', 'Blocked'])

// 主流程状态序列：只保留"中间过程"状态
const mainFlowStates = computed(() => {
  if (!taskRegime.value) return []
  return taskRegime.value.states.filter(s => !SIDE_STATES.has(s))
})

const isDone = computed(() => props.task.state === 'Done')
const isCancelled = computed(() => props.task.state === 'Cancelled')

const stateIndex = computed(() => mainFlowStates.value.indexOf(props.task.state))

function isStateDone(i: number) {
  if (isDone.value) return true
  return i < stateIndex.value
}
function isStateActive(i: number) {
  return i === stateIndex.value && !isDone.value
}

// ── 状态标签（优先用制度角色名，特殊状态用固定中文）────────────────────
const SPECIAL_LABELS: Record<string, string> = {
  Pending: '待处理', Done: '已完成', Cancelled: '已取消', Blocked: '已阻塞',
}

function _findRole(state: string) {
  if (!taskRegime.value) return null
  const lower = state.toLowerCase()
  return taskRegime.value.roles.find(
    r => r.id.toLowerCase() === lower        // 大小写不敏感匹配
  ) || null
}

function stateLabel(state: string): string {
  if (SPECIAL_LABELS[state]) return SPECIAL_LABELS[state]
  const role = _findRole(state)
  return role ? role.name : state
}

// ── 状态图标 ─────────────────────────────────────────────────────────
const SPECIAL_ICONS: Record<string, string> = {
  Pending: '⌛', Done: '✅', Cancelled: '❌', Blocked: '🔒',
}
const FALLBACK_ICONS = ['🔵', '🟡', '🟠', '🟢', '🔷', '💠', '🔶']

function stateIcon(state: string): string {
  if (SPECIAL_ICONS[state]) return SPECIAL_ICONS[state]
  const role = _findRole(state)
  if (role?.icon) return role.icon
  const idx = mainFlowStates.value.indexOf(state)
  return FALLBACK_ICONS[idx >= 0 ? idx % FALLBACK_ICONS.length : 0]
}

// ── 动态 badge 颜色（基于状态 hash） ──────────────────────────────────
const TERMINAL_COLORS: Record<string, [string, string]> = {
  Done:      ['rgba(39,174,96,.15)',   '#27ae60'],
  Cancelled: ['rgba(192,57,43,.15)',   '#c0392b'],
  Blocked:   ['rgba(192,57,43,.10)',   '#e74c3c'],
  Pending:   ['rgba(127,140,141,.2)',  '#7f8c8d'],
}
// 制度主流程状态按色板循环
const STATE_PALETTE: [string, string][] = [
  ['rgba(200,169,110,.15)', '#c8a96e'],   // 金
  ['rgba(41,128,185,.15)',  '#2980b9'],   // 蓝
  ['rgba(142,68,173,.15)',  '#8e44ad'],   // 紫
  ['rgba(230,126,34,.15)',  '#e67e22'],   // 橙
  ['rgba(52,152,219,.15)',  '#3498db'],   // 天蓝
  ['rgba(241,196,15,.15)',  '#e6b800'],   // 黄
  ['rgba(26,188,156,.15)',  '#1abc9c'],   // 青绿
]

function badgeStyle(state: string): Record<string, string> {
  if (TERMINAL_COLORS[state]) {
    const [bg, color] = TERMINAL_COLORS[state]
    return { background: bg, color }
  }
  const idx = mainFlowStates.value.indexOf(state)
  const [bg, color] = STATE_PALETTE[idx >= 0 ? idx % STATE_PALETTE.length : 0]
  return { background: bg, color }
}

// ── 手动推进（从制度 state_transitions 动态获取） ──────────────────────
function advance() {
  if (!taskRegime.value) {
    alert('当前制度信息未加载，无法推进')
    return
  }
  // 从 flow_log 反推 state_transitions（因为 RegimeInfo 里没有直接暴露 transitions）
  // 使用 mainFlowStates 顺序做简单推进：直接找下一个状态
  const current = props.task.state
  const idx = mainFlowStates.value.indexOf(current)

  if (idx < 0) {
    alert('当前状态无法手动推进')
    return
  }
  if (idx >= mainFlowStates.value.length - 1) {
    alert('已是最终状态')
    return
  }
  const next = mainFlowStates.value[idx + 1]
  taskStore.advanceTask(props.task.id, next)
}

const flowLog = computed(() => [...(props.task.flow_log || [])].reverse())
const progressLog = computed(() => [...(props.task.progress_log || [])].reverse())

function formatTime(t?: string) {
  return t ? t.slice(0, 16).replace('T', ' ') : ''
}

function cancel() {
  taskStore.cancelTask(props.task.id)
}

function unblock() {
  const note = prompt('请描述解除阻塞的原因（可留空）：', '人工排查后解除')
  if (note !== null) {
    taskStore.unblockTask(props.task.id, note || '人工解除阻塞')
  }
}
</script>

<style scoped>
.task-header {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px 24px;
  display: flex; align-items: flex-start; gap: 16px;
}
.task-header-left { flex: 1; }
.task-id-badge {
  font-family: monospace; font-size: 12px; color: var(--text-dim);
  background: var(--bg3); padding: 3px 8px; border-radius: 4px;
  display: inline-block; margin-bottom: 8px;
}
.task-title { font-size: 20px; font-weight: 700; color: var(--gold-light); line-height: 1.3; }
.task-content { font-size: 13px; color: var(--text-dim); margin-top: 6px; line-height: 1.6; }
.task-meta { display: flex; gap: 12px; margin-top: 12px; flex-wrap: wrap; align-items: center; }
.meta-item { font-size: 12px; color: var(--text-dim); }

.regime-tag {
  font-size: 11px; font-weight: 600;
  background: rgba(200,169,110,.08);
  border: 1px solid rgba(200,169,110,.2);
  color: var(--gold); padding: 2px 8px; border-radius: 10px;
  display: inline-flex; gap: 5px; align-items: center;
}
.regime-era { opacity: .65; font-weight: 400; }

.task-actions { display: flex; flex-direction: column; gap: 8px; align-items: flex-end; }
.action-btn {
  padding: 6px 14px; border-radius: 6px; font-size: 12px; cursor: pointer;
  border: 1px solid; transition: var(--transition);
}
.action-btn.cancel { border-color: var(--red); color: var(--red); background: transparent; }
.action-btn.cancel:hover { background: rgba(192,57,43,.1); }
.action-btn.advance { border-color: var(--gold); color: var(--gold); background: transparent; }
.action-btn.advance:hover { background: rgba(200,169,110,.1); }
.action-btn.unblock { border-color: #e67e22; color: #e67e22; background: transparent; }
.action-btn.unblock:hover { background: rgba(230,126,34,.12); }

.flow-track {
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 16px 20px;
}
.section-title {
  font-size: 11px; font-weight: 700; letter-spacing: 2px;
  color: var(--text-dim); text-transform: uppercase; margin-bottom: 14px;
}
.flow-steps {
  display: flex; gap: 0; align-items: center;
  overflow-x: auto; padding-bottom: 4px;
}
.flow-empty { font-size: 13px; color: var(--text-dim); padding: 8px 0; }

.flow-step {
  display: flex; flex-direction: column; align-items: center;
  gap: 5px; min-width: 72px; position: relative;
}
.flow-step::after {
  content: ""; position: absolute; right: -16px; top: 14px;
  width: 32px; height: 2px;
  background: var(--border);
}
.flow-step:last-child::after { display: none; }
.flow-step .dot {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--bg3); border: 2px solid var(--border);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; transition: var(--transition);
}
.flow-step.active .dot   { border-color: var(--gold); background: rgba(200,169,110,.15); }
.flow-step.done .dot     { border-color: var(--green); background: rgba(39,174,96,.15); }
.flow-step .label { font-size: 11px; color: var(--text-dim); white-space: nowrap; }
.flow-step.active .label { color: var(--gold); }
.flow-step.done .label   { color: var(--green); }

.result-card {
  background: var(--bg2);
  border: 1px solid rgba(39,174,96,.3);
  border-radius: var(--radius); padding: 20px 24px;
}
.result-title { font-size: 13px; font-weight: 700; color: var(--green); margin-bottom: 12px; }
.result-body  {
  font-size: 14px; line-height: 1.8; color: var(--text);
  white-space: pre-wrap; word-break: break-word;
}

.log-container {
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 16px 20px;
}
.log-list { display: flex; flex-direction: column; gap: 8px; max-height: 280px; overflow-y: auto; }
.log-item {
  display: flex; gap: 12px; align-items: flex-start;
  font-size: 12px; line-height: 1.5;
}
.log-time  { color: var(--text-dim); white-space: nowrap; font-family: monospace; flex-shrink: 0; }
.log-arrow { color: var(--gold); flex-shrink: 0; }
.log-agent { color: var(--blue); flex-shrink: 0; font-weight: 600; }
.log-note  { color: var(--text); }

.progress-container {
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 16px 20px;
}
.progress-list { display: flex; flex-direction: column; gap: 8px; max-height: 240px; overflow-y: auto; }
.progress-item {
  background: var(--bg3); border-radius: 8px; padding: 10px 12px;
}
.progress-header { display: flex; gap: 10px; align-items: center; margin-bottom: 4px; }
.progress-agent  { font-size: 12px; font-weight: 700; color: var(--purple); }
.progress-time   { font-size: 11px; color: var(--text-dim); font-family: monospace; }
.progress-tokens { font-size: 11px; color: var(--text-dim); margin-left: auto; }
.progress-doing  { font-size: 13px; color: var(--text); line-height: 1.5; }
.progress-todos  { margin-top: 6px; display: flex; flex-direction: column; gap: 2px; }
.progress-todo   { font-size: 12px; color: var(--text-dim); }

/* badge 样式：颜色通过 :style 动态注入，这里只给基础结构 */
.badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 700; letter-spacing: .5px;
}
</style>
