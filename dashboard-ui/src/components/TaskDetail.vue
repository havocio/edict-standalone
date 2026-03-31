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
          <span class="badge" :class="'badge-' + task.state">{{ task.state }}</span>
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

    <!-- 状态流程 -->
    <div class="flow-track fade-in">
      <div class="section-title">流转路径</div>
      <div class="flow-steps">
        <div
          v-for="(s, i) in flowStates"
          :key="s"
          class="flow-step"
          :class="{ done: i < stateIndex || isDone, active: i === stateIndex && !isDone }"
        >
          <div class="dot">{{ flowIcons[s] }}</div>
          <div class="label">{{ flowLabels[s] }}</div>
        </div>
      </div>
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

const props = defineProps<{ task: Task }>()
const taskStore = useTaskStore()

const flowStates = ['Pending', 'Taizi', 'Zhongshu', 'Menxia', 'Assigned', 'Doing', 'Review', 'Done']
const flowLabels: Record<string, string> = {
  Pending: '待处理', Taizi: '太子', Zhongshu: '中书省', Menxia: '门下省',
  Assigned: '尚书省', Doing: '六部执行', Review: '复核', Done: '完成'
}
const flowIcons: Record<string, string> = {
  Pending: '⌛', Taizi: '👑', Zhongshu: '📜', Menxia: '⚖️',
  Assigned: '📋', Doing: '⚙️', Review: '🔍', Done: '✅'
}

const isDone = computed(() => props.task.state === 'Done')
const isCancelled = computed(() => props.task.state === 'Cancelled')
const stateIndex = computed(() => flowStates.indexOf(props.task.state))

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

function advance() {
  const allowedMap: Record<string, string[]> = {
    Pending: ['Taizi'],
    Taizi: ['Zhongshu', 'Done'],
    Zhongshu: ['Menxia'],
    Menxia: ['Assigned', 'Zhongshu'],
    Assigned: ['Doing'],
    Doing: ['Review'],
    Review: ['Done', 'Doing'],
  }
  const nexts = allowedMap[props.task.state] || []
  if (!nexts.length) {
    alert('当前状态无法手动推进')
    return
  }
  const next = nexts.length === 1
    ? nexts[0]
    : prompt(`选择目标状态 (${nexts.join(' / ')})`)
  if (next && nexts.includes(next)) {
    taskStore.advanceTask(props.task.id, next)
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
.task-meta { display: flex; gap: 12px; margin-top: 12px; flex-wrap: wrap; }
.meta-item { font-size: 12px; color: var(--text-dim); }
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

.badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 700; letter-spacing: .5px;
}
.badge-Pending   { background: rgba(127,140,141,.2); color: var(--gray); }
.badge-Taizi     { background: rgba(200,169,110,.15); color: var(--gold); }
.badge-Zhongshu  { background: rgba(41,128,185,.15); color: var(--blue); }
.badge-Menxia    { background: rgba(142,68,173,.15); color: var(--purple); }
.badge-Assigned  { background: rgba(230,126,34,.15); color: #e67e22; }
.badge-Doing     { background: rgba(52,152,219,.15); color: #3498db; }
.badge-Review    { background: rgba(241,196,15,.15); color: #f1c40f; }
.badge-Done      { background: rgba(39,174,96,.15); color: var(--green); }
.badge-Cancelled { background: rgba(192,57,43,.15); color: var(--red); }
.badge-Blocked   { background: rgba(192,57,43,.1); color: #e74c3c; }
</style>
