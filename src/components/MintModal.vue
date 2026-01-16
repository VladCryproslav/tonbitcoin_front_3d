<script setup>
const Exit = defineAsyncComponent(() => import('@/assets/upg-modal-close.svg'))
import { useTelegram } from '@/services/telegram'
import { useAppStore } from '@/stores/app'
import { useTonAddress } from '@townsquarelabs/ui-vue'
import { computed, defineAsyncComponent, ref } from 'vue'
import { host } from '../../axios.config'
import { useI18n } from 'vue-i18n'
import CustomSlider from './CustomSlider.vue'
import { max_kw } from '@/services/data'

const app = useAppStore()
const { t } = useI18n()
const min = computed(() => app.withdraw_config?.min_kw || 300)
// available — полный баланс без ограничения max_kw
const available = computed(() => Math.max(0, Math.floor(app?.wallet_info?.kw_amount)))
// max ограничивает ход ползунка (останавливается на 20000)
const max = computed(() => Math.min(max_kw, Math.floor(app?.user?.energy)))
const amount = ref(Math.min(max.value, available.value))

const premiumActive = computed(() => new Date(app.user?.premium_sub_expires) >= new Date())

const commissionRate = computed(() => {
  const hasGold = app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft
  const hasSilver = app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft
  if (hasGold || premiumActive.value) return 0.08 // 4% + 4%
  if (hasSilver) return 0.09 // 4.5% + 4.5%
  return 0.10 // 5% + 5%
})

const individualFeeRate = computed(() => commissionRate.value / 2)

const tokensToReceive = computed(() => {
  const gross = Number(amount.value) || 0
  return +(gross * (1 - commissionRate.value)).toFixed(0)
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
    return t('modals.mint_modal.time_expired')
  }

  const hours = Math.floor(difference / (1000 * 60 * 60))
  const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60))

  return t('modals.mint_modal.hours_minutes', { hours, minutes })
}

async function claim() {
  const user_id = user?.id
  const receiveWallet = ton_address.value
  // Обновляем профиль, чтобы подтянуть актуальные флаги SBT/premium перед расчетом комиссии
  if (typeof app.fetchUserProfile === 'function') {
    try {
      await app.fetchUserProfile()
    } catch (e) {
      console.warn('fetchUserProfile failed, continue with cached data', e)
    }
  }

  const rate = commissionRate.value
  const gross = Number(amount.value) || 0
  const tokensNet = +(gross * (1 - rate)).toFixed(0)
  const reqData = {
    user_id: user_id,
    wallet_address: receiveWallet,
    token_amount: gross,
    token_contract_address: 'EQDSYiFUtMVS9rhBDhbTfP-zbj_uqa69bHv6e5IberQH5n1N',
    isMining: false,
  }
  try {
    await host
      .post('create-withdrawal-request/', reqData)
      .then(() => {
        const tokens = tokensNet
        const time = amount.value < app.withdraw_config?.max_auto_kw ? t('modals.mint_modal.few_minutes') : t('modals.mint_modal.24_hours')
        emit('close', {
          status: 'success',
          title: t('notification.st_success'),
          body: t('modals.mint_modal.request_accepted', { tokens, time }),
        })
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
            address: ton_address?.slice(0, 5) + '...' +
              ton_address.slice(-5)
          }) }}</div>
          <CustomSlider v-model="amount" :min="min" :max="max" :available="available" />
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
                :class="{ '!text-[#FCD909]': (app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive }">
                {{ (individualFeeRate * 100).toFixed(1).replace(/\.0$/, '') }}%
                <template v-if="(app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive">
                  ({{ premiumActive ? t('boost.king') : 'SBT' }})
                </template>
              </span>
            </div>
            <div class="kw-price">
              <span>{{ t('modals.mint_modal.liquidity_pool') }}</span>
              <span class="font-semibold flex gap-1"
                :class="{ '!text-[#FCD909]': (app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive }">
                {{ (individualFeeRate * 100).toFixed(1).replace(/\.0$/, '') }}%
                <template v-if="(app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive">
                  ({{ premiumActive ? t('boost.king') : 'SBT' }})
                </template>
              </span>
            </div>
            <div class="kw-price">
              <span>{{ t('modals.mint_modal.tokens_to_receive') }}</span>
              <span class="font-semibold flex gap-1">{{ tokensToReceive }}
                <img class="ml-1" src="@/assets/kW_token.png" width="16px" height="16px" />
              </span>
            </div>
            <div class="tbtc-price">
              <span>{{ t('modals.mint_modal.balance_remaining') }}</span>
              <span class="font-semibold flex gap-1">
                {{ Math.floor(+app?.user?.energy - amount) }}
                <img v-if="app.user.has_hydro_station || (app.user.has_orbital_station && !app.user.orbital_first_owner)" class="ml-1" src="@/assets/kW_token.png" width="16px"
                  height="16px" />
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
</style>
