<script setup>
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref, watch } from 'vue'
const EquipButton = defineAsyncComponent(() => import('@/assets/equip.svg'))
const Exit = defineAsyncComponent(() => import('@/assets/exit.svg'))
const Disk = defineAsyncComponent(() => import('@/assets/boost_disk.svg'))
const NFTBoost = defineAsyncComponent(() => import('@/assets/mintable.svg'))
const InfoIcon = defineAsyncComponent(() => import('@/assets/white-info.svg'))
const Cart = defineAsyncComponent(() => import('@/assets/cart.svg'))
import { useTabsStore } from '@/stores/tabs'
import { useAppStore } from '@/stores/app'
import { useTelegram } from '@/services/telegram'
import { host, tonapi } from '../../axios.config'
import { useTonAddress, useTonConnectUI } from '@townsquarelabs/ui-vue'
import { beginCell, toNano } from '@ton/core'
import { RouterLink } from 'vue-router'
import ModalNew from '@/components/ModalNew.vue'
import RedirectModal from '@/components/RedirectModal.vue'
import SpecialPriceModal from '@/components/SpecialPriceModal.vue'
import WithdrawModal from '@/components/WithdrawModal.vue'
import ReconnectModal from '@/components/ReconnectModal.vue'
import InfoModal from '@/components/InfoModal.vue'
import asicsSheet, { gemsSheet, gemsSaleActive, gemsSalePercent, gemsSaleEndDate, getGemPrice, sortGemsBySale, asicsSaleActive, asicsSalePercent, asicsSaleEndDate, getAsicPrice, isAsicInSale } from '@/services/data'
import _ from "lodash"
import { getAsicData } from '@/utils/asics'
import { useI18n } from 'vue-i18n'

import { useScreen } from '@/composables/useScreen'
import SpeedUpModal from '@/components/SpeedUpModal.vue'

const app = useAppStore()
const all_asics = computed(() => app.getAsicsFromStorage())
const tabs = useTabsStore()
const { width } = useScreen()
const { tg, user } = useTelegram()
const { t, locale } = useI18n()
const ton_address = useTonAddress()
const connectedAddressString = useTonAddress(false)
const asicsIsOpen = useTabsStore()
const premiumActive = computed(() => new Date(app.user?.premium_sub_expires) >= new Date())

// Состояние для закрытия промо-плашки
const promoBannerClosed = ref(false)
const gemsPromoBannerClosed = ref(false)

let controller = null

const miningTime = ref(0)
const miningInterval = ref(null)
// const openMiningStopped = ref(false)

const isProcessing = ref(false)

const { tonConnectUI } = useTonConnectUI()

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

const openRedirectModal = ref(false)
const redirectLink = ref(null)
const redirectItemName = ref(null)
const redirectItemClass = ref(null)

const openReconnectModal = ref(false)
const reconnectExample = ref(null)

const openSpecialModal = ref(false)
const openClaim = ref(false)
const openGemInfo = ref(false)
const gemInfoText = ref('')
const currentGemItem = ref(null)
const openStarterPackInfo = ref(false)
const openDaoOwnerInfo = ref(false)
const openHydroelectricInfo = ref(false)
const openOrbitalInfo = ref(false)
const openOrbitalCraftInfo = ref(false)

const currBuyAsic = ref(null)

const hideSlotInfo = ref({})
const showProgressPercent = ref(true)

const booostedFarmConsumtion = computed(() => {
  let cons = +app?.user?.total_farm_consumption + +app?.user?.rent_farm_consumption_plus - +app?.user?.rent_farm_consumption_minus
  if (app?.user?.is_powerbank_active) {
    cons -= +app?.user?.powerbank_max_consume
  }
  if (app?.user?.magnit_expires && new Date(app?.user?.magnit_expires) > new Date()) {
    cons *= 1 - (premiumActive.value ? 24 : app?.boosters?.find((el) => el?.slug == 'magnit')?.n1) / 100
  }
  return +cons.toFixed(2)
})

const curr_boost = ref(0)

const nextBoost = () => {
  curr_boost.value = (curr_boost.value + 1) % 3
}

const currBoost = computed(() => {
  let name, active, time, forever = false
  if (curr_boost.value == 0) {
    name = 'manager'
    if (app?.user?.manager_expires && new Date(app?.user?.manager_expires) > new Date()) {
      active = true
      const now = new Date()
      const expires = new Date(app?.user?.manager_expires)
      const timeDiff = expires - now // Time difference in milliseconds
      const totalMinutes = Math.floor(timeDiff / 1000 / 60) // Convert to minutes
      const hours = Math.floor(totalMinutes / 60) // Full hours
      const minutes = totalMinutes % 60 // Remaining minutes
      const formattedHours = String(hours).padStart(2, '0')
      const formattedMinutes = String(minutes).padStart(2, '0')
      time = `${formattedHours}:${formattedMinutes}`
      forever = expires.getFullYear() === 2100
    } else {
      active = false
      time = '00:00'
      forever = false
    }
    return { name, active, time, forever }
  } else if (curr_boost.value == 1) {
    name = 'magnit'
    if (app?.user?.magnit_expires && new Date(app?.user?.magnit_expires) > new Date()) {
      active = true
      const now = new Date()
      const expires = new Date(app?.user?.magnit_expires)
      const timeDiff = expires - now // Time difference in milliseconds
      const totalMinutes = Math.floor(timeDiff / 1000 / 60) // Convert to minutes
      const hours = Math.floor(totalMinutes / 60) // Full hours
      const minutes = totalMinutes % 60 // Remaining minutes
      const formattedHours = String(hours).padStart(2, '0')
      const formattedMinutes = String(minutes).padStart(2, '0')
      time = `${formattedHours}:${formattedMinutes}`
      forever = expires.getFullYear() === 2100
    } else {
      active = false
      time = '00:00'
      forever = false
    }
    return { name, active, time, forever }
  } else if (curr_boost.value == 2) {
    name = 'powerbank'
    if (app?.user?.is_powerbank_active) {
      active = true
      const now = new Date()
      const expires = app?.user?.powerbank_activated
        ? new Date(app?.user?.powerbank_activated)
        : new Date(Date.now() - 1000 * 60 * 60)
      const timeDiff = now - expires
      const totalMinutes = Math.floor(timeDiff / 1000 / 60)
      const hours = Math.floor(totalMinutes / 60)
      const minutes = totalMinutes % 60
      const formattedHours = String(hours).padStart(2, '0')
      const formattedMinutes = String(minutes).padStart(2, '0')
      time = `${formattedHours}:${formattedMinutes}`
      forever = false
    } else {
      active = false
      time = '00:00'
      forever = false
    }
    return { name, active, time, forever }
  }
  return {}
})

const boostActive = (boost) => {
  return computed(() => {
    if (
      boost == 0 &&
      app?.user?.manager_expires &&
      new Date(app?.user?.manager_expires) > new Date()
    )
      return true
    if (boost == 1 && app?.user?.magnit_expires && new Date(app?.user?.magnit_expires) > new Date())
      return true
    if (boost == 2 && app?.user?.is_powerbank_active) return true
    return false
  }).value
}

const specialModalResponse = async (res) => {
  openSpecialModal.value = false
  if (res.check) {
    const asicIndex = asicsSheet.findIndex((el) => el.name == currBuyAsic.value.name)
    const asicItem = asicsSheet[asicIndex]
    // ВАЖНО: Используем оригинальную цену без скидки для транзакции в смартконтракт
    const finalPrice = asicItem?.price
    await buyAsics(
      asicIndex,
      finalPrice,
      asicItem?.link,
      false, // Не показываем модальное окно повторно
      asicItem?.shop
    )
  }
}

const checkReconnect = async (val) => {
  openReconnectModal.value = false
  reconnectExample.value = null
  if (val) {
    showModal(val?.status, val?.title, val?.body)
    await app.initUser()
  }
}

const reconnectTime = computed(() => {
  const now = new Date()
  const last_activate = new Date(app?.user?.stop_mining_activate_last)
  const timeDiff = now - last_activate
  return `${Math.floor((10 * 60 * 1000 - timeDiff) / 60000)
    .toString()
    .padStart(2, '0')}:${Math.floor(((10 * 60 * 1000 - timeDiff) % 60000) / 1000)
      .toString()
      .padStart(2, '0')}`
})

// Форматуємо час у вигляді 000:00:00
const formattedTime = computed(() => {
  const hours = String(Math.floor(miningTime.value / 3600)).padStart(3, '0')
  const minutes = String(Math.floor((miningTime.value % 3600) / 60)).padStart(2, '0')
  const seconds = String(miningTime.value % 60).padStart(2, '0')
  return `${hours}:${minutes}:${seconds}`
})

// Запуск лічильника
function startTimer() {
  miningInterval.value = setInterval(() => {
    const now = new Date()
    miningTime.value = Math.floor((now - new Date(app.user.true_started_mining_at)) / 1000) // Обчислюємо час у секундах
  }, 1000)
}

// Зупинка і обнулення
function stopAndResetTimer() {
  miningTime.value = 0
  if (miningInterval.value) {
    clearInterval(miningInterval.value)
    miningInterval.value = null
  }
}

const imagePath = (asic) => {
  const com = computed(
    () => new URL(`../assets/${asic?.toString().toUpperCase()}.webp`, import.meta.url).href,
  )
  return com
}

const imagePathAsics = (asic) => {
  const com = computed(
    () => new URL(`../assets/asics/${asic?.toString().toUpperCase()}.webp`, import.meta.url).href,
  )
  return com
}

