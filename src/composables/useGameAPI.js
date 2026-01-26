import { ref } from 'vue'
import { host } from '../../axios.config'

export function useGameAPI() {
  const isLoading = ref(false)
  const error = ref(null)
  
  const completeRun = async (runData) => {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await host.post('game-run-complete/', runData)
      return {
        success: true,
        data: response.data
      }
    } catch (err) {
      error.value = err.response?.data?.error || 'Ошибка завершения забега'
      return {
        success: false,
        error: error.value
      }
    } finally {
      isLoading.value = false
    }
  }
  
  return {
    isLoading,
    error,
    completeRun
  }
}
