<script setup>
import Wheel from '@/components/Wheel.vue'
import WheelPrizeModal from '@/components/WheelPrizeModal.vue'
import ModalNew from '@/components/ModalNew.vue'
import { useAppStore } from '@/stores/app'
const InfoIcon = defineAsyncComponent(() => import('@/assets/info_friends.svg'))
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref, watch } from 'vue'
import { host } from '../../axios.config'
import { useTelegram } from '@/services/telegram'
import asicsSheet from '@/services/data'
import { useI18n } from 'vue-i18n'

const wheelRef = ref(null)

const app = useAppStore()
const { t, locale } = useI18n()
const { tg } = useTelegram()

const myPrize = ref(null)
const showMyPrize = ref(true)

const modalStatus = ref('')
const modalTitle = ref('')
const modalBody = ref('')
const openModal = ref(false)

const stopUpdate = ref(false)

const starsBalance = ref(0)
const prizeIdRef = ref(null)
const prizeId = computed(() => prizeIdRef?.value || 0)
const prizeList = computed(() => app?.wheel_prizes || [])

const currFilter = ref(null)
const currFilterSide = ref('btl')
const currRewards = ref([])
const currPage = ref(1)
const totalPages = ref(1)
const rewardsScrollContainer = ref(null)

const setFilter = (filter) => {
  if (rewardsScrollContainer.value) {
    rewardsScrollContainer.value.scrollTo({ top: 0, behavior: 'smooth' })
  }

  if (filter !== 'active' && filter !== 'unactive') {
    return
  }

  // Якщо фільтр не активний або активний інший фільтр
  if (currFilter.value === null || currFilter.value !== filter) {
    currFilter.value = filter
    currFilterSide.value = 'btl' // Перший клік - завжди btl
  }
  // Якщо той самий фільтр активний з btl
  else if (currFilter.value === filter && currFilterSide.value === 'btl') {
    currFilterSide.value = 'ltb' // Другий клік - змінюємо на ltb
  }
  // Якщо той самий фільтр активний з ltb
  else if (currFilter.value === filter && currFilterSide.value === 'ltb') {
    currFilter.value = null // Третій клік - вимикаємо фільтр
    currFilterSide.value = 'btl' // Повертаємо до btl для наступного циклу
  }
}

const getAllPrizes = async () => {
  try {
    let url = 'tasks/user_rewards/';
    const res = await host.get(url);
    if (res.status === 200) {
      return res.data?.results?.[0]?.slot ?? currRewards.value?.[0]?.slot
    }
  } catch (err) {
    console.log(err);
    return currRewards.value?.[0]?.slot
  }
};

const getHistory = async () => {
  try {
    // Формуємо базовий URL
    let url = 'tasks/user_rewards/?page_size=10';
    if (currPage.value) {
      const page = currPage.value
      url += `&page=${page}`;
    }

    // Додаємо параметр status, якщо currFilter.value задано
    if (currFilter.value) {
      const status = currFilter.value === 'active' ? 'unclaimed' : 'claimed';
      url += `&status=${status}`;
    }

    // Додаємо параметр ordering, якщо currFilterSide.value задано
    if (currFilterSide.value) {
      const ordering = currFilterSide.value === 'btl' ? '-created_at' : 'created_at';
      url += `&ordering=${ordering}`;
    }

    // Виконуємо запит
    const res = await host.get(url);
    if (res.status === 200) {
      currRewards.value = res.data?.results;
      totalPages.value = Math.ceil(res.data?.count / 10) || 1
      app.initUser()
    }
  } catch (err) {
    console.log(err);
  }
};

