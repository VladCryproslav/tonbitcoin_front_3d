<script setup>
import { computed, defineAsyncComponent, nextTick, onBeforeMount, onMounted, onUnmounted, ref, watch } from 'vue';
import LineChart from './LineChart.vue';
import InfoIcon from '@/assets/info_icon.svg'
import asicsSheet from '@/services/data';
import InfoModal from './InfoModal.vue';
import { useTonAddress, useTonConnectUI } from '@townsquarelabs/ui-vue'
import { beginCell, toNano } from '@ton/core'
import SpecialPriceModal from './SpecialPriceModal.vue';
import RedirectModal from './RedirectModal.vue';
import { useAppStore } from '@/stores/app';
import { host } from '../../axios.config';
import { useI18n } from 'vue-i18n';
const Exit = defineAsyncComponent(() => import('@/assets/exit.svg'))

const props = defineProps({
  tab: String
})

let controller;
const app = useAppStore()
const ton_address = useTonAddress()
const isProcessing = ref(false)
const { tonConnectUI, setOptions } = useTonConnectUI()
const openRedirectModal = ref(false)
const openSpecialModal = ref(false)
const redirectLink = ref(null)
const currBuyAsic = ref(null)

const { t, locale } = useI18n()

const scrollView = ref(null)
const energizerOnScreen = ref(null)
const minerOnScreen = ref(null)
const investorOnScreen = ref(null)
const activeSection = ref('energizer')

const handleScroll = () => {
  if (!scrollView.value) return

  const sections = [
    { ref: energizerOnScreen, name: 'energizer' },
    { ref: minerOnScreen, name: 'miner' },
    { ref: investorOnScreen, name: 'investor' }
  ]

  const scrollTop = scrollView.value.scrollTop
  const containerHeight = scrollView.value.clientHeight

  // Знаходимо яка секція найбільше видима
  let maxVisibleSection = null
  let maxVisibleArea = 0

  sections.forEach(section => {
    if (section.ref.value) {
      const elementTop = section.ref.value.offsetTop - scrollView.value.offsetTop
      const elementHeight = section.ref.value.offsetHeight
      const elementBottom = elementTop + elementHeight

      // Обчислюємо видиму частину секції
      const visibleTop = Math.max(scrollTop, elementTop)
      const visibleBottom = Math.min(scrollTop + containerHeight, elementBottom)
      const visibleArea = Math.max(0, visibleBottom - visibleTop)

      // Якщо ця секція більше видима, оновлюємо активну
      if (visibleArea > maxVisibleArea) {
        maxVisibleArea = visibleArea
        maxVisibleSection = section.name
      }
    }
  })

  if (maxVisibleSection) {
    activeSection.value = maxVisibleSection
  }
}

// Throttle функція для оптимізації скролінга
let scrollTimeout = null
const throttledHandleScroll = () => {
  if (scrollTimeout) return

  scrollTimeout = setTimeout(() => {
    handleScroll()
    scrollTimeout = null
  }, 16) // ~60fps
}

const scrollToSection = async (sectionRef) => {
  await nextTick()

  if (sectionRef && scrollView.value) {
    sectionRef.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    })
  }
}

const currFilter = ref('all_time')
const timeout_id = ref(null)
const openInfoModal = ref(false)


const revealBuy = ref(null)

const setReveal = (asic) => {
  if (timeout_id.value) {
    clearTimeout(timeout_id.value)
    timeout_id.value = null
  }
  revealBuy.value = asic
  timeout_id.value = setTimeout(() => { revealBuy.value = null }, 5000)
}

const openModal = ref(false)
const modalStatus = ref('')
const modalTitle = ref('')
const modalBody = ref('')

const showModal = (status, title, body) => {
  modalStatus.value = status
  modalTitle.value = title
  modalBody.value = body
  openModal.value = true
}

const setFilter = (filter) => {
  if (currFilter.value == filter) {
    return
  } else {
    currFilter.value = filter
  }
}

// const scrollToTop = () => {
//   scrollView.value.scrollTo({ top: 0, behavior: 'smooth' });
// };

function formatNumber(value) {
  if (value >= 1000000) {
    return (value / 1000000).toFixed(3).replace(/\.?0+$/, '') + 'm';
  } else if (value >= 1000) {
    return (value / 1000).toFixed(3).replace(/\.?0+$/, '') + 'k';
  } else {
    return value.toString();
  }
}

