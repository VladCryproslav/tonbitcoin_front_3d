<script setup>
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref } from 'vue'
const DeDust = defineAsyncComponent(() => import('@/assets/dedust.svg'))
const Stonfi = defineAsyncComponent(() => import('@/assets/stonfi.svg'))
import { useTelegram } from '@/services/telegram'
import axios from 'axios'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import { useTabsStore } from '@/stores/tabs'
import { useRouter } from 'vue-router'
import { useTonAddress, useTonConnectUI } from '@townsquarelabs/ui-vue'
import { beginCell, toNano } from '@ton/core'
import InfoModal from '@/components/InfoModal.vue'
import ModalNew from '@/components/ModalNew.vue'
import { gemsSheet, gemsSaleActive, getGemPrice } from '@/services/data'

const app = useAppStore()
const tabs = useTabsStore()
const router = useRouter()
const { tg } = useTelegram()
const { t } = useI18n()
const ton_address = useTonAddress()
const { tonConnectUI } = useTonConnectUI()

const starterPack = computed(() => gemsSheet.find(g => g.type === 'Starter Pack'))
const openStarterPackInfo = ref(false)
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

const buyStarterPack = async () => {
  if (!starterPack.value || isProcessing.value) return
  openStarterPackInfo.value = false
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
    await tonConnectUI.closeModal().catch(() => {})
    const transferAmount = getStarterPackPriceDisplay()
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
      openModal.value = true
      modalStatus.value = 'success'
      modalTitle.value = t('notification.st_success')
      modalBody.value = t('gems.starter_pack_price_offer', { price: transferAmount })
      await app.initUser()
    }
  } catch (err) {
    console.error('buyStarterPack:', err)
    openModal.value = true
    modalStatus.value = 'error'
    modalTitle.value = t('notification.st_error')
    modalBody.value = t('notification.failed_transaction')
  } finally {
    isProcessing.value = false
  }
}

const openAsicsShop = () => {
  tabs.setTab('home')
  tabs.setCategory('miner')
  tabs.setOpenAsicsShop(true)
  router.push('/')
}

const openBoostersShop = () => {
  tabs.setTab('home')
  tabs.setCategory('boost')
  tabs.setBoost(true)
  router.push('/')
}

const openPowerPlantsShop = () => {
  tabs.setTab('home')
  tabs.setCategory('miner')
  tabs.setOpenAsicsShop(true)
  router.push('/')
}

const stonfiFBTCPrice = ref(0)
const stonfiKwPrice = ref(0)
let controller = null

const direct = (link) => {
  return link.includes('t.me') ? tg?.openTelegramLink(link) : tg?.openLink(link)
}