const imagePathGems = (path) => {
  if (!path) return null
  const com = computed(() => {
    // Remove @/ prefix if present
    const cleanPath = path.replace(/^@\//, '')
    const fileName = cleanPath.replace(/.*\//, '')
    return new URL(`../assets/gems/${fileName}`, import.meta.url).href
  })
  return com
}

const getTimedNftData = (item) => {
  return app.timed_nfts?.find(el => el.nft_address == (item.address ?? item.nft))
}

const getTimedNftProgress = (item) => {
  const timedNft = getTimedNftData(item)
  if (!timedNft?.block_until) return 0

  const now = new Date()
  const future = new Date(timedNft.block_until)
  const diffMs = future - now

  if (diffMs <= 0) return 100

  // Calculate progress based on the actual block duration
  if (timedNft.blocked_at) {
    const blockedAt = new Date(timedNft.blocked_at)
    const totalDuration = future.getTime() - blockedAt.getTime()
    const elapsed = totalDuration - diffMs
    return Math.min(Math.max((elapsed / totalDuration) * 100, 0), 100)
  } else {
    // Fallback to 24 hours if we can't determine the start time
    const totalDuration = 24 * 60 * 60 * 1000 // 24 hours in milliseconds
    const elapsed = totalDuration - diffMs
    return Math.min(Math.max((elapsed / totalDuration) * 100, 0), 100)
  }
}

// Add reactive timer for progress updates
const progressUpdateInterval = ref(null)

onMounted(() => {
  // Update progress every minute
  progressUpdateInterval.value = setInterval(() => {
    // Force reactivity by triggering a reactive update
    app.timed_nfts = [...(app.timed_nfts || [])]
  }, 60000) // Update every minute
})

onUnmounted(() => {
  if (progressUpdateInterval.value) {
    clearInterval(progressUpdateInterval.value)
  }
})

async function claim() {
  await app?.initUser()
  if (!ton_address.value) {
    showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }
  if (minedTokens.value < (app.withdraw_config?.min_claim || 2)) {
    showModal(
      'warning',
      t('notification.st_attention'),
      t('notification.min_claim_fbtc', { value: app.withdraw_config?.min_claim || 2 }),
    )
    return
  }
  if (minedTokensWallet.value < (app.withdraw_config?.min_claim || 2)) {
    showModal(
      'warning',
      t('notification.st_attention'),
      t('notification.min_claim_fbtc_wallet', { value: app.withdraw_config?.min_claim || 2, address: ton_address.value?.slice(0, 5) + '...' + ton_address.value?.slice(-5) }),
    )
    return
  }
  openClaim.value = true
}

const getClaimResponse = (val) => {
  openClaim.value = false
  showModal(val.status, val.title, val.body)
}

const minedTokens = computed(() => {
  return +(app?.user?.mined_tokens_balance + app?.user?.mined_tokens_balance_s21 + app?.user?.mined_tokens_balance_sx).toFixed(3) || 0
})

const minedTokensWallet = computed(() => {
  return +(app?.wallet_info?.tbtc_amount + app?.wallet_info?.tbtc_amount_s21 + app?.wallet_info?.tbtc_amount_sx).toFixed(3) || 0
})

const getTimeRemaining = (futureISO) => {
  if (!futureISO) {
    return `00${t('common.d')} 00${t('common.h')} 00${t('common.m')}`
  }
  const speedUpTime = ref(`00:00:00`)
  const timeRemaining = ref(`00${t('common.d')} 00${t('common.h')} 00${t('common.m')}`)
  const timeRemainingMs = ref('00:00:00')
  const progressPercent = ref(0)

  const updateTime = () => {
    const now = new Date()
    const future = new Date(futureISO)
    const diffMs = future - now
    timeRemainingMs.value = diffMs

    if (diffMs <= 0) {
      progressPercent.value = 100
      return `00${t('common.d')} 00${t('common.h')} 00${t('common.m')}`
    }

    // Calculate progress based on the actual block duration
    // We need to find when the blocking started to calculate total duration
    const timedNft = app.timed_nfts?.find(el => el.block_until === futureISO)
    if (timedNft && timedNft.blocked_at) {
      const blockedAt = new Date(timedNft.blocked_at)
      const totalDuration = future.getTime() - blockedAt.getTime()
      const elapsed = totalDuration - diffMs
      progressPercent.value = Math.min(Math.max((elapsed / totalDuration) * 100, 0), 100)
    } else {
      // Fallback to 24 hours if we can't determine the start time
      const totalDuration = 24 * 60 * 60 * 1000 // 24 hours in milliseconds
      const elapsed = totalDuration - diffMs
      progressPercent.value = Math.min(Math.max((elapsed / totalDuration) * 100, 0), 100)
    }

    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))
    const seconds = Math.floor((diffMs % (1000 * 60)) / 1000)

    const formattedDays = String(days).padStart(2, '0')
    const formattedHours = String(hours).padStart(2, '0')
    const formattedMinutes = String(minutes).padStart(2, '0')
    const formattedSeconds = String(seconds).padStart(2, '0')

    timeRemaining.value = `${formattedDays}${t('common.d')} ${formattedHours}${t('common.h')} ${formattedMinutes}${t('common.m')}`
    speedUpTime.value = `${formattedHours}:${formattedMinutes}:${formattedSeconds}`
  }

  // Update immediately
  updateTime()

  // Set interval to update every minute (60000ms) since seconds are no longer displayed
  const interval = setInterval(updateTime, 60000)

  // Clear interval on component unmount
  onUnmounted(() => clearInterval(interval))

  return {
    time: timeRemaining.value,
    speedup: speedUpTime.value,
    remain: timeRemainingMs.value,
    progress: progressPercent.value
  }
}

const buyAsics = async (item, price, link, sale, shop = true) => {
  if (!shop) {
    return
  }
  // Для SX ULTRA PRO всегда редиректим на GetGems (не показываем модальное окно с акцией)
  if (link) {
    redirectLink.value = link
    redirectItemName.value = asicsSheet[item]?.name || null
    redirectItemClass.value = null
    openRedirectModal.value = true
    return
  }
  if (sale) {
    const asicItem = asicsSheet[item]
    // Подготавливаем данные для модального окна
    currBuyAsic.value = {
      ...asicItem,
      new_price: getAsicPrice(asicItem),
      perc: asicsSalePercent
    }
    openSpecialModal.value = true
    return
  }
  if (isProcessing.value) return
  isProcessing.value = true
  if (!ton_address.value) {
    showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }
  const mainCell = beginCell()
    .storeUint(1, 32)
    .storeUint(1, 64)
    .storeUint(+item, 4)
    .endCell()
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
    // showModal('error', t('notification.st_error'), t('notification.failed_transaction'))
  } finally {
    isProcessing.value = false
  }
}

const buyGem = async (gemItem) => {
  if (!gemItem?.shop) return

  // Orbital Power Plant: открываем модалку инструкции крафта
  if (gemItem?.type === 'Orbital Power Plant') {
    openOrbitalCraftInfo.value = true
    return
  }

  // Если это стартер пакет - используем отправку TON
  if (gemItem?.type === 'Starter Pack') {
    if (isProcessing.value) return
    isProcessing.value = true

    if (!ton_address.value) {
      showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
      isProcessing.value = false
      return
    }

    // Скидаємо стан модального вікна перед новою транзакцією
    try {
      await tonConnectUI.closeModal()
    } catch {
      // Ігноруємо помилки закриття модального вікна
    }

    try {
      const transferAmount = gemsSaleActive ? getGemPrice(gemItem) : gemItem.price
      const receiveAddress = 'UQDJMlSoT5-5CdCQROyN4SK_j0kMxpexF0Q3-boppeO7kZdl'

      // Простая передача TON без дополнительных данных
      const simplePayload = beginCell()
        .storeUint(0, 32) // op: 0 = simple transfer
        .storeUint(0, 64) // query id
        .endCell()

      const transactionData = {
        validUntil: Date.now() + 1000 * 60 * 5, // 5 minutes
        messages: [
          {
            address: receiveAddress,
            amount: toNano(transferAmount).toString(),
            payload: simplePayload.toBoc().toString('base64'),
          },
        ],
      }

      const result = await tonConnectUI.sendTransaction(transactionData, {
        modals: ['before', 'success'],
        notifications: [],
      })

      if (result?.boc) {
        showModal('success', t('notification.st_success'), `Успешно куплен Starter Pack за ${transferAmount} TON!`)
        await app.initUser()
      }
    } catch (err) {
      console.log('Error in buyGem:', err)
      showModal('error', t('notification.st_error'), t('notification.failed_transaction'))
        } finally {
      isProcessing.value = false
    }
  } else {
    // Для всех остальных - редирект на getgems.io
    const link = gemItem?.link || 'https://getgems.io'
    redirectLink.value = link
    redirectItemName.value = gemItem?.type || gemItem?.name
    // Передаём класс только для GEMS (не для DAO)
    redirectItemClass.value = (gemItem?.type !== 'DAO Owner' && gemItem?.rarity) ? t(`gems.${gemItem.rarity}`) : ''
    openRedirectModal.value = true
  }
}

function openAsics(side = true) {
  let opt = side == true ? true : false
  asicsIsOpen.setOpenAsicsShop(opt)
  // Сбрасываем состояние закрытия промо-плашки при открытии магазина
  if (opt) {
    promoBannerClosed.value = false
    gemsPromoBannerClosed.value = false
  }
  if (tg.platform === 'android') {
    tg.HapticFeedback.notificationOccurred('success');
  } else {
    tg.HapticFeedback.impactOccurred('medium');
  }
  if (asicsIsOpen.category !== 'miner') {
    asicsIsOpen.setCategory('miner')
  }
}

function openEquip(side = true) {
  let opt = side == true ? true : false
  asicsIsOpen.setOpenAsicsShop(false)
  asicsIsOpen.setOpenEquip(opt)
  if (tg.platform === 'android') {
    tg.HapticFeedback.notificationOccurred('success');
  } else {
    tg.HapticFeedback.impactOccurred('medium');
  }
}

const cachedAsicNfts = ref(_.concat(app?.nfts?.filter(el => !app?.rentOutNfts?.some(item => item?.nft == el?.address) && (el?.metadata?.name?.toLowerCase()?.includes('asic') || el?.metadata?.name?.toLowerCase()?.includes('sbt'))), app?.rentedNfts))

const updateAsicNfts = () => {
  const upd_nfts = _.concat(app?.nfts?.filter(el => !app?.rentOutNfts?.some(item => item?.nft == el?.address) && (el?.metadata?.name?.toLowerCase()?.includes('asic') || el?.metadata?.name?.toLowerCase()?.includes('sbt'))), app?.rentedNfts);
  if (upd_nfts !== cachedAsicNfts.value) {
    cachedAsicNfts.value = upd_nfts;
  }
}

const rentedPlusSpeed = computed(() => {
  return (app?.rentedNfts?.filter(el => getTimeRemaining(el?.end_date).remain > 0) || []).reduce((sum, item) => sum + (+item.mining_speed_tbtc * (100 - +item.owner_percentage) / 100), 0)
})

const setNav = (nav) => {
  tabs.setTab(nav)
  tabs.setBackground('#000000')
  document.body.style.background = tabs.background
  tg?.setHeaderColor(tabs.background)
}

const startMine = async () => {
  await app.initUser()
  if (!ton_address.value) {
    showModal('warning', t('notification.st_attention'), t('notification.connect_for_mine'))
    return
  }
  if (app.isMining == true) {
    try {
      const res = await host.post('stop-mining/')
      if (res.status == 200) {
        app?.setMining(false)
        stopAndResetTimer()
      } else {
        showModal('error', t('notification.st_error'), res.data.error)
      }
      return
    } catch (e) {
      showModal('error', t('notification.st_error'), e.response.data.error)
      return
    }
  }
  // if (app.user?.kw_wallet < 500) {
  //   modalStatus.value = "error"
  //   modalTitle.value = "Ошибка"
  //   modalBody.value = "У вас недостаточно kW"
  //   openModal.value = true
  //   return
  // }
  if (app.isMining == false) {
    try {
      const res = await host.post('start-mining/')
      if (res.status == 200) {
        app.setMining(true)
        await app.initUser()
        startTimer()
      } else {
        showModal('error', t('notification.st_error'), res.data.error)
      }
      return
    } catch (e) {
      showModal(
        'error',
        t('notification.st_error'),
        e.response.data.error == 'No NFT'
          ? t('notification.no_asics')
          : t('notification.no_energy_for_mining', { value: booostedFarmConsumtion.value }),
      )
      return
    }
  }
}

function generateMathExample() {
  let result = null, num1 = null, num2 = null
  const operations = ['+', '-']
  const operator = operations[Math.floor(Math.random() * operations.length)]

  while (!result) {
    num1 = Math.floor(Math.random() * 100) + 1
    num2 = Math.floor(Math.random() * 100) + 1
    switch (operator) {
      case '+':
        result = num1 + num2;
        break;
      case '-':
        result = num1 - num2;
        break;
    }
  }

  // Генеруємо варіанти відповідей
  const answers = [result] // Додаємо правильну відповідь
  while (answers.length < 4) {
    const deviation = Math.floor(Math.random() * 41) - 20
    const wrongAnswer = result + deviation
    if (
      !answers.includes(wrongAnswer) &&
      wrongAnswer !== 0 &&
      wrongAnswer !== result &&
      (operator === '+' ? wrongAnswer >= 0 : true)
    ) {
      answers.push(wrongAnswer)
    }
  }

  // Перемішуємо масив відповідей
  for (let i = answers.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [answers[i], answers[j]] = [answers[j], answers[i]];
  }

  return {
    firstNumber: num1,
    operator: operator,
    secondNumber: num2,
    result: result,
    answers: answers,
  }
}

const reconnectMining = async () => {
  reconnectExample.value = generateMathExample()
  openReconnectModal.value = true
}

const copyInvite = () => {
  const link = `https://t.me/tBTCminer_bot?startapp=ref_id${user?.id}`
  showModal('success', t('notification.st_success'), t('notification.invite_copied'))
  return navigator.clipboard.writeText(link)
}

