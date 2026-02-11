import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { host } from '../../axios.config'

// Количество энергетических поинтов за забег (редактируемо)
const ENERGY_POINTS_COUNT = 100

/**
 * Генерирует массив поинтов энергии: 0.5%, 1%, 2% от storage.
 * Сумма = storage. 2% поинты — светящиеся (isGlowing).
 * Распределение: 40×1%, 40×0.5%, 20×2% = 100%
 */
function generateEnergyPoints(storageKw) {
  const storage = Math.max(1, Number(storageKw) || 70)
  const points = []
  for (let i = 0; i < 40; i++) points.push({ pct: 1, isGlowing: false })
  for (let i = 0; i < 40; i++) points.push({ pct: 0.5, isGlowing: false })
  for (let i = 0; i < 20; i++) points.push({ pct: 2, isGlowing: true })

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

  const totalPoints = computed(() => energyPoints.value.length)
  const distanceProgress = computed(() => {
    const total = totalPoints.value
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
    if (idx >= energyPoints.value.length) return null
    energyPointsIndex.value = idx + 1
    return energyPoints.value[idx]
  }

  const markPointPassed = () => {
    passedPointsCount.value += 1
  }

  // Забег завершается когда:
  // 1. Все поинты прошли (собраны или пропущены) - 100% дистанции
  // 2. ИЛИ все поинты собраны (даже если не все прошли)
  const isRunComplete = () => {
    const total = totalPoints.value
    if (total <= 0) return false
    // Завершаем если все поинты прошли (100% дистанции)
    if (passedPointsCount.value >= total) return true
    // ИЛИ если все поинты собраны (пользователь собрал все токены)
    if (collectedPointsCount.value >= total) return true
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

  const completeRun = async () => {
    if (!isRunning.value) return null

    const finalDuration = runDuration.value || ((Date.now() - runStartTime.value) / 1000)

    const runData = {
      distance: distance.value,
      energy_collected: energyCollected.value,
      run_duration: finalDuration,
      obstacles_hit: obstaclesHit.value,
      power_used: Math.max(0, 100 - currentPower.value),
      bonus_multiplier: 1.0 // Можно добавить логику бустеров
    }

    try {
      const response = await host.post('game-run-complete/', runData)

      if (response.status === 200) {
        // Обновляем состояние приложения
        app.setScore(response.data.total_energy)
        app.setStorage(response.data.storage)
        app.setPower(response.data.power)

        return {
          success: true,
          energyGained: response.data.energy_gained,
          totalEnergy: response.data.total_energy,
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
