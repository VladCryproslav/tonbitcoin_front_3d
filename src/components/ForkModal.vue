<script setup>
// const UpTrend = defineAsyncComponent(() => import('@/assets/up-trend.svg'))
// const DownTrend = defineAsyncComponent(() => import('@/assets/down-trend.svg'))
const Exit = defineAsyncComponent(() => import('@/assets/exit.svg'))
import { useAppStore } from '@/stores/app'
import { defineAsyncComponent, onMounted, ref, computed } from 'vue'
import ModalNew from './ModalNew.vue'
import WithdrawStakingModal from './WithdrawStakingModal.vue'
import { host } from '../../axios.config'
import { useI18n } from 'vue-i18n'

defineOptions({
  inheritAttrs: false
})

const app = useAppStore()
const { t } = useI18n()
const emit = defineEmits(['close'])

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

const responseWithdraw = (val) => {
  openWithdraw.value = false
  if (val) {
    showModal(val?.status, val?.title, val?.body)
  }
}

// Computed property for sorted special_stake
const sortedSpecialStake = computed(() => {
  if (!app?.special_stake) return []

  return [...app.special_stake].sort((a, b) => {
    const aEndDate = new Date(a?.end_date)
    const bEndDate = new Date(b?.end_date)
    const currentDate = new Date()

    // Check if items are completed (end_date has passed)
    const aCompleted = aEndDate <= currentDate
    const bCompleted = bEndDate <= currentDate

    // If one is completed and the other is not, put completed items at the end
    if (aCompleted && !bCompleted) return 1
    if (!aCompleted && bCompleted) return -1

    // If both are completed or both are active, sort by days in ascending order
    return a?.days - b?.days
  })
})

onMounted(async () => {
  await host.get('user-burned-tbtc/').then(res => {
    if (res.status == 200) {
      app?.setBurnedTbtc(res.data)
    }
  })
})
</script>

<template>
  <div class="fork_modal">
    <div class="top-panel">
      <h1>{{ t('modals.fork.title') }}</h1>
      <button class="close" @click="emitClose">
        <Exit style="color: #fff" />
      </button>
    </div>
    <div class="fork-list" v-auto-animate>
      <div class="converted-item-wrapper" v-for="item in app?.burned_tbtc" :key="item">
        <div class="status-info">
          <span class="apr">APR {{ item?.apr }} %</span>
          •
          <span class="num">#{{ item?.id }}</span>
          •
          <span class="stat" :class="{ completed: new Date(item?.end_date) <= new Date() }">{{
            new Date(item?.end_date) <= new Date() ? t('modals.fork.completed') : t('modals.fork.active') }}</span>
        </div>
        <div class="converted-item">
          <h1>{{ t('modals.fork.converted_fbtc') }}</h1>
          <div class="grouping">
            <span class="converted-naming">{{ t('modals.fork.burned_tbtc') }}<label class="converted-value">{{
              +(item?.amount).toFixed(2) }} tBTC</label></span>
            <span class="converted-naming">{{ t('modals.fork.received_fbtc') }}<label class="converted-value">{{
              +(item?.amount / 10).toFixed(2) }} fBTC</label></span>
            <span class="converted-naming">{{ t('modals.fork.unlock_1') }}<label class="converted-value">{{ new
              Date(item?.unlock_date_1).toLocaleDateString('ru-RU') }}</label></span>
            <span class="converted-naming">{{ t('modals.fork.unlock_2') }}<label class="converted-value">{{ new
              Date(item?.unlock_date_2).toLocaleDateString('ru-RU') }}</label></span>
            <span class="converted-naming">{{ t('modals.fork.unlock_3') }}<label class="converted-value">{{ new
              Date(item?.unlock_date_3).toLocaleDateString('ru-RU') }}</label></span>
            <span class="converted-naming">{{ t('modals.fork.unlock_4') }}<label class="converted-value">{{ new
              Date(item?.unlock_date_4).toLocaleDateString('ru-RU') }}</label></span>
            <span class="converted-naming">{{ t('modals.fork.unlock_5') }}<label class="converted-value">{{ new
              Date(item?.unlock_date_5).toLocaleDateString('ru-RU') }}</label></span>
            <!-- <span class="converted-naming">№6 Разблокировка 20%<label class="converted-value">{{ new Date(item?.unlock_date_6).toLocaleDateString('ru-RU')
                }}</label></span> -->
            <span class="converted-naming">APR<label class="converted-value">{{ item?.apr }}% {{
              t('modals.fork.apr_remaining') }}</label></span>
            <span class="converted-naming">{{ t('modals.fork.interest_amount') }}<label class="converted-value">{{
              +((item?.amount / 10) * 0.04).toFixed(2) }} fBTC</label></span>
          </div>
        </div>
      </div>
      <div v-if="sortedSpecialStake.length" class="mining-fbtc">
        <h1 v-if="app?.burned_tbtc.length">{{ t('modals.fork.mining_fbtc') }}</h1>
        <div class="stat-item">
          <h1>{{ t('modals.fork.total_asics') }}</h1>
          <div class="grouping">
            <span class="stat-naming">{{ t('modals.fork.total_claimed') }}<label class="stat-value">{{
              +(sortedSpecialStake?.reduce((acc, val) => acc + val?.token_amount, 0) / sortedSpecialStake.length *
                (sortedSpecialStake.length +
                  1)).toFixed(2) || 0}} fBTC</label></span>
            <span class="stat-naming">{{ t('modals.fork.sent_25') }}<label class="stat-value">{{
              +(sortedSpecialStake?.reduce((acc, val) => acc + val?.token_amount, 0) /
                sortedSpecialStake.length).toFixed(2) || 0}} fBTC</label></span>
            <span class="stat-naming" v-for="(item, index) in sortedSpecialStake" :key="index">{{ t('modals.fork.lock')
            }}{{ index + 1 }} {{ item?.apr }}%<label class="stat-value">{{ +(item?.token_amount).toFixed(2) || 0 }}
                fBTC</label></span>
            <span class="stat-naming">{{ t('modals.fork.interest') }}<label class="stat-value">{{
              sortedSpecialStake?.reduce((acc, val) => acc + (val?.token_amount * val?.apr * Math.floor(val?.days /
                30) / 12 / 100), 0).toFixed(2)}} fBTC</label></span>
          </div>
        </div>
      </div>
      <div class="fork-list-item-wrapper" v-for="(item, index) in sortedSpecialStake" :key="index">
        <div class="status-info">
          <span class="apr">APR {{ item?.apr }}%</span>
          •
          <span class="num">{{ t('modals.fork.lock') }}{{ index + 1 }}</span>
          •
          <span class="stat" :class="{ completed: new Date(item?.end_date) <= new Date() }">{{ new Date(item?.end_date)
            <= new Date() ? t('modals.fork.completed') : t('modals.fork.active') }}</span>
        </div>
        <div class="fork-list-item">
          <h1>{{ t('modals.fork.asics_s21') }}</h1>
          <div class="grouping">
            <span class="fork-naming">{{ t('modals.fork.total_staked') }}<label class="fork-value">{{ item?.token_amount
            }} fBTC</label></span>
            <span class="fork-naming">{{ t('modals.fork.staking_period') }}<label class="fork-value">{{
              t('common.days', { n: item?.days }) }}</label></span>
            <span class="fork-naming">{{ t('modals.fork.unlock_date') }}<label class="fork-value">{{ new
              Date(item?.end_date).toLocaleDateString('ru-RU') }}</label></span>
            <span class="fork-naming">APR<label class="fork-value">{{ item?.apr }}%</label></span>
            <span class="fork-naming">{{ t('modals.fork.interest') }}<label class="fork-value">{{ +(item?.token_amount *
              item?.apr * Math.floor(item?.days / 30) / 12 / 100).toFixed(2) }} fBTC</label></span>
          </div>
        </div>
        <!-- <button v-if="new Date(item?.end_date) <= new Date() && item?.status == 'active'" class="withdraw-btn"
            @click="withdraw(item?.token_amount, item?.id)">
            Вывести депозит
          </button> -->
      </div>
    </div>
  </div>
  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
  <WithdrawStakingModal v-if="openWithdraw" :sum="withdraw_sum" :deposit="withdraw_dep" @close="responseWithdraw" />