const copyAddress = async (address) => {
  await navigator.clipboard.writeText(address)
  showModal('success', t('notification.st_success'), t('notification.address_copied'))
}

let isPaused = ref(false)
let timeoutId = null

onMounted(() => {
  asicsIsOpen.setBackground('#0B150F')
  document.body.style.background = asicsIsOpen.background
  tg?.setHeaderColor(asicsIsOpen.background)
  app.setPauseUpdate(true)
  startInfoUpdate()
  if (app.isMining) {
    startTimer()
  }

  // Initialize sale timers
  updateSaleTimer()
  const saleTimerInterval = setInterval(updateSaleTimer, 1000)

  updateAsicsSaleTimer()
  const asicsSaleTimerInterval = setInterval(updateAsicsSaleTimer, 1000)

  onUnmounted(() => {
    if (saleTimerInterval) {
      clearInterval(saleTimerInterval)
    }
    if (asicsSaleTimerInterval) {
      clearInterval(asicsSaleTimerInterval)
    }
  })
})

async function startInfoUpdate() {
  if (isProcessing.value || tabs.openDashboard) {
    isPaused.value = true
    return
  }
  try {
    await app.initUser()
    if (connectedAddressString) {
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
          }
        })
        .catch((err) => {
          console.log(err)
          nfts1 = []
        })
        .finally(() => {
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
          }
        })
        .catch((err) => {
          console.log(err)
          nfts2 = []
        })
        .finally(() => {
          controller = null
        })
      app.setNfts(nfts1.concat(nfts2))
      controller = new AbortController()
      await tonapi.get(`accounts/${connectedAddressString.value}`, { signal: controller.signal }).then((res) => {
        if (res.status == 200) {
          app.setTonBalance(res?.data?.balance)
        }
      }).finally(() => { controller = null })
      controller = new AbortController()
      await tonapi.get(`accounts/${connectedAddressString.value}/jettons`, { signal: controller.signal }).then((res) => {
        if (res.status == 200) {
          app.setJettons(res?.data?.balances)
        }
      }).finally(() => { controller = null })
    } else {
      app.setNfts([])
    }
    if (!Object.keys(app?.availableNftRentals).length) {
      controller = new AbortController()
      await host.get("available-nft-rentals/", { signal: controller.signal }).then((res) => {
        if (res.status == 200) {
          app.setAvailableRental(res.data)
        }
      }).finally(() => {
        controller = null
      })
    }
    if (!app?.rentedNfts.length) {
      controller = new AbortController()
      await host.get("user-rented-nfts/", { signal: controller.signal }).then((res) => {
        if (res.status == 200) {
          app.setRentedNft(res.data)
        }
      }).finally(() => {
        controller = null
      })
    }
    if (!app?.rentOutNfts.length) {
      controller = new AbortController()
      await host.get("user-lent-nfts/", { signal: controller.signal }).then((res) => {
        if (res.status == 200) {
          app.setRentOutNfts(res.data)
        }
      }).finally(() => {
        controller = null
      })
    }
    updateAsicNfts()
  } catch (err) {
    console.log(err)
  } finally {
    controller = null
    timeoutId = setTimeout(() => startInfoUpdate(), 3000) //set timer
  }
}

const openNftSpeedUpInfo = ref(false)
const openNftSpeedUp = ref(false)
const speedUpAddress = ref(null)

const activeShopTab = ref('gems')

const toggleShopTab = () => {
  activeShopTab.value = activeShopTab.value === 'asics' ? 'gems' : 'asics'
}

// Sale timer logic for GEMS
const showSaleTimer = ref(true)
const saleTimeRemaining = ref({
  days: 0,
  hours: 0,
  minutes: 0,
  seconds: 0
})

// Sale timer logic for ASICs
const showAsicsSaleTimer = ref(true)
const asicsSaleTimeRemaining = ref({
  days: 0,
  hours: 0,
  minutes: 0,
  seconds: 0
})

// Function to get correct plural form for Russian/Ukrainian
const getPluralForm = (count, forms) => {
  const n = Math.abs(count) % 100
  const n1 = n % 10
  if (n > 10 && n < 20) return forms[2]
  if (n1 > 1 && n1 < 5) return forms[1]
  if (n1 === 1) return forms[0]
  return forms[2]
}

const getTimeUnitText = (count, type) => {
  if (locale.value === 'ru') {
    const forms = {
      days: ['день', 'дня', 'дней'],
      hours: ['час', 'часа', 'часов'],
      minutes: ['минута', 'минуты', 'минут'],
      seconds: ['секунда', 'секунды', 'секунд']
    }
    return getPluralForm(count, forms[type])
  } else if (locale.value === 'uk') {
    const forms = {
      days: ['день', 'дні', 'днів'],
      hours: ['година', 'години', 'годин'],
      minutes: ['хвилина', 'хвилини', 'хвилин'],
      seconds: ['секунда', 'секунди', 'секунд']
    }
    return getPluralForm(count, forms[type])
  } else {
    // English
    return count === 1 ? type.slice(0, -1) : type
  }
}

const updateSaleTimer = () => {
  const now = new Date()
  const endDate = new Date(gemsSaleEndDate)
  const diffMs = endDate - now

  if (diffMs <= 0) {
    showSaleTimer.value = false
    return
  }

  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))
  const seconds = Math.floor((diffMs % (1000 * 60)) / 1000)

  saleTimeRemaining.value = {
    days: days.toString().padStart(2, '0'),
    hours: hours.toString().padStart(2, '0'),
    minutes: minutes.toString().padStart(2, '0'),
    seconds: seconds.toString().padStart(2, '0')
  }
}

const updateAsicsSaleTimer = () => {
  const now = new Date()
  const endDate = new Date(asicsSaleEndDate)
  const diffMs = endDate - now

  if (diffMs <= 0) {
    showAsicsSaleTimer.value = false
    return
  }

  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))
  const seconds = Math.floor((diffMs % (1000 * 60)) / 1000)

  asicsSaleTimeRemaining.value = {
    days: days.toString().padStart(2, '0'),
    hours: hours.toString().padStart(2, '0'),
    minutes: minutes.toString().padStart(2, '0'),
    seconds: seconds.toString().padStart(2, '0')
  }
}

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

const getStarterPackPrice = () => {
  const starterPack = gemsSheet.find(gem => gem.type === 'Starter Pack')
  if (!starterPack) return 99

  if (gemsSaleActive && starterPack.enableSale !== false) {
    const discountedPrice = getGemPrice(starterPack)
    // Округляем до десятых (1 знак после запятой)
    return Math.round(discountedPrice * 10) / 10
  }
  return starterPack.price
}


const buyCurrentGem = () => {
  if (currentGemItem.value) {
    buyGem(currentGemItem.value)
  }
}

const buyDaoOwner = () => {
  // Находим DAO Owner в списке GEMS
  const daoOwner = gemsSheet.find(gem => gem.type === 'DAO Owner')
  if (daoOwner) {
    buyGem(daoOwner)
  }
}