const imagePathAsics = (asic) => {
  const com = computed(
    () => new URL(`../assets/asics/${asic?.toString().toUpperCase()}.webp`, import.meta.url).href,
  )
  return com
}

const allStations = [...new Set(app.stations?.storage_configs?.map((el) => el?.station_type))].slice(4)

const imagePath = (val) => {
  const res = computed(() => {
    return new URL(`../assets/${val}-3.webp`, import.meta.url).href
  })
  return res.value
}

const buyAsics = async (item, price, link, sale) => {
  if (sale) {
    currBuyAsic.value = asicsSheet[item]
    openSpecialModal.value = true
    return
  }
  if (link) {
    redirectLink.value = link
    openRedirectModal.value = true
    return
  }
  if (isProcessing.value) return
  isProcessing.value = true
  if (!ton_address.value) {
    showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }

  // Скидаємо стан модального вікна перед новою транзакцією
  try {
    await tonConnectUI.closeModal()
  } catch {
    // Ігноруємо помилки закриття модального вікна
  }

  const mainCell = beginCell().storeUint(1, 32).storeUint(1, 64).storeUint(+item, 4).endCell()
  try {
    const transactionData = {
      validUntil: Math.floor(Date.now() / 1000) + 600,
      messages: [
        {
          address: 'EQAGKlyJq1BJ0h-ACkt9fNH3OYpNZNhcg8GxVvLw6ESy2C2n',
          amount: toNano(price + 0.1).toString(), // Convert BigInt to string
          payload: mainCell.toBoc().toString('base64'), // Convert mainCell to base64 string
        },
      ],
    }

    await tonConnectUI.sendTransaction(transactionData, {
      modals: ['before', 'success'],
      notifications: [],
    })
  } catch (err) {
    console.log(err)
    showModal('error', t('notification.st_error'), t('notification.failed_transaction'))
  } finally {
    isProcessing.value = false
  }
}

const fetchkwPerTbtc = async () => {
  controller = new AbortController();
  try {
    const response = await host.get('gecko/v2/networks/ton/pools/EQAlKqUCLVveQUakwzyyXl-mr1OvLNpkiI1LkjLDeIpfH74i/', { signal: controller.signal });
    app.setKwPerTbtc(+(+response?.data?.data?.attributes?.base_token_price_quote_token).toFixed(2) || 'N/A')
  } catch (err) {
    app.setKwPerTbtc('N/A')
    console.error(err);
  } finally {
    controller = null;
  }
}

const getSign = (value, side) => {
  if (side == 'energizer') {
    if (value >= 100000000000000 && value < 99900000000000) {
      return { num: +(value / 1000000000000000).toFixed(2), val: `${(value / 1000000000000000).toFixed(2)} eW/h`, sign: 'eW/h' };
    } else if (value >= 100000000000 && value < 99900000000000) {
      return { num: +(value / 1000000000000).toFixed(2), val: `${(value / 1000000000000).toFixed(2)} pW/h`, sign: 'pW/h' };
    } else if (value >= 100000000 && value < 99900000000) {
      return { num: +(value / 1000000000).toFixed(2), val: `${(value / 1000000000).toFixed(2)} tW/h`, sign: 'tW/h' };
    } else if (value >= 100000 && value < 99900000) {
      return { num: +(value / 1000000).toFixed(2), val: `${(value / 1000000).toFixed(2)} gW/h`, sign: 'gW/h' };
    } else if (value >= 100 && value < 99900) {
      return { num: +(value / 1000).toFixed(2), val: `${(value / 1000).toFixed(2)} mW/h`, sign: 'mW/h' };
    } else {
      return { num: +(value).toFixed(2), val: `${(value).toFixed(2)} kW/h`, sign: 'kW/h' };
    }
  }
  if (side == 'miner') {
    if (value >= 100000000 && value < 99900000000) {
      return { num: +(value / 1000000000).toFixed(2), val: `${(value / 1000000000).toFixed(2)} Eh/s`, sign: 'Eh/s' };
    } else if (value >= 100000 && value < 99900000) {
      return { num: +(value / 1000000).toFixed(2), val: `${(value / 1000000).toFixed(2)} Ph/s`, sign: 'Ph/s' };
    } else if (value >= 100 && value < 99900) {
      return { num: +(value / 1000).toFixed(2), val: `${(value / 1000).toFixed(2)} Th/s`, sign: 'Th/s' };
    } else if (value >= 0.1 && value < 99.9) {
      return { num: +(value).toFixed(2), val: `${(value).toFixed(2)} Gh/s`, sign: 'Gh/s' };
    } else if (value >= 0.0001 && value < 0.099) {
      return { num: +(value * 1000).toFixed(2), val: `${(value * 1000).toFixed(2)} Mh/s`, sign: 'Mh/s' };
    } else {
      return { num: +(value * 1000000).toFixed(2), val: `${(value * 1000000).toFixed(2)} h/s`, sign: 'h/s' };
    }
  }
  else {
    return '&#8734'
  }
};

