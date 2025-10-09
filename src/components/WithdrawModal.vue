<script setup>
const Exit = defineAsyncComponent(() => import('@/assets/upg-modal-close.svg'))
import { useTelegram } from '@/services/telegram'
import { useAppStore } from '@/stores/app'
import { useTonAddress } from '@townsquarelabs/ui-vue'
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { host } from '../../axios.config'
import { useI18n } from 'vue-i18n'
import CustomSlider from './CustomSlider.vue'

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
const max = computed(() => Math.floor(props.claim ? totalBalance.value : app?.user?.tbtc_wallet))
const available = computed(() => Math.max(0, Math.min(Math.floor(app?.wallet_info?.tbtc_amount + app?.wallet_info?.tbtc_amount_s21 + app?.wallet_info?.tbtc_amount_sx), max.value)))

// Виправляємо ініціалізацію withdraw_amount
const withdraw_amount = ref(Math.min(available.value, max.value)?.toFixed(2))

const commissionRate = computed(() => {
  return (app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 0.0085 : ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 0.007 : 0.01
})

const totalCommission = computed(() => {
  return withdraw_amount.value < 100 ? 1 : +(withdraw_amount.value * commissionRate.value).toFixed(2)
})

const isS21SX = computed(() => {
  return +((app?.wallet_info?.tbtc_amount_s21 || 0) + (app?.wallet_info?.tbtc_amount_sx || 0))
})

// Виправляємо обчислення балансів
const s1s19Balance = computed(() => {
  const totalWithdraw = withdraw_amount.value || 0
  if (totalWithdraw <= 0) return 0

  const s1s19Available = app?.wallet_info?.tbtc_amount || 0
  const s21sxAvailable = isS21SX.value

  if (s1s19Available + s21sxAvailable === 0) return 0

  // Розподіляємо вибрану суму пропорційно
  const s1s19Ratio = s1s19Available / (s1s19Available + s21sxAvailable)
  const s1s19Part = totalWithdraw * s1s19Ratio

  // Застосовуємо комісію
  const s1s19AfterCommission = s1s19Part - (s1s19Part * commissionRate.value)

  return +s1s19AfterCommission.toFixed(2)
})

const s21sxBalance = computed(() => {
  const totalWithdraw = withdraw_amount.value || 0
  if (totalWithdraw <= 0) return 0

  const s1s19Available = app?.wallet_info?.tbtc_amount || 0
  const s21sxAvailable = isS21SX.value

  if (s1s19Available + s21sxAvailable === 0) return 0

  // Розподіляємо вибрану суму пропорційно
  const s21sxRatio = s21sxAvailable / (s1s19Available + s21sxAvailable)
  const s21sxPart = totalWithdraw * s21sxRatio

  // Застосовуємо комісію
  const s21sxAfterCommission = s21sxPart - (s21sxPart * commissionRate.value)

  return +s21sxAfterCommission.toFixed(2)
})

const toWalletAmount = computed(() => {
  const totalWithdraw = withdraw_amount.value || 0
  if (totalWithdraw <= 0) return 0

  // Розподіляємо суму пропорційно до доступних балансів
  const s1s19Available = app?.wallet_info?.tbtc_amount || 0
  const s21sxAvailable = isS21SX.value

  if (s1s19Available + s21sxAvailable === 0) return 0

  // Розподіляємо вибрану суму пропорційно
  const s1s19Ratio = s1s19Available / (s1s19Available + s21sxAvailable)
  const s21sxRatio = s21sxAvailable / (s1s19Available + s21sxAvailable)

  const s1s19Part = totalWithdraw * s1s19Ratio
  const s21sxPart = totalWithdraw * s21sxRatio

  // Застосовуємо комісію
  const s1s19AfterCommission = s1s19Part - (s1s19Part * commissionRate.value)
  const s21sxAfterCommission = s21sxPart - (s21sxPart * commissionRate.value)

  // 25% від S21/SX йде в гаманець
  const s21sxToWallet = s21sxAfterCommission * 0.50

  return +((s1s19AfterCommission + s21sxToWallet)).toFixed(2)
})

const toStakingAmount = computed(() => {
  const totalWithdraw = withdraw_amount.value || 0
  if (totalWithdraw <= 0) return 0

  const s1s19Available = app?.wallet_info?.tbtc_amount || 0
  const s21sxAvailable = isS21SX.value

  if (s1s19Available + s21sxAvailable === 0) return 0

  // Розподіляємо вибрану суму пропорційно
  const s21sxRatio = s21sxAvailable / (s1s19Available + s21sxAvailable)

  const s21sxPart = totalWithdraw * s21sxRatio

  // Застосовуємо комісію
  const s21sxAfterCommission = s21sxPart - (s21sxPart * commissionRate.value)

  // 75% від S21/SX йде в стейкінг
  const s21sxToStaking = s21sxAfterCommission * 0.50

  return +s21sxToStaking.toFixed(2)
})

// Додаємо watch для оновлення withdraw_amount при зміні available
watch(available, (newAvailable) => {
  if (props?.claim) {
    withdraw_amount.value = +Math.min(newAvailable, totalBalance.value)?.toFixed(2)
  } else {
    withdraw_amount.value = +Math.min(app?.user?.tbtc_wallet, newAvailable)?.toFixed(2)
  }
})

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
  const tbtcToWithdraw = withdraw_amount.value
  const mining = props?.claim ? true : false
  const reqData = {
    user_id: user_id,
    wallet_address: receiveWallet,
    token_amount: tbtcToWithdraw,
    token_contract_address: 'EQBOqBiArR45GUlifxdzZ40ZahdVhjtU7GjY-lVtqruHvQEc',
    is_mining: mining,
  }
  try {
    await host
      .post('create-withdrawal-request/', reqData)
      .then((res) => {
        if (res.status == 200) {
          const timeText = tbtcToWithdraw < (props?.claim ? app.withdraw_config?.max_auto_claim : app.withdraw_config?.max_auto_tbtc) ? t('modals.withdraw_modal.several_minutes') : t('modals.withdraw_modal.24_hours')
          emit('close', {
            status: 'success',
            title: t('notification.st_success'),
            body: props?.claim ? t('modals.withdraw_modal.claim_request_accepted', { amount: tbtcToWithdraw, time: timeText }) : t('modals.withdraw_modal.withdraw_request_accepted', { amount: tbtcToWithdraw, time: timeText }),
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
          <CustomSlider v-model="withdraw_amount" :min="min" :max="Math.max(max, available)" :available="available"
            disabled />
          <div class="price">
            <div class="tbtc-price">
              <span>{{ t('modals.withdraw_modal.volume') }}</span>
              <span class="font-semibold flex gap-1">{{ withdraw_amount }}<img class="ml-1" src="@/assets/fBTC.webp"
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
              <span>{{ t('modals.withdraw_modal.asics_s1_s19') }}</span>
              <span class="font-semibold flex gap-1">{{ s1s19Balance }}<img class="ml-1" src="@/assets/fBTC.webp"
                  width="16px" height="16px" />
              </span>
            </div>
            <div class="tbtc-price">
              <span>{{ t('modals.withdraw_modal.asics_s21_sx') }}</span>
              <span class="font-semibold flex gap-1">{{ s21sxBalance }}<img class="ml-1" src="@/assets/fBTC.webp"
                  width="16px" height="16px" />
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
              <span>{{ t('modals.withdraw_modal.staking_amount') }}</span>
              <span class="font-semibold flex gap-1">{{ toStakingAmount }}<img class="ml-1" src="@/assets/fBTC.webp"
                  width="16px" height="16px" />
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