const displayedPages = computed(() => {
  const total = totalPages.value
  const current = currRewards.value
  if (total <= 8) return [...Array(total)].map((_, i) => i + 1)

  const visiblePages = []
  const range = 1 // Скільки сторінок показувати з обох боків від поточної

  // Завжди додаємо першу сторінку
  visiblePages.push(1)

  // Логіка для крапок зліва
  if (current - range > 2) {
    visiblePages.push('...')
  }

  // Центральні сторінки
  const start = Math.max(2, current - range)
  const end = Math.min(total - 1, current + range)

  for (let i = start; i <= end; i++) {
    visiblePages.push(i)
  }

  // Логіка для крапок справа
  if (current + range < total - 1) {
    visiblePages.push('...')
  }

  // Завжди додаємо останню сторінку
  if (total > 1) {
    visiblePages.push(total)
  }

  return visiblePages
})

const nextPage = () => {
  if (currPage.value < totalPages.value) {
    currPage.value++
  } else {
    return
  }
}

const prevPage = () => {
  if (currPage.value > 1) {
    currPage.value--
  } else {
    return
  }
}

watch([currFilter, currFilterSide, currPage], () => {
  getHistory()
})

const imagePath = (path) => {
  const com = computed(
    () => new URL(`../assets/slots/${path}.webp`, import.meta.url).href,
  )
  return com
}

const jarvisIsForever = computed(() => {
  const date = new Date(app?.user?.jarvis_expires)
  return date.getFullYear() === 2100
})
const cryoIsForever = computed(() => {
  const date = new Date(app?.user?.cryo_expires)
  return date.getFullYear() === 2100
})
const magnitIsForever = computed(() => {
  const date = new Date(app?.user?.magnit_expires)
  return date.getFullYear() === 2100
})
const managerIsForever = computed(() => {
  const date = new Date(app?.user?.manager_expires)
  return date.getFullYear() === 2100
})

const spinWheel = async (currency) => {
  if (stopUpdate.value) return
  stopUpdate.value = true
  try {
    if (currency !== 'Stars') {
      const res = await host.post('tasks/spin_wheel/', { currency: currency })
      if (res.status == 200) {
        prizeIdRef.value = res.data?.slot_id
        wheelRef.value.prizeId = prizeId.value
        wheelRef.value?.handleClick()
      }
    } else {
      const invoiceLink = await host.post('tasks/wheel_stars/')
      if (invoiceLink.status == 200) {
        tg.openInvoice(invoiceLink.data?.link, async (status) => {
          if (status == 'paid') {
            const starPrize = await getAllPrizes()
            prizeIdRef.value = starPrize
            wheelRef.value.prizeId = prizeId.value
            wheelRef.value?.handleClick()
          } else {
            // Скидаємо stopUpdate якщо користувач закрив invoice без оплати
            stopUpdate.value = false
            getHistory()
          }
        })
      } else {
        // Якщо invoice не створений, скидаємо stopUpdate
        stopUpdate.value = false
        getHistory()
      }
    }
  } catch (err) {
    console.log(err)
    modalStatus.value = 'error'
    modalTitle.value = t('notification.st_error')
    modalBody.value = t('notification.spin_fail')
    openModal.value = true
    stopUpdate.value = false
    getHistory()
  }
}

function onCanvasRotateStart(rotate) {
  console.log('onCanvasRotateStart')
}

function onRotateEnd(prize) {
  console.log('onRotateEnd', prize)
  myPrize.value = prize
  showMyPrize.value = true
  prizeIdRef.value = null
  stopUpdate.value = false
  getHistory()
}

async function fetchStarsBalance() {
  // try {
  //   // Assuming the method 'payments.getStarsStatus' is available via tg.callMethod
  //   const response = await tg.callMethod('payments.getStarsStatus', {
  //     peer: {
  //       _: 'inputPeerSelf'
  //     }
  //   });
  //   // The actual response structure might differ, adjust accordingly
  //   starsBalance.value = response.balance.amount;
  // } catch (error) {
  //   console.error('Error fetching stars balance:', error);
  // }
  starsBalance.value = 0
}

