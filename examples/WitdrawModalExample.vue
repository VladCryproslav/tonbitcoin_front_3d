<script setup>
const Exit = defineAsyncComponent(() => import('@/assets/upg-modal-close.svg'))
import { useTelegram } from '@/services/telegram'
import { useAppStore } from '@/stores/app'
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { host } from '../../axios.config'
import { useI18n } from 'vue-i18n'
import CustomSlider from './CustomSlider.vue'
import { SOLANA_CONTRACTS } from '@/utils/solanaContracts'
import { BLOCKCHAIN_WITHDRAWAL_ENABLED_SBTC, INAPP_WITHDRAWAL_ENABLED_SBTC } from '@/config/maintenance'

const { t } = useI18n()

const app = useAppStore()

const props = defineProps({
  claim: Boolean,
})

// Переключатель Blockchain/In-App
const withdrawalType = ref('blockchain') // 'blockchain' | 'inapp'

// Computed property для адреса кошелька
const walletAddress = computed(() => {
  return app.solanaWallet.publicKey || null
})


const totalBalance = computed(() => {
  const balance = (+app?.user?.mined_tokens_balance || 0) + (+app?.user?.mined_tokens_balance_s21 || 0) + (+app?.user?.mined_tokens_balance_sx || 0)
  return isNaN(balance) ? 0 : balance
})

const premiumActive = computed(() => new Date(app.user?.premium_sub_expires) >= new Date())

// Computed для расчета оставшегося баланса
const balanceRemaining = computed(() => {
  const withdrawAmt = +withdraw_amount.value || 0
  if (isNaN(withdrawAmt)) return 0

  if (withdrawalType.value === 'inapp') {
    const total = totalBalance.value || 0
    return Math.max(0, Math.floor(total - withdrawAmt))
  }

  // Для blockchain
  const balance = props?.claim ? totalBalance.value : (+app?.user?.tbtc_wallet || 0)
  if (isNaN(balance)) return 0
  return Math.max(0, Math.floor(balance - withdrawAmt))
})

const min = computed(() => props?.claim ? app.withdraw_config?.min_claim || 2 : app.withdraw_config?.min_tbtc || 50)

// ВАЖНО: Для In-App доступный баланс ТОЛЬКО из mined_tokens_balance
const max = computed(() => {
  if (withdrawalType.value === 'inapp') {
    // Для In-App всегда используем totalBalance (mined_tokens_balance)
    return Math.floor(totalBalance.value)
  }
  // Для blockchain логика остается прежней
  return Math.floor(props.claim ? totalBalance.value : app?.user?.tbtc_wallet)
})

const available = computed(() => {
  if (withdrawalType.value === 'inapp') {
    // Для In-App доступный баланс только из mined_tokens_balance
    return Math.max(0, Math.min(
      Math.floor(app?.wallet_info?.tbtc_amount + app?.wallet_info?.tbtc_amount_s21 + app?.wallet_info?.tbtc_amount_sx),
      max.value
    ))
  }
  // Для blockchain логика остается прежней
  return Math.max(0, Math.min(
    Math.floor(app?.wallet_info?.tbtc_amount + app?.wallet_info?.tbtc_amount_s21 + app?.wallet_info?.tbtc_amount_sx),
    max.value
  ))
})

const clampAmount = (value) => {
  const numeric = Number(value) || 0
  const minVal = Number(min.value) || 0
  const maxVal = Math.max(Number(max.value) || 0, Number(available.value) || 0)
  return Math.min(maxVal, Math.max(minVal, numeric))
}

// Стартовое значение: внутри диапазона, без toFixed в состоянии
const withdraw_amount = ref(clampAmount(Math.min(available.value || 0, max.value || 0)))

