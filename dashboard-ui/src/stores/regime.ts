import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { RegimeInfo } from '../types'

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

export const useRegimeStore = defineStore('regime', () => {
  const regimes = ref<RegimeInfo[]>([])
  const currentId = ref<string>('san_sheng_liu_bu')
  const loading = ref(false)
  const switching = ref(false)

  const currentRegime = computed(() =>
    regimes.value.find(r => r.id === currentId.value) || null
  )

  async function loadRegimes() {
    loading.value = true
    try {
      const res = await api<{ regimes: RegimeInfo[]; current: string; current_obj: RegimeInfo | null }>('/api/regimes')
      regimes.value = res.regimes || []
      if (res.current) currentId.value = res.current
    } catch (e) {
      console.error('加载制度列表失败', e)
    } finally {
      loading.value = false
    }
  }

  async function switchRegime(regimeId: string): Promise<boolean> {
    if (regimeId === currentId.value) return true
    switching.value = true
    try {
      const res = await api<{ status: string; to: string; regime: RegimeInfo }>('/api/regimes/switch', 'POST', { regime_id: regimeId })
      if (res.status === 'switched') {
        currentId.value = res.to
        // 更新本地制度对象数据（如有变动）
        const idx = regimes.value.findIndex(r => r.id === res.to)
        if (idx >= 0 && res.regime) {
          regimes.value[idx] = res.regime
        }
        return true
      }
      return false
    } catch (e) {
      console.error('切换制度失败', e)
      return false
    } finally {
      switching.value = false
    }
  }

  return {
    regimes, currentId, loading, switching,
    currentRegime,
    loadRegimes, switchRegime,
  }
})
