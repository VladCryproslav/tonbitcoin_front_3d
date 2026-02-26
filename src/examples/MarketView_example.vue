<script setup>
import { defineAsyncComponent, onMounted, onUnmounted, ref, computed, watch } from 'vue'
// const UpTrend = defineAsyncComponent(() => import('@/assets/up-trend.svg'))
// const DownTrend = defineAsyncComponent(() => import('@/assets/down-trend.svg'))
const Raydium = defineAsyncComponent(() => import('@/assets/raydium.svg'))
const Exit = defineAsyncComponent(() => import('@/assets/exit.svg'))
const Success = defineAsyncComponent(() => import('@/assets/success.svg'))
import confetti from 'canvas-confetti'
import { useTelegram } from '@/services/telegram'
import axios from 'axios'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import { useTabsStore } from '@/stores/tabs'
import { useRoute } from 'vue-router'
import InfoModal from '@/components/InfoModal.vue'
import SpecialPriceModal from '@/components/SpecialPriceModal.vue'
import ModalNew from '@/components/ModalNew.vue'
import CryptoBrowserModal from '@/components/CryptoBrowserModal.vue'
import { shouldShowCryptoBrowserNotification } from '@/utils/browserDetector'
import asicsSheet, { gemsSheet, powerPlantsSheet, gemsSaleActive, gemsSalePercent, gemsSaleEndDate, getGemPrice, sortGemsBySale, asicsSaleActive as asicsSaleActiveFromData, asicsSalePercent, boostersSaleActive as boostersSaleActiveFromData, boostersSalePercent, getBoosterPrice, starterPackSaleActive, starterPackSalePercent, getStarterPackPrice } from '@/services/data'
import { getAsicData } from '@/utils/asics'
import { useScreen } from '@/composables/useScreen'
import { solanaWalletService } from '@/services/solana-simple'
import { host } from '../../axios.config'
import _ from 'lodash'
import { PHANTOM_VERIFICATION_NOTICE, POWER_PLANT_ENABLED, TRADE_ENABLED_KW, TRADE_ENABLED_SBTC } from '@/config/maintenance'


const app = useAppStore()
const tabs = useTabsStore()
const route = useRoute()
const { tg } = useTelegram()
const { t } = useI18n()
const { width } = useScreen()

// Модальное окно для Trade кнопок
const showTradeModal = ref(false)
const showStarterPackModal = ref(false)
// Модальное окно для уведомления о крипто-браузере
const showCryptoBrowserModal = ref(false)

// Переключение между Mint и P2P Market
const isMintMode = ref(true)

// ASICs Shop состояние
const showAsicsShop = ref(false)
const showOwnedAsics = ref(false)
const promoBannerClosed = ref(false)
const isProcessing = ref(false)
const purchaseSuccess = ref(false)
const purchasedAsic = ref(null)
const purchasedBoost = ref(null)
const processingType = ref('purchase') // 'purchase' | 'activate' | 'disable'
const stationActionSuccess = ref(false)
const stationActionMessage = ref('')
const openSpecialModal = ref(false)
const currBuyAsic = ref(null)
const cachedAsicNfts = ref([])

// Boosters Shop состояние
const showBoostersShop = ref(false)
const showOwnedBoosters = ref(false)
const cachedBoostAssets = ref([])
const boostersPromoBannerClosed = ref(false)

// Power Plants Shop состояние
const showPowerPlantsShop = ref(false)
const showOwnedPowerPlants = ref(false)
const cachedPowerPlantsAssets = ref([])
const openGemInfo = ref(false)
const gemInfoText = ref('')
const currentGemItem = ref(null)
const openStarterPackInfo = ref(false)
const openDaoOwnerInfo = ref(false)
const openHydroelectricInfo = ref(false)
const openOrbitalInfo = ref(false)
const openOrbitalCraftInfo = ref(false)
const openBoostConditionsInfo = ref(false)
const boostConditionsInfoHtml = ref('')
const openSwitchStationConfirm = ref(false)
const pendingStationToActivate = ref(null)
const openDisableStationConfirm = ref(false)

// Модальное окно для уведомлений
const openModal = ref(false)
const modalStatus = ref('')
const modalTitle = ref('')
const modalBody = ref('')
const shouldOpenAsicsShopOnClose = ref(false)

// Phantom Verification состояние
const phantomConfirmOpen = ref(false)
const phantomPendingAction = ref(null)

// Форматирование сообщения с красным "Proceed Anyway"
const phantomVerificationMessage = computed(() => {
  const message = t('wallet.phantom_verification_message')
  return message.replace(
    /Proceed Anyway/g,
    '<span style=\'color: #ff3b59 !important; font-weight: bold;\'>Proceed Anyway</span>'
  )
})

const openPhantomConfirmation = (action) => {
  if (phantomConfirmOpen.value) return
  phantomPendingAction.value = action
  phantomConfirmOpen.value = true
}

const handlePhantomConfirm = (payload = { check: false }) => {
  phantomConfirmOpen.value = false
  const action = phantomPendingAction.value
  phantomPendingAction.value = null
  if (payload?.check && typeof action === 'function') {
    Promise.resolve(action()).catch((err) => {
      console.error('Phantom confirmation action failed:', err)
    })
  }
}

// Ссылки на соцсети из переменных окружения (как в HomeView)
const twitterLink = import.meta.env.VITE_SOCIAL_TWITTER_URL || 'https://x.com/sBTC_x'
const discordLink = import.meta.env.VITE_SOCIAL_DISCORD_URL || 'https://discord.gg/vqyG2r2G'

// Обработчик закрытия модального окна
const handleTradeModalClose = (e) => {
  if (e?.check) {
    // Нажата кнопка Discord - открываем ссылку
    if (typeof window !== 'undefined') {
      window.open(discordLink, '_blank', 'noopener,noreferrer')
    }
  }
  showTradeModal.value = false
}

// Функция для открытия Raydium swap для sBTC
const openRaydiumSwap = () => {
  const sbtcTokenAddress = 'Bed7NA23HErs4AaQuiVbSAuxigb4aDjMGFXDZhWviCL4'
  const raydiumUrl = `https://raydium.io/swap/?inputMint=${sbtcTokenAddress}`
  if (typeof window !== 'undefined') {
    window.open(raydiumUrl, '_blank', 'noopener,noreferrer')
  }
}

// Открыть Raydium swap для kW
const openKwRaydiumSwap = () => {
  const kwTokenAddress = '4fFS8haXMKTWfcSWjve5dxN1TX5bM1qTaxbKREhhxLa3'
  const raydiumUrl = `https://raydium.io/swap/?inputMint=${kwTokenAddress}`
  if (typeof window !== 'undefined') {
    window.open(raydiumUrl, '_blank', 'noopener,noreferrer')
  }
}

// Обработчик клика Trade для kW
const openKwTrade = () => {
  // Проверка браузера перед торговлей (forceShow = true - всегда показываем при попытке покупки)
  if (shouldShowCryptoBrowserNotification(true)) {
    showCryptoBrowserModal.value = true
    return
  }
  if (!TRADE_ENABLED_KW) {
    showTradeModal.value = true
    return
  }
  openKwRaydiumSwap()
}

// Обработчик клика Trade для sBTC
const openSbtcTrade = () => {
  // Проверка браузера перед торговлей (forceShow = true - всегда показываем при попытке покупки)
  if (shouldShowCryptoBrowserNotification(true)) {
    showCryptoBrowserModal.value = true
    return
  }
  if (!TRADE_ENABLED_SBTC) {
    showTradeModal.value = true
    return
  }
  openRaydiumSwap()
}

// Обработчик закрытия модалки крипто-браузера
const handleCryptoBrowserModalClose = () => {
  showCryptoBrowserModal.value = false
}

// Функция для определения текущего открытого магазина
const getCurrentShop = () => {
  if (showAsicsShop.value) return 'asics'
  if (showBoostersShop.value) return 'boosters'
  if (showPowerPlantsShop.value) return 'powerplants'
  return null
}

const raydiumFBTCPrice = ref(0)
const raydiumKwPrice = ref(0)
let controller = null
let sbtcPriceInterval = null

// Соотношения для расчета цен (только Raydium)
const KW_PER_SOL = 457000 // 1 SOL = 457000 kW
// const SBTC_PER_SOL = 1600 // 1 SOL = 1600 sBTC (временно не используется - статичная цена)

// Курс SOL/USD
const solPriceUsd = ref(0)
const SOL_PRICE_CACHE_KEY = 'sol_price_cache'
const SOL_PRICE_UPDATE_INTERVAL = 300000 // 5 минут
let solPriceUpdateInterval = null

// Загрузить курс SOL из кеша
function loadSolPriceFromCache() {
  try {
    const cached = localStorage.getItem(SOL_PRICE_CACHE_KEY)
    if (cached) {
      const { price, timestamp } = JSON.parse(cached)
      const now = Date.now()
      const cacheAge = now - timestamp

      // Если кеш не старше 5 минут, используем его
      if (cacheAge < SOL_PRICE_UPDATE_INTERVAL) {
        console.log('📦 Loading SOL price from cache:', { price, cacheAge: Math.round(cacheAge / 1000) + 's' })
        return price
      }
    }
  } catch (e) {
    console.warn('⚠️ Failed to load SOL price from cache:', e)
  }
  return null
}

// Сохранить курс SOL в кеш
function saveSolPriceToCache(price) {
  try {
    const cacheData = {
      price,
      timestamp: Date.now()
    }
    localStorage.setItem(SOL_PRICE_CACHE_KEY, JSON.stringify(cacheData))
    console.log('💾 SOL price saved to cache:', price)
  } catch (e) {
    console.warn('⚠️ Failed to save SOL price to cache:', e)
  }
}

// Функция для получения курса SOL из CoinGecko API
async function fetchSolPrice(useCache = true) {
  // Загружаем из кеша, если запрошено
  if (useCache) {
    const cachedPrice = loadSolPriceFromCache()
    if (cachedPrice !== null) {
      solPriceUsd.value = cachedPrice
      console.log('✅ Using cached SOL price:', cachedPrice, 'USD')
      return
    }
  }

  try {
    console.log('🔄 Fetching SOL price from CoinGecko...')
    // Используем CoinGecko API для получения курса SOL
    const response = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd', {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    })

    if (!response.ok) {
      throw new Error(`CoinGecko API error: ${response.status}`)
    }

    const data = await response.json()
    const price = data?.solana?.usd

    if (price && price > 0) {
      const oldPrice = solPriceUsd.value
      solPriceUsd.value = price
      saveSolPriceToCache(price)

      if (oldPrice !== price) {
        console.log('✅ SOL price updated:', { old: oldPrice, new: price })
      } else {
        console.log('✅ SOL price unchanged:', price, 'USD')
      }
    } else {
      throw new Error('Invalid price data from CoinGecko')
    }
  } catch (error) {
    console.error('❌ Error fetching SOL price:', error)
    // При ошибке используем цену из app.prices как fallback
    const fallbackPrice = app.prices?.['SOL'] || 0
    if (fallbackPrice > 0) {
      solPriceUsd.value = fallbackPrice
      console.log('⚠️ Using fallback SOL price from app.prices:', fallbackPrice)
    }
  }
}

// Запустить периодическое обновление курса SOL
function startSolPriceUpdateInterval() {
  // Очищаем существующий интервал
  if (solPriceUpdateInterval) {
    clearInterval(solPriceUpdateInterval)
  }

  console.log('🔄 Starting SOL price update interval (5min)')

  // Обновляем курс каждые 5 минут (без использования кеша)
  solPriceUpdateInterval = setInterval(() => {
    fetchSolPrice(false) // false = не использовать кеш, загружать свежий курс
  }, SOL_PRICE_UPDATE_INTERVAL)
}

// Остановить периодическое обновление курса SOL
function stopSolPriceUpdateInterval() {
  if (solPriceUpdateInterval) {
    clearInterval(solPriceUpdateInterval)
    solPriceUpdateInterval = null
    console.log('⏹️ Stopped SOL price update interval')
  }
}

// Рассчитываем цену за 1000 kW в долларах (Raydium)
const kwPriceUsd = computed(() => {
  if (!solPriceUsd.value || solPriceUsd.value === 0) return 0
  // (1000 kW / 457000 kW) * цена_SOL_USD = цена за 1000 kW в USD
  return (1000 / KW_PER_SOL) * solPriceUsd.value
})

// Цена sBTC с DEXScreener API (динамическое обновление)
const sbtcPriceUsd = ref(0)
const sbtcPriceLoading = ref(false)

// Computed для получения цены sBTC с fallback на данные из dashboard
const sbtcPriceDisplay = computed(() => {
  // Приоритет 1: цена из API
  if (sbtcPriceUsd.value > 0) {
    return sbtcPriceUsd.value
  }
  // Приоритет 2: цена из dashboard (последнее значение из графика)
  const dashboardPrice = app?.dashboard?.sbtc_price || app?.dashboard?.tbtc_price
  if (dashboardPrice && dashboardPrice.length > 0) {
    const lastPrice = dashboardPrice[dashboardPrice.length - 1]?.value
    if (lastPrice && lastPrice > 0) {
      return lastPrice
    }
  }
  // Приоритет 3: цена из app.prices
  if (app?.prices?.['sBTC'] || app?.prices?.['tBTC']) {
    return app.prices['sBTC'] || app.prices['tBTC']
  }
  return 0
})

// Функция для получения цены sBTC с DEXScreener API
const fetchSbtcPrice = async () => {
  if (sbtcPriceLoading.value) return
  sbtcPriceLoading.value = true
  try {
    // DEXScreener API для Solana пары sBTC/SOL
    // Pair address: 4pwynfhs4ucnsae4sozpl5xmdqnl7untcqangf2nnrtj
    const response = await fetch('https://api.dexscreener.com/latest/dex/pairs/solana/4pwynfhs4ucnsae4sozpl5xmdqnl7untcqangf2nnrtj', {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    })

    if (response.ok) {
      const data = await response.json()
      const pair = data?.pairs?.[0]
      if (pair?.priceUsd) {
        sbtcPriceUsd.value = parseFloat(pair.priceUsd)
        console.log('✅ sBTC price from DEXScreener:', sbtcPriceUsd.value)
      } else {
        console.warn('⚠️ sBTC price not found in DEXScreener response')
      }
    } else {
      console.warn('⚠️ DEXScreener API response not OK:', response.status)
    }
  } catch (error) {
    console.error('❌ Error fetching sBTC price from DEXScreener:', error)
  } finally {
    sbtcPriceLoading.value = false
  }
}

