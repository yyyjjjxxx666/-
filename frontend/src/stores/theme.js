import { defineStore } from 'pinia'
import { ref, watchEffect } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const isDark = ref(
    localStorage.getItem('theme') === 'dark' ||
    (localStorage.getItem('theme') === null &&
     window.matchMedia('(prefers-color-scheme: dark)').matches)
  )

  function toggle() {
    isDark.value = !isDark.value
    localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  }

  function setLight() {
    isDark.value = false
    localStorage.setItem('theme', 'light')
  }

  function setDark() {
    isDark.value = true
    localStorage.setItem('theme', 'dark')
  }

  watchEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
  })

  return { isDark, toggle, setLight, setDark }
})
