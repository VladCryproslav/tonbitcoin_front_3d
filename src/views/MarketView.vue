<script setup>
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref } from 'vue'
const DeDust = defineAsyncComponent(() => import('@/assets/dedust.svg'))
const Stonfi = defineAsyncComponent(() => import('@/assets/stonfi.svg'))
const Exit = defineAsyncComponent(() => import('@/assets/exit.svg'))
import { useTelegram } from '@/services/telegram'
import axios from 'axios'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import { useTonAddress, useTonConnectUI } from '@townsquarelabs/ui-vue'
import { beginCell, toNano } from '@ton/core'
import InfoModal from '@/components/InfoModal.vue'
import ModalNew from '@/components/ModalNew.vue'
import RedirectModal from '@/components/RedirectModal.vue'
import SpecialPriceModal from '@/components/SpecialPriceModal.vue'
import { gemsSheet, gemsSaleActive, gemsSalePercent, getGemPrice, sortGemsBySale, asicsSheet, asicsSalePercent, getAsicPrice, isAsicInSale } from '@/services/data'
import { useScreen } from '@/composables/useScreen'

const app = useAppStore()
const { tg } = useTelegram()
const { t } = useI18n()
const { width } = useScreen()
const ton_address = useTonAddress()
const { tonConnectUI } = useTonConnectUI()

const showAsicsShop = ref(false)
const showPowerPlantsShop = ref(false)
const showBoostersShop = ref(false)

const openRedirectModal = ref(false)
const redirectLink = ref(null)
const redirectItemName = ref(null)
const redirectItemClass = ref(null)
const openSpecialModal = ref(false)
const currBuyAsic = ref(null)

const daoGem = computed(() => gemsSheet.find(g => g.type === 'DAO Owner'))
const starterPack = computed(() => gemsSheet.find(g => g.type === 'Starter Pack'))
const openStarterPackInfo = ref(false)
const openDaoOwnerInfo = ref(false)
const openHydroelectricInfo = ref(false)
const openOrbitalInfo = ref(false)
const openOrbitalCraftInfo = ref(false)
const openGemInfo = ref(false)
const gemInfoText = ref('')
const currentGemItem = ref(null)
const isProcessing = ref(false)
const openModal = ref(false)
const modalStatus = ref('')
const modalTitle = ref('')
const modalBody = ref('')

const getStarterPackPriceDisplay = () => {
  if (!starterPack.value) return 0
  return gemsSaleActive && starterPack.value.enableSale !== false
    ? getGemPrice(starterPack.value)
    : starterPack.value.price
}

/** Как в MinerView: для отображения цены в модалке (округление до десятых) */
const getStarterPackPrice = () => {
  if (!starterPack.value) return 99
  if (gemsSaleActive && starterPack.value.enableSale !== false) {
    const discountedPrice = getGemPrice(starterPack.value)
    return Math.round(discountedPrice * 10) / 10
  }
  return starterPack.value.price
}

const showModal = (status, title, body) => {
  modalStatus.value = status
  modalTitle.value = title
  modalBody.value = body
  openModal.value = true
}

const buyStarterPack = () => {
  if (starterPack.value) buyGem(starterPack.value)
  openStarterPackInfo.value = false
}

const handleGemInfoClick = (gemItem) => {
  if (gemItem?.info === 'hydroelectric_power_plant_modal') {
    openHydroelectricInfo.value = true
  } else if (gemItem?.info === 'orbital_power_plant_modal') {
    openOrbitalInfo.value = true
  } else if (gemItem?.info) {
    gemInfoText.value = gemItem.info
    currentGemItem.value = gemItem
    openGemInfo.value = true
  }
}

const buyHydroelectric = () => {
  const hydroelectric = gemsSheet.find(gem => gem.type === 'Hydroelectric Power Plant')
  if (hydroelectric) buyGem(hydroelectric)
  openHydroelectricInfo.value = false
}

const buyCurrentGem = () => {
  if (currentGemItem.value) buyGem(currentGemItem.value)
  openGemInfo.value = false
}

const buyHydroelectricFromCraft = () => {
  openOrbitalCraftInfo.value = false
  setTimeout(() => buyHydroelectric(), 300)
}

const orbitalGem = computed(() => gemsSheet.find(g => g.type === 'Orbital Power Plant'))

const closeOrbitalInfo = () => {
  openOrbitalInfo.value = false
}

const buyOrbital = () => {
  if (orbitalGem.value) buyGem(orbitalGem.value)
  openOrbitalInfo.value = false
}

const copyAddress = async (address) => {
  await navigator.clipboard.writeText(address)
  showModal('success', t('notification.st_success'), t('notification.address_copied'))
}

const openAsicsShop = () => { showAsicsShop.value = true }
const openBoostersShop = () => { showBoostersShop.value = true }
const openPowerPlantsShop = () => { showPowerPlantsShop.value = true }
const closeAsicsShop = () => { showAsicsShop.value = false }
const closePowerPlantsShop = () => { showPowerPlantsShop.value = false }
const closeBoostersShop = () => { showBoostersShop.value = false }

const POWER_PLANT_TYPES = ['Hydroelectric Power Plant', 'Orbital Power Plant', 'Singularity Reactor']
const BOOSTER_TYPES = ['Repair Kit', 'Jarvis Bot', 'Cryochamber', 'ASIC Manager', 'Magnetic ring']
const boostersCategory = ref('energizers') // 'energizers' | 'miners'
const powerPlantsGems = computed(() =>
  sortGemsBySale(gemsSheet.filter(el => el.shop && POWER_PLANT_TYPES.includes(el.type)))
)
const boostersGems = computed(() => {
  const base = gemsSheet.filter(el => el.shop && BOOSTER_TYPES.includes(el.type))
  const benefitsKey = boostersCategory.value === 'energizers' ? 'for_energizers' : 'for_miners'
  return sortGemsBySale(base.filter(el => el.benefits?.includes(benefitsKey)))
})

const STATION_LEVELS = ['Boiler house', 'Coal power plant', 'Thermal power plant', 'Geothermal power plant', 'Nuclear power plant', 'Thermonuclear power plant', 'Dyson Sphere', 'Neutron star', 'Antimatter', 'Galactic core']
const userStationLevel = computed(() => {
  if (!app.user?.station_type) return null
  let stationTypeToCheck = app.user.station_type
  if (app.user.premium_station_type) {
    const premiumMapping = { 'Hydroelectric Power Plant': 'Nuclear power plant', 'Orbital Power Plant': 'Thermonuclear power plant' }
    const mapped = premiumMapping[app.user.premium_station_type]
    if (mapped) stationTypeToCheck = mapped
  }
  const idx = STATION_LEVELS.indexOf(stationTypeToCheck)
  return idx === -1 ? null : idx + 1
})
const userHashrate = computed(() => {
  if (app.user?.mining_farm_speed == null) return null
  return app.user.mining_farm_speed
})
const checkPowerPlantLevelMatch = (benefit) => {
  if (!benefit || typeof benefit !== 'string') return false
  if (!benefit.includes('power_plant_lvl:')) return false
  if (userStationLevel.value === null) return false
  const match = benefit.match(/power_plant_lvl:\s*(\d+)-(\d+)/)
  if (!match) return false
  const minLevel = parseInt(match[1])
  const maxLevel = parseInt(match[2])
  return userStationLevel.value >= minLevel && userStationLevel.value <= maxLevel
}
const checkHashrateMatch = (benefit) => {
  if (!benefit || typeof benefit !== 'string') return false
  if (!benefit.includes('gh_s:')) return false
  if (userHashrate.value === null) return false
  const plusMatch = benefit.match(/gh_s:\s*(\d+)\+/)
  if (plusMatch) return userHashrate.value >= parseFloat(plusMatch[1])
  const rangeMatch = benefit.match(/gh_s:\s*(\d+)-(\d+)/)
  if (rangeMatch) {
    const minH = parseFloat(rangeMatch[1])
    const maxH = parseFloat(rangeMatch[2])
    return userHashrate.value >= minH && userHashrate.value <= maxH
  }
  return false
}

const imagePathAsics = (asic) =>
  computed(() => new URL(`../assets/asics/${asic?.toString().toUpperCase()}.webp`, import.meta.url).href)