const imagePathGems = (path) => {
  if (!path) return null
  const com = computed(() => {
    // Remove @/ prefix if present
    const cleanPath = path.replace(/^@\//, '')
    const fileName = cleanPath.replace(/.*\//, '')
    return new URL(`../assets/market/${fileName}`, import.meta.url).href
  })
  return com
}

// ASICs Shop функции
const all_asics = computed(() => app.getAsicsFromStorage())

const imagePathAsics = (asic) => {
  const com = computed(
    () => new URL(`../assets/asics/${asic?.toString().toUpperCase()}.webp`, import.meta.url).href,
  )
  return com
}

const ASIC_SALE_DISCOUNT = 0.5
const ASIC_SALE_PERCENT = Math.round(ASIC_SALE_DISCOUNT * 100)

const asicsSaleActive = computed(() => {
  // Сначала проверяем флаг от бэкенда
  const userFlag = app?.user?.asic_sale_active
  if (typeof userFlag === 'boolean') {
    return userFlag
  }
  // Затем проверяем localStorage
  if (typeof window !== 'undefined') {
    const storedFlag = localStorage.getItem('asic_sale_active')
    if (storedFlag !== null) {
      return storedFlag === 'true'
    }
  }
  // В конце используем значение из data.js
  return asicsSaleActiveFromData
})

const boostersSaleActive = computed(() => {
  // Сначала проверяем флаг от бэкенда
  const userFlag = app?.user?.booster_sale_active
  if (typeof userFlag === 'boolean') {
    return userFlag
  }
  // Затем проверяем localStorage
  if (typeof window !== 'undefined') {
    const storedFlag = localStorage.getItem('booster_sale_active')
    if (storedFlag !== null) {
      return storedFlag === 'true'
    }
  }
  // В конце используем значение из data.js
  return boostersSaleActiveFromData
})

const shopAsics = computed(() => {
  return asicsSheet
    .map((item, idx) => {
      const basePrice = Number(item.price) || 0
      const manualSale = !!item.sale && typeof item.new_price === 'number'
      const globalSale = asicsSaleActive.value

      let saleFlag = manualSale
      let discountPercent = typeof item.perc === 'number' ? item.perc : null
      let discountedPrice = typeof item.new_price === 'number' ? Number(item.new_price) : null

      if (item.shop && globalSale) {
        saleFlag = true
        discountPercent = ASIC_SALE_PERCENT
        discountedPrice = Number((basePrice * (1 - ASIC_SALE_DISCOUNT)).toFixed(3))
      } else if (saleFlag) {
        if (discountedPrice === null) {
          discountedPrice = Number((basePrice * (1 - ASIC_SALE_DISCOUNT)).toFixed(3))
        }
        if (discountPercent === null) {
          discountPercent = ASIC_SALE_PERCENT
        }
      }

      const payablePrice = saleFlag && discountedPrice !== null
        ? discountedPrice
        : basePrice

      return {
        ...item,
        index: idx,
        sale: saleFlag,
        perc: saleFlag ? discountPercent : item.perc,
        new_price: saleFlag ? discountedPrice : item.new_price,
        original_price: basePrice,
        payablePrice,
        requiresModal: manualSale,
      }
    })
    .filter(item => item.shop)
})

const getShopAsicByIndex = (idx) => shopAsics.value.find(entry => entry.index === idx)

const getRarityColor = (rarity) => {
  switch ((rarity || '').toLowerCase()) {
    case 'rare':
      return '#009600'
    case 'epic':
      return '#0918E9'
    case 'legendary':
      return '#E98509'
    case 'mythic':
      return '#6B25A1'
    case 'common':
    default:
      return '#5D625E'
  }
}

// Функция для конвертации class_X в rarity (для Boosters Shop)
const convertClassToRarity = (classRarity) => {
  switch (classRarity) {
    case 'class_1':
      return 'mythic'
    case 'class_2':
      return 'legendary'
    case 'class_3':
      return 'epic'
    case 'class_4':
      return 'rare'
    default:
      return 'rare'
  }
}

// Функция для получения стиля rarity тега для Boosters Shop (аналогично Power Plants Shop)
const getBoostersRarityStyle = (gemItem) => {
  // Если есть buttonColor, используем его стили
  if (gemItem?.buttonColor === 'gold') {
    return 'background: linear-gradient(270deg, #FEA400 0%, #FCD909 100%), #FFC300; color: #000000;'
  }
  if (gemItem?.buttonColor === 'purple') {
    return 'background: linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(152, 81, 236, 1) 50%, rgba(94, 124, 234, 1) 100%), #FFC300;'
  }
  if (gemItem?.buttonColor === 'blue') {
    return 'background: linear-gradient(270deg, rgba(49, 207, 255, 1) 0%, rgba(31, 255, 255, 1) 100%), #31CFFF; color: #000000;'
  }

  // Конвертируем class_X в rarity и применяем стили как в Power Plants Shop
  const rarity = convertClassToRarity(gemItem?.rarity)

  switch (rarity) {
    case 'mythic':
      return 'background: linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(94, 124, 234, 1) 100%);'
    case 'legendary':
      return 'background-color: #E98509;'
    case 'epic':
      return 'background-color: #0918E9;'
    case 'rare':
      return 'background-color: #009600;'
    case 'common':
    default:
      return 'background-color: #5D625E;'
  }
}

// Функция для получения текста rarity тега для Boosters Shop
const getBoostersRarityText = (gemItem) => {
  if (!gemItem) return ''
  const rarity = convertClassToRarity(gemItem.rarity)
  return t(`boosters_shop.${rarity}`) || t(`power_plants_shop.${rarity}`) || rarity
}

const getOwnedAsicImageKey = (ownedItem) => {
  const address = ownedItem?.nft || ownedItem?.address
  const nameFromSheet = address
    ? getAsicData(address, all_asics.value, asicsSheet, 'name')
    : null

  const rawName = ownedItem?.metadata?.name || nameFromSheet

  if (rawName) {
    return rawName.toUpperCase()
  }

  return 'ASIC S1'
}

const ownedAsicsDisplay = computed(() => {
  const source = cachedAsicNfts.value || []
  return source.map((ownedItem, idx) => {
    const address = ownedItem?.nft || ownedItem?.address
    const nameFromSheet = address
      ? getAsicData(address, all_asics.value, asicsSheet, 'name')
      : null
    const baseName = ownedItem?.metadata?.name || nameFromSheet || ''
    const normalizedName = baseName.replace(/\s+/g, '').toUpperCase()
    const sheetEntry = normalizedName
      ? asicsSheet.find(entry => entry.name.replace(/\s+/g, '').toUpperCase() === normalizedName)
      : null

    const rarityFallback = address
      ? getAsicData(address, all_asics.value, asicsSheet, 'rarity')
      : null
    const hashRateFallback = address
      ? getAsicData(address, all_asics.value, asicsSheet, 'hash_rate')
      : 0
    const speedFallback = address
      ? getAsicData(address, all_asics.value, asicsSheet, 'speed')
      : 0
    const consumptionFallback = address
      ? getAsicData(address, all_asics.value, asicsSheet, 'consumption')
      : 0

    const resolvedName = sheetEntry?.name || baseName || `ASIC #${idx + 1}`
    const rarity = sheetEntry?.rarity || rarityFallback || 'Common'
    const hashRate = sheetEntry?.hash_rate ?? hashRateFallback ?? 0
    const speed = sheetEntry?.speed ?? speedFallback ?? 0
    const consumption = sheetEntry?.consumption ?? consumptionFallback ?? 0

    const imageKey = sheetEntry?.name
      ? sheetEntry.name.toUpperCase()
      : getOwnedAsicImageKey(ownedItem)

    return {
      item: ownedItem,
      idx,
      slot: idx + 1,
      name: resolvedName,
      rarity: rarity || 'Common',
      hashRate,
      speed,
      consumption,
      imageKey,
    }
  })
})

const getTimedNftData = (item) => {
  return app.timed_nfts?.find(el => el.nft_address == (item.address ?? item.nft))
}

// Функция для обновления баланса SOL после транзакции
async function updateSolBalanceAfterTransaction() {
  const publicKey = app.solanaWallet?.publicKey || app.user?.ton_wallet
  if (!publicKey) {
    console.log('⏸️ Skipping balance update: no public key')
    return
  }

  try {
    console.log('🔄 Updating SOL balance after transaction (backend):', publicKey.substring(0, 8) + '...')
    const balance = await solanaWalletService.getSolBalance(publicKey)
    const solAmount = balance / 10 ** 9
    console.log('✅ Balance updated after transaction:', { lamports: balance, sol: solAmount })

    app.setSolBalance(balance)

    window.dispatchEvent(new CustomEvent('sol-balance-updated', {
      detail: { balance, publicKey }
    }))
  } catch (error) {
    console.error('❌ Error updating SOL balance after transaction:', error)
  }
}

const showModal = (status, title, body, openShopOnClose = false) => {
  modalStatus.value = status
  modalTitle.value = title
  modalBody.value = body
  shouldOpenAsicsShopOnClose.value = openShopOnClose
  openModal.value = true
}

const handleModalClose = () => {
  openModal.value = false
  if (shouldOpenAsicsShopOnClose.value) {
    shouldOpenAsicsShopOnClose.value = false
    openAsicsShop()
  }
}

const buyAsics = async (item, price, link, sale, shop = true) => {
  if (!shop) {
    return
  }
  // Проверка браузера перед покупкой (forceShow = true - всегда показываем при попытке покупки)
  if (shouldShowCryptoBrowserNotification(true)) {
    showCryptoBrowserModal.value = true
    return
  }
  // Если есть link - редиректим на внешний сайт
  if (link) {
    window.open(link, '_blank')
    return
  }
  const displayAsic = getShopAsicByIndex(item)
  if (sale) {
    const baseAsic = displayAsic || asicsSheet[item]
    currBuyAsic.value = {
      ...baseAsic,
      index: item,
      price: baseAsic?.original_price ?? baseAsic?.price,
      new_price: baseAsic?.new_price ?? price,
      perc: baseAsic?.perc ?? ASIC_SALE_PERCENT,
      payablePrice: baseAsic?.payablePrice ?? price,
    }
    openSpecialModal.value = true
    return
  }
  if (isProcessing.value) return

  // Проверяем подключение Solana кошелька
  console.log('Wallet connection check:', {
    storeConnected: app.solanaWallet.isConnected,
    storePublicKey: app.solanaWallet.publicKey,
    phantomExists: !!window.solana,
    phantomConnected: window.solana?.isConnected,
    phantomPublicKey: window.solana?.publicKey?.toString()
  })

  if (!app.solanaWallet.isConnected) {
    showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }

  const executePurchase = async () => {
    isProcessing.value = true
    processingType.value = 'purchase'
    purchaseSuccess.value = false
    purchasedAsic.value = null
    purchasedBoost.value = null
    stationActionSuccess.value = false
    stationActionMessage.value = ''
    try {
      const recipientAddress = '8F2aYsinzm7hkcR6LBf8Tx5dQStc9h37cFPY8y69Fd4v'
      const asicData = asicsSheet[item]

      console.log('Покупка ASIC:', asicData.name, 'за', price, 'SOL')

      const transactionResult = await solanaWalletService.sendSolanaTransaction(
        recipientAddress,
        price,
        asicData
      )

      if (transactionResult.success) {
        console.log('✅ Solana транзакция успешна:', transactionResult.signature)
        console.log('Transaction signature type:', typeof transactionResult.signature)
        console.log('Transaction signature value:', transactionResult.signature)

        try {
          let signature = transactionResult.signature
          if (typeof signature !== 'string') {
            signature = signature.signature || signature.toString()
            console.log('Converted signature to string:', signature)
          }

          const purchaseData = {
            asic_name: asicData.name,
            asic_price: price,
            transaction_signature: signature,
            asic_index: item,
            asic_data: {
              hash_rate: asicData.hash_rate,
              consumption: asicData.consumption,
              speed: asicData.speed,
              rarity: asicData.rarity
            }
          }

          console.log('Sending purchase data to backend:', purchaseData)
          const backendResponse = await host.post('asic-purchase-success/', purchaseData)

          if (backendResponse.status === 200) {
            // Сохраняем данные о купленном ASIC для показа в модалке успеха
            purchasedAsic.value = {
              name: asicData.name,
              rarity: asicData.rarity,
              hashRate: asicData.hash_rate,
              speed: asicData.speed,
              consumption: asicData.consumption,
              signature: typeof signature === 'string' ? signature : signature.signature || 'unknown'
            }

            // Переключаемся на состояние успеха
            purchaseSuccess.value = true

            // Запускаем confetti анимацию
            confetti({
              particleCount: 100,
              spread: 70,
              origin: { y: 0.6 },
              colors: ['#31ff80', '#fcd909', '#14F195'],
              zIndex: 100001
            })

            await app.initUser()

            // Обновляем баланс SOL после успешной покупки ASIC (принудительно через бэкенд)
            setTimeout(() => {
              updateSolBalanceAfterTransaction()
            }, 3000) // Задержка 3 секунды, чтобы транзакция точно подтвердилась в блокчейне

            // Автоматически закрываем модалку успеха через 3 секунды
            setTimeout(() => {
              purchaseSuccess.value = false
              isProcessing.value = false
              purchasedAsic.value = null
            }, 3000)
          } else {
            purchaseSuccess.value = false
            purchasedAsic.value = null
            showModal('warning', t('notification.st_attention'),
              t('wallet.topup_error_server'))
          }
        } catch (backendError) {
          console.error('Ошибка при отправке данных на бэкенд:', backendError)
          purchaseSuccess.value = false
          purchasedAsic.value = null
          showModal('warning', t('notification.st_attention'),
            t('wallet.topup_error_server'))
        }
      } else {
        console.error('❌ Solana транзакция не удалась:', transactionResult.error)
        purchaseSuccess.value = false
        purchasedAsic.value = null
        // Проверяем, является ли ошибка недостаточным балансом
        const errorMsg = transactionResult.error || ''
        if (errorMsg.toLowerCase().includes('insufficient balance') || errorMsg.toLowerCase().includes('insufficient funds')) {
          // Если ошибка содержит детали о балансе (Available/Required), показываем полное сообщение
          if (errorMsg.includes('Available') && errorMsg.includes('Required')) {
            showModal('error', t('notification.st_error'), errorMsg)
          } else {
            showModal('error', t('notification.st_error'),
              t('notification.insufficient_funds'))
          }
        } else {
          showModal('error', t('notification.st_error'),
            t('asic_shop.purchase_error', { error: errorMsg }))
        }
      }
    } catch (err) {
      console.error('Общая ошибка при покупке ASIC:', err)
      purchaseSuccess.value = false
      purchasedAsic.value = null
      // Проверяем, является ли ошибка недостаточным балансом
      const errorMsg = err.message || ''
      if (errorMsg.toLowerCase().includes('insufficient balance') || errorMsg.toLowerCase().includes('insufficient funds')) {
        // Если ошибка содержит детали о балансе (Available/Required), показываем полное сообщение
        if (errorMsg.includes('Available') && errorMsg.includes('Required')) {
          showModal('error', t('notification.st_error'), errorMsg)
        } else {
          showModal('error', t('notification.st_error'),
            t('notification.insufficient_funds'))
        }
      } else {
        showModal('error', t('notification.st_error'),
          errorMsg || t('notification.failed_transaction'))
      }
    } finally {
      if (!purchaseSuccess.value) {
        isProcessing.value = false
      }
    }
  }

  // Проверка Phantom Verification перед покупкой
  if (PHANTOM_VERIFICATION_NOTICE) {
    openPhantomConfirmation(() => executePurchase())
    return
  }

  await executePurchase()
}

// Обработка ответа от SpecialPriceModal
const specialModalResponse = async (res) => {
  openSpecialModal.value = false
  if (res.check && currBuyAsic.value) {
    await buyAsics(
      currBuyAsic.value?.index ?? asicsSheet.findIndex((el) => el.name == currBuyAsic.value.name),
      currBuyAsic.value?.payablePrice ?? currBuyAsic.value?.new_price ?? currBuyAsic.value?.price,
      undefined,
      false,
      true,
    )
  }
}

// Функция для открытия ASICs Shop
const openAsicsShop = () => {
  showAsicsShop.value = true
}

// Функция для закрытия ASICs Shop
const closeAsicsShop = () => {
  showAsicsShop.value = false
}

// Функция для открытия Boosters Shop
const openBoostersShop = () => {
  showBoostersShop.value = true
  // Сбрасываем состояние баннера при открытии магазина
  boostersPromoBannerClosed.value = false
}

// Функция для закрытия Boosters Shop
const closeBoostersShop = () => {
  showBoostersShop.value = false
}

// Функция для открытия Power Plants Shop
const openPowerPlantsShop = () => {
  showPowerPlantsShop.value = true
}

// Функция для закрытия Power Plants Shop
const closePowerPlantsShop = () => {
  showPowerPlantsShop.value = false
}

// Функция для форматирования времени постройки в часы
const formatBuildingTime = (duration) => {
  if (!duration) return 0

  let totalSeconds = 0
  let hasDays = false

  // Если duration - строка формата "1 12:00:00" (дни и время)
  if (typeof duration === 'string' && duration.includes(' ')) {
    hasDays = true
    const [daysPart, timePart] = duration.split(' ')
    const days = parseInt(daysPart) || 0
    const [hours, minutes, seconds] = (timePart || '0:0:0').split(':').map(Number)

    totalSeconds = days * 24 * 60 * 60 + (hours || 0) * 60 * 60 + (minutes || 0) * 60 + (seconds || 0)
  }
  // Если duration - строка формата "12:00:00" (только время)
  else if (typeof duration === 'string' && duration.includes(':')) {
    const [hours, minutes, seconds] = duration.split(':').map(Number)
    totalSeconds = (hours || 0) * 60 * 60 + (minutes || 0) * 60 + (seconds || 0)
  }
  // Если duration - число (секунды)
  else if (typeof duration === 'number') {
    totalSeconds = duration
  }
  // Если duration - строка с числом (секунды)
  else {
    totalSeconds = parseInt(duration) || 0
  }

  // Конвертируем в часы
  const totalHours = totalSeconds / 3600

  // Если время без дней и >= 23:59:59 (86399 секунд = 23.999722 часа), показываем 24 часа
  // Для времени с днями просто округляем вверх
  if (!hasDays && totalSeconds >= 86399 && totalSeconds < 86400) {
    return 24
  }

  // Округляем вверх до ближайшего часа
  return Math.ceil(totalHours)
}

// Функция для получения характеристик электростанции из бэкенда
const getPowerPlantStats = (powerPlantItem) => {
  if (!app.stations?.storage_configs || !app.stations?.gen_configs) {
    return {
      storage: powerPlantItem.storage || 0,
      generation: powerPlantItem.generation || 0,
      building: powerPlantItem.building || 0
    }
  }

  // Находим конфиг для уровня 1 этой электростанции (используем нестрогое сравнение как в других местах)
  const storageConfig = app.stations.storage_configs.find(
    (el) => el.station_type == powerPlantItem.type && Number(el.level) === 1
  )
  const genConfig = app.stations.gen_configs.find(
    (el) => el.station_type == powerPlantItem.type && Number(el.level) === 1
  )

  const duration = storageConfig?.duration
  const buildingHours = duration ? formatBuildingTime(duration) : (powerPlantItem.building || 0)

  return {
    storage: storageConfig?.storage_limit || powerPlantItem.storage || 0,
    generation: genConfig?.generation_rate ? Math.round(genConfig.generation_rate) : (powerPlantItem.generation || 0),
    building: buildingHours
  }
}

// Функция для определения boost_type и boost_class из gemItem
const getBoostTypeAndClass = (gemItem) => {
  const type = gemItem?.type
  const rarity = gemItem?.rarity

  if (type === 'Jarvis Bot') {
    const classMap = { 'class_4': 4, 'class_3': 3, 'class_2': 2, 'class_1': 1 }
    return { boost_type: 'jarvis', boost_class: classMap[rarity] || null }
  }
  if (type === 'Cryochamber') {
    const classMap = { 'class_3': 3, 'class_2': 2, 'class_1': 1 }
    return { boost_type: 'cryo', boost_class: classMap[rarity] || null }
  }
  if (type === 'ASIC Manager') {
    const classMap = { 'class_3': 3, 'class_2': 2, 'class_1': 1 }
    return { boost_type: 'asic_manager', boost_class: classMap[rarity] || null }
  }
  if (type === 'Magnetic ring') {
    const classMap = { 'class_2': 2, 'class_1': 1 }
    return { boost_type: 'magnit', boost_class: classMap[rarity] || null }
  }
  if (type === 'Electrics') {
    return { boost_type: 'electrics', boost_class: 1 }
  }

  return null
}

// Функция для покупки буста (аналогично buyAsics)
const buyBoost = async (gemItem, price) => {
  if (isProcessing.value) return

  // Проверка браузера перед покупкой (forceShow = true - всегда показываем при попытке покупки)
  if (shouldShowCryptoBrowserNotification(true)) {
    showCryptoBrowserModal.value = true
    return
  }

  // Проверяем подключение Solana кошелька
  if (!app.solanaWallet.isConnected) {
    showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }

  const executePurchase = async () => {
    isProcessing.value = true
    processingType.value = 'purchase'
    purchaseSuccess.value = false
    purchasedAsic.value = null
    purchasedBoost.value = null
    stationActionSuccess.value = false
    stationActionMessage.value = ''
    try {
      const recipientAddress = '8F2aYsinzm7hkcR6LBf8Tx5dQStc9h37cFPY8y69Fd4v'
      const boostInfo = getBoostTypeAndClass(gemItem)

      if (!boostInfo || !boostInfo.boost_class) {
        showModal('error', t('notification.st_error'), 'Invalid boost type or class')
        isProcessing.value = false
        return
      }

      console.log('Покупка буста:', gemItem.type, 'класс', boostInfo.boost_class, 'за', price, 'SOL')

      const transactionResult = await solanaWalletService.sendSolanaTransaction(
        recipientAddress,
        price,
        gemItem
      )

      if (transactionResult.success) {
        console.log('✅ Solana транзакция успешна:', transactionResult.signature)

        try {
          let signature = transactionResult.signature
          if (typeof signature !== 'string') {
            signature = signature.signature || signature.toString()
            console.log('Converted signature to string:', signature)
          }

          const purchaseData = {
            boost_type: boostInfo.boost_type,
            boost_class: boostInfo.boost_class,
            boost_price: price,
            transaction_signature: signature
          }

          console.log('Sending boost purchase data to backend:', purchaseData)
          const backendResponse = await host.post('boost-purchase-success/', purchaseData)

          if (backendResponse.status === 200) {
            // Сохраняем данные о купленном бустере для показа в модалке успеха
            purchasedBoost.value = {
              name: gemItem.type,
              rarity: gemItem.rarity,
              class: boostInfo.boost_class,
              boostType: boostInfo.boost_type,
              signature: typeof signature === 'string' ? signature : signature.signature || 'unknown',
              gemItem: gemItem
            }

            // Переключаемся на состояние успеха
            purchaseSuccess.value = true

            // Запускаем confetti анимацию
            confetti({
              particleCount: 100,
              spread: 70,
              origin: { y: 0.6 },
              colors: ['#31ff80', '#fcd909', '#14F195'],
              zIndex: 100001
            })

            await app.initUser()

            // Обновляем список купленных бустов
            await fetchBoostAssets()

            // Обновляем баланс SOL после успешной покупки
            setTimeout(() => {
              updateSolBalanceAfterTransaction()
            }, 3000)

            // Автоматически закрываем модалку успеха через 3 секунды
            setTimeout(() => {
              purchaseSuccess.value = false
              isProcessing.value = false
              purchasedBoost.value = null
            }, 3000)
          } else {
            purchaseSuccess.value = false
            purchasedBoost.value = null
            showModal('warning', t('notification.st_attention'),
              t('wallet.topup_error_server'))
          }
        } catch (backendError) {
          console.error('Ошибка при отправке данных на бэкенд:', backendError)
          purchaseSuccess.value = false
          purchasedBoost.value = null
          showModal('warning', t('notification.st_attention'),
            t('wallet.topup_error_server'))
        }
      } else {
        console.error('❌ Solana транзакция не удалась:', transactionResult.error)
        // Проверяем, является ли ошибка недостаточным балансом
        const errorMsg = transactionResult.error || ''
        if (errorMsg.toLowerCase().includes('insufficient balance') || errorMsg.toLowerCase().includes('insufficient funds')) {
          // Если ошибка содержит детали о балансе (Available/Required), показываем полное сообщение
          if (errorMsg.includes('Available') && errorMsg.includes('Required')) {
            showModal('error', t('notification.st_error'), errorMsg)
          } else {
            showModal('error', t('notification.st_error'),
              t('notification.insufficient_funds'))
          }
        } else {
          showModal('error', t('notification.st_error'),
            t('boosters_shop.purchase_error', { error: errorMsg }) || errorMsg || t('notification.failed_transaction'))
        }
      }
    } catch (err) {
      console.error('Общая ошибка при покупке буста:', err)
      // Проверяем, является ли ошибка недостаточным балансом
      const errorMsg = err.message || ''
      if (errorMsg.toLowerCase().includes('insufficient balance') || errorMsg.toLowerCase().includes('insufficient funds')) {
        // Если ошибка содержит детали о балансе (Available/Required), показываем полное сообщение
        if (errorMsg.includes('Available') && errorMsg.includes('Required')) {
          showModal('error', t('notification.st_error'), errorMsg)
        } else {
          showModal('error', t('notification.st_error'),
            t('notification.insufficient_funds'))
        }
      } else {
          showModal('error', t('notification.st_error'),
            errorMsg || t('notification.failed_transaction'))
      }
    } finally {
      if (!purchaseSuccess.value) {
        isProcessing.value = false
        purchasedBoost.value = null
      }
    }
  }

  // Проверка Phantom Verification перед покупкой
  if (PHANTOM_VERIFICATION_NOTICE) {
    openPhantomConfirmation(() => executePurchase())
    return
  }

  await executePurchase()
}

const premiumStationTypes = powerPlantsSheet
  .filter(item => item.shop && item.type !== 'Starter Pack')
  .map(item => item.type)

const hasActivePremiumStation = computed(() => !!app.user?.premium_station_type)
const activePremiumStationLabel = computed(() => app.user?.premium_station_type || '')

const buyPremiumStation = async (gemItem, price) => {
  if (isProcessing.value) return

  // Проверка браузера перед покупкой (forceShow = true - всегда показываем при попытке покупки)
  if (shouldShowCryptoBrowserNotification(true)) {
    showCryptoBrowserModal.value = true
    return
  }

  if (!app.solanaWallet.isConnected) {
    showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }

  const executePurchase = async () => {
    isProcessing.value = true
    processingType.value = 'purchase'
    purchaseSuccess.value = false
    purchasedAsic.value = null
    purchasedBoost.value = null
    stationActionSuccess.value = false
    stationActionMessage.value = ''
    try {
      const recipientAddress = '8F2aYsinzm7hkcR6LBf8Tx5dQStc9h37cFPY8y69Fd4v'

      const transactionResult = await solanaWalletService.sendSolanaTransaction(
        recipientAddress,
        price,
        gemItem
      )

      if (transactionResult.success) {
        try {
          let signature = transactionResult.signature
          if (typeof signature !== 'string') {
            signature = signature.signature || signature.toString()
          }

          const payload = {
            station_type: gemItem.type,
            station_price: price,
            transaction_signature: signature,
          }

          const backendResponse = await host.post('premium-station-purchase-success/', payload)
          if (backendResponse.status === 200) {
            showModal('success', t('notification.st_success'),
              t('premium_station.purchase_success', { station: gemItem.type }))
            await app.initUser()
            // Обновляем список купленных станций
            await fetchPowerPlantsAssets()
            setTimeout(() => {
              updateSolBalanceAfterTransaction()
            }, 3000)
          } else {
            showModal('warning', t('notification.st_attention'), t('wallet.topup_error_server'))
          }
        } catch (backendError) {
          console.error('Ошибка при отправке данных на бэкенд:', backendError)
          showModal('warning', t('notification.st_attention'), t('wallet.topup_error_server'))
        }
      } else {
        const errorMsg = transactionResult.error || ''
        if (errorMsg.toLowerCase().includes('insufficient balance') || errorMsg.toLowerCase().includes('insufficient funds')) {
          if (errorMsg.includes('Available') && errorMsg.includes('Required')) {
            showModal('error', t('notification.st_error'), errorMsg)
          } else {
            showModal('error', t('notification.st_error'), t('notification.insufficient_funds'))
          }
        } else {
          showModal('error', t('notification.st_error'), errorMsg || t('notification.failed_transaction'))
        }
      }
    } catch (err) {
      const errorMsg = err.message || ''
      if (errorMsg.toLowerCase().includes('insufficient balance') || errorMsg.toLowerCase().includes('insufficient funds')) {
        if (errorMsg.includes('Available') && errorMsg.includes('Required')) {
          showModal('error', t('notification.st_error'), errorMsg)
        } else {
          showModal('error', t('notification.st_error'), t('notification.insufficient_funds'))
        }
      } else {
        showModal('error', t('notification.st_error'), errorMsg || t('notification.failed_transaction'))
      }
    } finally {
      isProcessing.value = false
    }
  }

  if (PHANTOM_VERIFICATION_NOTICE) {
    openPhantomConfirmation(() => executePurchase())
    return
  }

  await executePurchase()
}

// Функция для покупки бустера/станции/стартер пака
const buyGem = async (gemItem) => {
  if (!gemItem?.shop) return

  // Проверка браузера перед покупкой (forceShow = true - всегда показываем при попытке покупки)
  if (shouldShowCryptoBrowserNotification(true)) {
    showCryptoBrowserModal.value = true
    return
  }

  // Премиальные станции через бекенд SOL
  if (premiumStationTypes.includes(gemItem?.type)) {
    const stationPrice = gemsSaleActive && gemItem?.enableSale !== false ? getGemPrice(gemItem) : gemItem.price
    await buyPremiumStation(gemItem, stationPrice)
    return
  }

  // Проверяем, является ли это бустом для покупки через Solana
  const boostInfo = getBoostTypeAndClass(gemItem)
  if (boostInfo && boostInfo.boost_class) {
    // Это буст - используем покупку через Solana
    const boostPrice = boostersSaleActive.value && gemItem?.enableSale !== false
      ? getBoosterPrice(gemItem)
      : gemItem.price

    await buyBoost(gemItem, boostPrice)
    return
  }

  // Если это стартер пакет - используем отправку SOL
  if (gemItem?.type === 'Starter Pack') {
    if (isProcessing.value) return
    isProcessing.value = true
    processingType.value = 'purchase'
    purchaseSuccess.value = false
    purchasedAsic.value = null
    purchasedBoost.value = null
    stationActionSuccess.value = false
    stationActionMessage.value = ''

    if (!app.solanaWallet.isConnected) {
      showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
      isProcessing.value = false
      processingType.value = 'purchase'
      return
    }

    try {
      const transferAmount = gemsSaleActive ? getGemPrice(gemItem) : gemItem.price
      const recipientAddress = '8F2aYsinzm7hkcR6LBf8Tx5dQStc9h37cFPY8y69Fd4v'

      console.log('Покупка Starter Pack за', transferAmount, 'SOL')

      const transactionResult = await solanaWalletService.sendSolanaTransaction(
        recipientAddress,
        transferAmount,
        null
      )

      if (transactionResult.success) {
        try {
          await host.post('gem-purchase-success/', {
            gem_type: gemItem.type,
            price: transferAmount,
            transaction_signature: transactionResult.signature
          })
          showModal('success', t('notification.st_success'), `Успешно куплен Starter Pack за ${transferAmount} SOL!`)
          await app.initUser()
        } catch (backendError) {
          console.error('Ошибка при отправке данных на бэкенд:', backendError)
          showModal('warning', t('notification.st_attention'), t('wallet.topup_error_server'))
        }
      } else {
        showModal('error', t('notification.st_error'), t('notification.failed_transaction'))
      }
    } catch (err) {
      console.error('Error in buyGem:', err)
      showModal('error', t('notification.st_error'), err.message || t('notification.failed_transaction'))
    } finally {
      isProcessing.value = false
    }
  } else {
    // Для всех остальных - редирект на getgems.io или внешний сайт
    const link = gemItem?.link || 'https://getgems.io'
    window.open(link, '_blank')
  }
}

// Обработчики для модалок бустеров
const handleGemInfoClick = (gemItem) => {
  if (gemItem?.info === 'starter_pack_modal') {
    openStarterPackInfo.value = true
  } else if (gemItem?.info === 'gems.dao_owner_info') {
    openDaoOwnerInfo.value = true
  } else if (gemItem?.info === 'hydroelectric_power_plant_modal') {
    openHydroelectricInfo.value = true
  } else if (gemItem?.info === 'orbital_power_plant_modal') {
    openOrbitalInfo.value = true
  } else {
    gemInfoText.value = gemItem?.info || ''
    currentGemItem.value = gemItem
    openGemInfo.value = true
  }
}

const buyCurrentGem = () => {
  if (currentGemItem.value) {
    buyGem(currentGemItem.value)
  }
}

const buyDaoOwner = () => {
  const daoOwner = gemsSheet.find(gem => gem.type === 'DAO Owner')
  if (daoOwner) {
    buyGem(daoOwner)
  }
}

const buyStarterPack = async () => {
  if (isProcessing.value) return

  // Проверка браузера перед покупкой (forceShow = true - всегда показываем при попытке покупки)
  if (shouldShowCryptoBrowserNotification(true)) {
    showCryptoBrowserModal.value = true
    return
  }

  // Проверяем подключение Solana кошелька
  if (!app.solanaWallet.isConnected) {
    showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }

  const executePurchase = async () => {
    isProcessing.value = true
    processingType.value = 'purchase'
    purchaseSuccess.value = false
    purchasedAsic.value = null
    purchasedBoost.value = null
    stationActionSuccess.value = false
    stationActionMessage.value = ''
    try {
      const starterPack = powerPlantsSheet.find(gem => gem.type === 'Starter Pack')
      if (!starterPack) {
        showModal('error', t('notification.st_error'), 'Starter Pack not found')
        return
      }

      const recipientAddress = '8F2aYsinzm7hkcR6LBf8Tx5dQStc9h37cFPY8y69Fd4v'
      const price = getStarterPackPriceDisplay()

      console.log('Покупка Starter Pack за', price, 'SOL')

      const transactionResult = await solanaWalletService.sendSolanaTransaction(
        recipientAddress,
        price,
        starterPack
      )

      if (transactionResult.success) {
        console.log('✅ Solana транзакция успешна:', transactionResult.signature)

        // БЕЗ проверки бекендом - просто показываем успех
        showModal('success', t('notification.st_success'),
          `Starter Pack purchased successfully for ${price} SOL!`)

        // Обновляем баланс SOL после успешной покупки
        setTimeout(() => {
          updateSolBalanceAfterTransaction()
        }, 3000)
      } else {
        console.error('❌ Solana транзакция не удалась:', transactionResult.error)
        const errorMsg = transactionResult.error || ''
        if (errorMsg.toLowerCase().includes('insufficient balance') || errorMsg.toLowerCase().includes('insufficient funds')) {
          if (errorMsg.includes('Available') && errorMsg.includes('Required')) {
            showModal('error', t('notification.st_error'), errorMsg)
          } else {
            showModal('error', t('notification.st_error'), t('notification.insufficient_funds'))
          }
        } else {
          showModal('error', t('notification.st_error'), errorMsg || t('notification.failed_transaction'))
        }
      }
    } catch (err) {
      console.error('Общая ошибка при покупке Starter Pack:', err)
      const errorMsg = err.message || ''
      if (errorMsg.toLowerCase().includes('insufficient balance') || errorMsg.toLowerCase().includes('insufficient funds')) {
        if (errorMsg.includes('Available') && errorMsg.includes('Required')) {
          showModal('error', t('notification.st_error'), errorMsg)
        } else {
          showModal('error', t('notification.st_error'), t('notification.insufficient_funds'))
        }
      } else {
        showModal('error', t('notification.st_error'), errorMsg || t('notification.failed_transaction'))
      }
    } finally {
      isProcessing.value = false
    }
  }

  // Проверка Phantom Verification перед покупкой
  if (PHANTOM_VERIFICATION_NOTICE) {
    openPhantomConfirmation(() => executePurchase())
    return
  }

  await executePurchase()
}

const buyHydroelectric = () => {
  const hydroelectric = gemsSheet.find(gem => gem.type === 'Hydroelectric Power Plant')
  if (hydroelectric) {
    buyGem(hydroelectric)
  }
  openHydroelectricInfo.value = false
}

const buyHydroelectricFromCraft = () => {
  openOrbitalCraftInfo.value = false
  setTimeout(() => {
    buyHydroelectric()
  }, 300)
}

const disablePremiumStation = async () => {
  if (isProcessing.value) return
  // Показываем модальное окно подтверждения
  openDisableStationConfirm.value = true
}

const executeDisablePremiumStation = async () => {
  if (isProcessing.value) return
  isProcessing.value = true
  processingType.value = 'disable'
  stationActionSuccess.value = false
  stationActionMessage.value = ''
  purchaseSuccess.value = false
  purchasedAsic.value = null
  try {
    const resp = await host.post('disable-premium-station/')
    if (resp.status === 200) {
      stationActionSuccess.value = true
      stationActionMessage.value = t('premium_station.disable_success')
      await app.initUser()
      // Обновляем список купленных станций
      await fetchPowerPlantsAssets()
      // Автоматически закрываем модальное окно через 3 секунды
      setTimeout(() => {
        stationActionSuccess.value = false
        isProcessing.value = false
        processingType.value = 'purchase'
        stationActionMessage.value = ''
      }, 3000)
    } else {
      isProcessing.value = false
      processingType.value = 'purchase'
      showModal('error', t('notification.st_error'), t('premium_station.disable_error'))
    }
  } catch (err) {
    console.error('Disable premium station error:', err)
    isProcessing.value = false
    processingType.value = 'purchase'
    showModal('error', t('notification.st_error'), t('premium_station.disable_error'))
  }
}

const handleDisableStationConfirm = async (event) => {
  const confirmed = event?.check || false
  openDisableStationConfirm.value = false
  if (confirmed) {
    await executeDisablePremiumStation()
  }
}

const activatePremiumStation = async (stationType, assetId) => {
  if (isProcessing.value) return

  // Проверяем, есть ли уже активная премиальная станция
  const currentActiveStation = app.user?.premium_station_type
  if (currentActiveStation && currentActiveStation !== stationType) {
    // Показываем модальное окно подтверждения
    pendingStationToActivate.value = { stationType, assetId }
    openSwitchStationConfirm.value = true
    return
  }

  // Если нет активной станции или это та же станция, активируем напрямую
  await executeActivatePremiumStation(stationType, assetId)
}

const executeActivatePremiumStation = async (stationType, assetId) => {
  if (isProcessing.value) return
  isProcessing.value = true
  processingType.value = 'activate'
  stationActionSuccess.value = false
  stationActionMessage.value = ''
  purchaseSuccess.value = false
  purchasedAsic.value = null
  try {
    const resp = await host.post('enable-premium-station/', {
      station_type: stationType,
      asset_id: assetId
    })
    if (resp.status === 200) {
      stationActionSuccess.value = true
      // Убеждаемся, что stationType - это строка, а не объект
      const stationName = typeof stationType === 'string' ? stationType : (stationType?.stationType || stationType?.name || 'Premium power plant')
      stationActionMessage.value = t('premium_station.activate_success', { station: stationName }) || `Premium power plant ${stationName} activated`
      await app.initUser()
      // Обновляем список купленных станций
      await fetchPowerPlantsAssets()
      // Автоматически закрываем модальное окно через 3 секунды
      setTimeout(() => {
        stationActionSuccess.value = false
        isProcessing.value = false
        processingType.value = 'purchase'
        stationActionMessage.value = ''
      }, 3000)
    } else {
      isProcessing.value = false
      processingType.value = 'purchase'
      showModal('error', t('notification.st_error'), t('premium_station.activate_error'))
    }
  } catch (err) {
    console.error('Activate premium station error:', err)
    isProcessing.value = false
    processingType.value = 'purchase'
    showModal('error', t('notification.st_error'),
      err.response?.data?.error || t('premium_station.activate_error'))
  }
}

const getSwitchConfirmationMessage = () => {
  const currentStation = app.user?.premium_station_type || ''
  const newStation = typeof pendingStationToActivate.value === 'object'
    ? pendingStationToActivate.value.stationType
    : pendingStationToActivate.value || ''
  const message = t('premium_station.switch_confirmation_message', {
    current: currentStation,
    new: newStation
  })
  // Выделяем названия станций желтым цветом
  let formattedMessage = message
  if (currentStation) {
    formattedMessage = formattedMessage.replace(
      currentStation,
      `<span style="color: #ffc300; font-weight: bold;">${currentStation}</span>`
    )
  }
  if (newStation) {
    formattedMessage = formattedMessage.replace(
      newStation,
      `<span style="color: #ffc300; font-weight: bold;">${newStation}</span>`
    )
  }
  return formattedMessage
}

const getDisableConfirmationMessage = () => {
  const currentStation = app.user?.premium_station_type || ''
  const message = t('premium_station.disable_confirmation_message', {
    station: currentStation
  })
  // Выделяем название станции желтым цветом
  let formattedMessage = message
  if (currentStation) {
    formattedMessage = formattedMessage.replace(
      currentStation,
      `<span style="color: #ffc300; font-weight: bold;">${currentStation}</span>`
    )
  }
  return formattedMessage
}

const handleSwitchStationConfirm = async (event) => {
  const confirmed = event?.check || false
  openSwitchStationConfirm.value = false
  if (!confirmed || !pendingStationToActivate.value) {
    pendingStationToActivate.value = null
    return
  }

  const stationToActivate = pendingStationToActivate.value
  const stationType = typeof stationToActivate === 'object' ? stationToActivate.stationType : stationToActivate
  const assetId = typeof stationToActivate === 'object' ? stationToActivate.assetId : null
  pendingStationToActivate.value = null

  // Сначала отключаем текущую станцию
  if (isProcessing.value) return
  isProcessing.value = true
  processingType.value = 'disable'
  stationActionSuccess.value = false
  stationActionMessage.value = ''
  purchaseSuccess.value = false
  purchasedAsic.value = null

  try {
    // Отключаем текущую станцию
    const disableResp = await host.post('disable-premium-station/')
    if (disableResp.status === 200) {
      await app.initUser()
      await fetchPowerPlantsAssets()

      // Теперь активируем новую станцию
      processingType.value = 'activate'
      const activateResp = await host.post('enable-premium-station/', {
        station_type: stationType,
        asset_id: assetId
      })
      if (activateResp.status === 200) {
        stationActionSuccess.value = true
        // Используем stationType, который уже извлечен из объекта
        stationActionMessage.value = t('premium_station.activate_success', { station: stationType }) || `Premium power plant ${stationType} activated`
        await app.initUser()
        await fetchPowerPlantsAssets()
        // Автоматически закрываем модальное окно через 3 секунды
        setTimeout(() => {
          stationActionSuccess.value = false
          isProcessing.value = false
          processingType.value = 'purchase'
          stationActionMessage.value = ''
        }, 3000)
      } else {
        isProcessing.value = false
        processingType.value = 'purchase'
        showModal('error', t('notification.st_error'), t('premium_station.activate_error'))
      }
    } else {
      isProcessing.value = false
      processingType.value = 'purchase'
      showModal('error', t('notification.st_error'), t('premium_station.disable_error'))
    }
  } catch (err) {
    console.error('Switch premium station error:', err)
    isProcessing.value = false
    processingType.value = 'purchase'
    showModal('error', t('notification.st_error'),
      err.response?.data?.error || t('premium_station.activate_error'))
  }
}

const getStarterPackPriceDisplay = () => {
  // Ищем Starter Pack в powerPlantsSheet, так как он там находится
  const starterPack = powerPlantsSheet.find(gem => gem.type === 'Starter Pack')
  if (!starterPack) return 8.6
  return getStarterPackPrice(starterPack)
}

const getStarterPackOriginalPrice = () => {
  const starterPack = powerPlantsSheet.find(gem => gem.type === 'Starter Pack')
  if (!starterPack) return 17.2
  return starterPack.originalPrice || starterPack.price
}

const copyAddress = async (address) => {
  await navigator.clipboard.writeText(address)
  showModal('success', t('notification.st_success'), t('notification.address_copied'))
}

// Обновление NFT данных
const updateAsicNfts = () => {
  const upd_nfts = _.concat(app?.nfts?.filter(el => !app?.rentOutNfts?.some(item => item?.nft == el?.address) && (el?.metadata?.name?.toLowerCase()?.includes('asic') || el?.metadata?.name?.toLowerCase()?.includes('sbt'))) || [], app?.rentedNfts || [])
  if (JSON.stringify(upd_nfts) !== JSON.stringify(cachedAsicNfts.value)) {
    cachedAsicNfts.value = upd_nfts
  }
}

// Инициализация NFT данных при открытии ASICs Shop
watch(showAsicsShop, (isOpen) => {
  if (isOpen) {
    updateAsicNfts()
    app.initUser().then(() => {
      updateAsicNfts()
    })
  }
})

// Автоматическое обновление NFT данных при изменении app.nfts или app.rentedNfts
watch([() => app.nfts, () => app.rentedNfts], () => {
  if (showAsicsShop.value) {
    updateAsicNfts()
  }
}, { deep: true })

// Функция для получения купленных бустов с бэкенда
const fetchBoostAssets = async () => {
  try {
    const response = await host.get('user-boost-assets/')
    if (response.data && Array.isArray(response.data)) {
      cachedBoostAssets.value = response.data
    } else {
      cachedBoostAssets.value = []
    }
  } catch (error) {
    console.error('Ошибка при получении купленных бустов:', error)
    cachedBoostAssets.value = []
  }
}

// Функция для получения купленных премиальных станций с бэкенда
const fetchPowerPlantsAssets = async () => {
  try {
    const response = await host.get('user-premium-stations/')
    if (response.data && Array.isArray(response.data)) {
      cachedPowerPlantsAssets.value = response.data
    } else {
      cachedPowerPlantsAssets.value = []
    }
  } catch (error) {
    console.error('Ошибка при получении купленных премиальных станций:', error)
    cachedPowerPlantsAssets.value = []
  }
}

// Получаем уровень станции пользователя (индекс станции в списке + 1, как в бекенде)
const userStationLevel = computed(() => {
  if (!app.user?.station_type) return null

  // Список станций в порядке возрастания уровня (как в бекенде get_station_level)
  const STATION_LEVELS = [
    "Boiler house",
    "Coal power plant",
    "Thermal power plant",
    "Geothermal power plant",
    "Nuclear power plant",
    "Thermonuclear power plant",
    "Dyson Sphere",
    "Neutron star",
    "Antimatter",
    "Galactic core",
  ]

  // ВАЖНО: Если есть активная премиальная станция, используем маппинг (как на бэкенде)
  let stationTypeToCheck = app.user.station_type
  if (app.user.premium_station_type) {
    // Маппинг премиальных станций на обычные
    const premiumMapping = {
      'Hydroelectric Power Plant': 'Nuclear power plant',
      'Orbital Power Plant': 'Thermonuclear power plant',
    }
    const mappedType = premiumMapping[app.user.premium_station_type]
    if (mappedType) {
      stationTypeToCheck = mappedType
    }
  }

  const stationIndex = STATION_LEVELS.indexOf(stationTypeToCheck)
  if (stationIndex === -1) return null

  // Возвращаем индекс + 1 (как в бекенде: get_station_level() + 1)
  return stationIndex + 1
})

// Получаем хешрейт пользователя (в Gh/s)
const userHashrate = computed(() => {
  if (!app.user?.mining_farm_speed && app.user?.mining_farm_speed !== 0) return null
  return app.user.mining_farm_speed // Уже в Gh/s
})

// Функция для проверки соответствия требования power_plant_lvl
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

// Функция для проверки соответствия требования gh_s
const checkHashrateMatch = (benefit) => {
  if (!benefit || typeof benefit !== 'string') return false
  if (!benefit.includes('gh_s:')) return false
  if (userHashrate.value === null) return false

  // Проверяем формат "gh_s: 1200+" (с плюсом)
  const plusMatch = benefit.match(/gh_s:\s*(\d+)\+/)
  if (plusMatch) {
    const minHashrate = parseFloat(plusMatch[1])
    return userHashrate.value >= minHashrate
  }

  // Проверяем формат "gh_s: 1-299" (диапазон)
  const rangeMatch = benefit.match(/gh_s:\s*(\d+)-(\d+)/)
  if (rangeMatch) {
    const minHashrate = parseFloat(rangeMatch[1])
    const maxHashrate = parseFloat(rangeMatch[2])
    return userHashrate.value >= minHashrate && userHashrate.value <= maxHashrate
  }

  return false
}

// Инициализация бустов при открытии Boosters Shop
watch(showBoostersShop, (isOpen) => {
  if (isOpen) {
    // Сбрасываем состояние баннера при открытии магазина
    boostersPromoBannerClosed.value = false
    fetchBoostAssets()
    app.initUser().then(() => {
      fetchBoostAssets()
    })
  }
})

// Инициализация премиальных станций при открытии Power Plants Shop
watch(showPowerPlantsShop, (isOpen) => {
  if (isOpen) {
    fetchPowerPlantsAssets()
    app.initUser().then(() => {
      fetchPowerPlantsAssets()
    })
  }
})

// Computed для отображения купленных бустов
const ownedBoostersDisplay = computed(() => {
  if (!cachedBoostAssets.value || !Array.isArray(cachedBoostAssets.value) || cachedBoostAssets.value.length === 0) {
    return []
  }

  if (!gemsSheet || !Array.isArray(gemsSheet) || gemsSheet.length === 0) {
    return []
  }

  // Получаем активные бусты из get_active_boosts() (как на бекенде)
  // Активен только один буст каждого типа И класса (первый найденный, который соответствует условиям)
  const activeBoostKeys = new Set()  // Храним ключи (boost_type, boost_class) активных бустов

  // Сортируем бусты по purchase_time (новые первыми) для консистентности
  const sortedAssets = [...cachedBoostAssets.value].sort((a, b) => {
    const timeA = new Date(a.purchase_time || 0).getTime()
    const timeB = new Date(b.purchase_time || 0).getTime()
    return timeB - timeA
  })

  const mapped = sortedAssets.map((boostAsset, idx) => {
    // Находим соответствующий gemItem из gemsSheet
    const boostTypeMap = {
      'jarvis': 'Jarvis Bot',
      'cryo': 'Cryochamber',
      'asic_manager': 'ASIC Manager',
      'magnit': 'Magnetic ring',
      'electrics': 'Electrics',
    }

    const boostTypeName = boostTypeMap[boostAsset.boost_type] || boostAsset.boost_type
    const rarityMap = {
      1: 'class_1',
      2: 'class_2',
      3: 'class_3',
      4: 'class_4',
    }
    const rarity = rarityMap[boostAsset.boost_class] || 'class_4'

    // Ищем соответствующий элемент в gemsSheet (gemsSheet - это обычный массив, не ref)
    const gemItem = gemsSheet.find(item => {
      if (boostAsset.boost_type === 'jarvis' && item.type === 'Jarvis Bot') {
        return item.rarity === rarity
      } else if (boostAsset.boost_type === 'cryo' && item.type === 'Cryochamber') {
        return item.rarity === rarity
      } else if (boostAsset.boost_type === 'asic_manager' && item.type === 'ASIC Manager') {
        return item.rarity === rarity
      } else if (boostAsset.boost_type === 'magnit' && item.type === 'Magnetic ring') {
        return item.rarity === rarity
      } else if (boostAsset.boost_type === 'electrics' && item.type === 'Electrics') {
        return true
      }
      return false
    })

    // Убираем класс из названия, так как он отображается в плашке ниже
    let cleanName = boostAsset.name || ''
    // Убираем паттерны типа "Class 1", "Class 2", "Class 3", "Class 4" из названия (в любом месте строки)
    cleanName = cleanName.replace(/\s*Class\s+\d+\s*/gi, '').trim()

    // Определяем, активен ли этот буст
    // Активен только если: условия выполнены И буст включен И это первый буст этого типа И класса
    const conditionsMet = boostAsset.conditions_met || false
    const isEnabled = boostAsset.is_enabled !== undefined ? boostAsset.is_enabled : true
    const boostKey = `${boostAsset.boost_type}_${boostAsset.boost_class}`
    const isFirstOfTypeClass = !activeBoostKeys.has(boostKey)
    // Используем is_active с бэкенда, но также проверяем локально для консистентности
    const isActive = (boostAsset.is_active !== undefined ? boostAsset.is_active : false) && isFirstOfTypeClass

    // Если буст активен, добавляем его ключ в множество активных ключей
    if (isActive) {
      activeBoostKeys.add(boostKey)
    }

    return {
      boostAsset,
      gemItem: gemItem || null,
      idx,
      slot: idx + 1,
      name: cleanName,
      boost_type: boostAsset.boost_type,
      boost_class: boostAsset.boost_class,
      is_active: isActive,
      is_enabled: isEnabled,
      conditions_met: conditionsMet,
      purchase_time: boostAsset.purchase_time,
    }
  })

  return mapped
})

// Обработчик переключения на вкладку Your
const handleShowOwnedPowerPlants = async () => {
  showOwnedPowerPlants.value = true
  await fetchPowerPlantsAssets()
}

// Computed для отображения купленных премиальных станций
const ownedPowerPlantsDisplay = computed(() => {
  if (!cachedPowerPlantsAssets.value || !Array.isArray(cachedPowerPlantsAssets.value) || cachedPowerPlantsAssets.value.length === 0) {
    return []
  }

  if (!powerPlantsSheet || !Array.isArray(powerPlantsSheet) || powerPlantsSheet.length === 0) {
    return []
  }

  return cachedPowerPlantsAssets.value.map((asset, idx) => {
    // Получаем название станции из asset_name или metadata
    const stationName = asset.asset_name || asset.metadata?.station_type || asset.metadata?.name || ''

    // Находим соответствующий powerPlantItem из powerPlantsSheet
    const powerPlantItem = powerPlantsSheet.find(item => item.type === stationName)

    // Проверяем, активна ли эта конкретная станция (по asset.id)
    // premium_station_asset может быть объектом {id: ...} или просто числом
    const activeAssetId = app.user?.premium_station_asset?.id || app.user?.premium_station_asset
    const isActive = activeAssetId === asset.id

    return {
      asset,
      powerPlantItem: powerPlantItem || null,
      idx,
      slot: idx + 1,
      name: stationName,
      is_active: isActive,
      purchase_time: asset.purchase_time,
    }
  })
})

// Функция для получения информации о требованиях бустера
const getBoostRequirements = (owned) => {
  if (!owned.gemItem || !owned.gemItem.benefits) return { powerPlantLevel: null, hashrate: null }

  let powerPlantLevel = null
  let hashrate = null

  for (const benefit of owned.gemItem.benefits) {
    if (benefit.includes('power_plant_lvl:')) {
      const match = benefit.match(/power_plant_lvl:\s*(\d+)-(\d+)/)
      if (match) {
        powerPlantLevel = { min: parseInt(match[1]), max: parseInt(match[2]) }
      }
    } else if (benefit.includes('gh_s:')) {
      // Проверяем формат "gh_s: 1200+" (с плюсом)
      const plusMatch = benefit.match(/gh_s:\s*(\d+)\+/)
      if (plusMatch) {
        hashrate = { min: parseFloat(plusMatch[1]), max: Infinity }
      } else {
        // Проверяем формат "gh_s: 1-299" (диапазон)
        const rangeMatch = benefit.match(/gh_s:\s*(\d+)-(\d+)/)
        if (rangeMatch) {
          hashrate = { min: parseFloat(rangeMatch[1]), max: parseFloat(rangeMatch[2]) }
        }
      }
    }
  }

  return { powerPlantLevel, hashrate }
}

// Функция для определения нужного диапазона уровней для текущего уровня пользователя
const getRequiredLevelRange = (currentLevel) => {
  // Диапазоны уровней для бустеров (как в бекенде)
  const levelRanges = [
    { min: 1, max: 3 },   // class_4
    { min: 4, max: 5 },   // class_3
    { min: 6, max: 7 },   // class_2
    { min: 8, max: 9 },   // class_1
  ]

  for (const range of levelRanges) {
    if (currentLevel >= range.min && currentLevel <= range.max) {
      return range
    }
  }

  return null
}

// Функция для определения нужного диапазона хешрейта для текущего хешрейта пользователя
const getRequiredHashrateRange = (currentHashrate, boostType) => {
  if (boostType === 'asic_manager') {
    // ASIC Manager: class_3 (1-299), class_2 (300-1199), class_1 (1200+)
    if (currentHashrate >= 1 && currentHashrate < 300) {
      return { min: 1, max: 299 }
    } else if (currentHashrate >= 300 && currentHashrate < 1200) {
      return { min: 300, max: 1199 }
    } else if (currentHashrate >= 1200) {
      return { min: 1200, max: Infinity }
    }
  } else if (boostType === 'magnit') {
    // Magnetic ring: class_2 (1-249), class_1 (250-599)
    // Максимальный диапазон 250-599, выше не существует
    if (currentHashrate >= 1 && currentHashrate < 250) {
      return { min: 1, max: 249 }
    } else if (currentHashrate >= 250 && currentHashrate < 600) {
      return { min: 250, max: 599 }
    } else if (currentHashrate >= 600) {
      // Для хешрейта >= 600 нет подходящего Magnetic ring
      return null
    }
  }

  return null
}

// Функция для показа модального окна с информацией о несоответствии условий
const showBoostConditionsModal = (owned) => {
  const requirements = getBoostRequirements(owned)

  let message = ''

  // Определяем какой тип требования не выполнен
  if (requirements.powerPlantLevel) {
    const levelMatch = checkPowerPlantLevelMatch(`power_plant_lvl:${requirements.powerPlantLevel.min}-${requirements.powerPlantLevel.max}`)
    if (!levelMatch && userStationLevel.value !== null) {
      const requiredRange = getRequiredLevelRange(userStationLevel.value)
      const requiredLevelText = requiredRange ? `${requiredRange.min}-${requiredRange.max}` : 'N/A'

      message = `This booster is not designed for your current Power Plant level (Level ${userStationLevel.value}).\n\nThis booster requires Power Plant level <span style="background: #FCD909; color: #000; padding: 2px 6px; border-radius: 4px; font-weight: 500;">${requirements.powerPlantLevel.min}-${requirements.powerPlantLevel.max}</span>.\n\nYou need a booster designed for Power Plant level <span style="background: #FCD909; color: #000; padding: 2px 6px; border-radius: 4px; font-weight: 500;">${requiredLevelText}</span>.`
    }
  }

  if (requirements.hashrate) {
    const hashrateMatch = checkHashrateMatch(`gh_s:${requirements.hashrate.min}-${requirements.hashrate.max}`)
    if (!hashrateMatch && userHashrate.value !== null) {
      const requiredRange = getRequiredHashrateRange(userHashrate.value, owned.boost_type)

      if (message) message += '\n\n'

      if (owned.boost_type === 'magnit' && userHashrate.value >= 600) {
        // Для Magnetic ring нет буста для хешрейта >= 600
        message += `This booster is not designed for your current ASICs hashrate (${userHashrate.value.toFixed(1)} Gh/s).\n\nThis booster requires ASICs hashrate <span style="background: #FCD909; color: #000; padding: 2px 6px; border-radius: 4px; font-weight: 500;">${requirements.hashrate.min}-${requirements.hashrate.max} Gh/s</span>.\n\nA booster for your ASICs hashrate does not exist.`
      } else {
        const requiredHashrateText = requiredRange
          ? (requiredRange.max === Infinity
              ? `${requiredRange.min}+ Gh/s`
              : `${requiredRange.min}-${requiredRange.max} Gh/s`)
          : 'N/A'
        message += `This booster is not designed for your current ASICs hashrate (${userHashrate.value.toFixed(1)} Gh/s).\n\nThis booster requires ASICs hashrate <span style="background: #FCD909; color: #000; padding: 2px 6px; border-radius: 4px; font-weight: 500;">${requirements.hashrate.min}-${requirements.hashrate.max} Gh/s</span>.\n\nYou need a booster designed for ASICs hashrate <span style="background: #FCD909; color: #000; padding: 2px 6px; border-radius: 4px; font-weight: 500;">${requiredHashrateText}</span>.`
      }
    }
  }

  // Используем v-html в slot, стили применятся автоматически из InfoModal
  boostConditionsInfoHtml.value = message.replace(/\n/g, '<br>')

  openBoostConditionsInfo.value = true
}

// Обработчик закрытия модального окна условий бустера
const handleBoostConditionsModalClose = (payload) => {
  openBoostConditionsInfo.value = false
  if (payload?.check) {
    // Открываем вкладку Boosters
    showOwnedBoosters.value = false
  }
}

// Функция для переключения активности буста
const toggleBoost = async (boostAssetId) => {
  try {
    const response = await host.post('toggle-boost-asset/', {
      boost_asset_id: boostAssetId
    })

    if (response.status === 200) {
      // ВАЖНО: Обновляем данные пользователя чтобы фронт получил актуальные *_expires поля
      await app.initUser()
      // Обновляем список бустов
      await fetchBoostAssets()

      // Показываем уведомление
      const isEnabled = response.data.is_enabled
      showModal(
        'success',
        t('notification.st_success'),
        isEnabled
          ? t('boosters_shop.boost_enabled') || 'Boost enabled'
          : t('boosters_shop.boost_disabled') || 'Boost disabled'
      )
    }
  } catch (error) {
    console.error('Ошибка при переключении буста:', error)
    showModal('error', t('notification.st_error'),
      error.response?.data?.error || t('notification.failed_transaction'))
  }
}

const direct = (link) => {
  if (link.includes('t.me')) {
    return tg?.openTelegramLink(link)
  }
  // Для внешних ссылок (Twitter, Discord) используем window.open
  if (typeof window !== 'undefined') {
    window.open(link, '_blank', 'noopener,noreferrer')
  }
}

let intervalId

const fetchData = async () => {
  let controller1 = new AbortController()

  try {
    // Первый запрос
    const response = await axios.get('https://api.ston.fi/v1/assets/EQBhF8jWase_Cn1dNTTe_3KMWQQzDbVw_lUUkvW5k6s61ikb', {
      signal: controller1.signal
    })

    if (response?.data?.asset?.dex_usd_price) {
      raydiumKwPrice.value = response.data.asset.dex_usd_price
    }
  } catch (error) {
    // Тихая обработка ошибки - не логируем в консоль
  }

  // Очистка контроллера
  controller1 = null
}

const startInterval = () => {
  intervalId = setInterval(fetchData, 10000)
}

const stopInterval = () => {
  clearInterval(intervalId)
}

// Обработчики для анимации закрытия баннера Boosters shop
const onBannerBeforeLeave = (el) => {
  // Сохраняем реальную высоту элемента
  el.style.height = `${el.offsetHeight}px`
  el.style.overflow = 'hidden'
}

const onBannerLeave = (el, done) => {
  // Запускаем анимацию схлопывания
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      el.style.height = '0'
      el.style.marginBottom = '0'
      el.style.paddingTop = '0'
      el.style.paddingBottom = '0'
      el.style.opacity = '0'
      el.style.transform = 'translateY(-10px)'
      el.style.filter = 'blur(3px)'

      // Вызываем done после завершения анимации
      setTimeout(done, 300)
    })
  })
}

