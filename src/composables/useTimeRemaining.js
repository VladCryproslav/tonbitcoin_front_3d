import { ref, onUnmounted, watch } from 'vue'

/**
 * Використання: const { timeRemaining, timeRemainingMs } = useTimeRemaining(futureISO)
 * @param {string|Ref<string>} futureISO - ISO-строка майбутньої дати або ref
 * @returns {{ timeRemaining: Ref<string>, timeRemainingMs: Ref<number|null> }}
 */
export function useTimeRemaining(futureISO) {
  const timeRemaining = ref('00д 00ч 00м')
  const timeRemainingMs = ref(null)
  let interval = null

  const updateTime = () => {
    const now = new Date()
    const future = new Date(futureISO)
    const diffMs = future - now
    timeRemainingMs.value = diffMs

    if (diffMs <= 0) {
      timeRemaining.value = '00д 00ч 00м'
      return
    }

    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))

    const formattedDays = String(days).padStart(2, '0')
    const formattedHours = String(hours).padStart(2, '0')
    const formattedMinutes = String(minutes).padStart(2, '0')

    timeRemaining.value = `${formattedDays}д ${formattedHours}ч ${formattedMinutes}м`
  }

  // Оновити одразу
  updateTime()
  // Оновлювати кожну хвилину
  interval = setInterval(updateTime, 60000)

  // Якщо futureISO - це ref, оновлювати при зміні
  if (futureISO && typeof futureISO === 'object' && 'value' in futureISO) {
    watch(futureISO, updateTime)
  }

  onUnmounted(() => clearInterval(interval))

  return { timeRemaining, timeRemainingMs }
} 