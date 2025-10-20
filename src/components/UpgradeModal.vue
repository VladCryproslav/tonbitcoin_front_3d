<script setup>
const Exit = defineAsyncComponent(() => import('@/assets/upg-modal-close.svg'))

import { useAppStore } from '@/stores/app'
import { defineAsyncComponent, ref } from 'vue'
import { host } from '../../axios.config'
import ModalNew from './ModalNew.vue'
import { useTelegram } from '@/services/telegram'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  title: String,
  body: String,
  price: Object,
  kind: String,
  stationType: String, // Добавляем prop для типа станции
})

const app = useAppStore()

const { tg } = useTelegram()

const modalStatus = ref(null)
const modalTitle = ref(null)
const modalBody = ref(null)
const openModal = ref(false)

const confirm = () => {
  switch (props.kind) {
    case 'station':
      upgradeStation()
      break
    case 'repair':
      repairStation()
      break
    case 'engineer':
      upgrade('engineer')
      break
  }
}

async function upgradeStation() {
  try {
    // Обновляем данные пользователя перед запросом, чтобы получить актуальный баланс
    await app.initUser()

    // Бэкенд сам определяет следующую станцию через get_next_station_type()
    // Не передаем station_type, так как бэкенд его не использует
    const res = await host.post('upgrade-station/', {})
    if (res.status == 200) {
      await app.initUser()
      emit('close', { status: 'success', title: t('notification.st_success'), body: t('modals.upgrade_modal.station_upgraded') })
    }
  } catch (err) {
    console.log('Upgrade station error:', err)
    emit('close', {
      status: 'error',
      title: t('notification.st_error'),
      body: t('notification.insufficient_funds'),
    })
  }
}

async function repairStation() {
  try {
    const res = await host.post('repair-station/')
    if (res.status == 200) {
      emit('close', {
        status: 'success',
        title: t('notification.st_success'),
        body: t('modals.upgrade_modal.station_repaired'),
      })
    }
  } catch (err) {
    console.log(err)
    emit('close', {
      status: 'error',
      title: t('notification.st_error'),
      body: t('notification.insufficient_funds'),
    })
  }
}

async function upgrade(params, eng_side) {
  try {
    if (eng_side) {
      const res = await host.post(`upgrade-${params}/`)
      if (res.status == 200) {
        await app.initUser()
        switch (params) {
          case 'engineer':
            emit('close', {
              status: 'success',
              title: t('notification.st_success'),
              body: t('modals.upgrade_modal.engineer_hired'),
            })
            break
        }
      }
    } else {
      const invoiceLink = await host.post(`stars-engineer/`)
      if (invoiceLink.status == 200) {
        tg.openInvoice(invoiceLink.data?.link, (status) => {
          if (status == 'cancelled' || status == 'failed') {
            emit('close')
          }
          if (status == 'paid') {
            app.initUser()
            emit('close', {
              status: 'success',
              title: t('notification.st_success'),
              body: t('modals.upgrade_modal.engineer_hired'),
            })
          }
        })
      }
    }
  } catch (err) {
    console.log(err)
    emit('close', {
      status: 'error',
      title: t('notification.st_error'),
      body: t('notification.insufficient_funds'),
    })
  }
}

const emit = defineEmits(['close'])

const emitClose = () => {
  emit('close')
}
</script>

<template>
  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
  <div class="modal-mask" name="modal">
    <div class="modal-wrapper">
      <div class="modal-container">
        <button class="close" @click="emit('close')">
          <Exit style="color: #fff" />
        </button>
        <div class="grouping">
          <div class="modal-header">
            <slot name="header">{{ props.title }}</slot>
          </div>
          <div v-if="props.body" class="modal-body">
            <slot name="body"> {{ props.body }} </slot>
          </div>
          <div class="price">
            <div v-if="props.price.kw && props.kind !== 'engineer'" class="kw-price">
              <span v-if="props.kind == 'engineer'">{{ app.user?.engineer_level >= 49 ?
                t('modals.upgrade_modal.cost_in_stars') : t('modals.upgrade_modal.cost_in_kw') }}</span>
              <span v-if="props.kind !== 'engineer'">{{ t('modals.upgrade_modal.cost_in_kw') }}</span>
              <span class="font-semibold flex justify-center items-center gap-1">
                {{ +(+props?.price?.kw).toFixed(6) }}
                <img v-if="props.kind !== 'engineer'" class="ml-1" src="@/assets/kW.png" width="16px" height="16px" />
                <img v-if="props.kind == 'engineer' && app.user?.engineer_level < 49" class="ml-1" src="@/assets/kW.png"
                  width="16px" height="16px" />
                <img v-if="props.kind == 'engineer' && app.user?.engineer_level >= 49" class="ml-1"
                  src="@/assets/stars.png" width="14px" height="14px" />
              </span>
            </div>
            <div v-if="props.price.tbtc && props.kind !== 'engineer'" class="tbtc-price">
              <span>{{ t('modals.upgrade_modal.cost_in_tbtc') }}</span>
              <span class="font-semibold flex gap-1">{{ +(+props?.price?.tbtc).toFixed(6)
                }}<img class="ml-1" src="@/assets/fBTC.webp" width="16px" height="16px" /></span>
            </div>
            <div v-if="props.kind == 'engineer'" class="eng-container">
              <div class="energy-side" :class="{ disabled: !props.price.kw }">
                <img src="@/assets/kW.png" width="16px" height="16px" />
                <span>{{ props?.price?.kw }}</span>
              </div>
              <div class="stars-side" :class="{ disabled: !props.price.stars }">
                <img src="@/assets/stars.png" width="16px" height="16px" />
                <span>{{ props?.price?.stars }}</span>
              </div>
            </div>
          </div>
          <div class="buttons-group">
            <button v-if="props.kind !== 'engineer'" class="confirm" @click="confirm">{{
              t('modals.upgrade_modal.confirm') }}</button>
            <button v-if="props.kind !== 'engineer'" class="cancel" @click="emitClose">{{
              t('modals.upgrade_modal.cancel') }}</button>
            <button v-if="props.kind == 'engineer'" class="eng-energy" :class="{ disabled: !props.price.kw }"
              @click="upgrade('engineer', 1)" :disabled="!props.price.kw">kW</button>
            <button v-if="props.kind == 'engineer'" class="eng-stars" :class="{ disabled: !props.price.stars }"
              @click="upgrade('engineer')" :disabled="!props.price.stars">Stars</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
$bar-height: 8px;

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

      .eng-container {
        width: 100%;
        display: flex;
        align-items: center;

        .energy-side,
        .stars-side {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #fff;
          font-size: 16px;
          font-weight: 600;
          gap: 0.2rem;

          &.disabled {
            filter: grayscale(1);
          }
        }
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

        &.disabled {
          filter: grayscale(1);
        }
      }

      .eng-energy {
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

        &.disabled {
          filter: grayscale(1);
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

        &.disabled {
          filter: grayscale(1);
        }
      }

      .eng-stars {
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

        &.disabled {
          filter: grayscale(1);
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
  font-weight: 400;
  font-size: 11px;
  color: #8b898b;
  margin: 0 0 10px;
  width: 100%;
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

.progress-bar {
  width: 90%;
  margin: 0 auto;
  height: $bar-height;
  border-radius: 3px;
  background: linear-gradient(#6fa6d66c, #7db1df54);

  .inner-bar {
    height: 100%;
    border-radius: 3px;
    background: #fff;
    animation: progressAnimation 2s linear forwards;
  }
}

@keyframes progressAnimation {
  from {
    width: 0;
  }

  to {
    width: 100%;
  }
}
</style>