const onBannerAfterLeave = (el) => {
  // Очищаем стили после анимации
  el.style.height = ''
  el.style.marginBottom = ''
  el.style.paddingTop = ''
  el.style.paddingBottom = ''
  el.style.overflow = ''
}

onMounted(() => {
  // window.addEventListener('focus', startInterval())
  // window.addEventListener('blur', stopInterval())

  // Сохраняем текущую категорию перед переходом на Market (если были на Home)
  const wasOnHome = tabs.tab === 'home'
  const wasOnBoost = tabs.category === 'boost'
  if (wasOnHome && !wasOnBoost) {
    tabs.previousCategory = tabs.category
  }

  // Устанавливаем активную вкладку Market
  tabs.setTab('market')
  tabs.setBackground('#000000')
  document.body.style.background = tabs.background
  tg?.setHeaderColor(tabs.background)

  // Восстанавливаем навигацию (на случай если она была скрыта)
  const mainNav = document.querySelector('.menu')
  if (mainNav) {
    mainNav.removeAttribute('style')
    mainNav.style.display = 'flex'
    mainNav.style.visibility = 'visible'
    mainNav.style.opacity = '1'
    console.log('✅ MarketView: Navigation restored on mount')
  }

  // Проверяем query параметр для автоматического открытия ASICs Shop
  if (route.query.openAsics === 'true') {
    openAsicsShop()
  }

  // Проверяем query параметр для автоматического открытия Boosters Shop
  if (route.query.openBoosters === 'true') {
    openBoostersShop()
  }

  // Проверяем query параметр для автоматического открытия Power Plants Shop
  if (route.query.openPowerPlants === 'true') {
    openPowerPlantsShop()
  }

  fetchData()
  startInterval()

  // Загружаем курс SOL при монтировании компонента
  fetchSolPrice(true) // true = использовать кеш если доступен
  startSolPriceUpdateInterval()

  // Загружаем цену sBTC при монтировании
  fetchSbtcPrice()

  // Обновляем цену sBTC каждые 5 минут
  sbtcPriceInterval = setInterval(() => {
    fetchSbtcPrice()
  }, 5 * 60 * 1000)
})

