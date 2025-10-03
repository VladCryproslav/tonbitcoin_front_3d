<script setup>
const UpTrend = defineAsyncComponent(() => import('@/assets/up-trend.svg'))
const DownTrend = defineAsyncComponent(() => import('@/assets/down-trend.svg'))
const Exit = defineAsyncComponent(() => import('@/assets/exit.svg'))
import { useAppStore } from '@/stores/app'
import { useTonAddress } from '@townsquarelabs/ui-vue'
import { computed, defineAsyncComponent, ref } from 'vue'
import ModalNew from './ModalNew.vue'
import WithdrawStakingModal from './WithdrawStakingModal.vue'
import { useI18n } from 'vue-i18n'

defineOptions({
  inheritAttrs: false
})

const app = useAppStore()
const { t } = useI18n()
const emit = defineEmits(['close'])

const ton_address = useTonAddress()

const emitClose = () => {
  emit('close')
}

const withdraw_sum = ref(null)
const withdraw_dep = ref(null)
const openWithdraw = ref(false)

const openModal = ref(false)
const modalBody = ref('')
const modalTitle = ref('')
const modalStatus = ref('')

const showModal = (status, title, body) => {
  modalStatus.value = status
  modalTitle.value = title
  modalBody.value = body
  openModal.value = true
}

// const currCollected = computed(() => {
//   const totalEarnings = app?.staking
//     ?.reduce((sum, item) => {
//       const lastCollectedDate = new Date(item.last_collected)
//       const operationDate = new Date(item?.end_date) - new Date() > 0 ? new Date() : new Date(item?.end_date)
//       const timeDiffMs = operationDate - lastCollectedDate
//       const daysPassed = timeDiffMs / (1000 * 60 * 60 * 24)
//       const dailyProfit = (item?.token_amount * (item?.apr / 100)) / 365
//       const periodProfit = dailyProfit * daysPassed
//       return sum + periodProfit
//     }, 0)
//   return totalEarnings
// })

const currCollected = computed(() => {
  const totalEarnings = app?.staking
    ?.reduce((sum, item) => {
      // Використовуємо дату останнього забирання, якщо є, інакше дату початку стейкінгу
      const referenceDate = item.last_collected ? new Date(item.last_collected) : new Date(item.start_date)
      const endDate = new Date(item?.end_date)
      const currentDate = new Date()

      // Якщо дата останнього забирання (або початку) більша за дату завершення стейкінгу, повертаємо 0
      if (referenceDate > endDate) {
        return sum + 0
      }

      // Визначаємо дату для розрахунку: поточна дата або дата завершення стейкінгу
      const operationDate = currentDate < endDate ? currentDate : endDate

      // Обчислюємо різницю в днях між датою операції та референтною датою
      const timeDiffMs = operationDate - referenceDate
      const daysPassed = timeDiffMs / (1000 * 60 * 60 * 24)

      // Обчислюємо денний прибуток
      const dailyProfit = (item?.token_amount * (item?.apr / 100)) / 365

      // Обчислюємо прибуток за період
      const periodProfit = dailyProfit * daysPassed

      return sum + periodProfit
    }, 0)
  return totalEarnings
})

async function withdraw(sum, dep) {
  if (!ton_address.value) {
    showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }
  if (dep == 0 && sum < app?.withdraw_config?.min_staking_out) {
    showModal(
      'warning', t('notification.st_attention'), t('notification.min_withdraw_fbtc', { min: app?.withdraw_config?.min_staking_out })
    )
    return
  }

  withdraw_sum.value = sum
  withdraw_dep.value = dep

  openWithdraw.value = true
}

const responseWithdraw = (val) => {
  openWithdraw.value = false
  if (val) {
    showModal(val?.status, val?.title, val?.body)
  }
}
</script>

<template>
  <div class="stake-percentage">
    <div class="top-panel">
      <h1>{{ t('modals.percentages.title') }}</h1>
      <button class="close" @click="emitClose">
        <Exit style="color: #fff" />
      </button>
    </div>
    <div class="percentage-list" v-auto-animate>
      <div class="percentage-main-withdraw">
        <span>{{ t('modals.percentages.all_collected') }}</span>
        <div class="main-perc">
          <UpTrend v-if="currCollected > 0" />
          <DownTrend v-else />
          <h1>{{ +currCollected?.toFixed(4) }} fBTC</h1>
        </div>
        <button @click="withdraw(currCollected, 0)">{{ t('modals.percentages.withdraw') }}</button>
      </div>
      <div class="percentage-list-item-wrapper" v-for="(item, index) in app?.staking" :key="index">
        <div class="status-info">
          <span class="apr">APR {{ item?.apr }}%</span>
          •
          <span class="num">#{{ item?.id }}</span>
          •
          <span class="stat" :class="{ completed: new Date(item?.end_date) <= new Date() }">{{
            new Date(item?.end_date) <= new Date() ? t('modals.percentages.completed') : t('modals.percentages.active')
          }}</span>
        </div>
        <div class="percentage-list-item">
          <div class="grouping">
            <div class="trans-data">
              <label style="opacity: 0.7">{{ t('modals.percentages.deposit') }}</label>
              <h1>{{ item?.token_amount }} fBTC</h1>
              <label style="opacity: 0.5">{{ t('modals.percentages.until') }} {{ new
                Date(item?.end_date).toLocaleDateString('ru-RU') }}</label>
            </div>
            <div class="trans-amount">
              <label style="opacity: 0.7">{{ t('modals.percentages.received') }}</label>
              <h1>
                {{
                  item?.status == 'active'
                    ? +(+item?.collected)?.toFixed(4)
                    : +(+item?.reward)?.toFixed(4)
                }}
                fBTC
              </h1>
              <label v-if="item?.status == 'active'" style="opacity: 0.5">{{ +(item?.reward / item?.days).toFixed(4) }}
                {{ t('modals.percentages.per_day') }}</label>
            </div>
          </div>
          <button v-if="new Date(item?.end_date) <= new Date() && item?.status == 'active'" class="withdraw-btn"
            @click="withdraw(item?.token_amount, item?.id)">
            {{ t('modals.percentages.withdraw_deposit') }}
          </button>
        </div>
      </div>
    </div>
  </div>
  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
  <WithdrawStakingModal v-if="openWithdraw" :sum="withdraw_sum" :deposit="withdraw_dep" @close="responseWithdraw" />
</template>

<style lang="scss" scoped>
.stake-percentage {
  position: fixed;
  bottom: 0;
  z-index: 100;
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

  .percentage-list {
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

    .percentage-main-withdraw {
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

        .apr {
          font-weight: 600;
          color: #ffffffb3;
        }

        .num {
          font-weight: 500;
          color: #ffffff80;
        }

        .stat {
          color: #7ff974;

          &.completed {
            color: #8674f9;
          }
        }
      }

      .percentage-list-item {
        width: 100%;
        border-radius: 1rem;
        border: 1px solid #ffffff50;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        padding: 15px;
        background-color: #08150a80;

        .grouping {
          display: flex;
          width: 100%;
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
            font-size: 20px;
            font-weight: 600;
            letter-spacing: 0%;
            color: #fff;
          }

          label {
            font-family: 'Inter';
            font-size: 16px;
            font-weight: 400;
            letter-spacing: 0%;
            color: #fff;
            line-height: 16px;
          }
        }

        .trans-amount {
          display: flex;
          min-width: max-content;
          flex-direction: column;
          align-items: end;
          justify-content: center;

          h1 {
            font-family: 'Inter';
            font-size: 20px;
            font-weight: 600;
            letter-spacing: 0%;
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