const buyStarterPack = () => {
  // Находим стартер пакет в списке GEMS
  const starterPack = gemsSheet.find(gem => gem.type === 'Starter Pack')
  if (starterPack) {
    buyGem(starterPack)
  }
  openStarterPackInfo.value = false
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


watch(
  [isProcessing, () => tabs.openDashboard],
  ([newIsProcessing, newDashboard]) => {
    if (
      (newIsProcessing == false && isPaused.value == true) ||
      (newDashboard === false && isPaused.value === true)) {
      isPaused.value = false
      startInfoUpdate()
    }
  },
  { immediate: true },
)

onUnmounted(() => {
  stopAndResetTimer()
  app.setPauseUpdate(false)
  if (controller) {
    controller.abort()
  }
  if (timeoutId) {
    clearTimeout(timeoutId) // Clear the setTimeout
    timeoutId = null
  }
})
</script>

<template>
  <SpeedUpModal v-if="openNftSpeedUp" :address="speedUpAddress" @close="openNftSpeedUp = false" />
  <RedirectModal v-if="openRedirectModal" :link="redirectLink" :itemName="redirectItemName" :itemClass="redirectItemClass" @close="openRedirectModal = false" />
  <ReconnectModal v-if="openReconnectModal" :example="reconnectExample" @close="checkReconnect" />
  <SpecialPriceModal v-if="openSpecialModal" :saleAsic="currBuyAsic" @close="specialModalResponse" />
  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
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
          • {{ t('gems.hydroelectric_info_2') }}
        </div>
      </div>
    </template>
  </InfoModal>
  <!-- <InfoModal v-if="openMiningStopped" @close="openMiningStopped = false">
    <template #modal-body>
      {{ t('modals.mining_stopped.message') }}
    </template>
</InfoModal> -->
  <WithdrawModal v-if="openClaim" @close="getClaimResponse" claim />
  <Transition name="fade">
    <div v-if="asicsIsOpen.openAsicShop || asicsIsOpen.openEquip" class="overlay"
      @click="(openAsics(false), openEquip(false))"></div>
  </Transition>
  <Transition name="slide-up">
    <div v-if="asicsIsOpen.openAsicShop" class="asics-shop">
      <div class="top-panel">
        <div class="ton">
          <img src="@/assets/TON.png" width="22px" height="22px" />
          <span class="amount">{{ (app?.tonBalance / 10 ** 9).toFixed(3) || 0 }}</span>
        </div>

        <!-- Shop Tab Switcher -->
        <div class="shop-tabs">
          <button
            class="tab-btn"
            :class="{ active: activeShopTab === 'gems' }"
            @click="toggleShopTab"
          >
            {{ t('asic_shop.gems') }}
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeShopTab === 'asics' }"
            @click="toggleShopTab"
          >
            {{ t('asic_shop.asics_short') }}
          </button>
        </div>

        <button class="close" @click="openAsics(false)">
          <Exit :width="16" style="color: #fff" />
        </button>
      </div>

      <!-- Sale Timer for GEMS -->
      <div v-if="activeShopTab === 'gems' && gemsSaleActive && showSaleTimer" class="sale-timer">
        <div class="sale-timer-content">
          <span class="sale-timer-text">{{ t('asic_shop.sale_ends_in') }}</span>
          <div class="sale-timer-countdown">
            <div class="timer-unit">
              <span class="timer-value">{{ saleTimeRemaining.days }}</span>
              <span class="timer-label">{{ getTimeUnitText(parseInt(saleTimeRemaining.days), 'days') }}</span>
            </div>
            <span class="timer-separator">:</span>
            <div class="timer-unit">
              <span class="timer-value">{{ saleTimeRemaining.hours }}</span>
              <span class="timer-label">{{ getTimeUnitText(parseInt(saleTimeRemaining.hours), 'hours') }}</span>
            </div>
            <span class="timer-separator">:</span>
            <div class="timer-unit">
              <span class="timer-value">{{ saleTimeRemaining.minutes }}</span>
              <span class="timer-label">{{ getTimeUnitText(parseInt(saleTimeRemaining.minutes), 'minutes') }}</span>
            </div>
            <span class="timer-separator">:</span>
            <div class="timer-unit">
              <span class="timer-value">{{ saleTimeRemaining.seconds }}</span>
              <span class="timer-label">{{ getTimeUnitText(parseInt(saleTimeRemaining.seconds), 'seconds') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Sale Timer for ASICs -->
      <div v-if="activeShopTab === 'asics' && asicsSaleActive && showAsicsSaleTimer" class="sale-timer">
        <div class="sale-timer-content">
          <span class="sale-timer-text">{{ t('asic_shop.sale_ends_in') }}</span>
          <div class="sale-timer-countdown">
            <div class="timer-unit">
              <span class="timer-value">{{ asicsSaleTimeRemaining.days }}</span>
              <span class="timer-label">{{ getTimeUnitText(parseInt(asicsSaleTimeRemaining.days), 'days') }}</span>
            </div>
            <span class="timer-separator">:</span>
            <div class="timer-unit">
              <span class="timer-value">{{ asicsSaleTimeRemaining.hours }}</span>
              <span class="timer-label">{{ getTimeUnitText(parseInt(asicsSaleTimeRemaining.hours), 'hours') }}</span>
            </div>
            <span class="timer-separator">:</span>
            <div class="timer-unit">
              <span class="timer-value">{{ asicsSaleTimeRemaining.minutes }}</span>
              <span class="timer-label">{{ getTimeUnitText(parseInt(asicsSaleTimeRemaining.minutes), 'minutes') }}</span>
            </div>
            <span class="timer-separator">:</span>
            <div class="timer-unit">
              <span class="timer-value">{{ asicsSaleTimeRemaining.seconds }}</span>
              <span class="timer-label">{{ getTimeUnitText(parseInt(asicsSaleTimeRemaining.seconds), 'seconds') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Маркетинговая плашка с акцией -->
      <Transition name="promo-banner">
        <div v-if="activeShopTab === 'asics' && asicsSaleActive && !promoBannerClosed" class="promo-banner">
          <div class="promo-banner-shine-wrapper">
            <div class="promo-banner-shine"></div>
          </div>
          <button class="promo-banner-close" @click="promoBannerClosed = true">
            <Exit :width="14" style="color: rgba(255, 255, 255, 0.8)" />
          </button>
          <div class="promo-banner-content">
            <div class="promo-banner-text">
              <div class="promo-banner-title">
                <span class="promo-banner-icon-inline">🔥</span>
                <span class="promo-banner-title-text">{{ t('asic_shop.promo_banner_title') }}</span>
                <span class="promo-banner-icon-inline">🔥</span>
              </div>
              <div class="promo-banner-description">{{ t('asic_shop.promo_banner_text') }}</div>
            </div>
          </div>
        </div>
      </Transition>

      <!-- ASICs List -->
      <div v-if="activeShopTab === 'asics'" class="asics-list" ref="asicsList">
        <div class="item" v-for="(asicItem, index) in asicsSheet.filter(el => el.shop)" :key="asicItem">
          <div class="picture">
            <!-- <Asics :width="62" :height="62" /> -->
            <img :src="imagePathAsics(asicItem?.name)?.value" :style="asicItem?.rarity == 'Epic' || asicItem?.rarity == 'Legendary'
              ? 'min-width: 125px; margin: -30px 0 -10px'
              : asicItem?.rarity == 'Mythic'
                ? 'min-width: 140px; margin: -30px 0 -10px'
                : 'min-width: 115px'
              " />
            <!-- <span class="tag"
              :style="asicItem.rarity == 'Common' ? 'background-color: #323232' : asicItem.rarity == 'Rare' ? 'background-color: #009600;' : asicItem.rarity == 'Epic' ? 'background-color: #1d4ed8;' : asicItem.rarity == 'Legendary' ? 'background-color: #d97706;' : 'background-color: #6d28d9;'">{{
                asicItem.rarity }}</span> -->
          </div>
          <div class="info">
            <span v-if="asicItem?.name == 'ASIC S7+'" class="label">{{ t('asic_shop.recommend') }}</span>
            <span class="name">{{ asicItem?.name }}</span>
            <span>{{ width > 345 ? t('asic_shop.speed') : t('asic_shop.speed').slice(0, 1) +
              t('asic_shop.speed').slice(-2, -1) }}
              {{
                asicItem?.hash_rate >= 1000
                  ? asicItem?.hash_rate / 1000 + ` ${t('common.per_s', { value: 'Gh' })}`
                  : asicItem?.hash_rate + ` ${t('common.per_s', { value: 'Mh' })}`
              }}</span>
            <span>{{ width > 345 ? t('asic_shop.mining') : t('asic_shop.mining').slice(0, 1) +
              t('asic_shop.mining').slice(-2, -1) }} {{ asicItem?.speed }} {{ t('common.per_d', { value: 'fBTC' })
              }}</span>
            <span>{{ width > 345 ? t('asic_shop.consumption') : t('asic_shop.consumption').slice(0, 1) +
              t('asic_shop.consumption').slice(-2, -1) }} {{ asicItem?.consumption }} {{ t('common.per_h', {
                value:
                  'kW'
              }) }}</span>
          </div>
          <button @click="buyAsics(index, isAsicInSale(asicItem) ? getAsicPrice(asicItem) : asicItem?.price, asicItem?.link, isAsicInSale(asicItem) || asicItem?.sale, asicItem?.shop)"
            :disabled="asicItem?.sold_out">
            <span>{{ asicItem?.sold_out ? t('common.sold_out') : t('asic_shop.buy_asic') }}</span>
            <span class="price" :class="{ saleprice: isAsicInSale(asicItem) || asicItem?.new_price }">
              <img src="@/assets/TON.png" width="14px" height="14px" />
              {{ asicItem?.price }}
            </span>
            <div v-if="isAsicInSale(asicItem) || asicItem?.perc" class="sale-perc">-{{ isAsicInSale(asicItem) ? asicsSalePercent : asicItem?.perc }}%</div>
            <div v-if="isAsicInSale(asicItem) || asicItem?.new_price" class="sale-newprice">
              <img src="@/assets/TON.png" width="12px" height="12px" />
              {{ isAsicInSale(asicItem) ? getAsicPrice(asicItem) : asicItem?.new_price }}
            </div>
          </button>
          <span v-if="isAsicInSale(asicItem) || (!isAsicInSale(asicItem) && !asicItem?.sale)" class="tag" :style="asicItem?.rarity == 'Common'
            ? 'background-color: #5D625E'
            : asicItem?.rarity == 'Rare'
              ? 'background-color: #009600;'
              : asicItem?.rarity == 'Epic'
                ? 'background-color: #0918E9;'
                : asicItem?.rarity == 'Legendary'
                  ? 'background-color: #E98509;'
                  : 'background-color: #6B25A1;'
            ">{{ t(`asic_shop.${asicItem?.rarity.toLowerCase()}`) }}</span>
          <span v-if="!isAsicInSale(asicItem) && asicItem?.sale" class="runline" :style="asicItem?.rarity == 'Common'
            ? 'background-color: #5D625E'
            : asicItem?.rarity == 'Rare'
              ? 'background-color: #009600;'
              : asicItem?.rarity == 'Epic'
                ? 'background-color: #0918E9;'
                : asicItem?.rarity == 'Legendary'
                  ? 'background-color: #E98509;'
                  : 'background-color: #6B25A1;'
            ">
            <div class="backplane">
              <div class="asic-type" :style="asicItem?.rarity == 'Common'
                ? 'background-color: #5D625E'
                : asicItem?.rarity == 'Rare'
                  ? 'background-color: #009600;'
                  : asicItem?.rarity == 'Epic'
                    ? 'background-color: #0918E9;'
                    : asicItem?.rarity == 'Legendary'
                      ? 'background-color: #E98509;'
                      : 'background-color: #6B25A1;'
                ">
                {{ t(`asic_shop.${asicItem?.rarity.toLowerCase()}`) }}
              </div>
              <p v-if="locale == 'en'" class="textline">
                - Best choise now - Sale - Best choise now - Sale - Best choise now - Sale - Best
                choise now - Sale - Best choise now - Sale - Best choise now - Sale - Best choise
                now - Sale - Best choise now - Sale
              </p>
              <p v-if="locale == 'ru'" class="textline">
                - Лучший выбор сейчас - Распродажа - Лучший выбор сейчас - Распродажа - Лучший выбор сейчас - Распродажа
                - Лучший
                выбор сейчас - Распродажа - Лучший выбор сейчас - Распродажа - Лучший выбор сейчас - Распродажа - Лучший
                выбор
                сейчас - Распродажа - Лучший выбор сейчас - Распродажа
              </p>
              <p v-if="locale == 'uk'" class="textline">
                - Найкращий вибір зараз - Розпродаж - Найкращий вибір зараз - Розпродаж - Найкращий вибір зараз -
                Розпродаж - Найкращий вибір зараз - Розпродаж - Найкращий вибір зараз - Розпродаж - Найкращий вибір
                зараз - Розпродаж - Найкращий вибір зараз - Розпродаж - Найкращий вибір зараз - Розпродаж - Найкращий
                вибір зараз - Розпродаж
              </p>
            </div>
          </span>
        </div>
      </div>

      <!-- Маркетинговая плашка с акцией для GEMS -->
      <Transition name="promo-banner">
        <div v-if="activeShopTab === 'gems' && gemsSaleActive && !gemsPromoBannerClosed" class="promo-banner gems-promo-banner">
          <div class="promo-banner-shine-wrapper">
            <div class="promo-banner-shine"></div>
            <!-- Новогодние снежинки -->
            <div class="snowflakes">
              <div class="snowflake">❄</div>
              <div class="snowflake">❄</div>
              <div class="snowflake">❄</div>
              <div class="snowflake">❄</div>
              <div class="snowflake">❄</div>
              <div class="snowflake">❄</div>
            </div>
          </div>
          <button class="promo-banner-close" @click="gemsPromoBannerClosed = true">
            <Exit :width="14" style="color: rgba(255, 255, 255, 0.8)" />
          </button>
          <!-- Елочки по бокам -->
          <span class="promo-banner-tree-left">🎄</span>
          <span class="promo-banner-tree-right">🎄</span>
          <div class="promo-banner-content">
            <div class="promo-banner-text">
              <div class="promo-banner-title">
                <span class="promo-banner-icon-inline">🎄</span>
                <span class="promo-banner-title-text">{{ t('gems.promo_banner_title') }}</span>
                <span class="promo-banner-icon-inline">❄️</span>
              </div>
              <div class="promo-banner-description">{{ t('gems.promo_banner_text') }}</div>
            </div>
          </div>
        </div>
      </Transition>

      <!-- GEMS List -->
      <div v-if="activeShopTab === 'gems'" class="gems-list">
        <div class="gem-item"
          :class="{
            'has-gold-stroke': gemItem?.hasGoldStroke,
            'has-purple-stroke': gemItem?.hasPurpleStroke,
            'has-blue-stroke': gemItem?.hasBlueStroke
          }"
          v-for="gemItem in sortGemsBySale(gemsSheet.filter(el => el.shop))"
          :key="gemItem">
          <div class="gem-info-icon-top" @click="handleGemInfoClick(gemItem)">i</div>
          <div class="gem-picture">
            <img v-if="gemItem?.imagePath" :src="imagePathGems(gemItem.imagePath)?.value" class="gem-image"
              :class="{ 'hide-under-tag': gemItem?.buttonColor !== 'gold' && gemItem?.buttonColor !== 'purple' && gemItem?.buttonColor !== 'blue' && gemItem?.type !== 'Cryochamber' }"
              alt="NFT" />
            <div v-else class="gem-icon">💎</div>
          </div>
          <div class="gem-info">
            <span class="gem-type">{{ gemItem.type === 'Hydroelectric Power Plant' ? 'Hydroelectric\nPower Plant' : gemItem.type }}</span>
            <span class="gem-description" v-for="(benefit, idx) in gemItem.benefits" :key="idx">
              {{ t(`gems.${benefit}`) }}
            </span>
          </div>
          <button class="gem-buy-btn"
            :class="{
              'btn-gold': gemItem?.buttonColor === 'gold',
              'btn-purple': gemItem?.buttonColor === 'purple',
              'btn-blue': gemItem?.buttonColor === 'blue'
            }"
            :disabled="!gemItem?.shop"
            @click="buyGem(gemItem)">
            <span>{{ gemItem.name }}</span>
            <span v-if="gemItem?.type !== 'Orbital Power Plant'" class="gem-price" :class="{ 'gem-saleprice': gemsSaleActive && gemItem?.enableSale !== false }">
              <img src="@/assets/TON.png" width="14px" height="14px" />
              {{ gemItem.price }}
            </span>
            <span v-else class="gem-price">{{ gemItem.price }}</span>
            <div v-if="gemsSaleActive && gemItem?.enableSale !== false" class="gem-sale-perc">-{{ gemItem.salePercent || gemsSalePercent }}%</div>
            <div v-if="gemsSaleActive && gemItem?.enableSale !== false" class="gem-sale-newprice">
              <img src="@/assets/TON.png" width="12px" height="12px" />
              {{ getGemPrice(gemItem) }}
            </div>
          </button>
          <span class="gem-tag"
            :style="gemItem?.buttonColor === 'gold'
              ? 'background: linear-gradient(270deg, #FEA400 0%, #FCD909 100%), #FFC300; color: #000000;'
              : gemItem?.buttonColor === 'purple'
                ? 'background: linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(152, 81, 236, 1) 50%, rgba(94, 124, 234, 1) 100%), #FFC300;'
                : gemItem?.buttonColor === 'blue'
                  ? 'background: linear-gradient(270deg, rgba(49, 207, 255, 1) 0%, rgba(31, 255, 255, 1) 100%), #31CFFF; color: #000000;'
                  : gemItem?.rarity == 'class_4'
                    ? 'background-color: #5D625E;'
                    : gemItem?.rarity == 'class_3'
                      ? 'background-color: #009600;'
                      : gemItem?.rarity == 'class_2'
                        ? 'background-color: #0918E9;'
                        : 'background-color: #6B25A1;'
              ">{{ t(`gems.${gemItem.rarity}`) }}</span>
        </div>
      </div>
    </div>
  </Transition>

  <Transition name="slide-up">
    <div v-if="asicsIsOpen.openEquip" class="equip-modal">
      <div class="top-panel">
        <div class="ton"></div>
        <h1>{{ t('miner.asic_equip') }}</h1>
        <button class="close" @click="openEquip(false)">
          <Exit :width="16" style="color: #fff" />
        </button>
      </div>
      <div class="asics-list">
        <div class="slot-item" :class="{ rented: item?.nft, connect: getTimedNftData(item) }"
          v-for="(item, idx) in cachedAsicNfts" :key="item">
          <div class="top-label" :class="{ rented: item?.nft, connect: getTimedNftData(item) }">
            {{ t('miner.slot') }} {{ idx + 1 }}</div>
          <div class="pic-wrapper" :class="{ connect: getTimedNftData(item) }">
            <img
              :src="imagePath((item?.metadata?.attributes?.some(attr => attr.value?.toString()?.trim() == 'SBT') && item?.metadata?.attributes?.some(attr => attr.value.includes('class'))) ?
                `${item?.metadata?.name}-${item?.metadata?.attributes.find(attr => attr.value.includes('class'))?.value?.split(' ')[0]}` :
                (item?.metadata?.attributes?.some(attr => attr.value?.toString()?.trim() !== 'SBT') && item?.metadata?.attributes?.some(attr => attr.value.includes('class'))) ?
                  `${item?.metadata?.name?.toUpperCase()}` :
                  `${item.nft ? getAsicData(item.nft, all_asics, asicsSheet, 'name') : getAsicData(item.address, all_asics, asicsSheet, 'name')}`).value"
              class="pic" />
            <InfoIcon v-if="getTimedNftData(item) && new Date(getTimedNftData(item).block_until) > new Date()"
              class="info-label" :class="{ checked: openNftSpeedUpInfo }"
              @click="openNftSpeedUpInfo = !openNftSpeedUpInfo" />
            <img class="visible-eye" :style="hideSlotInfo[idx] ? 'opacity: 1' : 'opacity: 0.5'" src="@/assets/eye.png"
              width="24px" height="24px" @click="hideSlotInfo[idx] = hideSlotInfo[idx] ? false : true" />
            <div v-if="item?.nft && !hideSlotInfo[idx]" class="rent-time">
              <p>{{ t('miner.rent_end') }}</p>
              <h1>{{ getTimeRemaining(item?.end_date).time }}</h1>
            </div>
            <div v-if="getTimedNftData(item)" class="locked-nft">
              <h1>{{getTimeRemaining(app.timed_nfts?.find(el => el.nft_address == (item.address ??
                item.nft))?.block_until).speedup}}</h1>
              <div class="nft-name" v-if="openNftSpeedUpInfo">{{item?.metadata?.name || all_asics?.find(el => el.a ==
                item?.nft)?.n}}</div>
              <div class="speedup-btn" v-if="!openNftSpeedUpInfo" @click="speedUpNft(item)">
                {{ t('common.speedup') }}
              </div>
              <div class="lock-progress">
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: getTimedNftProgress(item) + '%' }">
                  </div>
                </div>
                <div class="progress-text">
                  {{ t('common.connect') }}
                  <span class="progress-percent" v-if="showProgressPercent">
                    ({{ Math.round(getTimedNftProgress(item)) }}%)
                  </span>
                </div>
              </div>
            </div>
            <div class="gradient-overlay"
              :class="{ rented: item?.nft && !hideSlotInfo[idx], connect: getTimedNftData(item) }">
            </div>
            <div class="second-gradient-overlay" v-if="getTimedNftData(item)"></div>
          </div>
          <div class="bottom-panel" v-if="!getTimedNftData(item)">
            <span>{{item?.metadata?.name || all_asics?.find(el => el.a == item?.nft)?.n
            }}</span>
            <div class="chips"></div>
          </div>
        </div>
        <div class="slot-item" v-for="idx in cachedAsicNfts?.length % 2 || cachedAsicNfts?.length == 0 ? 14 : 15"
          :key="idx">
          <div class="top-label">{{ t('miner.slot') }} {{ cachedAsicNfts?.length + idx }}</div>
          <img src="../assets/asics/ASIC S9+.webp" class="picture" style="opacity: 0.25; scale: 0.6" />
          <button class="buy-button" @click="
            () => {
              asicsIsOpen.setOpenEquip(false)
              asicsIsOpen.setOpenAsicsShop(true)
            }
          ">
            {{ t('miner.buy_asic') }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
  <div class="screen-box">
    <div class="currencies">
      <div class="ton currency">
        <!-- <Ton :width="22" :height="22" /> -->
        <img src="@/assets/TON.png" width="22px" height="22px" />
        <span>{{ (app?.tonBalance / 10 ** 9).toFixed(3) || 0 }}</span>
      </div>
      <RouterLink to="/wallet" @click="setNav('wallet')">
        <div class="coin currency">
          <!-- <TonBitcoin :width="22" :height="22" /> -->
          <img src="@/assets/fBTC.webp" width="22px" height="22px" />
          <span>{{ +app?.user?.tbtc_wallet?.toFixed(2) || 0 }}</span>
        </div>
      </RouterLink>
      <RouterLink to="/wallet" @click="setNav('wallet')">
        <div class="energy currency" @click="tabs.setTab('wallet')">
          <!-- <Energy :width="22" :height="22" /> -->
          <img src="@/assets/kW_token.png" width="22px" height="22px" />
          <span>{{ +app?.user?.kw_wallet?.toFixed(2) || 0 }}</span>
        </div>
      </RouterLink>
    </div>
    <div class="mining-panel">
      <div class="miner-block" :style="{
        background: app.isMining
          ? 'radial-gradient(ellipse at right top, #FF3B59, #FF3B5950 35%, transparent), #08150a50'
          : 'radial-gradient(ellipse at right top, #31ff8070, #31ff8030 35%, transparent), #08150a50',
        border: boostActive(0) ? 'none' : '1px solid #ffffff25',
      }">
        <div v-if="boostActive(0)" class="bg"></div>
        <img src="@/assets/mining-panel_new.webp" width="95px" height="95px"
          style="margin: -27px 0 -15px 0; z-index: 2" />
        <div class="grouping">
          <button class="ctrl-mining-btn" @click="startMine" :style="{
            background: app.isMining
              ? 'radial-gradient(ellipse 80% 30% at bottom center, #ffffff50, transparent), linear-gradient(to bottom, #FF3B59, #90192B)'
              : 'radial-gradient(ellipse 80% 30% at bottom center, #ffffff50, transparent), linear-gradient(to bottom, #fcd909, #fea400)',
            color: app.isMining ? '#fff' : '#000',
            boxShadow: app.isMining ? 'inset 0px 0px 0px 1px #ffffff70' : 'none',
          }">
            {{ app.isMining ? t('miner.stop_mine_btn') : t('miner.start_mine_btn') }}
          </button>
          <span>{{ t('miner.mining_time') }} <span class="mining-time">{{ formattedTime }}</span></span>
        </div>
      </div>
      <div class="equip-block">
        <div class="equip-btn" @click="openEquip(true)">
          <EquipButton :width="26" :height="25" style="color: #000" />
        </div>
        <span>{{ t('miner.equip_btn') }}</span>
      </div>
    </div>
    <div class="add-grid">
      <div class="item col-span-2 overflow-visible">
        <div v-if="boostActive(2)" class="bg"></div>
        <div class="item-grouping">
          <img src="@/assets/accum_new.webp" width="70px" style="margin: -3vw 0 0 -2vw" />
          <div class="grid-item-text">
            <span class="data">{{ +(+app?.user?.kw_wallet)?.toFixed(2) || 0 }} kW</span>
            <span class="desc">{{ t('miner.acc_energy') }}</span>
          </div>
        </div>
        <RouterLink to="/wallet" style="z-index: 5;" @click="setNav('wallet')">
          <button>{{ width > 350 ? t('miner.acc_energy_btn') : t('miner.acc_energy_btn').split(" ")[0] }}</button>
        </RouterLink>
      </div>
      <div class="item">
        <div class="item-grouping">
          <img src="@/assets/asic_new.webp" width="46px" />
          <div class="grid-item-text">
            <span class="data">{{ cachedAsicNfts?.length || 0 }}</span>
            <span class="desc">{{ t('miner.asics') }}</span>
          </div>
        </div>
        <button @click="openAsics(true)" class="plus">
          <Cart :width="15" :height="17" style="color: #000" />
          <!-- {{ t('miner.asics_btn') }} -->
        </button>
      </div>
      <div class="item">
        <div class="item-grouping">
          <div class="grid-item-text">
            <span class="data"> <img src="@/assets/fBTC.webp" width="10px" height="10px" />{{ minedTokens }}</span>
            <span class="desc">{{ t('miner.mined') }}</span>
          </div>
        </div>
        <button @click="claim">{{ t('miner.mined_btn') }}</button>
      </div>
      <div class="item" :class="{ 'timeout-pulse': app?.user?.mining_was_stopped }">
        <div v-if="app?.user?.mining_was_stopped"
          class="item-grouping !justify-between !w-full !absolute !z-50 !gap-0 px-2">
          <div class="grid-item-text">
            <span class="data">{{ t('miner.error') }}</span>
            <span class="desc !text-[8px]">{{ t('miner.error_text') }}</span>
          </div>
          <button class="timeout-btn" @click="reconnectMining" :disabled="app?.user?.stop_mining_activate_last !== null &&
            new Date() - new Date(app?.user?.stop_mining_activate_last) < 10 * 60 * 1000
            ">
            {{
              app?.user?.stop_mining_activate_last == null ||
                (app?.user?.stop_mining_activate_last !== null &&
                  new Date() - new Date(app?.user?.stop_mining_activate_last) >= 10 * 60 * 1000)
                ? t('miner.reconnect')
                : reconnectTime
            }}
          </button>
        </div>
        <div class="item-grouping" :style="app?.user?.mining_was_stopped ? 'filter: blur(2px) brightness(0.6)' : ''">
          <img src="@/assets/hash_rate_new.webp" style="width: 46px; height: 46px" />
          <div class="grid-item-text">
            <span class="data">{{+(app?.user?.mining_farm_speed + +(_.sum([...(app?.rentedNfts?.map(el => +el?.hashrate)
              || [])]) / 1000).toFixed(1) - +(_.sum([...(app?.rentOutNfts?.filter(el => el.end_date)?.map(el =>
                +el?.hashrate) || [])]) / 1000).toFixed(1) || 0).toFixed(1)
            }} {{ t('common.per_s', { value: 'Gh' }) }}</span>
            <span class="desc">{{ t('miner.mining_power') }}</span>
          </div>
        </div>
      </div>
      <div class="item">
        <div v-if="boostActive(1)" class="bg"></div>
        <div class="item-grouping">
          <img src="@/assets/power_consumption_new.webp" style="width: 46px; height: 46px" />
          <div class="grid-item-text">
            <span class="data">{{ booostedFarmConsumtion || 0 }} {{ t('common.per_h', { value: 'kW' }) }}</span>
            <span class="desc">{{ t('miner.power_cons') }}</span>
          </div>
        </div>
      </div>
      <div class="item">
        <div class="item-grouping">
          <img src="@/assets/mining_speed_new.webp" style="width: 46px; height: 46px" />
          <div class="grid-item-text">
            <span class="data">{{ +(+app.user?.total_mining_speed - +app.user?.rent_total_mining_speed_minus +
              rentedPlusSpeed)?.toFixed(2) || 0 }} {{ t('common.per_h', { value: 'fBTC' }) }}</span>
            <span class="desc">{{ t('miner.mining_speed') }}</span>
          </div>
        </div>
      </div>
      <div class="item">
        <div class="item-grouping">
          <img src="@/assets/energy_left_new.webp" style="width: 46px; height: 46px" />
          <div class="grid-item-text">
            <!-- <span class="data">{{ +(+app?.user?.farm_runtime)?.toFixed(2) || 0 }} Hours</span> -->
            <span class="data">{{ t('common.hours', {
              n: booostedFarmConsumtion > 0 ? +(+app?.user?.kw_wallet /
                booostedFarmConsumtion)?.toFixed(2) : 0 || 0
            }) }}</span>
            <span class="desc">{{ t('miner.energy_left') }}</span>
          </div>
        </div>
      </div>
      <div class="item" @click="nextBoost">
        <div v-if="currBoost.active" class="bg"></div>
        <div class="item-grouping">
          <div class="-mr-1 p-0 flex flex-col items-center justify-center gap-1">
            <Disk :style="currBoost.name == 'manager' && currBoost.active
              ? 'color: #46FF8D'
              : boostActive(0)
                ? 'color: #46FF8D50'
                : 'color: #ffffff50;'
              " />
            <Disk :style="currBoost.name == 'magnit' && currBoost.active
              ? 'color: #46FF8D'
              : boostActive(1)
                ? 'color: #46FF8D50'
                : 'color: #ffffff50;'
              " />
            <Disk :style="currBoost.name == 'powerbank' && currBoost.active
              ? 'color: #46FF8D'
              : boostActive(2)
                ? 'color: #46FF8D50'
                : 'color: #ffffff50;'
              " />
          </div>
          <!-- <img src="@/assets/boost_new.webp" class="-mr-1" style="width: 46px; height: 46px;" /> -->
          <img v-if="currBoost.name == 'manager'" src="@/assets/boost_am.webp" class="-mr-1"
            style="width: 46px; height: 46px" />
          <img v-else-if="currBoost.name == 'magnit'" src="@/assets/boost_magnit.webp" class="-mr-1"
            style="width: 46px; height: 46px" />
          <img v-else src="@/assets/boost_pb.webp" class="-mr-1" style="width: 46px; height: 46px" />
          <div class="grid-item-text">
            <span class="data">{{
              currBoost.name == 'manager'
                ? 'AM'
                : currBoost.name == 'magnit'
                  ? `${premiumActive ? 24 : app?.boosters?.find((el) => el.slug == 'magnit')?.n1 || 0}%`
                  : 'PB'
            }}
              {{ currBoost.forever ? t('miner.boost_forever') : t('miner.boost_text', { time: currBoost.time })
              }}</span>
            <span class="desc">
              <NFTBoost v-if="currBoost.forever" :width="12" :height="13" />
              {{ t('miner.boost') }} •
              <span :style="currBoost.active ? 'color: #46FF8D' : 'color: #FF4646'">{{
                currBoost.active ? t('miner.boost_active') : t('miner.boost_unactive')
              }}</span>
            </span>
          </div>
        </div>
      </div>
      <div class="item">
        <div class="item-grouping">
          <img src="@/assets/co-miners_new.webp" style="width: 46px; height: 46px" />
          <div class="grid-item-text">
            <span class="data">0</span>
            <span class="desc">{{ t('miner.co_miners') }}</span>
          </div>
        </div>
        <button class="plus" @click="copyInvite">+</button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: #00000070;
  backdrop-filter: blur(2px);
  z-index: 50;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.5s ease-in-out;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100vh);
}

