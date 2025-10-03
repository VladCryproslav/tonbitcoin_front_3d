import { ref, onMounted, onUnmounted, watch } from 'vue'
import { tonapi } from '../../axios.config'

export function useTonApiPolling(url, options = {}) {
  const {
    initialInterval = 2000,
    maxInterval = 30000,
    backoffMultiplier = 1.5,
    unchangedThreshold = 5 // кількість незмінних відповідей для збільшення інтервалу
  } = options

  const data = ref(null)
  const isLoading = ref(false)
  const error = ref(null)
  
  let currentInterval = initialInterval
  let unchangedCount = 0
  let lastDataHash = null
  let timeoutId = null
  let isVisible = true
  let lastActivity = Date.now()
  let controller = null

  // Функція для хешування даних
  const hashData = (data) => {
    return JSON.stringify(data)
  }

  // Функція запиту
  const fetchData = async () => {
    if (!isVisible) return // Не робити запити якщо вкладка неактивна
    
    try {
      isLoading.value = true
      error.value = null
      controller = new AbortController() // Створюємо новий контролер
      const response = await tonapi.get(url, { signal: controller.signal })
      const newDataHash = hashData(response.data)
      
      // Перевіряємо чи змінились дані
      if (lastDataHash === newDataHash) {
        unchangedCount++
        // Збільшуємо інтервал якщо дані не змінюються
        if (unchangedCount >= unchangedThreshold) {
          currentInterval = Math.min(currentInterval * backoffMultiplier, maxInterval)
        }
      } else {
        // Дані змінились - повертаємо початковий інтервал
        unchangedCount = 0
        currentInterval = initialInterval
        lastDataHash = newDataHash
        data.value = response.data
      }
    } catch (err) {
      if (err.name === 'AbortError') return // Ігноруємо помилки скасування
      error.value = err
      // При помилці збільшуємо інтервал
      currentInterval = Math.min(currentInterval * backoffMultiplier, maxInterval)
    } finally {
      isLoading.value = false
      controller = null // Очищаємо контролер
      scheduleNext()
    }
  }

  // Планування наступного запиту
  const scheduleNext = () => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(fetchData, currentInterval)
  }

  // Відстеження активності користувача
  const updateActivity = () => {
    lastActivity = Date.now()
    // Якщо користувач активний і інтервал великий - зменшуємо його
    if (currentInterval > initialInterval) {
      currentInterval = initialInterval
      unchangedCount = 0
    }
  }

  // Відстеження видимості вкладки
  const handleVisibilityChange = () => {
    isVisible = !document.hidden
    if (isVisible) {
      // Коли вкладка стає активною - одразу робимо запит
      fetchData()
    } else {
      if (controller) controller.abort() // Скасовуємо активний запит
      // Коли вкладка неактивна - зупиняємо запити
      clearTimeout(timeoutId)
    }
  }

  // Зупинка при неактивності
  const checkInactivity = () => {
    const inactiveTime = Date.now() - lastActivity
    if (inactiveTime > 60000) { // 1 хвилина неактивності
      currentInterval = maxInterval
    }
  }

  // Відстеження змін URL
  if (typeof url === 'object' && url !== null && 'value' in url) {
    watch(url, (newUrl) => {
      // Скидаємо стан при зміні URL
      unchangedCount = 0
      lastDataHash = null
      currentInterval = initialInterval
      data.value = null
      clearTimeout(timeoutId)
      fetchData(newUrl)
    })
  }

  onMounted(() => {
    // Перший запит
    fetchData()
    
    // Слухачі подій
    document.addEventListener('visibilitychange', handleVisibilityChange)
    document.addEventListener('click', updateActivity)
    document.addEventListener('keydown', updateActivity)
    document.addEventListener('scroll', updateActivity)
    
    // Перевірка неактивності кожну хвилину
    setInterval(checkInactivity, 60000)
  })

  onUnmounted(() => {
    clearTimeout(timeoutId)
    if (controller) controller.abort() // Скасовуємо запит при знищенні
    document.removeEventListener('visibilitychange', handleVisibilityChange)
    document.removeEventListener('click', updateActivity)
    document.removeEventListener('keydown', updateActivity)
    document.removeEventListener('scroll', updateActivity)
  })

  return {
    data,
    isLoading,
    error,
    currentInterval: ref(currentInterval)
  }
}