<script setup>
import InfoIcon from '@/assets/info_icon.svg'
import { useAppStore } from '@/stores/app'
import { useTabsStore } from '@/stores/tabs'
import { getAsicData } from '@/utils/asics'
import { useTonAddress } from '@townsquarelabs/ui-vue'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import RentListModal from '../RentListModal.vue'
import RentAvaliableModal from '../RentAvaliableModal.vue'
import RentModal from '../RentModal.vue'
import RentBanModal from '../RentBanModal.vue'
import { host, tonapi } from '../../../axios.config'
import _ from 'lodash'
import VueSlider from 'vue-3-slider-component'
import asicsSheet from '@/services/data'
import ModalNew from '../ModalNew.vue'
import InfoModal from '../InfoModal.vue'

let controller = null
const app = useAppStore()
const emit = defineEmits(['back'])
const { t } = useI18n()
const all_asics = computed(() => app.getAsicsFromStorage())
const connectedAddressString = useTonAddress(false)
const ton_address = useTonAddress()
const openRentListModal = ref(false)
const openRentAvaliableModal = ref(false)

const asicsIsOpen = useTabsStore()

function openAsics() {
  asicsIsOpen.setCategory('miner')
  asicsIsOpen.setOpenAsicsShop(true)
}

const imagePathAsics = (asic) => {
  const com = computed(
    () => new URL(`../../assets/asics/${asic?.toString().toUpperCase()}.webp`, import.meta.url).href,
  )
  return com
}

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

const rentAvaliableResponse = (val) => {
  openRentAvaliableModal.value = false;
  if (val) {
    rentAsic.value = (!Object.keys(val.asic).length ? {} : val.asic)
  }
}

const rentListResponse = (val) => {
  openRentListModal.value = false;
  if (val) {
    showModal(val.status, val.title, val.body)
  }
}

const rentalParams = ref({ side: null, kw_day: null, kw_all: null, tbtc: null, nft: null, time: null, nft_address: null, profit_per: null, id: null })
const openRentalModal = ref(false)

const makeRent = (side, kw_day, kw_all, tbtc, nft, time, nft_address, profit_per, id) => {
  if (!ton_address.value) {
    showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }
  if (app?.user?.rent_blocked_until && getTimeRemaining(app?.user?.rent_blocked_until).remain > 0) {
    openRentalBan.value = true;
    return;
  }
  rentalParams.value.side = side;
  rentalParams.value.kw_day = kw_day;
  rentalParams.value.kw_all = kw_all;
  rentalParams.value.tbtc = tbtc;
  rentalParams.value.nft = nft;
  rentalParams.value.time = time;
  rentalParams.value.nft_address = nft_address;
  rentalParams.value.profit_per = profit_per;
  rentalParams.value.id = id

  openRentalModal.value = true;
}

const rentModalResponse = (val) => {
  openRentalModal.value = false
  rentalParams.value = {
    side: null,
    kw_day: null,
    kw_all: null,
    tbtc: null,
    nft: null,
    time: null,
    nft_address: null,
    profit_per: null,
    id: null
  }
  if (val) {
    rentAsic.value = {}
    showModal(val.status, val.title, val.body)
  }
}

const currRentToggle = ref('investor')
const rentPeriod = ref(7)
const rentProfit = ref(30)
const rentAsic = ref({})
const openRentalBan = ref(false)
const currFilter = ref(null)
const rentAvailableScrollContainer = ref(null)
const currFilterSide = ref('btl')
const setFilter = (filter) => {
  // Прокрутка до верху, якщо контейнер існує
  // if (rentAvailableScrollContainer.value) {
  //   rentAvailableScrollContainer.value.scrollTo({ top: 0, behavior: 'smooth' });
  // }

  // Якщо фільтр не встановлено або клік на інший фільтр
  if (currFilter.value === null || currFilter.value !== filter) {
    currFilter.value = filter;
    currFilterSide.value = 'btl';
  }
  // Якщо клік на той самий фільтр
  else if (currFilter.value === filter) {
    if (currFilterSide.value === 'btl') {
      currFilterSide.value = 'ltb';
    } else {
      currFilter.value = null;
      currFilterSide.value = 'btl';
    }
  }
};

