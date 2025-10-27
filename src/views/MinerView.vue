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
import asicsSheet, { gemsSheet } from '@/services/data'
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

const openReconnectModal = ref(false)
const reconnectExample = ref(null)

const openSpecialModal = ref(false)
const openClaim = ref(false)

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
    await buyAsics(
      asicsSheet.findIndex((el) => el.name == currBuyAsic.value.name),
      currBuyAsic.value?.price,
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

function openAsics(side = true) {
  let opt = side == true ? true : false
  asicsIsOpen.setOpenAsicsShop(opt)
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
  activeShopTab.value = activeShopTab.value === 'gems' ? 'asics' : 'gems'
}

const speedUpNft = (item) => {
  speedUpAddress.value = item.nft ? item.nft : item.address
  openNftSpeedUp.value = true
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
  <RedirectModal v-if="openRedirectModal" :link="redirectLink" @close="openRedirectModal = false" />
  <ReconnectModal v-if="openReconnectModal" :example="reconnectExample" @close="checkReconnect" />
  <SpecialPriceModal v-if="openSpecialModal" :saleAsic="currBuyAsic" @close="specialModalResponse" />
  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
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
        <h1>{{ t('asic_shop.title') }}</h1>
        <button class="close" @click="openAsics(false)">
          <Exit :width="16" style="color: #fff" />
        </button>
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
          <button @click="buyAsics(index, asicItem?.price, asicItem?.link, asicItem?.sale, asicItem?.shop)"
            :disabled="!asicItem?.shop">
            <span>{{ t('asic_shop.buy_asic') }}</span>
            <span class="price" :class="{ saleprice: asicItem?.new_price }">
              <img src="@/assets/TON.png" width="14px" height="14px" />
              {{ asicItem?.price }}
            </span>
            <div v-if="asicItem?.perc" class="sale-perc">-{{ asicItem?.perc }}%</div>
            <div v-if="asicItem?.new_price" class="sale-newprice">
              <img src="@/assets/TON.png" width="12px" height="12px" />
              {{ asicItem?.new_price }}
            </div>
          </button>
          <span v-if="!asicItem?.sale" class="tag" :style="asicItem?.rarity == 'Common'
            ? 'background-color: #5D625E'
            : asicItem?.rarity == 'Rare'
              ? 'background-color: #009600;'
              : asicItem?.rarity == 'Epic'
                ? 'background-color: #0918E9;'
                : asicItem?.rarity == 'Legendary'
                  ? 'background-color: #E98509;'
                  : 'background-color: #6B25A1;'
            ">{{ t(`asic_shop.${asicItem?.rarity.toLowerCase()}`) }}</span>
          <span v-if="asicItem?.sale" class="runline" :style="asicItem?.rarity == 'Common'
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
                - BEst choise now - Sale - BEst choise now - Sale - BEst choise now - Sale - BEst
                choise now - Sale - BEst choise now - Sale - BEst choise now - Sale - BEst choise
                now - Sale - BEst choise now - Sale
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

      <!-- GEMS List -->
      <div v-if="activeShopTab === 'gems'" class="gems-list">
        <div class="gem-item"
          :class="{
            'has-gold-stroke': gemItem?.hasGoldStroke,
            'has-purple-stroke': gemItem?.hasPurpleStroke
          }"
          v-for="gemItem in gemsSheet.filter(el => el.shop)"
          :key="gemItem">
          <div class="gem-info-icon-top">!</div>
          <div class="gem-picture">
            <img v-if="gemItem?.imagePath" :src="gemItem.imagePath" class="gem-image" alt="NFT" />
            <div v-else class="gem-icon">💎</div>
          </div>
          <div class="gem-info">
            <span class="gem-type">{{ gemItem.type }}</span>
            <span class="gem-description" v-for="(benefit, idx) in gemItem.benefits" :key="idx">
              {{ benefit }}
            </span>
          </div>
          <button class="gem-buy-btn"
            :class="{
              'btn-gold': gemItem?.buttonColor === 'gold',
              'btn-purple': gemItem?.buttonColor === 'purple'
            }"
            :disabled="!gemItem?.shop">
            <span>{{ gemItem.name }}</span>
            <span class="gem-price">
              <img src="@/assets/TON.png" width="14px" height="14px" />
              {{ gemItem.price }}
            </span>
          </button>
          <span class="gem-tag" :style="gemItem?.buttonColor === 'gold'
            ? 'background: linear-gradient(270deg, #FEA400 0%, #FCD909 100%), #FFC300;'
            : gemItem?.buttonColor === 'purple'
              ? 'background: linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(152, 81, 236, 1) 50%, rgba(94, 124, 234, 1) 100%), #FFC300;'
              : gemItem?.rarity == '4 class'
                ? 'background-color: #5D625E;'
                : gemItem?.rarity == '3 class'
                  ? 'background-color: #009600;'
                  : gemItem?.rarity == '2 class'
                    ? 'background-color: #0918E9;'
                    : 'background-color: #6B25A1;'
            ">{{ gemItem.rarity }}</span>
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

  .shop-tabs {
    display: flex;
    width: 90%;
    margin: 0.5rem 0;
    background: rgba(0, 0, 0, 0.5);
    border-radius: 20px;
    padding: 3px;
    gap: 3px;

    .tab-btn {
      flex: 1;
      padding: 8px;
      border-radius: 17px;
      background: transparent;
      border: none;
      color: #FFFFFF;
      font-family: 'Inter' !important;
      font-weight: 600;
      font-size: 16px;
      cursor: pointer;
      transition: all 0.3s ease;

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
        box-shadow: none;
        background: linear-gradient(#08150a50, #08150a50) padding-box,
          linear-gradient(0deg, #FEA400 0%, #FCD909 100%) border-box;
        border: 1px solid transparent;
      }

      &.has-purple-stroke {
        box-shadow: none;
        background: linear-gradient(#08150a50, #08150a50) padding-box,
          linear-gradient(-90deg, rgba(231, 87, 236, 1) 0%, rgba(152, 81, 236, 1) 50%, rgba(94, 124, 234, 1) 100%) border-box;
        border: 1px solid transparent;
      }

      .gem-info-icon-top {
        position: absolute;
        top: 5px;
        right: 5px;
        width: 15px;
        height: 15px;
        background: #FFFFFF;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        font-weight: 700;
        color: #000000;
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

        .gem-icon {
          font-size: 40px;
        }

        .gem-image {
          min-width: 115px;
          margin: -25px 0 -10px;
          height: auto;
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
        min-width: max-content;
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

        &.btn-gold {
          background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
            linear-gradient(180deg, #FCD909 0%, #FEA400 100%);
        }

        &.btn-purple {
          background: radial-gradient(ellipse 80% 40% at bottom center, #ffffff90, transparent),
            linear-gradient(270deg, rgba(231, 87, 236, 1) 0%, rgba(152, 81, 236, 1) 50%, rgba(94, 124, 234, 1) 100%);
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
        }

        .gem-price {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 0.3rem;
          font-size: 12px;
          line-height: 16pt;
        }
      }

      .gem-tag {
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
</style>
