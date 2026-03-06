<script setup>
const Exit = defineAsyncComponent(() => import('@/assets/upg-modal-close.svg'))
import { useTelegram } from '@/services/telegram'
import { useAppStore } from '@/stores/app'
import { computed, defineAsyncComponent, ref } from 'vue'
import { host } from '../../axios.config'
import { useI18n } from 'vue-i18n'
import CustomSlider from './CustomSlider.vue'
import { SOLANA_CONTRACTS } from '@/utils/solanaContracts'
import { BLOCKCHAIN_WITHDRAWAL_ENABLED_KW, INAPP_WITHDRAWAL_ENABLED_KW, BLOCKCHAIN_WITHDRAWAL_KW_BOILER_DISABLED } from '@/config/maintenance'

const app = useAppStore()
const { t } = useI18n()

// Blockchain/In-App toggle
const withdrawalType = ref('blockchain') // 'blockchain' | 'inapp'

const min = computed(() => app.withdraw_config?.min_kw || 300)
const max = computed(() => Math.floor(app?.user?.energy || 0))
const available = computed(() => Math.max(0, Math.min(Math.floor(app?.wallet_info?.kw_amount || 0), max.value)))
const amount = ref(Math.min(available.value || 0, max.value || 0) || 0)

const isBoilerHouse = computed(() => (app.user?.station_type || 'Boiler house') === 'Boiler house')

// Computed для расчета количества токенов к получению
const tokensToReceive = computed(() => {
  const amt = amount.value || 0
  if (!amt || isNaN(amt)) return 0

  if (withdrawalType.value === 'inapp') {
    return Math.floor(amt * 0.9)
  }

  // Blockchain: -20% комиссия (или с учетом SBT/Premium)
  const multiplier = (app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 0.82 :
                     ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 0.84 : 0.8
  return Math.floor(amt * multiplier)
})

// Computed для расчета оставшегося баланса
const balanceRemaining = computed(() => {
  const energy = +app?.user?.energy || 0
  const amt = +amount.value || 0
  if (isNaN(energy) || isNaN(amt)) return 0
  return Math.max(0, Math.floor(energy - amt))
})

// Computed property для адреса кошелька
const walletAddress = computed(() => {
  return app.user?.ton_wallet || app.solanaWallet.publicKey || null
})

const { user } = useTelegram()

const premiumActive = computed(() => new Date(app.user?.premium_sub_expires) >= new Date())

const emit = defineEmits(['close'])
const emitClose = () => {
  emit('close')
}

const handleWithdrawalTypeClick = (type) => {
  if (type === 'blockchain' && BLOCKCHAIN_WITHDRAWAL_KW_BOILER_DISABLED && isBoilerHouse.value) {
    emit('close', {
      status: 'warning',
      title: 'Attention',
      body: 'kW token withdrawal to blockchain will be available after upgrading your power plant to Coal Power Plant.',
    })
    return
  }

  withdrawalType.value = type
}

function getTimeUntil(date) {
  const now = new Date()
  const futureDate = new Date(new Date(date).getTime() + 24 * 60 * 60 * 1000)

  const difference = futureDate - now

  if (difference <= 0) {
    return t('modals.mint_modal.time_expired')
  }

  const hours = Math.floor(difference / (1000 * 60 * 60))
  const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60))

  return t('modals.mint_modal.hours_minutes', { hours, minutes })
}

async function claim() {
  // Проверка типа вывода
  if (withdrawalType.value !== 'blockchain' && withdrawalType.value !== 'inapp') {
    emit('close', {
      status: 'error',
      title: t('notification.st_error'),
      body: 'Invalid withdrawal type',
    })
    return
  }

  // Ограничение вывода kW на блокчейн для Boiler house (уровень 1 электростанции)
  if (withdrawalType.value === 'blockchain' && BLOCKCHAIN_WITHDRAWAL_KW_BOILER_DISABLED && (app.user?.station_type || 'Boiler house') === 'Boiler house') {
    emit('close', {
      status: 'warning',
      title: 'Attention',
      body: 'kW token withdrawal to blockchain will be available after upgrading your power plant to Coal Power Plant.',
    })
    return
  }

  // Проверка доступности типа вывода для kW токенов
  if (withdrawalType.value === 'blockchain' && !BLOCKCHAIN_WITHDRAWAL_ENABLED_KW) {
    emit('close', {
      status: 'warning',
      title: 'Blockchain withdrawal unavailable',
      body: 'Blockchain withdrawal is temporarily unavailable right now. It will be back soon.',
    })
    return
  }

  if (withdrawalType.value === 'inapp' && !INAPP_WITHDRAWAL_ENABLED_KW) {
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

  const reqData = {
    user_id: user_id,
    wallet_address: withdrawalType.value === 'blockchain' ? receiveWallet : null, // In-App doesn't need address
    token_amount: +amount.value,
    token_contract_address: SOLANA_CONTRACTS.KW_TOKEN,
    isMining: false,
    withdrawal_type: withdrawalType.value, // 'blockchain' | 'inapp'
  }
  try {
    await host
      .post('create-withdrawal-request/', reqData)
      .then(() => {
        if (withdrawalType.value === 'inapp') {
          // In-App withdrawal: special message
          const tokens = Math.floor(amount.value * 0.9)  // -10% for In-App
          emit('close', {
            status: 'success',
            title: t('notification.st_success'),
            body: `Your In-App balance has been topped up, ${tokens} kW. Next withdrawal will be available in 24 hours.`,
          })
        } else {
          // Blockchain вывод: существующее сообщение
          const tokens = Math.floor(amount.value * ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 0.82 :
                                      ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 0.84 : 0.8))  // -20% для blockchain
          const time = amount.value < app.withdraw_config?.max_auto_kw ? t('modals.mint_modal.few_minutes') : t('modals.mint_modal.24_hours')
          emit('close', {
            status: 'success',
            title: t('notification.st_success'),
            body: t('modals.mint_modal.request_accepted', { tokens, time }),
          })
        }
      })
      .catch((e) => {
        let body
        if (e.response.data.error == 'All fields are required') {
          body = t('modals.mint_modal.check_data')
        } else if (e.response.data.error == 'You can only make one withdrawal request per day') {
          body = t('modals.mint_modal.next_mint_available', { time: getTimeUntil(app.user?.last_withdrawal_date) })
        } else {
          body = e.response.data.error
        }
        emit('close', {
          status: 'error',
          title: t('notification.st_error'),
          body,
        })
      })
  } catch (e) {
    let body
    if (e.response.data.error == 'All fields are required') {
      body = t('modals.mint_modal.check_data')
    } else if (e.response.data.error == 'You can only make one withdrawal request per day') {
      body = t('modals.mint_modal.next_mint_available', { time: getTimeUntil(app.user?.last_withdrawal_date) })
    } else {
      body = e.response.data.error
    }
    emit('close', {
      status: 'error',
      title: t('notification.st_error'),
      body,
    })
  }
}