</template>

<style lang="scss" scoped>
.fork_modal {
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

  .fork-list {
    display: flex;
    flex-direction: column;
    width: 90%;
    border-radius: 1rem;
    // border-top: 1px solid #ffffff50;
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

    .converted-item-wrapper {
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

      .converted-item {
        width: 100%;
        border-radius: 1rem;
        border: 1px solid #ffffff50;
        display: flex;
        flex-direction: column;
        align-items: start;
        gap: 5px;
        padding: 15px;
        background-color: #08150a80;

        h1 {
          color: #FFFFFF;
          font-family: 'Inter', sans-serif;
          font-weight: 600;
          font-size: 20px;
        }

        .grouping {
          display: flex;
          flex-direction: column;
          width: 100%;
          align-items: start;
        }

        .converted-naming {
          color: #FFFFFFB3;
          font-family: 'Inter', sans-serif;
          font-weight: 400;
          font-size: 16px;
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: space-between;

          .converted-value {
            color: #FFFFFF;
          }
        }
      }
    }

    .mining-fbtc {
      width: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;

      h1 {
        color: #fff;
        font-family: 'Inter' !important;
        font-weight: 600;
        font-size: 28px;
        margin-bottom: 10px;
      }

      .stat-item {
        width: 100%;
        border-radius: 1rem;
        border: 1px solid #ffffff50;
        display: flex;
        flex-direction: column;
        align-items: start;
        gap: 5px;
        padding: 15px;
        background-color: #8143FC66;

        h1 {
          color: #FFFFFF;
          font-family: 'Inter', sans-serif;
          font-weight: 600;
          font-size: 20px;
        }

        .grouping {
          display: flex;
          flex-direction: column;
          width: 100%;
          align-items: start;
        }

        .stat-naming {
          color: #FFFFFFB3;
          font-family: 'Inter', sans-serif;
          font-weight: 400;
          font-size: 16px;
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: space-between;

          .stat-value {
            color: #FFFFFF;
          }
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

      .fork-list-item {
        width: 100%;
        border-radius: 1rem;
        border: 1px solid #ffffff50;
        display: flex;
        flex-direction: column;
        align-items: start;
        gap: 10px;
        padding: 15px;
        background-color: #08150a80;

        h1 {
          color: #FFFFFF;
          font-family: 'Inter', sans-serif;
          font-weight: 600;
          font-size: 20px;
        }

        .fork-naming {
          color: #FFFFFFB3;
          font-family: 'Inter', sans-serif;
          font-weight: 400;
          font-size: 16px;
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: space-between;

          .fork-value {
            color: #FFFFFF;
          }
        }

        .grouping {
          display: flex;
          flex-direction: column;
          width: 100%;
          align-items: start;
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
</style>
