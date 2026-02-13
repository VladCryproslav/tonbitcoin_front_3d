<template>
  <div class="overheat-modal-mask" @click.self="handleBackdropClick">
    <div class="overheat-modal-wrapper">
      <div class="overheat-modal-container" :class="{ 'pulsing-red': isOverheatActive, 'cooled-down': !isOverheatActive }">
        <div class="overheat-modal-header">
          <img src="@/assets/warning.png" width="74px" alt="Warning" />
          <h1>{{ t('game.overheat_title') }}</h1>
        </div>
        <div class="overheat-modal-body">
          <div class="overheat-message" v-html="isOverheatActive ? t('game.overheat_desc') : t('game.overheat_ready_desc')"></div>
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
            v-if="showNitrogenButton"
            class="btn-primary btn-primary--secondary btn-primary--wide btn-activate-nitrogen"
            :class="{ 'btn-buy-nitrogen': !canUseFreeNitrogen }"
            @click.stop.prevent="handleUseNitrogen"
            :disabled="isUsingNitrogen"
          >
            <span v-if="canUseFreeNitrogen" class="btn-activate-nitrogen__text">{{ t('game.activate_nitrogen') }}</span>
            <span v-else class="btn-activate-nitrogen__text">{{ t('game.buy_nitrogen') }}</span>
            <span v-if="canUseFreeNitrogen" class="btn-activate-nitrogen__available">{{ t('game.available') }}: {{ nitrogenUsesLeft }}</span>
            <span v-else class="btn-activate-nitrogen__price">
              <img v-if="paymentRadio === 'fbtc'" src="@/assets/fBTC.webp" width="15px" alt="fBTC" />
              <img v-else src="@/assets/stars.png" width="15px" alt="Stars" />
              {{ azotPrice }}
            </span>
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
import { useTelegram } from '@/services/telegram'
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
const { tg } = useTelegram()

// Режим оплаты (по умолчанию stars)
const paymentRadio = ref('stars')

// Текущее время для реактивной проверки перегрева
const currentTime = ref(new Date())

// Обновляем текущее время каждую секунду для проверки окончания перегрева
let timeInterval = null

onMounted(async () => {
  timeInterval = setInterval(() => {
    currentTime.value = new Date()
  }, 1000) // Обновляем каждую секунду
  
  // Инициализируем бустеры если их еще нет
  if (!app.boosters || app.boosters.length === 0) {
    await app.initBoosters()
  }
})

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval)
    timeInterval = null
  }
})

// Отслеживаем изменения пропса overheatedUntil (без логирования)

const isOverheatActive = computed(() => {
  if (!props.overheatedUntil) {
    // Если нет данных о перегреве, считаем что перегрев не активен
    return false
  }
  const overheatedUntilDate = new Date(props.overheatedUntil)
  const now = currentTime.value
  const isActive = overheatedUntilDate > now
  
  // Убрана отладочная информация о времени
  
  return isActive
})

// Проверка доступности бесплатного азота (логика из Boost.vue isFreeBooster)
const isFreeNitrogen = computed(() => {
  const user = app.user
  if (!user) return false
  
  const hourDiff = user.azot_activated 
    ? Math.max(0, Math.floor((new Date() - new Date(user.azot_activated)) / (1000 * 60 * 60)))
    : 24
  
  // Азот бесплатный если: прошло 24 часа ИЛИ есть azot_uses_left/azot_reward_balance
  return hourDiff >= 24 || (user.azot_uses_left || 0) + (user.azot_reward_balance || 0) > 0
})

// Кнопка азота должна показываться всегда (либо бесплатно, либо купить)
const showNitrogenButton = computed(() => {
  return true // Всегда показываем кнопку
})

// Проверка доступности бесплатного азота для отображения
const canUseFreeNitrogen = computed(() => {
  return isFreeNitrogen.value
})