const currPageAvailableAsics = ref(app?.availableNftRentals?.results || [])
const allAvailablePages = ref(Math.ceil(app?.availableNftRentals?.count / 10) || 1)
const currAvailablePageNum = ref(1)

const handleRentAvailableModal = () => {
  if (!ton_address.value) {
    showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }
  openRentAvaliableModal.value = true
}

const displayedPages = computed(() => {
  const total = allAvailablePages.value
  const current = currAvailablePageNum.value
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

const loadPageData = async (page) => {
  try {
    const params = {
      page: page,
      ordering: currFilter.value
        ? `${currFilterSide.value === 'btl' ? '-' : ''}${currFilter.value}`
        : null,
    }
    controller = new AbortController()
    const respon = await host.get('available-nft-rentals/', { params, signal: controller.signal })

    if (respon.status === 200) {
      currPageAvailableAsics.value = respon.data?.results
      allAvailablePages.value = Math.ceil(respon.data?.count / 10)
      app.setAvailableRental({})
    }
  } catch (error) {
    console.error(error)
    showModal('error', t('notification.st_error'), t('notification.no_available_asics'))
  } finally {
    controller = null
  }
}

const filteredAsics = computed(() => {
  const excludedNfts = new Set(app.nfts?.map(nft => nft?.address) || []);
  return currPageAvailableAsics.value?.filter(asic => !excludedNfts.has(asic?.nft) && !all_asics.value.find(item => item?.a == asic?.nft)?.n?.match(/SBT|21|SX|Maxx/)) || [];
});

const setPage = (page) => {
  if (+page) {
    currAvailablePageNum.value = +page
  }
}

const nextPage = () => {
  if (currAvailablePageNum.value < allAvailablePages.value) {
    currAvailablePageNum.value++
    loadPageData(currAvailablePageNum.value)
  } else {
    return
  }
}

const prevPage = () => {
  if (currAvailablePageNum.value > 1) {
    currAvailablePageNum.value--
    loadPageData(currAvailablePageNum.value)
  } else {
    return
  }
}

watch(
  [currFilter, currFilterSide],
  () => {
    currAvailablePageNum.value = 1
    loadPageData(1)
  },
  { immediate: true }
)

let timeoutId = null
async function updateRent() {
  try {
    if (!app.getAsicsFromStorage().length) {
      const collection1Addr = '0:c9511472ee373f1aeb5d2dd12fc5f5cbf43d30cc1c9f0e23ad2f00346ea9e205'
      const collection2Addr = '0:3126dc7f3db3b6901eb79de8d54a308d7ded51396d04d7ebcb218c48b536b25b'

      try {
        const [col1Info, col2Info] = await Promise.all([
          tonapi.get(`nfts/collections/${collection1Addr}`),
          tonapi.get(`nfts/collections/${collection2Addr}`),
        ])

        const nfts1_pages = Math.ceil(col1Info.data?.next_item_index / 1000)
        const nfts2_pages = Math.ceil(col2Info.data?.next_item_index / 1000)

        const allPagesPromises = []
        for (let i = 0; i < nfts1_pages; i++) {
          allPagesPromises.push(
            tonapi.get(`nfts/collections/${collection1Addr}/items?offset=${i * 1000}`),
          )
        }
        for (let i = 0; i < nfts2_pages; i++) {
          allPagesPromises.push(
            tonapi.get(`nfts/collections/${collection2Addr}/items?offset=${i * 1000}`),
          )
        }

        const allPagesResults = await Promise.allSettled(allPagesPromises)
        const allNfts = allPagesResults?.filter((res) => res.status === 'fulfilled' && res.value.status === 200)?.flatMap((res) => res.value.data?.nft_items)

        // Зберігаємо тільки необхідні дані для зменшення розміру
        const optimizedAsics = allNfts?.map(nft => ({
          a: nft.address,
          n: nft.metadata?.name,
          at: nft.metadata?.attributes
        })) || []
        try {
          // Очищаємо localStorage перед збереженням
          localStorage.removeItem('all_asics')
          localStorage.setItem('all_asics', JSON.stringify(optimizedAsics))
        } catch (error) {
          console.error('Помилка збереження ASIC\'ів в localStorage:', error)
        }
      } catch (error) {
        console.error('Помилка завантаження ASIC\'ів:', error)
      }
    }
    if (connectedAddressString.value) {
      let nfts1 = [],
        nfts2 = []
      controller = new AbortController()
      await tonapi
        .get(
          `accounts/${connectedAddressString.value}/nfts?collection=0:c9511472ee373f1aeb5d2dd12fc5f5cbf43d30cc1c9f0e23ad2f00346ea9e205`, { signal: controller.signal }
        )
        .then((res) => {
          if (res.status == 200) {
            nfts1 = res.data?.nft_items
            app.setNfts(nfts1)
          }
        })
        .catch((err) => {
          console.log(err)
          nfts1 = []
        }).finally(() => {
          controller = null
        })
      controller = new AbortController()
      await tonapi
        .get(
          `accounts/${connectedAddressString.value}/nfts?collection=0:3126dc7f3db3b6901eb79de8d54a308d7ded51396d04d7ebcb218c48b536b25b`, { signal: controller.signal }
        )
        .then((res) => {
          if (res.status == 200) {
            nfts2 = res.data?.nft_items
            app.setNfts(_.concat(nfts1, nfts2))
          }
        })
        .catch((err) => {
          console.log(err)
          nfts2 = []
        }).finally(() => {
          controller = null
        })
      app.setNfts(_.concat(nfts1, nfts2))
    }
    if (!Object.keys(app?.availableNftRentals).length) {
      controller = new AbortController()
      await host.get("available-nft-rentals/").then((res) => {
        if (res.status == 200) {
          app.setAvailableRental(res.data)
        }
      }).finally(() => {
        controller = null
      })
    }
    controller = new AbortController()
    await host.get("user-rented-nfts/", { signal: controller.signal }).then((res) => {
      if (res.status == 200) {
        app.setRentedNft(res.data)
      }
    }).finally(() => {
      controller = null
    })
    controller = new AbortController()
    await host.get("user-lent-nfts/", { signal: controller.signal }).then((res) => {
      if (res.status == 200) {
        app.setRentOutNfts(res.data)
      }
    }).finally(() => {
      controller = null
    })
  } catch (err) {
    console.log(err)
  } finally {
    controller = null
    timeoutId = setTimeout(() => updateRent(), 3000)
  }
}


const getTimeRemaining = (futureISO) => {
  if (!futureISO) {
    return '00:00:00'
  }

  const timeRemaining = ref('00:00:00')
  const timeRemainingMs = ref(null)
  const updateTime = () => {
    const now = new Date()
    const future = new Date(futureISO)
    const diffMs = future - now
    timeRemainingMs.value = diffMs

    if (diffMs <= 0) {
      return '00:00:00'
    }

    const hours = Math.floor(diffMs / (1000 * 60 * 60))
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))
    const seconds = Math.floor((diffMs % (1000 * 60)) / 1000)

    const formattedHours = String(hours).padStart(2, '0')
    const formattedMinutes = String(minutes).padStart(2, '0')
    const formattedSeconds = String(seconds).padStart(2, '0')

    timeRemaining.value = `${formattedHours}:${formattedMinutes}:${formattedSeconds}`
  }

  // Оновлюємо одразу
  updateTime()

  // Запускаємо таймер для оновлення кожну секунду
  const interval = setInterval(updateTime, 1000)

  // Очищаємо інтервал при завершенні (опціонально, залежить від фреймворку)
  onUnmounted(() => clearInterval(interval))

  return { time: timeRemaining.value, remain: timeRemainingMs.value }
}

