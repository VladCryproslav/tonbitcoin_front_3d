<script setup>
import { useTonConnectUI } from '@townsquarelabs/ui-vue'
import { computed, defineAsyncComponent, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { host } from '../../axios.config'
import { useTelegram } from '@/services/telegram'
import { useAppStore } from '@/stores/app'

const Exit = defineAsyncComponent(() => import('@/assets/upg-modal-close.svg'))
const { t } = useI18n()
const app = useAppStore()
const { tg } = useTelegram()
const { tonConnectUI, setOptions } = useTonConnectUI()
const emit = defineEmits(['close'])

const props = defineProps({
  address: {
    type: String
  },
  wallet: {
    type: Boolean
  },
})

const selectedNft = computed(() => {
  return props.address ? app.timed_nfts?.find(el => el.nft_address == props.address) : null
})

let timeRemainingInterval = null
const getTimeRemaining = (futureISO) => {
  if (!futureISO) {
    return '00:00:00'
  }

  const timeRemaining = ref('00:00:00')
  const timeRemainingMs = ref(null)
  const updateTime = () => {
    const now = new Date()
    const future = new Date(futureISO)
    const diffMs = future - now
    timeRemainingMs.value = diffMs

    if (diffMs <= 0) {
      return '00:00:00'
    }

    const hours = Math.floor(diffMs / (1000 * 60 * 60))
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))
    const seconds = Math.floor((diffMs % (1000 * 60)) / 1000)

    const formattedHours = String(hours).padStart(2, '0')
    const formattedMinutes = String(minutes).padStart(2, '0')
    const formattedSeconds = String(seconds).padStart(2, '0')

    timeRemaining.value = `${formattedHours}:${formattedMinutes}:${formattedSeconds}`
  }

  // Оновлюємо одразу
  updateTime()

  // Запускаємо таймер для оновлення кожну секунду
  timeRemainingInterval = setInterval(updateTime, 1000)

  return { time: timeRemaining.value, remain: timeRemainingMs.value }
}


const btnAction = () => {
  if (props.wallet) {
    tonConnectUI.disconnect()
    emitClose()
  } else {
    emitClose()
  }
}

const speedUp = async () => {
  if (props.wallet) {
    try {
      const res = await host.post('user-wallet-info-stars/')
      if (res.status == 200) {
        const invoiceLink = res.data?.link
        tg.openInvoice(invoiceLink, async (status) => {
          if (status == 'paid') {
            app.initUser()
            emitClose()
          }
        })
      }
    } catch (error) {
      console.log(error)
    }
  } else {
    if (props.address) {
      try {
        const res = await host.post('timed-nft-stars/', { timed_nft_id: selectedNft.value?.id})
        if (res.status == 200) {
          const invoiceLink = res.data?.link
          tg.openInvoice(invoiceLink, async (status) => {
            if (status == 'paid') {
              app.initUser()
              emitClose()
            }
          })
        }
      } catch (error) {
        console.log(error)
      }
    }
  }
}

const emitClose = () => {
  emit('close')
}

onUnmounted(() => {
  if (timeRemainingInterval) {
    clearInterval(timeRemainingInterval)
  }
})
</script>

<template>
  <div class="modal-mask" name="modal">
    <div class="modal-wrapper">
      <div class="modal-container">
        <button class="close" @click="emitClose">
          <Exit style="color: #fff" />
        </button>
        <div class="grouping">
          <div class="modal-header">
            <slot name="header">{{ props.wallet ? t('modals.speedup.title') : t('modals.info_modal.title') }}</slot>
          </div>
          <div class="modal-body"
            v-html="props.wallet ? t('modals.speedup.description_1') : t('modals.speedup.description_2')"></div>
          <div class="time-remaining" v-if="props.wallet">
            {{ getTimeRemaining(app.wallet_info.block_until).time }}
          </div>
          <div class="time-remaining" v-else>
            {{ getTimeRemaining(selectedNft?.block_until).time }}
          </div>
          <div class="buttons-group">
            <button class="change" @click="btnAction">{{ props.wallet ? t('modals.speedup.change') : t('common.confirm')
              }}</button>
            <button class="stars" @click="speedUp">
              {{ t('common.speedup') }}
              <img src="@/assets/stars.png" width="18px" height="18px" alt="start" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.modal-mask {
  position: fixed;
  z-index: 9998;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: table;
  background-color: #00000050;
  transition: opacity 0.3s ease;
}

.modal-wrapper {
  display: table-cell;
  vertical-align: middle;
}

.modal-container {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  margin: 0px auto;
  width: 90%;
  padding: 15px 0 10px;
  background: #10151b;
  transition: all 0.3s ease;
  box-shadow: inset 0 0 0 1px #ffffff70;
  font-family: Helvetica, Arial, sans-serif;
  border-radius: 1rem;

  .close {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
  }

  .grouping {
    width: 90%;
    display: flex;
    flex-direction: column;
    align-items: start;
    gap: 0.5rem;

    .price {
      width: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      gap: 0.5rem;

      .kw-price,
      .tbtc-price {
        width: 100%;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: #fff;
        font-family: 'Inter' !important;
        font-size: 11px;
      }
    }

    .buttons-group {
      width: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 1rem;
      margin-bottom: 5px;

      .change {
        width: 50%;
        padding: 0.3rem 0.5rem;
        color: #000;
        border-radius: 5rem;
        background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
          linear-gradient(to bottom, #e2f974, #009600);
        box-shadow:
          inset 0 0 0 2px #10151b,
          0 0 0 1px #8be113;

        &:active {
          background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
            linear-gradient(to bottom, #e2f97490, #00960090);
        }
      }

      .stars {
        width: 50%;
        padding: 0.3rem 0.5rem;
        border-radius: 5rem;
        display: flex;
        gap: 5px;
        justify-content: center;
        align-items: center;
        color: #fff;
        background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
          linear-gradient(to left, #e757ec, #9851ec, #5e7cea);
        box-shadow:
          inset 0 0 0 2px #10151b,
          0 0 0 1px #9851ec;

        &:active {
          background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
            linear-gradient(to left, #e757ec90, #9851ec90, #5e7cea90);
        }
      }
    }
  }
}

.modal-header {
  width: 100%;
  text-align: center;
  color: #fff;
  font-weight: 600;
  font-size: 18px;
  line-height: 1.3;
  font-family: 'Inter' !important;
}

.modal-body {
  white-space: pre-wrap;
  text-align: center;
  font-family: 'Inter' !important;
  font-weight: 500;
  font-size: 13.5px;
  color: #8b898b;
  width: 100%;
}

.time-remaining {
  color: #fff;
  font-family: 'Inter' !important;
  font-weight: 700;
  font-size: 24px;
  width: 100%;
  margin: 0 0 10px;
}

.modal-default-button {
  float: right;
}

.modal-enter {
  opacity: 0;
}

.modal-leave-active {
  opacity: 0;
}

.modal-enter .modal-container,
.modal-leave-active .modal-container {
  -webkit-transform: scale(1.1);
  transform: scale(1.1);
}
</style>
