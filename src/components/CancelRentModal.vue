<template>
  <div class="modal-mask" name="modal">
    <div class="modal-wrapper">
      <div class="modal-container">
        <button class="close" @click="emitClose">
          <Exit style="color: #fff" />
        </button>
        <div class="grouping">
          <div class="modal-header">{{ t('modals.cancel_rent.title') }}</div>
          <div class="modal-body">
            <p v-if="props.item?.end_date == null">{{ t('modals.cancel_rent.message_delete') }}</p>
            <p v-else>{{ t('modals.cancel_rent.message_cancel') }}</p>
          </div>
          <div class="buttons-group">
            <button class="confirm" @click="confirm">{{ t('modals.cancel_rent.confirm') }}</button>
            <button class="cancel" @click="emitClose">{{ t('modals.cancel_rent.cancel') }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const Exit = defineAsyncComponent(() => import('@/assets/upg-modal-close.svg'))
import { useAppStore } from '@/stores/app'
import { computed, defineAsyncComponent } from 'vue'
import { host } from '../../axios.config'
import { useI18n } from 'vue-i18n'

const app = useAppStore()
const { t } = useI18n()
const all_asics = computed(() => app.getAsicsFromStorage())

const props = defineProps({
  item: Object
})

const emit = defineEmits(['close'])

const emitClose = () => {
  emit('close')
}

async function confirm() {
  try {
    if (props.item?.end_date == null && app?.rentOutNfts.some(el => el?.nft == props.item?.nft)) {
      await host.post('cancel-nft-rental/', { 'rental_id': props.item?.id }).then((res) => {
        if (res.status == 200) {
          emit('close', { status: 'success', title: t('notification.st_success'), body: t('modals.cancel_rent.rental_cancelled', { asic: all_asics.value?.find(el => el.a == props.item?.nft)?.n?.toUpperCase() }) })
        }
      }).catch(err => { console.log(err) })
    }
    if (new Date(props.item?.end_date) <= new Date() && app?.rentOutNfts.some(el => el?.nft == props.item?.nft)) {
      await host.post('return-nft-rental/', { 'rental_id': props.item?.id }).then((res) => {
        if (res.status == 200) {
          emit('close', { status: 'success', title: t('notification.st_success'), body: t('modals.cancel_rent.rental_cancelled', { asic: all_asics.value?.find(el => el.a == props.item?.nft)?.n?.toUpperCase() }) })
        }
      }).catch(err => {
        console.log(err)
        emit('close', {
          status: 'error',
          title: t('notification.st_error'),
          body: t('notification.was_error'),
        })
      })
    }
  } catch (err) {
    console.log(err)
    emit('close', {
      status: 'error',
      title: t('notification.st_error'),
      body: t('notification.was_error'),
    })
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