onUnmounted(() => {
  clearInterval(intervalId)
  window.removeEventListener('focus', startInterval())
  window.removeEventListener('blur', stopInterval())
  stopSolPriceUpdateInterval()
  if (sbtcPriceInterval) {
    clearInterval(sbtcPriceInterval)
    sbtcPriceInterval = null
  }
  if (controller) {
    controller.abort()
  }
})
</script>

<template>
  <div v-if="!showAsicsShop && !showBoostersShop && !showPowerPlantsShop" class="screen-box">
    <h1 class="title">{{ t('market.title') }}</h1>

    <div class="market-toggle-panel">
      <div class="market-toggle-container">
        <button
          class="market-toggle-btn"
          :class="{ active: isMintMode }"
          @click="() => {}"
        >
          {{ t('market.mint') }}
        </button>
        <button
          class="market-toggle-btn"
          :class="{ active: !isMintMode }"
          @click="() => {}"
        >
          {{ t('market.p2p_market') }}
        </button>
      </div>
    </div>

    <div class="market-grid">
      <div class="special-offers-header">
        <h2 class="special-offers-title">Limited Offers</h2>
        <span class="special-offers-count">Only 10 left</span>
      </div>
      <h2 class="assets-title">In-App Assets</h2>
      <div class="assets-item" :class="{ 'has-sale-stroke': asicsSaleActive }">
        <img :src="imagePathGems('@/assets/market/mining_equip_market_icon.webp')?.value" class="assets-icon" alt="Mining Equipment" />
        <div class="assets-content">
          <h3 class="assets-item-title">{{ t('market.assets_mining_equipment') }}</h3>
          <p class="assets-item-desc">{{ t('market.assets_mining_equipment_desc') }}</p>
          <button class="assets-buy-btn" @click="openAsicsShop">{{ t('market.assets_buy_asics') }}</button>
        </div>
        <div v-if="asicsSaleActive" class="assets-sale-badge">-{{ ASIC_SALE_PERCENT }}%</div>
      </div>
      <div class="assets-item">
        <img :src="imagePathGems('@/assets/market/power_plant_market_icon.webp')?.value" class="assets-icon" alt="Power Plants" />
        <div class="assets-content">
          <h3 class="assets-item-title">{{ t('market.assets_power_plants') }}</h3>
          <p class="assets-item-desc">{{ t('market.assets_power_plants_desc') }}</p>
          <button
            class="assets-buy-btn"
            :class="{ disabled: !POWER_PLANT_ENABLED }"
            :disabled="!POWER_PLANT_ENABLED"
            @click="POWER_PLANT_ENABLED && openPowerPlantsShop()"
          >
            {{ t('market.assets_buy_power_plant') }}
          </button>
        </div>
      </div>
      <div class="assets-item" :class="{ 'has-sale-stroke': boostersSaleActive }">
        <img :src="imagePathGems('@/assets/market/booster_market_icon.webp')?.value" class="assets-icon" alt="Boosters" />
        <div class="assets-content">
          <h3 class="assets-item-title">{{ t('market.assets_boosters') }}</h3>
          <p class="assets-item-desc">{{ t('market.assets_boosters_desc') }}</p>
          <button class="assets-buy-btn" @click="openBoostersShop">{{ t('market.assets_buy_boosters') }}</button>
        </div>
        <div v-if="boostersSaleActive" class="assets-sale-badge">-{{ boostersSalePercent }}%</div>
      </div>
      <h2 class="tokens-title">Tokens</h2>
      <div class="item">
        <div class="label-group">
          <span class="label-text">{{ t('market.rate', { pair: "kW/SOL" }) }}
            <Raydium :width="14" />Raydium
          </span>
        </div>
        <div class="price-group">
          <div class="indicator-row" style="line-height: 22px;">
            <!-- <DownTrend /> -->
            <h3>${{ kwPriceUsd.toFixed(4) || '0.0000' }}</h3>
            <p>{{ t('market.per_k') }}</p>
          </div>
          <button class="trade-btn" @click="openKwTrade">{{ t('market.trade_btn') }}<img src="@/assets/kW_token.png" width="18px" height="18px" /></button>
        </div>
      </div>
      <div class="item">
        <div class="label-group">
          <span class="label-text">{{ t('market.rate', { pair: "sBTC/SOL" }) }}
            <Raydium :width="14" />Raydium
          </span>
        </div>
        <div class="price-group">
          <div class="indicator-row">
            <!-- <UpTrend /> -->
            <h3>
              <template v-if="sbtcPriceLoading && sbtcPriceDisplay === 0">
                {{ locale == 'en' ? 'Loading...' : 'Загрузка...' }}
              </template>
              <template v-else-if="sbtcPriceDisplay > 0">
                ${{ sbtcPriceDisplay.toFixed(4) }}
              </template>
              <template v-else>
                $0.0000
              </template>
            </h3>
          </div>
          <button class="trade-btn" @click="openSbtcTrade">{{
              t('market.trade_btn') }} <img src="@/assets/sBTC.webp" width="18px" height="18px" /></button>
        </div>
      </div>
      <div class="item comming">
        <span>{{ t('market.more_dex') }}</span>
      </div>
      <button class="check-news" @click="direct(twitterLink)">{{ t('market.check_news_btn') }}</button>
    </div>
  </div>

  <!-- Modal window for Trade buttons -->
  <InfoModal
      v-if="showTradeModal"
      @close="handleTradeModalClose"
      confirm-label="Discord"
    >
      <template #header>
        Coming Soon
      </template>
      <template #modal-body>
        Listing will be available soon, stay tuned for project updates.
      </template>
    </InfoModal>

  <!-- Modal window for Starter Pack -->
    <InfoModal
      v-if="showStarterPackModal"
      @close="showStarterPackModal = false"
      confirm-label="Confirm"
    >
      <template #header>
        <div style="text-align: center;" v-html="t('gems.starter_pack_title')"></div>
      </template>
      <template #modal-body>
        <div class="starter-pack-content">
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

  <!-- Modal window for Phantom Verification -->
  <InfoModal
      v-if="phantomConfirmOpen"
      :confirm-label="t('wallet.phantom_verification_confirm')"
      :body-html="phantomVerificationMessage"
      @close="handlePhantomConfirm"
    >
      <template #header>{{ t('wallet.phantom_verification_title') }}</template>
    </InfoModal>

  <!-- Modal window for notifications -->
  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="handleModalClose" />

  <!-- Modal window for ASIC purchase process -->
  <Transition name="fade">
    <div v-if="isProcessing" class="processing-modal-mask" @click.self="false">
      <div class="processing-modal-container" :class="{ 'success-state': purchaseSuccess || stationActionSuccess }">
        <!-- Processing state -->
        <template v-if="!purchaseSuccess && !stationActionSuccess">
          <div class="processing-spinner-wrapper">
            <div class="processing-spinner"></div>
            <div class="processing-spinner-ring"></div>
          </div>
          <div class="processing-content">
            <h3 class="processing-title">
              <template v-if="processingType === 'purchase'">{{ t('asic_shop.processing_purchase') }}</template>
              <template v-else-if="processingType === 'activate'">{{ t('premium_station.processing_activate') }}</template>
              <template v-else-if="processingType === 'disable'">{{ t('premium_station.processing_disable') }}</template>
            </h3>
            <p class="processing-description">
              <template v-if="processingType === 'purchase'">{{ t('asic_shop.processing_description') }}</template>
              <template v-else-if="processingType === 'activate'">{{ t('premium_station.processing_activate_description') }}</template>
              <template v-else-if="processingType === 'disable'">{{ t('premium_station.processing_disable_description') }}</template>
            </p>
          </div>
          <div class="processing-pulse"></div>
        </template>

        <!-- Success state for ASIC purchase -->
        <template v-else-if="purchaseSuccess && purchasedAsic && !purchasedBoost">
          <div class="success-animation-wrapper">
            <div class="success-checkmark">
              <Success :width="80" :height="80" style="color: #31ff80" />
            </div>
            <div class="success-rings">
              <div class="success-ring success-ring-1"></div>
              <div class="success-ring success-ring-2"></div>
              <div class="success-ring success-ring-3"></div>
            </div>
          </div>
          <div class="success-content">
            <h3 class="success-title">{{ t('asic_shop.purchase_complete') }}</h3>
            <div class="success-asic-info">
              <div class="success-asic-name">{{ purchasedAsic.name }}</div>
              <div class="success-asic-details">
                <span class="success-detail-item">
                  <span class="success-detail-label">{{ t('asic_shop.hashrate') }}</span>
                  <span class="success-detail-value">
                    {{ purchasedAsic.hashRate >= 1000
                      ? (purchasedAsic.hashRate / 1000) + ` ${t('common.per_s', { value: 'Gh' })}`
                      : purchasedAsic.hashRate + ` ${t('common.per_s', { value: 'Mh' })}`
                    }}
                  </span>
                </span>
                <span class="success-detail-item">
                  <span class="success-detail-label">{{ t('asic_shop.mining_speed') }}</span>
                  <span class="success-detail-value">{{ purchasedAsic.speed }} {{ t('common.per_d', { value: 'sBTC' }) }}</span>
                </span>
                <span class="success-detail-item">
                  <span class="success-detail-label">{{ t('asic_shop.consumption') }}</span>
                  <span class="success-detail-value">{{ purchasedAsic.consumption }} {{ t('common.per_h', { value: 'kW' }) }}</span>
                </span>
              </div>
              <div class="success-rarity-badge" :style="`background-color: ${getRarityColor(purchasedAsic.rarity)}`">
                {{ t(`asic_shop.${(purchasedAsic.rarity || 'Common').toLowerCase()}`) }}
              </div>
            </div>
          </div>
          <div class="success-particles">
            <div class="particle" v-for="i in 12" :key="i" :style="`--delay: ${i * 0.1}s`"></div>
          </div>
        </template>

        <!-- Success state for booster purchase -->
        <template v-else-if="purchaseSuccess && purchasedBoost">
          <div class="success-animation-wrapper">
            <div class="success-checkmark">
              <Success :width="80" :height="80" style="color: #31ff80" />
            </div>
            <div class="success-rings">
              <div class="success-ring success-ring-1"></div>
              <div class="success-ring success-ring-2"></div>
              <div class="success-ring success-ring-3"></div>
            </div>
          </div>
          <div class="success-content">
            <h3 class="success-title">{{ t('boosters_shop.purchase_complete') || t('asic_shop.purchase_complete') }}</h3>
            <div class="success-asic-info">
              <div class="success-asic-name">{{ purchasedBoost.name }}</div>
              <div class="success-asic-details">
                <span class="success-detail-item">
                  <span class="success-detail-label">{{ t('boosters_shop.class') || 'Class' }}</span>
                  <span class="success-detail-value">{{ purchasedBoost.class }}</span>
                </span>
                <span v-if="purchasedBoost.gemItem?.benefits" class="success-detail-item">
                  <span class="success-detail-label">{{ t('boosters_shop.power_plant_level') || 'Power Plant Level' }}</span>
                  <span class="success-detail-value">
                    {{ (() => {
                      const powerPlantBenefit = purchasedBoost.gemItem.benefits.find(b => b.includes('power_plant_lvl'))
                      if (!powerPlantBenefit) return ''
                      const translated = t(powerPlantBenefit)
                      return translated !== powerPlantBenefit ? translated : powerPlantBenefit.replace(/_/g, ' ')
                    })() }}
                  </span>
                </span>
              </div>
              <div class="success-rarity-badge" :style="getBoostersRarityStyle(purchasedBoost.gemItem)">
                {{ getBoostersRarityText(purchasedBoost.gemItem) }}
              </div>
            </div>
          </div>
          <div class="success-particles">
            <div class="particle" v-for="i in 12" :key="i" :style="`--delay: ${i * 0.1}s`"></div>
          </div>
        </template>

        <!-- Success state for station activation/deactivation -->
        <template v-else-if="stationActionSuccess">
          <div class="success-animation-wrapper">
            <div class="success-checkmark">
              <Success :width="80" :height="80" style="color: #31ff80" />
            </div>
            <div class="success-rings">
              <div class="success-ring success-ring-1"></div>
              <div class="success-ring success-ring-2"></div>
              <div class="success-ring success-ring-3"></div>
            </div>
          </div>
          <div class="success-content">
            <h3 class="success-title">{{ stationActionMessage }}</h3>
          </div>
        </template>
      </div>
    </div>
  </Transition>

  <!-- Modal window for Special Price -->
  <SpecialPriceModal v-if="openSpecialModal" :saleAsic="currBuyAsic" @close="specialModalResponse" />

  <!-- ASICs Shop (page, not modal window) -->
  <div v-if="showAsicsShop" class="asics-shop-page">
    <div class="asics-shop-top-panel">
        <div class="asics-shop-balance">
          <img src="@/assets/SOL.png" width="22px" height="22px" />
          <span class="asics-shop-amount">{{ app.getSolBalanceFromCache().toFixed(3) || 0 }}</span>
        </div>
        <h1>{{ t('asic_shop.title') }}</h1>
        <button class="asics-shop-close" @click="closeAsicsShop">
          <Exit :width="16" style="color: #fff" />
        </button>
    </div>

    <!-- Toggle button between shop and purchased ASICs -->
    <div class="asics-shop-toggle-panel">
        <div class="asics-shop-toggle-panel-spacer"></div>
        <div class="asics-shop-toggle-container">
          <button
            class="asics-shop-toggle-btn"
            :class="{ active: !showOwnedAsics }"
            @click="showOwnedAsics = false"
          >
            {{ t('asic_shop.shop') }}
          </button>
          <button
            class="asics-shop-toggle-btn"
            :class="{ active: showOwnedAsics }"
            @click="showOwnedAsics = true"
          >
            {{ t('asic_shop.your') }}
          </button>
        </div>
        <div class="asics-shop-toggle-panel-right">
          <Transition name="promo-button">
            <button
              v-if="!showOwnedAsics && asicsSaleActive && promoBannerClosed"
              class="asics-shop-promo-button-compact"
              @click="promoBannerClosed = false"
              :title="t('asic_shop.promo_banner_title')"
            >
              <svg class="asics-shop-promo-button-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M13.73 21a2 2 0 0 1-3.46 0" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <circle cx="18" cy="5" r="3" fill="#fcd909" stroke="currentColor" stroke-width="1.5"/>
              </svg>
            </button>
          </Transition>
      </div>
    </div>

    <!-- Marketing banner with promotion -->
    <Transition name="promo-banner">
        <div v-if="!showOwnedAsics && asicsSaleActive && !promoBannerClosed" class="asics-shop-promo-banner">
          <button class="asics-shop-promo-banner-close" @click="promoBannerClosed = true">
            <Exit :width="14" style="color: rgba(255, 255, 255, 0.8)" />
          </button>
          <div class="asics-shop-promo-banner-content">
            <div class="asics-shop-promo-banner-text">
              <div class="asics-shop-promo-banner-title">
                <span class="asics-shop-promo-banner-icon-inline">🔥</span>
                {{ t('asic_shop.promo_banner_title') }}
                <span class="asics-shop-promo-banner-icon-inline">🔥</span>
              </div>
              <div class="asics-shop-promo-banner-description">{{ t('asic_shop.promo_banner_text') }}</div>
            </div>
          </div>
      </div>
    </Transition>

    <div class="asics-shop-list" ref="asicsList">
        <!-- ASICs shop -->
        <template v-if="!showOwnedAsics">
          <div class="asics-shop-item" v-for="asicItem in shopAsics" :key="asicItem.index">
            <div class="asics-shop-picture">
              <img :src="imagePathAsics(asicItem?.name)?.value" :style="asicItem?.rarity == 'Epic' || asicItem?.rarity == 'Legendary'
                ? 'min-width: 125px; margin: -30px 0 -10px'
                : asicItem?.rarity == 'Mythic'
                  ? 'min-width: 140px; margin: -30px 0 -10px'
                  : 'min-width: 115px'
              " />
            </div>
            <div class="asics-shop-info">
              <span class="asics-shop-name">{{ asicItem?.name }}</span>
              <span>{{ width > 345 ? t('asic_shop.speed') : t('asic_shop.speed').slice(0, 1) +
                t('asic_shop.speed').slice(-2, -1) }}
                {{
                  asicItem?.hash_rate >= 1000
                    ? asicItem?.hash_rate / 1000 + ` ${t('common.per_s', { value: 'Gh' })}`
                    : asicItem?.hash_rate + ` ${t('common.per_s', { value: 'Mh' })}`
                }}</span>
              <span>{{ width > 345 ? t('asic_shop.mining') : t('asic_shop.mining').slice(0, 1) +
                t('asic_shop.mining').slice(-2, -1) }} {{ asicItem?.speed }} {{ t('common.per_d', { value: 'sBTC' })
                }}</span>
              <span>{{ width > 345 ? t('asic_shop.consumption') : t('asic_shop.consumption').slice(0, 1) +
                t('asic_shop.consumption').slice(-2, -1) }} {{ asicItem?.consumption }} {{ t('common.per_h', {
                  value:
                    'kW'
                }) }}</span>
            </div>
            <button @click="buyAsics(asicItem.index, asicItem?.payablePrice, asicItem?.link, asicItem?.requiresModal, asicItem?.shop)"
              :disabled="!asicItem?.shop">
              <span>{{ t('asic_shop.buy_asic') }}</span>
              <span class="asics-shop-price" :class="{ saleprice: asicItem?.sale }">
                <img src="@/assets/SOL.png" width="14px" height="14px" />
                {{ asicItem?.original_price ?? asicItem?.price }}
              </span>
              <div v-if="asicItem?.sale && asicItem?.perc" class="asics-shop-sale-perc">-{{ asicItem?.perc }}%</div>
              <div v-if="asicItem?.sale && asicItem?.new_price !== null" class="asics-shop-sale-newprice">
                <img src="@/assets/SOL.png" width="12px" height="12px" />
                {{ asicItem?.new_price }}
              </div>
            </button>
            <span class="asics-shop-tag" :style="asicItem?.rarity == 'Common'
              ? 'background-color: #5D625E'
              : asicItem?.rarity == 'Rare'
                ? 'background-color: #009600;'
                : asicItem?.rarity == 'Epic'
                  ? 'background-color: #0918E9;'
                  : asicItem?.rarity == 'Legendary'
                    ? 'background-color: #E98509;'
                    : 'background-color: #6B25A1;'
            ">{{ t(`asic_shop.${asicItem?.rarity.toLowerCase()}`) }}</span>
          </div>
        </template>

        <!-- User's purchased ASICs -->
        <div v-if="showOwnedAsics" class="asics-shop-owned-asics">
          <div v-if="ownedAsicsDisplay && ownedAsicsDisplay.length > 0" class="asics-shop-owned-list">
            <div
              class="asics-shop-item asics-shop-owned-item"
              v-for="owned in ownedAsicsDisplay"
              :key="owned.item?.address || owned.item?.nft || owned.idx"
            >
              <div class="asics-shop-picture">
                <img
                  :src="imagePathAsics(owned.imageKey).value"
                  :style="owned.rarity == 'Epic' || owned.rarity == 'Legendary'
                    ? 'min-width: 125px; margin: -30px 0 -10px'
                    : owned.rarity == 'Mythic'
                      ? 'min-width: 140px; margin: -30px 0 -10px'
                      : 'min-width: 115px'"
                />
              </div>
              <div class="asics-shop-info">
                <span class="asics-shop-name">{{ owned.name }}</span>
                <span>{{ width > 345 ? t('asic_shop.speed') : t('asic_shop.speed').slice(0, 1) +
                  t('asic_shop.speed').slice(-2, -1) }}
                  {{
                    owned.hashRate >= 1000
                      ? (owned.hashRate / 1000) + ` ${t('common.per_s', { value: 'Gh' })}`
                      : owned.hashRate + ` ${t('common.per_s', { value: 'Mh' })}`
                  }}</span>
                <span>{{ width > 345 ? t('asic_shop.mining') : t('asic_shop.mining').slice(0, 1) +
                  t('asic_shop.mining').slice(-2, -1) }} {{ owned.speed }} {{ t('common.per_d', { value: 'sBTC' }) }}</span>
                <span>{{ width > 345 ? t('asic_shop.consumption') : t('asic_shop.consumption').slice(0, 1) +
                  t('asic_shop.consumption').slice(-2, -1) }} {{ owned.consumption }} {{ t('common.per_h', { value: 'kW' }) }}</span>
                <div class="asics-shop-status-row" v-if="owned.item?.nft || getTimedNftData(owned.item)">
                  <span v-if="owned.item?.nft" class="asics-shop-status-badge asics-shop-rented">{{ t('asic_shop.rented') }}</span>
                  <span v-if="getTimedNftData(owned.item)" class="asics-shop-status-badge asics-shop-connecting">{{ t('asic_shop.connecting') }}</span>
                </div>
              </div>
              <button disabled>
                <span>{{ t('asic_shop.sell') }}</span>
              </button>
              <span class="asics-shop-tag" :style="`background-color: ${getRarityColor(owned.rarity)}`">
                {{ t(`asic_shop.${(owned.rarity || 'Common').toLowerCase()}`) }}
              </span>
            </div>
          </div>
          <div v-else class="asics-shop-empty-state">
            <p>{{ t('asic_shop.no_asics') }}</p>
            <button @click="showOwnedAsics = false" class="asics-shop-buy-asic-btn">
              {{ t('asic_shop.buy_first_asic') }}
            </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Boosters Shop (page, not modal window) -->
  <div v-if="showBoostersShop" class="boosters-shop-page">
    <div class="boosters-shop-top-panel">
        <div class="boosters-shop-balance">
          <img src="@/assets/SOL.png" width="22px" height="22px" />
          <span class="boosters-shop-amount">{{ app.getSolBalanceFromCache().toFixed(3) || 0 }}</span>
        </div>
        <h1>{{ t('boosters_shop.title') || 'Boosters Shop' }}</h1>
        <button class="boosters-shop-close" @click="closeBoostersShop">
          <Exit :width="16" style="color: #fff" />
        </button>
    </div>

    <!-- Toggle button between shop and purchased boosters -->
    <div class="boosters-shop-toggle-panel">
        <div class="boosters-shop-toggle-panel-spacer"></div>
        <div class="boosters-shop-toggle-container">
          <button
            class="boosters-shop-toggle-btn"
            :class="{ active: !showOwnedBoosters }"
            @click="showOwnedBoosters = false"
          >
            {{ t('boosters_shop.shop') || 'Boosters' }}
          </button>
          <button
            class="boosters-shop-toggle-btn"
            :class="{ active: showOwnedBoosters }"
            @click="showOwnedBoosters = true"
          >
            {{ t('boosters_shop.your') || 'Your' }}
          </button>
        </div>
        <div class="boosters-shop-toggle-panel-right">
          <Transition name="promo-button">
            <button
              v-if="!showOwnedBoosters && boostersSaleActive && boostersPromoBannerClosed"
              class="asics-shop-promo-button-compact"
              @click="boostersPromoBannerClosed = false"
              :title="t('boosters_shop.promo_banner_title') || 'Special Offer'"
            >
              <svg class="asics-shop-promo-button-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M13.73 21a2 2 0 0 1-3.46 0" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <circle cx="18" cy="5" r="3" fill="#fcd909" stroke="currentColor" stroke-width="1.5"/>
              </svg>
            </button>
          </Transition>
        </div>
    </div>

    <!-- Marketing banner with promotion for Boosters -->
    <Transition name="promo-banner" @before-leave="onBannerBeforeLeave" @leave="onBannerLeave" @after-leave="onBannerAfterLeave">
      <div v-if="!showOwnedBoosters && boostersSaleActive && !boostersPromoBannerClosed" class="asics-shop-promo-banner">
        <button class="asics-shop-promo-banner-close" @click="boostersPromoBannerClosed = true">
          <Exit :width="14" style="color: rgba(255, 255, 255, 0.8)" />
        </button>
        <div class="asics-shop-promo-banner-content">
          <div class="asics-shop-promo-banner-text">
            <div class="asics-shop-promo-banner-title">
              <span class="asics-shop-promo-banner-icon-inline">🔥</span>
              <span class="asics-shop-promo-banner-title-text" v-html="t('boosters_shop.promo_banner_title') || 'Christmas Sale -50%'"></span>
              <span class="asics-shop-promo-banner-icon-inline">🔥</span>
            </div>
            <div class="asics-shop-promo-banner-description">{{ t('boosters_shop.promo_banner_text') || 'Discounts are valid for one month, from December 19 to January 19.' }}</div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- User information -->
    <div class="boosters-shop-user-info">
      <div class="boosters-shop-user-info-item">
        <span class="boosters-shop-user-info-label">{{ t('boosters_shop.your_power_plant_lvl') || 'Your Power Plant lvl' }}</span>
        <span class="boosters-shop-user-info-value">{{ userStationLevel !== null ? userStationLevel : '—' }}</span>
      </div>
      <div class="boosters-shop-user-info-item">
        <span class="boosters-shop-user-info-label">{{ t('boosters_shop.your_asics_hashrate') || 'Your ASICs hashrate' }}</span>
        <span class="boosters-shop-user-info-value">{{ userHashrate !== null ? `${userHashrate.toFixed(1)} Gh/s` : '—' }}</span>
      </div>
    </div>

    <div class="boosters-shop-list" ref="boostersList">
        <!-- Boosters shop -->
        <template v-if="!showOwnedBoosters">
          <div class="boosters-shop-item"
            :class="{
              'has-gold-stroke': gemItem?.hasGoldStroke,
              'has-purple-stroke': gemItem?.hasPurpleStroke,
              'has-blue-stroke': gemItem?.hasBlueStroke,
              'has-sale-stroke': boostersSaleActive && gemItem?.enableSale !== false
            }"
            v-for="gemItem in sortGemsBySale(gemsSheet.filter(el => el.shop && el.type !== 'DAO Owner' && el.type !== 'Hydroelectric Power Plant' && el.type !== 'Orbital Power Plant' && el.type !== 'Starter Pack'))"
            :key="gemItem">
            <!-- <div class="boosters-shop-info-icon-top" @click="handleGemInfoClick(gemItem)">i</div> -->
            <div class="boosters-shop-picture">
              <img v-if="gemItem?.imagePath" :src="imagePathGems(gemItem.imagePath)?.value" class="boosters-shop-image"
                :class="{ 'hide-under-tag': gemItem?.buttonColor !== 'gold' && gemItem?.buttonColor !== 'purple' && gemItem?.buttonColor !== 'blue' && gemItem?.type !== 'Cryochamber' }"
                alt="NFT" />
              <div v-else class="boosters-shop-icon">💎</div>
            </div>
            <div class="boosters-shop-info">
              <span class="boosters-shop-type">{{ gemItem.type }}</span>
              <span
                class="boosters-shop-description"
                v-for="(benefit, idx) in gemItem.benefits"
                :key="idx"
                :class="{
                  'boosters-shop-benefit-match': checkPowerPlantLevelMatch(benefit) || checkHashrateMatch(benefit)
                }"
              >
                <span v-if="checkPowerPlantLevelMatch(benefit) || checkHashrateMatch(benefit)" class="boosters-shop-check-icon">✓</span>
                {{ t(`gems.${benefit}`) || benefit.replace(/_/g, ' ') }}
              </span>
            </div>
            <button class="boosters-shop-buy-btn"
              :class="{
                'btn-gold': gemItem?.buttonColor === 'gold',
                'btn-purple': gemItem?.buttonColor === 'purple',
                'btn-blue': gemItem?.buttonColor === 'blue'
              }"
              :disabled="!gemItem?.shop"
              @click="buyGem(gemItem)">
              <span>{{ gemItem.name }}</span>
              <span v-if="gemItem?.type !== 'Orbital Power Plant'" class="boosters-shop-price" :class="{ 'boosters-shop-saleprice': boostersSaleActive && gemItem?.enableSale !== false }">
                <img src="@/assets/SOL.png" width="14px" height="14px" />
                {{ gemItem.price }}
              </span>
              <span v-else class="boosters-shop-price">{{ gemItem.price }}</span>
              <div v-if="boostersSaleActive && gemItem?.enableSale !== false" class="boosters-shop-sale-perc">-{{ gemItem.salePercent || boostersSalePercent }}%</div>
              <div v-if="boostersSaleActive && gemItem?.enableSale !== false" class="boosters-shop-sale-newprice">
                <img src="@/assets/SOL.png" width="12px" height="12px" />
                {{ getBoosterPrice(gemItem) }}
              </div>
            </button>
            <span class="boosters-shop-tag"
              :style="getBoostersRarityStyle(gemItem)"
            >{{ getBoostersRarityText(gemItem) }}</span>
            <div v-if="boostersSaleActive && gemItem?.enableSale !== false" class="assets-sale-badge">-{{ boostersSalePercent }}%</div>
          </div>
        </template>

        <!-- User's purchased boosters -->
        <div v-if="showOwnedBoosters" class="boosters-shop-owned-boosters">
          <template v-if="ownedBoostersDisplay && ownedBoostersDisplay.length > 0">
            <div class="boosters-shop-item"
              :class="{
                'has-gold-stroke': owned.gemItem?.hasGoldStroke,
                'has-purple-stroke': owned.gemItem?.hasPurpleStroke,
                'has-blue-stroke': owned.gemItem?.hasBlueStroke
              }"
              v-for="owned in ownedBoostersDisplay"
              :key="owned.boostAsset.id">
              <!-- <div class="boosters-shop-info-icon-top" v-if="owned.gemItem" @click="handleGemInfoClick(owned.gemItem)">i</div> -->
              <div class="boosters-shop-picture">
                <img v-if="owned.gemItem?.imagePath" :src="imagePathGems(owned.gemItem.imagePath)?.value" class="boosters-shop-image"
                  :class="{ 'hide-under-tag': owned.gemItem?.buttonColor !== 'gold' && owned.gemItem?.buttonColor !== 'purple' && owned.gemItem?.buttonColor !== 'blue' && owned.gemItem?.type !== 'Cryochamber' }"
                  alt="NFT" />
                <div v-else class="boosters-shop-icon">💎</div>
              </div>
              <div class="boosters-shop-info">
                <span class="boosters-shop-type">{{ owned.name }}</span>
                <span v-if="!owned.is_active" class="boosters-shop-inactive-label">
                  {{ t('boosters_shop.inactive') || 'Inactive (conditions not met)' }}
                </span>
                <span v-else class="boosters-shop-active-label">
                  {{ t('boosters_shop.active') || 'Active' }}
                </span>
                <span
                  v-if="owned.gemItem"
                  class="boosters-shop-description"
                  v-for="(benefit, idx) in owned.gemItem.benefits"
                  :key="idx"
                  :class="{
                    'boosters-shop-benefit-match': checkPowerPlantLevelMatch(benefit) || checkHashrateMatch(benefit),
                    'boosters-shop-benefit-mismatch': !owned.conditions_met && (benefit.includes('power_plant_lvl:') || benefit.includes('gh_s:')) && !checkPowerPlantLevelMatch(benefit) && !checkHashrateMatch(benefit)
                  }"
                >
                  <span v-if="checkPowerPlantLevelMatch(benefit) || checkHashrateMatch(benefit)" class="boosters-shop-check-icon">✓</span>
                  <span v-else-if="!owned.conditions_met && (benefit.includes('power_plant_lvl:') || benefit.includes('gh_s:')) && !checkPowerPlantLevelMatch(benefit) && !checkHashrateMatch(benefit)" class="boosters-shop-cross-icon">✗</span>
                  {{ t(`gems.${benefit}`) || benefit.replace(/_/g, ' ') }}
                </span>
              </div>
              <button
                class="boosters-shop-toggle-btn"
                :class="{
                  'boost-active': owned.is_active && owned.is_enabled,
                  'boost-inactive-btn': !owned.is_active && (owned.conditions_met || !owned.conditions_met),
                  'boost-disabled-yellow': !owned.is_active && owned.conditions_met && ownedBoostersDisplay.some(other =>
                    other.boost_type === owned.boost_type &&
                    other.boost_class === owned.boost_class &&
                    other.is_active &&
                    other.boostAsset.id !== owned.boostAsset.id
                  )
                }"
                :disabled="!owned.is_active && owned.conditions_met && ownedBoostersDisplay.some(other =>
                  other.boost_type === owned.boost_type &&
                  other.boost_class === owned.boost_class &&
                  other.is_active &&
                  other.boostAsset.id !== owned.boostAsset.id
                )"
                @click="!owned.conditions_met ? showBoostConditionsModal(owned) : toggleBoost(owned.boostAsset.id)">
                <span v-if="owned.is_active && owned.is_enabled">
                  {{ t('boosters_shop.disable') || 'Disable' }}
                </span>
                <span v-else-if="!owned.is_active && owned.conditions_met && ownedBoostersDisplay.some(other =>
                  other.boost_type === owned.boost_type &&
                  other.boost_class === owned.boost_class &&
                  other.is_active &&
                  other.boostAsset.id !== owned.boostAsset.id
                )">
                  {{ t('boosters_shop.activated') || 'Activated' }}
                </span>
                <span v-else>
                  {{ t('boosters_shop.activate') || 'Activate' }}
                </span>
              </button>
              <span v-if="owned.gemItem" class="boosters-shop-tag"
                :style="getBoostersRarityStyle(owned.gemItem)"
              >{{ owned.gemItem ? getBoostersRarityText(owned.gemItem) : `Class ${owned.boost_class}` }}</span>
            </div>
          </template>
          <div v-else class="boosters-shop-empty-state">
            <p>{{ t('boosters_shop.no_boosters') || 'No boosters yet' }}</p>
            <button @click="showOwnedBoosters = false" class="boosters-shop-buy-booster-btn">
              {{ t('boosters_shop.buy_first_booster') || 'Buy first booster' }}
            </button>
          </div>
        </div>
    </div>
  </div>

  <!-- Power Plants Shop (page, not modal window) -->
  <div v-if="showPowerPlantsShop" class="boosters-shop-page">
    <div class="boosters-shop-top-panel">
        <div class="boosters-shop-balance">
          <img src="@/assets/SOL.png" width="22px" height="22px" />
          <span class="boosters-shop-amount">{{ app.getSolBalanceFromCache().toFixed(3) || 0 }}</span>
        </div>
        <h1>{{ t('power_plants_shop.title') || 'Power Plants Shop' }}</h1>
        <button class="boosters-shop-close" @click="closePowerPlantsShop">
          <Exit :width="16" style="color: #fff" />
        </button>
    </div>

    <!-- Toggle button between shop and purchased power plants -->
    <div class="boosters-shop-toggle-panel">
        <div class="boosters-shop-toggle-panel-spacer"></div>
        <div class="boosters-shop-toggle-container">
          <button
            class="boosters-shop-toggle-btn"
            :class="{ active: !showOwnedPowerPlants }"
            @click="showOwnedPowerPlants = false"
          >
            {{ t('power_plants_shop.shop') || 'Power Plants' }}
          </button>
          <button
            class="boosters-shop-toggle-btn"
            :class="{ active: showOwnedPowerPlants }"
            @click="handleShowOwnedPowerPlants"
          >
            {{ t('power_plants_shop.your') || 'Your' }}
          </button>
        </div>
        <div class="boosters-shop-toggle-panel-right"></div>
    </div>

    <div class="boosters-shop-list" ref="powerPlantsList">
        <!-- Power plants shop -->
        <template v-if="!showOwnedPowerPlants">
          <div class="boosters-shop-item"
            :class="{
              'has-gold-stroke': powerPlantItem?.hasGoldStroke,
              'has-purple-stroke': powerPlantItem?.hasPurpleStroke,
              'has-blue-stroke': powerPlantItem?.hasBlueStroke,
              'power-plant-tall': ['Hydroelectric Power Plant', 'Orbital Power Plant', 'Singularity Reactor', 'Proton Star', 'Dark Matter'].includes(powerPlantItem?.type)
            }"
            v-for="powerPlantItem in sortGemsBySale(powerPlantsSheet.filter(el => el.shop && el.type !== 'Starter Pack'))"
            :key="powerPlantItem">
            <!-- <div class="boosters-shop-info-icon-top" @click="handleGemInfoClick(powerPlantItem)">i</div> -->
            <div class="boosters-shop-picture">
              <img v-if="powerPlantItem?.imagePath" :src="imagePathGems(powerPlantItem.imagePath)?.value" class="boosters-shop-image"
                alt="NFT" />
              <div v-else class="boosters-shop-icon">💎</div>
            </div>
            <div class="boosters-shop-info">
              <span class="boosters-shop-type">{{ powerPlantItem.type }}</span>
              <!-- For Starter Pack show benefits -->
              <template v-if="powerPlantItem.type === 'Starter Pack' && powerPlantItem.benefits">
                <span class="boosters-shop-description" v-for="(benefit, idx) in powerPlantItem.benefits" :key="idx">
                  {{ t(`gems.${benefit}`) || benefit.replace(/_/g, ' ') }}
                </span>
              </template>
              <!-- For other power plants show stats from backend -->
              <template v-else>
                <span class="boosters-shop-description" v-if="powerPlantItem?.engineers">
                  {{ t('power_plants_shop.engineers', { value: powerPlantItem.engineers }) }}
                </span>
                <span class="boosters-shop-description" v-if="getPowerPlantStats(powerPlantItem).storage">
                  {{ t('power_plants_shop.storage', { value: getPowerPlantStats(powerPlantItem).storage }) }}
                </span>
                <span class="boosters-shop-description" v-if="getPowerPlantStats(powerPlantItem).generation">
                  {{ t('power_plants_shop.generation', { value: getPowerPlantStats(powerPlantItem).generation }) }}
                </span>
                <span
                  class="boosters-shop-description"
                  v-if="getPowerPlantStats(powerPlantItem).building">
                  <template v-if="getPowerPlantStats(powerPlantItem).building === 'now!'">
                    {{ t('power_plants_shop.building', { value: '' }).split(':')[0] }}:
                    <span class="building-now">
                      <span
                        v-for="(char, index) in 'now!'.split('')"
                        :key="index"
                        class="building-now-letter"
                        :style="{ animationDelay: `${index * 0.1}s` }">
                        {{ char === ' ' ? '\u00A0' : char }}
                      </span>
                    </span>
                  </template>
                  <template v-else>
                    {{ t('power_plants_shop.building', { value: getPowerPlantStats(powerPlantItem).building }) }}
                  </template>
                </span>
              </template>
            </div>
            <button class="boosters-shop-buy-btn"
              :class="{
                'btn-gold': powerPlantItem?.buttonColor === 'gold',
                'btn-purple': powerPlantItem?.buttonColor === 'purple',
                'btn-blue': powerPlantItem?.buttonColor === 'blue'
              }"
              :disabled="!powerPlantItem?.shop"
              @click="buyGem(powerPlantItem)">
              <span>{{ powerPlantItem.name }}</span>
              <span class="boosters-shop-price" :class="{ 'boosters-shop-saleprice': gemsSaleActive && powerPlantItem?.enableSale !== false }">
                <img src="@/assets/SOL.png" width="14px" height="14px" />
                {{ powerPlantItem.price }}
              </span>
              <div v-if="gemsSaleActive && powerPlantItem?.enableSale !== false" class="boosters-shop-sale-perc">-{{ powerPlantItem.salePercent || gemsSalePercent }}%</div>
              <div v-if="gemsSaleActive && powerPlantItem?.enableSale !== false" class="boosters-shop-sale-newprice">
                <img src="@/assets/SOL.png" width="12px" height="12px" />
                {{ getGemPrice(powerPlantItem) }}
              </div>
            </button>
            <span class="boosters-shop-tag"
              :style="powerPlantItem?.rarity === 'special'
                ? 'background: linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(152, 81, 236, 1) 50%, rgba(94, 124, 234, 1) 100%);'
                : powerPlantItem?.rarity === 'common' && powerPlantItem?.rarityColor === 'gray'
                  ? 'background-color: #5D625E;'
                  : powerPlantItem?.rarity === 'rare' && powerPlantItem?.rarityColor === 'green'
                    ? 'background-color: #009600;'
                    : powerPlantItem?.rarity === 'epic' && powerPlantItem?.rarityColor === 'blue'
                      ? 'background-color: #0918E9;'
                      : powerPlantItem?.rarity === 'legendary' && powerPlantItem?.rarityColor === 'purple'
                        ? 'background-color: #E98509;'
                        : powerPlantItem?.rarity === 'mythic' && powerPlantItem?.rarityColor === 'gradient'
                          ? 'background: linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(94, 124, 234, 1) 100%);'
                          : 'background-color: #5D625E;'
                ">{{ powerPlantItem?.rarity === 'special' ? t('gems.special') : t(`power_plants_shop.${powerPlantItem?.rarity || 'common'}`) }}</span>
          </div>
        </template>

        <!-- User's purchased power plants -->
        <div v-if="showOwnedPowerPlants" class="boosters-shop-owned-boosters">
          <template v-if="ownedPowerPlantsDisplay && ownedPowerPlantsDisplay.length > 0">
            <div class="boosters-shop-item"
              :class="{
                'has-gold-stroke': owned.powerPlantItem?.hasGoldStroke,
                'has-purple-stroke': owned.powerPlantItem?.hasPurpleStroke,
                'has-blue-stroke': owned.powerPlantItem?.hasBlueStroke,
                'power-plant-tall': owned.powerPlantItem?.type === 'Hydroelectric Power Plant' || owned.powerPlantItem?.type === 'Orbital Power Plant'
              }"
              v-for="owned in ownedPowerPlantsDisplay"
              :key="owned.asset.id">
              <div class="boosters-shop-picture">
                <img v-if="owned.powerPlantItem?.imagePath" :src="imagePathGems(owned.powerPlantItem.imagePath)?.value" class="boosters-shop-image"
                  alt="Power Plant" />
                <div v-else class="boosters-shop-icon">⚡</div>
              </div>
              <div class="boosters-shop-info">
                <span class="boosters-shop-type">{{ owned.name }}</span>
                <span v-if="owned.is_active" class="boosters-shop-active-label">
                  {{ t('premium_station.active') || 'Active' }}
                </span>
                <span v-else class="boosters-shop-inactive-label">
                  {{ t('premium_station.inactive') || 'Inactive' }}
                </span>
                <template v-if="owned.powerPlantItem">
                  <span class="boosters-shop-description" v-if="owned.powerPlantItem.engineers">
                    {{ t('power_plants_shop.engineers', { value: owned.powerPlantItem.engineers }) }}
                  </span>
                  <span class="boosters-shop-description" v-if="getPowerPlantStats(owned.powerPlantItem).storage">
                    {{ t('power_plants_shop.storage', { value: getPowerPlantStats(owned.powerPlantItem).storage }) }}
                  </span>
                  <span class="boosters-shop-description" v-if="getPowerPlantStats(owned.powerPlantItem).generation">
                    {{ t('power_plants_shop.generation', { value: getPowerPlantStats(owned.powerPlantItem).generation }) }}
                  </span>
                </template>
                <template v-else>
                  <span class="boosters-shop-description" v-if="owned.asset.metadata?.engineers">
                    {{ t('power_plants_shop.engineers', { value: owned.asset.metadata.engineers }) }}
                  </span>
                  <span class="boosters-shop-description" v-if="owned.asset.metadata?.storage">
                    {{ t('power_plants_shop.storage', { value: owned.asset.metadata.storage }) }}
                  </span>
                  <span class="boosters-shop-description" v-if="owned.asset.metadata?.generation">
                    {{ t('power_plants_shop.generation', { value: owned.asset.metadata.generation }) }}
                  </span>
                </template>
              </div>
              <button
                v-if="owned.is_active"
                class="boosters-shop-toggle-btn boost-active"
                @click="disablePremiumStation()"
                :disabled="isProcessing">
                {{ t('premium_station.disable') || 'Disable' }}
              </button>
              <button
                v-else
                class="boosters-shop-toggle-btn boost-inactive-btn"
                @click="activatePremiumStation(owned.name, owned.asset.id)"
                :disabled="isProcessing">
                {{ t('premium_station.activate') || 'Activate' }}
              </button>
              <span v-if="owned.powerPlantItem" class="boosters-shop-tag"
                :style="owned.powerPlantItem?.rarity === 'special'
                  ? 'background: linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(152, 81, 236, 1) 50%, rgba(94, 124, 234, 1) 100%);'
                  : owned.powerPlantItem?.rarity === 'common' && owned.powerPlantItem?.rarityColor === 'gray'
                    ? 'background-color: #5D625E;'
                    : owned.powerPlantItem?.rarity === 'rare' && owned.powerPlantItem?.rarityColor === 'green'
                      ? 'background-color: #009600;'
                      : owned.powerPlantItem?.rarity === 'epic' && owned.powerPlantItem?.rarityColor === 'blue'
                        ? 'background-color: #0918E9;'
                        : owned.powerPlantItem?.rarity === 'legendary' && owned.powerPlantItem?.rarityColor === 'purple'
                          ? 'background-color: #E98509;'
                          : owned.powerPlantItem?.rarity === 'mythic' && owned.powerPlantItem?.rarityColor === 'gradient'
                            ? 'background: linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(94, 124, 234, 1) 100%);'
                            : 'background-color: #5D625E;'
                  ">{{ owned.powerPlantItem?.rarity === 'special' ? t('gems.special') : t(`power_plants_shop.${owned.powerPlantItem?.rarity || 'common'}`) }}</span>
            </div>
          </template>
          <div v-else class="boosters-shop-empty-state">
            <p>{{ t('power_plants_shop.no_power_plants') || 'No power plants yet' }}</p>
            <button @click="showOwnedPowerPlants = false" class="boosters-shop-buy-booster-btn">
              {{ t('power_plants_shop.buy_first_power_plant') || 'Buy first power plant' }}
            </button>
          </div>
        </div>
    </div>
  </div>

  <!-- Modals for booster information -->
  <InfoModal
    v-if="openBoostConditionsInfo"
    :confirm-label="t('boosters_shop.go_to_boosters') || 'Go to Boosters'"
    @close="handleBoostConditionsModalClose">
    <template #header>{{ t('boosters_shop.conditions_not_met') || 'Conditions not met' }}</template>
    <template #modal-body>
      <div v-html="boostConditionsInfoHtml"></div>
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
  <InfoModal v-if="openOrbitalInfo" :confirm-label="t('gems.orbital_instruction_btn')" @close="(e) => { if (e?.check) { openOrbitalCraftInfo = true } openOrbitalInfo = false }">
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
          {{ t('gems.orbital_unique') }}<br><br>
          {{ t('gems.orbital_progress') }}
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
  <InfoModal v-if="openStarterPackInfo" :confirm-label="t('common.buy')" @close="(e) => { if (e?.check) buyStarterPack(); openStarterPackInfo = false }">
    <template #header>
      <div style="text-align: center;" v-html="t('gems.starter_pack_title')"></div>
    </template>
    <template #modal-body>
      <div class="starter-pack-content">
        <div class="starter-pack-text">
          • {{ t('gems.starter_pack_item_1') }}<br>
          {{ t('gems.starter_pack_item_2') }}<br>
          • {{ t('gems.starter_pack_item_3') }}<br>
          • {{ t('gems.starter_pack_item_4') }}<br>
          • {{ t('gems.starter_pack_item_5') }}<br>
          • {{ t('gems.starter_pack_item_6') }}<br>
          • {{ t('gems.starter_pack_item_7') }}<br><br>
          {{ t('gems.starter_pack_price_info') }}<br>
          {{ t('gems.starter_pack_price_offer', { price: getStarterPackPriceDisplay() }) }}<br><br>
          <span style="color: #ffc300;">{{ t('gems.starter_pack_item_8') }}
            <br>{{ t('gems.starter_pack_item_9') }}
            <br>{{ t('gems.starter_pack_item_10') }}
          </span>
        </div>
      </div>
    </template>
  </InfoModal>
  <InfoModal v-if="openDaoOwnerInfo" :confirm-label="t('common.buy')" @close="(e) => { if (e?.check) buyDaoOwner(); openDaoOwnerInfo = false }">
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
  <InfoModal
    v-if="openSwitchStationConfirm"
    :confirm-label="t('premium_station.switch_confirm')"
    :cancel-label="t('premium_station.switch_cancel')"
    @close="handleSwitchStationConfirm">
    <template #header>
      {{ t('premium_station.switch_confirmation_title') }}
    </template>
    <template #modal-body>
      <div v-html="getSwitchConfirmationMessage()"></div>
    </template>
  </InfoModal>
  <InfoModal
    v-if="openDisableStationConfirm"
    :confirm-label="t('premium_station.disable_confirm')"
    :cancel-label="t('premium_station.disable_cancel')"
    @close="handleDisableStationConfirm">
    <template #header>
      {{ t('premium_station.disable_confirmation_title') }}
    </template>
    <template #modal-body>
      <div v-html="getDisableConfirmationMessage()"></div>
    </template>
  </InfoModal>

  <!-- Модальное окно для уведомления о крипто-браузере -->
  <CryptoBrowserModal
    v-if="showCryptoBrowserModal"
    :open-shop="getCurrentShop()"
    @close="handleCryptoBrowserModalClose"
  />
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

  .market-toggle-panel {
    display: flex;
    justify-content: center;
    width: 90%;
    margin: 0 auto 1rem;
    align-items: center;
  }

  .market-toggle-container {
    display: flex;
    background: rgba(0, 0, 0, 0.5);
    border-radius: 20px;
    padding: 2px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    max-width: 232px;
    width: 100%;

    .market-toggle-btn {
      flex: 1;
      padding: 8px 20px;
      border-radius: 20px;
      border: none;
      background: transparent;
      color: #fff;
      font-family: 'Inter' !important;
      font-weight: 600;
      font-size: 16px;
      line-height: 1.21em;
      cursor: pointer;
      transition: all 0.3s ease;
      text-align: center;
      white-space: nowrap;

      &.active {
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);
        color: #000;
      }

      &:hover:not(.active) {
        background: rgba(255, 255, 255, 0.1);
      }
    }
  }
}

