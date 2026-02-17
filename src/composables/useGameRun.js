import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { host } from '../../axios.config'

/**
 * НАСТРОЙКИ ГЕНЕРАЦИИ ПОИНТОВ И ЗАВЕРШЕНИЯ ЗАБЕГА
 *
 * ENERGY_POINTS_BASE_COUNT - базовое количество поинтов за забег
 *   Можно менять: например, 100, 120, 150 и т.д.
 *
 * ENERGY_POINTS_RESERVE_PERCENT - процент запаса поинтов сверх базового количества (редактируемо: 5-15%)
 *   Запас нужен чтобы поинты продолжали спавниться даже если некоторые пропущены
 *   Например: 100 базовых + 10% запаса = 110 поинтов всего будет сгенерировано
 *   Рекомендуется: 10% (можно менять от 5% до 15%)
 *
 * ВАЖНО: 100% дистанции = базовое количество + запас
 *   Например: 100 + 10% = 110 токенов = 100% дистанции
 *
 * УСЛОВИЯ ЗАВЕРШЕНИЯ ЗАБЕГА:
 *   1. Пробежал все 100% дистанции (прошло базовое количество + запас поинтов)
 *   2. Собрал весь Storage (все поинты собраны, даже если не все прошли)
 *   3. Потерял все жизни (hitCount >= 3, обрабатывается в GameRunView.vue)
 */
const ENERGY_POINTS_BASE_COUNT = 200
const ENERGY_POINTS_RESERVE_PERCENT = 10

/**
 * Генерирует массив поинтов энергии. Проценты масштабируются от базового количества:
 * при BASE=100: 0.5%, 1%, 2%; при BASE=1000: 0.05%, 0.1%, 0.2%.
 * Сумма всех поинтов = 100% storage. Крупные (2×) поинты — светящиеся (isGlowing).
 * Распределение по типам: 40%×мелкие(0.5×), 40%×средние(1×), 20%×крупные(2×).
 *
 * Генерируется больше поинтов чем базовое количество (с запасом),
 * чтобы поинты продолжали спавниться даже если некоторые пропущены.
 */
function generateEnergyPoints(storageKw) {
  const storage = Math.max(1, Number(storageKw) || 70)

  // Рассчитываем общее количество поинтов с учетом запаса
  const totalPointsCount = Math.ceil(ENERGY_POINTS_BASE_COUNT * (1 + ENERGY_POINTS_RESERVE_PERCENT / 100))

  // Масштаб процента: при 100 поинтах 1% = 1%, при 1000 поинтах 1% → 0.1%
  const pctScale = 100 / ENERGY_POINTS_BASE_COUNT
  const pct05 = 0.5 * pctScale
  const pct1 = 1 * pctScale
  const pct2 = 2 * pctScale

  // Распределение по типам: 40% средние, 40% мелкие, 20% крупные (от totalPointsCount)
  const scale = totalPointsCount / ENERGY_POINTS_BASE_COUNT
  const count1pct = Math.round(40 * scale)
  const count05pct = Math.round(40 * scale)
  const count2pct = Math.round(20 * scale)

  const points = []
  for (let i = 0; i < count1pct; i++) points.push({ pct: pct1, isGlowing: false })
  for (let i = 0; i < count05pct; i++) points.push({ pct: pct05, isGlowing: false })
  for (let i = 0; i < count2pct; i++) points.push({ pct: pct2, isGlowing: true })

  // Перемешиваем поинты
  for (let i = points.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[points[i], points[j]] = [points[j], points[i]]
  }

  return points.map((p) => ({
    value: (storage * p.pct) / 100,
    isGlowing: p.isGlowing
  }))
}

