<script setup>
import { defineAsyncComponent } from 'vue'
import { useI18n } from 'vue-i18n'

const Exit = defineAsyncComponent(() => import('@/assets/upg-modal-close.svg'))
const { t } = useI18n()

const emit = defineEmits(['close', 'buy'])

const emitClose = () => {
  emit('close', { check: false })
}

const emitBuy = () => {
  emit('buy')
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
            {{ t('asic_shop.information') }}
          </div>
          <div class="modal-body">
            <div class="starter-pack-content">
              <div class="starter-pack-title">
                {{ t('gems.starter_pack_title') }}
              </div>
              <ul class="starter-pack-list">
                <li>{{ t('gems.starter_pack_item_1') }}</li>
                <li>{{ t('gems.starter_pack_item_2') }}</li>
                <li>{{ t('gems.starter_pack_item_3') }}</li>
                <li>{{ t('gems.starter_pack_item_4') }}</li>
                <li>{{ t('gems.starter_pack_item_5') }}</li>
                <li>{{ t('gems.starter_pack_item_6') }}</li>
                <li>{{ t('gems.starter_pack_item_7') }}</li>
                <li>{{ t('gems.starter_pack_item_8') }}</li>
              </ul>
              <div class="starter-pack-price">
                <div class="price-info">
                  {{ t('gems.starter_pack_price_info') }}
                </div>
                <div class="price-offer">
                  {{ t('gems.starter_pack_price_offer') }}
                </div>
              </div>
            </div>
          </div>
          <div class="buttons-group">
            <button class="buy-btn" @click="emitBuy">{{ t('common.buy') }}</button>
            <button class="cancel" @click="emitClose">{{ t('modals.info_modal.cancel') }}</button>
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
  width: 90%;
  max-width: 400px;
  margin: 0 auto;
  background: radial-gradient(ellipse 45% 50% at top center, #ffffff1a, transparent), #08150a;
  border: 1px solid;
  border-image: linear-gradient(180deg, #FEA400 0%, #FCD909 100%) 1;
  border-radius: 1rem;
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.close {
  position: absolute;
  top: 15px;
  right: 15px;
  background: none;
  border: none;
  cursor: pointer;
  z-index: 10;
}

.grouping {
  padding: 2rem 1.5rem 1.5rem;
}

.modal-header {
  font-family: 'Inter', sans-serif;
  font-size: clamp(18px, 6dvw, 24px);
  font-weight: 700;
  color: #ffffff;
  text-align: center;
  margin-bottom: 1.5rem;
}

.modal-body {
  margin-bottom: 1.5rem;
}

.starter-pack-content {
  color: #ffffff;
}

.starter-pack-title {
  font-family: 'Inter', sans-serif;
  font-size: clamp(16px, 5dvw, 20px);
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 1rem;
  text-align: center;
}

.starter-pack-list {
  list-style: none;
  padding: 0;
  margin: 0 0 1.5rem 0;

  li {
    position: relative;
    padding-left: 1.5rem;
    margin-bottom: 0.5rem;
    font-family: 'Inter', sans-serif;
    font-size: clamp(14px, 4dvw, 16px);
    line-height: 1.4;
    color: #ffffff;

    &::before {
      content: '•';
      position: absolute;
      left: 0;
      color: #FCD909;
      font-weight: bold;
      font-size: 1.2em;
    }
  }
}

.starter-pack-price {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  padding: 1rem;
  text-align: center;
}

.price-info {
  font-family: 'Inter', sans-serif;
  font-size: clamp(12px, 3.5dvw, 14px);
  color: #cccccc;
  margin-bottom: 0.5rem;
}

.price-offer {
  font-family: 'Inter', sans-serif;
  font-size: clamp(14px, 4dvw, 16px);
  font-weight: 600;
  color: #FCD909;
}

.buttons-group {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.buy-btn {
  flex: 1;
  padding: 0.75rem 1rem;
  background: linear-gradient(180deg, #FCD909 0%, #FEA400 100%);
  border: none;
  border-radius: 0.5rem;
  font-family: 'Inter', sans-serif;
  font-size: clamp(14px, 4dvw, 16px);
  font-weight: 600;
  color: #000000;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: linear-gradient(180deg, #FEA400 0%, #FCD909 100%);
    transform: translateY(-1px);
  }

  &:active {
    transform: translateY(0);
  }
}

.cancel {
  flex: 1;
  padding: 0.75rem 1rem;
  background: transparent;
  border: 1px solid #ffffff30;
  border-radius: 0.5rem;
  font-family: 'Inter', sans-serif;
  font-size: clamp(14px, 4dvw, 16px);
  font-weight: 600;
  color: #ffffff;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    border-color: #ffffff50;
  }
}
</style>