const specialModalResponse = async (res) => {
  openSpecialModal.value = false
  if (res.check) {
    await buyAsics(
      asicsSheet.findIndex((el) => el.name == currBuyAsic.value.name),
      currBuyAsic.value?.price,
    )
  }
}

const emit = defineEmits(['close'])
const emitClose = () => {
  emit('close')
}
const checkScreen = (screen) => {
  switch (screen) {
    case 'energizer':
      scrollToSection(energizerOnScreen.value)
      break
    case 'miner':
      scrollToSection(minerOnScreen.value)
      break
    case 'investor':
      scrollToSection(investorOnScreen.value)
      break
    default:
      break
  }
}

function getPriceRange(stationType) {
  // Фільтруємо конфігурації за типом станції
  const stations = app?.stations?.storage_configs?.filter(config => config.station_type === stationType);

  // Знаходимо максимальні ненульові значення для min_ton_price і max_ton_price
  let minTonPrice = 0;
  let maxTonPrice = 0;

  stations.forEach(station => {
    if (station.min_ton_price > minTonPrice) {
      minTonPrice = station.min_ton_price;
    }
    if (station.max_ton_price > maxTonPrice) {
      maxTonPrice = station.max_ton_price;
    }
  });

  // Форматуємо результат
  return `${minTonPrice} - ${maxTonPrice}`;
}

async function fetchChart() {
  controller = new AbortController();
  try {
    await host.get(`all-charts-dashboard/?filter_type=${currFilter.value}`, { signal: controller.signal }).then((res) => {
      if (res.status == 200) {
        app.setDashboard(res.data)
      }
    })
  } catch (err) {
    console.log(err)
  } finally {
    controller = null
  }
}

onBeforeMount(() => {
  fetchChart()
})

// onMounted(() => {
//   fetchkwPerTbtc()
// })

onUnmounted(() => {
  if (controller) {
    controller.abort()
  }
})

watch(currFilter, async () => {
  await fetchChart()
}, { immediate: true })
</script>