.asics-shop {
  position: absolute;
  bottom: -50px;
  z-index: 100;
  width: 100%;
  height: 100%;
  display: flex;
  padding-bottom: 60px;
  flex-direction: column;
  align-items: center;
  border-radius: 1rem 1rem 0 0;
  background:
    url('@/assets/asics-shop-bg.webp') no-repeat top center,
    radial-gradient(ellipse 45% 50% at top center, #31ff8080, transparent),
    #08150a;
  // box-shadow: 0 -10px 40px 10px #31ff8080;

  .top-panel {
    display: flex;
    width: 90%;
    padding: 1rem 0 .5rem;
    align-items: center;
    justify-content: space-between;

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
      font-size: clamp(14px, 5.5dvw, 24px);
      text-wrap: nowrap;
    }

    .close {
      width: 20%;
      display: flex;
      align-items: center;
      justify-content: end;
    }
  }

  .sale-timer {
    display: flex;
    width: 90%;
    justify-content: center;
    margin: 0.5rem 0;

    .sale-timer-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      /* как карточки gems/asics */
      background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff20, transparent), rgba(0,0,0,0.6);
      border-radius: 15px;
      padding: 12px 20px;
      /* жёлтая обводка как -50% */
      position: relative;
      border: none;
      &::before {
        content: '';
        position: absolute;
        inset: 0;
        border-radius: 15px;
        padding: 1px;
        background: linear-gradient(180deg, #FEA400 0%, #FCD909 100%);
        -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
        -webkit-mask-composite: xor;
                mask-composite: exclude;
      }

      .sale-timer-text {
        color: #FFFFFF; /* белый заголовок */
        font-family: 'Inter' !important;
        font-weight: 600;
        font-size: 16px; /* как заголовки */
        margin-bottom: 8px;
        text-align: center;
      }

      .sale-timer-countdown {
        display: flex;
        align-items: center;
        gap: 8px;

        .timer-unit {
          display: flex;
          flex-direction: column;
          align-items: center;
          min-width: 50px;
          background: linear-gradient(180deg, #FCD909 0%, #FEA400 100%); /* жёлтый фрейм как -50% */
          border-radius: 10px;
          padding: 8px 6px;
          gap: 2px;

          .timer-value {
            color: #000000;
            font-family: 'Inter' !important;
            font-weight: 800;
            font-size: 20px;
            line-height: 1;
            text-align: center;
          }

          .timer-label {
            color: #000000;
            font-family: 'Inter' !important;
            font-weight: 600;
            font-size: 10px;
            text-align: center;
            line-height: 1;
          }
        }

        .timer-separator {
          color: #ffffff; /* белые разделители */
          font-family: 'Inter' !important;
          font-weight: 700;
          font-size: 18px;
          margin: 0 4px;
        }
      }
    }
  }

  .promo-banner {
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

    .promo-banner-shine-wrapper {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      border-radius: 1rem;
      z-index: 0;
      pointer-events: none;
    }

    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: linear-gradient(135deg,
        rgba(252, 217, 9, 0.2) 0%,
        rgba(254, 164, 0, 0.2) 50%,
        rgba(226, 249, 116, 0.15) 100%);
      border-radius: 1rem;
      opacity: 0;
      z-index: -1;
      animation: promoGlow 3s ease-in-out infinite;
      transition: opacity 0.3s ease;
    }

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

    @keyframes promoGlow {
      0%, 100% {
        opacity: 0;
      }
      50% {
        opacity: 0.4;
      }
    }

    .promo-banner-shine {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: linear-gradient(
        90deg,
        transparent 0%,
        transparent 30%,
        rgba(255, 255, 255, 0.25) 50%,
        transparent 70%,
        transparent 100%
      );
      animation: shine 4s ease-in-out infinite;
      pointer-events: none;
      transform: translateX(-100%);

      @keyframes shine {
        0% {
          transform: translateX(-100%) skewX(-15deg);
        }
        50% {
          transform: translateX(200%) skewX(-15deg);
        }
        100% {
          transform: translateX(200%) skewX(-15deg);
        }
      }
    }

    .promo-banner-close {
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

    .promo-banner-icon-inline {
      display: inline-block;
      font-size: 1.2rem;
      margin: 0;
      animation: iconBounce 2.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite,
                 iconGlow 2s ease-in-out infinite;
      vertical-align: middle;
      filter: drop-shadow(0 0 4px rgba(252, 217, 9, 0.6));
      flex-shrink: 0;

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

    .promo-banner-content {
      position: relative;
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
      z-index: 2;
      width: 100%;
      flex: 1;
      padding: 0 0.5rem;
      min-height: 100%;

      .promo-banner-text {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        flex: 1;
        min-width: 0;
        width: 100%;
        word-wrap: break-word;
        overflow-wrap: break-word;
        overflow: visible;

        .promo-banner-title {
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
          flex-wrap: nowrap;
          gap: 0.5rem;
        }

        .promo-banner-title-text {
          flex-shrink: 0;
        }

        .promo-banner-description {
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
          will-change: auto;
          backface-visibility: hidden;
          transform: translateZ(0);
        }
      }
    }

    // Новогодний баннер для GEMS (стилистика как у ASICs)
    &.gems-promo-banner {
      background: linear-gradient(135deg,
        rgba(252, 217, 9, 0.15) 0%,
        rgba(254, 164, 0, 0.15) 50%,
        rgba(226, 249, 116, 0.1) 100%);
      border: 1px solid rgba(252, 217, 9, 0.3);
      animation: promoPulse 4s ease-in-out infinite;
      box-shadow:
        0 4px 20px rgba(252, 217, 9, 0.2),
        inset 0 1px 0 rgba(255, 255, 255, 0.1);
      position: relative;
      overflow: hidden;

      &::before {
        background: linear-gradient(135deg,
          rgba(252, 217, 9, 0.2) 0%,
          rgba(254, 164, 0, 0.2) 50%,
          rgba(226, 249, 116, 0.15) 100%);
      }

      .promo-banner-title {
        color: #fcd909;
        text-shadow: 0 2px 8px rgba(252, 217, 9, 0.4);
      }

      .promo-banner-icon-inline {
        filter: drop-shadow(0 0 4px rgba(252, 217, 9, 0.6));
        animation: iconBounce 2.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite,
                   iconGlow 2s ease-in-out infinite;
      }

      // Елочки по бокам с анимацией
      .promo-banner-tree-left,
      .promo-banner-tree-right {
        position: absolute;
        top: 50%;
        transform: translateY(-50%);
        font-size: 1.8rem;
        z-index: 1;
        animation: treeTwinkle 2s ease-in-out infinite;
        filter: drop-shadow(0 0 8px rgba(252, 217, 9, 0.8));
        pointer-events: none;
      }

      .promo-banner-tree-left {
        left: 0.3rem;
        animation-delay: 0s;
      }

      .promo-banner-tree-right {
        right: 0.3rem;
        animation-delay: 1s;
      }

      // Добавляем отступы для контента, чтобы елочки не перекрывали текст
      .promo-banner-content {
        padding-left: 2rem;
        padding-right: 2rem;
      }

      // Снежинки
      .snowflakes {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 0;
      }

      .snowflake {
        position: absolute;
        color: rgba(255, 255, 255, 0.8);
        font-size: 1rem;
        animation: snowfall linear infinite;
        pointer-events: none;

        &:nth-child(1) {
          left: 10%;
          animation-duration: 10s;
          animation-delay: 0s;
        }

        &:nth-child(2) {
          left: 30%;
          animation-duration: 12s;
          animation-delay: 2s;
        }

        &:nth-child(3) {
          left: 50%;
          animation-duration: 14s;
          animation-delay: 4s;
        }

        &:nth-child(4) {
          left: 70%;
          animation-duration: 11s;
          animation-delay: 1s;
        }

        &:nth-child(5) {
          left: 85%;
          animation-duration: 13s;
          animation-delay: 3s;
        }

        &:nth-child(6) {
          left: 20%;
          animation-duration: 15s;
          animation-delay: 5s;
        }
      }
    }

    @keyframes treeTwinkle {
      0%, 100% {
        opacity: 1;
        transform: translateY(-50%) scale(1);
        filter: drop-shadow(0 0 8px rgba(252, 217, 9, 0.8));
      }
      50% {
        opacity: 0.7;
        transform: translateY(-50%) scale(1.1);
        filter: drop-shadow(0 0 12px rgba(252, 217, 9, 1));
      }
    }

    @keyframes snowfall {
      0% {
        transform: translateY(-100%) rotate(0deg);
        opacity: 0;
      }
      10% {
        opacity: 1;
      }
      90% {
        opacity: 1;
      }
      100% {
        transform: translateY(200%) rotate(360deg);
        opacity: 0;
      }
    }

    @media (max-width: 420px) {
      padding: 1rem 0.75rem;

      .promo-banner-close {
        top: 0.5rem;
        right: 0.5rem;
        width: 24px;
        height: 24px;
      }

      .promo-banner-icon-inline {
        font-size: 1.2rem;
        margin: 0;
        display: inline-block;
        animation: iconBounce 2.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite,
                   iconGlow 2s ease-in-out infinite;
        vertical-align: middle;
        filter: drop-shadow(0 0 4px rgba(252, 217, 9, 0.6));
        flex-shrink: 0;
      }

      .promo-banner-content {
        gap: 0.5rem;
        align-items: flex-start;
        padding: 0 0.5rem;

        .promo-banner-text {
          gap: 0.4rem;

          .promo-banner-title {
            line-height: 1.3;
            font-size: clamp(13px, 3.5vw, 16px);
          }

          .promo-banner-description {
            line-height: 1.5;
          }
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

  .shop-tabs {
    display: flex;
    width: auto;
    margin: 0 0 0 20px;
    background: rgba(0, 0, 0, 0.5);
    border-radius: 20px;
    padding: 3px;
    gap: 3px;
    min-width: 200px;

    .tab-btn {
      flex: 1;
      padding: 6px 12px;
      border-radius: 17px;
      background: transparent;
      border: none;
      color: #FFFFFF;
      font-family: 'Inter' !important;
      font-weight: 600;
      font-size: 14px;
      cursor: pointer;
      transition: all 0.3s ease;
      white-space: nowrap;

      &.active {
        background: linear-gradient(to bottom, #e2f974, #009600);
        color: #000000;
      }
    }
  }

  .gems-list {
    display: flex;
    width: 90%;
    flex-direction: column;
    padding: 10px 0;
    align-items: center;
    gap: 1.5rem;
    overflow-y: scroll;
    overflow-x: hidden;
    margin-bottom: -10px;
    -ms-overflow-style: none;
    scrollbar-width: none;

    &::-webkit-scrollbar {
      display: none;
    }

    .gem-item {
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

      .gem-info-icon-top {
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

      .gem-picture {
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        max-width: 95px;
        gap: 0;

        .gem-icon {
          font-size: 40px;
        }

        .gem-image {
          min-width: 115px;
          margin: -25px 0 -10px;
          height: auto;

          &.hide-under-tag {
            z-index: -15;
          }
        }
      }

      .gem-info {
        display: flex;
        flex-direction: column;
        align-items: start;
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

          .gem-price {
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

          .gem-price {
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

        .gem-price {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 0.3rem;
          font-size: 12px;
          line-height: 16pt;
          font-weight: 700;
          font-family: 'Inter' !important;
          color: #000;

          &.gem-saleprice {
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
          box-shadow:
            0 0 15px 2px #fccd0835,
            0 0 2px 2px #00000020;
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
          box-shadow:
            0 0 15px 2px #fccd0835,
            -1px -1px 2px 2px #00000020;
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
  }

  .asics-list {
    display: flex;
    width: 90%;
    flex-direction: column;
    padding: 10px 0;
    align-items: center;
    // gap: .5rem;
    gap: 1.5rem;
    overflow-y: scroll;
    margin-bottom: -10px;
    -ms-overflow-style: none;
    scrollbar-width: none;

    &::-webkit-scrollbar {
      display: none;
    }

    .item {
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
        // gap: 0.4rem;
        gap: 0;
        // width: min(95px, 12dvh);
        max-width: 95px;

        img {
          // width: 62px;
          // max-width: 62px;
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
        background-color: #323232;
        border-radius: 0 0 1rem 1rem;
        padding: 0.2rem 0;
        margin: 0 -1rem;
        z-index: -10;
      }

      .runline {
        position: absolute;
        bottom: 0;
        width: 100%;
        color: #fff;
        font-family: 'Inter' !important;
        text-transform: uppercase;
        font-weight: 400;
        font-size: 0.55rem;
        background-color: #323232;
        border-radius: 0 0 1rem 1rem;
        padding: 0.2rem 0;
        margin: 0 -1rem;
        z-index: -10;
        overflow: hidden;

        .backplane {
          position: relative;
          width: 100%;
          height: 80%;
          display: flex;
          justify-content: start;
          align-items: center;
          background: #fccd08;

          .asic-type {
            position: absolute;
            left: 50%;
            padding: 0.2rem 1rem;
            text-align: center;
            color: #fff;
            font-family: 'Inter' !important;
            text-transform: uppercase;
            font-weight: 600;
            font-size: 0.55rem;
            border-radius: 0.1rem;
            transform: translateX(-50%);
            border-radius: 0.3rem;
            box-shadow: inset 0 0 0 1px #ffffff40;
            z-index: 10;
          }

          .textline {
            text-align: center;
            color: #000;
            text-transform: uppercase;
            animation: text 8s infinite linear;
            white-space: nowrap;
            z-index: 1;
          }

          @keyframes text {
            0% {
              transform: translateX(0);
            }

            100% {
              transform: translateX(-50%);
            }
          }
        }
      }

      .info {
        display: flex;
        flex-direction: column;
        align-items: start;
        justify-content: center;
        width: 100%;
        min-width: 110px;
        line-height: 95%;
        margin-bottom: 10px;

        span:not(.name):not(.label) {
          text-wrap: nowrap;
        }

        .label {
          color: #000;
          font-family: 'Inter' !important;
          font-weight: 600;
          font-size: 0.5rem;
          padding: 0 0.5rem;
          border-radius: 1rem;
          margin: -0.4rem 0 0.1rem;
          background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
            linear-gradient(to bottom, #e2f974, #009600);
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

        .price {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 0.3rem;
          font-size: 12px;
          line-height: 16pt;
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
          box-shadow:
            0 0 15px 2px #fccd0835,
            0 0 2px 2px #00000020;
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
            linear-gradient(to bottom, #fcd909, #fea400);
        }

        .sale-newprice {
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
}

.equip-modal {
  position: absolute;
  bottom: -110px;
  z-index: 100;
  width: 100%;
  height: 100%;
  display: flex;
  padding-bottom: 120px;
  flex-direction: column;
  align-items: center;
  border-radius: 1rem 1rem 0 0;
  background:
    url('@/assets/asics-shop-bg.webp') no-repeat top center,
    radial-gradient(ellipse 45% 50% at top center, #31ff8080, transparent),
    #08150a;
  // box-shadow: 0 -10px 40px 10px #31ff8080;

  .top-panel {
    display: flex;
    width: 90%;
    padding: 1rem 0 .5rem;
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
      font-size: clamp(14px, 5.5dvw, 24px);
      text-wrap: nowrap;
    }

    .close {
      width: 20%;
      display: flex;
      align-items: center;
      justify-content: end;
    }
  }

  .asics-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.5rem;
    width: 90%;
    padding: 10px 0;
    margin-bottom: -10px;
    overflow-y: scroll;
    -ms-overflow-style: none;
    scrollbar-width: none;

    &::-webkit-scrollbar {
      display: none;
    }

    .slot-item {
      position: relative;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      width: 100%;
      height: auto;
      aspect-ratio: 1/1;
      background: #08150a50;
      backdrop-filter: blur(5px);
      box-shadow: inset 0 0 0 2px #009600;
      border-radius: 1rem;
      gap: 1rem;

      &.connect {
        box-shadow: inset 0 0 0 2px #565656;
      }

      &.rented {
        box-shadow: inset 0 0 0 2px #8143fc;
      }

      .buy-button {
        color: #000;
        background: linear-gradient(to bottom, #e2f974, #009600);
        box-shadow: inset 0 0 2px 2px #ffffff50;
        padding: 0.7rem 1rem;
        border-radius: 0.3rem;
        font-family: 'Inter' !important;
        font-weight: 600;
        font-size: 13px;
        z-index: 30;

        &:active {
          background: linear-gradient(to bottom, #e2f97490, #00960090);
        }
      }

      .top-label {
        position: absolute;
        z-index: 50;
        top: 0;
        width: 100%;
        text-align: center;
        display: flex;
        justify-content: center;
        align-items: center;
        border-radius: 1rem 1rem 0 0;
        font-family: 'Inter' !important;
        font-size: 14px;
        font-weight: bold;
        background: linear-gradient(to bottom, #e2f974, #009600);

        &.connect {
          color: #000;
          background: linear-gradient(to bottom, #E2E2E2, #646464);
        }

        &.rented {
          color: #fff;
          background: linear-gradient(to bottom, #B28FF8, #8143FC);
        }
      }

      .pic-wrapper {
        position: relative;
        width: 100%;
        height: 100%;


        .info-label {
          position: absolute;
          right: 10px;
          top: 30px;
          width: 18px;
          height: 18px;
          z-index: 20;
          transition: all 100ms ease-in-out;

          &.checked {
            transform: scale(0.8);
            opacity: 0.7;
          }
        }

        .rent-time {
          position: absolute;
          z-index: 15;
          width: 100%;
          left: 50%;
          top: 50%;
          transform: translate(-50%, -50%);
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          gap: 3px;

          >p {
            font-family: 'Inter';
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 0;
            color: #8A8C8F;
          }

          >h1 {
            font-family: 'Inter';
            font-size: 20px;
            font-weight: bold;
            letter-spacing: 0;
            color: #fff;
          }
        }

        .locked-nft {
          position: absolute;
          z-index: 15;
          width: 100%;
          left: 50%;
          bottom: 5%;
          transform: translateX(-50%);
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          gap: 3px;

          .nft-name {
            width: 100%;
            color: #fff;
            font-family: 'Inter' !important;
            font-size: clamp(8px, 3vw, 14px);
            line-height: clamp(12px, 7.5vw, 30px);
            font-weight: bold;
            text-transform: uppercase;
            text-align: center;
          }

          >p {
            font-family: 'Inter';
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 0;
            color: #8A8C8F;
          }

          >h1 {
            font-family: 'Inter';
            font-size: 24px;
            font-weight: bold;
            letter-spacing: 0%;
            color: #fff;
          }

          .speedup-btn {
            color: transparent;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-family: 'Inter';
            font-weight: 600;
            font-size: clamp(12px, 5vw, 20px);
            overflow: hidden;
            background: linear-gradient(90deg, transparent, #fff, transparent);
            background-repeat: no-repeat;
            background-size: 80%;
            animation: animate 2.5s linear infinite;
            -webkit-background-clip: text;
            -webkit-text-fill-color: rgba(255, 255, 255, 0);
          }

          .lock-progress {
            width: 80%;
            margin-top: 8px;

            .progress-bar {
              width: 100%;
              height: 4px;
              background: rgba(255, 255, 255, 0.2);
              border-radius: 2px;
              overflow: hidden;

              .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #ffffff, #c8c8c8);
                border-radius: 2px;
                transition: width 0.3s ease;
                position: relative;
                overflow: hidden;

                &::after {
                  content: '';
                  position: absolute;
                  top: 0;
                  left: -100%;
                  width: 100%;
                  height: 100%;
                  background: linear-gradient(90deg, transparent, rgba(61, 61, 61, 0.595), transparent);
                  animation: shimmer 2s infinite;
                }

                @keyframes shimmer {
                  0% {
                    left: -100%;
                  }

                  100% {
                    left: 100%;
                  }
                }
              }
            }

            .progress-text {
              margin-top: 4px;
              font-family: 'Inter';
              font-size: 10px;
              font-weight: 400;
              color: rgba(255, 255, 255, 0.7);
              text-align: center;

              .progress-percent {
                color: #ffffff;
                font-weight: 600;
              }
            }
          }

          @keyframes animate {
            0% {
              background-position: -500%;
            }

            100% {
              background-position: 500%;
            }
          }
        }

        .pic {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          border-radius: 1rem;
          object-fit: contain;
          z-index: 0;
        }

        .visible-eye {
          position: absolute;
          top: 27px;
          right: 5px;
          z-index: 60;
        }

        &.connect {
          .pic {
            filter: blur(1px);
            opacity: 0.2;
          }

          .visible-eye {
            display: none;
          }
        }

        .gradient-overlay {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: linear-gradient(to bottom, #000000, transparent, #000000);
          border-radius: 1rem;
          z-index: 10;
          pointer-events: none;

          &.rented {
            background: linear-gradient(to bottom, #000000bb, transparent, #000000bb), #24242499;
          }

          &.connect {
            background: linear-gradient(to bottom, #363636B3, #363636B3);
          }
        }

        .second-gradient-overlay {
          position: absolute;
          bottom: 0;
          left: 0;
          width: 100%;
          height: 40%;
          background: linear-gradient(to bottom, transparent, #000000);
          border-radius: 0 0 1rem 1rem;
          z-index: 12;
          pointer-events: none;
        }
      }

      .picture {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        border-radius: 1rem;
        object-fit: contain;
        z-index: 0;
      }

      .bottom-panel {
        position: absolute;
        bottom: 0;
        width: 100%;
        padding: 1rem 0;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 30;

        span {
          width: 100%;
          color: #fff;
          font-family: 'Inter' !important;
          font-size: clamp(8px, 3vw, 14px);
          font-weight: bold;
          text-transform: uppercase;
          text-align: center;
        }
      }
    }
  }
}

.screen-box {
  width: 100%;
  height: 90vh;
  background: radial-gradient(ellipse 80% 30% at top, #31ff80, transparent 100%), #08150a;
  padding: 10px 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;

  .add-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin: 0 auto;
    width: 90%;
    padding: 15px 0 70% 0;
    gap: 10px;
    overflow-y: scroll;
    -ms-overflow-style: none;
    scrollbar-width: none;

    &::-webkit-scrollbar {
      display: none;
      /* Safari and Chrome */
    }

    .item {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 0 0 0.5rem;
      background: #08150a50;
      border: 1px solid #ffffff25;
      border-radius: 1rem;
      height: 54px;
      z-index: 1;
      width: 100%;

      &.timeout-pulse {
        border: 1px solid #ff3b59;
        animation: pulse linear 2s infinite;

        @keyframes pulse {
          0% {
            border-color: #ff3b59;
            box-shadow: inset 0 0 3px 1px #ff3b5950;
          }

          50% {
            border-color: #ff3b5925;
            box-shadow: inset 0 0 3px 3px #ff3b5925;
          }

          100% {
            border-color: #ff3b59;
            box-shadow: inset 0 0 3px 1px #ff3b5950;
          }
        }
      }

      .bg {
        --m-i: linear-gradient(#000, #000);
        --m-o: content-box, padding-box;
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        border-radius: 15px;
        padding: 2px;
        -webkit-mask-image: var(--m-i), var(--m-i);
        mask-image: var(--m-i), var(--m-i);
        -webkit-mask-origin: var(--m-o);
        mask-origin: var(--m-o);
        -webkit-mask-clip: var(--m-o);
        mask-composite: exclude;
        border: none;
        overflow: hidden;

        &::before {
          content: '';
          position: absolute;
          left: 50%;
          top: 50%;
          margin: 0 auto;
          width: 120%;
          z-index: -1;
          aspect-ratio: 1/1;
          transform-origin: 0% 0%;
          place-content: center;
          place-items: center;
          background-image: linear-gradient(to right, #46ff8d, #006928, transparent);
          animation: speeen linear 2s infinite;

          @keyframes speeen {
            from {
              transform: rotate(0deg) translate(-50%, -50%);
            }

            to {
              transform: rotate(360deg) translate(-50%, -50%);
            }
          }
        }
      }

      .reconnect {
        --m-i: linear-gradient(#000, #000);
        --m-o: content-box, padding-box;
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        border-radius: 15px;
        padding: 2px;
        -webkit-mask-image: var(--m-i), var(--m-i);
        mask-image: var(--m-i), var(--m-i);
        -webkit-mask-origin: var(--m-o);
        mask-origin: var(--m-o);
        -webkit-mask-clip: var(--m-o);
        mask-composite: exclude;
        border: none;
        overflow: hidden;

        &::before {
          content: '';
          position: absolute;
          left: 50%;
          top: 50%;
          margin: 0 auto;
          width: 150%;
          z-index: -1;
          aspect-ratio: 1/1;
          transform-origin: 0% 0%;
          place-content: center;
          place-items: center;
          background-image: linear-gradient(to right, #ff3b59, #690002, transparent);
          animation: speeen linear 2s infinite;

          @keyframes speeen {
            from {
              transform: rotate(0deg) translate(-50%, -50%);
            }

            to {
              transform: rotate(360deg) translate(-50%, -50%);
            }
          }
        }
      }

      .item-grouping {
        display: flex;
        align-items: center;
        gap: 0.3rem;
        z-index: 2;

        .grid-item-text {
          display: flex;
          flex-direction: column;

          .data {
            display: flex;
            align-items: center;
            gap: 0.2rem;
            font-family: 'Inter' !important;
            font-size: clamp(8px, 3.2vw, 13px);
            font-weight: 700;
            color: #fff;
          }

          .desc {
            // text-wrap: nowrap;
            // display: flex;
            // align-items: center;
            // gap: 0.1rem;
            font-family: 'Inter' !important;
            font-size: 10px;
            color: #ffffff50;
          }
        }
      }

      button {
        color: #212121;
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);
        padding: 0 0.5rem;
        margin-right: 0.5rem;
        max-height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 24px;
        font-family: 'Inter' !important;
        font-size: 10px;
        font-weight: 700;
        border-radius: 5px;

        &.timeout-btn {
          color: #fff;
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
            linear-gradient(to bottom, #ff3b59, #90192b);
          animation: pulsation 2s infinite;

          @keyframes pulsation {
            0% {
              color: #fff;
              background: radial-gradient(ellipse 100% 30% at bottom center,
                  #ffffff70,
                  transparent),
                linear-gradient(to bottom, #ff3b59, #90192b);
            }

            50% {
              color: #212121;
              background: radial-gradient(ellipse 100% 30% at bottom center,
                  #ffffff70,
                  transparent),
                linear-gradient(to bottom, #fcd909, #fea400);
            }

            100% {
              color: #fff;
              background: radial-gradient(ellipse 100% 30% at bottom center,
                  #ffffff70,
                  transparent),
                linear-gradient(to bottom, #ff3b59, #90192b);
            }
          }
        }

        &:active {
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff50, transparent),
            linear-gradient(to bottom, #ff3b59, #90192b);
        }
      }

      .plus {
        padding: 0;
        font-size: 15px;
        line-height: 17px;
        aspect-ratio: 1/1;
        max-height: 24px;
        max-width: 24px;
      }
    }
  }
}

.currencies {
  width: 90%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin: 0 auto;

  .currency {
    display: flex;
    align-items: center;
    padding: 0 1.5rem 0 0;
    background: linear-gradient(to left, #00000050, transparent);
    border-radius: 5rem;
    gap: 0.3rem;
    font-family: 'Inter' !important;
    font-weight: 600;
    font-size: 13px;
    color: #fff;
  }
}

.mining-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
  width: 90%;
  overflow: visible;

  .miner-block {
    padding: 0.8rem 1.2rem 0.8rem 0;
    margin-right: 1rem;
    border-radius: 1rem;
    border: 1px solid #ffffff25;
    display: flex;
    gap: 0.3rem;
    font-family: 'Inter' !important;
    font-size: 13px;
    font-weight: 600;
    overflow: visible;
    position: relative;
    z-index: 1;

    .bg {
      --m-i: linear-gradient(#000, #000);
      --m-o: content-box, padding-box;
      position: absolute;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      border-radius: 0.9rem;
      padding: 2px;
      -webkit-mask-image: var(--m-i), var(--m-i);
      mask-image: var(--m-i), var(--m-i);
      -webkit-mask-origin: var(--m-o);
      mask-origin: var(--m-o);
      -webkit-mask-clip: var(--m-o);
      mask-composite: exclude;
      border: none;
      overflow: hidden;

      &::before {
        content: '';
        position: absolute;
        left: 50%;
        top: 50%;
        margin: 0 auto;
        width: 150%;
        z-index: -1;
        aspect-ratio: 1/1;
        transform-origin: 0% 0%;
        place-content: center;
        place-items: center;
        background-image: linear-gradient(to right, #46ff8d, #006928, transparent);
        animation: speeen linear 2s infinite;

        @keyframes speeen {
          from {
            transform: rotate(0deg) translate(-50%, -50%);
          }

          to {
            transform: rotate(360deg) translate(-50%, -50%);
          }
        }
      }
    }

    .grouping {
      display: flex;
      flex-direction: column;
      align-items: start;

      .ctrl-mining-btn {
        position: relative;
        width: 100%;
        padding: 0.5rem 0.5rem;
        border-radius: 0.5rem;
        background: linear-gradient(to bottom, #fcd909, #fea400);
        margin-bottom: 5px;

        &::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: url('@/assets/pickaxe.svg') no-repeat center;
          opacity: 0.15;
          /* Adjust opacity value as needed */
          z-index: 1;
          /* Ensure the background image stays behind the content */
        }

        &:active {
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
            linear-gradient(to bottom, #fcd90990, #fea40090);
        }
      }

      span {
        color: #ffffff75;
        font-family: 'Inter' !important;
        font-weight: 400;
        font-size: 10px;

        .mining-time {
          color: #fff;
        }
      }
    }
  }
}

.equip-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #fff;
  font-family: 'Inter' !important;

  span {
    margin-top: 3px;
    font-size: 12px;
  }

  .equip-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 0.75rem;
    background: linear-gradient(to bottom, #fcd909, #fea400);
    border-radius: 1rem;

    &:active {
      background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
        linear-gradient(to bottom, #fcd90990, #fea40090);
    }
  }
}

/* Стили для стартер пакета в модалке */
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
</style>
