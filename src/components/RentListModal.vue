<script setup>
const UpTrend = defineAsyncComponent(() => import('@/assets/up-trend.svg'))
const DownTrend = defineAsyncComponent(() => import('@/assets/down-trend.svg'))
const Exit = defineAsyncComponent(() => import('@/assets/exit.svg'))
import { useAppStore } from '@/stores/app'
import { useTonAddress } from '@townsquarelabs/ui-vue'
import { computed, defineAsyncComponent, ref } from 'vue'
import ModalNew from './ModalNew.vue'
import WithdrawRentModal from './WithdrawRentModal.vue'
import asicsSheet from '@/services/data'
import CancelRentModal from './CancelRentModal.vue'
import { getAsicData } from '@/utils/asics'
import { useI18n } from 'vue-i18n'

const app = useAppStore()
const all_asics = computed(() => app.getAsicsFromStorage())
const { t } = useI18n()
const emit = defineEmits(['close'])

const ton_address = useTonAddress()

const emitClose = () => {
  emit('close')
}

const withdraw_sum = ref(null)
const cancelItem = ref(null)
const openWithdraw = ref(false)
const openCancelRent = ref(false)

const openModal = ref(false)
const modalBody = ref('')
const modalTitle = ref('')
const modalStatus = ref('')

const imagePathAsics = (asic) => {
  const com = computed(
    () => new URL(`../assets/asics/${asic?.toString().toUpperCase()}.webp`, import.meta.url).href,
  )
  return com
}

function getDaysUntilDate(isoDate) {
  const targetDate = new Date(isoDate);
  const today = new Date();
  today.setHours(0, 0, 0, 0); // Скидаємо час для коректного порівняння

  // Якщо дата вже пройшла, повертаємо 0
  if (targetDate < today) {
    return `0 ${t('modals.rent_list_modal.days_many')}`;
  }

  // Різниця в мілісекундах
  const diffTime = targetDate - today;
  // Конвертуємо в дні
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

  // Логіка відмінювання
  let word;
  const lastDigit = diffDays % 10;
  const lastTwoDigits = diffDays % 100;

  if (lastTwoDigits >= 11 && lastTwoDigits <= 19) {
    word = t('modals.rent_list_modal.days_many');
  } else if (lastDigit === 1) {
    word = t('modals.rent_list_modal.day');
  } else if (lastDigit >= 2 && lastDigit <= 4) {
    word = t('modals.rent_list_modal.days_few');
  } else {
    word = t('modals.rent_list_modal.days_many');
  }

  return { days: diffDays, days_word: `${diffDays} ${word}` };
}

const showModal = (status, title, body) => {
  modalStatus.value = status
  modalTitle.value = title
  modalBody.value = body
  openModal.value = true
}

async function withdraw(sum) {
  if (!ton_address.value) {
    showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }
  if (sum < app?.withdraw_config?.min_staking_out) {

    showModal(
      'warning', t('notification.st_attention'), t('notification.min_withdraw_fbtc', { min: app?.withdraw_config?.min_rent })
    )
    return
  }

  withdraw_sum.value = sum
  openWithdraw.value = true
}

async function cancelRent(item) {
  if (item?.end_date && new Date(item?.end_date) > new Date()) {
    return
  }
  cancelItem.value = item
  openCancelRent.value = true
}

const responseWithdraw = (val) => {
  openWithdraw.value = false
  if (val) {
    showModal(val?.status, val?.title, val?.body)
  }
}

const responseCancelRent = (val) => {
  openCancelRent.value = false
  if (val) {
    showModal(val?.status, val?.title, val?.body)
  }
}
</script>