const imagePathGems = (path) => {
  if (!path) return computed(() => '')
  const fileName = (path || '').replace('@/assets/gems/', '')
  return computed(() => new URL(`../assets/gems/${fileName}`, import.meta.url).href)
}

const specialModalResponse = async (res) => {
  openSpecialModal.value = false
  if (res?.check && currBuyAsic.value) {
    const asicIndex = asicsSheet.findIndex(el => el.name === currBuyAsic.value.name)
    const asicItem = asicsSheet[asicIndex]
    const finalPrice = asicItem?.price
    await buyAsics(asicIndex, finalPrice, asicItem?.link, false, asicItem?.shop)
  }
}

const buyAsics = async (item, price, link, sale, shop = true) => {
  if (!shop) return
  if (link) {
    redirectLink.value = link
    redirectItemName.value = asicsSheet[item]?.name || null
    redirectItemClass.value = null
    openRedirectModal.value = true
    return
  }
  if (sale) {
    currBuyAsic.value = {
      ...asicsSheet[item],
      new_price: getAsicPrice(asicsSheet[item]),
      perc: asicsSalePercent
    }
    openSpecialModal.value = true
    return
  }
  if (isProcessing.value) return
  isProcessing.value = true
  if (!ton_address.value) {
    openModal.value = true
    modalStatus.value = 'warning'
    modalTitle.value = t('notification.st_attention')
    modalBody.value = t('notification.unconnected')
    isProcessing.value = false
    return
  }
  try {
    const mainCell = beginCell()
      .storeUint(1, 32)
      .storeUint(1, 64)
      .storeUint(+item, 4)
      .endCell()
    const transactionData = {
      validUntil: Math.floor(Date.now() / 1000) + 600,
      messages: [{
        address: 'EQAGKlyJq1BJ0h-ACkt9fNH3OYpNZNhcg8GxVvLw6ESy2C2n',
        amount: toNano(price + 0.1).toString(),
        payload: mainCell.toBoc().toString('base64'),
      }],
    }
    await tonConnectUI.sendTransaction(transactionData, { modals: ['before', 'success'], notifications: [] })
    await app.initUser()
  } catch (err) {
    console.error(err)
  } finally {
    isProcessing.value = false
  }
}

const buyGem = async (gemItem) => {
  if (!gemItem?.shop && gemItem?.type !== 'Starter Pack') return

  // Starter Pack — как в MinerView: отправка TON
  if (gemItem?.type === 'Starter Pack') {
    if (isProcessing.value) return
    isProcessing.value = true
    if (!ton_address.value) {
      showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
      isProcessing.value = false
      return
    }
    try {
      await tonConnectUI.closeModal().catch(() => {})
    } catch { /* ignore */ }
    try {
      const transferAmount = gemsSaleActive && gemItem.enableSale !== false ? getGemPrice(gemItem) : gemItem.price
      const receiveAddress = 'UQDJMlSoT5-5CdCQROyN4SK_j0kMxpexF0Q3-boppeO7kZdl'
      const simplePayload = beginCell()
        .storeUint(0, 32)
        .storeUint(0, 64)
        .endCell()
      const transactionData = {
        validUntil: Date.now() + 1000 * 60 * 5,
        messages: [{
          address: receiveAddress,
          amount: toNano(transferAmount).toString(),
          payload: simplePayload.toBoc().toString('base64'),
        }],
      }
      const result = await tonConnectUI.sendTransaction(transactionData, {
        modals: ['before', 'success'],
        notifications: [],
      })
      if (result?.boc) {
        showModal('success', t('notification.st_success'), t('gems.starter_pack_price_offer', { price: transferAmount }))
        await app.initUser()
      }
    } catch (err) {
      console.error('buyGem Starter Pack:', err)
      showModal('error', t('notification.st_error'), t('notification.failed_transaction'))
    } finally {
      isProcessing.value = false
    }
    return
  }

  const link = gemItem?.link || 'https://getgems.io'
  redirectLink.value = link
  redirectItemName.value = gemItem?.type || gemItem?.name
  // Электростанции: бейдж по типу (как на карточках), не gems.special
  if (POWER_PLANT_TYPES.includes(gemItem?.type)) {
    redirectItemClass.value = gemItem?.type === 'Hydroelectric Power Plant' ? t('asic_shop.common') : gemItem?.type === 'Orbital Power Plant' ? t('asic_shop.rare') : t('asic_shop.epic')
  } else {
    redirectItemClass.value = (gemItem?.type !== 'DAO Owner' && gemItem?.rarity) ? t(`gems.${gemItem.rarity}`) : ''
  }
  openRedirectModal.value = true
}

const stonfiFBTCPrice = ref(0)
const stonfiKwPrice = ref(0)
let controller = null

const direct = (link) => {
  return link.includes('t.me') ? tg?.openTelegramLink(link) : tg?.openLink(link)
}

let intervalId

const fetchData = async () => {
  let controller1 = new AbortController()
  let controller2 = new AbortController()

  const promises = [
    // Первый запрос
    axios.get('https://api.ston.fi/v1/assets/EQBhF8jWase_Cn1dNTTe_3KMWQQzDbVw_lUUkvW5k6s61ikb', {
      signal: controller1.signal
    }),

    // Второй запрос
    axios.get('https://api.ston.fi/v1/assets/EQBOqBiArR45GUlifxdzZ40ZahdVhjtU7GjY-lVtqruHvQEc', {
      signal: controller2.signal
    })
  ]

  const results = await Promise.allSettled(promises)

  // Обработка результатов
  results.forEach((result, index) => {
    if (result.status === 'fulfilled') {
      switch (index) {
        case 0:
          stonfiKwPrice.value = result.value?.data?.asset?.dex_usd_price
          break
        case 1:
          stonfiFBTCPrice.value = result.value?.data?.asset?.dex_usd_price
          break
      }
    } else {
      console.error(`Ошибка в запросе ${index + 1}:`, result.reason)
    }
  })

  // Очистка контроллеров
  controller1 = null
  controller2 = null
}

const startInterval = () => {
  intervalId = setInterval(fetchData, 10000)
}

const stopInterval = () => {
  clearInterval(intervalId)
}

onMounted(() => {
  // window.addEventListener('focus', startInterval())
  // window.addEventListener('blur', stopInterval())
  fetchData()
  startInterval()
})

onUnmounted(() => {
  clearInterval(intervalId)
  window.removeEventListener('focus', startInterval())
  window.removeEventListener('blur', stopInterval())
  if (controller) {
    controller.abort()
  }
})
</script>

