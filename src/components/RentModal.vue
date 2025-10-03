<template>
  <div class="modal-mask" name="modal">
    <div class="modal-wrapper">
      <div class="modal-container">
        <button class="close" @click="emitClose">
          <Exit style="color: #fff" />
        </button>
        <div class="grouping">
          <div class="modal-header">{{ t('modals.rent_modal.title') }}</div>
          <div class="modal-body" :class="{ 'left-text': side == 'in' }">
            <p v-if="props.side == 'in'">{{ t('modals.rent_modal.confirm_rent_in') }}</p>
            <p v-if="props.side == 'in'"><strong><br>{{ t('modals.rent_modal.important') }}</strong></p>
            <ul v-if="props.side == 'in'">
              <li>{{ t('modals.rent_modal.rule_1') }}</li>
              <li>{{ t('modals.rent_modal.rule_2') }}</li>
              <li>{{ t('modals.rent_modal.rule_3') }}</li>
              <li>{{ t('modals.rent_modal.rule_4') }}</li>
            </ul>
            <p v-else>{{ t('modals.rent_modal.confirm_rent_out') }}</p>
          </div>
          <div class="price">
            <div v-if="props.side == 'in'" class="tbtc-price">
              <span>{{ t('modals.rent_modal.daily_kw_consumption') }}</span>
              <span class="font-semibold flex gap-1">{{ props.kw_day || 0 }}<img class="ml-1"
                  src="@/assets/kW_token.png" width="16px" height="16px" /></span>
            </div>
            <div v-if="props.time" class="tbtc-price">
              <span>{{ t('modals.rent_modal.rental_period') }}</span>
              <span class="font-semibold flex gap-1">{{ t('common.days', { n: props.time }) }}<img class="ml-1"
                  src="@/assets/time.webp" width="16px" height="16px" />
              </span>
            </div>
            <!-- <div v-if="props.side == 'in'" class="tbtc-price">
                <span>Нужно kW за весь период:</span>
                <span class="font-semibold flex gap-1">{{ props.kw_all || 0 }}<img class="ml-1"
                    src="@/assets/kW_token.png" width="16px" height="16px" /></span>
              </div> -->
            <div v-if="props.tbtc" class="tbtc-price">
              <span>{{ props.side == 'in' ? t('modals.rent_modal.miner_income') : t('modals.rent_modal.income_period')
              }}</span>
              <span class="font-semibold flex gap-1">{{ props.tbtc }}<img class="ml-1" src="@/assets/fBTC.webp"
                  width="16px" height="16px" /></span>
            </div>
            <div v-if="props.nft && props.side == 'out'" class="tbtc-price">
              <span>{{ t('modals.rent_modal.equipment') }}</span>
              <span class="font-semibold flex gap-1">{{ props.nft }}<img class="ml-1" src="@/assets/mintable.png"
                  width="16px" height="16px" /></span>
            </div>
          </div>
          <div class="buttons-group">
            <button class="confirm" @click="confirm">{{ t('modals.rent_modal.confirm') }}</button>
            <button class="cancel" @click="emitClose">{{ t('modals.rent_modal.cancel') }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const Exit = defineAsyncComponent(() => import('@/assets/upg-modal-close.svg'))
import { useAppStore } from '@/stores/app'
import { defineAsyncComponent } from 'vue'
import { host } from '../../axios.config'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const app = useAppStore()

const props = defineProps({
  side: String,
  kw_day: String,
  kw_all: String,
  tbtc: String,
  nft: String,
  time: String,
  nft_address: String,
  profit_per: Number,
  id: Number
})

const emit = defineEmits(['close'])

const emitClose = () => {
  emit('close')
}

async function confirm() {
  if (props.side == 'in') {
    try {
      const res = await host.post('rent-nft/', { "rental_id": props.id })
      if (res.status == 200) {
        await app.initUser()
        emit('close', { status: 'success', title: t('modals.rent_modal.success'), body: t('modals.rent_modal.rental_request_accepted', { nft: props.nft }) })
      }
    } catch (err) {
      console.log(err)
      err.response.data.error.includes("NFT")
        ? emit('close')
        : emit('close', {
          status: 'error',
          title: t('modals.rent_modal.error'),
          body: t('modals.rent_modal.insufficient_funds'),
        })
    }
  }
  if (props.side == 'out') {
    const params =
    {
      "nft": props.nft_address,
      "rental_days": props.time,
      "owner_percentage": props.profit_per
    }
    try {
      const res = await host.post('nft-rental/', params)
      if (res.status == 200) {
        await app.initUser()
        emit('close', { status: 'success', title: t('modals.rent_modal.success'), body: t('modals.rent_modal.asic_successfully_placed') })
      }
    } catch (err) {
      console.log(err)
      err.response.data.error.includes("NFT")
        ? emit('close')
        : emit('close', {
          status: 'error',
          title: t('modals.rent_modal.error'),
          body: t('modals.rent_modal.insufficient_funds'),
        })
    }
  }
}
</script>

<style lang="scss" scoped>
.modal-mask {
  position: fixed;
  z-index: 999;
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
        font-weight: 400;
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
  font-weight: 700;
  font-size: 18px;
  line-height: 1.3;
  font-family: 'Inter' !important;
}

.modal-body {
  white-space: pre-wrap;
  width: 100%;
  text-align: center;
  font-family: 'Inter' !important;
  font-weight: 500;
  letter-spacing: -0.5px;
  font-size: 12px;
  color: #8b898b;
  margin: 0 0 10px;

  ul {
    list-style: disc;
    list-style-position: inside;
  }

  &.left-text {
    text-align: left;
  }
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