const nitrogenUsesLeft = computed(() => {
  const user = app.user
  if (!user) return 0
  
  const hourDiff = user.azot_activated 
    ? Math.max(0, Math.floor((new Date() - new Date(user.azot_activated)) / (1000 * 60 * 60)))
    : 24
  
  const hasSilverSBT = user.has_silver_sbt && user.has_silver_sbt_nft
  const hasGoldSBT = user.has_gold_sbt && user.has_gold_sbt_nft
  const premiumActive = user.premium_sub_expires && new Date(user.premium_sub_expires) > new Date()
  
  const azotUsesLeft = user.azot_uses_left || 0
  const azotRewardBalance = user.azot_reward_balance || 0
  
  let freeUses = 0
  if (hourDiff >= 24) {
    freeUses = hasGoldSBT || premiumActive ? 2 : hasSilverSBT ? 1 : 1
  }
  
  return azotUsesLeft + azotRewardBalance + freeUses
})

// Получаем информацию о бустере азота
const azotBooster = computed(() => {
  return app.boosters?.find(b => b.slug === 'azot')
})

// Расчет цены азота (логика из Boost.vue getTotalStarsPrice)
const azotPrice = computed(() => {
  const booster = azotBooster.value
  const user = app.user
  if (!booster || !user) return 0
  
  const premiumActive = user.premium_sub_expires && new Date(user.premium_sub_expires) > new Date()
  const hasSilverSBT = user.has_silver_sbt && user.has_silver_sbt_nft
  const hasGoldSBT = user.has_gold_sbt && user.has_gold_sbt_nft
  
  let sum = (paymentRadio.value == 'fbtc' ? booster?.price1_fbtc : booster?.price1) + (booster?.n1 || 0) * (user.azot_counts || 0)
  
  if ((hasSilverSBT || hasGoldSBT || premiumActive) && paymentRadio.value == 'stars') {
    sum = Math.floor(sum * (100 - (hasSilverSBT ? 5 : (hasGoldSBT || premiumActive) ? 10 : 0)) / 100)
  }
  
  return Math.ceil(sum)
})

const isUsingNitrogen = ref(false)

const handleContinue = () => {
  if (!isOverheatActive.value) {
    emit('continue')
  }
}

const handleUseNitrogen = async () => {
  if (isUsingNitrogen.value) {
    return
  }
  
  isUsingNitrogen.value = true
  let response = null
  
  try {
    const isFree = isFreeNitrogen.value
    const activate_url = paymentRadio.value == 'fbtc' ? "tasks/activate_booster_fbtc/" : "tasks/activate_booster/"
    
    response = await host.post(activate_url, {
      slug: 'azot',
      day_count: null // Азот не требует day_count
    })
    
    if (response.status === 200) {
      if (isFree || paymentRadio.value == 'fbtc') {
        // Бесплатный бустер или fBTC - сразу активируем
        await app.initUser()
        emit('continue')
        isUsingNitrogen.value = false
      } else {
        // Покупка через invoice
        const invoiceLink = response.data?.link
        if (invoiceLink && tg) {
          tg.openInvoice(invoiceLink, async (status) => {
            if (status == 'paid') {
              await app.initUser()
              emit('continue')
            }
            isUsingNitrogen.value = false
          })
          return // Не сбрасываем isUsingNitrogen здесь, так как это сделается в callback
        } else {
          isUsingNitrogen.value = false
        }
      }
    } else {
      console.error('Failed to activate nitrogen:', response)
      isUsingNitrogen.value = false
    }
  } catch (error) {
    console.error('Error activating nitrogen:', error)
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
  
  &__price {
    font-size: 11px;
    opacity: 0.8;
    font-weight: 500;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
  }
  
  &.btn-buy-nitrogen {
    background: linear-gradient(135deg, #e757ec 0%, #9851ec 50%, #5e7cea 100%);
    box-shadow: 0 12px 30px rgba(102, 126, 234, 0.45);
    
    &:hover:not(:disabled) {
      opacity: 0.9;
    }
    
    &:active:not(:disabled) {
      transform: scale(0.96);
      box-shadow: 0 6px 18px rgba(102, 126, 234, 0.35);
    }
  }
}
</style>
