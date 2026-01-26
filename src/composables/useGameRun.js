import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { host } from '../../axios.config'

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
  const currentStorage = computed(() => app.storage || 0)
  
  const startRun = () => {
    isRunning.value = true
    isPaused.value = false
    distance.value = 0
    energyCollected.value = 0
    obstaclesHit.value = 0
    runStartTime.value = Date.now()
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