const getBtnStyle = (item, btn) => {
  return computed(() => {
    if (!item?.asset_type) return ''
    const isDisabled = (item.status !== 'unclaimed' || (item?.asset_type == 'electrics' && app.user?.engineer_level + item?.asset_quantity > 49)) && btn
    const elemStyle =
      item?.asset_type == 'ASIC' ?
        'asic' :
        item?.asset_quantity >= 5 ?
          item?.asset_type == 'jarvis' ? 'violet_bg' : 'violet_border' :
          item?.asset_quantity >= 3 ?
            ['asic_manager', 'magnit'].includes(item?.asset_type) ? 'yellow_bg' : 'yellow_border' : ''
    return isDisabled ? 'disabled' : elemStyle || ''
  })
}

const claimReward = async (item) => {
  if (!item || item.status == 'claimed' || item.status == 'processing') return
  if (item?.asset_type == 'electrics' && app.user?.engineer_level + item?.asset_quantity > 49) return
  try {
    const res = await host.post('tasks/claim_user_reward/', { reward_id: item.id })
    if (res.status == 200) {
      modalStatus.value = 'success'
      modalTitle.value = t('notification.st_success')
      modalBody.value = item?.asset_type == 'electrics' ?
        t("notification.eng_up") :
        ['azot', 'powerbank', 'autostart'].includes(item?.asset_type) ?
          t("notification.booster_dep") :
          item?.asset_type == 'ASIC' ? t("notification.slot_send", { slot: item?.processing_type == 'manual' ? item.n_parameter : t(`boost.${item?.asset_type}`) }) :
            t("notification.temp_activate")
      openModal.value = true
      getHistory()
    }
  } catch (err) {
    console.log(err)
    modalStatus.value = 'error'
    modalTitle.value = t('notification.st_error')
    modalBody.value = err.response.data.status == 'Too many days of active boosters' &&
      ((item?.asset_type == 'jarvis' && jarvisIsForever.value) ||
        (item?.asset_type == 'magnit' && magnitIsForever.value) ||
        (item?.asset_type == 'asic_manager' && managerIsForever.value) ||
        (item?.asset_type == 'cryo' && cryoIsForever.value)) ? t('notification.forever_boost_duration') : err.response.data.status == 'Too many days of active boosters' ?
      t('notification.max_boost_duration') :
      err.response.data.status == 'Max engineer level reached' ? t('notification.max_eng_level') : err.response.data.status || err.response.data.error || err.data.error
    openModal.value = true
  }
}

const premiumActive = computed(() => new Date(app.user?.premium_sub_expires) >= new Date())
const starCost = computed(() => {
  if ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) {
    return Math.round(app?.withdraw_config?.wheel_stars_cost * (100 - ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 5 : ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 10 : 0)) / 100) || 0
  }
  return app?.withdraw_config?.wheel_stars_cost || 0
})

const setPage = (page) => {
  if (+page) {
    currPage.value = +page
  }
}

onMounted(() => {
  app.initWheel()
  app.initUser()
  fetchStarsBalance()
  getHistory()
})

const Asic = (name) => {
  const res = computed(() => {
    return new URL(`../assets/asics/${String(name).toUpperCase()}.webp`, import.meta.url).href
  })
  return res
}

</script>