<template>
  <div class="rent-percentage">
    <div class="top-panel">
      <h1>{{ t('modals.rent_list_modal.title') }}</h1>
      <button class="close" @click="emitClose">
        <Exit style="color: #fff" />
      </button>
    </div>
    <div class="rent-list" v-auto-animate>
      <div class="rent-main-withdraw">
        <span>{{ t('modals.rent_list_modal.total_accumulated') }}</span>
        <div class="main-perc">
          <UpTrend v-if="app?.user?.rent_mined_tokens_balance > 0" />
          <DownTrend v-else />
          <h1>{{ app?.user?.rent_mined_tokens_balance?.toFixed(4) || (0).toFixed(4) }} fBTC
          </h1>
        </div>
        <button @click="withdraw(app?.user?.rent_mined_tokens_balance)">{{ t('modals.rent_list_modal.withdraw')
        }}</button>
      </div>
      <div class="rent-list-item-wrapper" v-for="(item, index) in app?.rentOutNfts" :key="index">
        <div class="status-info">
          <span class="num">#{{ item?.id }}</span>
          •
          <span class="stat"
            :class="{ completed: item?.end_date && new Date(item?.end_date) <= new Date(), unactive: !item?.end_date }">{{
              !item?.end_date
                ? t('modals.rent_list_modal.not_active') : item?.end_date && new Date(item?.end_date) <= new Date() ?
                  t('modals.rent_list_modal.completed') : t('modals.rent_list_modal.active') }}</span>
        </div>
        <div class="rent-list-item">
          <div class="grouping">
            <img :src="imagePathAsics(getAsicData(item?.nft, all_asics, asicsSheet, 'name'))?.value" width="70px" />
            <div class="trans-data">
              <h1>{{all_asics?.find(el => el?.a == item?.nft)?.n?.toUpperCase()}}</h1>
              <label>{{ t('modals.rent_list_modal.mined') }} <span>{{ item?.end_date ?
                +(getAsicData(item?.nft, all_asics, asicsSheet, 'speed') * (item.rentals_days - (new
                  Date(item?.end_date) - new Date() > 0 ? getDaysUntilDate(item?.end_date).days : 0))).toFixed(3) : 0 }}
                  fBTC</span></label>
              <label>{{ t('modals.rent_list_modal.you_received') }} <span>{{ item?.end_date ?
                +(getAsicData(item?.nft, all_asics, asicsSheet, 'speed') * (item.rentals_days - (new
                  Date(item?.end_date) - new Date() > 0 ? getDaysUntilDate(item?.end_date).days : 0)) * ((1 -
                    (item?.platform_fee / 100)) * (item?.owner_percentage / 100))).toFixed(3) : 0 }} fBTC</span></label>
              <label>{{ t('modals.rent_list_modal.until_end') }} <span>{{ item?.end_date ? new Date(item?.end_date) -
                new Date() > 0 ?
                getDaysUntilDate(item?.end_date).days_word : 0 : t('common.days', { n: item.rentals_days })
                  }}</span></label>
              <label>{{ t('modals.rent_list_modal.distribution') }} <span>{{ item?.owner_percentage }}%</span></label>
            </div>
            <button class="trans-btn"
              :class="{ active_rent: item?.end_date && new Date(item?.end_date) > new Date(), discard: !item?.end_date }"
              @click="cancelRent(item)">
              <h1 v-if="!item?.end_date">{{ t('modals.rent_list_modal.cancel') }}</h1>
              <h1 v-if="item?.end_date && new Date(item?.end_date) <= new Date()">{{ t('modals.rent_list_modal.delete')
                }}</h1>
              <h2 v-if="item?.end_date && new Date(item?.end_date) > new Date()">{{
                t('modals.rent_list_modal.accumulated') }}</h2>
              <p v-if="item?.end_date && new Date(item?.end_date) > new Date()"><img src="@/assets/fBTC.webp"
                  width="16px" />{{+(getAsicData(item.nft, all_asics, asicsSheet, 'speed') * (item.rentals_days -
                    getDaysUntilDate(item?.end_date).days) * ((1 - (item?.platform_fee / 100)) * (item?.owner_percentage /
                      100))).toFixed(3) }}</p>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
  <WithdrawRentModal v-if="openWithdraw" :sum="withdraw_sum" @close="responseWithdraw" />
  <CancelRentModal v-if="openCancelRent" :item="cancelItem" @close="responseCancelRent" />
</template>