<template>
  <div v-if="!showAsicsShop && !showPowerPlantsShop && !showBoostersShop" class="screen-box">
    <h1 class="title">{{ t('market.title') }}</h1>

    <div class="market-grid">
      <div class="special-offers-header">
        <h2 class="special-offers-title">{{ t('market.limited_offers') }}</h2>
      </div>
      <!-- DAO first, then Starter Pack - both gem-item (gems shop style) -->
      <div v-if="daoGem" class="gem-item has-gold-stroke">
        <div class="gem-info-icon-top" @click="openDaoOwnerInfo = true">i</div>
        <div class="gem-picture">
          <img v-if="daoGem.imagePath" :src="imagePathGems(daoGem.imagePath)?.value" class="gem-image" alt="" />
          <div v-else class="gem-icon">💎</div>
        </div>
        <div class="gem-info">
          <span class="gem-type">{{ daoGem.type }}</span>
          <span v-for="(benefit, idx) in daoGem.benefits" :key="idx" class="gem-description">{{ t(`gems.${benefit}`) }}</span>
        </div>
        <button class="gem-buy-btn btn-gold" :disabled="isProcessing" @click="buyGem(daoGem)">
          <span>{{ daoGem.name || t('common.buy') }}</span>
          <span class="gem-price">
            <img src="@/assets/TON.png" width="14" height="14" alt="TON" />
            {{ daoGem.price }}
          </span>
        </button>
        <span class="gem-tag" style="background: linear-gradient(270deg, #FEA400 0%, #FCD909 100%); color: #000;">{{ t('gems.special') }}</span>
      </div>
      <div v-if="starterPack" class="gem-item has-purple-stroke">
        <div class="gem-info-icon-top" @click="openStarterPackInfo = true">i</div>
        <div class="gem-picture">
          <img v-if="starterPack.imagePath" :src="imagePathGems(starterPack.imagePath)?.value" class="gem-image" alt="Starter Pack" />
          <div v-else class="gem-icon">💎</div>
        </div>
        <div class="gem-info">
          <span class="gem-type">{{ starterPack.type }}</span>
          <span v-for="(benefit, idx) in starterPack.benefits" :key="idx" class="gem-description">{{ t(`gems.${benefit}`) }}</span>
        </div>
        <button class="gem-buy-btn btn-purple" :disabled="isProcessing" @click="buyGem(starterPack)">
          <span>{{ t('common.buy') }}</span>
          <span class="gem-price" :class="{ 'gem-saleprice': gemsSaleActive && starterPack.enableSale !== false }">
            <img src="@/assets/TON.png" width="14" height="14" alt="TON" />
            {{ starterPack.price }}
          </span>
          <template v-if="gemsSaleActive && starterPack.enableSale !== false">
            <div class="gem-sale-perc">-{{ starterPack.salePercent || 10 }}%</div>
            <div class="gem-sale-newprice">
              <img src="@/assets/TON.png" width="12" height="12" alt="TON" />
              {{ getStarterPackPriceDisplay() }}
            </div>
          </template>
        </button>
        <span class="gem-tag" style="background: linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(152, 81, 236, 1) 50%, rgba(94, 124, 234, 1) 100%);">{{ t('gems.special') }}</span>
      </div>

      <h2 class="section-title">{{ t('market.nft_assets') }}</h2>
      <div class="assets-item">
        <img src="@/assets/market/mining_equip_market_icon.webp" class="assets-icon" alt="" />
        <div class="assets-content">
          <h3 class="assets-item-title">{{ t('market.assets_mining_equipment') }}</h3>
          <p class="assets-item-desc">{{ t('market.assets_mining_equipment_desc') }}</p>
          <button class="assets-buy-btn" @click="openAsicsShop">{{ t('market.assets_buy_asics') }}</button>
        </div>
      </div>
      <div class="assets-item">
        <img src="@/assets/market/power_plant_market_icon.webp" class="assets-icon" alt="" />
        <div class="assets-content">
          <h3 class="assets-item-title">{{ t('market.assets_power_plants') }}</h3>
          <p class="assets-item-desc">{{ t('market.assets_power_plants_desc') }}</p>
          <button class="assets-buy-btn" @click="openPowerPlantsShop">{{ t('market.assets_buy_power_plant') }}</button>
        </div>
      </div>
      <div class="assets-item">
        <img src="@/assets/market/booster_market_icon.webp" class="assets-icon" alt="" />
        <div class="assets-content">
          <h3 class="assets-item-title">{{ t('market.assets_boosters') }}</h3>
          <p class="assets-item-desc">{{ t('market.assets_boosters_desc') }}</p>
          <button class="assets-buy-btn" @click="openBoostersShop">{{ t('market.assets_buy_boosters') }}</button>
        </div>
      </div>

      <h2 class="section-title tokens-title">{{ t('market.tokens') }}</h2>
      <div class="item">
        <span class="comm">{{ t('common.comming') }}</span>
        <div class="label-group" style="filter: blur(3px); opacity: 0.5">
          <span class="label-text">{{ t('market.rate', { pair: "kW/TON" }) }}
            <DeDust :width="14" /> DeDust
          </span>
        </div>
        <div class="price-group" style="filter: blur(3px); opacity: 0.5">
          <div class="indicator-row">
            <!-- <UpTrend /> -->
            <!-- <h3>${{ +(+dedustKWPrice * 1000)?.toFixed(6) || '0.000000' }}</h3> -->
            <h3>$0.0000</h3>
            <!-- <p>{{ t('market.per_k') }}</p> -->
          </div>
          <button class="trade-btn">
            {{ t('market.trade_btn') }}<img src="@/assets/kW_token.png" width="18px" height="18px" />
          </button>
        </div>
      </div>
      <div class="item">
        <div class="label-group">
          <span class="label-text">{{ t('market.rate', { pair: "kW/TON" }) }}
            <Stonfi :width="14" />Stonfi
          </span>
        </div>
        <div class="price-group">
          <div class="indicator-row" style="line-height: 22px;">
            <!-- <DownTrend /> -->
            <h3>${{ +(+stonfiKwPrice * 1000)?.toFixed(4) || +(+app?.stonfi_kw * 1000)?.toFixed(4) || '0.0000' }}</h3>
            <p>{{ t('market.per_k') }}</p>
          </div>
          <button class="trade-btn" @click="
            direct(
              'https://app.ston.fi/swap?chartVisible=true&ft=TON&tt=EQBhF8jWase_Cn1dNTTe_3KMWQQzDbVw_lUUkvW5k6s61ikb&chartInterval=1w',
            )
            ">{{ t('market.trade_btn') }}<img src="@/assets/kW_token.png" width="18px" height="18px" /></button>
        </div>
      </div>
      <div class="item">
        <div class="label-group">
          <span class="comm">{{ t('common.comming') }}</span>
          <span class="label-text" style="filter: blur(3px); opacity: 0.5">
            {{ t('market.rate', { pair: "tBTC/TON" }) }}
            <DeDust :width="14" /> DeDust
          </span>
        </div>
        <div class="price-group" style="filter: blur(3px); opacity: 0.5">
          <div class="indicator-row">
            <!-- <UpTrend /> -->
            <h3>$0.0000</h3>
          </div>
          <button class="trade-btn">
            {{ t('market.trade_btn') }}
            <img src="@/assets/TBTC.png" width="18px" height="18px" />
          </button>
        </div>
      </div>
      <div class="item">
        <div class="label-group">
          <span class="label-text">{{ t('market.rate', { pair: "fBTC/TON" }) }}
            <Stonfi :width="14" />Stonfi
          </span>
        </div>
        <div class="price-group">
          <div class="indicator-row">
            <!-- <UpTrend /> -->
            <h3>${{ +(+stonfiFBTCPrice)?.toFixed(4) || +(+app?.stonfi_fbtc)?.toFixed(4) || '0.0000' }}</h3>
          </div>
          <button class="trade-btn"
            @click="direct('https://app.ston.fi/swap?chartVisible=true&ft=TON&tt=EQBOqBiArR45GUlifxdzZ40ZahdVhjtU7GjY-lVtqruHvQEc&chartInterval=1w')">{{
              t('market.trade_btn') }} <img src="@/assets/fBTC.webp" width="18px" height="18px" /></button>
        </div>
      </div>
      <button class="view-btn" @click="
        direct(
          'https://www.geckoterminal.com/ton/pools/EQDRJ6wZJeaYYcR3FrqaShDgV2SyDtKBwoGI_wChiTrXL9mr',
        )
        ">
        {{ t('market.look_chart_btn', { pair: "fBTC/TON" }) }}
      </button>
      <button class="view-btn" @click="
        direct(
          'https://www.geckoterminal.com/ton/pools/EQAHxCJBgyH8aXBizy3zLnHfZPYBQ4DAlkVXYZ3yrKNHcrX2',
        )
        ">
        {{ t('market.look_chart_btn', { pair: "kW/TON" }) }}
      </button>
      <div class="item comming">
        <span>{{ t('market.more_dex') }}</span>
      </div>
      <button class="check-news" @click="direct('https://t.me/ton4btc')">{{ t('market.check_news_btn') }}</button>
    </div>
  </div>

  <InfoModal
    v-if="openStarterPackInfo"
    :confirm-label="t('common.buy')"
    @close="(e) => { if (e?.check) buyStarterPack(); openStarterPackInfo = false }"
  >
    <template #header>
      {{ t('asic_shop.information') }}
    </template>
    <template #modal-body>
      <div class="starter-pack-content">
        <div class="starter-pack-text">
          {{ t('gems.starter_pack_title') }}<br><br>
          • {{ t('gems.starter_pack_item_1') }}<br>
          • {{ t('gems.starter_pack_item_2') }}<br>
          • {{ t('gems.starter_pack_item_3') }}<br>
          • {{ t('gems.starter_pack_item_4') }}<br>
          • {{ t('gems.starter_pack_item_5') }}<br>
          • {{ t('gems.starter_pack_item_6') }}<br>
          • {{ t('gems.starter_pack_item_7') }}<br><br>
          {{ t('gems.starter_pack_price_info') }}<br>
          {{ t('gems.starter_pack_price_offer', { price: getStarterPackPrice() }) }}<br><br>
          <span style="color: #ffc300;">{{ t('gems.starter_pack_item_8') }}</span>
        </div>
      </div>
    </template>
  </InfoModal>

  <InfoModal
    v-if="openDaoOwnerInfo"
    :confirm-label="t('common.buy')"
    @close="(e) => { if (e?.check) buyGem(daoGem); openDaoOwnerInfo = false }"
  >
    <template #header>
      {{ t('asic_shop.information') }}
    </template>
    <template #modal-body>
      <div class="dao-owner-content">
        <div class="dao-owner-text">
          {{ t('gems.dao_owner_title') }}<br><br>
          • {{ t('gems.dao_owner_item_1') }}<br>
          • {{ t('gems.dao_owner_item_2') }}<br>
          • {{ t('gems.dao_owner_item_3') }}<br>
          • {{ t('gems.dao_owner_item_4') }}<br>
          • {{ t('gems.dao_owner_item_5') }}<br>
          • {{ t('gems.dao_owner_item_6') }}<br>
          • {{ t('gems.dao_owner_item_7') }}
        </div>
      </div>
    </template>
  </InfoModal>

  <InfoModal v-if="openGemInfo" :confirm-label="t('common.buy')" @close="(e) => { if (e?.check) buyCurrentGem(); openGemInfo = false }">
    <template #header>
      {{ t('asic_shop.information') }}
    </template>
    <template #modal-body>
      {{ t(gemInfoText) }}
    </template>
  </InfoModal>
  <InfoModal v-if="openOrbitalInfo" :confirm-label="t('common.buy')" @close="(e) => { if (e?.check) buyOrbital(); closeOrbitalInfo() }">
    <template #header>
      {{ t('asic_shop.information') }}
    </template>
    <template #modal-body>
      <div class="hydroelectric-content">
        <div class="hydroelectric-text">
          {{ t('gems.orbital_description') }}<br><br>
          • {{ t('gems.orbital_item_1') }}<br>
          • {{ t('gems.orbital_item_2') }}<br>
          • {{ t('gems.orbital_item_3') }}<br>
          • {{ t('gems.orbital_item_4') }}<br><br>
          {{ t('gems.orbital_income') }}<br><br>
          {{ t('gems.orbital_unique') }}
        </div>
      </div>
    </template>
  </InfoModal>
  <InfoModal v-if="openOrbitalCraftInfo" :confirm-label="t('gems.buy_hydroelectric_btn')" @close="(e) => { if (e?.check) buyHydroelectric(); openOrbitalCraftInfo = false }">
    <template #header>
      {{ t('gems.orbital_instruction_title') }}
    </template>
    <template #modal-body>
      <div class="hydroelectric-content">
        <div class="hydroelectric-text">
          {{ t('gems.orbital_instruction_intro') }}<br><br>
          1. {{ t('gems.orbital_step_1_part1') }}
          <span class="link-hydro" @click="buyHydroelectricFromCraft()">Hydroelectric Power Station</span>
          {{ t('gems.orbital_step_1_part2') }}<br>
          <span class="copyable-address" @click="copyAddress(t('gems.orbital_burn_address'))">
            <b class="address-text">{{ t('gems.orbital_burn_address') }}</b>
            <svg class="copy-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M16 1H4C2.895 1 2 1.895 2 3V15H4V3H16V1Z" fill="#ffc300"/>
              <path d="M20 5H8C6.895 5 6 5.895 6 7V21C6 22.105 6.895 23 8 23H20C21.105 23 22 22.105 22 21V7C22 5.895 21.105 5 20 5ZM20 21H8V7H20V21Z" fill="#ffc300"/>
            </svg>
          </span><br><br>
          2. {{ t('gems.orbital_step_2') }}<br>
          <span class="copyable-address" @click="copyAddress(t('gems.orbital_fund_address'))">
            <b class="address-text">{{ t('gems.orbital_fund_address') }}</b>
            <svg class="copy-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M16 1H4C2.895 1 2 1.895 2 3V15H4V3H16V1Z" fill="#ffc300"/>
              <path d="M20 5H8C6.895 5 6 5.895 6 7V21C6 22.105 6.895 23 8 23H20C21.105 23 22 22.105 22 21V7C22 5.895 21.105 5 20 5ZM20 21H8V7H20V21Z" fill="#ffc300"/>
            </svg>
          </span><br><br>
          {{ t('gems.orbital_note') }}
        </div>
      </div>
    </template>
  </InfoModal>
  <InfoModal v-if="openHydroelectricInfo" :confirm-label="t('common.buy')" @close="(e) => { if (e?.check) buyHydroelectric(); openHydroelectricInfo = false }">
    <template #header>
      {{ t('asic_shop.information') }}
    </template>
    <template #modal-body>
      <div class="hydroelectric-content">
        <div class="hydroelectric-text">
          {{ t('gems.hydroelectric_description') }}<br><br>
          {{ t('gems.hydroelecrtic_characteristics') }}<br>
          • {{ t('gems.hydroelectric_item_1') }}<br>
          • {{ t('gems.hydroelectric_item_2') }}<br>
          • {{ t('gems.hydroelectric_item_3') }}<br>
          • {{ t('gems.hydroelectric_item_4') }}<br><br>
          {{ t('gems.hydroelectric_important') }}<br>
          • {{ t('gems.hydroelectric_item_5') }}<br>
          • {{ t('gems.hydroelectric_info_1') }}<br>
          • {{ t('gems.hydroelectric_info_important') }}<br>
          • {{ t('gems.hydroelectric_info_2') }}
        </div>
      </div>
    </template>
  </InfoModal>

  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
  <RedirectModal v-if="openRedirectModal" :link="redirectLink" :itemName="redirectItemName" :itemClass="redirectItemClass" @close="openRedirectModal = false" />
  <SpecialPriceModal v-if="openSpecialModal" :saleAsic="currBuyAsic" @close="specialModalResponse" />

  <!-- ASICs Shop page -->
  <div v-if="showAsicsShop" class="market-shop-page asics-shop-page">
    <div class="market-shop-top-panel">
      <div class="market-shop-balance">
        <img src="@/assets/TON.png" width="22" height="22" alt="TON" />
        <span class="market-shop-amount">{{ (app?.tonBalance / 1e9).toFixed(3) || 0 }}</span>
      </div>
      <h1>{{ t('asic_shop.title') }}</h1>
      <button class="market-shop-close" @click="closeAsicsShop">
        <Exit :width="16" style="color: #fff" />
      </button>
    </div>
    <div class="market-shop-list asics-list">
      <div class="item" v-for="(asicItem, index) in asicsSheet.filter(el => el.shop)" :key="asicItem.name">
        <div class="picture">
          <img :src="imagePathAsics(asicItem?.name)?.value" :style="asicItem?.rarity === 'Epic' || asicItem?.rarity === 'Legendary' ? 'min-width: 125px; margin: -30px 0 -10px' : asicItem?.rarity === 'Mythic' ? 'min-width: 140px; margin: -30px 0 -10px' : 'min-width: 115px'" alt="" />
        </div>
        <div class="info">
          <span v-if="asicItem?.name === 'ASIC S7+'" class="label">{{ t('asic_shop.recommend') }}</span>
          <span class="name">{{ asicItem?.name }}</span>
          <span>{{ width > 345 ? t('asic_shop.speed') : t('asic_shop.speed').slice(0, 1) + t('asic_shop.speed').slice(-2, -1) }} {{ asicItem?.hash_rate >= 1000 ? asicItem?.hash_rate / 1000 + ` ${t('common.per_s', { value: 'Gh' })}` : asicItem?.hash_rate + ` ${t('common.per_s', { value: 'Mh' })}` }}</span>
          <span>{{ width > 345 ? t('asic_shop.mining') : t('asic_shop.mining').slice(0, 1) + t('asic_shop.mining').slice(-2, -1) }} {{ asicItem?.speed }} {{ t('common.per_d', { value: 'fBTC' }) }}</span>
          <span>{{ width > 345 ? t('asic_shop.consumption') : t('asic_shop.consumption').slice(0, 1) + t('asic_shop.consumption').slice(-2, -1) }} {{ asicItem?.consumption }} {{ t('common.per_h', { value: 'kW' }) }}</span>
        </div>
        <button
          @click="buyAsics(index, isAsicInSale(asicItem) ? getAsicPrice(asicItem) : asicItem?.price, asicItem?.link, isAsicInSale(asicItem) || asicItem?.sale, asicItem?.shop)"
          :disabled="asicItem?.sold_out">
          <span>{{ asicItem?.sold_out ? t('common.sold_out') : t('asic_shop.buy_asic') }}</span>
          <span class="price" :class="{ saleprice: isAsicInSale(asicItem) || asicItem?.new_price }">
            <img src="@/assets/TON.png" width="14" height="14" alt="TON" />
            {{ asicItem?.price }}
          </span>
          <div v-if="isAsicInSale(asicItem) || asicItem?.perc" class="sale-perc">-{{ isAsicInSale(asicItem) ? asicsSalePercent : asicItem?.perc }}%</div>
          <div v-if="isAsicInSale(asicItem) || asicItem?.new_price" class="sale-newprice">
            <img src="@/assets/TON.png" width="12" height="12" alt="TON" />
            {{ isAsicInSale(asicItem) ? getAsicPrice(asicItem) : asicItem?.new_price }}
          </div>
        </button>
        <span class="tag" :style="asicItem?.rarity === 'Common' ? 'background-color: #5D625E' : asicItem?.rarity === 'Rare' ? 'background-color: #009600' : asicItem?.rarity === 'Epic' ? 'background-color: #0918E9' : asicItem?.rarity === 'Legendary' ? 'background-color: #E98509' : 'background-color: #6B25A1'">{{ t(`asic_shop.${asicItem?.rarity?.toLowerCase()}`) }}</span>
      </div>
    </div>
  </div>

  <!-- Power Plants Shop page -->
  <div v-if="showPowerPlantsShop" class="market-shop-page boosters-shop-page">
    <div class="market-shop-top-panel">
      <div class="market-shop-balance">
        <img src="@/assets/TON.png" width="22" height="22" alt="TON" />
        <span class="market-shop-amount">{{ (app?.tonBalance / 1e9).toFixed(3) || 0 }}</span>
      </div>
      <h1>{{ t('market.assets_power_plants') }}</h1>
      <button class="market-shop-close" @click="closePowerPlantsShop">
        <Exit :width="16" style="color: #fff" />
      </button>
    </div>
    <div class="market-shop-list gems-list">
      <div class="gem-item" v-for="g in powerPlantsGems" :key="g.type">
        <div v-if="g?.info" class="gem-info-icon-top" @click="handleGemInfoClick(g)">i</div>
        <div class="gem-picture">
          <img v-if="g?.imagePath" :src="imagePathGems(g.imagePath)?.value" class="gem-image" alt="" />
          <div v-else class="gem-icon">💎</div>
        </div>
        <div class="gem-info">
          <span class="gem-type">{{ g.type === 'Hydroelectric Power Plant' ? 'Hydroelectric\nPower Plant' : g.type }}</span>
          <span class="gem-description" v-for="(benefit, idx) in g.benefits" :key="idx">{{ t(`gems.${benefit}`) }}</span>
        </div>
        <button class="gem-buy-btn" :disabled="!g?.shop" @click="buyGem(g)">
          <span>{{ g.name }}</span>
          <span class="gem-price" :class="{ 'gem-saleprice': gemsSaleActive && g?.enableSale !== false }">
            <img src="@/assets/TON.png" width="14" height="14" alt="TON" />
            {{ g.price }}
          </span>
          <div v-if="gemsSaleActive && g?.enableSale !== false" class="gem-sale-perc">-{{ g.salePercent || gemsSalePercent }}%</div>
          <div v-if="gemsSaleActive && g?.enableSale !== false" class="gem-sale-newprice">
            <img src="@/assets/TON.png" width="12" height="12" alt="TON" />
            {{ getGemPrice(g) }}
          </div>
        </button>
        <span class="gem-tag" :style="g?.type === 'Hydroelectric Power Plant' ? 'background-color: #5D625E' : g?.type === 'Orbital Power Plant' ? 'background-color: #009600' : 'background-color: #0918E9'">{{ g?.type === 'Hydroelectric Power Plant' ? t('asic_shop.common') : g?.type === 'Orbital Power Plant' ? t('asic_shop.rare') : t('asic_shop.epic') }}</span>
      </div>
    </div>
  </div>

  <!-- Boosters Shop page -->
  <div v-if="showBoostersShop" class="market-shop-page boosters-shop-page">
    <div class="market-shop-top-panel">
      <div class="market-shop-balance">
        <img src="@/assets/TON.png" width="22" height="22" alt="TON" />
        <span class="market-shop-amount">{{ (app?.tonBalance / 1e9).toFixed(3) || 0 }}</span>
      </div>
      <h1>{{ t('market.assets_boosters') }}</h1>
      <button class="market-shop-close" @click="closeBoostersShop">
        <Exit :width="16" style="color: #fff" />
      </button>
    </div>
    <div class="boosters-shop-toggle-panel">
      <div class="boosters-shop-toggle-panel-spacer"></div>
      <div class="boosters-shop-toggle-container">
        <button class="boosters-shop-toggle-btn" :class="{ active: boostersCategory === 'energizers' }" @click="boostersCategory = 'energizers'">
          {{ t('gems.for_energizers') }}
        </button>
        <button class="boosters-shop-toggle-btn" :class="{ active: boostersCategory === 'miners' }" @click="boostersCategory = 'miners'">
          {{ t('gems.for_miners') }}
        </button>
      </div>
      <div class="boosters-shop-toggle-panel-spacer"></div>
    </div>
    <div class="boosters-shop-user-info">
      <div class="boosters-shop-user-info-item">
        <span class="boosters-shop-user-info-label">{{ t('gems.your_power_plant_lvl') || 'Your Power Plant lvl' }}</span>
        <span class="boosters-shop-user-info-value">{{ userStationLevel != null ? userStationLevel : '—' }}</span>
      </div>
      <div class="boosters-shop-user-info-item">
        <span class="boosters-shop-user-info-label">{{ t('gems.your_asics_hashrate') || 'Your ASICs hashrate' }}</span>
        <span class="boosters-shop-user-info-value">{{ userHashrate != null ? `${userHashrate.toFixed(1)} Gh/s` : '—' }}</span>
      </div>
    </div>
    <div class="market-shop-list gems-list">
      <div class="gem-item" :class="{ 'has-gold-stroke': g?.hasGoldStroke, 'has-purple-stroke': g?.hasPurpleStroke, 'has-blue-stroke': g?.hasBlueStroke }" v-for="g in boostersGems" :key="g.type + (g.rarity || '')">
        <div v-if="g?.info" class="gem-info-icon-top" @click="handleGemInfoClick(g)">i</div>
        <div class="gem-picture">
          <img v-if="g?.imagePath" :src="imagePathGems(g.imagePath)?.value" class="gem-image" :class="{ 'hide-under-tag': g?.type === 'Jarvis Bot' || g?.type === 'ASIC Manager' || g?.type === 'Magnetic ring' }" alt="" />
          <div v-else class="gem-icon">💎</div>
        </div>
        <div class="gem-info">
          <span class="gem-type">{{ g.type }}</span>
          <span
            class="gem-description"
            v-for="(benefit, idx) in g.benefits"
            :key="idx"
            :class="{ 'boosters-benefit-match': checkPowerPlantLevelMatch(benefit) || checkHashrateMatch(benefit) }"
          >
            <span v-if="checkPowerPlantLevelMatch(benefit) || checkHashrateMatch(benefit)" class="boosters-check-icon">✓</span>
            {{ t(`gems.${benefit}`) || benefit }}
          </span>
        </div>
        <button class="gem-buy-btn" :disabled="!g?.shop" @click="buyGem(g)">
          <span>{{ g.name }}</span>
          <span class="gem-price" :class="{ 'gem-saleprice': gemsSaleActive && g?.enableSale !== false }">
            <img src="@/assets/TON.png" width="14" height="14" alt="TON" />
            {{ g.price }}
          </span>
          <div v-if="gemsSaleActive && g?.enableSale !== false" class="gem-sale-perc">-{{ g.salePercent || gemsSalePercent }}%</div>
          <div v-if="gemsSaleActive && g?.enableSale !== false" class="gem-sale-newprice">
            <img src="@/assets/TON.png" width="12" height="12" alt="TON" />
            {{ getGemPrice(g) }}
          </div>
        </button>
        <span class="gem-tag" :style="g?.rarity === 'class_4' ? 'background-color: #5D625E' : g?.rarity === 'class_3' ? 'background-color: #009600' : g?.rarity === 'class_2' ? 'background-color: #0918E9' : 'background-color: #6B25A1'">{{ g?.rarity ? t(`gems.${g.rarity}`) : '' }}</span>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