const openInfoModal = ref(false)

onMounted(() => {
  updateRent()
})

onUnmounted(() => {
  if (controller) {
    controller.abort()
  }
  if (timeoutId) {
    clearTimeout(timeoutId)
    timeoutId = null
  }
})
</script>

<template>
  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
  <RentListModal v-if="openRentListModal" @close="rentListResponse" />
  <RentAvaliableModal v-if="openRentAvaliableModal" :rentAsic="rentAsic" @close="rentAvaliableResponse" />
  <RentModal v-if="openRentalModal" v-bind="rentalParams" @close="rentModalResponse" />
  <RentBanModal v-if="openRentalBan" @close="openRentalBan = false" />
  <InfoModal v-if="openInfoModal" @close="openInfoModal = false">
    <template #modal-body>
      {{ t('notification.rental_off') }}
    </template>
  </InfoModal>
  <div class="investor-radio">
    <label class="rent-radio">
      <input type="radio" :class="{ checked: currRentToggle == 'investor' }" v-model="currRentToggle"
        value="investor" />
      <span class="name" :style="{ borderRadius: '0 0.5rem 0.5rem 0' }">{{ t('investor.investor_tab') }}</span>
    </label>
    <label class="rent-radio">
      <!-- v-model="currRentToggle" -->
      <input type="radio" :class="{ checked: currRentToggle == 'miner' }" value="miner" @click="openInfoModal = true" />
      <span class="name" :style="{ borderRadius: '0.5rem 0 0 0.5rem' }">{{ t('investor.miner_tab') }}</span>
    </label>
  </div>
  <div class="rent">
    <div v-if="currRentToggle == 'investor'" class="rent-pannel">
      <div class="rent-pannel-inv-asic-group">
        <button class="asic-shop-btn" @click="openAsics"><label>{{ t('investor.asics_shop') }}</label></button>
        <button class="asic-history-btn" @click="openRentListModal = true"><img src="@/assets/percent.png"
            width="22px" /></button>
      </div>
      <h1 class="rent-pannel-inv-title">{{ t('investor.rental_setting') }}</h1>
      <div class="own-asic-block">
        <button v-if="!Object.keys(rentAsic).length" class="own-asic-block-btn" @click="handleRentAvailableModal">+
          {{ t('investor.add_asic') }}</button>
        <div v-else class="own-asic-block-pannel" @click="openRentAvaliableModal = true">
          <img :src="imagePathAsics(rentAsic?.metadata?.name)?.value" />
          <div class="own-asic-info">
            <h1 class="own-asic-info-title">{{ rentAsic?.metadata?.name?.toUpperCase() }}</h1>
            <div class="own-asic-info-desc">
              <span class="will-mine">{{ t('investor.rental_mine') }} <label>{{+(getAsicData(rentAsic?.address,
                all_asics,
                asicsSheet, 'speed') * rentPeriod).toFixed(3) }} fBTC</label></span>
              <span class="will-take">{{ t('investor.rental_get') }} <label>{{+(getAsicData(rentAsic?.address,
                all_asics,
                asicsSheet, 'speed') * rentPeriod * (rentProfit / 100 -
                  app?.rental_config?.platform_fee / 100)).toFixed(3) }}
                  fBTC</label></span>
            </div>
          </div>
        </div>
      </div>
      <div class="rent-period">
        <div class="rent-period-text">
          <p>{{ t('investor.rental_period') }}</p>
          <p><b>{{ t('common.days', { n: rentPeriod }) }}</b></p>
        </div>
        <VueSlider v-model="rentPeriod" :height="8" :dotSize="25"
          :dotStyle="{ backgroundColor: '#8143FC', boxShadow: 'none' }" :width="'100%'"
          :min="app?.rental_config?.min_days" :max="app?.rental_config?.max_days" :tooltip="'none'"
          :processStyle="{ backgroundColor: '#8143FC80' }" :railStyle="{ backgroundColor: '#ffffff30' }" />
      </div>
      <div class="rent-profit">
        <div class="rent-profit-text">
          <p>{{ t('investor.rental_income') }}</p>
          <p>{{ rentProfit }} %</p>
        </div>
        <VueSlider v-model="rentProfit" :height="8" :dotSize="25"
          :dotStyle="{ backgroundColor: '#8143FC', boxShadow: 'none' }" :width="'100%'"
          :min="app?.rental_config?.min_percentage" :max="app?.rental_config?.max_percentage" :interval="5"
          :tooltip="'none'" :processStyle="{ backgroundColor: '#8143FC80' }"
          :railStyle="{ backgroundColor: '#ffffff30' }" />
      </div>
      <!--
          @click="makeRent(
            'out',
            null,
            null,
            +(getAsicData(rentAsic?.address, all_asics, asicsSheet, 'speed') * rentPeriod * (rentProfit / 100 - app?.rental_config?.platform_fee / 100)).toFixed(3),
            rentAsic?.metadata?.name?.toUpperCase(),
            rentPeriod,
            rentAsic?.address,
            rentProfit,
            null
          )"
           -->
      <button class="rent-btn" :disabled="!Object.keys(rentAsic).length" @click="openInfoModal = true">{{
        t('investor.rent_out') }}</button>
      <button class="back-btn" @click="emit('back')">
        {{ t('investor.back') }}
      </button>
    </div>
    <div v-if="currRentToggle == 'miner'" class="rent-pannel">
      <div class="rent-pannel-inv-asic-group">
        <button class="asic-shop-btn" @click="openAsics"><label>{{ t('investor.asics_shop') }}</label></button>
      </div>
      <button class="back-btn" @click="emit('back')">
        {{ t('investor.back') }}
      </button>
      <h1 class="rent-pannel-mine-title">{{ t('investor.nft_list') }}
        <InfoIcon :width="30" style="width: 30px;" />
      </h1>
      <div class="rent-filters">
        <div class="sort-pill" :class="{ selected: currFilter == 'rentals_days' }" @click="setFilter('rentals_days')">
          {{ currFilter == 'rentals_days' && currFilterSide == 'ltb'
            ? '▲'
            : '▼'
          }} {{ t('investor.period') }}
        </div>
        <div class="sort-pill" :class="{ selected: currFilter == 'adjusted_owner_percentage' }"
          @click="setFilter('adjusted_owner_percentage')">
          {{ currFilter == 'adjusted_owner_percentage' && currFilterSide == 'ltb'
            ? '▲'
            : '▼'
          }} {{ t("investor.percent") }}
        </div>
        <div class="sort-pill" :class="{ selected: currFilter == 'hashrate' }" @click="setFilter('hashrate')">
          {{
            currFilter == 'hashrate' && currFilterSide == 'ltb'
              ? '▲'
              : '▼'
          }}
          {{ t("investor.asic_power") }}
        </div>
      </div>
      <div class="rent-list-wrapper" ref="rentAvailableScrollContainer" v-auto-animate>
        <div class="rent-list-item" v-for="item in filteredAsics" :key="item.nft">
          <div class="grouping">
            <img :src="imagePathAsics(getAsicData(item.nft, all_asics, asicsSheet, 'name'))?.value" width="70px" />
            <div class="trans-data">
              <h1>{{all_asics?.find(el => el?.a == item?.nft)?.n?.toUpperCase() ||
                t("preloader.loading")}}</h1>
              <label>{{ t("investor.rental_mine") }}<span>{{+(getAsicData(item.nft, all_asics, asicsSheet, 'speed') *
                item?.rentals_days).toFixed(3) || 0 }}
                  fBTC</span></label>
              <label>{{ t('investor.rental_get') }} <span>{{+((getAsicData(item.nft, all_asics, asicsSheet, 'speed') *
                item?.rentals_days) * (1 - (item?.owner_percentage / 100) - (item?.platform_fee /
                  100))).toFixed(3) || 0 }}
                  fBTC</span></label>
              <label>{{ t("investor.rental_period") }}<span>{{ t('common.days', { n: item?.rentals_days ?? 0 })
              }}</span></label>
              <label>{{ t("investor.rental_distr") }}<span>{{ 100 - item?.owner_percentage - item?.platform_fee
                  }}%</span></label>
            </div>
            <button class="trans-btn"
              :disabled="!all_asics?.find(el => el?.a == item?.nft) || !getAsicData(item.nft, all_asics, asicsSheet, 'consumption')"
              @click="() => {
                if (
                  !all_asics?.find(el => el?.a == item?.nft) ||
                  !getAsicData(item.nft, all_asics, asicsSheet, 'consumption')
                ) { return }
                makeRent(
                  'in',
                  getAsicData(item.nft, all_asics, asicsSheet, 'consumption') * 24,
                  getAsicData(item.nft, all_asics, asicsSheet, 'consumption') * 24 * item?.rentals_days,
                  +((getAsicData(item.nft, all_asics, asicsSheet, 'speed') * item?.rentals_days) * (1 - (item.owner_percentage / 100) - (item.platform_fee / 100))).toFixed(3),
                  all_asics?.find(el => el?.a == item?.nft)?.n.toUpperCase(),
                  item?.rentals_days,
                  null,
                  null,
                  item?.id
                )
              }">
              <h1>{{ t('investor.rent_in') }}</h1>
              <label><img src="@/assets/kW_token.png" width="14px" />{{((num) => num ? num < 1000 ? num.toString() :
                +(num / 1000).toFixed(num % 1000 >= 100 ? 2 : num % 1000 >= 10 ? 1 : 0) + 'К' :
                0)(getAsicData(item.nft, all_asics, asicsSheet, 'consumption') * 24) }}</label>
            </button>
          </div>
        </div>
      </div>
      <div v-if="filteredAsics.length > 0" class="available-pagination">
        <div class="pages">
          <ul class="page-group">
            <li class="page-cell" :class="{ activepage: currAvailablePageNum == number, dots: number == '...' }"
              v-for="number in displayedPages" :key="number" @click="setPage(number)">
              {{ number }}
            </li>
          </ul>
        </div>
        <div class="navigate-control">
          <button class="prev" :class="{ unactive: currAvailablePageNum == 1 }" @click="prevPage">
            {{ t('common.prev_page') }}
          </button>
          <button class="next" :class="{ unactive: currAvailablePageNum == allAvailablePages }" @click="nextPage">
            {{ t('common.next_page') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.investor-radio {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  border-radius: 0.7rem;
  border: 1px solid #8143fc;
  box-sizing: border-box;
  box-shadow: 0 0 0px 1px rgba(0, 0, 0, 0.06);
  width: 100%;
  font-family: 'Inter';
  font-weight: 600;
  font-size: 24px;
  letter-spacing: 0px;
  overflow: hidden;

  .radio {
    flex: 1 0 50%;
    text-align: center;

    input {
      display: none;

      &:checked+.name {
        background-color: #8143fc;
        font-weight: 600;
      }
    }

    .name {
      display: flex;
      cursor: pointer;
      align-items: center;
      justify-content: center;
      border-radius: 0.5rem;
      border: none;
      padding: 0.5rem 0;
      color: #fff;
      transition: all 0.15s ease-in-out;

      &.rent-border {
        border-radius: 0.5rem 0 0 0.5rem;
      }
    }
  }

  .rent-radio {
    flex: 1 0 50%;
    text-align: center;

    input {
      display: none;

      &.checked+.name {
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);
        color: #212121;
        font-weight: 600;
      }
    }

    .name {
      display: flex;
      cursor: pointer;
      align-items: center;
      justify-content: center;
      border-radius: 0.5rem;
      border: none;
      padding: 0.2rem 0;
      font-size: 20px;
      color: #fff;
      transition: all 0.15s ease-in-out;
    }
  }
}

.rent {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;

  &-pannel {
    width: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 0.2em;

    .rent-filters {
      display: flex;
      justify-content: center;
      gap: 5%;
      align-items: center;
      padding: 0;
      margin-bottom: 10px;

      .sort-pill {
        padding: 0.3rem 0.5rem 0.2rem 0.5rem;
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

    &-inv-asic-group {
      display: flex;
      justify-content: center;
      gap: .5rem;

      .asic-shop-btn {
        position: relative;
        text-transform: uppercase;
        color: #212121;
        font-family: 'Inter';
        font-size: 20px;
        font-weight: 900;
        padding: .8rem 0;
        border-radius: .7rem;
        width: 100%;
        min-height: 60px;
        background: linear-gradient(to bottom, #FFC10D, #E37706);
        transition: all 100ms ease-in-out;

        label {
          position: absolute;
          left: 50%;
          top: 50%;
          transform: translate(-50%, -50%);
          z-index: 100;
          text-wrap: nowrap;
        }

        &::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: url('@/assets/mining-panel_new.svg') no-repeat center;
          background-size: 250px;
          background-position: 50% 60%;
          opacity: 0.25;
          z-index: 1;
        }

        &:active {
          scale: 0.95;
          opacity: 0.8;
        }
      }

      .asic-history-btn {
        border-radius: .7rem;
        aspect-ratio: 1/1;
        width: 70px;
        display: flex;
        justify-content: center;
        align-items: center;
        border: 1px solid #8143fc;
        transition: all 100ms ease-in-out;
        z-index: 10;

        &:active {
          scale: 0.95;
          opacity: 0.8;
        }
      }
    }

    &-inv-title {
      width: 100%;
      margin: .7rem 0 .2rem;
      text-align: center;
      color: #fff;
      font-family: 'Inter';
      font-weight: 600;
      font-size: 20px;
      letter-spacing: 0px;
    }

    .rent-list-wrapper {
      width: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      gap: .5rem;

      .rent-list-item {
        width: 100%;
        border-radius: 1rem;
        border: 1px solid #ffffff50;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        padding: 5px 7px;
        background-color: #08150a80;

        .grouping {
          display: flex;
          width: 100%;
          gap: .7rem;
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
            color: #8143FC;
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
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff50, transparent),
            linear-gradient(to bottom, #B28FF8, #8143FC);
          padding: .3rem .7rem;
          border-radius: .7rem;
          transition: all 100ms ease-in-out;

          h1 {
            font-family: 'Inter';
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0%;
            color: #212121;
          }

          label {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 2px;
            font-family: 'Inter';
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0%;
            line-height: 16px;
            color: #212121;
          }

          &:active {
            opacity: 0.9;
            scale: 0.98;
          }

          &:disabled {
            background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
              linear-gradient(to bottom, #e2e2e2, #646464);
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

    .available-pagination {
      grid-column: span 3 / span 3;
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

    &-mine-title {
      width: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
      gap: .5rem;
      margin: .7rem 0 .2rem;
      text-align: center;
      color: #fff;
      font-family: 'Inter';
      font-weight: 600;
      font-size: 24px;
      letter-spacing: 0px;
    }

    .own-asic-block {
      display: flex;
      justify-content: center;
      align-items: center;

      &-btn {
        border-radius: .7rem;
        box-shadow: inset 0 0 1px 1px #ffffff50;
        color: #fff;
        font-family: 'Inter';
        font-weight: 700;
        font-size: 15px;
        letter-spacing: 0px;
        width: 100%;
        padding: .8rem 0;
        background: #8143FC80;
        transition: all 100ms ease-in-out;

        &:active {
          scale: 0.95;
          opacity: 0.8;
        }
      }

      &-pannel {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #08150A80;
        border-radius: 1.2rem;
        border: 1px solid #ffffff50;
        gap: .5rem;
        margin: .2rem 0 0.5rem;
        padding: 0.2rem 0rem;

        img {
          max-width: 70px;
          margin-left: 15%;
        }

        .own-asic-info {
          display: flex;
          width: 100%;
          flex-direction: column;
          gap: 0;
          justify-content: center;
          align-items: start;

          &-title {
            color: #8143FC;
            font-family: 'Inter';
            font-weight: 700;
            font-size: 15px;
            letter-spacing: 0px;
          }

          &-desc {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: start;

            .will-mine,
            .will-take {
              color: #ffffff80;
              font-family: 'Inter';
              font-weight: 400;
              font-size: 12px;
              line-height: 15px;
              letter-spacing: 0px;

              label {
                font-weight: 500;
                color: #ffffff;
              }
            }
          }
        }
      }
    }

    .rent-period,
    .rent-profit {
      display: flex;
      flex-direction: column;
      margin: .5rem 1rem;

      &-text {
        color: #fff;
        font-family: 'Inter';
        font-weight: 400;
        font-size: 11px;
        letter-spacing: 0px;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
    }

    .rent-btn {
      position: relative;
      color: #212121;
      font-family: 'Inter';
      font-size: 15px;
      font-weight: 700;
      padding: .8rem 0;
      border-radius: .7rem;
      width: 100%;
      background: linear-gradient(to bottom, #FCD909, #FEA400);
      transition: all 100ms ease-in-out;

      &:active {
        scale: 0.95;
        opacity: 0.8;
      }

      &:disabled {
        opacity: 0.5;
      }
    }
  }
}

.back-btn {
  margin-top: 8px;
  width: 100%;
  height: 48px;
  padding: 10px 0;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  border: 1px solid #8143fc;
  border-radius: 10px;
  color: #fff;
  font-family: 'Inter';
  font-weight: 600;
  font-size: clamp(14px, 4dvw, 18px);
  letter-spacing: 0px;
  transition: all 100ms ease;

  &:active {
    opacity: 0.5;
    scale: 0.95;
  }
}
</style>
