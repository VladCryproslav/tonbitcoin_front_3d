<script setup>
const Exit = defineAsyncComponent(() => import('@/assets/upg-modal-close.svg'))
import { useTelegram } from '@/services/telegram'
import { useAppStore } from '@/stores/app'
import { useTonAddress } from '@townsquarelabs/ui-vue'
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { host } from '../../axios.config'
import { useI18n } from 'vue-i18n'
import CustomSlider from './CustomSlider.vue'
import { max_fbtc } from '@/services/data'

const { t } = useI18n()

const app = useAppStore()

const props = defineProps({
  claim: Boolean,
})


const totalBalance = computed(() => {
  return app?.user?.mined_tokens_balance + app?.user?.mined_tokens_balance_s21 + app?.user?.mined_tokens_balance_sx
})

const premiumActive = computed(() => new Date(app.user?.premium_sub_expires) >= new Date())

const min = computed(() => props?.claim ? app.withdraw_config?.min_claim || 2 : app.withdraw_config?.min_tbtc || 50)
// available всегда показывает полное доступное количество
const available = computed(() => {
  return Math.max(0, Math.floor(app?.wallet_info?.tbtc_amount + app?.wallet_info?.tbtc_amount_s21 + app?.wallet_info?.tbtc_amount_sx))
})
const max = computed(() => {
  if (props?.claim) {
    // Для claim ограничиваем только max на 3000
    return Math.min(max_fbtc, Math.floor(totalBalance.value))
  } else {
    return Math.min(max_fbtc, Math.floor(app?.user?.tbtc_wallet))
  }
})

// Виправляємо ініціалізацію withdraw_amount (храним как число)
const withdraw_amount = ref(Math.min(max.value, available.value))

const commissionRate = computed(() => {
  return (app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 0.0085 : ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 0.007 : 0.01
})

const totalCommission = computed(() => {
  const amount = typeof withdraw_amount.value === 'number' ? withdraw_amount.value : parseFloat(withdraw_amount.value) || 0
  return amount < 100 ? 1 : +(amount * commissionRate.value).toFixed(2)
})

// 100% йде в гаманець (всі токени після комісії)
const toWalletAmount = computed(() => {
  const totalWithdraw = typeof withdraw_amount.value === 'number' ? withdraw_amount.value : parseFloat(withdraw_amount.value) || 0
  if (totalWithdraw <= 0) return 0

  // Застосовуємо комісію
  const totalAfterCommission = totalWithdraw - (totalWithdraw * commissionRate.value)

  // 100% йде в гаманець
  return +totalAfterCommission.toFixed(2)
})

// Додаємо watch для оновлення withdraw_amount при зміні available или max
watch([available, max], ([newAvailable, newMax]) => {
  withdraw_amount.value = Math.min(newMax, newAvailable)
})

// Додаємо watch на сам withdraw_amount, щоб гарантувати, що він ніколи не перевищує max
watch(withdraw_amount, (newValue) => {
  const numValue = typeof newValue === 'string' ? +newValue : newValue
  const maxValue = max.value
  if (numValue > maxValue) {
    // Проверяем, чтобы не создавать бесконечный цикл
    if (withdraw_amount.value !== maxValue) {
      withdraw_amount.value = maxValue
    }
  }
}, { immediate: false })

const { user } = useTelegram()
const ton_address = useTonAddress()

const emit = defineEmits(['close'])

const emitClose = () => {
  emit('close')
}

function getTimeUntil(date) {
  const now = new Date()
  const futureDate = new Date(new Date(date).getTime() + 24 * 60 * 60 * 1000)

  const difference = futureDate - now

  if (difference <= 0) {
    return t('modals.withdraw_modal.time_expired')
  }

  const hours = Math.floor(difference / (1000 * 60 * 60))
  const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60))

  return t('modals.withdraw_modal.hours_minutes', { h: hours, m: minutes })
}

