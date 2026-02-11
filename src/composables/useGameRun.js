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
const ENERGY_POINTS_BASE_COUNT = 100
const ENERGY_POINTS_RESERVE_PERCENT = 10

/**
 * Генерирует массив поинтов энергии: 0.5%, 1%, 2% от storage.
 * Сумма = storage. 2% поинты — светящиеся (isGlowing).
 * Распределение: 40×1%, 40×0.5%, 20×2% = 100%
 * 
 * Генерируется больше поинтов чем базовое количество (с запасом),
 * чтобы поинты продолжали спавниться даже если некоторые пропущены.
 */
function generateEnergyPoints(storageKw) {
  const storage = Math.max(1, Number(storageKw) || 70)
  
  // Рассчитываем общее количество поинтов с учетом запаса
  const totalPointsCount = Math.ceil(ENERGY_POINTS_BASE_COUNT * (1 + ENERGY_POINTS_RESERVE_PERCENT / 100))
  
  // Распределяем проценты пропорционально базовому количеству
  // Базовое распределение: 40×1%, 40×0.5%, 20×2% = 100 поинтов
  // Масштабируем пропорционально для общего количества
  const scale = totalPointsCount / ENERGY_POINTS_BASE_COUNT
  const count1pct = Math.round(40 * scale)
  const count05pct = Math.round(40 * scale)
  const count2pct = Math.round(20 * scale)
  
  const points = []
  for (let i = 0; i < count1pct; i++) points.push({ pct: 1, isGlowing: false })
  for (let i = 0; i < count05pct; i++) points.push({ pct: 0.5, isGlowing: false })
  for (let i = 0; i < count2pct; i++) points.push({ pct: 2, isGlowing: true })

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
  // Максимум энергии за забег: используем ту же логику, что и при генерации поинтов
  // (fallback к 70 kW, если storage ещё не инициализирован).
  const currentStorage = computed(() => {
    const s = app.storage
    return (s === null || s === undefined) ? 70 : s
  })

  const energyPoints = ref([])
  const energyPointsIndex = ref(0)
  const passedPointsCount = ref(0)
  const collectedPointsCount = ref(0) // Счетчик собранных токенов

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

  const startRun = () => {
    isRunning.value = true
    isPaused.value = false
    distance.value = 0
    energyCollected.value = 0
    obstaclesHit.value = 0
    runStartTime.value = Date.now()

    const storageKw = app.storage ?? 70
    energyPoints.value = generateEnergyPoints(storageKw)
    energyPointsIndex.value = 0
    passedPointsCount.value = 0
    collectedPointsCount.value = 0 // Сбрасываем счетчик собранных токенов
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
      const storageKw = currentStorage.value
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
    // Максимальное количество = storage (сумма всех поинтов)
    const maxCollectibleEnergy = currentStorage.value
    if (energyCollected.value >= maxCollectibleEnergy) return true
    
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
  }

  const updateDistance = (newDistance) => {
    distance.value = newDistance
    if (runStartTime.value > 0) {
      runDuration.value = (Date.now() - runStartTime.value) / 1000
    }
  }

  const collectEnergy = (amount) => {
    energyCollected.value += amount
    collectedPointsCount.value += 1 // Увеличиваем счетчик собранных токенов
  }

  const hitObstacle = () => {
    obstaclesHit.value++
  }

  const completeRun = async (isWin = false) => {
    if (!isRunning.value) {
      console.warn('completeRun called but game is not running')
      return null
    }

    const finalDuration = runDuration.value || ((Date.now() - runStartTime.value) / 1000)
    
    // Ограничиваем собранную энергию максимумом storage (нельзя собрать больше чем storage)
    const maxCollectibleEnergy = currentStorage.value
    const limitedEnergyCollected = Math.min(energyCollected.value, maxCollectibleEnergy)

    const runData = {
      distance: distance.value,
      energy_collected: limitedEnergyCollected,
      run_duration: finalDuration,
      obstacles_hit: obstaclesHit.value,
      power_used: Math.max(0, 100 - currentPower.value),
      is_win: isWin,
      bonus_multiplier: 1.0 // Можно добавить логику бустеров
    }

    console.log('Sending game-run-complete request:', runData)

    try {
      const response = await host.post('game-run-complete/', runData)
      console.log('game-run-complete response:', response.data)

      if (response.status === 200 && response.data) {
        // Обновляем состояние приложения
        if (response.data.total_energy !== undefined) {
          app.setScore(response.data.total_energy)
        }
        if (response.data.storage !== undefined) {
          app.setStorage(response.data.storage)
        }
        if (response.data.power !== undefined) {
          app.setPower(response.data.power)
        }

        return {
          success: true,
          energyGained: response.data.energy_gained,
          totalEnergy: response.data.total_energy,
          storage: response.data.storage,
          power: response.data.power,
          bonuses: response.data.bonuses,
          penalties: response.data.penalties
        }
      }
    } catch (error) {
      console.error('Ошибка завершения забега:', error)
      return {
        success: false,
        error: error.response?.data?.error || 'Неизвестная ошибка'
      }
    } finally {
      stopRun()
    }

    return null
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