</script>

<template>
  <div class="modal-mask" name="modal">
    <div class="modal-wrapper">
      <div class="modal-container">
        <button class="close" @click="emitClose">
          <Exit style="color: #fff" />
        </button>
        <div class="grouping">
          <div class="modal-header">{{ t('modals.mint_modal.title') }}</div>
          <div class="modal-body">{{ t('modals.mint_modal.description', {
            address: walletAddress?.slice(0, 5) + '...' +
              walletAddress?.slice(-5)
          }) }}          </div>

          <!-- Blockchain/In-App toggle -->
          <div class="toggle-panel">
            <div class="toggle-panel-spacer"></div>
            <div class="toggle-container">
              <button
                class="toggle-btn"
                :class="{ active: withdrawalType === 'blockchain' }"
                @click="handleWithdrawalTypeClick('blockchain')"
              >
                {{ t('modals.mint_modal.blockchain') }}
              </button>
              <button
                class="toggle-btn"
                :class="{ active: withdrawalType === 'inapp' }"
                @click="handleWithdrawalTypeClick('inapp')"
              >
                {{ t('modals.mint_modal.inapp') }}
              </button>
            </div>
            <div class="toggle-panel-spacer"></div>
          </div>

          <CustomSlider v-model="amount" :min="min" :max="Math.max(max, available)" :available="available" />
          <!-- <VueSlider v-model="amount" :height="8" :dotSize="25" :dotStyle="{ boxShadow: 'none' }" :width="'100%'"
            :min="min" :max="max" :tooltip="'none'" :enableCross="false"
            :processStyle="{ backgroundColor: '#31FF80' }" :intervalStyle="[{ backgroundColor: '#6c6c6c' }]"
            :railStyle="{ backgroundColor: '#502024' }" /> -->
          <div class="price">
            <div class="kw-price">
              <span>{{ t('modals.mint_modal.volume') }}</span>
              <span class="font-semibold flex gap-1">
                {{ amount?.toFixed(2) }}
                <img v-if="app.user.has_hydro_station || (app.user.has_orbital_station && !app.user.orbital_first_owner)" class="ml-1"
                  src="@/assets/kW_token.png" width="16px" height="16px" />
                <img v-else class="ml-1" src="@/assets/kW.png" width="16px" height="16px" />
              </span>
            </div>
            <div class="kw-price">
              <span>{{ t('modals.mint_modal.mint_fee') }}</span>
              <span class="font-semibold flex gap-1"
                :class="{ '!text-[#FCD909]': withdrawalType === 'blockchain' && ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive) }">{{
                  withdrawalType === 'inapp' ? '10%' :
                  (app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? '9% (SBT)' :
                  ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive) ? `8% (${premiumActive ? t('boost.king') : 'SBT'})` :
                  '10%' }}</span>
            </div>
            <div class="kw-price">
              <span>{{ t('modals.mint_modal.liquidity_pool') }}</span>
              <span class="font-semibold flex gap-1"
                :class="{ '!text-[#FCD909]': withdrawalType === 'blockchain' && ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive) }">{{
                  withdrawalType === 'inapp' ? '0%' :
                  (app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? '9% (SBT)' :
                  ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive) ? `8% (${premiumActive ? t('boost.king') : 'SBT'})` :
                  '10%' }}</span>
            </div>
            <div class="kw-price">
              <span>{{ t('modals.mint_modal.tokens_to_receive') }}</span>
              <span class="font-semibold flex gap-1">{{ tokensToReceive }}<img class="ml-1" src="@/assets/kW_token.png" width="16px" height="16px" /></span>
            </div>
            <div class="tbtc-price">
              <span>{{ t('modals.mint_modal.balance_remaining') }}</span>
              <span class="font-semibold flex gap-1">
                {{ balanceRemaining }}
                <img v-if="app.user.has_hydro_station || (app.user.has_orbital_station && !app.user.orbital_first_owner)" class="ml-1" src="@/assets/kW_token.png" width="16px" height="16px" />
                <img v-else class="ml-1" src="@/assets/kW.png" width="16px" height="16px" />
              </span>
            </div>
          </div>
          <div class="buttons-group">
            <button class="confirm" @click="claim">{{ t('modals.mint_modal.confirm') }}</button>
            <button class="cancel" @click="emitClose">{{ t('modals.mint_modal.cancel') }}</button>
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
    position: relative;
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
      margin-top: 1rem;
      gap: 1rem;

      .confirm {
        width: 60%;
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
        width: 40%;
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
