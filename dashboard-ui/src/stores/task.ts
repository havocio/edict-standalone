import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { Task, TaskStats } from '../types'

const API_BASE = ''

async function api<T>(path: string, method: string = 'GET', body?: unknown): Promise<T> {
  const opts: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body) opts.body = JSON.stringify(body)
  const r = await fetch(API_BASE + path, opts)
  return r.json() as Promise<T>
}

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])
  const activeId = ref<string | null>(null)
  const stats = ref<TaskStats>({ total: 0, running: 0, done: 0 })
  const loading = ref(false)
  const polling = ref(false)

  const activeTask = computed(() => tasks.value.find(t => t.id === activeId.value) || null)
  const runningTasks = computed(() => tasks.value.filter(t => !['Done', 'Cancelled'].includes(t.state)))
  const chatReply = ref<string | null>(null)

  async function loadTasks() {
    loading.value = true
    try {
      const res = await api<{tasks: Task[]; count: number}>('/api/tasks')
      tasks.value = res.tasks ? res.tasks.reverse() : []
      const runningCount = tasks.value.filter(t => !['Done', 'Cancelled'].includes(t.state)).length
      stats.value = {
        total: tasks.value.length,
        running: runningCount,
        done: tasks.value.filter(t => t.state === 'Done').length
      }

      // 自动选中
      if (activeId.value) {
        const current = tasks.value.find(t => t.id === activeId.value)
        if (current) {
          if (['Done', 'Cancelled', 'Blocked'].includes(current.state)) {
            stopAutoRefresh()
          }
          return
        }
      }
      const running = runningTasks.value[0]
      if (running) {
        activeId.value = running.id
      } else if (tasks.value.length > 0) {
        activeId.value = tasks.value[0].id
        stopAutoRefresh()
      }
    } finally {
      loading.value = false
    }
  }

  function selectTask(id: string) {
    activeId.value = id
    const task = tasks.value.find(t => t.id === id)
    if (task && !['Done', 'Cancelled'].includes(task.state)) {
      startAutoRefresh()
    } else {
      stopAutoRefresh()
    }
  }

  let refreshTimer: number | null = null
  function startAutoRefresh() {
    stopAutoRefresh()
    refreshTimer = window.setInterval(loadTasks, 3000)
  }
  function stopAutoRefresh() {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }

  // 创建任务并轮询
  async function createTask(message: string, regimeId?: string) {
    await api('/api/tasks', 'POST', { message, regime_id: regimeId })
    startPolling()
  }

  let pollTimer: number | null = null
  function startPolling() {
    stopPolling()
    polling.value = true
    pollTimer = window.setInterval(async () => {
      try {
        const latest = await api<{ pending: boolean; task_id?: string; result?: string; error?: string; state?: string }>('/api/tasks/latest')
        if (!latest.pending) {
          stopPolling()
          polling.value = false
          if (latest.task_id) {
            // 正式任务
            await loadTasks()
            selectTask(latest.task_id)
            startAutoRefresh()
          } else if (latest.result) {
            // 闲聊回复
            chatReply.value = latest.result
            activeId.value = null
          } else if (latest.error) {
            chatReply.value = '错误: ' + latest.error
            activeId.value = null
          }
        }
      } catch (e) {
        console.error('轮询失败', e)
      }
    }, 1000)
  }
  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    polling.value = false
  }

  // 任务操作
  async function cancelTask(id: string) {
    if (!confirm('确认取消该任务？')) return
    await api(`/api/tasks/${id}/cancel`, 'POST')
    await loadTasks()
  }

  async function advanceTask(id: string, state: string) {
    await api(`/api/tasks/${id}/advance`, 'POST')
    await loadTasks()
  }

  async function unblockTask(id: string, note: string) {
    await api(`/api/tasks/${id}/unblock`, 'POST')
    await loadTasks()
  }

  function clearChatReply() {
    chatReply.value = null
  }

  return {
    tasks, activeId, stats, loading, polling, chatReply,
    activeTask, runningTasks,
    loadTasks, selectTask, createTask, clearChatReply,
    startAutoRefresh, stopAutoRefresh,
    cancelTask, advanceTask, unblockTask,
  }
})