function roundToFirstSignificantDecimal(num) {
  if (num === 0) return 0 // Для 0 возвращаем 0

  const magnitude = Math.pow(10, -Math.floor(Math.log10(Math.abs(num))))
  return Math.round(num * magnitude) / magnitude
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
  <div class="screen-box">
    <h1 class="title">{{ t('market.title') }}</h1>

    <div class="market-grid">
      <div class="special-offers-header">
        <h2 class="special-offers-title">{{ t('market.limited_offers') }}</h2>
      </div>
      <div v-if="starterPack" class="starter-pack-item has-purple-stroke">
        <div class="starter-pack-picture">
          <img src="@/assets/gems/Starter_pack.webp" class="starter-pack-image" alt="Starter Pack" />
        </div>
        <div class="starter-pack-info">
          <span class="starter-pack-type">{{ starterPack.type }}</span>
          <span class="starter-pack-description">{{ t('gems.starter_pack_benefit_1') }}</span>
          <span class="starter-pack-description">{{ t('gems.starter_pack_benefit_2') }}</span>
          <span class="starter-pack-description">{{ t('gems.starter_pack_benefit_3') }}</span>
          <span class="starter-pack-description">{{ t('gems.starter_pack_benefit_4') }}</span>
        </div>
        <button
          class="starter-pack-buy-btn btn-purple"
          :disabled="isProcessing"
          @click="openStarterPackInfo = true"
        >
          <span>{{ t('common.buy') }}</span>
          <span class="starter-pack-price">
            <img src="@/assets/TON.png" width="14" height="14" alt="TON" />
            {{ getStarterPackPriceDisplay() }}
          </span>
        </button>
        <span class="starter-pack-tag">Special</span>
      </div>

      <h2 class="section-title">{{ t('market.nft_assets') }}</h2>
      <div class="assets-item">
        <img src="@/assets/gems_shop_icon.png" class="assets-icon" alt="" />
        <div class="assets-content">
          <h3 class="assets-item-title">{{ t('market.assets_mining_equipment') }}</h3>
          <p class="assets-item-desc">{{ t('market.assets_mining_equipment_desc') }}</p>
          <button class="assets-buy-btn" @click="openAsicsShop">{{ t('market.assets_buy_asics') }}</button>
        </div>
      </div>
      <div class="assets-item">
        <img src="@/assets/gems_shop_icon.png" class="assets-icon" alt="" />
        <div class="assets-content">
          <h3 class="assets-item-title">{{ t('market.assets_power_plants') }}</h3>
          <p class="assets-item-desc">{{ t('market.assets_power_plants_desc') }}</p>
          <button class="assets-buy-btn" @click="openPowerPlantsShop">{{ t('market.assets_buy_power_plant') }}</button>
        </div>
      </div>
      <div class="assets-item">
        <img src="@/assets/boost_disk.svg" class="assets-icon" alt="" />
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
      <div style="text-align: center;" v-html="t('gems.starter_pack_title')"></div>
    </template>
    <template #modal-body>
      <div class="starter-pack-modal-content">
        <div class="starter-pack-text">
          • {{ t('gems.starter_pack_item_1') }}<br>
          • {{ t('gems.starter_pack_item_3') }}<br>
          • {{ t('gems.starter_pack_item_4') }}<br>
          • {{ t('gems.starter_pack_item_5') }}<br>
          • {{ t('gems.starter_pack_item_6') }}<br>
          • {{ t('gems.starter_pack_item_7') }}<br><br>
          {{ t('gems.starter_pack_price_info') }}<br>
          {{ t('gems.starter_pack_price_offer', { price: getStarterPackPriceDisplay() }) }}<br><br>
          <span style="color: #ffc300;">{{ t('gems.starter_pack_item_8') }}</span>
        </div>
      </div>
    </template>
  </InfoModal>

  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
</template>

<style lang="scss" scoped>
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

  .starter-pack-item {
    grid-column: 1 / -1;
    position: relative;
    display: flex;
    align-items: center;
    width: 100%;
    background: #151408;
    backdrop-filter: blur(5px);
    box-shadow: inset 0 0 0 1px #ffffff25;
    border-radius: 1rem;
    padding: 0.7rem 1rem;
    gap: 1rem;
    overflow: visible;

    &.has-purple-stroke {
      padding: calc(0.7rem - 2px) calc(1rem - 2px);
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
        z-index: 0;
      }
    }

    .starter-pack-picture {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      max-width: 95px;
      .starter-pack-image {
        min-width: 75px;
        width: 75px;
        height: auto;
      }
    }

    .starter-pack-info {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      justify-content: center;
      flex: 1;
      min-width: 0;
      line-height: 1.2;
      .starter-pack-type {
        color: #fff;
        font-family: 'Inter' !important;
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 4px;
      }
      .starter-pack-description {
        color: #ffffff70;
        font-family: 'Inter' !important;
        font-weight: 400;
        font-size: 10px;
      }
    }

    .starter-pack-buy-btn {
      position: absolute;
      top: 50%;
      right: 0.5rem;
      transform: translateY(-50%);
      display: flex;
      flex-direction: column;
      align-items: center;
      min-width: 70px;
      padding: 0.3rem 0.5rem;
      border: none;
      border-radius: 0.7rem;
      background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
        linear-gradient(180deg, #FCD909 0%, #FEA400 100%);
      cursor: pointer;
      transition: all 0.2s ease;
      z-index: 1;

      &.btn-purple {
        background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
          linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(152, 81, 236, 1) 50%, rgba(94, 124, 234, 1) 100%);
      }
      &:disabled {
        opacity: 0.7;
        cursor: not-allowed;
      }
      > span:first-child {
        color: #000;
        font-family: 'Inter' !important;
        font-weight: 700;
        font-size: 10px;
      }
      .starter-pack-price {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.25rem;
        font-size: 12px;
        font-weight: 700;
        font-family: 'Inter' !important;
        color: #000;
      }
    }

    .starter-pack-tag {
      position: absolute;
      top: 0.5rem;
      right: 0.5rem;
      font-family: 'Inter' !important;
      font-size: 10px;
      font-weight: 700;
      color: #fff;
      background: rgba(152, 81, 236, 0.9);
      padding: 2px 6px;
      border-radius: 4px;
      z-index: 1;
    }
  }

  .assets-item {
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    width: 100%;
    background: rgba(21, 20, 8, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.25);
    border-radius: 15px;
    padding: 0;
    min-height: 90px;
    overflow: hidden;

    .assets-icon {
      width: 90px;
      min-width: 90px;
      height: 90px;
      object-fit: cover;
    }

    .assets-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      padding: 12px 16px;
      gap: 6px;
      justify-content: center;
      min-width: 0;
    }

    .assets-item-title {
      color: #fff;
      font-family: 'Inter' !important;
      font-weight: 700;
      font-size: 14px;
      margin: 0;
    }

    .assets-item-desc {
      color: #ffffff70;
      font-family: 'Inter' !important;
      font-weight: 400;
      font-size: 10px;
      margin: 0;
      line-height: 1.2;
    }

    .assets-buy-btn {
      align-self: flex-start;
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 5px 16px;
      height: 28px;
      border: none;
      border-radius: 5px;
      background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
        linear-gradient(to bottom, #fcd909, #fea400);
      color: #000;
      font-family: 'Inter' !important;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s ease;

      &:active {
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
</style>
