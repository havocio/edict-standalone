import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref(localStorage.getItem('theme') || 'dark')

  const isDark = computed(() => theme.value === 'dark')

  function toggle() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    localStorage.setItem('theme', theme.value)
  }

  function init() {
    const saved = localStorage.getItem('theme') || 'dark'
    theme.value = saved
  }

  return { theme, isDark, toggle, init }
})
