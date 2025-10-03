<script setup>
import { defineAsyncComponent } from 'vue'
import { useI18n } from 'vue-i18n'

const Exit = defineAsyncComponent(() => import('@/assets/upg-modal-close.svg'))
const { t } = useI18n()

const props = defineProps({
  saleAsic: Object,
})

const emit = defineEmits(['close'])

const confirm = () => {
  emit('close', { check: true })
}
const emitClose = () => {
  emit('close', { check: false })
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
          <div class="modal-header">
            <slot name="header">{{ t('modals.special_price_modal.title') }}</slot>
          </div>
          <div class="modal-body" v-html="t('modals.special_price_modal.mint_price_message', {
              price: props.saleAsic.price,
              discount: `<span style='color: #fea400; font-weight: bold'>${+(+props.saleAsic.price -
                +props.saleAsic.new_price).toFixed(1)}</span>`,
              percentage: `<span style='color: #fea400; font-weight: bold'>${props.saleAsic.perc}</span>`,
              name: `<span style='color: #fea400; font-weight: bold'>${props.saleAsic.name}</span>`
            })"></div>
          <div class="buttons-group">
            <button class="confirm" @click="confirm">{{ t('modals.special_price_modal.proceed') }}</button>
            <button class="cancel" @click="emitClose">{{ t('modals.special_price_modal.cancel') }}</button>
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

      .confirm {
        width: 70%;
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

      .cancel {
        width: 30%;
        padding: 0.3rem 0.5rem;
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
  text-align: center;
  font-family: 'Inter' !important;
  font-weight: 500;
  font-size: 13.5px;
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
</style>