.market-grid {
  display: grid;
  width: 90%;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.7rem;

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

  .special-offers-count {
    padding: 6px 10px;
    border-radius: 8px;
    background: linear-gradient(135deg, #ff3b59 0%, #e00b0b 100%);
    color: #fff;
    font-family: 'Inter' !important;
    font-size: 13px;
    font-weight: 700;
    box-shadow:
      0 4px 12px rgba(255, 59, 89, 0.5),
      0 0 20px rgba(255, 59, 89, 0.3),
      inset 0 1px 0 rgba(255, 255, 255, 0.2);
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
    letter-spacing: 0.5px;
    text-align: right;
    margin: 0;
    display: inline-block;
    animation: saleBadgeAnimation 2.5s ease-in-out infinite;
  }

  .assets-title {
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

    &.has-sale-stroke {
      padding: 1px;
      position: relative;
      border: none;

      &::before {
        content: '';
        position: absolute;
        inset: 0;
        border-radius: 15px;
        padding: 1px;
        background: linear-gradient(
          90deg,
          #fcd909 0%,
          #fea400 20%,
          #fcd909 40%,
          #fea400 60%,
          #fcd909 80%,
          #fea400 100%
        );
        background-size: 200% 100%;
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        mask-composite: exclude;
        pointer-events: none;
        z-index: 0;
        animation: saleStrokeGradient 3s linear infinite;
        filter: drop-shadow(0 0 8px rgba(252, 217, 9, 0.6));
      }

      .assets-icon,
      .assets-content {
        position: relative;
        z-index: 1;
      }
    }

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

      &:active:not(:disabled):not(.disabled) {
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd90990, #fea40090);
      }

      &:disabled,
      &.disabled {
        background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
          linear-gradient(to bottom, #e2e2e2, #646464);
        color: rgba(255, 255, 255, 0.5);
        cursor: not-allowed;
        opacity: 0.6;
      }
    }

    .assets-sale-badge {
      position: absolute;
      bottom: 12px;
      left: 12px;
      padding: 6px 10px;
      border-radius: 8px;
      background: linear-gradient(135deg, #ff3b59 0%, #e00b0b 100%);
      color: #fff;
      font-family: 'Inter' !important;
      font-size: 13px;
      font-weight: 700;
      box-shadow:
        0 4px 12px rgba(255, 59, 89, 0.5),
        0 0 20px rgba(255, 59, 89, 0.3),
        inset 0 1px 0 rgba(255, 255, 255, 0.2);
      z-index: 20;
      animation: saleBadgeAnimation 2.5s ease-in-out infinite;
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
      letter-spacing: 0.5px;
    }
  }

  @keyframes saleStrokeGradient {
    0% {
      background-position: 0% 0%;
    }
    50% {
      background-position: 100% 0%;
    }
    100% {
      background-position: 0% 0%;
    }
  }

  @keyframes saleBadgeAnimation {
    0%, 100% {
      transform: scale(1) translateY(0);
      box-shadow:
        0 4px 12px rgba(255, 59, 89, 0.5),
        0 0 20px rgba(255, 59, 89, 0.3),
        inset 0 1px 0 rgba(255, 255, 255, 0.2);
    }
    25% {
      transform: scale(1.08) translateY(-2px);
      box-shadow:
        0 6px 16px rgba(255, 59, 89, 0.7),
        0 0 30px rgba(255, 59, 89, 0.5),
        inset 0 1px 0 rgba(255, 255, 255, 0.3);
    }
    50% {
      transform: scale(1.05) translateY(-1px);
      box-shadow:
        0 5px 14px rgba(255, 59, 89, 0.6),
        0 0 25px rgba(255, 59, 89, 0.4),
        inset 0 1px 0 rgba(255, 255, 255, 0.25);
    }
    75% {
      transform: scale(1.08) translateY(-2px);
      box-shadow:
        0 6px 16px rgba(255, 59, 89, 0.7),
        0 0 30px rgba(255, 59, 89, 0.5),
        inset 0 1px 0 rgba(255, 255, 255, 0.3);
    }
  }

  .tokens-title {
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

    .starter-pack-info-icon {
      position: absolute;
      top: 5px;
      right: 8px;
      width: 18px;
      height: 18px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #FFFFFF;
      border-radius: 50%;
      cursor: pointer;
      font-family: 'Inter', sans-serif;
      font-weight: 700;
      font-size: 9px;
      color: #000000;
      z-index: 10;
      transition: all 0.2s ease;

      &:hover {
        background: rgba(255, 255, 255, 0.8);
      }
    }

    .starter-pack-picture {
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      max-width: 95px;
      gap: 0;

      .starter-pack-image {
        min-width: 115px;
        margin: -25px 0 -10px;
        height: auto;
      }
    }

    .starter-pack-info {
      display: flex;
      flex-direction: column;
      align-items: start;
      justify-content: center;
      width: 100%;
      min-width: 110px;
      line-height: 95%;
      margin-bottom: 10px;

      .starter-pack-type {
        color: #fff;
        font-family: 'Inter' !important;
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 3px;
        white-space: pre-line;
      }

      .starter-pack-description {
        color: #ffffff70;
        font-family: 'Inter' !important;
        font-weight: 400;
        font-size: 10px;
        text-wrap: nowrap;
      }
    }

    .starter-pack-buy-btn {
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
        linear-gradient(180deg, #FCD909 0%, #FEA400 100%);
      cursor: pointer;
      transition: all 0.3s ease;
      z-index: 100;

      &.btn-purple {
        background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
          linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(152, 81, 236, 1) 50%, rgba(94, 124, 234, 1) 100%);
      }

      &:active {
        background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
          linear-gradient(to bottom, #fcd90990, #fea40090);
      }

      > span:first-child {
        color: #000;
        font-family: 'Inter' !important;
        font-weight: 700;
        font-size: 10px;
        text-align: center;
        width: 100%;
      }

      .starter-pack-price {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0.3rem;
        font-size: 12px;
        line-height: 16pt;
        font-weight: 700;
        font-family: 'Inter' !important;
        color: #000;

        &.saleprice {
          position: relative;
          display: flex;
          justify-content: center;
          align-items: center;
          color: #000;

          &::before {
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
      }

      .starter-pack-sale-perc {
        position: absolute;
        left: -10px;
        top: -15px;
        padding: 0.1rem 0.2rem;
        transform: rotate(-10deg);
        border-radius: 0.3rem;
        font-family: 'Inter' !important;
        font-size: 12px;
        font-weight: bold;
        box-shadow:
          0 0 15px 2px #fccd0835,
          0 0 2px 2px #00000020;
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);
      }

      .starter-pack-sale-newprice {
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
        box-shadow:
          0 0 15px 2px #fccd0835,
          -1px -1px 2px 2px #00000020;
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);
        color: #000;
      }
    }

    .starter-pack-tag {
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
      background: linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(152, 81, 236, 1) 50%, rgba(94, 124, 234, 1) 100%), #FFC300;
    }
  }

  // Анимации для плашки Starter Pack
  .promo-banner-enter-active {
    transition: opacity 0.6s cubic-bezier(0.34, 1.56, 0.64, 1),
                transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1),
                filter 0.6s ease-out;
  }

  .promo-banner-leave-active {
    transition: opacity 0.3s ease-out,
                transform 0.3s ease-out,
                filter 0.3s ease-out,
                margin-bottom 0.3s ease-out,
                height 0.3s ease-out,
                padding 0.3s ease-out;
    pointer-events: none;
  }

  .promo-banner-enter-from {
    opacity: 0;
    transform: translateY(-15px);
    filter: blur(4px);
  }

  .promo-banner-enter-to {
    opacity: 1;
    transform: translateY(0);
    filter: blur(0);
  }

  .promo-banner-leave-from {
    opacity: 1;
    transform: translateY(0);
    filter: blur(0);
    margin-bottom: 0.7rem;
    height: auto;
    padding: 0.7rem 1rem;
  }

  .promo-banner-leave-to {
    opacity: 0;
    transform: translateY(-10px);
    filter: blur(3px);
    margin-bottom: 0;
    height: 0;
    padding: 0;
    overflow: hidden;
  }
}

.starter-pack-content {
  text-align: left;
  width: 100%;
}

.starter-pack-text {
  font-family: 'Inter' !important;
  font-weight: 500;
  font-size: 13.5px;
  line-height: 1.2;
  color: #8b898b;
  text-align: left;
}

.dao-owner-content {
  text-align: left;
  width: 100%;
}

.dao-owner-text {
  font-family: 'Inter' !important;
  font-weight: 500;
  font-size: 13.5px;
  line-height: 1.2;
  color: #8b898b;
  text-align: left;
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

  &:hover {
    opacity: 0.8;
  }

  &:active {
    opacity: 0.6;
  }
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

// ASICs Shop стили (страница, не модальное окно)
.asics-shop-page {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 201;
  width: 100%;
  height: 100vh;
  display: flex;
  padding-top: 0;
  padding-bottom: 0;
  flex-direction: column;
  align-items: center;
  background:
    url('@/assets/asics-shop-bg.webp') no-repeat top center,
    radial-gradient(ellipse 45% 50% at top center, #31ff8080, transparent),
    #08150a;
  background-attachment: fixed, scroll, scroll;
  overflow-y: auto;
  -ms-overflow-style: none;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }

  .asics-shop-top-panel {
    display: flex;
    width: 90%;
    padding: 1rem 0 .5rem;
    align-items: center;

    .asics-shop-balance {
      display: flex;
      align-items: center;
      min-width: 70px;
      gap: 0.3rem;
      background: linear-gradient(to right, transparent, #00000050);
      border-radius: 1rem;

      .asics-shop-amount {
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
      font-size: clamp(14px, 5.5dvw, 24px);
      text-wrap: nowrap;
    }

    .asics-shop-close {
      width: 20%;
      display: flex;
      align-items: center;
      justify-content: end;
      background: transparent;
      border: none;
      cursor: pointer;
    }
  }

  .asics-shop-toggle-panel {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    width: 90%;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
    position: relative;

    .asics-shop-toggle-panel-spacer {
      min-width: 48px;
    }

    .asics-shop-toggle-container {
      display: flex;
      background: rgba(0, 0, 0, 0.5);
      border-radius: 20px;
      padding: 2px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      grid-column: 2;
      justify-self: center;

      .asics-shop-toggle-btn {
        padding: 8px 20px;
        border-radius: 20px;
        border: none;
        background: transparent;
        color: #fff;
        font-family: 'Inter' !important;
        font-weight: 600;
        font-size: 16px;
        cursor: pointer;
        transition: all 0.3s ease;

        &.active {
          background: linear-gradient(180deg, #e2f974 0%, #009600 100%);
          color: #000;
        }

        &:hover:not(.active) {
          background: rgba(255, 255, 255, 0.1);
        }
      }
    }

    .asics-shop-toggle-panel-right {
      grid-column: 3;
      display: flex;
      justify-content: flex-end;
      align-items: center;
    }

    .asics-shop-promo-button-compact {
      width: 48px;
      height: 48px;
      border-radius: 50%;
      border: none;
      background: linear-gradient(135deg,
        rgba(252, 217, 9, 0.2) 0%,
        rgba(254, 164, 0, 0.2) 50%,
        rgba(226, 249, 116, 0.15) 100%);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(252, 217, 9, 0.4);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow:
        0 4px 15px rgba(252, 217, 9, 0.3),
        inset 0 1px 0 rgba(255, 255, 255, 0.1);
      transition: all 0.3s ease;
      z-index: 10;
      flex-shrink: 0;

      &:hover {
        transform: scale(1.1);
        box-shadow:
          0 6px 20px rgba(252, 217, 9, 0.4),
          inset 0 1px 0 rgba(255, 255, 255, 0.2);
        border-color: rgba(252, 217, 9, 0.6);
      }

      &:active {
        transform: scale(0.95);
      }

      .asics-shop-promo-button-icon {
        color: #ffffff;
        filter: drop-shadow(0 2px 4px rgba(255, 255, 255, 0.3));
        animation: iconPulse 2.5s ease-in-out infinite,
                   iconShake 3s ease-in-out infinite;

        @keyframes iconPulse {
          0%, 100% {
            transform: scale(1);
            opacity: 1;
          }
          50% {
            transform: scale(1.15);
            opacity: 0.95;
          }
        }

        @keyframes iconShake {
          0%, 100% {
            transform: rotate(0deg);
          }
          10%, 30%, 50%, 70%, 90% {
            transform: rotate(-3deg);
          }
          20%, 40%, 60%, 80% {
            transform: rotate(3deg);
          }
        }
      }
    }
  }

  // Анимации для круглой кнопки
  .promo-button-enter-active {
    transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .promo-button-leave-active {
    transition: all 0.4s cubic-bezier(0.55, 0.055, 0.675, 0.19);
  }

  .promo-button-enter-from {
    opacity: 0;
    transform: scale(0) rotate(-180deg);
    filter: blur(4px);
  }

  .promo-button-enter-to {
    opacity: 1;
    transform: scale(1) rotate(0deg);
    filter: blur(0);
  }

  .promo-button-leave-from {
    opacity: 1;
    transform: scale(1) rotate(0deg);
    filter: blur(0);
  }

  .promo-button-leave-to {
    opacity: 0;
    transform: scale(0.8) rotate(180deg);
    filter: blur(4px);
  }

  .asics-shop-promo-banner {
    position: relative;
    width: 90%;
    margin-bottom: 1rem;
    background: linear-gradient(135deg,
      rgba(252, 217, 9, 0.15) 0%,
      rgba(254, 164, 0, 0.15) 50%,
      rgba(226, 249, 116, 0.1) 100%);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(252, 217, 9, 0.3);
    border-radius: 1rem;
    padding: 1.2rem 1rem;
    min-height: auto;
    height: auto;
    max-height: none;
    overflow: visible;
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    animation: promoPulse 4s ease-in-out infinite;
    box-shadow:
      0 4px 20px rgba(252, 217, 9, 0.2),
      inset 0 1px 0 rgba(255, 255, 255, 0.1);

    @keyframes promoPulse {
      0%, 100% {
        box-shadow:
          0 4px 20px rgba(252, 217, 9, 0.2),
          inset 0 1px 0 rgba(255, 255, 255, 0.1);
        border-color: rgba(252, 217, 9, 0.3);
      }
      50% {
        box-shadow:
          0 8px 35px rgba(252, 217, 9, 0.5),
          inset 0 1px 0 rgba(255, 255, 255, 0.2);
        border-color: rgba(252, 217, 9, 0.6);
      }
    }

    .asics-shop-promo-banner-close {
      position: absolute;
      top: 0.75rem;
      right: 0.75rem;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      border: none;
      background: rgba(0, 0, 0, 0.3);
      backdrop-filter: blur(5px);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      z-index: 10;
      transition: background 0.3s ease,
                  transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
      will-change: transform, background;
      backface-visibility: hidden;
      transform: translateZ(0);

      &:hover {
        background: rgba(0, 0, 0, 0.5);
        transform: translateZ(0) scale(1.15);
      }

      &:active {
        transform: translateZ(0) scale(0.95);
        transition: transform 0.1s ease;
      }

      &:not(:hover):not(:active) {
        transform: translateZ(0) scale(1);
      }
    }

    .asics-shop-promo-banner-icon-inline {
      display: inline-block;
      font-size: 1.2rem;
      margin: 0;
      flex-shrink: 0;
      animation: iconBounce 2.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite,
                 iconGlow 2s ease-in-out infinite;
      vertical-align: middle;
      filter: drop-shadow(0 0 4px rgba(252, 217, 9, 0.6));

      @keyframes iconBounce {
        0%, 100% {
          transform: translateY(0) scale(1) rotate(0deg);
        }
        25% {
          transform: translateY(-5px) scale(1.15) rotate(-5deg);
        }
        50% {
          transform: translateY(-8px) scale(1.2) rotate(0deg);
        }
        75% {
          transform: translateY(-5px) scale(1.15) rotate(5deg);
        }
      }

      @keyframes iconGlow {
        0%, 100% {
          filter: drop-shadow(0 0 4px rgba(252, 217, 9, 0.6));
        }
        50% {
          filter: drop-shadow(0 0 8px rgba(252, 217, 9, 0.9));
        }
      }

      &:last-child {
        animation-delay: 0.4s;
      }
    }

    .asics-shop-promo-banner-content {
      position: relative;
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
      z-index: 2;
      width: 100%;
      flex: 1;
      padding: 0 0.5rem;
      min-height: 100%;

      .asics-shop-promo-banner-text {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        flex: 1;
        min-width: 0;
        width: 100%;
        word-wrap: break-word;
        overflow-wrap: break-word;
        overflow: visible;

        .asics-shop-promo-banner-title {
          color: #fcd909;
          font-family: 'Inter' !important;
          font-weight: 700;
          font-size: clamp(14px, 4vw, 18px);
          line-height: 1.4;
          text-shadow: 0 2px 8px rgba(252, 217, 9, 0.4);
          letter-spacing: 0.02em;
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-wrap: nowrap;
          gap: 0.3rem;
        }

        .asics-shop-promo-banner-title-text {
          word-wrap: break-word;
          overflow-wrap: break-word;
          white-space: normal;
          text-align: center;
          display: block;
          width: 100%;
          flex: 1;
          min-width: 0;
        }

        .asics-shop-promo-banner-description {
          color: rgba(255, 255, 255, 0.9);
          font-family: 'Inter' !important;
          font-weight: 500;
          font-size: clamp(11px, 3vw, 13px);
          line-height: 1.6;
          word-wrap: break-word;
          overflow-wrap: break-word;
          white-space: normal;
          width: 100%;
          display: block;
          text-align: center;
        }
      }
    }
  }

  // Анимации для плашки
  .promo-banner-enter-active {
    transition: opacity 0.6s cubic-bezier(0.34, 1.56, 0.64, 1),
                transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1),
                filter 0.6s ease-out;
  }

  .promo-banner-leave-active {
    transition: opacity 0.3s ease-out,
                transform 0.3s ease-out,
                filter 0.3s ease-out,
                margin-bottom 0.3s ease-out,
                height 0.3s ease-out,
                padding 0.3s ease-out;
    pointer-events: none;
  }

  .promo-banner-enter-from {
    opacity: 0;
    transform: translateY(-15px);
    filter: blur(4px);
  }

  .promo-banner-enter-to {
    opacity: 1;
    transform: translateY(0);
    filter: blur(0);
  }

  .promo-banner-leave-from {
    opacity: 1;
    transform: translateY(0);
    filter: blur(0);
    margin-bottom: 1rem;
    height: auto;
    padding: 1.2rem 1rem;
  }

  .promo-banner-leave-to {
    opacity: 0;
    transform: translateY(-10px);
    filter: blur(3px);
    margin-bottom: 0;
    height: 0;
    padding: 0;
    overflow: hidden;
  }
}

// Выносим стили Transition на глобальный уровень, чтобы они применялись и к Boosters shop
.promo-banner-enter-active {
  transition: opacity 0.6s cubic-bezier(0.34, 1.56, 0.64, 1),
              transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1),
              filter 0.6s ease-out;
}

.promo-banner-leave-active {
  transition: opacity 0.3s ease-out,
              transform 0.3s ease-out,
              filter 0.3s ease-out,
              margin-bottom 0.3s ease-out,
              max-height 0.3s ease-out,
              padding-top 0.3s ease-out,
              padding-bottom 0.3s ease-out;
  pointer-events: none;
  overflow: hidden;
}

.promo-banner-enter-from {
  opacity: 0;
  transform: translateY(-15px);
  filter: blur(4px);
}

.promo-banner-enter-to {
  opacity: 1;
  transform: translateY(0);
  filter: blur(0);
}

.promo-banner-leave-from {
  opacity: 1;
  transform: translateY(0);
  filter: blur(0);
  margin-bottom: 1rem;
  max-height: 150px;
  padding-top: 1.2rem;
  padding-bottom: 1.2rem;
}

.promo-banner-leave-to {
  opacity: 0;
  transform: translateY(-10px);
  filter: blur(3px);
  margin-bottom: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
  overflow: hidden;
}

// Выносим стили баннера на глобальный уровень, чтобы они применялись и к Boosters shop
.asics-shop-promo-banner {
  position: relative;
  width: 90%;
  margin-bottom: 1rem;
  background: linear-gradient(135deg,
    rgba(252, 217, 9, 0.15) 0%,
    rgba(254, 164, 0, 0.15) 50%,
    rgba(226, 249, 116, 0.1) 100%);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(252, 217, 9, 0.3);
  border-radius: 1rem;
  padding: 1.2rem 1rem;
  min-height: auto;
  height: auto;
  max-height: none;
  overflow: visible;
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  animation: promoPulseGlobal 4s ease-in-out infinite;
  box-shadow:
    0 4px 20px rgba(252, 217, 9, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);

  @keyframes promoPulseGlobal {
    0%, 100% {
      box-shadow:
        0 4px 20px rgba(252, 217, 9, 0.2),
        inset 0 1px 0 rgba(255, 255, 255, 0.1);
      border-color: rgba(252, 217, 9, 0.3);
    }
    50% {
      box-shadow:
        0 8px 35px rgba(252, 217, 9, 0.5),
        inset 0 1px 0 rgba(255, 255, 255, 0.2);
      border-color: rgba(252, 217, 9, 0.6);
    }
  }

  .asics-shop-promo-banner-close {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    border: none;
    background: rgba(0, 0, 0, 0.3);
    backdrop-filter: blur(5px);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    z-index: 10;
    transition: background 0.3s ease,
                transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    will-change: transform, background;
    backface-visibility: hidden;
    transform: translateZ(0);

    &:hover {
      background: rgba(0, 0, 0, 0.5);
      transform: translateZ(0) scale(1.15);
    }

    &:active {
      transform: translateZ(0) scale(0.95);
      transition: transform 0.1s ease;
    }

    &:not(:hover):not(:active) {
      transform: translateZ(0) scale(1);
    }
  }

  .asics-shop-promo-banner-icon-inline {
    display: inline-block;
    font-size: 1.2rem;
    margin: 0;
    flex-shrink: 0;
    animation: iconBounceGlobal 2.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite,
               iconGlowGlobal 2s ease-in-out infinite;
    vertical-align: middle;
    filter: drop-shadow(0 0 4px rgba(252, 217, 9, 0.6));

    @keyframes iconBounceGlobal {
      0%, 100% {
        transform: translateY(0) scale(1) rotate(0deg);
      }
      25% {
        transform: translateY(-5px) scale(1.15) rotate(-5deg);
      }
      50% {
        transform: translateY(-8px) scale(1.2) rotate(0deg);
      }
      75% {
        transform: translateY(-5px) scale(1.15) rotate(5deg);
      }
    }

    @keyframes iconGlowGlobal {
      0%, 100% {
        filter: drop-shadow(0 0 4px rgba(252, 217, 9, 0.6));
      }
      50% {
        filter: drop-shadow(0 0 8px rgba(252, 217, 9, 0.9));
      }
    }

    &:last-child {
      animation-delay: 0.4s;
    }
  }

  .asics-shop-promo-banner-content {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    z-index: 2;
    width: 100%;
    flex: 1;
    padding: 0 0.5rem;
    min-height: 100%;

    .asics-shop-promo-banner-text {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      flex: 1;
      min-width: 0;
      width: 100%;
      word-wrap: break-word;
      overflow-wrap: break-word;
      overflow: visible;

      .asics-shop-promo-banner-title {
        color: #fcd909;
        font-family: 'Inter' !important;
        font-weight: 700;
        font-size: clamp(14px, 4vw, 18px);
        line-height: 1.4;
        text-shadow: 0 2px 8px rgba(252, 217, 9, 0.4);
        letter-spacing: 0.02em;
        word-wrap: break-word;
        overflow-wrap: break-word;
        white-space: normal;
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-wrap: wrap;
        gap: 0.2rem;
      }

      .asics-shop-promo-banner-description {
        color: rgba(255, 255, 255, 0.9);
        font-family: 'Inter' !important;
        font-weight: 500;
        font-size: clamp(11px, 3vw, 13px);
        line-height: 1.6;
        word-wrap: break-word;
        overflow-wrap: break-word;
        white-space: normal;
        width: 100%;
        display: block;
        text-align: center;
      }
    }
  }
}

.asics-shop-page {
  .asics-shop-list {
    display: flex;
    width: 90%;
    flex-direction: column;
    padding: 10px 0 100px;
    align-items: center;
    gap: 1.5rem;
    overflow-y: auto;
    margin-bottom: 0;
    flex: 1;
    min-height: 0;
    -ms-overflow-style: none;
    scrollbar-width: none;

    &::-webkit-scrollbar {
      display: none;
    }

    .asics-shop-item {
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

      .asics-shop-picture {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0;
        max-width: 95px;

        img {
          min-width: 115px;
          margin: -25px 0 -10px;
          height: auto;
        }
      }

      .asics-shop-tag {
        position: absolute;
        bottom: 0;
        width: 100%;
        text-align: center;
        color: #fff;
        font-family: 'Inter' !important;
        text-transform: uppercase;
        font-weight: 600;
        font-size: 0.55rem;
        background-color: #323232;
        border-radius: 0 0 1rem 1rem;
        padding: 0.2rem 0;
        margin: 0 -1rem;
        z-index: -10;
      }

      .asics-shop-info {
        display: flex;
        flex-direction: column;
        align-items: start;
        justify-content: center;
        width: 100%;
        min-width: 110px;
        line-height: 95%;
        margin-bottom: 10px;

        span:not(.asics-shop-name) {
          text-wrap: nowrap;
        }

        .asics-shop-name {
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
        background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
          linear-gradient(to bottom, #e2f974, #009600);
        border: none;
        cursor: pointer;

        &:active {
          background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
            linear-gradient(to bottom, #e2f97490, #00960090);
        }

        &:disabled {
          background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
            linear-gradient(to bottom, #e2e2e2, #646464);
        }

        span {
          color: #000;
          font-family: 'Inter' !important;
          font-weight: 700;
          font-size: 10px;
        }

        .asics-shop-price {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 0.3rem;
          font-size: 12px;
          line-height: 16pt;

          &.saleprice {
            position: relative;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #000;

            &::before {
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
        }

        .asics-shop-sale-perc {
          position: absolute;
          left: -10px;
          top: -15px;
          padding: 0.1rem 0.2rem;
          transform: rotate(-10deg);
          border-radius: 0.3rem;
          font-family: 'Inter' !important;
          font-size: 12px;
          font-weight: bold;
          box-shadow:
            0 0 15px 2px #fccd0835,
            0 0 2px 2px #00000020;
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
            linear-gradient(to bottom, #fcd909, #fea400);
        }

        .asics-shop-sale-newprice {
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
          box-shadow:
            0 0 15px 2px #fccd0835,
            -1px -1px 2px 2px #00000020;
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
            linear-gradient(to bottom, #fcd909, #fea400);
        }
      }
    }
  }

  .asics-shop-owned-asics {
    display: flex;
    width: 100%;
    flex-direction: column;
    align-items: center;

    .asics-shop-owned-list {
      display: flex;
      width: 100%;
      flex-direction: column;
      gap: 1.5rem;
      padding-bottom: 100px;

      .asics-shop-owned-item {
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

        .asics-shop-picture {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          max-width: 95px;

          img {
            min-width: 115px;
            margin: -25px 0 -10px;
            height: auto;
          }
        }

        .asics-shop-info {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          justify-content: center;
          width: 100%;
          min-width: 110px;
          line-height: 95%;
          margin-bottom: 10px;

          .asics-shop-name {
            color: #fff;
            font-family: 'Inter' !important;
            font-weight: 700;
            font-size: 1rem;
            margin-bottom: 3px;
          }

          span:not(.asics-shop-name) {
            color: #ffffff70;
            font-family: 'Inter' !important;
            font-weight: 400;
            font-size: 10px;
            text-wrap: nowrap;
          }

          .asics-shop-status-row {
            display: flex;
            align-items: center;
            gap: 0.4rem;
            margin-top: 0.35rem;

            .asics-shop-status-badge {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              padding: 0.2rem 0.45rem;
              border-radius: 0.5rem;
              font-size: 9px;
              font-weight: 600;
              text-transform: uppercase;
              letter-spacing: 0.02em;

              &.asics-shop-rented {
                background: linear-gradient(to bottom, #ff9f1c, #ff6f00);
                color: #1b0b00;
              }

              &.asics-shop-connecting {
                background: linear-gradient(to bottom, #31cfff, #1b43ff);
                color: #fff;
              }
            }
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
          padding: 0.35rem 1.1rem;
          border-radius: 0.7rem;
          overflow: visible;
          background: linear-gradient(to bottom, #3a3a3a, #1f1f1f);
          opacity: 0.6;
          cursor: not-allowed;
          pointer-events: none;
          border: none;

          span {
            color: #ffffffa0;
            font-family: 'Inter' !important;
            font-weight: 600;
            font-size: 11px;
            letter-spacing: 0.01em;
          }
        }
      }
    }

    .asics-shop-empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 2rem;
      text-align: center;

      p {
        color: #ffffff70;
        font-family: 'Inter' !important;
        font-size: 16px;
        margin-bottom: 1rem;
      }

      .asics-shop-buy-asic-btn {
        padding: 0.5rem 1rem;
        border-radius: 0.7rem;
        background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
          linear-gradient(to bottom, #e2f974, #009600);
        color: #000;
        font-family: 'Inter' !important;
        font-weight: 700;
        font-size: 14px;
        border: none;
        cursor: pointer;

        &:active {
          background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
            linear-gradient(to bottom, #e2f97490, #00960090);
        }
      }
    }
  }
}

// Модалка обработки покупки ASIC
.processing-modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 100000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  animation: fadeIn 0.3s ease-out;
}

.processing-modal-container {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 90%;
  max-width: 400px;
  padding: 2.5rem 2rem;
  background: radial-gradient(ellipse 80% 40% at top center, rgba(49, 255, 128, 0.15), transparent),
              linear-gradient(135deg, #10151b 0%, #0a0f14 100%);
  border: 1px solid rgba(49, 255, 128, 0.3);
  border-radius: 1.5rem;
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.1),
    0 0 40px rgba(49, 255, 128, 0.1);
  overflow: hidden;
}

.processing-spinner-wrapper {
  position: relative;
  width: 80px;
  height: 80px;
  margin-bottom: 1.5rem;
}

.processing-spinner {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 64px;
  height: 64px;
  border: 4px solid rgba(49, 255, 128, 0.2);
  border-top: 4px solid #31ff80;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.processing-spinner-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 80px;
  height: 80px;
  border: 2px solid rgba(49, 255, 128, 0.1);
  border-top: 2px solid rgba(49, 255, 128, 0.4);
  border-radius: 50%;
  animation: spin 1.5s linear infinite reverse;
}

.processing-content {
  text-align: center;
  z-index: 2;
}

.processing-title {
  color: #31ff80;
  font-family: 'Inter' !important;
  font-weight: 700;
  font-size: 20px;
  margin: 0 0 0.75rem 0;
  text-shadow: 0 0 10px rgba(49, 255, 128, 0.5);
  letter-spacing: 0.02em;
}

.processing-description {
  color: rgba(255, 255, 255, 0.7);
  font-family: 'Inter' !important;
  font-weight: 400;
  font-size: 14px;
  line-height: 1.5;
  margin: 0;
}

.processing-pulse {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(49, 255, 128, 0.2) 0%, transparent 70%);
  animation: pulse 2s ease-in-out infinite;
  z-index: 0;
}

@keyframes spin {
  0% {
    transform: translate(-50%, -50%) rotate(0deg);
  }
  100% {
    transform: translate(-50%, -50%) rotate(360deg);
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.4;
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    opacity: 0.8;
    transform: translate(-50%, -50%) scale(1.2);
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

// Стили для состояния успеха
.processing-modal-container.success-state {
  border-color: rgba(49, 255, 128, 0.5);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.1),
    0 0 60px rgba(49, 255, 128, 0.3);
  background: radial-gradient(ellipse 80% 40% at top center, rgba(49, 255, 128, 0.25), transparent),
              linear-gradient(135deg, #10151b 0%, #0a0f14 100%);
}

.success-animation-wrapper {
  position: relative;
  width: 120px;
  height: 120px;
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.success-checkmark {
  position: relative;
  z-index: 3;
  animation: checkmarkScale 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  filter: drop-shadow(0 0 20px rgba(49, 255, 128, 0.8));
}

.success-rings {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 120px;
  height: 120px;
}

.success-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border: 2px solid rgba(49, 255, 128, 0.4);
  border-radius: 50%;
  animation: ringExpand 1.5s ease-out infinite;
}

.success-ring-1 {
  width: 80px;
  height: 80px;
  animation-delay: 0s;
}

.success-ring-2 {
  width: 100px;
  height: 100px;
  animation-delay: 0.3s;
}

.success-ring-3 {
  width: 120px;
  height: 120px;
  animation-delay: 0.6s;
}

.success-content {
  text-align: center;
  z-index: 2;
  width: 100%;
}

.success-title {
  color: #31ff80;
  font-family: 'Inter' !important;
  font-weight: 700;
  font-size: 24px;
  margin: 0 0 1.25rem 0;
  text-shadow: 0 0 15px rgba(49, 255, 128, 0.6);
  letter-spacing: 0.02em;
  animation: titleFadeIn 0.5s ease-out 0.3s both;
}

.success-asic-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  animation: contentFadeIn 0.6s ease-out 0.5s both;
}

.success-asic-name {
  color: #fff;
  font-family: 'Inter' !important;
  font-weight: 700;
  font-size: 20px;
  text-align: center;
  margin-bottom: 0.5rem;
}

.success-asic-details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 0.75rem;
  border: 1px solid rgba(49, 255, 128, 0.2);
}

.success-detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: 'Inter' !important;
  font-size: 13px;
}

.success-detail-label {
  color: rgba(255, 255, 255, 0.6);
  font-weight: 400;
}

.success-detail-value {
  color: #31ff80;
  font-weight: 600;
}

.success-rarity-badge {
  display: inline-block;
  padding: 0.4rem 1rem;
  border-radius: 0.5rem;
  color: #fff;
  font-family: 'Inter' !important;
  font-weight: 700;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.success-particles {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 1;
}

.particle {
  position: absolute;
  width: 6px;
  height: 6px;
  background: #31ff80;
  border-radius: 50%;
  top: 50%;
  left: 50%;
  animation: particleFloat 2s ease-out infinite;
  animation-delay: var(--delay);
  box-shadow: 0 0 10px rgba(49, 255, 128, 0.8);
}

.particle:nth-child(1) { transform: translate(-50%, -50%) rotate(0deg) translateY(-60px); }
.particle:nth-child(2) { transform: translate(-50%, -50%) rotate(30deg) translateY(-60px); }
.particle:nth-child(3) { transform: translate(-50%, -50%) rotate(60deg) translateY(-60px); }
.particle:nth-child(4) { transform: translate(-50%, -50%) rotate(90deg) translateY(-60px); }
.particle:nth-child(5) { transform: translate(-50%, -50%) rotate(120deg) translateY(-60px); }
.particle:nth-child(6) { transform: translate(-50%, -50%) rotate(150deg) translateY(-60px); }
.particle:nth-child(7) { transform: translate(-50%, -50%) rotate(180deg) translateY(-60px); }
.particle:nth-child(8) { transform: translate(-50%, -50%) rotate(210deg) translateY(-60px); }
.particle:nth-child(9) { transform: translate(-50%, -50%) rotate(240deg) translateY(-60px); }
.particle:nth-child(10) { transform: translate(-50%, -50%) rotate(270deg) translateY(-60px); }
.particle:nth-child(11) { transform: translate(-50%, -50%) rotate(300deg) translateY(-60px); }
.particle:nth-child(12) { transform: translate(-50%, -50%) rotate(330deg) translateY(-60px); }

@keyframes checkmarkScale {
  0% {
    transform: scale(0);
    opacity: 0;
  }
  50% {
    transform: scale(1.2);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes ringExpand {
  0% {
    width: 60px;
    height: 60px;
    opacity: 1;
  }
  100% {
    width: 140px;
    height: 140px;
    opacity: 0;
  }
}

@keyframes titleFadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes contentFadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes particleFloat {
  0% {
    opacity: 1;
    transform: translate(-50%, -50%) translateY(0) scale(1);
  }
  100% {
    opacity: 0;
    transform: translate(-50%, -50%) translateY(-80px) scale(0);
  }
}

@media (max-width: 480px) {
  .processing-modal-container {
    padding: 2rem 1.5rem;
    max-width: 90%;
  }

  .processing-spinner-wrapper {
    width: 64px;
    height: 64px;
    margin-bottom: 1.25rem;
  }

  .processing-spinner {
    width: 48px;
    height: 48px;
    border-width: 3px;
  }

  .processing-spinner-ring {
    width: 64px;
    height: 64px;
  }

  .processing-title {
    font-size: 18px;
  }

  .processing-description {
    font-size: 13px;
  }

  .success-animation-wrapper {
    width: 100px;
    height: 100px;
    margin-bottom: 1.25rem;
  }

  .success-checkmark {
    :deep(svg) {
      width: 64px !important;
      height: 64px !important;
    }
  }

  .success-title {
    font-size: 20px;
    margin-bottom: 1rem;
  }

  .success-asic-name {
    font-size: 18px;
  }

  .success-asic-details {
    padding: 0.75rem;
    gap: 0.4rem;
  }

  .success-detail-item {
    font-size: 12px;
  }
}

// Анимация пульсации для кнопки Activate
@keyframes pulse-green {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(81, 207, 102, 0.6);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(81, 207, 102, 0);
  }
}

// Boosters Shop стили (страница, не модальное окно)
.boosters-shop-page {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 201;
  width: 100%;
  height: 100vh;
  display: flex;
  padding-top: 0;
  padding-bottom: 0;
  flex-direction: column;
  align-items: center;
  background:
    url('@/assets/asics-shop-bg.webp') no-repeat top center,
    radial-gradient(ellipse 45% 50% at top center, rgba(49, 207, 255, 0.5), transparent),
    #0a1a2a;
  background-attachment: fixed, scroll, scroll;
  overflow-y: auto;
  -ms-overflow-style: none;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }

  .boosters-shop-top-panel {
    display: flex;
    width: 90%;
    padding: 1rem 0 .5rem;
    align-items: center;

    .boosters-shop-balance {
      display: flex;
      align-items: center;
      min-width: 70px;
      gap: 0.3rem;
      background: linear-gradient(to right, transparent, #00000050);
      border-radius: 1rem;

      .boosters-shop-amount {
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
      font-size: clamp(14px, 5.5dvw, 24px);
      text-wrap: nowrap;
    }

    .boosters-shop-close {
      width: 20%;
      display: flex;
      align-items: center;
      justify-content: end;
      background: transparent;
      border: none;
      cursor: pointer;
    }
  }

  .boosters-shop-toggle-panel {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    width: 90%;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
    position: relative;

    .boosters-shop-toggle-panel-spacer {
      min-width: 48px;
    }

    .boosters-shop-toggle-container {
      display: flex;
      background: rgba(0, 0, 0, 0.5);
      border-radius: 20px;
      padding: 2px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      grid-column: 2;
      justify-self: center;

      .boosters-shop-toggle-btn {
        padding: 8px 20px;
        border-radius: 20px;
        border: none;
        background: transparent;
        color: #fff;
        font-family: 'Inter' !important;
        font-weight: 600;
        font-size: 16px;
        cursor: pointer;
        transition: all 0.3s ease;

        &.active {
          background: linear-gradient(180deg, rgba(49, 207, 255, 0.8) 0%, #31CFFF 100%);
          color: #000;
        }

        &:hover:not(.active) {
          background: rgba(255, 255, 255, 0.1);
        }
      }
    }

    .boosters-shop-toggle-panel-right {
      grid-column: 3;
      display: flex;
      justify-content: flex-end;
      align-items: center;

      .asics-shop-promo-button-compact {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        border: none;
        background: linear-gradient(135deg,
          rgba(252, 217, 9, 0.2) 0%,
          rgba(254, 164, 0, 0.2) 50%,
          rgba(226, 249, 116, 0.15) 100%);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(252, 217, 9, 0.4);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow:
          0 4px 15px rgba(252, 217, 9, 0.3),
          inset 0 1px 0 rgba(255, 255, 255, 0.1);
        transition: all 0.3s ease;
        z-index: 10;
        flex-shrink: 0;

        &:hover {
          transform: scale(1.1);
          box-shadow:
            0 6px 20px rgba(252, 217, 9, 0.4),
            inset 0 1px 0 rgba(255, 255, 255, 0.2);
          border-color: rgba(252, 217, 9, 0.6);
        }

        &:active {
          transform: scale(0.95);
        }

        .asics-shop-promo-button-icon {
          color: #ffffff;
          filter: drop-shadow(0 2px 4px rgba(255, 255, 255, 0.3));
          animation: iconPulse 2.5s ease-in-out infinite,
                     iconShake 3s ease-in-out infinite;

          @keyframes iconPulse {
            0%, 100% {
              transform: scale(1);
              opacity: 1;
            }
            50% {
              transform: scale(1.15);
              opacity: 0.95;
            }
          }

          @keyframes iconShake {
            0%, 100% {
              transform: rotate(0deg);
            }
            10%, 30%, 50%, 70%, 90% {
              transform: rotate(-3deg);
            }
            20%, 40%, 60%, 80% {
              transform: rotate(3deg);
            }
          }
        }
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
      backdrop-filter: blur(10px);

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

  .boosters-shop-list {
    display: flex;
    width: 90%;
    flex-direction: column;
    padding: 10px 0 120px;
    align-items: center;
    gap: 1.5rem;
    overflow-y: scroll;
    overflow-x: hidden;
    margin-bottom: 0;
    -ms-overflow-style: none;
    scrollbar-width: none;

    &::-webkit-scrollbar {
      display: none;
    }

    .boosters-shop-item {
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

      &.has-gold-stroke {
        padding: calc(0.7rem - 2px) calc(1rem - 2px);
        position: relative;

        &::after {
          content: '';
          position: absolute;
          inset: 0;
          border-radius: 1rem;
          padding: 2px;
          background: linear-gradient(180deg, #FEA400 0%, #FCD909 100%);
          -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
          -webkit-mask-composite: xor;
          mask-composite: exclude;
          pointer-events: none;
          z-index: -20;
        }
      }

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
          mask-composite: exclude;
          pointer-events: none;
          z-index: -20;
        }
      }

      &.has-blue-stroke {
        padding: calc(0.7rem - 2px) calc(1rem - 2px);
        position: relative;

        &::after {
          content: '';
          position: absolute;
          inset: 0;
          border-radius: 1rem;
          padding: 2px;
          background: linear-gradient(270deg, rgba(49, 207, 255, 1) 0%, rgba(31, 255, 255, 1) 100%);
          -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
          -webkit-mask-composite: xor;
          mask-composite: exclude;
          pointer-events: none;
          z-index: -20;
        }
      }

      &.power-plant-tall {
        // Фиксированная высота для премиальных станций (можно изменить)
        height: 120px;
        padding: 1rem 1rem;
      }

      .boosters-shop-info-icon-top {
        position: absolute;
        top: 5px;
        right: 8px;
        width: 18px;
        height: 18px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #FFFFFF;
        border-radius: 50%;
        cursor: pointer;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 9px;
        color: #000000;
        z-index: 10;
        transition: all 0.2s ease;

        &:hover {
          background: rgba(255, 255, 255, 0.8);
        }
      }

      .boosters-shop-picture {
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        max-width: 95px;
        gap: 0;

        .boosters-shop-icon {
          font-size: 40px;
        }

        .boosters-shop-image {
          min-width: 115px;
          margin: -25px 0 -10px;
          height: auto;
          position: relative;
          z-index: 1;

          &.hide-under-tag {
            z-index: -15;
          }
        }
      }

      .boosters-shop-info {
        display: flex;
        flex-direction: column;
        align-items: start;
        justify-content: center;
        width: 100%;
        min-width: 110px;
        line-height: 95%;
        margin-bottom: 10px;

        .boosters-shop-type {
          color: #fff;
          font-family: 'Inter' !important;
          font-weight: 700;
          font-size: 1rem;
          margin-bottom: 3px;
          white-space: pre-line;
        }

        .boosters-shop-description {
          color: #ffffff70;
          font-family: 'Inter' !important;
          font-weight: 400;
          font-size: 10px;
          text-wrap: nowrap;
          display: flex;
          align-items: center;
          gap: 0.25rem;

          &.boosters-shop-benefit-match {
            color: #51cf66;
            font-weight: 600;
          }

          &.boosters-shop-benefit-mismatch {
            color: #ff6b6b;
            font-weight: 600;
          }

          .boosters-shop-check-icon {
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

          .boosters-shop-cross-icon {
            color: #ff6b6b;
            font-weight: bold;
            font-size: 12px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 16px;
            height: 16px;
            background: rgba(255, 107, 107, 0.2);
            border-radius: 50%;
            flex-shrink: 0;
          }

          .building-now {
            display: inline-block;

            .building-now-letter {
              display: inline-block;
              font-weight: 600;
              color: #fcd909;
              text-shadow: 0 0 8px rgba(252, 217, 9, 0.8);
              animation: building-now-glow 2s ease-in-out infinite;
            }
          }
        }
      }

      @keyframes building-now-glow {
        0%, 100% {
          text-shadow: 0 0 8px rgba(252, 217, 9, 0.8);
        }
        50% {
          text-shadow: 0 0 16px rgba(252, 217, 9, 1), 0 0 24px rgba(252, 217, 9, 0.6);
        }
      }

      .boosters-shop-buy-btn {
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

          .boosters-shop-price {
            color: #000;
          }
        }

        &.btn-purple {
          background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
            linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(152, 81, 236, 1) 50%, rgba(94, 124, 234, 1) 100%);
        }

        &.btn-blue {
          background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
            linear-gradient(270deg, rgba(49, 207, 255, 1) 0%, rgba(31, 255, 255, 1) 100%);

          .boosters-shop-price {
            color: #000;
          }
        }

        &:active {
          background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
            linear-gradient(to bottom, #e2f97490, #00960090);
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

        .boosters-shop-price {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 0.3rem;
          font-size: 12px;
          line-height: 16pt;
          font-weight: 700;
          font-family: 'Inter' !important;
          color: #000;

          &.boosters-shop-saleprice {
            position: relative;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #000;

            &::before {
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
        }

        .boosters-shop-sale-perc {
          position: absolute;
          left: -10px;
          top: -15px;
          padding: 0.1rem 0.2rem;
          transform: rotate(-10deg);
          border-radius: 0.3rem;
          font-family: 'Inter' !important;
          font-size: 12px;
          font-weight: bold;
          box-shadow:
            0 0 15px 2px #fccd0835,
            0 0 2px 2px #00000020;
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
            linear-gradient(to bottom, #fcd909, #fea400);
        }

        .boosters-shop-sale-newprice {
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
          box-shadow:
            0 0 15px 2px #fccd0835,
            -1px -1px 2px 2px #00000020;
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
            linear-gradient(to bottom, #fcd909, #fea400);
        }
      }

      .boosters-shop-tag {
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

    .boosters-shop-owned-boosters {
      width: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1rem;
      padding-bottom: 120px;

      .boosters-shop-item {
        &.boost-inactive {
          opacity: 0.6;
          filter: grayscale(0.3);
        }

        .boosters-shop-inactive-label {
          display: block;
          color: #ff6b6b;
          font-family: 'Inter' !important;
          font-weight: 500;
          font-size: 11px;
          margin-top: 4px;
          margin-bottom: 4px;
        }

        .boosters-shop-active-label {
          display: block;
          color: #51cf66;
          font-family: 'Inter' !important;
          font-weight: 500;
          font-size: 11px;
          margin-top: 4px;
          margin-bottom: 4px;
        }

        .boosters-shop-toggle-btn {
          position: absolute;
          top: 50%;
          right: 5px;
          transform: translateY(-50%);
          display: flex;
          align-items: center;
          justify-content: center;
          min-width: 75px;
          width: 75px;
          padding: 0.2rem 0.7rem;
          margin-right: 0.2rem;
          margin-left: auto;
          border: none;
          border-radius: 0.7rem;
          cursor: pointer;
          transition: all 0.3s ease;
          color: #fff;
          font-family: 'Inter' !important;
          font-weight: 600;
          font-size: 11px;
          z-index: 100;
          // Базовый фон - зеленый для кнопки Activate (если не применены другие классы)
          background: linear-gradient(to bottom, #51cf66, #37b24d);

          &.boost-inactive-btn {
            background: linear-gradient(to bottom, #51cf66, #37b24d);
            animation: pulse-green 2s ease-in-out infinite;

            &:hover {
              background: linear-gradient(to bottom, #69db7c, #51cf66);
              transform: translateY(-50%) scale(1.05);
              animation: none; // Останавливаем пульсацию при hover
            }

            &:active {
              animation: none; // Останавливаем пульсацию при клике
            }
          }

          &.boost-conditions-not-met {
            background: linear-gradient(to bottom, #ff6b6b, #e03131);
            cursor: not-allowed;
            opacity: 0.8;

            &:hover {
              background: linear-gradient(to bottom, #ff6b6b, #e03131);
              transform: translateY(-50%);
            }

            &:disabled {
              opacity: 0.8;
              cursor: not-allowed;
              pointer-events: none; // Полностью блокируем клики
            }
          }

          &:disabled {
            opacity: 0.8;
            cursor: not-allowed;
            pointer-events: none; // Полностью блокируем клики для всех disabled кнопок
          }

          &.boost-active {
            background: linear-gradient(to bottom, #ff6b6b, #e03131);

            &:hover:not(:disabled) {
              background: linear-gradient(to bottom, #ff8787, #ff6b6b);
              transform: translateY(-50%) scale(1.05);
            }

            &:disabled {
              opacity: 0.6;
              cursor: not-allowed;
              background: linear-gradient(to bottom, #868e96, #495057);
            }
          }

          &.boost-disabled-yellow {
            background: linear-gradient(to bottom, #ffd43b, #fcc419);
            cursor: not-allowed;
            opacity: 0.9;
            animation: none; // Убираем анимацию пульсации
            color: #ffffff; // Черный цвет текста

            &:hover {
              background: linear-gradient(to bottom, #ffd43b, #fcc419);
              transform: translateY(-50%);
              animation: none; // Убираем анимацию при hover
              color: #ffffff; // Черный цвет текста при hover
            }

            &:disabled {
              opacity: 0.9;
              cursor: not-allowed;
              pointer-events: none;
              animation: none; // Убираем анимацию для disabled
              color: #ffffff; // Черный цвет текста для disabled
            }
          }

            &:active:not(:disabled) {
            transform: translateY(-50%) scale(0.95);
          }
        }
      }

      .boosters-shop-empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 3rem 1rem;
        text-align: center;

        p {
          color: rgba(255, 255, 255, 0.7);
          font-family: 'Inter' !important;
          font-size: 16px;
          margin-bottom: 1.5rem;
        }

        .boosters-shop-buy-booster-btn {
          padding: 0.75rem 1.5rem;
          border-radius: 0.7rem;
          border: none;
          background: linear-gradient(to bottom, #e2f974, #009600);
          color: #000;
          font-family: 'Inter' !important;
          font-weight: 700;
          font-size: 14px;
          cursor: pointer;
          transition: all 0.3s ease;

          &:hover {
            transform: scale(1.05);
          }

          &:active {
            transform: scale(0.95);
          }
        }
      }

      .premium-station-status {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 14px;
        margin: 12px 0;
        border: 1px solid #3f3f46;
        border-radius: 10px;
        background: #0f1319;
      }

      .premium-station-status__title {
        color: #9ca3af;
        font-size: 12px;
      }

      .premium-station-status__value {
        color: #fff;
        font-weight: 700;
      }

      .premium-station-status__disable {
        margin-left: auto;
        padding: 8px 12px;
        border-radius: 8px;
        background: #fe3b59;
        color: #fff;
        font-weight: 600;
        border: none;
      }

      .premium-station-status__disable:disabled {
        opacity: 0.6;
      }
    }

  }
}
</style>