async function withdrawTBTC() {
  const user_id = user?.id
  const receiveWallet = ton_address.value
  // Ограничиваем значение до max перед отправкой и округляем до 2 знаков
  // Убеждаемся, что значение - это число, а не строка
  const numAmount = typeof withdraw_amount.value === 'string' ? parseFloat(withdraw_amount.value) : Number(withdraw_amount.value) || 0
  const maxValue = max.value
  const tbtcToWithdraw = Math.min(numAmount, maxValue)
  // Округляем до 2 знаков после запятой
  const finalAmount = Math.round(tbtcToWithdraw * 100) / 100

  // Отладочная информация
  if (props?.claim) {
    console.log('Claim fBTC:', {
      withdraw_amount_value: withdraw_amount.value,
      withdraw_amount_type: typeof withdraw_amount.value,
      numAmount,
      maxValue,
      tbtcToWithdraw,
      finalAmount
    })
  }

  const mining = props?.claim ? true : false
  const reqData = {
    user_id: user_id,
    wallet_address: receiveWallet,
    token_amount: finalAmount,
    token_contract_address: 'EQBOqBiArR45GUlifxdzZ40ZahdVhjtU7GjY-lVtqruHvQEc',
    is_mining: mining,
  }
  try {
    await host
      .post('create-withdrawal-request/', reqData)
      .then((res) => {
        if (res.status == 200) {
          const timeText = finalAmount < (props?.claim ? app.withdraw_config?.max_auto_claim : app.withdraw_config?.max_auto_tbtc) ? t('modals.withdraw_modal.several_minutes') : t('modals.withdraw_modal.24_hours')
          emit('close', {
            status: 'success',
            title: t('notification.st_success'),
            body: props?.claim ? t('modals.withdraw_modal.claim_request_accepted', { amount: finalAmount, time: timeText }) : t('modals.withdraw_modal.withdraw_request_accepted', { amount: finalAmount, time: timeText }),
          })
        }
      })
      .catch((err) => {
        console.error(err)
        emit('close', {
          status: 'error',
          title: t('notification.st_error'),
          body:
            err.response.data.error == 'All fields are required'
              ? t('modals.withdraw_modal.check_data_correctness')
              : err.response.data.error == 'You can only make one withdrawal request per day'
                ? props?.claim ? t('modals.withdraw_modal.next_claim_available', { time: getTimeUntil(err.response.data.last_date) }) : t('modals.withdraw_modal.next_withdraw_available', { time: getTimeUntil(app.user?.last_withdrawal_date_tbtc) })
                : err.response.data.error,
        })
      })
  } catch (err) {
    emit('close', {
      status: 'error',
      title: t('notification.st_error'),
      body:
        err.response.data.error == 'All fields are required'
          ? t('modals.withdraw_modal.check_data_correctness')
          : err.response.data.error == 'You can only make one withdrawal request per day'
            ? props?.claim ? t('modals.withdraw_modal.next_claim_available', { time: getTimeUntil(err.response.data.last_date) }) : t('modals.withdraw_modal.next_withdraw_available', { time: getTimeUntil(app.user?.last_withdrawal_date_tbtc) })
            : err.response.data.error,
    })
  }
}
</script>

<template>
  <div class="modal-mask" name="modal">
    <div class="modal-wrapper">
      <div class="modal-container">
        <button class="close" @click="emit('close')">
          <Exit style="color: #fff" />
        </button>
        <div class="grouping">
          <div class="modal-header">{{ props?.claim ? t('modals.withdraw_modal.claim_fbtc') :
            t('modals.withdraw_modal.withdraw_fbtc') }}</div>
          <div class="modal-body">
            {{
              props?.claim
                ? t('modals.withdraw_modal.claim_fbtc_desc', {
                  address: ton_address?.slice(0, 5) + '...' +
                    ton_address.slice(-5)
                })
                : t('modals.withdraw_modal.withdraw_fbtc_desc', {
                  address: ton_address?.slice(0, 5) + '...' +
                    ton_address.slice(-5)
                })
            }}
          </div>
          <CustomSlider v-model="withdraw_amount" :min="min" :max="max" :available="available" />
          <div class="price">
            <div class="tbtc-price">
              <span>{{ t('modals.withdraw_modal.volume') }}</span>
              <span class="font-semibold flex gap-1">{{ typeof withdraw_amount === 'number' ? withdraw_amount.toFixed(2) : withdraw_amount }}<img class="ml-1" src="@/assets/fBTC.webp"
                  width="16px" height="16px" /></span>
            </div>
            <div class="tbtc-price">
              <span>{{ props?.claim ? t('modals.withdraw_modal.fee_for_claim') :
                t('modals.withdraw_modal.fee_for_withdraw') }}</span>
              <span class="font-semibold flex gap-1"
                :class="{ 'text-[#FCD909]': (app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive }">
                {{ totalCommission }}
                <img class="ml-1" src="@/assets/fBTC.webp" width="16px" height="16px" /> {{
                  ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt &&
                    app?.user?.has_gold_sbt_nft) || premiumActive) ? `(${premiumActive ? t('boost.king') : 'SBT'})` : "" }}
              </span>
            </div>
            <div class="tbtc-price">
              <span>{{ t('modals.withdraw_modal.to_wallet_fbtc') }}</span>
              <span class="font-semibold flex gap-1">
                {{ toWalletAmount }}
                <img class="ml-1" src="@/assets/fBTC.webp" width="16px" height="16px" />
              </span>
            </div>
            <div class="tbtc-price">
              <span>{{ t('modals.withdraw_modal.remaining_balance') }}</span>
              <span class="font-semibold flex gap-1">{{
                Math.max(0, Math.floor(+(props?.claim ? totalBalance : app?.user?.tbtc_wallet) - withdraw_amount))
              }}<img class="ml-1" src="@/assets/fBTC.webp" width="16px" height="16px" /></span>
            </div>
          </div>
          <div class="buttons-group">
            <button class="confirm" @click="withdrawTBTC">{{ t('modals.withdraw_modal.confirm') }}</button>
            <button class="cancel" @click="emitClose">{{ t('modals.withdraw_modal.cancel') }}</button>
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
      margin-top: 10px;
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
      margin-top: 1rem;
      gap: 1rem;

      .confirm {
        width: 70%;
        padding: 0.5rem;
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

      .cancel {
        width: 30%;
        padding: 0.5rem;
        color: #fff;
        border-radius: 5rem;
        box-shadow: 0 0 0 1px #fe3b59;

        &:active {
          background-color: #fe3b59;
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
  width: 100%;
  text-align: center;
  font-family: 'Inter' !important;
  font-weight: 400;
  font-size: 11px;
  color: #8b898b;
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
