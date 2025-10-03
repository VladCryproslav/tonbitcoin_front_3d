<template>
  <div class="modal-mask" name="modal">
    <div class="modal-wrapper">
      <div class="modal-container">
        <button class="close" @click="emit('close')">
          <Exit style="color: #fff" />
        </button>
        <div class="grouping">
          <div class="modal-header">{{ t('modals.withdraw_staking_modal.attention') }}</div>
          <div class="modal-body">
            {{
              props?.deposit > 0
                ? t('modals.withdraw_staking_modal.confirm_withdraw_deposit', {
                  amount: +props.sum.toFixed(2), deposit:
                    props.deposit
                })
                : t('modals.withdraw_staking_modal.confirm_withdraw_balance', { amount: +props.sum.toFixed(2) })
            }}
          </div>
          <div class="buttons-group">
            <button class="confirm" @click="withdrawTBTC">{{ t('modals.withdraw_staking_modal.confirm') }}</button>
            <button class="cancel" @click="emitClose">{{ t('modals.withdraw_staking_modal.cancel') }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const Exit = defineAsyncComponent(() => import('@/assets/upg-modal-close.svg'))
import { useTelegram } from '@/services/telegram'

import { useTonAddress } from '@townsquarelabs/ui-vue'
import { defineAsyncComponent } from 'vue'
import { host } from '../../axios.config'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()



const props = defineProps({
  deposit: Number,
  sum: Number,
})

const { user } = useTelegram()
const ton_address = useTonAddress()

const emit = defineEmits(['close'])

const emitClose = () => {
  emit('close')
}

async function withdrawTBTC() {
  const user_id = user?.id
  const receiveWallet = ton_address.value
  const reqData = {
    user_id: user_id,
    wallet_address: receiveWallet,
    token_amount: 1,
    token_contract_address: 'EQBOqBiArR45GUlifxdzZ40ZahdVhjtU7GjY-lVtqruHvQEc',
    is_staking: true,
  }

  try {
    if (props.deposit == 0) {
      await host
        .post('create-withdrawal-request/', reqData)
        .then((res) => {
          if (res.status == 200) {
            emit('close', {
              status: 'success',
              title: t('notification.st_success'),
              body: t('modals.withdraw_staking_modal.withdraw_balance_request_accepted', { amount: props.sum }),
            })
          }
        })
        .catch((err) => {
          console.error(err)
          emit('close', { status: 'error', title: t('notification.st_error'), body: err.response.data.error })
        })
    } else {
      await host
        .post('earn-deposit/', { stake_id: props.deposit })
        .then((res) => {
          if (res.status == 200) {
            emit('close', {
              status: 'success',
              title: t('notification.st_success'),
              body: t('modals.withdraw_staking_modal.withdraw_deposit_request_accepted', { amount: props.sum }),
            })
          }
        })
        .catch((err) => {
          console.error(err)
          emit('close', { status: 'error', title: t('notification.st_error'), body: err.response.data.error == 'You can only make one withdrawal request per day' ? t('modals.withdraw_staking_modal.withdraw_once_per_day') : err.response.data.error })
        })
    }
  } catch (err) {
    emit('close', { status: 'error', title: t('notification.st_error'), body: err.response.data.error == 'You can only make one withdrawal request per day' ? t('modals.withdraw_staking_modal.withdraw_once_per_day') : err.response.data.error })
  }
}
</script>

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
  width: 100%;
  text-align: center;
  font-family: 'Inter' !important;
  font-weight: 500;
  font-size: 14px;
  color: #8b898b;
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