const commissionRate = computed(() => {
  if (withdrawalType.value === 'inapp') {
    return 0 // Без комиссии для In-App
  }
  // Для blockchain комиссия остается прежней
  return (app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 0.0085 : ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 0.007 : 0.01
})

const totalCommission = computed(() => {
  if (withdrawalType.value === 'inapp') {
    return 0 // Без комиссии для In-App
  }
  return withdraw_amount.value < 100 ? 1 : +(withdraw_amount.value * commissionRate.value).toFixed(2)
})

const isS21SX = computed(() => {
  return +((app?.wallet_info?.tbtc_amount_s21 || 0) + (app?.wallet_info?.tbtc_amount_sx || 0))
})

// Объединенное вычисление баланса для всех ASICs
const asicsBalance = computed(() => {
  const totalWithdraw = withdraw_amount.value || 0
  if (totalWithdraw <= 0) return 0

  const s1s19Available = app?.wallet_info?.tbtc_amount || 0
  const s21sxAvailable = isS21SX.value
  const totalAvailable = s1s19Available + s21sxAvailable

  if (totalAvailable === 0) return 0

  // Применяем комиссию ко всей сумме
  const afterCommission = totalWithdraw - (totalWithdraw * commissionRate.value)

  return +afterCommission.toFixed(2)
})

const toWalletAmount = computed(() => {
  const totalWithdraw = withdraw_amount.value || 0
  if (totalWithdraw <= 0) return 0

  // Все токены теперь идут на кошелек (100% для S21/SX вместо 25%)
  const s1s19Available = app?.wallet_info?.tbtc_amount || 0
  const s21sxAvailable = isS21SX.value

  if (s1s19Available + s21sxAvailable === 0) return 0

  // Распределяем выбранную сумму пропорционально
  const s1s19Ratio = s1s19Available / (s1s19Available + s21sxAvailable)
  const s21sxRatio = s21sxAvailable / (s1s19Available + s21sxAvailable)

  const s1s19Part = totalWithdraw * s1s19Ratio
  const s21sxPart = totalWithdraw * s21sxRatio

  // Применяем комиссию
  const s1s19AfterCommission = s1s19Part - (s1s19Part * commissionRate.value)
  const s21sxAfterCommission = s21sxPart - (s21sxPart * commissionRate.value)

  // Все токены S21/SX теперь идут на кошелек (100% вместо 25%)
  return +((s1s19AfterCommission + s21sxAfterCommission)).toFixed(2)
})

// Клайпим только если вышли из диапазона при смене доступности/лимитов/режима
watch([available, max, min, () => withdrawalType.value], () => {
  withdraw_amount.value = clampAmount(withdraw_amount.value)
})

const { user } = useTelegram()

const emit = defineEmits(['close'])

const emitClose = () => {
  emit('close')
}

// Сумма, которую пользователь фактически получит на кошелёк (с учётом комиссии)
const netWithdrawAmount = computed(() => {
  const amount = +withdraw_amount.value || 0
  if (amount <= 0) return 0

  if (withdrawalType.value === 'inapp') {
    // In-App без комиссии
    return amount
  }

  // Blockchain
  if (props?.claim) {
    // claim из майнинга: используем уже посчитанный net (учитывает комиссию и S21/SX)
    return toWalletAmount.value || 0
  }

  // Обычный вывод sBTC из In-App кошелька: amount - комиссия (min 1 при < 100)
  const commission = totalCommission.value || 0
  return Math.max(0, +(amount - commission).toFixed(8))
})

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
  // Проверка типа вывода
  if (withdrawalType.value !== 'blockchain' && withdrawalType.value !== 'inapp') {
    emit('close', {
      status: 'error',
      title: t('notification.st_error'),
      body: 'Invalid withdrawal type',
    })
    return
  }

  // Проверка доступности типа вывода для sBTC токенов
  if (withdrawalType.value === 'blockchain' && !BLOCKCHAIN_WITHDRAWAL_ENABLED_SBTC) {
    emit('close', {
      status: 'warning',
      title: 'Blockchain withdrawal unavailable',
      body: 'Blockchain withdrawal is temporarily unavailable right now. It will be back soon.',
    })
    return
  }

  if (withdrawalType.value === 'inapp' && !INAPP_WITHDRAWAL_ENABLED_SBTC) {
    emit('close', {
      status: 'warning',
      title: 'In-App transfer unavailable',
      body: 'In-App transfer is temporarily unavailable right now. It will be back soon.',
    })
    return
  }

  const user_id = user?.id
  const receiveWallet = app.solanaWallet.publicKey

  // Для blockchain требуется подключенный кошелек
  if (withdrawalType.value === 'blockchain' && !receiveWallet) {
    emit('close', {
      status: 'error',
      title: t('notification.st_error'),
      body: 'Wallet not connected. Please connect your wallet first.',
    })
    return
  }

  const tbtcToWithdraw = +withdraw_amount.value || 0 // Преобразуем строку в число
  const mining = props?.claim ? true : false
  const reqData = {
    user_id: user_id,
    wallet_address: withdrawalType.value === 'blockchain' ? receiveWallet : null, // Для In-App не нужен адрес
    token_amount: tbtcToWithdraw,
    token_contract_address: SOLANA_CONTRACTS.TBTC_TOKEN,
    is_mining: mining,
    withdrawal_type: withdrawalType.value, // 'blockchain' | 'inapp'
  }
  try {
    await host
      .post('create-withdrawal-request/', reqData)
      .then((res) => {
        if (res.status == 200) {
          const netAmount = +(+netWithdrawAmount.value || 0).toFixed(8)

          if (withdrawalType.value === 'inapp') {
            // In-App вывод: специальное сообщение (без комиссии)
            const tokenName = 'sBTC'
            emit('close', {
              status: 'success',
              title: t('notification.st_success'),
              body: `Your In-App balance has been topped up, ${netAmount} ${tokenName}. Next withdrawal will be available in 24 hours.`,
            })
          } else {
            // Blockchain вывод: показываем сумму с учётом комиссии
            const limit = props?.claim ? app.withdraw_config?.max_auto_claim : app.withdraw_config?.max_auto_tbtc
            const timeText =
              tbtcToWithdraw < limit
                ? t('modals.withdraw_modal.several_minutes')
                : t('modals.withdraw_modal.24_hours')

            emit('close', {
              status: 'success',
              title: t('notification.st_success'),
              body: props?.claim
                ? t('modals.withdraw_modal.claim_request_accepted', {
                    amount: netAmount,
                    time: timeText,
                  })
                : t('modals.withdraw_modal.withdraw_request_accepted', {
                    amount: netAmount,
                    time: timeText,
                  }),
            })
          }
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
                  address: walletAddress?.slice(0, 5) + '...' +
                    walletAddress?.slice(-5)
                })
                : t('modals.withdraw_modal.withdraw_fbtc_desc', {
                  address: walletAddress?.slice(0, 5) + '...' +
                    walletAddress?.slice(-5)
                })
            }}
          </div>

          <!-- Blockchain/In-App toggle -->
          <div class="toggle-panel">
            <div class="toggle-panel-spacer"></div>
            <div class="toggle-container">
              <button
                class="toggle-btn"
                :class="{ active: withdrawalType === 'blockchain' }"
                @click="withdrawalType = 'blockchain'"
              >
                {{ t('modals.withdraw_modal.blockchain') }}
              </button>
              <button
                class="toggle-btn"
                :class="{ active: withdrawalType === 'inapp' }"
                @click="withdrawalType = 'inapp'"
              >
                {{ t('modals.withdraw_modal.inapp') }}
              </button>
            </div>
            <div class="toggle-panel-spacer"></div>
          </div>

          <CustomSlider
            v-model="withdraw_amount"
            :min="min"
            :max="Math.max(max, available)"
            :available="available"
          />
          <div class="price">
            <div class="tbtc-price">
              <span>{{ t('modals.withdraw_modal.volume') }}</span>
              <span class="font-semibold flex gap-1">{{ withdraw_amount?.toFixed(2) }}<img class="ml-1" src="@/assets/sBTC.webp"
                  width="16px" height="16px" /></span>
            </div>
            <div class="tbtc-price">
              <span>{{ props?.claim ? t('modals.withdraw_modal.fee_for_claim') :
                t('modals.withdraw_modal.fee_for_withdraw') }}</span>
              <span class="font-semibold flex gap-1"
                :class="{ 'text-[#FCD909]': withdrawalType === 'blockchain' && ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive) }">
                {{ withdrawalType === 'inapp' ? '0' : totalCommission }}
                <img class="ml-1" src="@/assets/sBTC.webp" width="16px" height="16px" /> {{
                  withdrawalType === 'blockchain' && ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt &&
                    app?.user?.has_gold_sbt_nft) || premiumActive) ? `(${premiumActive ? t('boost.king') : 'SBT'})` : "" }}
              </span>
            </div>
            <!-- Show ASIC details only for blockchain -->
            <template v-if="withdrawalType === 'blockchain'">
              <div class="tbtc-price">
                <span>{{ t('modals.withdraw_modal.to_wallet_fbtc') }}</span>
                <span class="font-semibold flex gap-1">
                  {{ toWalletAmount }}
                  <img class="ml-1" src="@/assets/sBTC.webp" width="16px" height="16px" />
                </span>
              </div>
            </template>
            <!-- For In-App show only amount to be credited -->
            <template v-else>
              <div class="tbtc-price">
                <span>{{ t('modals.withdraw_modal.to_wallet_fbtc') }}</span>
                <span class="font-semibold flex gap-1">
                  {{ withdraw_amount?.toFixed(2) }} <!-- No fee for In-App -->
                  <img class="ml-1" src="@/assets/sBTC.webp" width="16px" height="16px" />
                </span>
              </div>
            </template>
            <div class="tbtc-price">
              <span>{{ t('modals.withdraw_modal.remaining_balance') }}</span>
              <span class="font-semibold flex gap-1">
                {{ balanceRemaining }}<img class="ml-1" src="@/assets/sBTC.webp" width="16px" height="16px" />
              </span>
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

// Стили для переключателя Blockchain/In-App
.toggle-panel {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  width: 100%;
  align-items: center;
  gap: 0.5rem;
  margin: 0.5rem 0;
  position: relative;
}

.toggle-panel-spacer {
  min-width: 0;
}

.toggle-container {
  display: flex;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 20px;
  padding: 2px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  grid-column: 2;
  justify-self: center;
  width: 100%;
  max-width: 280px;
}

.toggle-btn {
  flex: 1;
  padding: 6px 16px;
  border-radius: 18px;
  border: none;
  background: transparent;
  color: #fff;
  font-family: 'Inter' !important;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;

  &.active {
    background: linear-gradient(135deg, rgba(49, 255, 128, 0.2), rgba(49, 255, 128, 0.1));
    color: #31ff80;
    box-shadow: 0 0 10px rgba(49, 255, 128, 0.3);
  }

  &:hover:not(.active) {
    background: rgba(255, 255, 255, 0.05);
  }
}
</style>