<template>
  <RedirectModal v-if="openRedirectModal" :link="redirectLink" @close="openRedirectModal = false" />
  <SpecialPriceModal v-if="openSpecialModal" :saleAsic="currBuyAsic" @close="specialModalResponse" />
  <InfoModal v-if="openInfoModal" @close="openInfoModal = !openInfoModal">
    <template #modal-body>
      {{ t('dashboard.profit_modal') }}
    </template>
  </InfoModal>
  <div class="dashboard-modal"
    :class="{ energ: props.tab == 'energizer', mine: props.tab == 'miner', inv: props.tab == 'investor' }">
    <div class="top-panel">
      <div class="ton"></div>
      <h1>{{ t('general.top_nav.dashboard') }}</h1>
      <button class="close" @click="emitClose">
        <Exit :width="16" style="color: #fff" />
      </button>
    </div>
    <div id="firstFilter" class="filter-switch">
      <input :checked="activeSection == 'energizer'" @change="checkScreen('energizer')" id="option1" name="options"
        type="radio" />
      <label class="option" for="option1">{{ t('dashboard.main') }}</label>
      <input :checked="activeSection == 'miner'" @change="checkScreen('miner')" id="option2" name="options"
        type="radio" />
      <label class="option" for="option2">{{ t('dashboard.asics') }}</label>
      <input :checked="activeSection == 'investor'" @change="checkScreen('investor')" id="option3" name="options"
        type="radio" />
      <label class="option" for="option3">{{ t('dashboard.stations') }}</label>
      <span class="background"></span>
    </div>
    <div class="scrollable-area" ref="scrollView" @scroll="throttledHandleScroll">
      <div ref="energizerOnScreen" class="main-dash" data-section="energizer">
        <ul class="filters">
          <li class="sort-pill" :class="{ selected: currFilter !== null && currFilter == 'week' }"
            @click="setFilter('week')">{{ t('common.week') }}</li>
          <li class="sort-pill" :class="{ selected: currFilter !== null && currFilter == 'month' }"
            @click="setFilter('month')">{{ t('common.month') }}</li>
          <li class="sort-pill" :class="{ selected: currFilter !== null && currFilter == 'all_time' }"
            @click="setFilter('all_time')">{{ t('common.all_time') }}</li>
        </ul>
        <div class="charts">
          <div class="chart-item">
            <div class="chart-item-line">
              <LineChart :chart-config="{
                is_mine: false,
                symb: ` ${getSign(Math.max(...app?.dashboard?.station_power?.map(el => el.value)), 'energizer').sign}`,
                data: app?.dashboard?.station_power?.map(el => ({ ...el, value: getSign(el.value, 'energizer').num }))
              }" />
            </div>
            <div class="chart-item-info">
              <span class="chart-item-info-title">{{ t('dashboard.curr_gen_energy') }}</span>
              <h1 class="chart-item-info-value"> {{
                getSign(app?.dashboard?.station_power?.[app?.dashboard?.station_power?.length - 1]?.value || 0,
                  'energizer').val }}
              </h1>
            </div>
          </div>
          <div class="chart-item">
            <div class="chart-item-line">
              <LineChart :chart-config="{
                is_mine: true,
                symb: ` ${getSign(app?.dashboard?.network_hashrate?.[app?.dashboard?.network_hashrate?.length - 1]?.value || 0, 'miner').sign}`,
                data: app?.dashboard?.network_hashrate?.map(el => ({ ...el, value: getSign(el.value, 'miner').num }))
              }" />
            </div>
            <div class="chart-item-info">
              <span class="chart-item-info-title">{{ t('dashboard.hashrate') }}</span>
              <h1 class="chart-item-info-value">{{
                getSign(app?.dashboard?.network_hashrate?.[app?.dashboard?.network_hashrate?.length - 1]?.value || 0,
                  'miner').val }}
              </h1>
            </div>
          </div>
          <!-- <div class="chart-item">
            <div class="chart-item-line">
              <LineChart :chart-config="{
                is_mine: false,
                symb: '',
                data: app?.dashboard?.active_stations
              }" />
            </div>
            <div class="chart-item-info">
              <span class="chart-item-info-title">Активные электростанции</span>
              <h1 class="chart-item-info-value">{{
                app?.dashboard?.active_stations?.[app?.dashboard?.active_stations?.length - 1]?.value || 0 }}</h1>
            </div>
          </div> -->
          <!-- <div class="chart-item">
            <div class="chart-item-line">
              <LineChart :chart-config="{
                is_mine: true,
                symb: '',
                data: app?.dashboard?.active_asics
              }" />
            </div>
            <div class="chart-item-info">
              <span class="chart-item-info-title">Активные ASICs</span>
              <h1 class="chart-item-info-value">{{
                app?.dashboard?.active_asics?.[app?.dashboard?.active_asics?.length - 1]?.value || 0 }}</h1>
            </div>
          </div> -->
          <div class="chart-item">
            <div class="chart-item-line">
              <LineChart :chart-config="{
                is_mine: false,
                symb: ' $',
                data: app?.dashboard?.kw_price
              }" />
            </div>
            <div class="chart-item-info">
              <span class="chart-item-info-title">{{ t('dashboard.price_kw') }}{{ currFilter == 'week' ?
                t('common.per_week')
                :
                currFilter == 'month'
                  ?
                  t('common.per_month') : t('common.per_all') }}</span>
              <h1 class="chart-item-info-value">{{
                +(app?.dashboard?.kw_price?.[app?.dashboard?.kw_price?.length - 1]?.value)?.toFixed(4) || 0 }} $
                <span>{{ locale == 'en' ? 'per' : 'за' }}
                  1000
                  kW</span>
              </h1>
            </div>
          </div>
          <div class="chart-item">
            <div class="chart-item-line">
              <LineChart :chart-config="{
                is_mine: true,
                symb: ' $',
                data: app?.dashboard?.tbtc_price
              }" />
            </div>
            <div class="chart-item-info">
              <span class="chart-item-info-title">{{ t('dashboard.price_fbtc') }}{{ currFilter == 'week' ?
                t('common.per_week') :
                currFilter ==
                  'month'
                  ?
                  t('common.per_month') : t('common.per_all') }}</span>
              <h1 class="chart-item-info-value">{{
                +(app?.dashboard?.tbtc_price?.[app?.dashboard?.tbtc_price?.length - 1]?.value)?.toFixed(4) || 0 }} $
              </h1>
            </div>
          </div>
        </div>
        <div class="row-data">
          <div class="row-data-item">
            <span class="row-data-item-title">{{ t('dashboard.mined_kw') }}{{ currFilter == 'week' ?
              t('common.per_week')
              :
              currFilter
                ==
                'month' ?
                t('common.per_month') : t('common.per_all') }}</span>
            <h1 class="row-data-item-value">{{ +(app?.dashboard?.kw_mined?.[app?.dashboard?.kw_mined?.length -
              1]?.value)?.toFixed(2) || 0
            }} kW</h1>
          </div>
          <div class="row-data-item">
            <span class="row-data-item-title">{{ t('dashboard.mined_fbtc') }} {{ currFilter == 'week' ?
              t('common.per_week') : currFilter
                == 'month'
                ?
                t('common.per_month') : t('common.per_all') }}</span>
            <h1 class="row-data-item-value">{{ +(app?.dashboard?.tbtc_mined?.[app?.dashboard?.tbtc_mined?.length -
              1]?.value)?.toFixed(4) || 0
            }} fBTC</h1>
          </div>
          <!-- <div class="row-data-item">
            <span class="row-data-item-title">Количество kW на 1 fBTC</span>
            <h1 class="row-data-item-value">{{ app?.kwPerTbtc }} kW <span>на 1 fBTC</span></h1>
          </div> -->
          <div class="row-data-item">
            <span class="row-data-item-title">{{ t('dashboard.all_burned_kw') }}</span>
            <h1 class="row-data-item-value">{{ +(app?.dashboard?.energy_burned?.[app?.dashboard?.energy_burned?.length -
              1]?.value)?.toFixed(2) || 0
            }} kW</h1>
          </div>
          <div class="row-data-item">
            <span class="row-data-item-title">{{ t('dashboard.lost_mined') }}</span>
            <h1 class="row-data-item-value">{{ +(app?.dashboard?.tbtc_remaining?.[app?.dashboard?.tbtc_remaining?.length
              -
              1]?.value)?.toFixed(4) || 0
              }} fBTC</h1>
          </div>
          <div class="row-data-item">
            <span class="row-data-item-title">{{ t('dashboard.fbtc_staking') }}</span>
            <h1 class="row-data-item-value">{{ +(app?.dashboard?.tbtc_staked?.[app?.dashboard?.tbtc_staked?.length -
              1]?.value)?.toFixed(4) || 0
            }} fBTC</h1>
          </div>
        </div>
      </div>
      <div ref="minerOnScreen" class="asics-dash" data-section="miner">
        <h2 class="asics-dash-title">ASICs</h2>
        <div class="asics-dash-list">
          <div v-for="item, index in asicsSheet.filter(el => el.shop)" class="asics-dash-list-item" :key="index">
            <div class="left-side">
              <div v-if="revealBuy == item?.name" class="asic-buy">
                <div class="asic-buy-price">
                  <span class="asic-buy-price-value">{{ item.price }}</span>
                  <img src="@/assets/TON.png" width="16px" height="16px" alt="" />
                </div>
                <button class="asic-buy-btn" @click="buyAsics(index, item?.price, item?.link, item?.sale)" :disabled="item?.sold_out">
                  <h1 class="asic-buy-btn-text">{{ item?.sold_out ? t('common.sold_out') : t('common.buy') }}</h1>
                  <img src="@/assets/shopping_cart.png" width="12px" />
                </button>
              </div>
              <img class="asic-image" :class="{ fading: revealBuy == item?.name }"
                :src="imagePathAsics(item?.name).value" alt="" />
              <p class="asic-title">{{ item?.name }}</p>
              <button v-if="revealBuy !== item?.name && !item?.sold_out" class="buy-reveal" @click="setReveal(item?.name)">
                <img src="@/assets/buy-reveal.png" alt="" />
              </button>
            </div>
            <div class="right-side">
              <div class="stat-grouping">
                <span class="stat-grouping-title">{{ t('dashboard.energy_cons') }}</span>
                <h1 class="stat-grouping-value">{{ +(item.consumption * 24 * 30 / (item.speed * 30)).toFixed(1) }} kW
                </h1>
              </div>
              <div class="stat-grouping">
                <span class="stat-grouping-title">{{ t('dashboard.same_cost') }}</span>
                <h1 class="stat-grouping-value">{{+((item.consumption * 24 * 30 / (item.speed * 30)) *
                  app?.stonfi_kw).toFixed(5) }}$</h1>
              </div>
              <div class="stat-grouping">
                <span class="stat-grouping-title">{{ t('dashboard.apr') }}
                  <InfoIcon @click="openInfoModal = true" class="stat-grouping-info" />
                </span>
                <h1 class="stat-grouping-value">{{ item.apr }}%</h1>
                <!-- <h1 class="stat-grouping-value">{{ Math.ceil(item?.speed * 365 * 0.17 / (item?.price * app.prices?.['TON']) * 100) || 0 }}%</h1> -->
              </div>
            </div>
          </div>
        </div>
      </div>
      <div ref="investorOnScreen" class="stations-dash" data-section="investor">
        <h2 class="stations-dash-title">{{ t('dashboard.stations_nft') }}</h2>
        <div class="stations-dash-list">
          <div v-for="item, index in allStations" class="stations-dash-list-item" :key="index">
            <div class="left-side">
              <img class="station-image" :src="imagePath(item)" alt="" />
              <p class="station-title">{{ t(`stations.${item}`) }}</p>
            </div>
            <div class="right-side">
              <div class="stat-grouping">
                <span class="stat-grouping-title">{{ t('dashboard.mine_kw_per_month') }}</span>
                <h1 class="stat-grouping-value">
                  <!-- {{
                formatNumber(app?.gen_config?.find(el => el.station_type == item &&
                  el.level ==
                  1)?.generation_rate * 24 * 30)}}
                  kW -  -->
                  {{ t('common.to') }} {{formatNumber(app?.gen_config?.find(el => el.station_type == item && el.level ==
                    3)?.generation_rate * 24 * 30)}} kW
                </h1>
              </div>
              <div class="stat-grouping">
                <span class="stat-grouping-title">{{ t('dashboard.your_earn') }}</span>
                <h1 class="stat-grouping-value">
                  <!--  {{+(app?.gen_config?.find(el => el.station_type == item && el.level ==
                  1)?.generation_rate * 24 * 30 * app?.stonfi_kw).toFixed(2)}}$ - -->
                  {{ t('common.to') }} {{+(app?.gen_config?.find(el =>
                    el.station_type == item && el.level ==
                    3)?.generation_rate * 24 * 30 * app?.stonfi_kw).toFixed(2)}}$
                </h1>
              </div>
              <div class="stat-grouping">
                <span class="stat-grouping-title">{{ t('dashboard.around_cost') }}</span>
                <h1 class="stat-grouping-value">{{ getPriceRange(item) }}<img src="@/assets/TON.png" width="18px"
                    aly="" />
                </h1>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.dashboard-modal {
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
  border-top: 1px solid #ffffff50;

  &.energ {
    background:
      radial-gradient(ellipse 60% 40% at top center, #31CFFF80, transparent),
      #141E36;
  }

  &.mine {
    background:
      radial-gradient(ellipse 60% 40% at top center, #31ff8080, transparent),
      #08150a;
  }

  &.inv {
    background:
      radial-gradient(ellipse 60% 40% at top center, #8143FC80, transparent),
      #1B1436;
  }



  .top-panel {
    display: flex;
    width: 90%;
    padding: 1rem 0;
    align-items: center;

    .ton {
      display: flex;
      align-items: center;
      min-width: 70px;
      gap: 0.3rem;
      background: linear-gradient(to right, transparent, #00000050);
      border-radius: 1rem;

      .amount {
        color: #fff;
        width: max-content;
        font-family: 'Inter' !important;
        font-weight: 600;
        font-size: 13px;
        padding: 0 0.5rem 0 0;
      }
    }

    h1 {
      text-align: center;
      color: #fff;
      max-width: 100%;
      width: 100%;
      font-family: 'Inter' !important;
      font-weight: 600;
      font-size: 28px;
    }

    .close {
      width: 20%;
      display: flex;
      align-items: center;
      justify-content: end;
    }
  }

  .filter-switch {
    background-color: #00000080;
    border-radius: 30px;
    position: relative;
    display: flex;
    align-items: center;
    height: 30px;
    min-height: 30px;
    width: 65%;
    overflow: hidden;

    input {
      display: none;
    }

    label {
      flex: 1;
      text-align: center;
      cursor: pointer;
      border: none;
      border-radius: 30px;
      position: relative;
      overflow: hidden;
      z-index: 1;
      transition: all 0.5s;
      font-family: 'Inter';
      font-weight: 600;
      letter-spacing: 0px;
      font-size: 13px;
    }

    .background {
      position: absolute;
      width: 33.33%;
      height: 30px;
      min-height: 30px;
      background: linear-gradient(to bottom, #FFFFFF, #9B9B9b);
      top: 0;
      left: 0;
      border-radius: 30px;
      transition: left 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
  }

  #option2:checked~.background {
    left: 33.33%;
  }

  #option3:checked~.background {
    left: 66.66%;
  }

  #option1:checked+label[for="option1"] {
    color: #000;
    font-weight: bold;
  }

  #option2:checked+label[for="option2"] {
    color: #000;
    font-weight: bold;
  }

  #option3:checked+label[for="option3"] {
    color: #000;
    font-weight: bold;
  }

  #option1:not(:checked)+label[for="option1"],
  #option2:not(:checked)+label[for="option2"],
  #option3:not(:checked)+label[for="option3"] {
    color: #fff;
  }

  .scrollable-area {
    width: 90%;
    height: 100%;
    padding-bottom: 140px;
    margin-top: 1rem;
    overflow-y: scroll;
    -ms-overflow-style: none;
    scrollbar-width: none;
    border-radius: .5rem;

    &::-webkit-scrollbar {
      display: none;
      /* Safari and Chrome */
    }

    .main-dash {
      width: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      gap: 1rem;
      margin-bottom: 1rem;

      .filters {
        width: 100%;
        display: flex;
        justify-content: center;
        gap: 1rem;
        align-items: center;
        padding: 0;

        .sort-pill {
          padding: 0.3rem 0.2rem;
          display: flex;
          justify-content: center;
          align-items: center;
          border-radius: .7rem;
          font-family: 'Inter' !important;
          font-weight: 400;
          font-size: 11px;
          color: #fff;
          width: 100%;
          min-width: max-content;
          border: 1px solid #ffffff25;
          transition: all .2s ease-in-out;

          &:active {
            scale: 0.95;
            opacity: 0.7;
          }

          &.selected {
            background: #58585850;
            border: 1px solid #ffffff;
          }
        }
      }

      .charts {
        width: 100%;
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: .5rem;
      }


      .chart-item {
        width: 100%;
        overflow: hidden;
        aspect-ratio: 1/1;
        position: relative;
        border-radius: 1rem;
        border: 1px solid #ffffff1A;

        &-line {
          height: calc(100% - 50px);
          background: #0F1B11;
        }

        &-info {
          position: absolute;
          left: 0;
          bottom: 0;
          display: flex;
          flex-direction: column;
          align-items: start;
          justify-content: center;
          background: #08150A80;
          width: 100%;
          padding: .2rem .5rem;
          border-top: 1px solid #ffffff1A;

          &-title {
            color: #ffffff80;
            font-family: 'Inter' !important;
            font-weight: 400;
            font-size: 11px;
          }

          &-value {
            color: #ffffff;
            font-family: 'Inter' !important;
            font-weight: 700;
            font-size: 16px;

            >span {
              color: #ffffff80;
              font-family: 'Inter' !important;
              font-weight: 400;
              font-size: 11px;
            }
          }
        }
      }

      .row-data {
        width: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: .25rem;

        &-item {
          width: 100%;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: start;
          padding: 8px 20px;
          border-radius: 1rem;
          border: 1px solid #ffffff1A;
          background: #08150A80;

          &-title {
            color: #ffffff80;
            font-family: 'Inter' !important;
            font-weight: 400;
            font-size: 11px;
          }

          &-value {
            color: #ffffff;
            font-family: 'Inter' !important;
            font-weight: 700;
            font-size: 16px;
            line-height: 20px;

            >span {
              color: #ffffff80;
              font-family: 'Inter' !important;
              font-weight: 400;
              font-size: 11px;
            }
          }
        }
      }
    }

    .asics-dash {
      width: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      gap: 1rem;
      margin-bottom: 1rem;

      &-title {
        text-align: center;
        color: #fff;
        max-width: 100%;
        width: 100%;
        font-family: 'Inter' !important;
        font-weight: 600;
        font-size: 20px;
        letter-spacing: 0;
      }

      &-list {
        width: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: 1rem;

        &-item {
          width: 100%;
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 1.5rem;
          background: #08150A80;
          padding: .7rem .7rem;
          border-radius: 1rem;
          border: 1px solid #ffffff1a;

          .left-side {
            position: relative;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-width: 35%;
            width: 35%;

            .asic-buy {
              position: absolute;
              z-index: 10;
              top: 40%;
              left: 50%;
              transform: translate(-50%, -50%);
              display: flex;
              flex-direction: column;
              align-items: center;
              justify-content: center;
              gap: .25rem;

              &-price {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 3px;

                &-value {
                  color: #ffffff;
                  font-family: 'Inter' !important;
                  font-weight: 600;
                  font-size: 14px;
                  letter-spacing: 0;
                  // line-height: 1px;
                }
              }

              &-btn {
                display: flex;
                align-items: center;
                justify-content: center;
                background: #1a1a1acc;
                border-radius: 1rem;
                border: 1px solid #FCD909;
                padding: .2rem 1rem .2rem 1.2rem;
                gap: .2rem;
                transition: all 100ms ease-in-out;

                &:active {
                  scale: 0.9;
                  opacity: 0.7;
                }

                &-text {
                  color: #ffffff;
                  font-family: 'Inter' !important;
                  font-weight: 700;
                  font-size: 12px;
                  letter-spacing: 0;
                }
              }
            }

            .asic-image {
              width: 90px;
              height: auto;
              transition: all 100ms ease-in-out;

              &.fading {
                filter: brightness(0.3);
              }
            }

            .asic-title {
              text-align: center;
              color: #fff;
              max-width: 100%;
              width: 100%;
              font-family: 'Inter' !important;
              font-weight: 600;
              font-size: 13px;
              letter-spacing: 0;
            }

            .buy-reveal {
              position: absolute;
              right: 0;
              top: calc(90px - 25px);
              width: 22px;
              transition: all 100ms ease-in-out;

              &:active {
                scale: 0.9;
                opacity: 0.7;
              }
            }
          }

          .right-side {
            position: relative;
            width: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: start;
            gap: .5rem;

            .stat-grouping {
              display: flex;
              flex-direction: column;
              gap: 0;

              &-title {
                position: relative;
                color: #ffffff80;
                font-family: 'Inter' !important;
                font-weight: 400;
                font-size: 11px;
              }

              &-value {
                color: #ffffff;
                font-family: 'Inter' !important;
                font-weight: 700;
                font-size: 16px;
                line-height: 18px;
              }

              &-info {
                position: absolute;
                right: -1rem;
                top: -.5rem;
                width: 14px;
                transition: all 100ms ease-in-out;

                &:active {
                  opacity: 0.7;
                  scale: 0.9;
                }
              }
            }
          }
        }
      }
    }

    .stations-dash {
      width: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      gap: 1rem;

      &-title {
        text-align: center;
        color: #fff;
        max-width: 100%;
        width: 100%;
        font-family: 'Inter' !important;
        font-weight: 600;
        font-size: 20px;
        letter-spacing: 0;
      }

      &-list {
        width: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: 1rem;

        &-item {
          width: 100%;
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 1.5rem;
          background: #08150A80;
          padding: .7rem .7rem;
          border-radius: 1rem;
          border: 1px solid #ffffff1a;

          .left-side {
            position: relative;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-width: 35%;
            width: 35%;

            .station-image {
              width: 90px;
              height: auto;
              transition: all 100ms ease-in-out;
            }

            .station-title {
              text-align: center;
              color: #fff;
              max-width: 100%;
              width: 100%;
              font-family: 'Inter' !important;
              font-weight: 600;
              font-size: 13px;
              letter-spacing: 0;
            }
          }

          .right-side {
            position: relative;
            width: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: start;
            gap: .5rem;

            .stat-grouping {
              display: flex;
              flex-direction: column;
              gap: 0;

              &-title {
                position: relative;
                color: #ffffff80;
                font-family: 'Inter' !important;
                font-weight: 400;
                font-size: 11px;
              }

              &-value {
                color: #ffffff;
                font-family: 'Inter' !important;
                display: flex;
                justify-self: center;
                align-items: center;
                gap: .25rem;
                font-weight: 700;
                font-size: 16px;
                line-height: 18px;
              }

              &-info {
                position: absolute;
                right: -1rem;
                top: -.5rem;
                width: 14px;
                transition: all 100ms ease-in-out;

                &:active {
                  opacity: 0.7;
                  scale: 0.9;
                }
              }
            }
          }
        }
      }
    }
  }
}
</style>
