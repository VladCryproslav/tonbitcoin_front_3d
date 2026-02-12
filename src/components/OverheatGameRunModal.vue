<template>
  <div class="overheat-modal-mask" @click.self="handleBackdropClick">
    <div class="overheat-modal-wrapper">
      <div class="overheat-modal-container" :class="{ 'pulsing-red': isOverheatActive }">
        <div class="overheat-modal-header">
          <img src="@/assets/warning.png" width="74px" alt="Warning" />
          <h1>{{ t('game.overheat_title') }}</h1>
        </div>
        <div class="overheat-modal-body">
          <div class="overheat-message" v-html="t('game.overheat_desc')"></div>
        </div>
        <div class="overheat-modal-actions">
          <!-- Кнопка использования азота (если доступен) -->
          <button
            v-if="isOverheatActive && canUseNitrogen"
            class="btn-primary btn-primary--wide btn-nitrogen"
            @click.stop.prevent="handleUseNitrogen"
            :disabled="isUsingNitrogen"
          >
            {{ t('game.use_nitrogen') }} ({{ nitrogenUsesLeft }})
          </button>
          
          <!-- Кнопка "Продолжить" -->
          <button
            class="btn-primary btn-primary--wide"
            :class="{ 'btn-disabled': isOverheatActive }"
            :disabled="isOverheatActive"
            @click.stop.prevent="handleContinue"
          >
            {{ t('game.continue') }}
          </button>
          
          <!-- Кнопка "Назад" (только когда перегрев закончился) -->
          <button
            v-if="!isOverheatActive"
            class="btn-primary btn-primary--secondary btn-primary--wide"
            @click.stop.prevent="$emit('close')"
          >
            {{ t('game.back_to_main') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import { host } from '@/../axios.config'

const props = defineProps({
  overheatedUntil: {
    type: Date,
    required: true
  }
})

const emit = defineEmits(['continue', 'close'])

const { t } = useI18n()
const app = useAppStore()

const isOverheatActive = computed(() => {
  return props.overheatedUntil && new Date(props.overheatedUntil) > new Date()
})

// Проверка доступности азота
const canUseNitrogen = computed(() => {
  const user = app.user
  if (!user) return false
  
  // Проверяем наличие азота (azot_uses_left или azot_reward_balance)
  const totalNitrogen = (user.azot_uses_left || 0) + (user.azot_reward_balance || 0)
  return totalNitrogen > 0
})

const nitrogenUsesLeft = computed(() => {
  const user = app.user
  if (!user) return 0
  return (user.azot_uses_left || 0) + (user.azot_reward_balance || 0)
})

const isUsingNitrogen = ref(false)

const handleContinue = () => {
  if (!isOverheatActive.value) {
    emit('continue')
  }
}

const handleUseNitrogen = async () => {
  if (isUsingNitrogen.value || !canUseNitrogen.value) {
    return
  }
  
  isUsingNitrogen.value = true
  
  try {
    // Активируем азот через существующий endpoint
    const response = await host.post('tasks/activate_booster/', {
      slug: 'azot',
      day_count: null // Азот не требует day_count
    })
    
    if (response.status === 200) {
      // Обновляем данные пользователя
      await app.initUser()
      
      // Перегрев снят азотом, закрываем модалку и продолжаем забег
      // emit('continue') вызовет handleOverheatContinue в GameRunView
      emit('continue')
    } else {
      console.error('Failed to activate nitrogen:', response)
      // Можно показать ошибку пользователю
    }
  } catch (error) {
    console.error('Error activating nitrogen:', error)
    // Можно показать ошибку пользователю
  } finally {
    isUsingNitrogen.value = false
  }
}

const handleBackdropClick = () => {
  // Не закрываем при клике на backdrop во время перегрева
  if (!isOverheatActive.value) {
    emit('close')
  }
}
</script>

<style lang="scss" scoped>
.overheat-modal-mask {
  position: fixed;
  z-index: 9999;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
}

.overheat-modal-wrapper {
  width: 90%;
  max-width: 400px;
}

.overheat-modal-container {
  background: #10151b;
  border-radius: 1rem;
  padding: 2rem;
  box-shadow: inset 0 0 0 1px #ff3b59;
  transition: all 0.3s ease;
  
  &.pulsing-red {
    animation: pulseRed 1s ease-in-out infinite;
  }
}

@keyframes pulseRed {
  0%, 100% {
    box-shadow: inset 0 0 0 1px #ff3b59;
  }
  50% {
    box-shadow: inset 0 0 0 3px #ff3b59, 0 0 20px rgba(255, 59, 89, 0.5);
  }
}

.overheat-modal-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  
  h1 {
    color: #ff3b59;
    font-size: 18px;
    font-weight: 700;
    text-align: center;
  }
}

.overheat-modal-body {
  text-align: center;
  margin-bottom: 1.5rem;
  
  .overheat-message {
    color: #fff;
    font-size: 14px;
    line-height: 1.5;
  }
}

.overheat-modal-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  align-items: center;
  width: 100%;
}

.btn-primary {
  min-width: 220px;
  padding: 14px 32px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(135deg, #7c3aed, #22d3ee);
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 12px 30px rgba(56, 189, 248, 0.45);
  letter-spacing: 0.02em;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;

  &:active:not(:disabled) {
    transform: scale(0.96);
    box-shadow: 0 6px 18px rgba(56, 189, 248, 0.35);
    opacity: 0.9;
  }
}

.btn-primary--wide {
  width: 100%;
}

.btn-primary--secondary {
  background: rgba(15, 23, 42, 0.8);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  
  &:active:not(:disabled) {
    transform: scale(0.9);
    opacity: 0.85;
  }
}

.btn-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  
  &:active {
    transform: none;
  }
}

.btn-nitrogen {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  box-shadow: 0 12px 30px rgba(102, 126, 234, 0.45);
  
  &:hover:not(:disabled) {
    opacity: 0.9;
  }
  
  &:active:not(:disabled) {
    transform: scale(0.96);
    box-shadow: 0 6px 18px rgba(102, 126, 234, 0.35);
  }
}
</style>