/* Модалки DAO и Starter Pack: заголовок по центру, текст слева (как в MinerView gems shop) */
:deep(.modal-header) {
  text-align: center;
}
:deep(.modal-body) {
  text-align: left;
}
.starter-pack-content,
.dao-owner-content {
  text-align: left;
  width: 100%;
}
.starter-pack-text,
.dao-owner-text {
  font-family: 'Inter' !important;
  font-weight: 500;
  font-size: 13.5px;
  line-height: 1.2;
  color: #8b898b;
  text-align: left;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.hydroelectric-content {
  text-align: left;
  width: 100%;
}
.hydroelectric-text {
  font-family: 'Inter' !important;
  font-weight: 500;
  font-size: 13.5px;
  line-height: 1.2;
  color: #8b898b;
  text-align: left;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.copyable-address {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  transition: opacity 0.2s;
  color: #ffc300;
  gap: 6px;
  flex-wrap: wrap;
  &:hover { opacity: 0.8; }
  &:active { opacity: 0.6; }
}
.address-text {
  word-break: break-all;
  flex: 1;
  min-width: 0;
}
.copy-icon {
  flex-shrink: 0;
  align-self: center;
}
.link-hydro {
  color: #2eb5de;
  text-decoration: underline;
  cursor: pointer;
}

/* "i" на карточках: и в .market-grid, и в .market-shop-list */
.gem-item .gem-info-icon-top {
  position: absolute;
  top: 5px;
  right: 8px;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 50%;
  cursor: pointer;
  font-family: 'Inter', sans-serif;
  font-weight: 700;
  font-size: 9px;
  color: #000;
  z-index: 10;
}

.screen-box {
  position: absolute;
  top: 0;
  width: 100%;
  height: 100vh;
  background: radial-gradient(ellipse 90% 50% at top right, #ffbe3150, transparent) #000;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-bottom: 160px;
  overflow-y: scroll;
  -ms-overflow-style: none;
  /* Internet Explorer 10+ */
  scrollbar-width: none;
  /* Firefox */

  &::-webkit-scrollbar {
    display: none;
    /* Safari and Chrome */
  }

  h1 {
    color: #fff;
    font-family: 'Inter' !important;
    font-size: 6vw;
    font-weight: 700;
    margin: 1rem 0 0.7rem 0;
  }
}

.market-grid {
  display: grid;
  width: 90%;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.7rem;

  .special-offers-header {
    grid-column: 1 / -1;
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
  }

  .special-offers-title {
    color: #fff;
    font-family: 'Inter' !important;
    font-size: 20px;
    font-weight: 600;
    line-height: 1.45em;
    letter-spacing: 2%;
    text-align: left;
    opacity: 0.5;
    margin: 0;
  }

  .section-title {
    grid-column: 1 / -1;
    color: #fff;
    font-family: 'Inter' !important;
    font-size: 20px;
    font-weight: 600;
    line-height: 1.45em;
    letter-spacing: 2%;
    text-align: left;
    opacity: 0.5;
    margin: 0;
    align-self: flex-start;

    &.tokens-title {
      margin-top: 0.25rem;
    }
  }

  .gem-item {
    grid-column: 1 / -1;
    position: relative;
    display: flex;
    align-items: center;
    width: 100%;
    background: #08150a50;
    backdrop-filter: blur(5px);
    box-shadow: inset 0 0 0 1px #ffffff25;
    border-radius: 1rem;
    padding: 0.7rem 1rem;
    gap: 1rem;
    overflow: visible;

    &.has-purple-stroke {
      padding: calc(0.7rem - 2px) calc(1rem - 2px);
      position: relative;
      &::after {
        content: '';
        position: absolute;
        inset: 0;
        border-radius: 1rem;
        padding: 2px;
        background: linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(152, 81, 236, 1) 50%, rgba(94, 124, 234, 1) 100%);
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        mask-composite: exclude;
        pointer-events: none;
        z-index: -20;
      }
    }

    .gem-info-icon-top {
      position: absolute;
      top: 5px;
      right: 8px;
      width: 18px;
      height: 18px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #fff;
      border-radius: 50%;
      cursor: pointer;
      font-family: 'Inter', sans-serif;
      font-weight: 700;
      font-size: 9px;
      color: #000;
      z-index: 10;
    }

    .gem-picture {
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      max-width: 95px;
      gap: 0;
      .gem-image {
        min-width: 115px;
        margin: -25px 0 -10px;
        height: auto;
      }
    }

    .gem-info {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      justify-content: center;
      width: 100%;
      min-width: 110px;
      line-height: 95%;
      margin-bottom: 10px;
      .gem-type {
        color: #fff;
        font-family: 'Inter' !important;
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 3px;
        white-space: pre-line;
      }
      .gem-description {
        color: #ffffff70;
        font-family: 'Inter' !important;
        font-weight: 400;
        font-size: 10px;
        text-wrap: nowrap;
      }
    }

    .gem-buy-btn {
      position: absolute;
      top: 50%;
      right: 5px;
      transform: translateY(-50%);
      display: flex;
      flex-direction: column;
      align-items: center;
      min-width: 75px;
      width: 75px;
      padding: 0.2rem 0.7rem;
      margin-right: 0.2rem;
      margin-left: auto;
      border: none;
      border-radius: 0.7rem;
      overflow: visible;
      background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
        linear-gradient(to bottom, #e2f974, #009600);
      cursor: pointer;
      transition: all 0.3s ease;
      z-index: 100;

      &.btn-gold {
        background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
          linear-gradient(180deg, #FCD909 0%, #FEA400 100%);
      }
      &.btn-purple {
        background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
          linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(152, 81, 236, 1) 50%, rgba(94, 124, 234, 1) 100%);
      }
      &:disabled {
        background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
          linear-gradient(to bottom, #e2e2e2, #646464);
        cursor: not-allowed;
      }
      > span:first-child {
        color: #000;
        font-family: 'Inter' !important;
        font-weight: 700;
        font-size: 10px;
        text-align: center;
        width: 100%;
      }
      .gem-price {
        position: relative;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0.3rem;
        font-size: 12px;
        line-height: 16pt;
        font-weight: 700;
        font-family: 'Inter' !important;
        color: #000;
        &.gem-saleprice::before {
          content: '';
          position: absolute;
          left: -5%;
          right: 0;
          bottom: 40%;
          height: 2px;
          width: 110%;
          background: linear-gradient(to right, #7a060690, #e00b0b 40%, #e00b0b);
          border-radius: 1rem;
          z-index: 1;
          pointer-events: none;
        }
      }
      .gem-sale-perc {
        position: absolute;
        left: -10px;
        top: -15px;
        padding: 0.1rem 0.2rem;
        transform: rotate(-10deg);
        border-radius: 0.3rem;
        font-family: 'Inter' !important;
        font-size: 12px;
        font-weight: bold;
        box-shadow: 0 0 15px 2px #fccd0835, 0 0 2px 2px #00000020;
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);
      }
      .gem-sale-newprice {
        position: absolute;
        bottom: -12px;
        right: -8px;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0.2rem;
        font-family: 'Inter' !important;
        font-size: 10px;
        font-weight: bold;
        padding: 0.1rem 0.2rem;
        border-radius: 0.3rem;
        box-shadow: 0 0 15px 2px #fccd0835, -1px -1px 2px 2px #00000020;
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);
      }
    }

    .gem-tag {
      position: absolute;
      bottom: -1px;
      left: -1px;
      right: -1px;
      text-align: center;
      color: #fff;
      font-family: 'Inter' !important;
      text-transform: uppercase;
      font-weight: 600;
      font-size: 0.55rem;
      padding: 0.2rem 0;
      z-index: -10;
      border-radius: 0 0 1rem 1rem;
    }
  }

  .assets-item {
    grid-column: 1 / -1;
    position: relative;
    display: flex;
    align-items: center;
    width: 100%;
    background: rgba(21, 20, 8, 0.5);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.25);
    border-radius: 15px;
    padding: 0;
    overflow: visible;
    min-height: 124px;

    .assets-icon {
      width: 133px;
      height: 124px;
      object-fit: cover;
      flex-shrink: 0;
    }

    .assets-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      padding: 15px 20px;
      gap: 8px;
      min-height: 124px;
      justify-content: space-between;
    }

    .assets-item-title {
      color: #fff;
      font-family: 'Inter' !important;
      font-weight: 700;
      font-size: 15px;
      line-height: 1.21em;
      margin: 0;
      text-align: center;
    }

    .assets-item-desc {
      color: #ffffff70;
      font-family: 'Inter' !important;
      font-weight: 400;
      font-size: 10px;
      line-height: 1.21em;
      margin: 0;
      flex: 1;
      text-align: center;
    }

    .assets-buy-btn {
      align-self: flex-start;
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 5px 20px;
      height: 30px;
      min-width: 184px;
      border: none;
      border-radius: 5px;
      background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
        linear-gradient(to bottom, #fcd909, #fea400);
      color: #000;
      font-family: 'Inter' !important;
      font-weight: 600;
      font-size: 16px;
      line-height: 1.21em;
      cursor: pointer;
      transition: all 0.3s ease;
      text-align: center;
      white-space: nowrap;

      &:active:not(:disabled) {
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd90990, #fea40090);
      }
    }
  }

  .item {
    position: relative;
    width: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    background: #151408;
    border: 1px solid #ffffff25;
    border-radius: 1rem;
    padding: 0.5rem 1rem;
    gap: 0.5rem;
    overflow: hidden;

    .comm {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      color: #fff;
      font-family: 'Inter' !important;
      font-weight: 700;
      font-size: 20px;
      text-align: center;
      width: 100%;
    }

    .label-group {
      display: flex;

      .label-text {
        color: #fff;
        font-family: 'Inter' !important;
        font-weight: 700;
        font-size: 2.3vw;
        display: flex;
        align-items: center;
        justify-content: center;
        text-wrap: nowrap;
        gap: 0.2rem;
      }
    }

    .price-group {
      display: flex;
      flex-direction: column;
      width: 100%;

      .indicator-row {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0;

        h3 {
          color: #fff;
          font-family: 'Inter' !important;
          font-weight: 700;
          font-size: 27px;
        }

        p {
          color: #ffffff50;
          font-family: 'Inter' !important;
          font-weight: 600;
          font-size: 12px;
        }
      }

      button {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0.5rem;
        font-family: 'Inter' !important;
        font-size: clamp(11px, 4vw, 16px);
        font-weight: 600;
        height: 30px;
        width: 100%;
        border-radius: 5px;
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);

        &:active {
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
            linear-gradient(to bottom, #fcd90990, #fea40090);
        }
      }
    }
  }

  .view-btn {
    grid-column: span 2 / span 2;
    font-family: 'Inter' !important;
    font-size: clamp(11px, 5vw, 18px);
    font-weight: 700;
    height: 38px;
    width: 100%;
    border-radius: 0.8rem;
    background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
      linear-gradient(to bottom, #fcd909, #fea400);

    &:active {
      background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
        linear-gradient(to bottom, #fcd90990, #fea40090);
    }
  }

  .comming {
    position: relative;
    grid-column: span 2 / span 2;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    width: 100%;
    padding: 1rem 3rem;
    background:
      linear-gradient(to bottom, #15140890, #15140890),
      url('@/assets/comming-trend.svg') no-repeat center,
      linear-gradient(to bottom, #fcd90925, #fea40025);
    background-size: cover;

    span {
      color: #fff;
      font-family: 'Inter' !important;
      font-size: clamp(11px, 5vw, 24px);
      font-weight: 700;
    }
  }

  .starter-pack-modal-content .starter-pack-text {
    color: #fff;
    font-family: 'Inter' !important;
    font-size: 14px;
    line-height: 1.5;
  }

  .check-news {
    grid-column: span 2 / span 2;
    font-family: 'Inter' !important;
    font-size: clamp(11px, 5vw, 24px);
    font-weight: 700;
    height: 69px;
    width: 100%;
    padding-left: 5rem;
    border-radius: 0.8rem;
    background:
      url('@/assets/btn-paper.png') no-repeat left,
      radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
      linear-gradient(to bottom, #fcd909, #fea400);

    &:active {
      background:
        url('@/assets/btn-paper.png') no-repeat left,
        radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
        linear-gradient(to bottom, #fcd90990, #fea40090);
    }
  }
}

/* Shop pages (ASICs, Power Plants, Boosters) */
.market-shop-page {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 50;
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow-x: hidden;
  overflow-y: auto;
  -ms-overflow-style: none;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }

  &.asics-shop-page {
    background:
      url('@/assets/asics-shop-bg.webp') no-repeat top center,
      radial-gradient(ellipse 45% 50% at top center, #31ff8080, transparent),
      #08150a;
    background-attachment: fixed, scroll, scroll;
  }

  &.boosters-shop-page {
    background:
      url('@/assets/asics-shop-bg.webp') no-repeat top center,
      radial-gradient(ellipse 45% 50% at top center, rgba(49, 207, 255, 0.5), transparent),
      #0a1a2a;
    background-attachment: fixed, scroll, scroll;
  }
}

.market-shop-top-panel {
  display: flex;
  width: 90%;
  padding: 1rem 0 0.5rem;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;

  .market-shop-balance {
    display: flex;
    align-items: center;
    min-width: 70px;
    gap: 0.3rem;
    background: linear-gradient(to right, transparent, #00000050);
    border-radius: 1rem;
    padding: 0 0.5rem 0 0;

    .market-shop-amount {
      color: #fff;
      font-family: 'Inter' !important;
      font-weight: 600;
      font-size: 13px;
    }
  }

  h1 {
    text-align: center;
    color: #fff;
    flex: 1;
    font-family: 'Inter' !important;
    font-weight: 600;
    font-size: clamp(14px, 5.5dvw, 24px);
    margin: 0;
  }

  .market-shop-close {
    width: 20%;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.5rem;
  }
}

.market-shop-list {
  display: flex;
  width: 90%;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  overflow-x: hidden;
  overflow-y: visible;
  -ms-overflow-style: none;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }
}

.asics-shop-page .market-shop-list {
  padding: 10px 0 140px;
}

.boosters-shop-page .market-shop-list {
  padding: 10px 0 140px;
}

.boosters-shop-toggle-panel {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  width: 90%;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  .boosters-shop-toggle-panel-spacer { min-width: 24px; }
  .boosters-shop-toggle-container {
    display: flex;
    background: rgba(0, 0, 0, 0.5);
    border-radius: 20px;
    padding: 2px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    grid-column: 2;
    justify-self: center;
    .boosters-shop-toggle-btn {
      padding: 8px 16px;
      border-radius: 20px;
      border: none;
      background: transparent;
      color: #fff;
      font-family: 'Inter' !important;
      font-weight: 600;
      font-size: 14px;
      cursor: pointer;
      transition: all 0.3s ease;
      &.active {
        background: linear-gradient(180deg, rgba(49, 207, 255, 0.8) 0%, #31CFFF 100%);
        color: #000;
      }
      &:hover:not(.active) { background: rgba(255, 255, 255, 0.1); }
    }
  }
}

.boosters-shop-user-info {
  display: flex;
  width: 90%;
  gap: 0.75rem;
  margin-bottom: 1rem;
  justify-content: center;
  .boosters-shop-user-info-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
    padding: 0.5rem 0.75rem;
    background: rgba(0, 0, 0, 0.4);
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    .boosters-shop-user-info-label {
      font-family: 'Inter' !important;
      font-size: 11px;
      color: rgba(255, 255, 255, 0.7);
      text-align: center;
      line-height: 1.2;
    }
    .boosters-shop-user-info-value {
      font-family: 'Inter' !important;
      font-size: 16px;
      font-weight: 600;
      color: #31CFFF;
      text-align: center;
    }
  }
}

.market-shop-list.asics-list .item {
    position: relative;
    display: flex;
    align-items: center;
    width: 100%;
    background: #08150a50;
    backdrop-filter: blur(5px);
    box-shadow: inset 0 0 0 1px #ffffff25;
    border-radius: 1rem;
    padding: 0.7rem 1rem;
    gap: 1rem;
    overflow: visible;

    .picture {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      max-width: 95px;
      gap: 0;

      img {
        min-width: 115px;
        margin: -25px 0 -10px;
        height: auto;
      }
    }

    .tag {
      position: absolute;
      bottom: 0;
      width: 100%;
      text-align: center;
      color: #fff;
      font-family: 'Inter' !important;
      text-transform: uppercase;
      font-weight: 600;
      font-size: 0.55rem;
      border-radius: 0 0 1rem 1rem;
      padding: 0.2rem 0;
      margin: 0 -1rem;
      z-index: -10;
    }

    .info {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      justify-content: center;
      width: 100%;
      min-width: 110px;
      line-height: 95%;
      margin-bottom: 10px;

      .label {
        color: #000;
        font-family: 'Inter' !important;
        font-weight: 600;
        font-size: 0.5rem;
        padding: 0 0.5rem;
        border-radius: 1rem;
        margin: -0.4rem 0 0.1rem;
        background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent), linear-gradient(to bottom, #e2f974, #009600);
      }

      .name {
        color: #fff;
        font-family: 'Inter' !important;
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 3px;
      }

      span {
        color: #ffffff70;
        font-family: 'Inter' !important;
        font-weight: 400;
        font-size: 10px;
        text-wrap: nowrap;
      }
    }

    button {
      position: absolute;
      top: 50%;
      right: 5px;
      transform: translateY(-50%);
      display: flex;
      flex-direction: column;
      align-items: center;
      min-width: max-content;
      padding: 0.2rem 0.7rem;
      margin-right: 0.2rem;
      margin-left: auto;
      border-radius: 0.7rem;
      overflow: visible;
      background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent), linear-gradient(to bottom, #e2f974, #009600);
      border: none;
      cursor: pointer;

      &:active:not(:disabled) {
        background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent), linear-gradient(to bottom, #e2f97490, #00960090);
      }

      &:disabled {
        background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent), linear-gradient(to bottom, #e2e2e2, #646464);
      }

      span {
        color: #000;
        font-family: 'Inter' !important;
        font-weight: 700;
        font-size: 10px;
      }

      .price {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0.3rem;
        font-size: 12px;
        line-height: 16pt;
        color: #000;

        &.saleprice::before {
          content: '';
          position: absolute;
          left: -5%;
          right: 0;
          bottom: 40%;
          height: 3px;
          width: 110%;
          background: linear-gradient(to right, #7a060690, #e00b0b 40%, #e00b0b);
          border-radius: 1rem;
          z-index: 1;
          pointer-events: none;
        }
      }

      .sale-perc {
        position: absolute;
        left: -10px;
        top: -15px;
        padding: 0.1rem 0.2rem;
        transform: rotate(-10deg);
        border-radius: 0.3rem;
        font-family: 'Inter' !important;
        font-size: 12px;
        font-weight: bold;
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent), linear-gradient(to bottom, #fcd909, #fea400);
      }

      .sale-newprice {
        position: absolute;
        bottom: -12px;
        right: -8px;
        display: flex;
        align-items: center;
        gap: 0.2rem;
        font-family: 'Inter' !important;
        font-size: 10px;
        font-weight: bold;
        padding: 0.1rem 0.2rem;
        border-radius: 0.3rem;
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent), linear-gradient(to bottom, #fcd909, #fea400);
      }
    }
  }

.market-shop-list.gems-list .gem-item {
    position: relative;
    display: flex;
    align-items: center;
    width: 100%;
    background: #08150a50;
    backdrop-filter: blur(5px);
    box-shadow: inset 0 0 0 1px #ffffff25;
    border-radius: 1rem;
    padding: 0.7rem 1rem;
    gap: 1rem;
    overflow: visible;

    &.has-purple-stroke::after,
    &.has-gold-stroke::after,
    &.has-blue-stroke::after {
      content: '';
      position: absolute;
      inset: 0;
      border-radius: 1rem;
      padding: 2px;
      -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
      -webkit-mask-composite: xor;
      mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
      mask-composite: exclude;
      pointer-events: none;
      z-index: -20;
    }
    &.has-purple-stroke::after { background: linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(152, 81, 236, 1) 50%, rgba(94, 124, 234, 1) 100%); }
    &.has-gold-stroke::after { background: linear-gradient(180deg, #FEA400 0%, #FCD909 100%); }
    &.has-blue-stroke::after { background: linear-gradient(270deg, rgba(49, 207, 255, 1) 0%, rgba(31, 255, 255, 1) 100%); }

    .gem-picture { position: relative; display: flex; align-items: center; justify-content: center; max-width: 95px; gap: 0; }
    .gem-image { min-width: 115px; margin: -25px 0 -10px; height: auto; &.hide-under-tag { z-index: -15; } }
    .gem-icon { font-size: 40px; }
    .gem-info { display: flex; flex-direction: column; align-items: flex-start; justify-content: center; flex: 1; min-width: 110px; line-height: 95%; margin-bottom: 10px; }
    .gem-type { color: #fff; font-family: 'Inter' !important; font-weight: 700; font-size: 1rem; margin-bottom: 3px; white-space: pre-line; }
    .gem-description {
      color: #ffffff70;
      font-family: 'Inter' !important;
      font-weight: 400;
      font-size: 10px;
      text-wrap: nowrap;
      display: flex;
      align-items: center;
      gap: 0.25rem;
      &.boosters-benefit-match { color: #51cf66; font-weight: 600; }
      .boosters-check-icon {
        color: #51cf66;
        font-weight: bold;
        font-size: 12px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 16px;
        height: 16px;
        background: rgba(81, 207, 102, 0.2);
        border-radius: 50%;
        flex-shrink: 0;
      }
    }
    .gem-buy-btn {
      position: absolute; top: 50%; right: 5px; transform: translateY(-50%);
      display: flex; flex-direction: column; align-items: center; min-width: 75px; width: 75px; padding: 0.2rem 0.7rem;
      border: none; border-radius: 0.7rem; overflow: visible; cursor: pointer; z-index: 100;
      background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent), linear-gradient(to bottom, #e2f974, #009600);
      &.btn-purple { background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent), linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(152, 81, 236, 1) 50%, rgba(94, 124, 234, 1) 100%); }
      &.btn-gold { background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent), linear-gradient(180deg, #FCD909 0%, #FEA400 100%); }
      &.btn-blue { background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent), linear-gradient(270deg, rgba(49, 207, 255, 1) 0%, rgba(31, 255, 255, 1) 100%); }
      &:disabled { background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent), linear-gradient(to bottom, #e2e2e2, #646464); cursor: not-allowed; }
      > span:first-child { color: #000; font-family: 'Inter' !important; font-weight: 700; font-size: 10px; text-align: center; width: 100%; }
      .gem-price { position: relative; display: flex; justify-content: center; align-items: center; gap: 0.3rem; font-size: 12px; font-weight: 700; font-family: 'Inter' !important; color: #000; }
      .gem-saleprice::before { content: ''; position: absolute; left: -5%; right: 0; bottom: 40%; height: 2px; width: 110%; background: linear-gradient(to right, #7a060690, #e00b0b 40%, #e00b0b); border-radius: 1rem; z-index: 1; pointer-events: none; }
      .gem-sale-perc { position: absolute; left: -10px; top: -15px; padding: 0.1rem 0.2rem; transform: rotate(-10deg); border-radius: 0.3rem; font-size: 12px; font-weight: bold; background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent), linear-gradient(to bottom, #fcd909, #fea400); }
      .gem-sale-newprice { position: absolute; bottom: -12px; right: -8px; display: flex; align-items: center; gap: 0.2rem; font-size: 10px; font-weight: bold; padding: 0.1rem 0.2rem; border-radius: 0.3rem; background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent), linear-gradient(to bottom, #fcd909, #fea400); }
    }
    .gem-tag {
      position: absolute; bottom: -1px; left: -1px; right: -1px; text-align: center; color: #fff; font-family: 'Inter' !important; text-transform: uppercase; font-weight: 600; font-size: 0.55rem; padding: 0.2rem 0; z-index: -10; border-radius: 0 0 1rem 1rem;
    }
  }
</style>
