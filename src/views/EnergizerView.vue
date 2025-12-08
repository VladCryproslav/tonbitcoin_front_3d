<script setup>
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
const UpgradeBtn = defineAsyncComponent(() => import('@/assets/upgrd_btn.svg'))
const Storage = defineAsyncComponent(() => import('@/assets/storage.svg'))
const Power = defineAsyncComponent(() => import('@/assets/power.svg'))
const StationLvl = defineAsyncComponent(() => import('@/assets/station_lvl.svg'))
const Exit = defineAsyncComponent(() => import('@/assets/exit.svg'))
const Swap = defineAsyncComponent(() => import('@/assets/swap.svg'))
const Info = defineAsyncComponent(() => import('@/assets/white-info.svg'))
const ArrowRight = defineAsyncComponent(() => import('@/assets/arrow-right.svg'))
import('vue3-carousel/carousel.css')
import { useTabsStore } from '@/stores/tabs'
import { host, tonapi } from '@/../axios.config'
import { useAppStore } from '@/stores/app'
import StationSlider from '@/components/StationSlider.vue'
import { useTonAddress } from '@townsquarelabs/ui-vue'
import { useTelegram } from '@/services/telegram'
import { halloweenActive } from '@/services/data'
import ModalNew from '@/components/ModalNew.vue'
import MintModal from '@/components/MintModal.vue'
import UpgradeModal from '@/components/UpgradeModal.vue'
import AfterHeatModal from '@/components/AfterHeatModal.vue'
import HeatSwitch from '@/components/HeatSwitch.vue'
import CraftStationModal from '@/components/CraftStationModal.vue'
import { useI18n } from 'vue-i18n'
import InfoModal from '@/components/InfoModal.vue'
import { useRouter } from 'vue-router'

const { tg, user } = useTelegram()
const ORBITAL_STATION = 'Orbital Power Station'
const HYDRO_STATION = 'Hydroelectric Power Station'
const ton_address = useTonAddress()
const connectedAddressString = useTonAddress(false)

const { t } = useI18n()
const router = useRouter()
const app = useAppStore()
const tabs = useTabsStore()
const asicsIsOpen = useTabsStore()
let controller = null
let infoUpdateTimer = null

const img = shallowRef(null)
const factory = shallowRef(null)
const upgradeIsOpen = ref(false)
const mintableIsOpen = ref(false)
const openMintModal = ref(false)

const openUpgModal = ref(false)
const upgModalTitle = ref(null)
const upgModalBody = ref(null)
const upgModalPrice = ref(null)
const upgModalKind = ref(null)

const openModal = ref(false)
const modalBody = ref('')
const modalTitle = ref('')
const modalStatus = ref('')

const openWalletChangeInfo = ref(false)

const selectedWorkers = ref('all')

const handleWorkers = () => {
  const availableStates = ['simple'];
  if (getWorkers.value.gold) availableStates.push('gold');
  if (getWorkers.value.blue) availableStates.push('blue');
  if (availableStates.length > 1) availableStates.push('all');
  if (!selectedWorkers.value || !availableStates.includes(selectedWorkers.value)) {
    selectedWorkers.value = availableStates[0];
    return;
  }
  const currentIdx = availableStates.indexOf(selectedWorkers.value);
  const nextIdx = (currentIdx + 1) % availableStates.length;
  selectedWorkers.value = availableStates[nextIdx];
};

const getWorkers = computed(() => {
  const simple = Math.min(app?.user?.engineer_level, 49) || 0
  const gold = app?.user?.past_engineer_level > 49 ? app?.user?.past_engineer_level - 49 : 0
  const blue = new Date(app?.user?.electrics_expires) > new Date() ? 10 : 0

  // Формуємо масив доступних воркерів
  const available = ['simple'];
  if (gold) available.push('gold');
  if (blue) available.push('blue');

  let sorted = [...available];
  if (selectedWorkers.value && available.includes(selectedWorkers.value)) {
    sorted = [selectedWorkers.value, ...available.filter(x => x !== selectedWorkers.value)];
  }

  return {
    all: simple + gold + blue,
    simple,
    gold,
    blue,
    sorted
  }
})


const maxAttempts = ref({ rent: 0, lent: 0 })

const showMeModal = (status, title, body) => {
  modalStatus.value = status
  modalTitle.value = title
  modalBody.value = body
  openModal.value = true
}

const openAfterHeat = ref(false)
const openHeatSwitch = ref(false)

const openHeatCheck = ref(false)

const unlockedWallet = computed(() => {
  if (app.wallet_info) {
    return { bool: new Date(app?.wallet_info?.block_until) < new Date(), time: app?.wallet_info?.block_until }
  }
  return { bool: true, time: new Date().toISOString() }
})

const hydroStation = computed(() => {
  if (app.user?.has_hydro_station) {
    const hydroData = app.timed_nfts?.find(el => el.name == HYDRO_STATION)
    if (hydroData) {
      return { data: hydroData, lock: new Date(hydroData.block_until) > new Date(), time: hydroData.block_until }
    }
  }
  return { data: null, lock: false, time: new Date().toISOString() }
})

const orbitalStation = computed(() => {
  if (app.user?.has_orbital_station) {
    const orbitalData = app.timed_nfts?.find(el => el.name == ORBITAL_STATION)
    if (orbitalData) {
      return { data: orbitalData, lock: new Date(orbitalData.block_until) > new Date(), time: orbitalData.block_until }
    }
  }
  return { data: null, lock: false, time: new Date().toISOString() }
})

const openCraftStation = ref(false)
const craftParams = ref({ kind: null, kw: null, tbtc: null, nft: null, eng_lost: null, time: null, notif_id: null })

const craft = (kind, kw, tbtc, nft, eng_lost, time, notif_id) => {
  if (!ton_address.value) {
    showMeModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }
  craftParams.value.kind = kind || null
  craftParams.value.kw = kw || null
  craftParams.value.tbtc = tbtc || null
  craftParams.value.nft = nft || null
  craftParams.value.eng_lost = eng_lost || null
  craftParams.value.time = time || null
  craftParams.value.notif_id = notif_id || null

  openCraftStation.value = true
}

const craftResponse = async (val) => {
  openCraftStation.value = false;
  mintableIsOpen.value = false;
  if (val && !val.notif_id) {
    showMeModal(val.status, val.title, val.body);
  }
  if (val.notif_id) {
    try {
      controller = new AbortController()
      await host.post("notifications/mark-read/", { "notification_id": val.notif_id }, { signal: controller.signal })
      showMeModal(val.status, val.title, val.body);
    } catch (err) {
      console.log(err)
    } finally {
      controller = null
    }
  }
}

function convertTimeFormat(timeStr) {
  if (!timeStr) return;

  let days, hours, minutes, seconds;
  if (timeStr.includes(' ')) {
    const [daysPart, timePart] = timeStr.split(' ');
    days = parseInt(daysPart);
    [hours, minutes, seconds] = timePart.split(':');
  } else {
    days = 0; // Днів немає
    [hours, minutes, seconds] = timeStr.split(':');
  }

  // Переводимо все в секунди
  const daysInSeconds = parseInt(days) * 24 * 60 * 60;
  const hoursInSeconds = parseInt(hours) * 60 * 60;
  const minutesInSeconds = parseInt(minutes) * 60;
  const secondsTotal = parseInt(seconds);

  // Сумуємо всі секунди
  const totalSeconds = daysInSeconds + hoursInSeconds + minutesInSeconds + secondsTotal;

  // Переводимо назад у формат HH:MM:SS
  const newHours = Math.floor(totalSeconds / 3600);
  const remainingSeconds = totalSeconds % 3600;
  const newMinutes = Math.floor(remainingSeconds / 60);
  const newSeconds = remainingSeconds % 60;

  // Форматуємо з провідними нулями
  const formattedHours = String(newHours).padStart(2, '0');
  const formattedMinutes = String(newMinutes).padStart(2, '0');
  const formattedSeconds = String(newSeconds).padStart(2, '0');

  return `${formattedHours}:${formattedMinutes}:${formattedSeconds}`;
}

const activeStation = ref(null)

let clickCount = ref(0)
let lastClickTime = ref(0)
const clickLimit = 1
const isProcessing = ref(false)
const updateStopped = ref(false)

const jarvisImg = shallowRef(null)

const isJarvis = computed(() => {
  const now = new Date()
  const expires = new Date(app?.user?.jarvis_expires)
  const forever = new Date(app?.user?.jarvis_expires).getFullYear() === 2100
  const timeDiff = expires - now // Time difference in milliseconds
  const active = timeDiff > 0
  const totalMinutes = Math.floor(timeDiff / 1000 / 60) // Convert to minutes
  const hours = Math.floor(totalMinutes / 60) // Full hours
  const minutes = totalMinutes % 60 // Remaining minutes

  // Pad with leading zeros if needed
  const formattedHours = String(hours).padStart(2, '0')
  const formattedMinutes = String(minutes).padStart(2, '0')
  return { active, time: `${formattedHours}:${formattedMinutes}`, forever }
})

let isStopped = false

const spawnNumber = (side) => {
  if (!jarvisImg.value) return // Ensure the image is available
  const rect = jarvisImg.value.getBoundingClientRect()
  const tap = app?.gen_config ? app?.gen_config?.find((el) => el?.station_type == app?.user?.station_type && el?.level == app?.user?.storage_level)?.generation_rate / 60 / 60 || 0 : 0
  const plusOne = document.createElement('div')
  plusOne.classList.add('plus-one')
  plusOne.style.position = 'absolute'
  plusOne.textContent = `+${+tap.toFixed(3) || 0.1}`
  plusOne.style.zIndex = 1000

  // Randomize vertical position for variety
  const randomY = rect.top - rect.height * 1.8

  if (side === 'left') {
    plusOne.style.left = `${rect.left - 140}px` // Left side offset
  } else {
    plusOne.style.left = `${rect.right - 60}px` // Right side offset
  }
  plusOne.style.top = `${randomY}px`
  jarvisImg.value.parentElement.appendChild(plusOne)
  setTimeout(() => plusOne.remove(), 1500) // Remove after 1.5s
}

let timeRemainingInterval = null
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
  timeRemainingInterval = setInterval(updateTime, 1000)

  return { time: timeRemaining.value, remain: timeRemainingMs.value }
}

async function speedUpBuilding() {
  controller = new AbortController()
  const invoiceLink = orbitalStation.value.lock ?
    await host.post(`timed-nft-stars/`, { timed_nft_id: orbitalStation.value?.data?.id }) :
    hydroStation.value.lock ?
      await host.post(`timed-nft-stars/`, { timed_nft_id: hydroStation.value?.data?.id }) :
      await host.post(`speed-build-stars/`, { signal: controller.signal })
  if (invoiceLink.status == 200) {
    controller = null
    tg.openInvoice(invoiceLink.data?.link, (status) => {
      if (status == 'paid') {
        app.initUser()
        showMeModal('success', t('notification.st_success'), t('notification.building_speedup'))
      }
    })
  }
}

let animationStarted = false

const startAnimation = () => {
  if (isStopped) return
  spawnNumber('left')
  setTimeout(() => {
    spawnNumber('right')
    setTimeout(startAnimation, 1000)
  }, 1000)
}

const stopAnimation = () => {
  isStopped = true
}

function getUpgModal(title, body, price, kind) {
  upgModalTitle.value = title
  upgModalBody.value = body
  upgModalPrice.value = price
  upgModalKind.value = kind
  openUpgModal.value = true
}

function showModal(val) {
  openUpgModal.value = false
  if (val) {
    showMeModal(val.status, val.title, val.body)
  }
}

const responseAfterHeat = (res) => {
  openAfterHeat.value = false
  if (res?.showSwitch) {
    openHeatSwitch.value = true
  }
}

const responseHeatSwitch = async () => {
  openHeatSwitch.value = false
  controller = new AbortController()
  await host.post('enable-station/', { signal: controller.signal }).finally(() => { controller = null })
  await app.init()
  openHeatCheck.value = false
}

function openAsics() {
  asicsIsOpen.setCategory('miner')
  asicsIsOpen.setOpenAsicsShop(true)
}

function openUpgrade() {
  upgradeIsOpen.value = true
}

const imagePath = computed(() => {
  // Если есть орбитальная станция и она активна (не в режиме Regular)
  if (app.user?.has_orbital_station && !app.user?.orbital_force_basic) {
    return new URL(`../assets/Orbital Power Plant.webp`, import.meta.url).href
  }
  if (app?.user?.has_hydro_station) {
    return new URL(`../assets/Hydroelectric power plant.webp`, import.meta.url).href
  }
  return new URL(`../assets/${app?.user?.station_type}-${app?.user?.storage_level}.webp`, import.meta.url).href
})

const imagePathCard = computed(() => {
  const currentStationIndex = allStations.indexOf(app.user.station_type)
  const currentLevel = app.user.storage_level

  // Если есть орбитальная станция и она активна (не в режиме Regular)
  if (app.user.has_orbital_station && !app.user?.orbital_force_basic) {
    return new URL(`../assets/Orbital Power Plant.webp`, import.meta.url).href
  }
  if (app.user.has_hydro_station) {
    return new URL(`../assets/Hydroelectric power plant.webp`, import.meta.url).href
  }
  if (currentLevel < 3) {
    // Переходимо на наступний рівень тієї ж станції
    return new URL(`../assets/${app.user.station_type}-${currentLevel + 1}.webp`, import.meta.url)
      .href
  } else {
    // Переходимо на наступну станцію
    const nextStationIndex = currentStationIndex + 1

    // Перевіряємо, чи є наступна станція
    if (nextStationIndex < allStations.length) {
      return new URL(`../assets/${allStations?.[nextStationIndex]}-1.webp`, import.meta.url).href
    } else {
      // Якщо немає наступної станції, повертаємо зображення поточної станції на поточному рівні
      return new URL(`../assets/${app.user.station_type}-${currentLevel}.webp`, import.meta.url).href
    }
  }
})

const allStations = app.stations?.storage_configs ? [...new Set(app.stations?.storage_configs?.sort((a, b) => a.id - b.id)?.map((el) => el?.station_type))] : []

const setActiveStation = (station) => {
  activeStation.value = station
}

const findMaxLevel = (array) => {
  const arr = Array.isArray(array) ? array.map((item) => item.level || 0) : [];
  return Math.max(...arr);
};

async function claim() {
  await app.initUser()
  if (!ton_address.value) {
    showMeModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }
  if (app.user.energy < (app.withdraw_config?.min_kw || 300)) {
    showMeModal(
      'warning',
      t('notification.st_attention'),
      t('notification.min_mint_bal', { bal: app.withdraw_config?.min_kw || 300 })
    )
    return
  }
  if (app.wallet_info?.kw_amount < (app.withdraw_config?.min_kw || 300)) {
    showMeModal(
      'warning',
      t('notification.st_attention'),
      t('notification.min_mint_bal_wallet', { bal: app.withdraw_config?.min_kw || 300, address: ton_address.value?.slice(0, 5) + '...' + ton_address.value?.slice(-5) })
    )
    return
  }
  openMintModal.value = true
}