<style lang="scss" scoped>
.rent-percentage {
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
    padding: 0.7rem 0;

    h1 {
      color: #fff;
      font-family: 'Inter' !important;
      font-weight: 600;
      font-size: 28px;
    }

    .close {
      position: absolute;
      right: 5px;
    }
  }

  .rent-list {
    display: flex;
    flex-direction: column;
    width: 90%;
    border-radius: 1rem;
    border-top: 1px solid #ffffff50;
    justify-content: start;
    align-items: center;
    gap: 0.7rem;
    padding-bottom: 130px;
    overflow-y: scroll;
    -ms-overflow-style: none;
    /* Internet Explorer 10+ */
    scrollbar-width: none;
    /* Firefox */

    &::-webkit-scrollbar {
      display: none;
      /* Safari and Chrome */
    }

    .rent-main-withdraw {
      width: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      border-radius: 1rem;
      border: 1px solid #ffffff50;
      background: #08150a80;
      padding: 10px 15px;
      margin-bottom: 1rem;
      gap: 5px;

      span {
        color: #ffffffb3;
        font-family: 'Inter';
        font-weight: 400;
        font-size: 16px;
      }

      .main-perc {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;

        h1 {
          color: #ffffff;
          font-family: 'Inter';
          font-weight: 600;
          font-size: 28px;
        }
      }

      button {
        color: #ffffff;
        font-family: 'Inter';
        font-weight: 600;
        font-size: 24px;
        background: #8143fc;
        width: 100%;
        padding: 0.5rem;
        border-radius: 0.7rem;
        transition: all 0.3s ease;

        &:active {
          opacity: 0.5;
          scale: 0.95;
        }
      }
    }

    &-item-wrapper {
      width: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;

      .status-info {
        display: flex;
        width: 94%;
        align-items: center;
        justify-content: start;
        color: #ffffff50;
        font-size: 18px;
        font-family: 'Inter';
        font-weight: 400;
        gap: 5px;

        .num {
          font-weight: 500;
          color: #ffffff;
        }

        .stat {
          color: #7ff974;

          &.completed {
            color: #8674f9;
          }

          &.unactive {
            color: #FF3B59;
          }
        }
      }

      .rent-list-item {
        width: 100%;
        border-radius: 1rem;
        border: 1px solid #ffffff50;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        padding: 10px;
        background-color: #08150a80;

        .grouping {
          display: flex;
          width: 100%;
          gap: .3rem;
          align-items: center;
        }

        .trans-data {
          display: flex;
          width: 100%;
          flex-direction: column;
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
            font-family: 'Inter';
            font-size: 12px;
            font-weight: 400;
            letter-spacing: 0%;
            color: #ffffff80;
            line-height: 16px;

            span {
              font-weight: 500;
              color: #fff;
            }
          }
        }

        .trans-btn {
          display: flex;
          min-width: max-content;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          background: linear-gradient(to bottom, #8143FC, #472193);
          padding: .7rem .7rem;
          border-radius: .7rem;
          transition: all 100ms ease-in-out;

          &:active {
            opacity: 0.5;
            scale: 0.95;
          }

          &.active_rent {
            background: linear-gradient(to bottom, #8143FC50, #47219350);
            box-shadow: inset 0 0 1px 1px #8143FC;
            padding: .5rem .7rem;
          }

          &.discard {
            background: none;
            box-shadow: inset 0 0 1px 1px #FF3B59;

            >h1 {
              color: #FF3B59 !important;
            }
          }

          h1 {
            font-family: 'Inter';
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0%;
            color: #fff;
          }

          h2 {
            font-family: 'Inter';
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0%;
            color: #ffffff80;
          }

          p {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 5px;
            font-family: 'Inter';
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0%;
            line-height: 16px;
            color: #fff;
          }

          label {
            font-family: 'Inter';
            font-size: 16px;
            font-weight: 400;
            letter-spacing: 0%;
            line-height: 16px;
            color: #fff;
          }
        }

        .withdraw-btn {
          width: 100%;
          color: #ffffff;
          font-family: 'Inter';
          font-weight: 600;
          font-size: 20px;
          background: #8143fc;
          width: 100%;
          padding: 0.5rem;
          border-radius: 0.7rem;
          transition: all 0.3s ease;

          &:active {
            opacity: 0.5;
            scale: 0.95;
          }
        }
      }
    }
  }
}
</style>
