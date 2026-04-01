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
        <div class="task-item-id">{{ task.id }}</div>
        <div class="task-item-title">{{ task.title }}</div>
        <span class="badge" :class="'badge-' + task.state">{{ task.state }}</span>
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
.task-item-id   { font-size: 10px; color: var(--text-dim); font-family: monospace; }
.task-item-title { font-size: 13px; margin-top: 2px; line-height: 1.4; }
.badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 700; letter-spacing: .5px;
  margin-top: 4px;
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