async function upgrade(params) {
  try {
    const tmp_storage_lvl = app.user.storage_level
    const tmp_gen_lvl = app.user.generation_level
    controller = new AbortController()
    const res = await host.post(`upgrade-${params}/`, { signal: controller.signal })
    if (res.status == 200) {
      modalStatus.value = 'success'
      modalTitle.value = t('notification.st_success')
      switch (params) {
        case 'storage':
          modalBody.value =
            tmp_storage_lvl == 1
              ? t('notification.storage_upd_2')
              : t('notification.storage_upd_max')
          break
        case 'generation':
          modalBody.value =
            tmp_gen_lvl == 1
              ? t('notification.gen_upd_2')
              : t('notification.gen_upd_max')
          break
        case 'engineer':
          modalBody.value = t('notification.eng_add')
          break
      }
    }
    await app.initUser()
  } catch (err) {
    console.log(err)
    modalStatus.value = 'error'
    modalTitle.value = t('notification.st_error')
    modalBody.value = t('notification.no_money')
  } finally {
    controller = null
    openModal.value = true
  }
}

async function switchOrbitalStation() {
  try {
    controller = new AbortController()
    const res = await host.post('switch-orbital-station/', { signal: controller.signal })
    if (res.status == 200) {
      await app.initUser()
      modalStatus.value = 'success'
      modalTitle.value = t('notification.st_success')
      modalBody.value = !app.user?.orbital_force_basic
        ? t('notification.switched_to_orbital')
        : t('notification.switched_to_regular')
    }
  } catch (err) {
    console.log(err)
    modalStatus.value = 'error'
    modalTitle.value = t('notification.st_error')
    modalBody.value = err?.response?.data?.error || t('notification.was_error')
  } finally {
    controller = null
    openModal.value = true
  }
}

const isOrbitalActive = computed(() => {
  // Special = орбитальная активна (orbital_force_basic = false)
  // Regular = обычная станция активна (orbital_force_basic = true)
  return app.user?.has_orbital_station && !app.user?.orbital_force_basic
})

const switchIconGreen = new URL('@/assets/switch-icon-green.png', import.meta.url).href
const switchIconRed = new URL('@/assets/switch-icon-red.png', import.meta.url).href

const conditionsToMint = computed(() => {
  if (allStations.indexOf(app.user?.station_type) == allStations.length) return false
  if (app.user?.storage_level !== findMaxLevel(app.stations?.storage_configs)) return false
  if (app.user?.generation_level !== findMaxLevel(app.stations?.gen_configs)) return false
  if (app.stationsNft.length && app.user?.current_mint) {
    const incl = app.stationsNft.filter(item => item?.metadata?.name?.toLowerCase() === app?.user?.station_type?.toLowerCase()).length;
    // const incl = app.stationsNft.filter(item => item === app?.user?.current_mint).length;
    return incl >= 2 ? true : false
  }
  return false
})

// async function handleTapRequest() {
//   try {
//     const res = await host.post('tap-energy/');
//     // Оновлюємо дані з сервера, коли вони прийшли
//     if (res.status == 200 && (!app.user?.overheated_until || new Date(app.user?.overheated_until) <= new Date())) {
//       app.setStorage(res.data.storage);
//       app.setPower(res.data.power);
//     }
//   } catch (err) {
//     // Обробка помилок і відкат змін, якщо потрібно
//     console.error("Помилка тапу:", err);

//     if (err?.response?.status == 400 && err.response?.data?.overheated_until) {
//       let overheatDate = new Date(err.response?.data?.overheated_until);
//       let currDate = new Date();
//       if (overheatDate > currDate) {
//         app.setOverheatedUntil(err.response?.data?.overheated_until);
//       } else {
//         openAfterHeat.value = true;
//       }
//       app.setStorage(err?.response?.data?.storage);
//       app.setPower(err?.response?.data?.power);
//     }
//   }
// }

// function increment(event) {
//   if (app.user?.building_until && getTimeRemaining(app.user?.building_until).remain > 0) return
//   if (isJarvis.value.active) return

//   const currentTime = Date.now()
//   if (currentTime - lastClickTime >= 400) {
//     clickCount = 0
//     lastClickTime = currentTime
//   }

//   if (clickCount >= clickLimit || app.power <= 0 || app.storage <= 0) {
//     console.log('Too much clicks or no power or storage');
//     return;
//   }

//   // --- Оптимістичний UI ---
//   clickCount++
//   tg.HapticFeedback.impactOccurred('heavy');
//   const tapValue = +(app.user.kw_per_tap * ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 1.05 : (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) ? 1.1 : 1)).toFixed(4) || 0;

//   // const touches = event.touches
//   // Беремо лише перший дотик
//   if (!app.user?.overheated_until || new Date(app.user?.overheated_until) <= new Date()) {
//     app.addScore(tapValue); // Оптимістично додаємо до рахунку
//     const touch = event.touches[0]
//     // for (let i = 0; i < touches.length; i++) {
//     // const touch = touches[i]
//     const rect = img.value.getBoundingClientRect()
//     const plusOne = document.createElement('div');
//     plusOne.classList.add('plus-one');
//     plusOne.style.position = 'absolute';
//     plusOne.textContent = `+${tapValue}`;
//     plusOne.style.zIndex = 1000;
//     plusOne.style.left = `${touch.clientX}px`;
//     plusOne.style.top = `${touch.clientY - rect.top * 1.1}px`;
//     img.value.parentElement.appendChild(plusOne);
//     setTimeout(() => plusOne.remove(), 1500);
//   }

//   // Асинхронно відправляємо запит на сервер
//   handleTapRequest()
// }

const premiumActive = computed(() => new Date(app.user?.premium_sub_expires) >= new Date())

async function increment(event) {
  if (!ton_address.value) {
    showMeModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }
  if (app.user?.building_until && getTimeRemaining(app.user?.building_until).remain > 0) return
  if (!unlockedWallet.value.bool) return
  if (orbitalStation.value.lock) return
  if (hydroStation.value.lock) return
  if (isJarvis.value.active) return
  // if (isProcessing.value) return
  const isOverheated = app.user?.overheated_until && new Date(app.user.overheated_until) > new Date();
  const timeToClick = allStations.indexOf(app.user?.station_type) >= 1 ? 500 : 250;

  const currentTime = Date.now()
  if (currentTime - lastClickTime.value <= timeToClick) {
    return
  }

  clickCount.value = 0
  lastClickTime.value = currentTime

  if (clickCount.value >= clickLimit || app.power <= 0 || app.storage <= 0) {
    console.log('Too much clicks')
    return
  }

  isProcessing.value = true
  // Беремо лише перший дотик
  const touch = event.touches[0]
  const rect = img.value.getBoundingClientRect()
  const additionalTap = (app.user?.kw_per_tap + app.stations?.eng_configs?.find(el => el?.level == getWorkers.value?.all)?.tap_power - app?.stations?.eng_configs?.find(el => el?.level == getWorkers.value?.simple)?.tap_power)
  const tapValue = +(additionalTap * ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 1.05 : ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 1.1 : 1)).toFixed(4) || 0
  tg.HapticFeedback.impactOccurred('heavy')

  // Оптимістичний UI - одразу показуємо зміни
  if (!isOverheated) {
    clickCount.value++
    // app.addScore(tapValue)
    const plusOne = document.createElement('div')
    plusOne.classList.add('plus-one')
    plusOne.style.position = 'absolute'
    plusOne.textContent = `+${tapValue}`
    plusOne.style.zIndex = 1000
    plusOne.style.left = `${touch.clientX}px`
    plusOne.style.top = `${touch.clientY - rect.top * 1.1}px`
    img.value.parentElement.appendChild(plusOne)
    setTimeout(() => plusOne.remove(), 1500)
  }

  // Асинхронна синхронізація з сервером
  try {
    const res = await host.post('tap-energy/')
    if (res.status == 200) {
      app.setScore(res.data.total_energy)
      app.setStorage(res.data.storage)
      app.setPower(res.data.power)
    }
  } catch (err) {
    console.error("Помилка тапу:", err)
    if (err?.response?.status == 400 && err.response?.data?.overheated_until) {
      let overheatDate = new Date(err.response?.data?.overheated_until)
      let currDate = new Date()

      if (overheatDate > currDate) {
        app.setOverheatedUntil(err.response?.data?.overheated_until)
      } else {
        openAfterHeat.value = true
      }
      app.setScore(err?.response?.data?.total_energy)
      app.setStorage(err?.response?.data?.storage)
      app.setPower(err?.response?.data?.power)
    }
  } finally {
    isProcessing.value = false
  }
}

function getWorkerImg(worker) {
  return new URL(`../assets/${worker}.webp`, import.meta.url).href;
}

const openSwapToken = ref(false)
const handleSwapToken = () => {
  openSwapToken.value = true
}

function getTimeUntil(date) {
  const now = new Date()
  const futureDate = new Date(new Date(date).getTime() + 24 * 60 * 60 * 1000)

  const difference = futureDate - now

  if (difference <= 0) {
    return t('modals.mint_modal.time_expired')
  }

  const hours = Math.floor(difference / (1000 * 60 * 60))
  const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60))

  return t('modals.mint_modal.hours_minutes', { hours, minutes })
}

const responseSwapToken = async (val) => {
  if (val.check) {
    openSwapToken.value = false
    if (!ton_address.value) {
    showMeModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }
    const max = computed(() => Math.floor(app?.user?.energy))
    const available = computed(() => Math.max(0, Math.min(Math.floor(app?.wallet_info?.kw_amount), max.value)))
    const amount = ref(Math.min(available.value, max.value))

    if (amount.value > 0 && amount.value < (app.withdraw_config?.min_kw || 300)) {
    showMeModal(
      'warning',
      t('notification.st_attention'),
      t('notification.min_mint_bal_wallet', { bal: app.withdraw_config?.min_kw || 300, address: ton_address.value?.slice(0, 5) + '...' + ton_address.value?.slice(-5) })
    )
    return
  }

    const user_id = user?.id
    const receiveWallet = ton_address.value
    const reqData = {
      user_id: user_id,
      wallet_address: receiveWallet,
      token_amount: +amount.value,
      token_contract_address: 'EQDSYiFUtMVS9rhBDhbTfP-zbj_uqa69bHv6e5IberQH5n1N',
    }
    try {
      await host
        .post('switch-orbital/', reqData)
        .then(() => {
          const tokens = Math.floor(amount.value * 0.9)
          const time = amount.value < app.withdraw_config?.max_auto_kw ? t('modals.mint_modal.few_minutes') : t('modals.mint_modal.24_hours')
          if(tokens > 0) {
            showMeModal('success', t('notification.st_success'), t('modals.mint_modal.request_accepted', { tokens, time }))
          }
        })
        .catch((e) => {
          let body
          if (e.response.data.error == 'All fields are required') {
            body = t('modals.mint_modal.check_data')
          } else if (e.response.data.error == 'You can only make one withdrawal request per day') {
            body = t('modals.swap_modal', { time: getTimeUntil(app.user?.last_withdrawal_date) })
          } else {
            body = e.response.data.error
          }
          showMeModal('error', t('notification.st_error'), body)
        })
    } catch (e) {
      let body
      if (e.response.data.error == 'All fields are required') {
        body = t('modals.mint_modal.check_data')
      } else if (e.response.data.error == 'You can only make one withdrawal request per day') {
        body = t('modals.swap_modal', { time: getTimeUntil(app.user?.last_withdrawal_date) })
      } else {
        body = e.response.data.error
      }
      showMeModal('error', t('notification.st_error'), body)
    }
  } else {
    openSwapToken.value = false
  }
}

async function startInfoUpdate() {
  if (tabs.openDashboard) {
    updateStopped.value = true
    return
  }

  try {
    // Створюємо масив для всіх промісів
    const promises = [];
    app.initUser()
    // Додаємо запити до масиву, якщо умови виконуються
    if (connectedAddressString.value) {
      promises.push(
        tonapi.get(`accounts/${connectedAddressString.value}/nfts?collection=0:7ea4186758460f6c8bb6e6e335629e4ca8616343ef097ace424f60ebf8e55def`)
      );
      promises.push(host.get("notifications/"));
    }
    if (!Object.keys(app?.availableNftRentals).length) {
      promises.push(host.get("available-nft-rentals/"));
    }
    if (!app?.rentedNfts.length && maxAttempts.value.rent < 3) {
      promises.push(host.get("user-rented-nfts/"));
      maxAttempts.value.rent++;
    }
    if (!app?.rentOutNfts.length && maxAttempts.value.lent < 3) {
      promises.push(host.get("user-lent-nfts/"));
      maxAttempts.value.lent++;
    }

    // Виконуємо всі запити паралельно
    const results = await Promise.allSettled(promises);

    // Обробляємо результати
    let resultIndex = 0;
    if (connectedAddressString.value) {
      const nftResult = results[resultIndex++];
      if (nftResult.status === 'fulfilled' && nftResult.value.status === 200) {
        app.setStationsNft(nftResult.value.data?.nft_items);
      }

      const notificationsResult = results[resultIndex++];
      if (notificationsResult.status === 'fulfilled' && notificationsResult.value.status === 200) {
        const isNotFound = notificationsResult.value.data?.find(el => el.notif_type == 'nft_not_found' && !el.is_read);
        if (isNotFound) {
          craft("notfound", 0, null, null, (app.withdraw_config.engineer_minus == -10 ? 0 : Math.max(1, app.user?.engineer_level - Math.max(0, allStations.indexOf(app.user?.station_type) + app.withdraw_config.engineer_minus))), app.stations?.storage_configs?.[0]?.duration, isNotFound?.id);
        }
      }
    }

    if (!Object.keys(app?.availableNftRentals).length) {
      const availableRentalsResult = results[resultIndex++];
      if (availableRentalsResult.status === 'fulfilled' && availableRentalsResult.value.status === 200) {
        app.setAvailableRental(availableRentalsResult.value.data);
      }
    }

    if (!app?.rentedNfts.length && maxAttempts.value.rent < 3) {
      const rentedNftsResult = results[resultIndex++];
      if (rentedNftsResult.status === 'fulfilled' && rentedNftsResult.value.status === 200) {
        app.setRentedNft(rentedNftsResult.value.data)
        maxAttempts.value.rent++
      } else {
        maxAttempts.value.rent++
      }
    }

    if (!app?.rentOutNfts.length && maxAttempts.value.lent < 3) {
      const rentOutNftsResult = results[resultIndex++];
      if (rentOutNftsResult.status === 'fulfilled' && rentOutNftsResult.value.status === 200) {
        app.setRentOutNfts(rentOutNftsResult.value.data)
        maxAttempts.value.lent++
      } else {
        maxAttempts.value.lent++
      }
    }
  } catch (err) {
    console.log(err)
  } finally {
    controller = null
    infoUpdateTimer = setTimeout(() => startInfoUpdate(), 5000)
  }
}

onMounted(() => {
  asicsIsOpen.setBackground('#141e36')
  document.body.style.background = asicsIsOpen.background
  tg?.setHeaderColor(asicsIsOpen.background)
  startInfoUpdate()
})

watch(
  app,
  () => {
    if (openHeatCheck.value) {
      return
    }
    if (app?.user?.overheated_until) {
      let curr_date = new Date()
      let overheat_date = new Date(app?.user?.overheated_until)
      if (overheat_date <= curr_date) {
        openHeatCheck.value = true
        setTimeout(() => {
          openAfterHeat.value = true
        }, 1000)
      }
    }
    if (isJarvis.value.active && !animationStarted) {
      animationStarted = true
      startAnimation()
    }
  },
  { immediate: true },
)

watch(
  [isProcessing, () => tabs.openDashboard],
  ([newIsProcessing, newDashboard]) => {
    if (
      (newIsProcessing === false && updateStopped.value === true) ||
      (newDashboard === false && updateStopped.value === true)
    ) {
      updateStopped.value = false;
      if (infoUpdateTimer) clearTimeout(infoUpdateTimer);
      startInfoUpdate()
    }
  },
  { immediate: true }
)

