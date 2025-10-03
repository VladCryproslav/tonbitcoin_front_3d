<script setup>
const Exit = defineAsyncComponent(() => import('@/assets/exit.svg'))
import { useAppStore } from '@/stores/app'
import { defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { host } from '../../axios.config'
import { useI18n } from 'vue-i18n'

const app = useAppStore()
const { t } = useI18n()
const emit = defineEmits(['close'])

const emitClose = () => {
  emit('close')
}

defineOptions({
  inheritAttrs: false
})

const currFilter = ref(null)
const currStatus = ref(null)
const currFilterSide = ref('btl')

const currHistory = ref(app?.staking || [])

const stakeScrollContainer = ref(null)

const setFilter = (filter) => {
  if (stakeScrollContainer.value) {
    stakeScrollContainer.value.scrollTo({ top: 0, behavior: 'smooth' })
  }
  if (filter == 'date') {
    if (currFilter.value !== null && currFilter.value !== 'start_date') {
      currFilter.value = 'start_date'
      currStatus.value = null
      currFilterSide.value = 'ltb'
    } else if (currFilterSide.value == 'ltb' && currFilter.value !== null) {
      currFilter.value = null
      currStatus.value = null
      currFilterSide.value = 'btl'
    } else if (currFilter.value == null) {
      currFilter.value = 'end_date'
      currStatus.value = null
      currFilterSide.value = 'btl'
    }
  } else if (filter == 'status') {
    if (currStatus.value == null) {
      currStatus.value = 'pending'
      currFilter.value = null
    } else if (currStatus.value !== null && currStatus.value == 'pending') {
      currStatus.value = 'active'
      currFilter.value = null
    } else if (currStatus.value !== null && currStatus.value == 'active') {
      currStatus.value = 'wait_deposit'
      currFilter.value = null
    } else if (currStatus.value !== null && currStatus.value == 'wait_deposit') {
      currStatus.value = 'finished'
      currFilter.value = null
    } else if (currStatus.value !== null && currStatus.value == 'finished') {
      currStatus.value = null
      currFilter.value = null
    }
  } else if (filter == 'sum') {
    if (currFilter.value !== null && currFilter.value !== 'token_amount') {
      currFilter.value = 'token_amount'
      currStatus.value = null
      currFilterSide.value = 'btl'
    } else if (currFilter.value !== null && currFilter.value == 'token_amount') {
      currFilter.value = null
      currStatus.value = null
      currFilterSide.value = 'btl'
    } else if (currFilter.value == null) {
      currFilter.value = 'token_amount'
      currStatus.value = null
      currFilterSide.value = 'btl'
    }
  } else {
    return
  }
}

const getHistory = async () => {
  try {
    await host
      .get(
        `user-stakings/${currStatus.value ? '?status=' + currStatus.value : ''}${currFilter.value ? '?ordering=' + currFilter.value : ''}`,
      )
      .then((res) => {
        if (res.status == 200) {
          currHistory.value = res.data
        }
      })
  } catch (err) {
    console.log(err)
  }
}

onMounted(() => {
  getHistory()
})

watch([currFilter, currStatus], () => {
  getHistory()
})
</script>

<template>
  <div class="stake-percentage">
    <div class="top-panel">
      <h1>{{ t('modals.history.title') }}</h1>
      <button class="close" @click="emitClose">
        <Exit style="color: #fff" />
      </button>
    </div>
    <div class="history-filters">
      <div class="sort-pill" :class="{ selected: currFilter !== null && currFilter !== 'token_amount' }"
        @click="setFilter('date')">
        {{
          currFilter !== null && currFilter !== 'token_amount' && currFilterSide == 'ltb'
            ? '▲'
            : '▼'
        }}
        {{ t('modals.history.date') }}
      </div>
      <div class="sort-pill" :class="{ selected: currStatus !== null }" @click="setFilter('status')">
        {{ currStatus !== null && currFilterSide == 'ltb' ? '▲' : '▼' }}
        {{ currStatus !== null ? currStatus?.split('_')[0] : t('modals.history.status') }}
      </div>
      <div class="sort-pill" :class="{ selected: currFilter == 'token_amount' }" @click="setFilter('sum')">
        {{ currFilter == 'token_amount' && currFilterSide == 'ltb' ? '▲' : '▼' }} {{ t('modals.history.sum') }}
      </div>
    </div>
    <div class="history-list" ref="stakeScrollContainer" v-auto-animate>
      <div class="history-list-item" v-for="(item, index) in currHistory" :key="index">
        <div class="trans-image">
          <img v-if="new Date(item?.end_date) > new Date()" src="@/assets/deposit_staking.webp" width="50px" />
          <img v-if="new Date(item?.end_date) <= new Date()" src="@/assets/withdraw_staking.webp" width="50px" />
        </div>
        <div class="trans-data">
          <h1>
            #{{ item?.id }} {{ new Date(item?.end_date) <= new Date() ? t('modals.history.completed') :
              t('modals.history.deposit') }} </h1>
              <label>{{ t('modals.history.period') }}: <span>{{ t('common.days', { n: item?.days })
              }}</span></label>
              <label>{{ t('modals.history.apr') }}: <span>{{ item?.apr }}%</span></label>
              <label>{{ t('modals.history.date_label') }}
                <span>{{
                  new Date(item?.end_date) <= new Date() ? new Date(item?.end_date).toLocaleDateString('ru-RU') : new
                    Date(item?.start_date).toLocaleDateString('ru-RU') }}</span></label>
        </div>
        <div class="trans-amount">
          <label>{{ new Date(item?.end_date) <= new Date() ? t('modals.history.received') : t('modals.history.sent')
              }}</label>
              <h1>
                {{ new Date(item?.end_date) <= new Date() ? +(item?.reward).toFixed(4) :
                  +(item?.token_amount).toFixed(4) }} fBTC </h1>
                  <label v-if="new Date(item?.end_date) <= new Date()">{{ t('modals.history.for_staking') }}</label>
        </div>
      </div>
    </div>
  </div>
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

  .history-list {
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
      padding: 5px 10px;
      background-color: #08150a80;

      .trans-image {
        min-width: 50px;
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
          color: #ffffff50;

          span {
            font-weight: 500;
            color: #ffffff;
          }
        }
      }

      .trans-amount {
        display: flex;
        min-width: max-content;
        flex-direction: column;
        align-items: end;
        justify-content: center;

        label {
          font-family: 'Inter';
          font-size: 12px;
          font-weight: 400;
          letter-spacing: 0%;
          line-height: 12px;
          color: #ffffff50;
        }

        h1 {
          font-family: 'Inter';
          font-size: 20px;
          font-weight: 600;
          letter-spacing: 0%;
          color: #fff;
        }
      }
    }
  }
}
</style>