<template>
  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
  <Transition name="fade">
    <WheelPrizeModal v-if="showMyPrize && myPrize" :prize="myPrize" @close="showMyPrize = false" />
  </Transition>
  <div class="wheel-screen">
    <div class="wheel-section">
      <Wheel ref="wheelRef" v-if="prizeList && prizeList.length > 0" style="width: 150%; max-width: 100%"
        :prizes="prizeList" :prizeId="prizeId" @rotateStart="onCanvasRotateStart" @rotateEnd="onRotateEnd" />
    </div>
    <div class="wheel-info">
      <div class="wheel-title">
        {{ t('wheel.title') }}
        <InfoIcon width="24px" height="24px" />
      </div>
      <div class="wheel-statistic">
        <div class="wheel-statistic-title">{{ t('wheel.balance') }}</div>
        <div class="wheel-statistic-balances">
          <div class="wheel-statistic-balances-kw">
            <img src="@/assets/kW_token.png" width="22px" height="22px" />{{
              +(+app.user.kw_wallet).toFixed(0) || 0
            }}
          </div>
          <div class="wheel-statistic-balances-tbtc">
            <img src="@/assets/fBTC.webp" width="22px" height="22px" />{{
              +(+app.user.tbtc_wallet).toFixed(0) || 0
            }}
          </div>
          <div class="wheel-statistic-balances-stars">
            <img src="@/assets/stars.png" width="22px" height="22px" />{{ starsBalance || 0 }}
          </div>
        </div>
      </div>
      <div class="wheel-button-group">
        <button class="btn-spin-kw" @click="spinWheel('kW')">
          {{ t('wheel.spin_for', { n: app?.withdraw_config?.wheel_kw_cost || 0 }) }}
          <img src="@/assets/kW_token.png" width="22px" height="22px" />
        </button>
        <button class="btn-spin-tbtc" @click="spinWheel('tBTC')">
          {{ t('wheel.spin_for', { n: app?.withdraw_config?.wheel_tbtc_cost || 0 }) }}
          <img src="@/assets/fBTC.webp" width="22px" height="22px" />
        </button>
        <button class="btn-spin-stars col-span-2" @click="spinWheel('Stars')">
          {{ t('wheel.super_for', { n: starCost }) }}
          <img src="@/assets/stars.png" width="22px" height="22px" />
        </button>
      </div>
      <div class="wheel-history">
        <div class="wheel-history-title">{{ t('wheel.rewards_history') }}</div>
        <div class="history-filters">
          <div class="sort-pill" :class="{ selected: currFilter == 'active' }" @click="setFilter('active')">
            {{ currFilter == 'active' && currFilterSide == 'ltb' ? '▲' : '▼' }} {{ t('wheel.active') }}
          </div>
          <div class="sort-pill" :class="{ selected: currFilter == 'unactive' }" @click="setFilter('unactive')">
            {{ currFilter == 'unactive' && currFilterSide == 'ltb' ? '▲' : '▼' }} {{ t('wheel.unactive') }}
          </div>
        </div>
        <div class="wheel-history-list">
          <div v-if="!currRewards?.length" class="wheel-history-list-nodata">
            <span>{{ t('wheel.no_prizes') }}</span>
          </div>
          <div class="wheel-history-list-item" :class="getBtnStyle(item, false).value"
            v-for="(item, index) in currRewards" :key="index">
            <div class="wheel-history-list-item-data">
              <div class="reward-data">
                <img v-if="item?.asset_type == 'kW'" src="@/assets/wheel_kw.png" width="65px" height="65px" />
                <img v-else-if="item?.asset_type == 'tBTC'" src="@/assets/fBTC.webp" width="65px" height="65px" />
                <img v-else-if="item?.asset_type == 'Stars'" src="@/assets/wheel_stars.png" width="65px"
                  height="65px" />
                <img v-else-if="item?.asset_type == 'ASIC'" :src="Asic(item?.n_parameter).value" width="65px"
                  height="65px" />
                <img v-else
                  :src="imagePath(`${item.asset_type}${['magnit', 'asic_manager', 'jarvis'].includes(item.asset_type) ? item.asset_quantity : ''}`).value"
                  width="65px" height="65px" />
                <div class="reward-info">
                  <h3>{{ item?.asset_type == 'ASIC' ? item?.n_parameter : t(`boost.${item?.asset_type}`) }}</h3>
                  <span v-if="item?.asset_type !== 'ASIC'">{{ ['azot', 'powerbank',
                    'autostart'].includes(item.asset_type) ?
                    String(t('common.pcs', { n: item.asset_quantity }).slice(0, -1)) :
                    item?.asset_type == 'electrics' ?
                      String(t('common.pers', { n: item.asset_quantity })) :
                      String((locale == 'en' ? 'for ' : 'на ') + t('common.days', { n: item.asset_quantity })) }}</span>
                  <span v-if="item?.asset_type == 'ASIC'">{{ t('asic_shop.speed') }}
                    {{
                      asicsSheet.find(
                        (el) =>
                          el.name.trim().toLowerCase() == item?.n_parameter.trim().toLowerCase(),
                      )?.hash_rate >= 1000
                        ? asicsSheet.find(
                          (el) =>
                            el.name.trim().toLowerCase() ==
                            item?.n_parameter.trim().toLowerCase(),
                        )?.hash_rate /
                        1000 +
                        ` ${t('common.per_s', { value: 'Gh' })}`
                        : asicsSheet.find(
                          (el) =>
                            el.name.trim().toLowerCase() ==
                            item?.n_parameter.trim().toLowerCase(),
                        )?.hash_rate + ` ${t('common.per_s', { value: 'Mh' })}`
                    }}</span>
                  <span v-if="item?.asset_type == 'ASIC'">{{ t('asic_shop.mining') }}
                    {{
                      asicsSheet.find(
                        (el) =>
                          el.name.trim().toLowerCase() == item?.n_parameter.trim().toLowerCase(),
                      )?.speed
                    }}
                    {{ t('common.per_d', { value: 'fBTC' }) }}</span>
                  <span v-if="item?.asset_type == 'ASIC'">{{ t('asic_shop.consumption') }}
                    {{
                      asicsSheet.find(
                        (el) =>
                          el.name.trim().toLowerCase() == item?.n_parameter.trim().toLowerCase(),
                      )?.consumption
                    }}
                    {{ t('common.per_h', { value: 'kW' }) }}</span>
                </div>
              </div>
              <button class="reward-btn" :class="getBtnStyle(item, true).value" @click="claimReward(item)">
                {{
                  item?.status == 'unclaimed'
                    ? ['azot', 'powerbank', 'autostart'].includes(item.asset_type) ? t('wheel.deposit') : item.asset_type ==
                      'ASIC' ? t('wheel.get') :
                      t('wheel.use')
                    : item?.status == 'processing'
                      ? t('wheel.inprocess')
                      : t('wheel.done')
                }}
              </button>
            </div>
            <div class="wheel-history-list-item-notif">
              {{ ['azot', 'powerbank', 'autostart'].includes(item.asset_type) ? t('wheel.bottom_text_1') :
                item.asset_type == 'ASIC' ? t('wheel.bottom_text_2') :
                  t('wheel.bottom_text_3')
              }}
            </div>
          </div>
        </div>
        <div v-if="currRewards?.length" class="available-pagination">
          <div class="pages">
            <ul class="page-group">
              <li class="page-cell" :class="{ activepage: currPage == number, dots: number == '...' }"
                v-for="number in displayedPages" :key="number" @click="setPage(number)">
                {{ number }}
              </li>
            </ul>
          </div>
          <div class="navigate-control">
            <button class="prev" :class="{ unactive: currPage == 1 }" @click="prevPage">
              {{ t('common.prev_page') }}
            </button>
            <button class="next" :class="{ unactive: currPage == totalPages }" @click="nextPage">
              {{ t('common.next_page') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.7s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.wheel-screen {
  position: absolute;
  top: 0;
  left: 0;
  padding-bottom: 160px;
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: radial-gradient(100% 70% at top center, #6762f0, transparent);
  overflow-y: scroll;
  overflow-x: hidden;
  -ms-overflow-style: none;
  /* Internet Explorer 10+ */
  scrollbar-width: none;
  /* Firefox */

  &::-webkit-scrollbar {
    display: none;
    /* Safari and Chrome */
  }

  .wheel-section {
    width: 150%;
    height: auto;
    margin: -68% -25% 0;
    padding-bottom: 10%;
  }

  .wheel-info {
    width: 90%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    margin: 0 auto;

    .wheel-title {
      display: flex;
      justify-content: center;
      align-items: center;
      text-align: center;
      gap: 10px;
      color: #fff;
      font-family: 'Inter';
      font-size: 28px;
      font-weight: bold;
      letter-spacing: 0px;
    }

    .wheel-statistic {
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      gap: 5px;
      padding: 10px 0 20px;

      &-title {
        display: flex;
        justify-content: center;
        align-items: center;
        text-align: center;
        color: #fff;
        font-family: 'Inter';
        font-size: 14px;
        font-weight: 400;
        letter-spacing: 0px;
        opacity: 0.5;
      }

      &-balances {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 90%;
        margin: 0 auto;
        color: #fff;
        font-family: 'Inter' !important;
        font-size: 11px;
        font-weight: 600;
        gap: 15px;

        &-tbtc,
        &-kw,
        &-stars {
          min-width: max-content;
          display: flex;
          align-items: center;
          gap: 5px;
          background: linear-gradient(to left, #00000050, transparent);
          border-radius: 5rem;
          padding-right: 7px;

          span {
            margin-right: 0.5rem;
          }
        }
      }
    }

    .wheel-button-group {
      width: 100%;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0.7rem;

      .btn-spin {

        &-kw,
        &-tbtc,
        &-stars {
          font-family: 'Inter';
          font-weight: bold;
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 5px;
          width: 100%;
          padding: 13px 0;
        }

        &-kw,
        &-tbtc {
          color: #212121;
          font-size: 12.15px;
        }

        &-kw {
          background: linear-gradient(to bottom, #e2f974, #009600);
          border-radius: 10px;

          &:active {
            background: linear-gradient(to bottom, #e2f97490, #00960090);
          }
        }

        &-tbtc {
          background: linear-gradient(to bottom, #fcd909, #fea400);
          border-radius: 10px;

          &:active {
            background: linear-gradient(to bottom, #fcd90990, #fea40090);
          }
        }

        &-stars {
          color: #fff;
          background: linear-gradient(to right, #d340ff, #ff7047);
          border-radius: 10px;
          box-shadow: 0 0 20px 5px #d340ff40;

          &:active {
            background: linear-gradient(to right, #d340ff90, #ff704790);
          }
        }
      }
    }

    .wheel-history {
      display: flex;
      flex-direction: column;
      justify-content: start;
      align-items: center;
      margin: 0 auto;
      width: 100%;
      gap: 20px;
      padding: 30px 0;

      &-title {
        font-family: 'Inter';
        font-weight: bold;
        font-size: 24px;
        letter-spacing: 0px;
        color: #fff;
      }

      &-list {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: 15px;

        &-nodata {
          width: 100%;
          display: flex;
          align-items: center;
          padding: 4rem 0 3rem 0;
          gap: 10px;

          >span {
            color: #ffffff99;
            font-family: 'Inter';
            font-weight: 400;
            font-size: 16px;
            text-align: center;
            letter-spacing: 0%;
          }
        }

        &-item {
          width: 100%;
          background: #08150a50;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          border-radius: 1rem;
          border: 1px solid #ffffff25;
          overflow: hidden;

          &.asic {
            background: linear-gradient(to right, #3f894c, #07522c);
            border: 1px solid #0ea65a;
            box-shadow: 0 0 35px 5px #2ce38460;
          }

          &.yellow_bg {
            background: linear-gradient(to left, #A36D00, #857100);
            border: 1px solid #fea400;
            box-shadow: 0 0 35px 5px #fcd90960;
          }

          &.yellow_border {
            border: 1px solid #fea400;
          }

          &.violet_bg {
            background: linear-gradient(to left, #5E7CEABB, #9851ECBB, #E757ECBB);
            border: 1px solid #d340ff;
            box-shadow: 0 0 35px 5px #d945e860;
          }

          &.violet_border {
            border: 1px solid #d340ff;
          }

          &-data {
            width: 100%;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            gap: 10px;

            .reward-data {
              display: flex;
              align-items: center;
              gap: 10px;

              span {
                color: #fff;
                font-family: 'Inter';
                font-weight: bold;
                font-size: 20px;
                letter-spacing: 0%;
              }

              .reward-info {
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: start;
                gap: 0;

                h3 {
                  color: #fff;
                  font-family: 'Inter';
                  font-weight: bold;
                  font-size: 15px;
                  line-height: 18px;
                }

                span {
                  color: #ffffff75;
                  font-family: 'Inter';
                  font-weight: 400;
                  font-size: 12px;
                }
              }
            }

            .reward-btn {
              color: #212121;
              padding: 12px 20px;
              background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
                linear-gradient(to bottom, #e2f974, #009600);
              border-radius: 12px;
              font-family: 'Inter';
              font-weight: bold;
              font-size: 12px;
              letter-spacing: 0px;
              text-align: center;

              &:active {
                background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
                  linear-gradient(to bottom, #e2f97490, #00960090);
              }

              &.asic {
                background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
                  linear-gradient(to bottom, #74f98a, #0ea65a);

                &:active {
                  background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
                    linear-gradient(to bottom, #74f98a90, #0ea65a90);
                }
              }

              &.yellow_bg,
              &.yellow_border {
                background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
                  linear-gradient(to bottom, #fcd909, #fea400);

                &:active {
                  background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
                    linear-gradient(to bottom, #fcd90990, #fea40090);
                }
              }

              &.violet_bg,
              &.violet_border {
                color: #fff;
                background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
                  linear-gradient(to right, #d340ff, #ff7047);

                &:active {
                  background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
                    linear-gradient(to bottom, #d340ff90, #ff704790);
                }
              }

              &.disabled {
                background: linear-gradient(to bottom, #e2e2e2, #646464);
              }
            }
          }

          &-notif {
            width: 100%;
            color: #fff;
            text-align: left;
            display: flex;
            justify-content: start;
            align-items: center;
            font-family: 'Inter';
            font-weight: 400;
            font-size: 11px;
            letter-spacing: 0%;
            background: #00000050;
            padding: 10px 15px;
          }
        }
      }

      .history-filters {
        display: flex;
        justify-content: center;
        gap: 5px;
        align-items: center;
        width: 90%;
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
          width: 100%;
          border: 1px solid #ffffff25;

          &.selected {
            border: 1px solid #ffffff;
          }
        }
      }

      .available-pagination {
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.3rem;
        padding: 1rem auto;

        .pages {
          display: flex;
          justify-content: center;
          align-items: center;
          margin-bottom: 0.3vh;

          .page-group {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 0.3rem;

            .page-cell {
              padding: 0.3rem 0.5rem;
              border-radius: 0.3rem;
              color: #fff;
              background: #08150a50;
              border: 1px solid #ffffff25;
              font-family: 'Inter' !important;
              font-weight: 500;
              font-size: 8px;

              &.dots {
                background: transparent;
                border: none;
                color: #fff;
              }

              &.activepage {
                padding: 0.2rem 0.6rem;
                border-radius: 0.4rem;
                color: #000;
                font-weight: 600;
                font-size: 12px;
                border: none;
                background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
                  linear-gradient(to bottom, #fcd909, #fea400);
              }
            }
          }
        }

        .navigate-control {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 1rem;
          width: 80%;

          .prev,
          .next {
            padding: 0.8rem 1rem;
            width: 100%;
            color: #000;
            font-family: 'Inter' !important;
            font-weight: 600;
            font-size: 3vw;
            border-radius: 0.7rem;
            background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
              linear-gradient(to bottom, #fcd909, #fea400);

            &:active {
              background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff25, transparent),
                linear-gradient(to bottom, #fcd90990, #fea40090);
            }

            &.unactive {
              background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff25, transparent),
                linear-gradient(to bottom, #fcd90990, #fea40090);
            }
          }
        }
      }
    }
  }
}
</style>