onUnmounted(() => {
  if (controller) {
    controller.abort()
  }
  if (infoUpdateTimer) {
    clearTimeout(infoUpdateTimer);
  }
  if (timeRemainingInterval) {
    clearInterval(timeRemainingInterval)
  }
  stopAnimation()
})
</script>

<template>
  <UpgradeModal v-if="openUpgModal" :title="upgModalTitle" :body="upgModalBody" :price="upgModalPrice"
    :kind="upgModalKind" @close="showModal" />
  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
  <InfoModal v-if="openWalletChangeInfo" @close="openWalletChangeInfo = false">
    <template #modal-body>
      {{ t('modals.wallet_change_info.body') }}
    </template>
  </InfoModal>
  <InfoModal v-if="openSwapToken" @close="responseSwapToken">
    <template #modal-body>
      {{ t('modals.swap_token', {
        energyType: t(`modals.energy_types.${app.user?.orbital_is_blue ? 'yellow' : 'blue'}`)
      })
      }}
    </template>
  </InfoModal>
  <MintModal v-if="openMintModal" @close="
    (val) => {
      openMintModal = false
      if (val) {
        modalStatus = val?.status || 'success'
        modalTitle = val?.title
        modalBody = val?.body
        openModal = true
      }
    }
  " />
  <AfterHeatModal v-if="openAfterHeat" @close="responseAfterHeat" />
  <HeatSwitch v-if="openHeatSwitch" @close="responseHeatSwitch" />
  <CraftStationModal v-if="openCraftStation" v-bind="craftParams" @close="craftResponse" />

  <Transition name="fade">
    <div v-if="upgradeIsOpen" class="overlay" @click="upgradeIsOpen = false"></div>
  </Transition>
  <Transition name="slide-up">
    <div v-if="upgradeIsOpen" class="upgrades">
      <div class="scrollable">
        <div class="top-panel">
          <h1>{{
            (app.user.has_orbital_station && activeStation == 'Dyson Sphere') ?
              t(`stations.${'Orbital power plant'}`) :
              (app.user.has_hydro_station && activeStation == 'Nuclear power plant') ?
                t(`stations.${'Hydroelectric power plant'}`) :
                t(`stations.${activeStation}`) }}</h1>
          <button class="close" @click="upgradeIsOpen = false">
            <Exit :width="16" style="color: #fff" />
          </button>
        </div>
        <div class="currencies">
          <div class="ton currency">
            <!-- <Ton :width="22" :height="22" /> -->
            <img src="@/assets/TON.png" width="22px" height="22px" />
            <span>{{ +(+app?.tonBalance / 10 ** 9).toFixed(2) || 0 }}</span>
          </div>
          <div class="coin currency">
            <!-- <TonBitcoin :width="22" :height="22" /> -->
            <img src="@/assets/fBTC.webp" width="22px" height="22px" />
            <span>{{ +(+app.user.tbtc_wallet).toFixed(2) || 0 }}</span>
          </div>
          <div class="energy currency">
            <!-- <Energy :width="22" :height="22" /> -->
            <img v-if="app.user.has_hydro_station || (app.user.has_orbital_station && !app.user.orbital_first_owner)"
              src="@/assets/kW_token.png" width="22px" height="22px" />
            <img v-else src="@/assets/kW.png" width="22px" height="22px" />
            <span>{{ +(+app.user.energy).toFixed(2) || 0 }}</span>
          </div>
        </div>
        <StationSlider @input="setActiveStation" @buystation="
          getUpgModal(
            t('modals.upgrade.buy_station_title'),
            t('modals.upgrade.buy_station_desc'),
            {
              kw: app.stations?.storage_configs?.find(
                (el) =>
                  el?.station_type ==
                  allStations?.[allStations.indexOf(app.user?.station_type) + 1] &&
                  el?.level == 1,
              )?.price_kw,
              tbtc: app.stations?.storage_configs?.find(
                (el) =>
                  el?.station_type ==
                  allStations?.[allStations.indexOf(app.user?.station_type) + 1] &&
                  el?.level == 1,
              )?.price_tbtc,
            },
            'station',
          )" @mintstation="() => {
            if (!app.stationsNft.length && !app.user?.current_mint) {
              craft(
                'mint',
                app.stations?.storage_configs?.find((el) => el?.station_type == allStations?.[allStations.indexOf(app.user?.station_type) + 1] && el?.level == 1)?.price_kw,
                app.stations?.storage_configs?.find((el) => el?.station_type == allStations?.[allStations.indexOf(app.user?.station_type) + 1] && el?.level == 1)?.price_tbtc,
                null,
                null,
                app.stations?.storage_configs?.find((el) => el?.station_type == allStations?.[allStations.indexOf(app.user?.station_type) + 1] && el?.level == 1)?.duration,
                null
              )
            } else {
              mintableIsOpen = true
            }
          }" />
        <div class="station-statistic">
          <div class="storage">
            <img src="@/assets/storage.webp" width="10px" />
            <span>{{
              activeStation == app.user.station_type
                ? `${+(+app.user?.storage_limit).toFixed(2) || 0}kW`
                : allStations.indexOf(activeStation) > allStations.indexOf(app.user.station_type)
                  ? `${+(+app.stations?.storage_configs?.find(
                    (el) => el.station_type == activeStation && el.level == 1,
                  )?.storage_limit).toFixed(2) || 0
                  }kW`
                  : `${+(+app.stations?.storage_configs?.find(
                    (el) => el.station_type == activeStation && el.level == 3,
                  )?.storage_limit).toFixed(2) || 0
                  }kW`
            }}</span>
          </div>
          <div class="generation">
            <img src="@/assets/generation-upg_new.webp" width="10px" />
            <span>{{
              activeStation == app.user.station_type
                ? `${+app.user?.generation_rate || 0} ${t('common.per_h', { value: 'kW' })}`
                : allStations.indexOf(activeStation) > allStations.indexOf(app.user.station_type)
                  ? `${app.stations?.gen_configs?.find(
                    (el) => el?.station_type == activeStation && el.level == 1,
                  )?.generation_rate || 0
                  } ${t('common.per_h', { value: 'kW' })}`
                  : `${app.stations?.gen_configs?.find(
                    (el) => el.station_type == activeStation && el.level == 3,
                  )?.generation_rate || 0
                  } ${t('common.per_h', { value: 'kW' })}`
            }}</span>
          </div>
          <div class="time">
            <img src="@/assets/fill.webp" width="10px" />
            <span>{{
              activeStation == app.user.station_type
                ? `${Math.round(app.user?.storage_limit / app.user?.generation_rate) || 0}${t('common.h')}`
                : allStations.indexOf(activeStation) > allStations.indexOf(app.user.station_type)
                  ? `${Math.round(
                    app.stations?.storage_configs?.find(
                      (el) => el.station_type == activeStation && el.level == 1,
                    )?.storage_limit /
                    app.stations?.gen_configs?.find(
                      (el) => el?.station_type == activeStation && el.level == 1,
                    )?.generation_rate,
                  ) || 0
                  }${t('common.h')}`
                  : `${Math.round(
                    app.stations?.storage_configs?.find(
                      (el) => el.station_type == activeStation && el.level == 3,
                    )?.storage_limit /
                    app.stations?.gen_configs?.find(
                      (el) => el.station_type == activeStation && el.level == 3,
                    )?.generation_rate,
                  ) || 0
                  }${t('common.h')}`
            }}</span>
          </div>
          <div class="minting">
            <img src="@/assets/mintable.png" width="10px" />
            <span>{{
              allStations?.indexOf(activeStation) > 3 && app.stationsNft.some(el => el.metadata.name?.toLowerCase() ==
                activeStation?.toLowerCase() && el.address == app.user?.current_mint) ? t('modals.upgrade.minted_nft') :
                allStations?.indexOf(activeStation) > 3 ? t('modals.upgrade.mintable_nft') :
                  t('modals.upgrade.unmintable_nft')}}</span>
          </div>
        </div>
        <div class="power-panel">
          <div class="power-progress">
            <div class="labels">
              <div class="left-side">
                <Power :width="18" :height="18" />
                <span>{{ t('modals.upgrade.power') }}</span>
              </div>
              <span>{{ +(+app.user.power).toFixed(2) || 0 }}%</span>
            </div>
            <div class="shell">
              <div class="bar" :style="{ width: (app.user.power ?? 0) + '%' }"></div>
            </div>
          </div>
          <button class="repair-btn" @click="
            getUpgModal(
              t('modals.upgrade.station_repair_title'),
              t('modals.upgrade.station_repair_desc'),
              {
                kw:
                  (100 - +app?.user?.power) *
                  +app.stations?.repair_configs?.find(
                    (el) => el?.station_type == app.user?.station_type,
                  )?.price_kw || null,
                tbtc:
                  (100 - +app?.user?.power) *
                  +app.stations?.repair_configs?.find(
                    (el) => el?.station_type == app.user?.station_type,
                  )?.price_tbtc || null,
              },
              'repair',
            )
            ">
            {{ t('modals.upgrade.repair') }}
          </button>
        </div>
        <div class="upgrade-station-panel">
          <div class="upgrade-card">
            <div v-if="
              app.user.has_orbital_station ||
              app.user.has_hydro_station ||
              app.user.storage_level < 3 ||
              allStations.indexOf(app.user.station_type) == allStations.length - 1" class="level"
              :class="{ mint: allStations?.indexOf(app?.user?.station_type) > 3 }">
              {{ t('common.lvl') }} {{ app.user.storage_level }}
            </div>
            <div
              v-if="!app.user.has_hydro_station && !app.user.has_orbital_station && app.user.storage_level == 3 && allStations.indexOf(app.user.station_type) !== allStations.length - 1"
              class="level-upgrade-station">
              {{ t('modals.upgrade.next_station') }}
            </div>
            <div class="service-title">
              {{
                app.user.storage_level == 3 && !app.user.has_hydro_station && !app.user.has_orbital_station &&
                  allStations.indexOf(app.user.station_type) !== allStations.length - 1
                  ? t(`stations.${allStations?.[allStations.indexOf(app.user?.station_type) + 1]}`)
                  : t('modals.upgrade.upg_station')
              }}
            </div>
            <div class="middle-sect">
              <div class="light-line"></div>
              <div class="picture">
                <!-- <NewBase :width="66" :height="66" /> -->
                <img :src="imagePathCard" width="66px" height="66px" />
              </div>
              <div v-if="app.user?.storage_level < findMaxLevel(app.stations?.storage_configs)"
                class="service-title-loc">
                {{ t('modals.upgrade.incr_capacity') }}
              </div>
              <div
                v-if="app.user?.storage_level == findMaxLevel(app.stations?.storage_configs) && !app.user.has_hydro_station && !app.user.has_orbital_station"
                class="service-title-loc">
                {{ t('modals.upgrade.upd_station') }}
              </div>
              <div v-if="app.user.has_hydro_station || app.user.has_orbital_station" class="service-title-loc spec">
                {{ t('modals.upgrade.spec') }}
              </div>
              <div
                v-if="app.user?.storage_level !== findMaxLevel(app.stations?.storage_configs) || app.user.has_hydro_station || app.user.has_orbital_station"
                class="increase-group">
                <Storage :width="10" />
                <span class="from">{{ +app.user.storage_limit }}</span>
                <ArrowRight v-if="
                  allStations.findIndex((el) => app?.user?.station_type) <=
                  allStations.length - 1 !==
                  app?.user?.station_type &&
                  app?.user?.storage_level < findMaxLevel(app.stations?.storage_configs)
                " :width="10" class="mx-[.2rem]" />
                <Storage v-if="
                  allStations.findIndex((el) => app?.user?.station_type) <=
                  allStations.length - 1 !==
                  app?.user?.station_type &&
                  app?.user?.storage_level < findMaxLevel(app.stations?.storage_configs)
                " :width="10" />
                <span v-if="app.user?.storage_level < findMaxLevel(app.stations?.storage_configs)" class="to">{{
                  app.stations.storage_configs?.find(
                    (el) =>
                      el?.station_type == app?.user?.station_type &&
                      el?.level == app?.user?.storage_level + 1,
                  )?.storage_limit || ''
                }}</span>
                <!-- <span v-if="app.user?.storage_level == findMaxLevel(app.stations?.storage_configs)" class="to">{{
                  app.stations.storage_configs?.find(el =>
                    el?.station_type == allStations?.[allStations.indexOf(app?.user?.station_type) + 1] && el?.level ==
                    1)?.storage_limit
                  || ""
                }}</span> -->
              </div>
            </div>
            <div
              v-if="app.user?.storage_level < findMaxLevel(app.stations?.storage_configs) && !app.user.has_hydro_station && !app.user.has_orbital_station"
              class="upgrade-price">
              <div class="upgrade-price-item col-span-2">
                <div class="flex items-center justify-center gap-1">
                  <img src="@/assets/kW.png" v-if="
                    app.stations?.storage_configs?.find(
                      (el) =>
                        el?.station_type == app.user?.station_type &&
                        el?.level == app.user?.storage_level + 1
                    )?.price_kw > 0
                  " width="10px" height="10px" />
                  <span class="energy">{{
                    app?.stations?.storage_configs?.find(
                      (el) =>
                        el?.station_type == app?.user?.station_type &&
                        el?.level == app?.user?.storage_level + 1
                    )?.price_kw || ''
                  }}</span>
                </div>
                <div class="flex items-center justify-center gap-1">
                  <img src="@/assets/fBTC.webp" v-if="
                    app.stations?.storage_configs?.find(
                      (el) =>
                        el?.station_type == app.user?.station_type &&
                        el?.level == app.user?.storage_level + 1
                    )?.price_tbtc > 0
                  " width="10px" />
                  <span class="tbtc">{{
                    app.stations?.storage_configs?.find(
                      (el) =>
                        el?.station_type == app.user?.station_type &&
                        el?.level == app.user?.storage_level + 1
                    )?.price_tbtc || ''
                  }}</span>
                </div>
              </div>
              <div class="upgrade-price-item col-span-2">
                <img src="@/assets/time.webp" v-if="
                  app.stations?.storage_configs?.find(
                    (el) =>
                      el?.station_type == app.user?.station_type &&
                      el?.level == app.user?.storage_level + 1
                  )?.duration !== null
                " width="10px" />
                <span class="tbtc">{{
                  convertTimeFormat(app.stations?.storage_configs?.find(
                    (el) =>
                      el?.station_type == app.user?.station_type &&
                      el?.level == app.user?.storage_level + 1
                  )?.duration) || ''
                }}</span>
              </div>
            </div>
            <div v-if="
              !app.user.has_orbital_station &&
              !app.user.has_hydro_station &&
              app.user?.storage_level == findMaxLevel(app.stations?.storage_configs) &&
              app.user?.station_type !== allStations?.[allStations.length - 1]
            " class="upgrade-price">
              <div class="upgrade-price-item col-span-2">
                <div class="flex items-center justify-center gap-1">
                  <img src="@/assets/kW.png" v-if="
                    app.stations?.storage_configs?.find(
                      (el) =>
                        el?.station_type ==
                        allStations?.[allStations.indexOf(app.user?.station_type) + 1] &&
                        el?.level == 1
                    )?.price_kw > 0
                  " width="10px" height="10px" />
                  <span class="energy">{{
                    app.stations?.storage_configs?.find(
                      (el) =>
                        el?.station_type ==
                        allStations?.[allStations.indexOf(app.user?.station_type) + 1] &&
                        el?.level == 1
                    )?.price_kw || ''
                  }}</span>
                </div>
                <div class="flex items-center justify-center gap-1">
                  <img src="@/assets/fBTC.webp" v-if="
                    app.stations?.storage_configs?.find(
                      (el) =>
                        el?.station_type ==
                        allStations?.[allStations.indexOf(app.user?.station_type) + 1] &&
                        el?.level == 1
                    )?.price_tbtc > 0
                  " width="10px" />
                  <span class="tbtc">{{
                    app.stations?.storage_configs?.find(
                      (el) =>
                        el?.station_type ==
                        allStations?.[allStations.indexOf(app.user?.station_type) + 1] &&
                        el?.level == 1
                    )?.price_tbtc || ''
                  }}</span>
                </div>
              </div>
              <div class="upgrade-price-item col-span-2">
                <img src="@/assets/time.webp" v-if="
                  app.stations?.storage_configs?.find(
                    (el) =>
                      el?.station_type ==
                      allStations?.[allStations.indexOf(app.user?.station_type) + 1] &&
                      el?.level == 1
                  )?.duration !== null
                " width="10px" />
                <span class="tbtc">{{
                  convertTimeFormat(app.stations?.storage_configs?.find(
                    (el) =>
                      el?.station_type ==
                      allStations?.[allStations.indexOf(app.user?.station_type) + 1] &&
                      el?.level == 1
                  )?.duration) || ''
                }}</span>
              </div>
            </div>
            <button v-if="app.user?.building_until && getTimeRemaining(app.user?.building_until).remain > 0"
              class="upg-btn-unactive"> {{ getTimeRemaining(app.user?.building_until).time }}</button>
            <button v-if="app.user?.storage_level < findMaxLevel(app.stations?.storage_configs) && (!app.user?.building_until || getTimeRemaining(app.user?.building_until).remain <= 0)
            " class="upg-btn" @click="upgrade('storage')">
              {{ t('common.upg') }}
            </button>
            <button v-if="
              app.user?.storage_level == findMaxLevel(app.stations?.storage_configs) &&
              app.user?.generation_level == findMaxLevel(app.stations?.gen_configs) &&
              app.user?.station_type !== allStations?.[allStations.length - 1] &&
              allStations?.indexOf(app.user?.station_type) >= 3 &&
              (!app.user?.building_until || getTimeRemaining(app.user?.building_until).remain <= 0)
            " class="upg-btn"
              :class="{ 'mint': (app.stationsNft.length && app.user?.current_mint) || allStations?.indexOf(app.user?.station_type) == 3, 'upg-btn-unactive': (!app.stationsNft.length || !app.user?.current_mint) && allStations?.indexOf(app.user?.station_type) !== 3 }"
              @click="() => {
                if (allStations?.indexOf(app.user?.station_type) == 3) {
                  craft(
                    'mint',
                    app.stations?.storage_configs?.find((el) => el?.station_type == allStations?.[allStations.indexOf(app.user?.station_type) + 1] && el?.level == 1)?.price_kw,
                    app.stations?.storage_configs?.find((el) => el?.station_type == allStations?.[allStations.indexOf(app.user?.station_type) + 1] && el?.level == 1)?.price_tbtc,
                    null,
                    null,
                    app.stations?.storage_configs?.find((el) => el?.station_type == allStations?.[allStations.indexOf(app.user?.station_type) + 1] && el?.level == 1)?.duration,
                    null
                  )
                }
                if (app.stationsNft.length && app.user?.current_mint) {
                  mintableIsOpen = true
                }
              }
              ">
              {{ allStations?.indexOf(app.user?.station_type) >= 4 ? t('common.craft') : t('common.mint') }}
            </button>
            <button v-if="
              app.user?.storage_level == findMaxLevel(app.stations?.storage_configs) &&
              app.user?.generation_level == findMaxLevel(app.stations?.gen_configs) &&
              app.user?.station_type !== allStations?.[allStations.length - 1] &&
              allStations.indexOf(app.user?.station_type) < 3 &&
              (!app.user?.building_until || getTimeRemaining(app.user?.building_until).remain <= 0)
            " class="upg-btn" @click="
              getUpgModal(
                t('modals.upgrade.buy_station_title'),
                t('modals.upgrade.buy_station_desc'),
                {
                  kw: app.stations?.storage_configs?.find(
                    (el) =>
                      el?.station_type ==
                      allStations?.[allStations.indexOf(app.user?.station_type) + 1] &&
                      el?.level == 1,
                  )?.price_kw,
                  tbtc: app.stations?.storage_configs?.find(
                    (el) =>
                      el?.station_type ==
                      allStations?.[allStations.indexOf(app.user?.station_type) + 1] &&
                      el?.level == 1,
                  )?.price_tbtc,
                },
                'station',
              )
              ">
              {{ t('common.buy') }}
            </button>
            <button v-if="
              app.user?.storage_level == findMaxLevel(app.stations?.storage_configs) &&
              app.user.generation_level < findMaxLevel(app.stations?.gen_configs) &&
              app.user?.station_type !== allStations?.[allStations.length - 1] &&
              (!app.user?.building_until || getTimeRemaining(app.user?.building_until).remain <= 0)
            " class="upg-btn-unactive" @click="
              () => {
                modalStatus = 'warning'
                modalTitle = t('notification.st_attention')
                modalBody = t('notification.gen_upd_to_3')
                openModal = true
              }
            ">
              {{ t('common.upg') }}
            </button>
            <button v-if="
              !app.user.has_orbital_station &&
              !app.user.has_hydro_station &&
              app.user?.station_type == allStations?.[allStations.length - 1] &&
              app.user?.storage_level == findMaxLevel(app.stations?.storage_configs)
            " class="upg-btn-max">
              {{ t('common.maximum') }}
            </button>
            <button v-else-if="app.user.has_hydro_station || app.user.has_orbital_station" class="upg-btn-unactive">
              {{ t('common.unavailable') }}
            </button>
          </div>
          <div class="upgrade-card">
            <div class="level" :class="{ mint: allStations?.indexOf(app?.user?.station_type) > 3 }">{{ t('common.lvl')
              }} {{
                app.user.generation_level }}</div>
            <div class="service-title">{{ t('modals.upgrade.incr_gen') }}</div>
            <div class="middle-sect">
              <div class="light-line"></div>
              <div class="picture">
                <img src="@/assets/generation-upg_new.webp" width="66px" height="66px" />
              </div>
              <div class="service-title-loc">{{ t('modals.upgrade.gen_speed') }}</div>
              <div class="increase-group">
                <img
                  v-if="app.user.has_hydro_station || (app.user.has_orbital_station && !app.user.orbital_first_owner)"
                  src="@/assets/kW_token.png" width="10px" height="10px" />
                <img v-else src="@/assets/kW.png" width="10px" height="10px" />
                <span class="from">{{ +app.user.generation_rate }} {{ t('common.per_h', { value: "kW" }) }}</span>
                <ArrowRight v-if="app.user.generation_level < findMaxLevel(app.stations?.gen_configs)" :width="10"
                  class="mx-[.2rem]" />
                <img src="@/assets/kW.png" v-if="app.user.generation_level < findMaxLevel(app.stations?.gen_configs)"
                  width="10px" height="10px" />
                <span v-if="app.user.generation_level < findMaxLevel(app.stations?.gen_configs)" class="to">{{
                  +app.stations?.gen_configs?.find(
                    (el) =>
                      el?.station_type == app.user?.station_type &&
                      el?.level == +app.user?.generation_level + 1,
                  )?.generation_rate || ''
                }}
                  {{ t('common.per_h', { value: "kW" }) }}</span>
              </div>
            </div>
            <div v-if="app.user.generation_level < findMaxLevel(app.stations?.gen_configs)" class="upgrade-price">
              <!-- <Energy v-if="app.stations?.gen_configs?.find(el => el?.station_type == app.user?.station_type &&
                el?.level == app.user?.generation_level + 1)?.price_kw > 0" :width="10" /> -->
              <div class="upgrade-price-item col-span-2">
                <div class="flex items-center justify-center gap-1">
                  <img src="@/assets/kW.png" v-if="
                    app.stations?.gen_configs?.find(
                      (el) =>
                        el?.station_type == app.user?.station_type &&
                        el?.level == app.user?.generation_level + 1,
                    )?.price_kw > 0
                  " width="10px" height="10px" />
                  <span class="energy">{{
                    app.stations?.gen_configs?.find(
                      (el) =>
                        el?.station_type == app.user?.station_type &&
                        el?.level == app.user?.generation_level + 1,
                    )?.price_kw || ''
                  }}</span>
                </div>
                <div class="flex items-center justify-center gap-1">
                  <img src="@/assets/fBTC.webp" v-if="
                    app.stations?.gen_configs?.find(
                      (el) =>
                        el?.station_type == app.user?.station_type &&
                        el?.level == app.user?.generation_level + 1,
                    )?.price_tbtc > 0
                  " width="10px" />
                  <span class="tbtc">{{
                    app.stations?.gen_configs?.find(
                      (el) =>
                        el?.station_type == app.user?.station_type &&
                        el?.level == app.user?.generation_level + 1,
                    )?.price_tbtc || ''
                  }}</span>
                </div>
              </div>
              <div class="upgrade-price-item col-span-2">
                <img src="@/assets/time.webp" v-if="
                  app?.gen_config?.find(
                    (el) =>
                      el?.station_type == app.user?.station_type &&
                      el?.level == app.user?.generation_level + 1
                  )?.duration !== null
                " width="10px" />
                <span class="tbtc">{{
                  convertTimeFormat(app?.gen_config?.find(
                    (el) =>
                      el?.station_type == app.user?.station_type &&
                      el?.level == app.user?.generation_level + 1
                  )?.duration) || ''
                }}</span>
              </div>
            </div>
            <button v-if="app.user?.building_until && getTimeRemaining(app.user?.building_until).remain > 0"
              class="upg-btn-unactive"> {{ getTimeRemaining(app.user?.building_until).time }}</button>
            <button v-if="app.user?.generation_level < findMaxLevel(app.stations?.gen_configs) && (!app.user?.building_until || getTimeRemaining(app.user?.building_until).remain <= 0)
            " class="upg-btn" @click="upgrade('generation')">
              {{ t('common.upg') }}
            </button>
            <button v-if="
              app.user?.generation_level == findMaxLevel(app.stations?.gen_configs) &&
              app.user?.station_type !== allStations?.[allStations.length - 1]
            " class="upg-btn-unactive" @click="
              () => {
                modalStatus = 'warning'
                modalTitle = 'Внимание'
                modalBody = 'Улучшите станицию для возможности улучшения генерации'
                openModal = true
              }
            ">
              {{ t('common.upg') }}
            </button>
            <button v-if="
              !app.user.has_orbital_station &&
              !app.user.has_hydro_station &&
              app.user?.station_type == allStations?.[allStations.length - 1] &&
              app.user?.generation_level == findMaxLevel(app.stations?.gen_configs)
            " class="upg-btn-max">
              {{ t('common.maximum') }}
            </button>
            <button v-else-if="app.user.has_hydro_station || app.user.has_orbital_station" class="upg-btn-unactive">
              {{ t('common.maximum') }}
            </button>
          </div>
          <div class="upgrade-card" :class="{ 'stars-card': app.user.engineer_level >= 50 }">
            <div class="level"
              :class="{ 'stars-level': app.user.engineer_level >= 50, mint: app.user.has_hydro_station || app.user.has_orbital_station }">
              {{ t('common.lvl') }} {{ app.user.engineer_level }}
            </div>
            <div class="service-title">{{ t('modals.upgrade.hire_eng') }}</div>
            <div class="middle-sect">
              <div class="light-line"></div>
              <div class="picture">
                <img v-if="app.user.engineer_level < 50" src="@/assets/engineer.webp" width="66px" height="66px" />
                <img v-if="app.user.engineer_level >= 50" src="@/assets/stars_eng.png" width="66px" height="66px" />
              </div>
              <div class="service-title-loc">{{ t('modals.upgrade.eff') }}</div>
              <div class="increase-group">
                <!-- <Engineer :width="10" /> -->
                <img v-if="app.user.engineer_level < 50" src="@/assets/engineer.webp" width="10px" height="10px" />
                <img v-if="app.user.engineer_level >= 50" src="@/assets/stars_eng.png" width="10px" height="10px" />
                <span class="from">{{ app.user.engineer_level }}</span>
                <ArrowRight
                  v-if="app.user?.engineer_level < findMaxLevel(app.stations?.eng_configs) && !app.user.has_hydro_station && !app.user.has_orbital_station"
                  :width="10" class="mx-[.2rem]" />
                <!-- <Engineer v-if="app.user?.engineer_level < findMaxLevel(app.stations?.eng_configs)" :width="10" /> -->
                <img v-if="
                  !app.user.has_orbital_station &&
                  !app.user.has_hydro_station &&
                  app.user.engineer_level < 49 &&
                  app.user?.engineer_level < findMaxLevel(app.stations?.eng_configs)
                " src="@/assets/engineer.webp" width="10px" height="10px" />
                <img v-if="
                  !app.user.has_orbital_station &&
                  !app.user.has_hydro_station &&
                  app.user.engineer_level >= 49 &&
                  app.user?.engineer_level < findMaxLevel(app.stations?.eng_configs)
                " src="@/assets/stars_eng.png" width="10px" height="10px" />
                <span
                  v-if="app.user?.engineer_level < findMaxLevel(app.stations?.eng_configs) && !app.user.has_hydro_station && !app.user.has_orbital_station"
                  class="to">{{
                    app.stations?.eng_configs?.find(
                      (el) => el?.level == app.user?.engineer_level + 1,
                    )?.level || ''
                  }}</span>
              </div>
            </div>
            <div
              v-if="app.user?.engineer_level < findMaxLevel(app.stations?.eng_configs) && !app.user.has_hydro_station && !app.user.has_orbital_station"
              class="upgrade-price">
              <div class="upgrade-price-item col-span-2">
                <img src="@/assets/kW_token.png" v-if="
                  (app.user.has_hydro_station || (app.user.has_orbital_station && !app.user.orbital_first_owner)) &&
                  app.stations?.eng_configs?.find(
                    (el) => el?.level == app.user?.engineer_level + 1,
                  )?.hire_cost > 0 &&
                  app.stations?.eng_configs?.find(
                    (el) => el?.level == app.user?.engineer_level + 1,
                  )?.level < 50
                " width="10px" height="10px" />
                <img src="@/assets/kW.png" v-if="
                  (!app.user.has_hydro_station || (app.user.has_orbital_station && app.user.orbital_first_owner)) &&
                  app.stations?.eng_configs?.find(
                    (el) => el?.level == app.user?.engineer_level + 1,
                  )?.hire_cost > 0
                " width="10px" height="10px" />
                <span class="energy" v-if="
                  !app.user.has_orbital_station &&
                  !app.user.has_hydro_station &&
                  app.stations?.eng_configs?.find(
                    (el) => el?.level == app.user?.engineer_level + 1,
                  )?.hire_cost > 0">{{
                    app.stations?.eng_configs?.find((el) => el?.level == app.user?.engineer_level + 1)
                      ?.hire_cost || ''
                  }}</span>
                <span class="energy" v-if="
                  !app.user.has_orbital_station &&
                  !app.user.has_hydro_station &&
                  app.stations?.eng_configs?.find(
                    (el) => el?.level == app.user?.engineer_level + 1,
                  )?.hire_cost > 0 &&
                  app.stations?.eng_configs?.find(
                    (el) => el?.level == app.user?.engineer_level + 1,
                  )?.hire_cost_stars > 0">{{ t('common.or') }}</span>
                <img src="@/assets/stars.png" v-if="
                  app.stations?.eng_configs?.find(
                    (el) => el?.level == app.user?.engineer_level + 1,
                  )?.hire_cost_stars > 0
                " width="10px" height="10px" />
                <span class="energy">{{
                  app.stations?.eng_configs?.find((el) => el?.level == app.user?.engineer_level + 1)
                    ?.hire_cost_stars || ''
                }}</span>
              </div>
            </div>
            <button
              v-if="app.user?.engineer_level < findMaxLevel(app.stations?.eng_configs) && !app.user.has_hydro_station && !app.user.has_orbital_station"
              class="upg-btn" :class="{ 'stars-btn': app.user.engineer_level >= 49 }" @click="
                getUpgModal(
                  t('modals.upgrade.hire_eng'),
                  t('modals.upgrade.hire_eng_desc'),
                  {
                    kw: app.stations?.eng_configs?.find(
                      (el) => el?.level == app.user?.engineer_level + 1,
                    )?.hire_cost,
                    tbtc: null,
                    stars: app.stations?.eng_configs?.find(
                      (el) => el?.level == app.user?.engineer_level + 1,
                    )?.hire_cost_stars
                  },
                  'engineer',
                )
                ">
              {{ t('common.upg') }}
            </button>
            <button v-if="
              !app.user.has_orbital_station &&
              !app.user.has_hydro_station &&
              app.user?.engineer_level < findMaxLevel(app.stations?.eng_configs) &&
              app.user?.energy <
              app.stations?.eng_configs?.find(
                (el) =>
                  el?.station_type == app.user?.station_type &&
                  el?.level == app.user?.engineer_level + 1,
              )?.hire_cost
            " class="upg-btn-unactive">
              {{ t('common.upg') }}
            </button>
            <button
              v-if="app.user?.engineer_level == findMaxLevel(app.stations?.eng_configs) && !app.user.has_hydro_station && !app.user.has_orbital_station"
              class="upg-btn-max">
              {{ t('common.maximum') }}
            </button>
            <button v-if="app.user.has_hydro_station || app.user.has_orbital_station" class="upg-btn-unactive">
              {{ t('common.unavailable') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Transition>

  <Transition name="slide-up">
    <div v-if="mintableIsOpen" class="mintable">
      <div class="scrollable">
        <div class="top-panel">
          <h1>{{ t(`stations.${allStations?.[allStations.indexOf(app.user.station_type) + 1]}`) }}</h1>
          <button class="close" @click="mintableIsOpen = false">
            <Exit :width="16" style="color: #fff" />
          </button>
        </div>
        <div class="currencies">
          <div class="ton currency">
            <img src="@/assets/TON.png" width="22px" height="22px" />
            <span>{{ +(+app?.tonBalance / 10 ** 9).toFixed(2) || 0 }}</span>
          </div>
          <div class="coin currency">
            <img src="@/assets/fBTC.webp" width="22px" height="22px" />
            <span>{{ +(+app.user.tbtc_wallet).toFixed(2) || 0 }}</span>
          </div>
          <div class="energy currency">
            <img src="@/assets/kW_token.png" width="22px" height="22px" />
            <span>{{ +(+app.user.energy).toFixed(2) || 0 }}</span>
          </div>
        </div>
        <div class="mint-cards">
          <div class="card">
            <h1>{{ t('modals.mintable.curr_progress') }}</h1>
            <div class="content">
              <h1>{{ t(`stations.${app.user.station_type}`) }}</h1>
              <div class="station-nft">
                <img :src="imagePath" alt="station" />
                <span class="level">{{ t('common.lvl').toUpperCase() }} {{ app.user?.storage_level }}</span>
              </div>
              <div class="conditions">
                <img v-if="app.user?.storage_level == findMaxLevel(app.stations?.storage_configs)"
                  src="@/assets/green-pin.png" :width="12" />
                <img v-if="app.user?.storage_level !== findMaxLevel(app.stations?.storage_configs)"
                  src="@/assets/red-pin.png" :width="12" />
                <span v-if="app.user?.storage_level == findMaxLevel(app.stations?.storage_configs)">{{
                  t('modals.mintable.cond_met') }}</span>
                <span v-if="app.user?.storage_level !== findMaxLevel(app.stations?.storage_configs)">{{
                  t('modals.mintable.need_upg') }}</span>
              </div>
            </div>
          </div>
          <img src="@/assets/plus.png" :width="20" alt="plus" />
          <div class="card">
            <h1>{{ t('modals.mintable.needed_nft') }}</h1>
            <div class="content">
              <h1>{{ t(`stations.${app.user.station_type}`) }}</h1>
              <div class="station-nft">
                <div v-if="!conditionsToMint" class="undefinable">
                  <button class="get-gems" @click="
                    () => {
                      tg?.openLink('https://getgems.io/collection/EQB-pBhnWEYPbIu25uM1Yp5MqGFjQ-8Jes5CT2Dr-OVd705u')
                    }
                  ">
                    {{ t('modals.mintable.buy_on') }}<label class="flex justify-center items-center gap-1">GetGems<img
                        src="@/assets/get-gems.png" width="14px" height="14px" alt="icon" /></label>
                  </button>
                  <button class="craft-new"
                    @click="craft('renew', 0, null, null, (app.withdraw_config.engineer_minus == -10 ? 0 : Math.max(1, app.user?.engineer_level - Math.max(0, allStations.indexOf(app.user?.station_type) + app.withdraw_config.engineer_minus))), app.stations?.storage_configs?.[0]?.duration, null)">
                    {{ t('modals.mintable.build_new') }}</button>
                </div>
                <img :src="imagePath" alt="station" />
                <span class="level">LVL {{ app.user?.storage_level }}</span>
              </div>
              <div class="conditions">
                <img v-if="conditionsToMint" src="@/assets/green-pin.png" :width="12" />
                <img v-if="!conditionsToMint" src="@/assets/red-pin.png" :width="12" />
                <span v-if="conditionsToMint">{{ t('modals.mintable.nft_detected') }}</span>
                <span v-if="!conditionsToMint">{{ t('modals.mintable.nft_undetected') }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="condition-banner">
          <h1>{{ t('modals.mintable.terms') }}</h1>
          <span>{{ t('modals.mintable.terms_text', {
            station_new: t(`stations.${allStations?.[allStations.indexOf(app.user.station_type) + 1]}`),
            station_old: t(`stations.${app.user.station_type}`)
          }) }}</span>
        </div>
        <div class="mint-options">
          <h2 class="title">
            {{ t('modals.mintable.create_price') }} {{
              t(`stations.${allStations?.[allStations.indexOf(app.user.station_type) + 1]}`) ||
              ''
            }}
          </h2>
          <div class="mint-grid">
            <div class="item">
              <img src="@/assets/kW.png" :width="25" alt="icon" />
              <div class="data-field">
                <label class="kw">{{ t('modals.mintable.need', { value: "kW" }) }}</label>
                <span class="kw">{{app.stations?.storage_configs?.find((el) => el?.station_type ==
                  allStations?.[allStations.indexOf(app.user?.station_type) + 1] && el?.level == 1)?.price_kw}}</span>
              </div>
            </div>
            <div class="item">
              <img src="@/assets/fBTC.webp" :width="25" alt="icon" />
              <div class="data-field">
                <label class="tbtc">{{ t('modals.mintable.need', { value: "fBTC" }) }}</label>
                <span class="tbtc">{{app.stations?.storage_configs?.find((el) => el?.station_type ==
                  allStations?.[allStations.indexOf(app.user?.station_type) + 1] && el?.level == 1)?.price_tbtc}}</span>
              </div>
            </div>
            <div class="item col-span-2">
              <img src="@/assets/time.webp" :width="25" alt="icon" />
              <div class="data-field">
                <label>{{ t('modals.mintable.create_time') }}</label>
                <span>{{convertTimeFormat(app.stations?.storage_configs?.find((el) => el?.station_type ==
                  allStations?.[allStations.indexOf(app.user?.station_type) + 1] && el?.level == 1)?.duration)}}</span>
              </div>
            </div>
            <div class="item col-span-2">
              <button class="mint-btn" @click="
                craft(
                  'mint',
                  app.stations?.storage_configs?.find((el) => el?.station_type == allStations?.[allStations.indexOf(app.user?.station_type) + 1] && el?.level == 1)?.price_kw,
                  app.stations?.storage_configs?.find((el) => el?.station_type == allStations?.[allStations.indexOf(app.user?.station_type) + 1] && el?.level == 1)?.price_tbtc,
                  app.user?.station_type,
                  null,
                  app.stations?.storage_configs?.find((el) => el?.station_type == allStations?.[allStations.indexOf(app.user?.station_type) + 1] && el?.level == 1)?.duration,
                  null
                )" :disabled="!conditionsToMint">
                {{ conditionsToMint ? t('modals.mintable.craft_nft') : t('modals.mintable.cond_not_met') }}
              </button>
            </div>
            <div class="item col-span-2 !gap-0">
              <h2 class="title">{{ t('modals.mintable.current') }}</h2>
              <h2 class="title">{{ t('modals.mintable.creating') }}</h2>
            </div>
            <div class="item">
              <img src="@/assets/storage.webp" :width="25" alt="icon" />
              <div class="data-field">
                <label>{{ t('modals.mintable.storage', { value: "kW" }) }}</label>
                <span>{{ +(+app.user?.storage_limit).toFixed(2) || 0 }}</span>
              </div>
            </div>
            <div class="item">
              <div class="w-[25px]"></div>
              <div class="data-field">
                <label class="need">{{ t('modals.mintable.storage', { value: "kW" }) }}</label>
                <span class="need">{{+(+app.stations?.storage_configs?.find((el) => el.station_type ==
                  allStations?.[allStations.indexOf(app.user?.station_type) + 1] &&
                  el.level == 1)?.storage_limit).toFixed(2) || 0}}</span>
              </div>
            </div>
            <div class="item">
              <img src="@/assets/gen.webp" :width="25" alt="icon" />
              <div class="data-field">
                <label>{{ t('modals.mintable.gen', { value: t('common.per_h', { value: 'kW' }) }) }}</label>
                <span>{{ +app.user?.generation_rate || 0 }}</span>
              </div>
            </div>
            <div class="item">
              <div class="w-[25px]"></div>
              <div class="data-field">
                <label class="need">{{ t('modals.mintable.gen', { value: t('common.per_h', { value: 'kW' }) })
                  }}</label>
                <span class="need">{{app.stations?.gen_configs?.find((el) => el?.station_type ==
                  allStations?.[allStations.indexOf(app.user?.station_type) + 1] &&
                  el.level == 1)?.generation_rate}}</span>
              </div>
            </div>
            <div class="item">
              <img src="@/assets/fill.webp" :width="25" alt="icon" />
              <div class="data-field">
                <label>{{ t('modals.mintable.fill', { value: t('common.h') }) }}</label>
                <span>{{ Math.round(app.user?.storage_limit / app.user?.generation_rate) || 0 }}</span>
              </div>
            </div>
            <div class="item">
              <div class="w-[25px]"></div>
              <div class="data-field">
                <label class="need">{{ t('modals.mintable.fill', { value: t('common.h') }) }}</label>
                <span class="need">{{Math.round(app.stations?.storage_configs?.find((el) => el.station_type ==
                  allStations?.[allStations.indexOf(app.user?.station_type) + 1] && el.level == 1)?.storage_limit /
                  app.stations?.gen_configs?.find((el) =>
                    el?.station_type == allStations?.[allStations.indexOf(app.user?.station_type) + 1] && el.level ==
                    1)?.generation_rate) || 0}}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>

  <div class="screen-box">
    <div class="panel">
      <div class="wheel" @click="router.push('/games')">
        <img src="@/assets/wheel-icon.webp" class="wheel-image" />
        <p>
          <span>{{ t('wheel.home_btn_1') }}<br /></span>{{ t('wheel.home_btn_2') }}
        </p>
      </div>
      <!-- <img src="@/assets/thirst-block11.png" width="52px" height="52px" /> -->
      <div class="balance">
        <div class="flex items-center gap-1">
          <Swap v-if="app.user?.has_orbital_station && app.user?.orbital_first_owner && !app.user?.orbital_force_basic" @click="handleSwapToken" />
          <h2 class="score" :class="{ smaller: app.user?.has_orbital_station && app.user?.orbital_first_owner && !app.user?.orbital_force_basic }"
            id="score">{{ app.score.toFixed(1) }}</h2>
          <div class="energy-block" v-if="app.user?.has_orbital_station && app.user?.orbital_first_owner && !app.user?.orbital_force_basic">
            <img src="@/assets/kW_token.png" :class="{ 'top-energy': app.user?.orbital_is_blue }" />
            <img src="@/assets/kW.png" :class="{ 'top-energy': !app.user?.orbital_is_blue }" />
          </div>
          <img
            v-else-if="app?.user?.has_hydro_station || (app.user?.has_orbital_station && !app.user?.orbital_first_owner)"
            src="@/assets/kW_token.png" height="22px" width="22px" />
          <img v-else src="@/assets/kW.png" height="22px" width="22px" />
        </div>
        <button class="claim-btn" @click="claim">{{ t('general.top_nav.mint_btn').toUpperCase() }}</button>
      </div>
      <div class="shop" :class="{ 'gems-shop-active': !halloweenActive }" @click="openAsics">
        <img v-if="halloweenActive" src="@/assets/Halloween.png" class="asic-image halloween-image" />
        <img v-else src="@/assets/gems_shop_icon.png" class="asic-image" />
        <p>
          <span>{{ t('general.top_nav.asics_shop_1') }}<br /></span>{{ t('general.top_nav.asics_shop_2') }}
        </p>
      </div>
    </div>
  </div>
  <div class="mainarea">
    <div class="tapzone" :class="{ orbital: app.user?.has_orbital_station && !app.user?.orbital_force_basic }">
      <div class="flex flex-col w-full items-center justify-center station-image">
        <div @touchstart="increment" ref="img" style="position: relative">
          <div
            v-if="isJarvis.active && (!app.user?.building_until || getTimeRemaining(app.user?.building_until).remain <= 0) && !hydroStation.lock && !orbitalStation.lock && unlockedWallet.bool"
            class="jarvis">
            <img src="@/assets/jarvis.webp" ref="jarvisImg" width="126px" />
            <div class="jarvis-message">
              <h1>{{ t('general.main.jarvis_title') }}</h1>
              <span>{{ t('general.main.jarvis_desc') }}</span>
            </div>
          </div>
          <div v-if="app?.user?.overheated_until" class="overheat">
            <img src="@/assets/warning.png" width="74px" />
            <span>{{ t('general.main.overheat_title') }}</span>
            <div class="overheat-message" v-html="t('general.main.overheat_desc')"></div>
          </div>
          <div v-if="!unlockedWallet.bool" class="wallet-lock">
            <img src="@/assets/maintenance.webp" ref="jarvisImg" width="190px" />
            <div class="wallet-lock-message">
              <Info class="info" @click="openWalletChangeInfo = true" />
              <h1>{{ t('modals.wallet_lock.title') }}</h1>
              <span>{{ t('modals.wallet_lock.message') }}</span>
              <span class="time">{{ getTimeRemaining(unlockedWallet.time).time }}</span>
            </div>
          </div>
          <div
            v-if="((app?.user?.building_until && getTimeRemaining(app.user?.building_until).remain > 0) || hydroStation.lock || orbitalStation.lock) && unlockedWallet.bool"
            class="building-wrapper">
            <img src="@/assets/build-station.webp" width="320px" />
            <div class="building">
              <div class="building-group">
                <span>{{ hydroStation.lock || orbitalStation.lock ? t('common.connect') : t('general.main.building')
                }}</span>
                <div class="building-timer">
                  {{ orbitalStation.lock ? getTimeRemaining(orbitalStation.time).time :
                    hydroStation.lock ? getTimeRemaining(hydroStation.time).time :
                      getTimeRemaining(app?.user?.building_until).time }}
                </div>
              </div>
              <button class="building-speedup-btn py-[0.3rem] px-[1.2rem]"
                :class="{ 'px-[0.5rem]': (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || (app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || premiumActive }"
                @click="speedUpBuilding">
                <span v-if="!app?.user?.has_gold_sbt && !app?.user?.has_silver_sbt && !premiumActive">
                  {{ t('common.speedup') }}
                  <div class="flex items-center justify-center gap-1">
                    <img src="@/assets/stars.png" :width="20" />
                    {{
                      orbitalStation.lock ?
                        Math.ceil(getTimeRemaining(orbitalStation.time).remain / 1000 / 60 /
                          app.stations?.gradation_config?.find(el => el.name == ORBITAL_STATION)?.gradation_minutes) *
                        app.stations?.gradation_config?.find(el => el.name == ORBITAL_STATION)?.gradation_value
                        :
                        hydroStation.lock ?
                          Math.ceil(getTimeRemaining(hydroStation.time).remain / 1000 / 60 /
                            app.stations?.gradation_config?.find(el => el.name == HYDRO_STATION)?.gradation_minutes) *
                          app.stations?.gradation_config?.find(el => el.name == HYDRO_STATION)?.gradation_value
                          :
                          Math.ceil(getTimeRemaining(app?.user?.building_until).remain / 1000 / 60 /
                            app.withdraw_config.gradation_minutes) * app.withdraw_config.gradation_value}}
                  </div>
                </span>
                <span v-else>
                  <div class="flex items-center gap-1">
                    {{ t('common.speedup') }}
                    <img v-if="premiumActive" src="@/assets/crown.png" style="width: 16px; height: 14px" />
                    <label v-else class="text-[#FCD909]">(SBT)</label>
                  </div>
                  <div class="flex justify-center items-center font-bold gap-1 text-[#FCD909]">
                    <img src="@/assets/stars.png" width="15px" alt="Stars" />
                    {{
                      orbitalStation.lock ?
                        Math.ceil(getTimeRemaining(orbitalStation.time).remain / 1000 / 60 /
                          app.stations?.gradation_config?.find(el => el.name == ORBITAL_STATION)?.gradation_minutes *
                          app.stations?.gradation_config?.find(el => el.name == ORBITAL_STATION)?.gradation_value
                          *
                          ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive ?
                            0.9 : (app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ?
                              0.95 : 1)) :
                        hydroStation.lock ?
                          Math.ceil(getTimeRemaining(hydroStation.time).remain / 1000 / 60 /
                            app.stations?.gradation_config?.find(el => el.name == HYDRO_STATION)?.gradation_minutes *
                            app.stations?.gradation_config?.find(el => el.name == HYDRO_STATION)?.gradation_value
                            *
                            ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive ?
                              0.9 : (app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ?
                                0.95 : 1)) :
                          Math.ceil(getTimeRemaining(app?.user?.building_until).remain / 1000 / 60 /
                            app.withdraw_config.gradation_minutes * app.withdraw_config.gradation_value *
                            ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) ||
                              premiumActive ?
                              0.9 : (app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ?
                                0.95 : 1))}}
                    <span class="text-[8px] text-white font-bold line-through decoration-red-400 decoration-[2px]">
                      {{
                        orbitalStation.lock ?
                          Math.ceil(getTimeRemaining(orbitalStation.time).remain / 1000 / 60 /
                            app.stations?.gradation_config?.find(el => el.name == ORBITAL_STATION)?.gradation_minutes) *
                          app.stations?.gradation_config?.find(el => el.name == ORBITAL_STATION)?.gradation_value :
                          hydroStation.lock ?
                            Math.ceil(getTimeRemaining(hydroStation.time).remain / 1000 / 60 /
                              app.stations?.gradation_config?.find(el => el.name == HYDRO_STATION)?.gradation_minutes) *
                            app.stations?.gradation_config?.find(el => el.name == HYDRO_STATION)?.gradation_value :
                            Math.ceil(getTimeRemaining(app?.user?.building_until).remain / 1000 / 60 /
                              app.withdraw_config.gradation_minutes) * app.withdraw_config.gradation_value}}</span>
                  </div>
                </span>
              </button>
            </div>
          </div>
          <img :src="imagePath" rel="preload" class="factory lightup"
            :class="{ heated: app?.user?.overheated_until, onbuild: (app.user?.building_until && getTimeRemaining(app.user?.building_until).remain > 0), locked: (hydroStation.lock || orbitalStation.lock) && !unlockedWallet.bool }"
            ref="factory" />
        </div>
        <div class="station-label-group">
          <span class="station-label">{{ (app?.user?.has_orbital_station && !app?.user?.orbital_force_basic) ? t(`stations.${'Orbital power plant'}`) :
            app?.user?.has_hydro_station ? t(`stations.${'Hydroelectric power plant'}`) :
              t(`stations.${app.user?.station_type}`) }} {{ allStations.indexOf(app.user?.station_type)
              > 3 ? "NFT" : '' }}</span>
          <button class="station-label-btn" v-if="
            !app.user.has_orbital_station &&
            !app.user.has_hydro_station &&
            !app.stationsNft.length &&
            !app.user?.current_mint &&
            app.user?.station_type !== allStations?.[allStations.length - 1] &&
            allStations?.indexOf(app.user?.station_type) >= 4 &&
            (!app.user?.building_until || getTimeRemaining(app.user?.building_until).remain <= 0)
          " @click="
            () => {
              craft(
                'mint',
                0,
                app.stations?.storage_configs?.find((el) => el?.station_type == allStations?.[allStations.indexOf(app.user?.station_type) + 1] && el?.level == 1)?.price_tbtc,
                app.user?.station_type,
                null,
                app.stations?.storage_configs?.find((el) => el?.station_type == allStations?.[allStations.indexOf(app.user?.station_type) + 1] && el?.level == 1)?.duration,
                null
              )
            }
          ">
            {{ t('general.main.create_first') }}
          </button>
        </div>
        <div class="statistic">
          <div class="power">
            <Storage :width="22" :height="22" />
            <span v-if="isJarvis.active">{{ +(+app.user?.storage_limit ?? 0) }} kW</span>
            <span v-else>{{ +(+app.storage).toFixed(2) || 0 }}/{{ +(+app.user?.storage_limit || 0) }} kW</span>
          </div>
          <div class="repair">
            <Power :width="22" :height="22" />
            <span>{{ Math.round(+app.power) || 0 }}/100</span>
          </div>
          <div class="level">
            <StationLvl :width="22" :height="22" />
            <span>{{ app.user?.storage_level || 0 }} {{ t('common.lvl') }}</span>
          </div>
          <div class="workers" @click="handleWorkers">
            <img v-show="isJarvis.active" src="@/assets/jarvis.webp" width="22px" height="22px" />
            <div class="workers-radio" v-show="!isJarvis.active">
              <button class="work-radio"
                :class="{ selected: selectedWorkers == 'simple' || selectedWorkers == 'all', disabled: !getWorkers.simple }"></button>
              <button class="work-radio gold"
                :class="{ selected: (selectedWorkers == 'gold' || selectedWorkers == 'all') && getWorkers.gold, disabled: !getWorkers.gold }"></button>
              <button class="work-radio blue"
                :class="{ selected: (selectedWorkers == 'blue' || selectedWorkers == 'all') && getWorkers.blue, disabled: !getWorkers.blue }"></button>
            </div>
            <div class="workers-container">
              <img class="worker-img" v-show="!isJarvis.active" v-for="worker in getWorkers.sorted"
                :src="getWorkerImg(worker)" :key="worker" />
            </div>
            <!-- <img v-show="!isJarvis.active &&
              app.user.engineer_level < 50 &&
              app.user?.engineer_level < findMaxLevel(app.stations?.eng_configs)
              " src="@/assets/engineer.webp" width="22px" height="22px" />
            <img v-show="!isJarvis.active &&
              app.user.engineer_level >= 50 &&
              app.user?.engineer_level < findMaxLevel(app.stations?.eng_configs)
              " src="@/assets/stars_eng.png" width="22px" height="22px" /> -->
            <span v-if="!isJarvis.active"
              :class="{ 'star-worker': selectedWorkers == 'gold' || (selectedWorkers == 'all' && getWorkers.gold), 'blue-worker': selectedWorkers == 'blue' || (selectedWorkers == 'all' && getWorkers.blue) }">
              {{ selectedWorkers == 'simple' ? getWorkers.simple : selectedWorkers == 'gold' ? getWorkers.gold :
                selectedWorkers ==
                  'blue'
                  ? getWorkers.blue : getWorkers.all }}</span>
            <span v-if="isJarvis.active">{{ isJarvis.forever ? t('common.forever') : isJarvis.time }}</span>
          </div>
        </div>
        <div class="buttons-row">
          <button class="upgrade-btn" @click="openUpgrade">
            {{ t('general.main.upg_btn') }}
            <UpgradeBtn :width="30" :height="30" />
          </button>
          <button v-if="app.user?.has_orbital_station"
            class="switch-station-btn"
            :class="{ 'special': isOrbitalActive, 'regular': !isOrbitalActive }"
            @click="switchOrbitalStation">
            <div class="switch-btn-content">
              <span class="switch-btn-text">{{ isOrbitalActive ? 'Special' : 'Regular' }}</span>
              <img :src="isOrbitalActive ? switchIconGreen : switchIconRed"
                alt="switch"
                class="switch-btn-icon" />
            </div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
:root {
  --carousel-transition: 300ms;
  --carousel-opacity-inactive: 0.5;
  --carousel-opacity-active: 1;
  --carousel-opacity-near: 0.9;
}

.star-worker {
  color: #fea400;
}

.blue-worker {
  color: #31CFFF;
}

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

.carousel__viewport {
  perspective: 1000px;
  overflow: visible !important;
}

.carousel__track {
  transform-style: preserve-3d;
}

.carousel__slide--sliding {
  transition:
    opacity var(--carousel-transition),
    transform var(--carousel-transition);
}

.carousel.is-dragging .carousel__slide {
  transition:
    opacity var(--carousel-transition),
    transform var(--carousel-transition);
}

.carousel__slide {
  opacity: var(--carousel-opacity-inactive);
  transform: translateX(10px) rotateY(-12deg) scale(0.9);
}

.carousel__slide--prev {
  opacity: var(--carousel-opacity-near);
  transform: rotateY(-10deg) scale(0.95);
}

.carousel__slide--active {
  opacity: var(--carousel-opacity-active);
  transform: rotateY(0) scale(1);
}

.carousel__slide--next {
  opacity: var(--carousel-opacity-near);
  transform: rotateY(10deg) scale(0.95);
}

.carousel__slide--next~.carousel__slide {
  opacity: var(--carousel-opacity-inactive);
  transform: translateX(-10px) rotateY(12deg) scale(0.9);
}

.slide {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 1.5rem 0;
  overflow: visible;

  button {
    position: absolute;
    background: linear-gradient(to bottom, #e2f974, #00960095);
    box-shadow: inset 0 0 2px 2px #ffffff50;
    padding: 1rem 1.5rem;
    border-radius: 0.5rem;
    font-family: 'Inter' !important;
    font-weight: 600;
    font-size: 13px;

    &:active {
      background: linear-gradient(to bottom, #e2f97490, #00960080);
    }
  }
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.5s ease-in-out;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100vh);
}

.shell {
  margin: 0 auto;
  height: 6px;
  width: 100%;
  border-radius: 13px;
  border: 1px solid #ff3b5950;
}

.bar {
  background: linear-gradient(to right, transparent, #ff3b59);
  height: 100%;
  width: 10px;
  border-radius: 1rem;
  transition: width 0.5s ease-in-out;
}

.jarvis {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 70vw;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 100;

  img {
    margin-top: -50px;
    filter: drop-shadow(0 50px 50px #96ecf1);
    z-index: 5;
  }

  .jarvis-message {
    width: 90%;
    text-align: center;
    font-family: 'Inter' !important;
    color: #fff;
    margin-top: -15px;
    padding: 0.8rem 1rem;
    background: #000000db;
    border-radius: 1rem;
    border: 1px solid #ffffff30;
    line-height: 11px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    z-index: 10;

    h1 {
      font-size: 15px;
      font-weight: 700;
    }

    span {
      opacity: 0.8;
      font-size: 10px;
      font-weight: 500;
      letter-spacing: 0%;
      line-height: auto;
    }
  }
}

.wallet-lock {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: calc(100%);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 100;

  img {
    margin-top: -50px;
    filter: drop-shadow(0 50px 50px #96ecf1);
    z-index: 5;
  }

  &-message {
    position: relative;
    width: 100%;
    text-align: center;
    font-family: 'Inter' !important;
    color: #fff;
    margin-top: -45px;
    padding: 0.8rem 1rem;
    background: #10151BEE;
    border-radius: 1rem;
    border: 1px solid #FFC10D;
    line-height: 11px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    z-index: 10;

    .info {
      position: absolute;
      top: 0.6rem;
      right: 0.5rem;
      width: 18px;
      height: 18px;
      z-index: 10;
    }

    h1 {
      font-size: 15px;
      font-weight: 700;
    }

    span {
      opacity: 0.8;
      font-size: 10px;
      font-weight: 500;
      letter-spacing: 0%;
      line-height: auto;
    }

    .time {
      opacity: 1;
      font-size: 20px;
      font-weight: 700;
    }
  }
}

.overheat {
  position: absolute;
  top: 50%;
  left: 50%;
  background: #ff3b5999;
  border-radius: 1rem;
  transform: translate(-50%, -50%);
  width: 70vw;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 1rem 0 0.5rem 0;
  z-index: 100;

  span {
    text-align: center;
    font-family: 'Inter' !important;
    font-size: 20px;
    font-weight: 600;
    color: #fff;
  }

  .overheat-message {
    width: 95%;
    text-align: center;
    font-family: 'Inter' !important;
    font-size: 9px;
    font-weight: 500;
    color: #fff;
    padding: 0.4rem;
    background: #2e080875;
    border-radius: 1rem;
  }
}

.building-wrapper {
  margin: 0;
  padding: 0;
  width: auto;
  height: auto;

  // position: absolute;
  // top: 50%;
  // left: 50%;
  // transform: translate(-50%, -50%);
  // width: 70vw;
  // z-index: 80;
  >img {
    position: absolute;
    top: 15%;
    left: 50%;
    transform: translate(-50%, -50%);
    min-width: 70vw;
    z-index: 80;
  }

  .building {
    position: absolute;
    top: 65%;
    left: 50%;
    background: #00000090;
    backdrop-filter: blur(5px);
    border-radius: 1rem;
    transform: translate(-50%, -50%);
    min-width: 80vw;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 1rem;
    padding: 1rem 0;
    z-index: 100;
    border: 1px solid #ffffff25;

    .building-group {
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      gap: 3px;

      span {
        color: #ffffff80;
        font-family: 'Inter';
        font-weight: 500;
        font-size: 20px;
        letter-spacing: 0px;
        line-height: 20px;
      }

      .building-timer {
        color: #fff;
        font-family: 'Inter';
        font-weight: 600;
        font-size: 28px;
        letter-spacing: 0px;
        line-height: 28px;
      }
    }

    .building-speedup-btn {
      color: #fff;
      font-family: 'Inter';
      font-weight: 600;
      font-size: 14px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      line-height: 16px;
      background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
        linear-gradient(to left, #e757ec, #9851ec, #5e7cea);
      border-radius: 0.5rem;
      transition: all 100ms ease-in-out;

      &:active {
        opacity: 0.7;
        scale: 0.98;
      }
    }
  }
}

.mintable {
  position: fixed;
  bottom: 0;
  z-index: 100;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  border-radius: 1rem 1rem 0 0;
  border-top: 1px solid #ffffff50;
  background: #141e36;
  z-index: 101;

  &::before {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 90%;
    background: url('@/assets/tapzone_bg.svg') no-repeat bottom;
    background-size: cover;
    opacity: 0.3;
    /* Adjust opacity (0 = fully transparent, 1 = fully opaque) */
    z-index: 0;
    /* Ensure it stays behind content */
  }

  .scrollable {
    width: 100%;
    height: 100%;
    padding-bottom: 140px;
    display: flex;
    flex-direction: column;
    justify-content: start;
    align-items: center;
    overflow-y: scroll;
    -ms-overflow-style: none;
    scrollbar-width: none;

    &::-webkit-scrollbar {
      display: none;
    }
  }

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
      font-size: clamp(14px, 5vw, 24px);
      text-transform: capitalize;
      letter-spacing: 0px;
    }

    .close {
      position: absolute;
      right: 5px;
      // top: 1.4rem;
    }
  }

  .currencies {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.8rem;
    z-index: 1;

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

  .mint-cards {
    display: flex;
    width: 90%;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    padding: 1.5rem 0;
    z-index: 1;

    .card {
      position: relative;
      display: flex;
      flex-direction: column;
      width: 100%;
      padding: 1px;
      background: linear-gradient(to bottom, #fcd909, #fea400);
      border-radius: 1.5rem;

      h1 {
        text-align: center;
        font-family: 'Inter';
        font-weight: 600;
        font-size: 13px;
        letter-spacing: 0px;
        padding: 0.2rem 0;
        z-index: 1;
      }

      .content {
        position: relative;
        width: 100%;
        height: 100%;
        border-radius: 1.5rem;
        background: #080c15;
        overflow: hidden;

        &::before {
          content: '';
          position: absolute;
          bottom: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: url('@/assets/tapzone_bg.svg') no-repeat center/cover;
          opacity: 0.2;
          z-index: 0;
        }

        h1 {
          color: #fff;
          text-align: center;
          text-transform: capitalize;
          font-family: 'Inter';
          font-weight: 500;
          font-size: 14px;
          letter-spacing: 0px;
          z-index: 1;
        }

        .station-nft {
          position: relative;
          display: flex;
          width: 80%;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          margin: 0 auto;
          padding-bottom: 3rem;

          .level {
            color: #fff;
            text-align: center;
            text-transform: uppercase;
            font-family: 'Inter';
            font-weight: 600;
            font-size: 8px;
            letter-spacing: 0px;
            background: linear-gradient(to bottom, #6478db, #5045c1);
            border: 1px solid #ffffff50;
            border-radius: 0.5rem;
            padding: 0.1rem 0.3rem;
          }

          .undefinable {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            margin: 0 auto;
            background: #000000cd;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
            padding: 2rem 0;
            z-index: 0;

            .get-gems,
            .craft-new {
              width: 100%;
              display: flex;
              flex-direction: column;
              justify-content: center;
              align-items: center;
              background: radial-gradient(ellipse 100% 30% at top center, #ffffff50, transparent),
                linear-gradient(to bottom, #fcd909, #fea400);
              font-family: 'Inter';
              font-weight: 700;
              font-size: 12px;
              letter-spacing: 0px;
              text-align: center;
              padding: 0.2rem .5rem;
              border-radius: 0.7rem;
              transition: all 100ms ease-in-out;

              &:active {
                opacity: 0.6;
                scale: 0.95;
              }

              &:disabled {
                color: #212121;
                background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
                  linear-gradient(to bottom, #e2e2e2, #646464);
              }
            }
          }
        }

        .conditions {
          position: absolute;
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 0.5rem;
          bottom: 0;
          left: 0;
          width: 100%;
          background: #080c15;
          padding: 0.8rem 5px;

          span {
            font-family: 'Inter';
            font-weight: 400;
            font-size: 11px;
            letter-spacing: 0%;
            color: #fff;
            opacity: 0.5;
          }
        }
      }
    }
  }

  .condition-banner {
    width: 90%;
    border-radius: 1.5rem;
    padding: 0.2rem 1rem;
    color: #fff;
    font-family: 'Inter';
    background: #080c1580;
    border: 1px solid #ffffff50;
    z-index: 1;

    h1 {
      text-align: center;
      color: #fff;
      font-weight: 500;
      font-size: 14px;
      letter-spacing: 0px;
    }

    span {
      display: inline-block;
      color: #fff;
      font-weight: 400;
      font-size: 11px;
      letter-spacing: 0px;
      line-height: 13px;
      opacity: 0.5;
    }
  }

  .mint-options {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    width: 90%;
    padding: 1rem 0;
    z-index: 1;

    .title {
      width: 90%;
      text-align: center;
      color: #fcd909;
      font-family: 'Inter';
      font-weight: 600;
      font-size: 13px;
      letter-spacing: 0%;
      padding-bottom: 5px;
      border-bottom: 1px solid #ffffff80;
    }

    .mint-grid {
      width: 90%;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      margin: 1rem auto;
      gap: 0.7rem;

      .item {
        width: 100%;
        display: flex;
        justify-content: center;
        align-items: end;
        gap: 1rem;

        .title {
          width: 100%;
        }

        .data-field {
          width: 100%;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: start;
          gap: 5px;

          label {
            color: #fff;
            font-family: 'Inter';
            font-weight: 400;
            font-size: 11px;
            letter-spacing: 0%;

            &.kw {
              color: #83aedd;
            }

            &.tbtc {
              color: #fccf08;
            }

            &.need {
              color: #8de616;
            }
          }

          span {
            background: #11150c;
            color: #fff;
            font-family: 'Inter';
            font-weight: 500;
            font-size: 14px;
            letter-spacing: 0%;
            text-align: center;
            width: 100%;
            padding: 0.2rem 1rem;
            border-radius: 0.7rem;
            border: 1px solid #ffffff50;

            &.kw {
              border: 1px solid #83aedd;
            }

            &.tbtc {
              border: 1px solid #fccf08;
            }

            &.need {
              border: 1px solid #8de616;
            }
          }
        }

        .mint-btn {
          width: 100%;
          background: radial-gradient(ellipse 100% 30% at top center, #ffffff50, transparent),
            linear-gradient(to bottom, #fcd909, #fea400);
          font-family: 'Inter';
          font-weight: 700;
          font-size: 15px;
          letter-spacing: 0px;
          text-align: center;
          padding: 0.7rem 1rem;
          border-radius: 0.7rem;
          transition: all 100ms ease-in-out;

          &:active {
            opacity: 0.6;
            scale: 0.95;
          }

          &:disabled {
            color: #212121;
            background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
              linear-gradient(to bottom, #e2e2e2, #646464);
          }
        }
      }
    }
  }
}

.upgrades {
  position: fixed;
  bottom: 0;
  z-index: 100;
  width: 100%;
  height: 95%;
  display: flex;
  flex-direction: column;
  align-items: center;
  border-radius: 1rem 1rem 0 0;
  background: #000;

  .scrollable {
    width: 100%;
    height: 100%;
    padding-bottom: 140px;
    display: flex;
    flex-direction: column;
    justify-content: start;
    align-items: center;
    overflow-y: scroll;
    -ms-overflow-style: none;
    scrollbar-width: none;

    &::-webkit-scrollbar {
      display: none;
    }
  }

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
      font-weight: bold;
      font-size: 13px;
      text-transform: uppercase;
    }

    .close {
      position: absolute;
      right: 5px;
    }
  }

  .currencies {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.8rem;
    margin-bottom: 10px;

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

  .station-statistic {
    display: flex;
    width: 90%;
    align-items: center;
    justify-content: center;
    margin-bottom: 0.5rem;
    gap: 0.4rem;

    .storage,
    .generation,
    .time,
    .minting {
      display: flex;
      justify-content: start;
      width: max-content;
      align-items: center;
      gap: 0.2rem;

      span {
        color: #fff;
        font-family: 'Inter' !important;
        font-weight: 400;
        font-size: 10px;
      }
    }
  }

  .power-panel {
    display: flex;
    width: 90%;
    justify-content: space-between;
    gap: 1rem;

    .power-progress {
      display: flex;
      width: 100%;
      flex-direction: column;
      align-items: start;
      justify-content: center;
      gap: 0.1rem;

      .labels {
        display: flex;
        width: 100%;
        justify-content: space-between;
        color: #fff;
        font-family: 'Inter' !important;
        font-size: 12px;

        .left-side {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
        }
      }
    }

    .repair-btn {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 60%;
      max-height: 40px;
      padding: 0.7rem 1rem;
      border-radius: 0.5rem;
      background: linear-gradient(to bottom, #fcd909, #fea400);
      margin-bottom: 5px;
      font-family: 'Inter' !important;
      font-weight: 600;
      font-size: 13px;

      &::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: url('@/assets/repair.svg') no-repeat center;
        background-size: 25%;
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
  }

  .upgrade-station-panel {
    display: flex;
    padding: 1rem 0.5rem;
    width: 100%;
    justify-content: center;
    gap: 0.5rem;

    .upgrade-card {
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: start;
      text-align: center;
      font-family: 'Inter' !important;
      padding: 1rem 0.3rem;
      width: 100%;
      border-radius: 1rem;
      gap: 0.7rem;
      box-shadow: inset 0 0 0 2px #ffffff50;
      background: radial-gradient(ellipse 80% 60% at right top, #42ff3150, transparent), #1d1e3a;

      &.stars-card {
        background: radial-gradient(ellipse 80% 60% at right top,
            #726eea90,
            #791ec975 50%,
            transparent),
          #1d1e3a;
      }

      .level {
        position: absolute;
        top: -0.3rem;
        font-size: 8px;
        font-weight: bold;
        padding: 0.2rem 0.5rem;
        border-radius: 2rem;
        background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
          linear-gradient(to bottom, #e2f974, #009600);

        &.mint {
          color: #fff;
          background: radial-gradient(ellipse 80% 20% at bottom, #ffffff25, transparent),
            linear-gradient(to bottom, #6478db, #5045c1);
        }

        &.stars-level {
          background: linear-gradient(to left, #e757ec, #9851ec, #5e7cea);
        }
      }

      .level-upgrade-station {
        position: absolute;
        top: -0.3rem;
        font-size: 8px;
        font-weight: bold;
        padding: 0.2rem 0.5rem;
        border-radius: 2rem;
        color: #000;
        background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);
      }

      .service-title {
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        width: 80%;
        height: 10%;
        padding-top: 10px;
        color: #fff;
        font-size: 10px;
        font-weight: bold;
      }

      .middle-sect {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.2rem;

        .light-line {
          width: 70%;
          height: 1px;
          background: linear-gradient(to right, transparent, #fff, transparent);
        }

        .picture {
          width: 90%;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .service-title-loc {
          display: flex;
          align-items: center;
          justify-content: center;
          color: #fff;
          font-size: 10px;
          font-weight: bold;
          height: 20px;

          &.spec {
            line-height: 10px;
            color: #FCD909;
          }
        }

        .increase-group {
          display: flex;
          align-items: center;
          justify-content: center;
          color: #fff;
          font-size: 10px;
          font-weight: 600;
          gap: 0.1rem;

          .to {
            color: #31ff80;
          }
        }
      }

      .upgrade-price {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        margin: 0 auto;

        .upgrade-price-item {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.1rem;

          span {
            color: #fff;
            font-size: 10px;
            font-weight: 600;
          }
        }
      }

      .upg-btn {
        position: absolute;
        bottom: -1.6rem;
        font-size: 13px;
        font-weight: 600;
        padding: 0.6rem .2rem;
        min-width: 100px;
        border-radius: 0.5rem;
        box-shadow: 0 0 0 2px #1e6a0850;
        background:
          url('@/assets/upg-icon.svg') no-repeat center,
          radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
          linear-gradient(to bottom, #e2f974, #009600);

        &:active {
          opacity: 0.98;
        }

        &.mint {
          color: #000;
          box-shadow: 0 0 0 2px #cacaca50;
          background:
            url('@/assets/upg-icon.svg') no-repeat center,
            radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
            linear-gradient(to bottom, #fcd909, #fea400);
        }

        &.stars-btn {
          box-shadow: 0 0 0 2px #123cd250;
          background:
            url('@/assets/upg-icon.svg') no-repeat center,
            radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
            linear-gradient(to left, #e757ec, #9851ec, #5e7cea);

          &:active {
            background:
              url('@/assets/upg-icon.svg') no-repeat center,
              radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
              linear-gradient(to left, #c249c6, #7d43c4, #4a63bb);
          }
        }
      }

      .upg-btn-unactive {
        position: absolute;
        bottom: -1.6rem;
        font-size: 13px;
        font-weight: 600;
        padding: 0.6rem .2rem;
        min-width: 100px;
        border-radius: 0.5rem;
        box-shadow: 0 0 0 2px #26262650;
        text-wrap: nowrap;
        background:
          url('@/assets/upg-icon.svg') no-repeat center,
          radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
          linear-gradient(to bottom, #757575, #2b2b2b);
      }

      .upg-btn-max {
        position: absolute;
        bottom: -1.6rem;
        font-size: 13px;
        font-weight: 600;
        padding: 0.6rem .2rem;
        min-width: 100px;
        border-radius: 0.5rem;
        box-shadow: 0 0 0 2px #cacaca50;
        text-wrap: nowrap;
        background:
          url('@/assets/upg-icon.svg') no-repeat center,
          radial-gradient(ellipse 80% 20% at top, #ffffff80, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);
      }
    }
  }
}

.screen-box {
  width: 90%;
  margin: 0 auto 1rem auto;
}

.panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-family: 'Inter' !important;
  width: 100%;
  gap: 1rem;

  .wheel {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    background: url('@/assets/wheel-back.webp') no-repeat center;
    background-size: cover;
    height: 52px;
    min-width: 52px;
    aspect-ratio: 1/1;
    border-radius: 0.8rem;

    &:active {
      opacity: 0.5;
    }

    img {
      max-width: none;
    }

    .wheel-image {
      margin: -15px;
      width: 55px;
      padding-bottom: 10px;
    }

    p {
      text-align: center;
      color: #fff;
      font-size: 6px;
      font-weight: 800;
      line-height: 1.1;
      text-transform: uppercase;

      span {
        font-size: 0.6rem;
        text-transform: none;
      }
    }
  }

  .shop {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: end;
    text-align: center;
    background: url('@/assets/thirst-block222.png') no-repeat center;
    background-size: cover;
    overflow: hidden;
    height: 52px;
    min-width: 52px;
    aspect-ratio: 1/1;
    border-radius: 0.8rem;
    overflow: visible;

    &.gems-shop-active {
      background: linear-gradient(180deg, rgba(222, 211, 183, 1) 0%, rgba(209, 139, 0, 1) 100%);
      box-shadow: 0px 4px 4px 0px rgba(0, 0, 0, 0.25);
    }

    &:active {
      opacity: 0.5;
    }

    img {
      max-width: none;
    }

    .asic-image {
      margin: -15px;
      width: 70px;
    }

    .halloween-image {
      position: relative;
      width: 60px;
      margin: -15px;
      padding-bottom: 10px;
      z-index: 0; /* под текстом */
      pointer-events: none; /* не перехватывать клики */
      filter: drop-shadow(0 6px 10px rgba(254, 164, 0, 0.22))
              drop-shadow(0 0 12px rgba(254, 164, 0, 0.18))
              drop-shadow(0 3px 6px rgba(0, 0, 0, 0.25));
      animation: halloween-pumpkin-dance 8s cubic-bezier(0.4, 0.0, 0.6, 1) infinite;
      transform-origin: center bottom;
      will-change: transform, filter;
    }

    @keyframes halloween-pumpkin-dance {
      /* Плавное качание влево */
      0% {
        transform: translateX(0) translateY(0) rotate(0deg);
        filter: drop-shadow(0 6px 10px rgba(254, 164, 0, 0.22))
                drop-shadow(0 0 12px rgba(254, 164, 0, 0.18))
                drop-shadow(0 3px 6px rgba(0, 0, 0, 0.25));
      }
      12.5% {
        transform: translateX(-2.5px) translateY(-0.8px) rotate(-1.5deg);
        filter: drop-shadow(0 7px 11px rgba(254, 164, 0, 0.24))
                drop-shadow(0 0 14px rgba(254, 164, 0, 0.19))
                drop-shadow(0 4px 7px rgba(0, 0, 0, 0.28));
      }

      /* Плавное качание вправо */
      25% {
        transform: translateX(2.5px) translateY(-0.8px) rotate(1.5deg);
        filter: drop-shadow(0 7px 11px rgba(254, 164, 0, 0.24))
                drop-shadow(0 0 14px rgba(254, 164, 0, 0.19))
                drop-shadow(0 4px 7px rgba(0, 0, 0, 0.28));
      }

      /* Мягкое подпрыгивание */
      37.5% {
        transform: translateX(0) translateY(-3px) rotate(0deg);
        filter: drop-shadow(0 8px 12px rgba(254, 164, 0, 0.25))
                drop-shadow(0 0 15px rgba(254, 164, 0, 0.2))
                drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3));
      }

      /* Возврат к центру */
      50% {
        transform: translateX(0) translateY(0) rotate(0deg);
        filter: drop-shadow(0 6px 10px rgba(254, 164, 0, 0.22))
                drop-shadow(0 0 12px rgba(254, 164, 0, 0.18))
                drop-shadow(0 3px 6px rgba(0, 0, 0, 0.25));
      }

      /* Мягкое качание влево (меньшая амплитуда) */
      62.5% {
        transform: translateX(-1.5px) translateY(-0.5px) rotate(-0.8deg);
        filter: drop-shadow(0 6px 10px rgba(254, 164, 0, 0.22))
                drop-shadow(0 0 12px rgba(254, 164, 0, 0.18))
                drop-shadow(0 3px 6px rgba(0, 0, 0, 0.25));
      }

      /* Мягкое качание вправо (меньшая амплитуда) */
      75% {
        transform: translateX(1.5px) translateY(-0.5px) rotate(0.8deg);
        filter: drop-shadow(0 6px 10px rgba(254, 164, 0, 0.22))
                drop-shadow(0 0 12px rgba(254, 164, 0, 0.18))
                drop-shadow(0 3px 6px rgba(0, 0, 0, 0.25));
      }

      /* Второе мягкое подпрыгивание */
      87.5% {
        transform: translateX(0) translateY(-2.5px) rotate(0deg);
        filter: drop-shadow(0 7px 11px rgba(254, 164, 0, 0.24))
                drop-shadow(0 0 14px rgba(254, 164, 0, 0.19))
                drop-shadow(0 4px 7px rgba(0, 0, 0, 0.28));
      }

      /* Возврат к началу */
      100% {
        transform: translateX(0) translateY(0) rotate(0deg);
        filter: drop-shadow(0 6px 10px rgba(254, 164, 0, 0.22))
                drop-shadow(0 0 12px rgba(254, 164, 0, 0.18))
                drop-shadow(0 3px 6px rgba(0, 0, 0, 0.25));
      }
    }

    p {
      position: relative;
      z-index: 1; /* над изображением */
      color: #fff;
      font-size: 6px;
      text-transform: uppercase;
      font-weight: 800;
      line-height: 1.1;

      span {
        text-transform: none;
        font-size: 0.6rem;
      }
    }
  }

  .balance {
    width: 100%;
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: space-evenly;
    background: #0e1526;
    border-radius: 1rem;
    border: 1px solid #ffffff40;
  }
}

.score {
  color: #fff;
  text-align: center;
  font-family: 'Inter' !important;
  font-size: clamp(1rem, 5vw, 24px);
  font-weight: 600;
  user-select: none;

  &.smaller {
    font-size: clamp(1rem, 4vw, 24px);
  }
}

.energy-block {
  height: 25px;
  width: 27px;
  position: relative;

  img {
    width: 16px;
    height: 16px;
    position: absolute;
    top: 0;
    right: 0;
    z-index: 1;
    transition: all 500ms ease-in-out;

    &.top-energy {
      width: 21px;
      height: 21px;
      position: absolute;
      top: auto;
      right: auto;
      bottom: 0;
      left: 0;
      z-index: 5;
    }
  }
}

.claim-btn {
  color: #fff;
  font-family: 'Inter' !important;
  font-weight: 900;
  font-size: 0.8rem;
  padding: 0 12px;
  height: 25px;
  background: linear-gradient(to bottom, #bc9aff, #8143fc);
  border-radius: 5rem;

  &:active {
    background: linear-gradient(to bottom, #bc9aff50, #8143fc50);
  }
}

.mainarea {
  position: relative;
  width: 100%;
}

.tapzone {
  width: 100%;
  height: 63dvh;
  background: url('@/assets/tapzone_bg.svg'), #242653;
  position: fixed;
  bottom: 0;
  border-radius: 2rem 2rem 0 0;
  border-top: 1px solid #ffffff20;
  display: flex;
  flex-direction: column;
  align-items: center;

  &.orbital {
    background:
      linear-gradient(to bottom, #0000004D, #0000004D),
      url('@/assets/space-bg.webp') center no-repeat;
    background-size: cover;
  }
}

.station-label-group {
  position: absolute;
  bottom: calc(120px + 50px + 20px + 6%);
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;

  .station-label {
    font-family: 'Inter' !important;
    font-size: 10px;
    font-weight: 600;
    color: #fff;
    background: #00000060;
    border: 1px solid #ffffff25;
    padding: 6px 8px;
    border-radius: 0.7rem;
  }

  .station-label-btn {
    border-radius: 0.7rem;
    padding: 6px 10px;
    font-family: 'Inter';
    font-size: 10px;
    font-weight: 600;
    background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
      linear-gradient(to bottom, #fcd909, #fea400);
    color: #000;
    transition: all 100ms ease-in-out;

    &:active {
      opacity: 0.8;
      scale: 0.98;
    }
  }
}

.statistic {
  position: absolute;
  bottom: calc(120px + 50px + 4%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 90%;
  color: #fff;
  font-family: 'Inter' !important;
  font-size: clamp(8px, 2.5vw, 11px);
  font-weight: 600;
  gap: 0.7rem;

  .power,
  .repair,
  .level {
    display: flex;
    align-items: center;
    gap: 2px;
    background: linear-gradient(to left, #00000050, transparent);
    border-radius: 5rem;

    span {
      margin-right: 0.5rem;
    }
  }

  .workers {
    display: flex;
    align-items: center;
    gap: 2px;
    background: linear-gradient(to left, #00000050, #00000025);
    border-radius: 1rem 5rem 5rem 1rem;

    span {
      margin-right: 0.5rem;
    }


    .workers-radio {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding-left: 3px;

      .work-radio {
        position: relative;
        width: 6px;
        height: 6px;
        z-index: 10;
        background:
          linear-gradient(to bottom, #000, #000) padding-box,
          linear-gradient(to bottom, #fff, #fff) border-box;
        border: 1px solid transparent;
        border-radius: 50%;
        opacity: 0.4;

        &::before {
          content: "";
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 2px;
          height: 2px;
          border-radius: 50%;
          background: #fff;
          z-index: 50;
        }

        &.gold {
          background:
            linear-gradient(to bottom, #000, #000) padding-box,
            linear-gradient(to bottom, #FCD909, #FEA400);

          &::before {
            background: linear-gradient(to bottom, #FCD909, #FEA400);
          }
        }

        &.blue {
          background:
            linear-gradient(to bottom, #000, #000) padding-box,
            linear-gradient(to bottom, #31CFFF, #31CFFF);

          &::before {
            background: linear-gradient(to bottom, #31CFFF, #31CFFF);
          }
        }


        &.selected {
          opacity: 1;
        }

        &.disabled {
          background:
            linear-gradient(to bottom, #000, #000) padding-box,
            linear-gradient(to bottom, #fff, #fff) border-box !important;
          opacity: 0.3;

          &::before {
            background: linear-gradient(to bottom, #fff, #fff);
          }

        }
      }
    }

    .workers-container {
      display: flex;
      align-items: center;

      .worker-img {
        width: 20px;
        height: 20px;
        z-index: 3;

        &:not(:first-child) {
          margin-left: -13px;
          z-index: 2;
        }

        &:last-child {
          z-index: 1;
        }
      }
    }
  }
}

.buttons-row {
  position: absolute;
  bottom: calc(120px + 2%);
  display: flex;
  align-items: center;
  gap: 1rem;
  z-index: 100;
}

.switch-station-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 50px;
  min-width: 109px;
  padding: 4px 12px;
  border-radius: 27px;
  border: 1px solid transparent;
  box-sizing: border-box;
  cursor: pointer;
  font-family: Inter, sans-serif;
  font-weight: 600;
  font-size: 18px;
  line-height: 1.21;
  transition: all 0.2s ease;

  .switch-btn-content {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }

  .switch-btn-text {
    color: #FFFFFF;
    text-align: center;
    line-height: 1;
    display: flex;
    align-items: center;
  }

  .switch-btn-icon {
    width: 24px;
    height: 24px;
    image-rendering: -webkit-optimize-contrast;
    image-rendering: crisp-edges;
    flex-shrink: 0;
    display: block;
  }

  &.special {
    background:
      radial-gradient(circle at 50% 100%, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0) 100%),
      radial-gradient(circle at 50% 22%, rgba(255, 255, 255, 0.2) 0%, rgba(255, 255, 255, 0) 100%),
      linear-gradient(270deg, rgba(0, 0, 0, 0.3) 0%, rgba(0, 0, 0, 0) 30%, rgba(0, 0, 0, 0) 70%, rgba(0, 0, 0, 0.3) 100%),
      linear-gradient(165deg, rgba(255, 255, 255, 0) 0%, rgba(255, 255, 255, 0.15) 50%, rgba(255, 255, 255, 0) 100%),
      linear-gradient(90deg, rgba(49, 207, 255, 1) 0%, rgba(77, 64, 255, 1) 100%);
    box-shadow: 0px 2px 0px 0px rgba(70, 255, 141, 1);
    border: 1px solid #46FF8D;

    &:active {
      opacity: 0.85;
      transform: translateY(1px);
      box-shadow: 0px 1px 0px 0px rgba(70, 255, 141, 1);
    }
  }

  &.regular {
    background:
      radial-gradient(circle at 50% 100%, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0) 100%),
      radial-gradient(circle at 50% 22%, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0) 100%),
      linear-gradient(270deg, rgba(0, 0, 0, 0.2) 0%, rgba(0, 0, 0, 0) 30%, rgba(0, 0, 0, 0) 70%, rgba(0, 0, 0, 0.2) 100%),
      linear-gradient(165deg, rgba(255, 255, 255, 0) 0%, rgba(255, 255, 255, 0.1) 50%, rgba(255, 255, 255, 0) 100%),
      linear-gradient(180deg, rgba(226, 226, 226, 1) 0%, rgba(100, 100, 100, 1) 100%),
      #B7B7B6;
    box-shadow: 0px 2px 0px 0px rgba(255, 70, 70, 1);
    border: 1px solid #FF4646;

    &:active {
      opacity: 0.85;
      transform: translateY(1px);
      box-shadow: 0px 1px 0px 0px rgba(255, 70, 70, 1);
    }
  }
}

.upgrade-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 600;
  font-size: 1.1rem;
  gap: 1rem;
  padding: 1rem 2.5rem;
  max-height: 50px;
  border-radius: 5rem;
  background: linear-gradient(to right, #d340ff, #ff7047);
  border: none;
  cursor: pointer;

  &:active {
    background: linear-gradient(to right, #d340ff50, #ff704750);
  }
}

@media screen and (max-height: 620px) {
  .station-image {
    margin-top: 40px;
  }

  .buttons-row {
    bottom: 125px;
  }

  .switch-station-btn {
    min-width: 95px;
    height: 45px;
    font-size: 16px;
    padding: 3px 10px;

    .switch-btn-icon {
      width: 22px;
      height: 22px;
      image-rendering: -webkit-optimize-contrast;
      image-rendering: crisp-edges;
    }
  }

  .upgrade-btn {
    padding: 0.5rem 1.5rem;
  }

  .statistic {
    bottom: 180px;
    font-size: 9px;
  }

  .station-label {
    bottom: 210px;
  }
}

.factory {
  width: clamp(200px, 45dvh, 320px);
  margin: calc(clamp(200px, 45dvh, 320px) * -0.15) auto auto;
  // transition: filter 1s ease-in-out;
  // filter: none;
}

.lightup {
  filter: drop-shadow(0 5px 30px #436efc80) grayscale(0) contrast(1);
  // animation: fadeOut 1.5s ease-in-out infinite;
}

.heated {
  filter: drop-shadow(0 5px 30px #ff3b5980) grayscale(0) contrast(1);
  // animation: fadeOutHeated 1.5s ease-in-out infinite;
}

.onbuild {
  filter: grayscale(1) contrast(1.75);
  // animation: fadeOutBuild 1.5s ease-in-out infinite;
}

.locked {
  filter: brightness(0.2);
}

@keyframes fadeOut {
  0% {
    filter: drop-shadow(0 0px 10px #436efc) grayscale(0) contrast(1);
  }

  50% {
    filter: drop-shadow(0 5px 30px #436efc80) grayscale(0) contrast(1);
  }

  100% {
    filter: drop-shadow(0 0px 10px #436efc) grayscale(0) contrast(1);
  }
}

@keyframes fadeOutHeated {
  0% {
    filter: drop-shadow(0 0px 10px #ff3b59) grayscale(0) contrast(1);
  }

  50% {
    filter: drop-shadow(0 5px 30px #ff3b5980) grayscale(0) contrast(1);
  }

  100% {
    filter: drop-shadow(0 0px 10px #ff3b59) grayscale(0) contrast(1);
  }
}

@keyframes fadeOutBuild {
  0% {
    filter: grayscale(1) contrast(1);
  }

  50% {
    filter: grayscale(1) contrast(1.75);
  }

  100% {
    filter: grayscale(1) contrast(1);
  }
}
</style>
