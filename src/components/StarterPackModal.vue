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
/* This component is now unused after switching to InfoModal for Starter Pack */
</style>