export function useGameRun() {
  const app = useAppStore()

  const isRunning = ref(false)
  const isPaused = ref(false)
  const distance = ref(0)
  const energyCollected = ref(0)
  const obstaclesHit = ref(0)
  const runStartTime = ref(0)
  const runDuration = ref(0)

  const currentPower = computed(() => app.power || 100)
  const currentEnergy = computed(() => app.score || 0)
  // Максимум энергии за забег: используем сохраненное начальное значение storage
  // (fallback к текущему app.storage или 70 kW, если storage ещё не инициализирован).
  const currentStorage = computed(() => {
    // Если забег запущен, используем сохраненное начальное значение
    if (isRunning.value && startStorage.value > 0) {
      return startStorage.value
    }
    // Иначе используем текущее значение из app (для UI до старта забега)
    const s = app.storage
    return (s === null || s === undefined || s === 0) ? 70 : s
  })

  const energyPoints = ref([])
  const energyPointsIndex = ref(0)
  const passedPointsCount = ref(0)
  const collectedPointsCount = ref(0) // Счетчик собранных токенов
  // Массив собранных поинтов для проверки на сервере (защита от подмены данных)
  const collectedEnergyPoints = ref([]) // [{value: 0.5, timestamp: 1234567890}, ...]
  // Сохраняем начальное значение storage при старте забега (до обнуления на сервере)
  const startStorage = ref(0)

  // Общее количество сгенерированных поинтов (базовое количество + запас)
  const totalPoints = computed(() => energyPoints.value.length)

  // Количество поинтов для 100% дистанции (базовое количество + запас)
  // Например: 100 + 10% = 110 токенов = 100% дистанции
  const pointsFor100Percent = computed(() => {
    return Math.ceil(ENERGY_POINTS_BASE_COUNT * (1 + ENERGY_POINTS_RESERVE_PERCENT / 100))
  })

  // Прогресс дистанции: считается от общего количества поинтов (базовое + запас = 100%)
  // Например: если 110 токенов = 100%, то 55 токенов = 50%
  const distanceProgress = computed(() => {
    const total = pointsFor100Percent.value
    if (total <= 0) return 0
    return Math.min(100, (passedPointsCount.value / total) * 100)
  })

  const startRun = (initialStorage = null) => {
    isRunning.value = true
    isPaused.value = false
    distance.value = 0
    energyCollected.value = 0
    obstaclesHit.value = 0
    runStartTime.value = Date.now()

    // Используем переданное начальное значение storage или текущее значение из app
    // Если storage уже обнулен на сервере, используем сохраненное значение или fallback
    const storageKw = initialStorage ?? app.storage ?? (startStorage.value || 70)
    // Сохраняем начальное значение для использования в течение забега
    startStorage.value = storageKw
    energyPoints.value = generateEnergyPoints(storageKw)
    energyPointsIndex.value = 0
    passedPointsCount.value = 0
    collectedPointsCount.value = 0 // Сбрасываем счетчик собранных токенов
    collectedEnergyPoints.value = [] // Сбрасываем массив собранных поинтов
  }

  const getNextEnergyPoint = () => {
    const idx = energyPointsIndex.value

    // Если все поинты из очереди выданы
    if (idx >= energyPoints.value.length) {
      // Проверяем, достигнута ли 100% дистанции
      // Логика: 100 поинтов + х% = 100% дистанции
      // Например: 100 + 10% = 110 поинтов = 100% дистанции
      // Когда passedPointsCount достигает pointsFor100Percent (110), дистанция = 100%
      if (passedPointsCount.value >= pointsFor100Percent.value) {
        // Дистанция достигла 100%, больше поинтов не нужно
        return null
      }

      // Дистанция еще не достигла 100%, но поинты закончились
      // Это может произойти если поинты не спавнились из-за вероятности спавна (90% и 40%)
      // Генерируем дополнительные поинты порциями до достижения 100% дистанции
      // Используем сохраненное начальное значение storage
      const storageKw = startStorage.value || currentStorage.value
      const remainingPoints = pointsFor100Percent.value - passedPointsCount.value

      // Генерируем порцию дополнительных поинтов (небольшую, чтобы не генерировать слишком много)
      // Используем минимум из: 20% от базового количества или оставшееся количество + небольшой запас
      const additionalBatchSize = Math.min(
        Math.ceil(ENERGY_POINTS_BASE_COUNT * 0.2),
        remainingPoints + 5 // +5 для небольшого запаса
      )

      // Генерируем полный набор поинтов и берем только нужное количество
      const fullBatch = generateEnergyPoints(storageKw)
      const additionalPoints = fullBatch.slice(0, additionalBatchSize)

      // Добавляем их в очередь
      energyPoints.value.push(...additionalPoints)
    }

    // Проверяем еще раз после возможного добавления поинтов
    if (idx >= energyPoints.value.length) {
      return null
    }

    // Возвращаем следующий поинт из очереди
    energyPointsIndex.value = idx + 1
    return energyPoints.value[idx]
  }

  const markPointPassed = () => {
    passedPointsCount.value += 1
  }

  // Забег завершается когда:
  // 1. Пробежал все 100% дистанции (прошло базовое количество + запас поинтов)
  // 2. ИЛИ собрал весь Storage (собранная энергия >= максимального количества которое можно собрать)
  // 3. ИЛИ потерял все жизни (обрабатывается в GameRunView.vue через hitCount >= 3)
  const isRunComplete = () => {
    const total = totalPoints.value
    const for100Percent = pointsFor100Percent.value
    if (total <= 0 || for100Percent <= 0) return false

    // 1. Завершаем если пробежал все 100% дистанции (прошло базовое количество + запас поинтов)
    if (passedPointsCount.value >= for100Percent) return true

    // 2. ИЛИ если собрал весь Storage (собранная энергия >= максимального количества которое можно собрать)
    // Максимальное количество = начальное значение storage (сохраненное при старте забега)
    // Используем сохраненное значение, чтобы не зависеть от обнуления storage на сервере
    const maxCollectibleEnergy = startStorage.value || currentStorage.value
    if (maxCollectibleEnergy > 0 && energyCollected.value >= maxCollectibleEnergy) return true

    return false
  }

  const pauseRun = () => {
    isPaused.value = true
  }

  const resumeRun = () => {
    isPaused.value = false
    runStartTime.value = Date.now() - runDuration.value * 1000
  }

  const stopRun = () => {
    isRunning.value = false
    isPaused.value = false
    // НЕ сбрасываем startStorage здесь, так как он нужен для completeRun
    // startStorage будет сброшен после успешного завершения забега в completeRun
  }

  const updateDistance = (newDistance) => {
    distance.value = newDistance
    if (runStartTime.value > 0) {
      runDuration.value = (Date.now() - runStartTime.value) / 1000
    }
  }

  const collectEnergy = (amount) => {
    const oldValue = energyCollected.value
    energyCollected.value += amount
    collectedPointsCount.value += 1 // Увеличиваем счетчик собранных токенов
    // Сохраняем информацию о собранном поинте для проверки на сервере (защита от подмены)
    collectedEnergyPoints.value.push({
      value: amount,
      timestamp: Date.now() - runStartTime.value // Время относительно начала забега в миллисекундах
    })
    console.log('collectEnergy: amount=', amount, 'oldValue=', oldValue, 'newValue=', energyCollected.value, 'startStorage=', startStorage.value)
  }

  const hitObstacle = () => {
    obstaclesHit.value++
  }

  const completeRun = async (isWin = false) => {
    // Проверяем что забег был запущен (даже если уже остановлен через stopGameLoop)
    // Не проверяем isRunning.value, так как при проигрыше забег может быть остановлен до вызова completeRun
    if (!runStartTime.value || runStartTime.value === 0) {
      console.warn('completeRun called but run was not started')
      return null
    }

    // Защита от повторных вызовов
    if (completeRun._isProcessing) {
      console.warn('completeRun already processing, ignoring duplicate call')
      return null
    }
    completeRun._isProcessing = true

    try {
      const finalDuration = runDuration.value || ((Date.now() - runStartTime.value) / 1000)

      // Сохраняем значения ДО любых изменений состояния
      const savedEnergyCollected = energyCollected.value
      const savedStartStorage = startStorage.value > 0 ? startStorage.value : (app.storage > 0 ? app.storage : 70)

      // Ограничиваем собранную энергию максимумом начального storage (нельзя собрать больше чем было при старте)
      const limitedEnergyCollected = Math.min(savedEnergyCollected, savedStartStorage)

      console.log('completeRun: savedEnergyCollected=', savedEnergyCollected, 'savedStartStorage=', savedStartStorage, 'startStorage.value=', startStorage.value, 'app.storage=', app.storage, 'limitedEnergyCollected=', limitedEnergyCollected, 'isWin=', isWin)

      // Вычисляем сумму собранных поинтов для проверки на сервере
      const collectedPointsSum = collectedEnergyPoints.value.reduce((sum, point) => sum + point.value, 0)
      console.log('completeRun: collectedPointsSum=', collectedPointsSum, 'limitedEnergyCollected=', limitedEnergyCollected, 'collectedPointsCount=', collectedPointsCount.value, 'collectedEnergyPoints.length=', collectedEnergyPoints.value.length)

      // ОПТИМИЗАЦИЯ: Ограничиваем количество поинтов до разумного максимума (200)
      // и отправляем только значения (без timestamp) для уменьшения размера данных
      // Timestamp нужен только для дополнительной проверки, основная проверка - сумма значений
      const pointsToSend = collectedEnergyPoints.value.slice(0, 200).map(point => ({
        value: Number(point.value.toFixed(2)) // Округляем до 2 знаков для точности
        // timestamp_ms убран для оптимизации размера данных - основная проверка по сумме значений
      }))

      const runData = {
        distance: distance.value,
        energy_collected: limitedEnergyCollected,
        run_duration: finalDuration,
        obstacles_hit: obstaclesHit.value,
        power_used: Math.max(0, 100 - currentPower.value),
        is_win: isWin,
        bonus_multiplier: 1.0, // Можно добавить логику бустеров
        // Отправляем массив собранных поинтов для проверки на сервере (защита от подмены)
        collected_points: pointsToSend
      }

      console.log('completeRun: Sending runData with energy_collected=', runData.energy_collected, 'from savedEnergyCollected=', savedEnergyCollected, 'collected_points_count=', runData.collected_points.length, 'collected_points_sum=', collectedPointsSum)

      console.log('Sending game-run-complete request:', runData)

      const response = await host.post('game-run-complete/', runData)
      console.log('game-run-complete response:', response.data)

      if (response.status === 200 && response.data) {
        // НЕ обновляем состояние приложения здесь - энергия еще не начислена
        // Начисление произойдет при нажатии "Забрать" через handleClaim()
        // Возвращаем данные для сохранения в completedRunData
        return {
          success: true,
          energy_collected: response.data.energy_collected ?? limitedEnergyCollected,
          energy_gained: response.data.energy_gained,
          is_win: response.data.is_win ?? isWin,
          total_energy: response.data.total_energy,  // Текущий баланс (без начисления)
          storage: response.data.storage,
          power: response.data.power,
          bonuses: response.data.bonuses,
          penalties: response.data.penalties
        }
      }

      return null
    } catch (error) {
      console.error('Ошибка завершения забега:', error)
      console.error('Error response:', error.response?.data)
      return {
        success: false,
        error: error.response?.data?.error || 'Неизвестная ошибка'
      }
    } finally {
      completeRun._isProcessing = false
      // Останавливаем забег, но НЕ сбрасываем startStorage и energyCollected здесь
      // Они нужны для отображения в модалке и будут сброшены только после нажатия "Забрать"
      isRunning.value = false
      isPaused.value = false
      // startStorage и energyCollected остаются для отображения в модалке
    }
  }

  return {
    isRunning,
    isPaused,
    distance,
    energyCollected,
    obstaclesHit,
    runDuration,
    currentPower,
    currentEnergy,
    currentStorage,
    startStorage, // Экспортируем ref напрямую для возможности изменения
    energyPoints,
    totalPoints,
    passedPointsCount,
    collectedPointsCount,
    distanceProgress,
    getNextEnergyPoint,
    markPointPassed,
    isRunComplete,
    startRun,
    pauseRun,
    resumeRun,
    stopRun,
    updateDistance,
    collectEnergy,
    hitObstacle,
    completeRun
  }
}
