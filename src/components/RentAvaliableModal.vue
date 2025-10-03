<script setup>
const Exit = defineAsyncComponent(() => import('@/assets/exit.svg'))
const Mining = defineAsyncComponent(() => import('@/assets/mining_tbtc.svg'))
const RentPerc = defineAsyncComponent(() => import('@/assets/rent_perc.svg'))
const Timer = defineAsyncComponent(() => import('@/assets/timer.svg'))
import { useAppStore } from '@/stores/app'
import { computed, defineAsyncComponent, ref } from 'vue'
import asicsSheet from '@/services/data'
import { getAsicData } from '@/utils/asics'
import { useI18n } from 'vue-i18n'

const app = useAppStore()
const { t } = useI18n()
const all_asics = computed(() => app.getAsicsFromStorage())

defineOptions({
  inheritAttrs: false
})

const emit = defineEmits(['close'])

const emitClose = () => {
  emit('close')
}

const props = defineProps({
  rentAsic: Object,
})


const availableAsics = computed(() => {
  return app?.nfts?.filter(nft =>
    !app?.rentOutNfts?.some(rented => rented?.nft === nft?.address) &&
    !nft?.metadata?.name?.match(/SBT|21|SX|Maxx/)
  ) || [];
})

const rentScrollContainer = ref(null)

const imagePathAsics = (asic) => {
  const com = computed(
    () => new URL(`../assets/asics/${asic?.toString().toUpperCase()}.webp`, import.meta.url).href,
  )
  return com
}
</script>

<template>
  <div class="available-asic">
    <div class="top-panel">
      <h1>{{ t('modals.rent_available_modal.title') }}</h1>
      <button class="close" @click="emitClose">
        <Exit style="color: #fff" />
      </button>
    </div>
    <div class="asic-list" ref="rentScrollContainer">
      <div class="asic-list-item" v-for="(item, index) in availableAsics" :key="index">
        <div class="asic-list-item-image">
          <img :src="imagePathAsics(getAsicData(item.address, all_asics, asicsSheet, 'name'))?.value" width="80px" />
        </div>
        <div class="asic-list-item-data">
          <h1>{{ item?.metadata?.name?.toUpperCase() }}</h1>
          <label>
            <Mining width="14px" />{{ getAsicData(item.address, all_asics, asicsSheet, 'speed') }}<span>
              {{ t('modals.rent_available_modal.fbtc_per_day') }}</span>
          </label>
          <label>
            <RentPerc width="14px" />{{ t('modals.rent_available_modal.from') }} {{ app?.rental_config?.min_percentage
            }} {{
              t('modals.rent_available_modal.to') }} {{
              app?.rental_config?.max_percentage }}<span>{{ t('modals.rent_available_modal.percent') }}</span>
          </label>
          <label>
            <Timer width="14px" />{{ t('modals.rent_available_modal.from') }} {{ app?.rental_config?.min_days }} {{
              t('modals.rent_available_modal.to') }} {{ app?.rental_config?.max_days
            }}<span>{{ t('modals.rent_available_modal.days') }}</span>
          </label>
        </div>
        <button class="asic-list-item-btn" :class="{ selected: props.rentAsic?.address == item?.address }"
          @click="emit('close', { asic: (props.rentAsic?.address == item?.address ? {} : item) })">{{
            props.rentAsic?.address == item.address ? t('modals.rent_available_modal.remove') :
              t('modals.rent_available_modal.add')
          }}</button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.available-asic {
  position: fixed;
  bottom: 0;
  z-index: 101;
  width: 100%;
  height: calc(100vh - 140px);
  display: flex;
  padding-top: 10px;
  flex-direction: column;
  align-items: center;
  border-radius: 1rem 1rem 0 0;
  background: #000000d9;
  backdrop-filter: blur(5px);
  border-top: 1px solid #ffffff50;

  .top-panel {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 90%;
    padding: 0.7rem 0 1rem;

    h1 {
      color: #fff;
      font-family: 'Inter' !important;
      font-weight: 600;
      font-size: 24px;
    }

    .close {
      position: absolute;
      right: 5px;
    }
  }

  .history-filters {
    display: flex;
    justify-content: center;
    gap: 10%;
    align-items: center;
    padding: 0;

    .sort-pill {
      padding: 0.3rem 0.2rem 0.2rem 0rem;
      display: flex;
      justify-content: center;
      align-items: center;
      border-radius: 1rem;
      font-family: 'Inter' !important;
      font-weight: 400;
      font-size: 12px;
      color: #fff;
      min-width: 20vw;
      border: 1px solid #ffffff25;

      &.selected {
        border: 1px solid #ffffff;
      }
    }
  }

  .asic-list {
    display: flex;
    flex-direction: column;
    width: 90%;
    border-radius: 1rem;
    border-top: 1px solid #ffffff50;
    justify-content: start;
    align-items: center;
    gap: 0.7rem;
    padding-bottom: 130px;
    margin-top: 1rem;
    overflow-y: scroll;
    -ms-overflow-style: none;
    /* Internet Explorer 10+ */
    scrollbar-width: none;
    /* Firefox */

    &::-webkit-scrollbar {
      display: none;
      /* Safari and Chrome */
    }

    &-item {
      width: 100%;
      border-radius: 1rem;
      border: 1px solid #ffffff50;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: .5rem 1rem .5rem .7rem;
      background-color: #08150a80;

      .asic-list-item-image {
        // width: 20%;
      }

      .asic-list-item-data {
        display: flex;
        flex-direction: column;
        width: 50%;
        align-items: start;
        justify-content: center;

        h1 {
          font-family: 'Inter';
          font-size: 15px;
          font-weight: 700;
          letter-spacing: 0%;
          color: #fff;
        }

        label {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 5px;
          font-family: 'Inter';
          font-size: 12px;
          font-weight: 400;
          letter-spacing: 0%;
          line-height: 0px;
          color: #ffffff80;

          span {
            font-weight: 500;
            color: #ffffff99;
          }
        }
      }

      .asic-list-item-btn {
        color: #212121;
        font-family: 'Inter';
        font-size: 15px;
        font-weight: 700;
        letter-spacing: 0%;
        background: radial-gradient(ellipse 60% 30% at bottom center, #ffffff50, transparent),
          linear-gradient(to bottom, #B28FF8, #8143FC);
        padding: .7rem 1rem;
        border-radius: .5rem;

        &.selected {
          background: radial-gradient(ellipse 60% 30% at bottom center, #ffffff50, transparent),
            linear-gradient(to bottom, #fcd909, #fea400);
          ;
        }

        &:active {
          opacity: 0.5;
          scale: 0.95;
        }
      }
    }
  }
}
</style>
