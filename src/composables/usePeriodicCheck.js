import { ref, onUnmounted } from 'vue'

/**
 * Запускає періодичну асинхронну перевірку з урахуванням видимості сторінки.
 * @param {Function} asyncCallback - Асинхронна функція, яку потрібно викликати.
 * @param {number} intervalMs - Інтервал у мілісекундах.
 */
export function usePeriodicCheck(asyncCallback, intervalMs = 7000) {
  const timerId = ref(null)

  // Функція, яка виконує перевірку і планує наступну
  const runCheck = async () => {
    // Спочатку очищуємо попередній таймер, щоб уникнути дублів
    if (timerId.value) {
      clearTimeout(timerId.value)
    }

    // Виконуємо сам колбек
    await asyncCallback()

    // Плануємо наступний запуск
    timerId.value = setTimeout(runCheck, intervalMs)
  }

  // Функція для обробки зміни видимості вкладки
  const handleVisibilityChange = () => {
    if (document.hidden) {
      // Якщо вкладка стала неактивною - зупиняємо таймер
      clearTimeout(timerId.value)
    } else {
      // Якщо вкладка стала активною - негайно запускаємо перевірку і відновлюємо цикл
      runCheck()
    }
  }

  // Функція для старту
  const start = () => {
    // Запускаємо перший раз негайно, а потім по інтервалу
    runCheck()
    // Додаємо слухача на зміну видимості
    document.addEventListener('visibilitychange', handleVisibilityChange)
  }

  // Функція для повної зупинки
  const stop = () => {
    clearTimeout(timerId.value)
    document.removeEventListener('visibilitychange', handleVisibilityChange)
  }

  // Автоматично зупиняємо все, коли компонент демонтується
  onUnmounted(stop)

  // Повертаємо контроль назовні
  return { start, stop }
}