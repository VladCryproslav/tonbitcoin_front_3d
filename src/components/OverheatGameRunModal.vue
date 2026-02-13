<template>
  <div class="overheat-modal-mask" @click.self="handleBackdropClick">
    <div class="overheat-modal-wrapper">
      <div class="overheat-modal-container" :class="{ 'pulsing-red': isOverheatActive, 'cooled-down': !isOverheatActive }">
        <div class="overheat-modal-header">
          <img src="@/assets/warning.png" width="74px" alt="Warning" />
          <h1>{{ t('game.overheat_title') }}</h1>
        </div>
        <div class="overheat-modal-body">
          <div class="overheat-message" v-html="t('game.overheat_desc')"></div>
        </div>
        <div class="overheat-modal-actions">
          <!-- Кнопка "Продолжить" -->
          <button
            class="btn-primary btn-primary--wide"
            :class="{ 'btn-disabled': isOverheatActive }"
            :disabled="isOverheatActive"
            @click.stop.prevent="handleContinue"
          >
            {{ t('game.continue') }}
          </button>
          
          <!-- Кнопка активации азота (под кнопкой продолжить) -->
          <button
            v-if="canUseNitrogen"
            class="btn-primary btn-primary--secondary btn-primary--wide btn-activate-nitrogen"
            @click.stop.prevent="handleUseNitrogen"
            :disabled="isUsingNitrogen"
          >
            <span class="btn-activate-nitrogen__text">{{ t('game.activate_nitrogen') }}</span>
            <span class="btn-activate-nitrogen__available">{{ t('game.available') }}: {{ nitrogenUsesLeft }}</span>
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import { host } from '@/../axios.config'

const props = defineProps({
  overheatedUntil: {
    type: Date,
    default: null
  }
})

const emit = defineEmits(['continue', 'close'])

const { t } = useI18n()
const app = useAppStore()

// Текущее время для реактивной проверки перегрева
const currentTime = ref(new Date())

// Обновляем текущее время каждую секунду для проверки окончания перегрева
let timeInterval = null

onMounted(() => {
  timeInterval = setInterval(() => {
    currentTime.value = new Date()
  }, 1000) // Обновляем каждую секунду
})

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval)
    timeInterval = null
  }
})

// Отслеживаем изменения пропса overheatedUntil
watch(() => props.overheatedUntil, (newValue) => {
  if (newValue) {
    console.log('[OverheatModal] overheatedUntil обновлен:', new Date(newValue).toISOString())
  }
}, { immediate: true })

const isOverheatActive = computed(() => {
  if (!props.overheatedUntil) {
    // Если нет данных о перегреве, считаем что перегрев не активен
    return false
  }
  const overheatedUntilDate = new Date(props.overheatedUntil)
  const now = currentTime.value
  const isActive = overheatedUntilDate > now
  
  // Отладочная информация
  const secondsLeft = Math.max(0, Math.floor((overheatedUntilDate - now) / 1000))
  if (isActive && secondsLeft > 0 && secondsLeft % 5 === 0) {
    // Логируем каждые 5 секунд когда перегрев активен
    console.log(`[OverheatModal] Перегрев активен, осталось: ${secondsLeft} секунд (until: ${overheatedUntilDate.toISOString()}, now: ${now.toISOString()})`)
  } else if (!isActive && secondsLeft <= 0 && props.overheatedUntil) {
    // Логируем когда перегрев закончился
    console.log(`[OverheatModal] Перегрев закончился! (until: ${overheatedUntilDate.toISOString()}, now: ${now.toISOString()})`)
  }
  
  return isActive
})

// Проверка доступности азота (логика из Boost.vue)
const canUseNitrogen = computed(() => {
  const user = app.user
  if (!user) return false
  
  // Проверяем время с последней активации азота
  const hourDiff = user.azot_activated 
    ? Math.max(0, Math.floor((new Date() - new Date(user.azot_activated)) / (1000 * 60 * 60)))
    : 24 // Если никогда не активировался, считаем что прошло 24 часа
  
  // Проверяем наличие азота с учетом времени активации и SBT/premium статуса
  const hasSilverSBT = user.has_silver_sbt && user.has_silver_sbt_nft
  const hasGoldSBT = user.has_gold_sbt && user.has_gold_sbt_nft
  const premiumActive = user.premium_sub_expires && new Date(user.premium_sub_expires) > new Date()
  
  // Если прошло 24 часа с последней активации, добавляем бесплатные использования
  const freeUses = hourDiff >= 24 ? (hasGoldSBT || premiumActive ? 2 : hasSilverSBT ? 1 : 0) : 0
  
  // Общее количество доступного азота
  const totalNitrogen = (user.azot_uses_left || 0) + (user.azot_reward_balance || 0) + freeUses
  
  return totalNitrogen > 0
})

const nitrogenUsesLeft = computed(() => {
  const user = app.user
  if (!user) return 0
  
  // Проверяем время с последней активации азота
  const hourDiff = user.azot_activated 
    ? Math.max(0, Math.floor((new Date() - new Date(user.azot_activated)) / (1000 * 60 * 60)))
    : 24
  
  const hasSilverSBT = user.has_silver_sbt && user.has_silver_sbt_nft
  const hasGoldSBT = user.has_gold_sbt && user.has_gold_sbt_nft
  const premiumActive = user.premium_sub_expires && new Date(user.premium_sub_expires) > new Date()
  
  // Если прошло 24 часа с последней активации, добавляем бесплатные использования
  const freeUses = hourDiff >= 24 ? (hasGoldSBT || premiumActive ? 2 : hasSilverSBT ? 1 : 0) : 0
  
  return (user.azot_uses_left || 0) + (user.azot_reward_balance || 0) + freeUses
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
  
  &.cooled-down {
    box-shadow: inset 0 0 0 1px #31cfff;
    
    .overheat-modal-header h1 {
      color: #31cfff;
    }
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

.btn-activate-nitrogen {
  display: flex;
  flex-direction: column;
  gap: 4px;
  
  &__text {
    font-size: 17px;
    font-weight: 600;
  }
  
  &__available {
    font-size: 11px;
    opacity: 0.6;
    font-weight: 400;
  }
}
</style>
