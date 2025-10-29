<script setup>
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref } from 'vue'
const Exit = defineAsyncComponent(() => import('@/assets/exit.svg'))
import mintableImg from '@/assets/mintable.png'
import kingImg from '@/assets/crown.png'
import timeImg from '@/assets/timer.png'
import ModalNew from '@/components/ModalNew.vue'
import { useAppStore } from '@/stores/app'
import { host } from '../../axios.config'
import { useTelegram } from '@/services/telegram'
import { useI18n } from 'vue-i18n'

const app = useAppStore()
const { tg } = useTelegram()
const { t, locale } = useI18n()
const loc_add = computed(() => locale.value == 'uk' ? '' : locale.value == 'ru' ? '_ru' : '_en')
const isMiners = ref(false)
const paymentRadio = ref('ton')

const modalStatus = ref(null)
const modalTitle = ref(null)
const modalBody = ref(null)
const openModal = ref(false)

const boosters = computed(() => app?.boosters || [])

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

const jarvisBlocked = computed(() => {
  const jarvisBlock = app.timed_nfts.find(el => el.name == 'Jarvis Bot')
  return new Date(jarvisBlock?.block_until) > new Date()
})
const cryoBlocked = computed(() => {
  const cryoBlock = app.timed_nfts.find(el => el.name == 'Cryochamber')
  return new Date(cryoBlock?.block_until) > new Date()
})
const magnitBlocked = computed(() => {
  const magnitBlock = app.timed_nfts.find(el => el.name == 'Magnetic ring')
  return new Date(magnitBlock?.block_until) > new Date()
})
const managerBlocked = computed(() => {
  const managerBlock = app.timed_nfts.find(el => el.name == 'ASIC Manager')
  return new Date(managerBlock?.block_until) > new Date()
})

const premiumActive = computed(() => new Date(app.user?.premium_sub_expires) >= new Date())

const foreverBoosts = ref({
  'jarvis': {
    name: 'Jarvis Bot',
    price: 89,
    old_price: 99,
    link: 'https://getgems.io/tbtc?filter=%7B%22attributes%22%3A%7B%7D%2C%22q%22%3A%22Jarvis%22%7D#items'
  },
  'cryo': {
    name: 'Cryochamber',
    price: 89,
    old_price: 99,
    link: 'https://getgems.io/tbtc?filter=%7B%22attributes%22%3A%7B%7D%2C%22q%22%3A%22Cryochamber%22%7D#items'
  },
  'magnit': {
    name: 'Magnetic ring',
    price: 89,
    old_price: 99,
    link: 'https://getgems.io/tbtc?filter=%7B%22attributes%22%3A%7B%7D%2C%22q%22%3A%22magnetic%22%7D#items'
  },
  'asic_manager': {
    name: 'ASIC Manager',
    price: 39,
    old_price: 49,
    link: 'https://getgems.io/tbtc?filter=%7B%22attributes%22%3A%7B%7D%2C%22q%22%3A%22manager%22%7D#items'
  }
})

// Enum: [ azot, jarvis, cryo, autostart, powerbank, magnit, asic_manager ]

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

const parseBoosterInfo = (booster) => {
  return computed(() => {
    let status, additional
    if (booster?.slug == 'azot') {
      status = booster?.[`status1${loc_add.value}`]
      const hourDiff = Math.max(
        0,
        Math.floor((new Date() - new Date(app?.user?.azot_activated)) / (1000 * 60 * 60)),
      )
      if (hourDiff < 24 && app?.user?.azot_uses_left + app.user?.azot_reward_balance <= 0) {
        additional = booster?.[`additional_info2${loc_add.value}`]?.replace('{N}', t('common.hours', { n: 24 - hourDiff }))
      } else {
        if ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) {
          if (app?.user?.azot_uses_left + app.user?.azot_reward_balance + (hourDiff >= 24 ? 2 : 0) > 0) {
            additional = `<span class="!text-[#FCD909] font-bold flex items-center gap-1">${premiumActive.value ? `<img src="${kingImg}" style="width: 14px; height: 13px;"/>` : ''} ${t('common.times', { n: app.user?.azot_reward_balance + (hourDiff >= 24 ? 2 : app?.user?.azot_uses_left) })}</span>${locale.value == 'uk' ? 'безкоштовно' : locale.value == 'ru' ? 'бесплатно' : 'for free'} ${!premiumActive.value ? '<span class="!text-[#FCD909]">(SBT)</span>' : ''}`
          } else {
            additional = `<span class="!text-[#FCD909] font-bold flex items-center gap-1">${premiumActive.value ? `<img src="${kingImg}" style="width: 14px; height: 13px;"/>` : ''}${locale.value == 'uk' ? '2 рази' : locale.value == 'ru' ? '2 раза' : '2 times'}</span> ${locale.value == 'uk' ? 'безкоштовно' : locale.value == 'ru' ? 'бесплатно' : 'for free'} ${!premiumActive.value ? '<span class="!text-[#FCD909]">(SBT)</span>' : ''}`
          }
        } else {
          if (app?.user?.azot_uses_left + app.user?.azot_reward_balance + (hourDiff >= 24 ? 1 : 0) > 0) {
            additional = `<span class="!text-white font-bold flex items-center gap-1">${t('common.times', { n: app.user?.azot_reward_balance + (hourDiff >= 24 ? 1 : app?.user?.azot_uses_left) })}</span>${locale.value == 'uk' ? 'безкоштовно' : locale.value == 'ru' ? 'бесплатно' : 'for free'}`
          }
          else {
            additional = booster?.[`additional_info1${loc_add.value}`]
          }
        }
      }
    }
    if (booster?.slug == 'jarvis') {
      const jarvisBlock = app.timed_nfts?.find(el => el?.name == 'Jarvis Bot')
      if (new Date(jarvisBlock?.block_until) > new Date()) {
        status = `<span class="!text-[#FCD909]">${t('common.connect')}</span>`
        additional = `<img src="${timeImg}" style="width: 12px; height: 13px;"/> ${getTimeRemaining(jarvisBlock?.block_until).time}`
      } else if (app?.user?.jarvis_expires) {
        const daysDiff = Math.max(0, Math.round((new Date(app?.user?.jarvis_expires) - new Date()) / (1000 * 60 * 60 * 24)))
        if (daysDiff > 0) {
          status = booster?.[`status2${loc_add.value}`]
          additional = jarvisIsForever.value
            ? `<img src="${mintableImg}" style="width: 12px; height: 13px;"/> ${t('common.forever')}`
            : booster?.[`additional_info2${loc_add.value}`]?.replace('{N}', t('common.days', { n: +daysDiff }))
        } else {
          status = booster?.[`status1${loc_add.value}`]
          additional = paymentRadio.value == 'ton' ? t('common.not_bought') : booster?.[`additional_info1${loc_add.value}`]
        }
      } else {
        status = booster?.[`status1${loc_add.value}`]
        additional = paymentRadio.value == 'ton' ? t('common.not_bought') : booster?.[`additional_info1${loc_add.value}`]
      }
    }
    if (booster?.slug == 'cryo') {
      const cryoBlock = app.timed_nfts?.find(el => el?.name == 'Cryochamber')
      if (new Date(cryoBlock?.block_until) > new Date()) {
        status = `<span class="!text-[#FCD909]">${t('common.connect')}</span>`
        additional = `<img src="${timeImg}" style="width: 12px; height: 13px;"/> ${getTimeRemaining(cryoBlock?.block_until).time}`
      } else if (app?.user?.cryo_expires) {
        const daysDiff = Math.max(0, Math.round((new Date(app?.user?.cryo_expires) - new Date()) / (1000 * 60 * 60 * 24)))
        if (daysDiff > 0) {
          status = booster?.[`status2${loc_add.value}`]
          additional = cryoIsForever.value
            ? `<img src="${mintableImg}" style="width: 12px; height: 13px;"/> ${t('common.forever')}`
            : booster?.[`additional_info2${loc_add.value}`]?.replace('{N}', t('common.days', { n: +daysDiff }))
        } else {
          status = booster?.[`status1${loc_add.value}`]
          additional = paymentRadio.value == 'ton' ? t('common.not_bought') : booster?.[`additional_info1${loc_add.value}`]
        }
      } else {
        status = booster?.[`status1${loc_add.value}`]
        additional =
          paymentRadio.value == 'ton'
            ? t('common.not_bought')
            : booster?.[`additional_info1${loc_add.value}`]
      }
    }
    if (booster?.slug == 'electrics') {
      const electricsBlock = app.timed_nfts.find(el => el.name == 'Electrics')
      if (new Date(electricsBlock?.block_until) > new Date()) {
        status = `<span class="!text-[#FCD909]">${t('common.connect')}</span>`
        additional = `<img src="${timeImg}" style="width: 12px; height: 13px;"/> ${getTimeRemaining(electricsBlock?.block_until).time}`
      } else if (app?.user?.electrics_expires) {
        const daysDiff = Math.max(0, Math.round((new Date(app?.user?.electrics_expires) - new Date()) / (1000 * 60 * 60 * 24)))
        if (daysDiff > 0) {
          status = booster?.[`status2${loc_add.value}`]
          additional = booster?.[`additional_info2${loc_add.value}`]?.replace('{N}', t('common.days', { n: +daysDiff }))
        } else {
          status = booster?.[`status1${loc_add.value}`]
          additional = paymentRadio.value == 'ton' ? t('common.not_bought') : booster?.[`additional_info1${loc_add.value}`]
        }
      } else {
        status = booster?.[`status1${loc_add.value}`]
        additional =
          paymentRadio.value == 'ton'
            ? t('common.not_bought')
            : booster?.[`additional_info1${loc_add.value}`]
      }
    }
    if (booster?.slug == 'premium_sub') {
      const premiumBlock = app.timed_nfts.find(el => el.name == 'Premium')
      if (new Date(premiumBlock?.block_until) > new Date()) {
        status = `<span class="!text-[#FCD909]">${t('common.connect')}</span>`
        additional = `<img src="${timeImg}" style="width: 12px; height: 13px;"/> ${getTimeRemaining(premiumBlock?.block_until).time}`
      } else if (app?.user?.premium_sub_expires) {
        const daysDiff = Math.max(0, Math.round((new Date(app?.user?.premium_sub_expires) - new Date()) / (1000 * 60 * 60 * 24)))
        if (daysDiff > 0) {
          status = booster?.[`status2${loc_add.value}`]
          additional = booster?.[`additional_info2${loc_add.value}`]?.replace('{N}', t('common.days', { n: +daysDiff }))
        } else {
          status = booster?.[`status1${loc_add.value}`]
          additional = paymentRadio.value == 'ton' ? t('common.not_bought') : booster?.[`additional_info1${loc_add.value}`]
        }
      } else {
        status = booster?.[`status1${loc_add.value}`]
        additional =
          paymentRadio.value == 'ton'
            ? t('common.not_bought')
            : booster?.[`additional_info1${loc_add.value}`]
      }
    }
    if (booster?.slug == 'autostart') {
      if (app.user?.autostart_count > 0) {
        status = booster?.[`status2${loc_add.value}`]
        additional = booster?.[`additional_info2${loc_add.value}`]?.replace('{N}', app.user?.autostart_count)
      } else {
        status = booster?.[`status1${loc_add.value}`]
        additional = booster?.[`additional_info1${loc_add.value}`]
      }
    }
    if (booster?.slug == 'powerbank') {
      if (app.user?.powerbank_activated !== null) {
        const hourDiff = Math.max(0, Math.floor((new Date() - new Date(app?.user?.powerbank_activated)) / (1000 * 60 * 60)))
        if (hourDiff < +booster?.n1 && app?.user?.powerbank_uses_left + app.user?.powerbank_reward_balance <= 0) {
          status = booster?.[`status2${loc_add.value}`]
          additional = booster?.[`additional_info2${loc_add.value}`]?.replace('{N}', t('common.hours', { n: booster?.n1 - hourDiff }))
        } else {
          if ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) {
            status = booster?.[`status1${loc_add.value}`]
            if (app?.user?.powerbank_uses_left + app.user?.powerbank_reward_balance + (hourDiff >= +booster?.n1 ? 2 : 0) > 0) {
              additional = `<span class="!text-[#FCD909] font-bold flex items-center gap-1">${premiumActive.value ? `<img src="${kingImg}" style="width: 14px; height: 13px;"/>` : ''} ${t('common.times', { n: app.user?.powerbank_reward_balance + (hourDiff >= +booster?.n1 ? 2 : app?.user?.powerbank_uses_left) })}</span> ${locale.value == 'uk' ? 'безкоштовно' : locale.value == 'ru' ? 'бесплатно' : 'for free'} ${!premiumActive.value ? '<span class="!text-[#FCD909]">(SBT)</span>' : ''}`
            } else {
              additional = `<span class="!text-[#FCD909] font-bold flex items-center gap-1">${premiumActive.value ? `<img src="${kingImg}" style="width: 14px; height: 13px;"/>` : ''} ${locale.value == 'uk' ? '2 рази' : locale.value == 'ru' ? '2 раза' : '2 times'}</span> ${locale.value == 'uk' ? 'безкоштовно' : locale.value == 'ru' ? 'бесплатно' : 'for free'} ${!premiumActive.value ? '<span class="!text-[#FCD909]">(SBT)</span>' : ''}`
            }
          } else {
            status = booster?.[`status1${loc_add.value}`]
            if (app?.user?.powerbank_uses_left + app.user?.powerbank_reward_balance + (hourDiff >= +booster?.n1 ? 1 : 0) > 0) {
              additional = `<span class="!text-white font-bold flex items-center gap-1">${t('common.times', { n: app.user?.powerbank_reward_balance + (hourDiff >= +booster?.n1 ? 1 : app?.user?.powerbank_uses_left) })}</span> ${locale.value == 'uk' ? 'безкоштовно' : locale.value == 'ru' ? 'бесплатно' : 'for free'}`
            } else {
              additional = booster?.[`additional_info1${loc_add.value}`]
            }
          }
        }
      } else if ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) {
        status = booster?.[`status1${loc_add.value}`]
        if (app?.user?.powerbank_uses_left + app.user?.powerbank_reward_balance > 0) {
          additional = `<span class="!text-[#FCD909] font-bold flex items-center gap-1">${premiumActive.value ? `<img src="${kingImg}" style="width: 14px; height: 13px;"/>` : ''} ${t('common.times', { n: app?.user?.powerbank_uses_left + app.user?.powerbank_reward_balance + 2 })}</span> ${locale.value == 'uk' ? 'безкоштовно' : locale.value == 'ru' ? 'бесплатно' : 'for free'} ${!premiumActive.value ? '<span class="!text-[#FCD909]">(SBT)</span>' : ''}`
        } else {
          additional = `<span class="!text-[#FCD909] font-bold flex items-center gap-1">${premiumActive.value ? `<img src="${kingImg}" style="width: 14px; height: 13px;"/>` : ''} ${locale.value == 'uk' ? '2 рази' : locale.value == 'ru' ? '2 раза' : '2 times'}</span> ${locale.value == 'uk' ? 'безкоштовно' : locale.value == 'ru' ? 'бесплатно' : 'for free'} ${!premiumActive.value ? '<span class="!text-[#FCD909]">(SBT)</span>' : ''}`
        }
      } else {
        status = booster?.[`status1${loc_add.value}`]
        if (app?.user?.powerbank_uses_left + app.user?.powerbank_reward_balance > 0) {
          additional = `<span class="font-bold flex items-center gap-1">${t('common.times', { n: app?.user?.powerbank_uses_left + app.user?.powerbank_reward_balance + 1 })}</span> ${locale.value == 'uk' ? 'безкоштовно' : locale.value == 'ru' ? 'бесплатно' : 'for free'}`
        } else {
          additional = booster?.[`additional_info1${loc_add.value}`]
        }
      }
    }
    if (booster?.slug == 'magnit') {
      const magnitBlock = app.timed_nfts.find(el => el.name == 'Magnetic ring')
      if (new Date(magnitBlock?.block_until) > new Date()) {
        status = `<span class="!text-[#FCD909]">${t('common.connect')}</span>`
        additional = `<img src="${timeImg}" style="width: 12px; height: 13px;"/> ${getTimeRemaining(magnitBlock?.block_until).time}`
      } else if (app?.user?.magnit_expires) {
        const daysDiff = Math.max(
          0,
          Math.round((new Date(app?.user?.magnit_expires) - new Date()) / (1000 * 60 * 60 * 24)),
        )
        if (daysDiff > 0) {
          status = booster?.[`status2${loc_add.value}`]
          additional = magnitIsForever.value
            ? `<img src="${mintableImg}" style="width: 12px; height: 13px;"/> ${t('common.forever')}`
            : booster?.[`additional_info2${loc_add.value}`]?.replace(
              '{N}',
              t('common.days', { n: +daysDiff })
            )
        } else {
          status = booster?.[`status1${loc_add.value}`]
          additional = paymentRadio.value == 'ton' ? t('common.not_bought') : booster?.[`additional_info1${loc_add.value}`]
        }
      } else {
        status = booster?.[`status1${loc_add.value}`]
        additional = paymentRadio.value == 'ton' ? t('common.not_bought') : booster?.[`additional_info1${loc_add.value}`]
      }
    }
    if (booster?.slug == 'asic_manager') {
      const managerBlock = app.timed_nfts.find(el => el.name == 'ASIC Manager')
      if (new Date(managerBlock?.block_until) > new Date()) {
        status = `<span class="!text-[#FCD909]">${t('common.connect')}</span>`
        additional = `<img src="${timeImg}" style="width: 12px; height: 13px;"/> ${getTimeRemaining(managerBlock?.block_until).time}`
      } else
        if (app?.user?.manager_expires) {
          const daysDiff = Math.max(
            0,
            Math.round((new Date(app?.user?.manager_expires) - new Date()) / (1000 * 60 * 60 * 24)),
          )
          if (daysDiff > 0) {
            status = booster?.[`status2${loc_add.value}`]
            additional = magnitIsForever.value
              ? `<img src="${mintableImg}" style="width: 12px; height: 13px;"/> ${t('common.forever')}`
              : booster?.[`additional_info2${loc_add.value}`]?.replace(
                '{N}',
                t('common.days', { n: +daysDiff })
              )
          } else {
            status = booster?.[`status1${loc_add.value}`]
            additional = paymentRadio.value == 'ton' ? t('common.not_bought') : booster?.[`additional_info1${loc_add.value}`]
          }
        } else {
          status = booster?.[`status1${loc_add.value}`]
          additional = paymentRadio.value == 'ton' ? t('common.not_bought') : booster?.[`additional_info1${loc_add.value}`]
        }
    }
    return { status, additional, booster }
  }).value
}
const priceByHash = app.hashrate
  ? Math.min(
    [...app.hashrate]
      ?.sort((a, b) => a.hashrate - b.hashrate)
      ?.findIndex((h) => app?.user?.mining_farm_speed < h.hashrate) + 1,
    7,
  ) || Math.min(app?.hashrate?.length + 1, 7)
  : 1

const getTotalStarsPrice = (item) => {
  return computed(() => {
    let sum = 0
    let price
    if (item?.slug == 'azot') {
      sum = (paymentRadio.value == 'fbtc' ? item?.price1_fbtc : item?.price1) + item?.n1 * app?.user?.azot_counts
      if (((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) && paymentRadio.value == 'stars') {
        sum = Math.floor(sum * (100 - ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 5 : ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 10 : 0)) / 100)
      }
    } else if (item?.slug == 'jarvis') {
      price = `price${app?.user?.station_type ? (Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3) >= 7 ? 7 : Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3)) : 1}${paymentRadio.value == 'fbtc' ? "_fbtc" : ""}`
      sum = item?.[price] * boosters_count.value[item?.slug]
      if (((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) && paymentRadio.value == 'stars') {
        sum = Math.floor(sum * (100 - ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 5 : ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 10 : 0)) / 100)
      }
      if (boosters_count.value[item?.slug] >= 5) {
        sum *= (100 - Math.min(boosters_count.value[item?.slug], 30)) / 100
      }
    } else if (item?.slug == 'cryo') {
      price = `price${app?.user?.station_type ? (Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3) >= 7 ? 7 : Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3)) : 1}${paymentRadio.value == 'fbtc' ? "_fbtc" : ""}`
      sum = item?.[price] * boosters_count.value[item?.slug]
      if (((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) && paymentRadio.value == 'stars') {
        sum = Math.floor(sum * (100 - ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 5 : ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 10 : 0)) / 100)
      }
      if (boosters_count.value[item?.slug] >= 5) {
        sum *= (100 - Math.min(boosters_count.value[item?.slug], 30)) / 100
      }
    } else if (item?.slug == 'autostart') {
      sum = (paymentRadio.value == 'fbtc' ? item?.price1_fbtc : item?.price1) * boosters_count.value[item?.slug]
      if (((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) && paymentRadio.value == 'stars') {
        sum = Math.floor(sum * (100 - ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 5 : ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 10 : 0)) / 100)
      }
    } else if (item?.slug == 'powerbank') {
      price = `price${priceByHash}${paymentRadio.value == 'fbtc' ? "_fbtc" : ""}`
      sum = item?.[price] * boosters_count.value[item?.slug]
      if (((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) && paymentRadio.value == 'stars') {
        sum = Math.floor(sum * (100 - ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 5 : ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 10 : 0)) / 100)
      }
    } else if (item?.slug == 'magnit') {
      price = `price${priceByHash}${paymentRadio.value == 'fbtc' ? "_fbtc" : ""}`
      sum = item?.[price] * boosters_count.value[item?.slug]
      if (((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) && paymentRadio.value == 'stars') {
        sum = Math.floor(sum * (100 - ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 5 : ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 10 : 0)) / 100)
      }
      if (boosters_count.value[item?.slug] >= 5) {
        sum *= (100 - Math.min(boosters_count.value[item?.slug], 30)) / 100
      }
    } else if (item?.slug == 'asic_manager') {
      price = `price${priceByHash}${paymentRadio.value == 'fbtc' ? "_fbtc" : ""}`
      sum = item?.[price] * boosters_count.value[item?.slug]
      if (((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) && paymentRadio.value == 'stars') {
        sum = Math.floor(sum * (100 - ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 5 : ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 10 : 0)) / 100)
      }
      if (boosters_count.value[item?.slug] >= 5) {
        sum *= (100 - Math.min(boosters_count.value[item?.slug], 30)) / 100
      }
    } else if (item?.slug == 'electrics') {
      price = `price${app?.user?.station_type ? (Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3) >= 7 ? 7 : Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3)) : 1}${paymentRadio.value == 'fbtc' ? "_fbtc" : ""}`
      sum = item?.[price] * boosters_count.value[item?.slug]
      if (((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) && paymentRadio.value == 'stars') {
        sum = Math.floor(sum * (100 - ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 5 : ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 10 : 0)) / 100)
      }
      if (boosters_count.value[item?.slug] >= 5) {
        sum *= (100 - Math.min(boosters_count.value[item?.slug], 30)) / 100
      }
    } else if (item?.slug == 'premium_sub') {
      price = `price${app?.user?.station_type ? (Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3) >= 7 ? 7 : Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3)) : 1}${paymentRadio.value == 'fbtc' ? "_fbtc" : ""}`
      sum = item?.[price] * boosters_count.value[item?.slug]
      if (((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft)) && paymentRadio.value == 'stars') {
        sum = Math.floor(sum * (100 - ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 5 : ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft)) ? 10 : 0)) / 100)
      }
      if (boosters_count.value[item?.slug] >= 5) {
        sum *= (100 - Math.min(boosters_count.value[item?.slug], 30)) / 100
      }
    }
    return Math.ceil(sum)
  }).value
}

async function activateBooster(booster) {
  if (!booster) return
  if (booster?.slug == 'powerbank' && app?.user?.is_powerbank_active) return
  if (booster?.slug == 'magnit' && paymentRadio.value !== 'ton') return
  let free_boost = isFreeBooster(booster)
  try {
    const activate_url = paymentRadio.value == 'fbtc' ? "tasks/activate_booster_fbtc/" : "tasks/activate_booster/"
    const res = await host.post(activate_url, {
      slug: booster?.slug,
      day_count: boosters_count.value[booster?.slug] || null,
    })
    if (res.status == 200) {
      if (free_boost || paymentRadio.value == 'fbtc') {
        await app.initUser()
        modalStatus.value = 'success'
        modalTitle.value = t('notification.st_success')
        modalBody.value = booster?.[`popup${loc_add.value}`].replace(
          '{N}',
          t('common.days', { n: +boosters_count.value[booster?.slug] })
        )
        openModal.value = true
      } else {
        const invoiceLink = res.data?.link
        tg.openInvoice(invoiceLink, async (status) => {
          if (status == 'paid') {
            await app.initUser()
            modalStatus.value = 'success'
            modalTitle.value = t('notification.st_success')
            modalBody.value = booster?.[`popup${loc_add.value}`].replace(
              '{N}',
              t('common.days', { n: +boosters_count.value[booster?.slug] })
            )
            openModal.value = true
          }
        })
      }
    } else {
      console.log(res)
      modalStatus.value = 'error'
      modalTitle.value = t('notification.st_error')
      modalBody.value = t('notification.imposible_activate_booster')
      openModal.value = true
    }
  } catch (err) {
    console.log(err)
    modalStatus.value = 'error'
    modalTitle.value = t('notification.st_error')
    modalBody.value = t('notification.imposible_activate_booster')
    openModal.value = true
  }
}

const isFreeBooster = (booster) => {
  return computed(() => {
    if (
      booster?.slug == 'azot' &&
      (((new Date() - new Date(app?.user?.azot_activated)) / (1000 * 60 * 60) >= 24) || app?.user?.azot_uses_left + app.user?.azot_reward_balance > 0)
    ) { return true }
    if (booster?.slug == 'powerbank' && app?.user?.powerbank_activated == null) { return true }
    if (booster?.slug == 'powerbank' && app?.user?.powerbank_activated != null) {
      if (!app?.user?.is_powerbank_active && app?.user?.powerbank_uses_left + app.user?.powerbank_reward_balance > 0) return true
      if (new Date() - new Date(app?.user?.powerbank_activated) >= booster.n1 * 3600000) return true
    }
    return false
  }).value
}

const isActiveBooster = (booster) => {
  return computed(() => {
    if (
      booster?.slug == 'azot' &&
      new Date() - new Date(app?.user?.azot_activated) / (1000 * 60 * 60) < 24
    )
      return true
    if (
      booster?.slug == 'jarvis' &&
      app?.user?.jarvis_expires &&
      (new Date(app?.user?.jarvis_expires) - new Date()) / (1000 * 60 * 60 * 24) >= 0
    )
      return true
    if (
      booster?.slug == 'electrics' &&
      app?.user?.electrics_expires &&
      (new Date(app?.user?.electrics_expires) - new Date()) / (1000 * 60 * 60 * 24) >= 0
    )
      return true
    if (
      booster?.slug == 'premium_sub' &&
      app?.user?.premium_sub_expires &&
      (new Date(app?.user?.premium_sub_expires) - new Date()) / (1000 * 60 * 60 * 24) >= 0
    )
      return true
    if (
      booster?.slug == 'cryo' &&
      app?.user?.cryo_expires &&
      (new Date(app?.user?.cryo_expires) - new Date()) / (1000 * 60 * 60 * 24) >= 0
    )
      return true
    if (booster?.slug == 'autostart' && app?.user?.autostart_count > 0) return true
    if (booster?.slug == 'powerbank' && app?.user?.is_powerbank_active) return true
    if (
      booster?.slug == 'magnit' &&
      (new Date(app?.user?.magnit_expires) - new Date()) / (1000 * 60 * 60 * 24) <= 0
    )
      return true
    if (
      booster?.slug == 'asic_manager' &&
      (new Date(app?.user?.manager_expires) - new Date()) / (1000 * 60 * 60 * 24) <= 0
    )
      return true
    return false
  }).value
}

const boosters_count = ref({
  azot: 1,
  jarvis: 1,
  cryo: 1,
  autostart: 1,
  powerbank: 1,
  magnit: 1,
  asic_manager: 1,
  electrics: 1,
  premium_sub: 1
})

const filteredBoosters = computed(() => {
  const inclSlug = isMiners.value
    ? paymentRadio.value == 'ton' ? ['magnit', 'asic_manager'] : ['powerbank', 'magnit', 'asic_manager']
    : paymentRadio.value == 'ton' ? ['jarvis', 'cryo'] : ['azot', 'jarvis', 'cryo', 'autostart', 'electrics', 'premium_sub']
  return boosters.value?.filter((el) => inclSlug.includes(el?.slug))
})

let timeoutId = null
async function updateData() {
  try {
    await app.initBoosters()
    await app.initUser()
  } catch (err) {
    console.log(err)
  } finally {
    timeoutId = setTimeout(() => {
      updateData()
    }, 3000)
  }
}

const decrement = (item) => {
  if (boosters_count.value[item?.slug] && boosters_count.value[item?.slug] > 1) {
    boosters_count.value[item?.slug] -= 1
  }
}

const increment = (item) => {
  if (!item?.slug || !boosters_count.value[item?.slug]) return

  const slug = item?.slug
  const expiresMap = {
    jarvis: 'jarvis_expires',
    cryo: 'cryo_expires',
    magnit: 'magnit_expires',
    asic_manager: 'manager_expires',
    electrics: 'electrics_expires',
    premium_sub: 'premium_sub_expires'
  }

  const daysDiff =
    expiresMap[slug] && app.user?.[expiresMap[slug]]
      ? Math.max(
        0,
        Math.floor((new Date(app.user?.[expiresMap[slug]]) - new Date()) / (1000 * 60 * 60 * 24)),
      )
      : slug === 'autostart'
        ? null
        : 0

  if (slug === 'autostart' || boosters_count.value[slug] < 30 - daysDiff) {
    boosters_count.value[slug]++
  }
}

onMounted(() => {
  updateData()
})

onUnmounted(() => {
  if (timeoutId) {
    clearTimeout(timeoutId)
    timeoutId = null
  }
})
</script>

<template>
  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
  <div class="boosts">
    <div class="top-panel">
      <h1>{{ t('boost.title') }}</h1>
      <button class="close" @click="app.initScreen()">
        <Exit :width="16" style="color: #fff" />
      </button>
    </div>
    <div class="boost-toggle">
      <label for="filter" class="switch" aria-label="Toggle Filter">
        <input type="checkbox" v-model="isMiners" id="filter" />
        <span>{{ t('boost.energizer') }}</span>
        <span>{{ t('boost.miner') }}</span>
      </label>
    </div>
    <div class="payment-radio-container">
     <!-- <div class="radio-payment">
        <input name="radio-group" id="radio2" v-model="paymentRadio" value="ton" class="radio-payment__input"
          type="radio">
        <label for="radio2" class="radio-payment__label">
          <img src="@/assets/TON.png" width="28px" />
          <span v-if="paymentRadio == 'ton'">{{ t('boost.eternal') }}</span>
          <span class="radio-payment__custom"></span>
        </label>
      </div> -->
      <div class="radio-payment">
        <input name="radio-group" id="radio1" v-model="paymentRadio" value="fbtc" class="radio-payment__input"
          type="radio">
        <label for="radio1" class="radio-payment__label temp">
          <img src="@/assets/fBTC.webp" width="28px" />
          <span v-if="paymentRadio == 'fbtc'">{{ t('boost.temporary') }}</span>
          <span class="radio-payment__custom"></span>
        </label>
      </div>
      <div class="radio-payment">
        <input name="radio-group" id="radio3" v-model="paymentRadio" value="stars" class="radio-payment__input"
          type="radio">
        <label for="radio3" class="radio-payment__label temp">
          <img src="@/assets/wheel_stars.png" width="28px" />
          <span v-if="paymentRadio == 'stars'">{{ t('boost.temporary') }}</span>
          <span class="radio-payment__custom"></span>
        </label>
      </div>
    </div>
    <div class="boost-list" ref="boostList">
      <div class="boost-list-item" v-for="(item, index) in filteredBoosters" :key="index">
        <div class="boost-list-item-data">
          <div class="booster-data">
            <img v-if="item?.icon" :src="item?.icon" width="65px" height="65px" style="border-radius: 15%" />
            <div v-if="item?.[`title${loc_add}`]" class="booster-info">
              <h3>{{ item?.[`title${loc_add}`] }}</h3>
              <span class="booster-status"
                :class="{ active: ['Активно', 'Active', 'В наличии', 'В наявності', 'In stock'].includes(parseBoosterInfo(item).status) }"
                v-html="parseBoosterInfo(item).status"></span>
              <span class="booster-additional-info" v-html="parseBoosterInfo(item).additional"></span>
              <span v-if="((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft)) && (item?.slug !== 'azot' && item?.slug !== 'powerbank' && item?.slug !== 'premium_sub') && paymentRadio == 'stars' && (
                item?.slug === 'cryo' ? !cryoIsForever && !cryoBlocked :
                  item?.slug === 'jarvis' ? !jarvisIsForever && !jarvisBlocked :
                    item?.slug == 'magnit' ? !magnitIsForever && !magnitBlocked :
                      item?.slug === 'asic_manager' ? !managerIsForever && !managerBlocked : true
              )" class="!text-[#FCD909] !font-bold">SBT</span>
              <span v-if="premiumActive && (item?.slug !== 'azot' && item?.slug !== 'powerbank' && item?.slug !== 'premium_sub') && paymentRadio == 'stars' && (
                item?.slug === 'cryo' ? !cryoIsForever && !cryoBlocked :
                  item?.slug === 'jarvis' ? !jarvisIsForever && !jarvisBlocked :
                    item?.slug == 'magnit' ? !magnitIsForever && !magnitBlocked :
                      item?.slug === 'asic_manager' ? !managerIsForever && !managerBlocked : true
              )" class="!text-[#FCD909] !font-bold">{{ t('boost.king') }}</span>
            </div>
          </div>
          <div class="btn-group">
            <div v-if="
              (paymentRadio == 'stars' || paymentRadio == 'fbtc') &&
              isFreeBooster(item) == false &&
              item?.slug !== 'azot' &&
              item?.slug !== 'powerbank' &&
              item?.slug !== 'magnit' &&
              (
                item?.slug === 'cryo' ? !cryoIsForever && !cryoBlocked :
                  item?.slug === 'jarvis' ? !jarvisIsForever && !jarvisBlocked :
                    // item?.slug == 'magnit' ? !magnitIsForever :
                    item?.slug === 'asic_manager' ? !managerIsForever && !managerBlocked : true
              )
            " class="boost-counter">
              <button @click="decrement(item)">-</button>
              <!-- <span>{{ boosters_count?.[item?.slug] +
                (item?.slug == "autostart" ? " шт." : " " +
                  getDayOrHour(boosters_count?.[item?.slug], 'd')) }}</span> -->
              <span v-if="
                item?.slug == 'magnit' ||
                item?.slug == 'jarvis' ||
                item?.slug == 'cryo' ||
                item?.slug == 'asic_manager' ||
                item?.slug == 'autostart' ||
                item?.slug == 'electrics' ||
                item?.slug == 'premium_sub'
              " class="flex flex-col justify-center items-center">{{
                (item?.slug == 'autostart'
                  ? t('common.pcs', { n: boosters_count?.[item?.slug] })
                  : t('common.days', { n: boosters_count?.[item?.slug] }))
              }}
                <label v-if="boosters_count?.[item?.slug] >= 5 && item?.slug !== 'autostart'">{{
                  t('common.discount') }}
                  {{
                    Math.min(boosters_count?.[item?.slug], 30) + (paymentRadio == 'stars' && ((app?.user?.has_gold_sbt &&
                      app?.user?.has_gold_sbt_nft) || (premiumActive && item?.slug !== 'premium_sub'))
                      ? 10 : (app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft && paymentRadio == 'stars')
                        ? 5 : 0)
                  }}%</label>
                <label
                  v-if="boosters_count?.[item?.slug] < 5 && (((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || (premiumActive && item?.slug !== 'premium_sub')) && paymentRadio == 'stars') && item?.slug !== 'autostart'">{{
                    t('common.discount') }}
                  {{ paymentRadio == 'stars' && ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) ||
                    (premiumActive && item?.slug !==
                      'premium_sub')) ? 10 :
                    (app?.user?.has_silver_sbt &&
                      app?.user?.has_silver_sbt_nft && paymentRadio == 'stars') ? 5 : 0 }}%</label>
                <label
                  v-if="((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || (premiumActive && item?.slug !== 'premium_sub')) && item?.slug == 'autostart' && paymentRadio == 'stars'">{{
                    t('common.discount') }}
                  {{ ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || (premiumActive && item?.slug !==
                    'premium_sub')) ? 10 :
                    (app?.user?.has_silver_sbt &&
                      app?.user?.has_silver_sbt_nft) ? 5 : 0 }}%</label>
              </span>
              <span v-else>{{
                (item?.slug == 'autostart'
                  ? t('common.pcs', { n: boosters_count?.[item?.slug] })
                  : t('common.days', { n: boosters_count?.[item?.slug] }))
              }}</span>
              <button @click="increment(item)">+</button>
            </div>
            <div v-if="
              paymentRadio == 'ton'
              && ((item?.slug == 'cryo' && !cryoIsForever && !cryoBlocked) ||
                (item?.slug == 'jarvis' && !jarvisIsForever && !jarvisBlocked) ||
                (item?.slug == 'magnit' && !magnitIsForever && !magnitBlocked) ||
                (item?.slug == 'asic_manager' && !managerIsForever && !managerBlocked))
            ">
              <span class="always-text">{{ t('common.forever') }}</span>
            </div>
            <button class="booster-btn" :class="{
              speedup: (item?.slug == 'jarvis' && jarvisBlocked) || (item?.slug == 'cryo' && cryoBlocked) || (item?.slug == 'magnit' && magnitBlocked) || (item?.slug == 'asic_manager' && managerBlocked),
              forever: paymentRadio == 'ton' && item?.slug !== 'azot' && item?.slug !== 'autostart' && !((item?.slug == 'cryo' && cryoBlocked) || (item?.slug == 'jarvis' && jarvisBlocked) || (item?.slug == 'magnit' && magnitBlocked) || (item?.slug == 'asic_manager' && managerBlocked)),
              bought: ((item?.slug == 'cryo' && cryoIsForever && !cryoBlocked) || (item?.slug == 'jarvis' && jarvisIsForever && !jarvisBlocked) || (item?.slug == 'magnit' && magnitIsForever && !magnitBlocked) || (item?.slug == 'asic_manager' && managerIsForever && !managerBlocked)),
              stars: (paymentRadio == 'stars' || paymentRadio == 'fbtc') && isFreeBooster(item) == false && item?.slug !== 'powerbank' && item?.slug !== 'magnit',
              disabled: (item?.slug == 'powerbank' && app?.user?.is_powerbank_active) || (item?.slug == 'magnit' && paymentRadio !== 'ton'),
            }" @click="async () => {
              if ((item?.slug == 'cryo' && cryoIsForever && !cryoBlocked) ||
                (item?.slug == 'jarvis' && jarvisIsForever && !jarvisBlocked) ||
                (item?.slug == 'magnit' && magnitIsForever && !magnitBlocked) ||
                (item?.slug == 'asic_manager' && managerIsForever && !managerBlocked)) {
                return;
              }
              else if ((item?.slug == 'cryo' && cryoBlocked) ||
                (item?.slug == 'jarvis' && jarvisBlocked) ||
                (item?.slug == 'magnit' && magnitBlocked) ||
                (item?.slug == 'asic_manager' && managerBlocked)) {
                const res = await host.post('timed-nft-stars/', {
                  timed_nft_id: app.timed_nfts.find(el => el.name == foreverBoosts?.[item?.slug]?.name)?.id,
                })
                if (res.status == 200) {
                  const invoiceLink = res.data?.link
                  tg.openInvoice(invoiceLink, async (status) => {
                    if (status == 'paid') {
                      await app.initUser()
                    }
                  })
                }
              }
              else if (paymentRadio == 'ton') {
                tg.openLink(foreverBoosts?.[item?.slug]?.link)
                return;
              } else {
                activateBooster(item)
              }
            }
            ">
              <span class="flex text-[12px] items-center gap-1"
                v-if="(item?.slug == 'jarvis' && jarvisBlocked) || (item?.slug == 'cryo' && cryoBlocked) || (item?.slug == 'magnit' && magnitBlocked) || (item?.slug == 'asic_manager' && managerBlocked)">
                {{ t('common.speedup') }}
                <img src="@/assets/wheel_stars.png" width="18px" height="18px" />
              </span>
              <span v-else-if="item?.slug == 'magnit' && paymentRadio !== 'ton'">{{ t('common.sold_out') }}</span>
              <span v-else-if="item?.slug == 'powerbank' && app?.user?.is_powerbank_active">{{ t('common.active')
              }}</span>
              <span v-else-if="isFreeBooster(item) || item?.slug == 'powerbank'">{{ t('common.free') }}</span>
              <span
                v-else-if="(paymentRadio == 'stars' || paymentRadio == 'fbtc') && isActiveBooster(item) && item?.slug == 'jarvis' && !jarvisIsForever">
                {{ t('common.continue') }}
                <div
                  v-if="boosters_count?.[item?.slug] >= 5 || (((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive) && paymentRadio == 'stars')"
                  class="flex justify-center items-center font-bold gap-1 text-[12px] text-[#FCD909]">
                  <img v-show="paymentRadio == 'fbtc'" src="@/assets/fBTC.webp" width="15px" alt="Stars" />
                  <img v-show="paymentRadio == 'stars'" src="@/assets/stars.png" width="15px" alt="Stars" />
                  {{ getTotalStarsPrice(item) }}
                  <span class="text-[8px] text-white font-bold line-through decoration-red-400 decoration-[2px]">{{
                    Math.ceil((paymentRadio == 'fbtc' ? item?.price1_fbtc : item?.price1) *
                      boosters_count?.[item?.slug]) }}</span>
                </div>
                <div v-else class="flex justify-center items-center gap-1 text-[12px]">
                  <img v-show="paymentRadio == 'fbtc'" src="@/assets/fBTC.webp" width="15px" alt="Stars" />
                  <img v-show="paymentRadio == 'stars'" src="@/assets/stars.png" width="15px" alt="Stars" />
                  {{ getTotalStarsPrice(item) }}
                </div>
              </span>
              <span class="p-0 m-0 w-full h-full text-nowrap" v-else-if="
                paymentRadio == 'ton' &&
                ((item?.slug == 'cryo' && cryoIsForever && !cryoBlocked) ||
                  (item?.slug == 'jarvis' && jarvisIsForever && !jarvisBlocked) ||
                  (item?.slug == 'magnit' && magnitIsForever && !magnitBlocked) ||
                  (item?.slug == 'asic_manager' && managerIsForever && !managerBlocked))
              ">{{ t('common.bought') }}</span>
              <span class="p-0 m-0 w-full h-full text-nowrap" v-else-if="
                (paymentRadio == 'stars' || paymentRadio == 'fbtc') &&
                ((item?.slug == 'cryo' && cryoIsForever && !cryoBlocked) ||
                  (item?.slug == 'jarvis' && jarvisIsForever && !jarvisBlocked) ||
                  (item?.slug == 'magnit' && magnitIsForever && !magnitBlocked) ||
                  (item?.slug == 'asic_manager' && managerIsForever && !managerBlocked))
              ">{{ t('common.bought') }}</span>
              <span v-else class="p-0 m-0 w-full h-full text-nowrap">
                {{ t('common.buy') }} {{ paymentRadio == 'ton' ? t('common.getgems') : '' }}
                <div v-if="
                  (paymentRadio == 'stars' || paymentRadio == 'fbtc') &&
                  boosters_count?.[item?.slug] >= 5 &&
                  (item?.slug == 'jarvis' ||
                    item?.slug == 'magnit' ||
                    item?.slug == 'cryo' ||
                    item?.slug == 'asic_manager' ||
                    item?.slug == 'electrics' ||
                    item?.slug == 'premium_sub'
                  )
                " class="flex justify-center items-center font-bold gap-1 text-[12px] text-[#FCD909]">
                  <img v-show="paymentRadio == 'fbtc'" src="@/assets/fBTC.webp" width="15px" alt="Stars" />
                  <img v-show="paymentRadio == 'stars'" src="@/assets/stars.png" width="15px" alt="Stars" />
                  {{ getTotalStarsPrice(item) }}
                  <span v-if="item?.slug == 'jarvis' || item?.slug == 'cryo'"
                    class="text-[8px] text-white font-bold line-through decoration-red-400 decoration-[2px]">{{
                      Math.ceil(
                        item?.[
                        `price${app?.user?.station_type
                          ? Math.ceil(
                            app.gen_config.find(
                              (el) => el?.station_type == app?.user?.station_type,
                            )?.id / 3,
                          ) >= 7
                            ? 7
                            : Math.ceil(
                              app.gen_config.find(
                                (el) => el?.station_type == app?.user?.station_type,
                              )?.id / 3,
                            )
                          : 1
                        }${paymentRadio == 'fbtc' ? "_fbtc" : ""}`
                        ] * boosters_count?.[item?.slug],
                      )
                    }}</span>
                  <span v-else
                    class="text-[8px] text-white font-bold line-through decoration-red-400 decoration-[2px]">{{
                      item?.slug == 'magnit' || item?.slug == 'asic_manager'
                        ? Math.ceil(item?.[`price${priceByHash}${paymentRadio == 'fbtc' ? "_fbtc" : ""}`] *
                          boosters_count?.[item?.slug])
                        : Math.ceil((paymentRadio == 'fbtc' ? item?.price1_fbtc : item?.price1) *
                          boosters_count?.[item?.slug])
                    }}</span>
                </div>
                <div v-else-if="
                  (paymentRadio == 'stars') &&
                  boosters_count?.[item?.slug] < 5 &&
                  ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || (premiumActive && item?.slug !== 'premium_sub')) &&
                  (item?.slug == 'jarvis' ||
                    item?.slug == 'magnit' ||
                    item?.slug == 'cryo' ||
                    item?.slug == 'asic_manager' ||
                    item?.slug == 'electrics' ||
                    item?.slug == 'premium_sub'
                  )
                " class="flex justify-center items-center font-bold gap-1 text-[12px] text-[#FCD909]">
                  <img v-show="paymentRadio == 'fbtc'" src="@/assets/fBTC.webp" width="15px" alt="Stars" />
                  <img v-show="paymentRadio == 'stars'" src="@/assets/stars.png" width="15px" alt="Stars" />
                  {{ getTotalStarsPrice(item) }}
                  <span v-if="item?.slug == 'jarvis' || item?.slug == 'cryo'"
                    class="text-[8px] text-white font-bold line-through decoration-red-400 decoration-[2px]">{{
                      Math.ceil(
                        item?.[
                        `price${app?.user?.station_type
                          ? Math.ceil(
                            app.gen_config.find(
                              (el) => el?.station_type == app?.user?.station_type,
                            )?.id / 3,
                          ) >= 7
                            ? 7
                            : Math.ceil(
                              app.gen_config.find(
                                (el) => el?.station_type == app?.user?.station_type,
                              )?.id / 3,
                            )
                          : 1
                        }${paymentRadio == 'fbtc' ? "_fbtc" : ""}`
                        ] * boosters_count?.[item?.slug],
                      )
                    }}</span>
                  <span v-else
                    class="text-[8px] text-white font-bold line-through decoration-red-400 decoration-[2px]">{{
                      item?.slug == 'magnit' || item?.slug == 'asic_manager'
                        ? Math.ceil(item?.[`price${priceByHash}${paymentRadio == 'fbtc' ? "_fbtc" : ""}`] *
                          boosters_count?.[item?.slug])
                        : Math.ceil((paymentRadio == 'fbtc' ? item?.price1_fbtc : item?.price1) *
                          boosters_count?.[item?.slug])
                    }}</span>
                </div>
                <div v-else-if="
                  (paymentRadio == 'stars') &&
                  item?.slug == 'autostart' &&
                  ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || (premiumActive && item?.slug !== 'premium_sub'))
                " class="flex justify-center items-center font-bold gap-1 text-[12px] text-[#FCD909]">
                  <img v-show="paymentRadio == 'fbtc'" src="@/assets/fBTC.webp" width="15px" alt="Stars" />
                  <img v-show="paymentRadio == 'stars'" src="@/assets/stars.png" width="15px" alt="Stars" />
                  {{ getTotalStarsPrice(item) }}
                  <span class="text-[8px] text-white font-bold line-through decoration-red-400 decoration-[2px]">
                    {{ Math.ceil((paymentRadio == 'fbtc' ? item?.price1_fbtc : item?.price1) *
                      boosters_count?.[item?.slug]) }}</span>
                </div>
                <div v-else-if="(paymentRadio == 'stars' || paymentRadio == 'fbtc')"
                  class="flex justify-center items-center font-bold gap-1 text-[12px]">
                  <img v-show="paymentRadio == 'fbtc'" src="@/assets/fBTC.webp" width="15px" alt="Stars" />
                  <img v-show="paymentRadio == 'stars'" src="@/assets/stars.png" width="15px" alt="Stars" />
                  {{ getTotalStarsPrice(item) }}
                </div>
                <div v-else-if="
                  paymentRadio == 'ton' && item?.slug !== 'azot' && item?.slug !== 'autostart'
                " class="flex justify-center items-center font-bold gap-1 text-[12px]">
                  {{ t('common.from') }}
                  <img src="@/assets/TON.png" width="15px" alt="TON" />
                  {{ foreverBoosts?.[item?.slug]?.price }}
                  <span class="text-[8px] text-black font-bold line-through decoration-red-400 decoration-[2px]">
                    {{ foreverBoosts?.[item?.slug]?.old_price }}</span>
                </div>
              </span>
            </button>
          </div>
        </div>
        <div class="boost-list-item-notif">{{ item?.[`description${loc_add}`] }}</div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.boosts {
  position: absolute;
  bottom: -145px;
  z-index: 100;
  width: 100%;
  height: 100%;
  display: flex;
  padding-bottom: 120px;
  flex-direction: column;
  align-items: center;
  border-radius: 1rem 1rem 0 0;
  border-top: 1px solid #ffffff90;
  background:
    url('@/assets/asics-shop-bg.webp') no-repeat top center,
    radial-gradient(ellipse 60% 50% at top center, #31cfff95, transparent),
    #000;
  // box-shadow: 0 -10px 40px 10px #31ff8080;

  .top-panel {
    position: relative;
    display: flex;
    width: 90%;
    padding: 1rem 0;
    align-items: center;

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
      position: absolute;
      right: 0;
      width: 20%;
      display: flex;
      align-items: center;
      justify-content: end;
    }
  }

  .boost-list {
    display: flex;
    width: 90%;
    flex-direction: column;
    padding: 0px 0 50px;
    align-items: center;
    gap: 0.5rem;
    border-radius: 1rem;
    border-top: 1px solid #ffffff50;
    overflow-y: scroll;
    margin: 10px 0 -10px;
    -ms-overflow-style: none;
    scrollbar-width: none;

    &::-webkit-scrollbar {
      display: none;
    }

    &-item {
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: center;
      width: 100%;
      background: #08150a50;
      backdrop-filter: blur(5px);
      box-shadow: inset 0 0 0 1px #ffffff25;
      border-radius: 1rem;
      overflow: visible;

      &-data {
        width: 100%;
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 15px;
        gap: 10px;

        .booster-data {
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

          .booster-info {
            display: flex;
            flex-direction: column;
            justify-content: start;
            align-items: start;
            text-align: left;
            gap: 0;

            h3 {
              color: #fff;
              font-family: 'Inter';
              font-weight: bold;
              font-size: 15px;
              letter-spacing: 0%;
            }

            span {
              color: #ffffff75;
              font-family: 'Inter';
              font-weight: 400;
              font-size: 12px;
              letter-spacing: 0%;
            }

            .booster-status {
              color: #ff3b59;

              &.active {
                color: #31cfff !important;
              }
            }

            .booster-additional-info {
              display: flex;
              align-items: center;
              flex-wrap: wrap;
              gap: 0.2rem;
            }
          }
        }

        .btn-group {
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          gap: 5px;
          min-width: 35%;

          .boost-counter {
            width: 100%;
            display: flex;
            justify-content: space-around;
            align-items: center;
            gap: 10px;

            button {
              background: linear-gradient(to right, #e757ec, #9851ec, #5e7cea);
              border: 1px solid #9851ec;
              width: 25px;
              aspect-ratio: 1/1;
              border-radius: 5px;
              color: #fff;
              font-family: 'Inter';
              font-weight: bold;
              font-size: 12px;

              &:active {
                background: linear-gradient(to right, #e757ec80, #9851ec80, #5e7cea80);
              }
            }

            span {
              color: #fff;
              font-family: 'Inter';
              font-weight: bold;
              font-size: 12px;
              letter-spacing: 0px;
              min-width: max-content;

              label {
                font-size: 12px;
                color: #fcd909;
              }
            }
          }

          .booster-btn {
            width: 100%;
            min-width: fit-content;
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

            &.stars {
              display: flex;
              flex-direction: column;
              justify-content: center;
              align-items: center;
              color: #fff;
              font-size: 10px;
              padding: 5px 10px;
              background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
                linear-gradient(to left, #e757ec, #9851ec, #5e7cea);

              &:active {
                background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
                  linear-gradient(to left, #e757ec90, #9851ec90, #5e7cea90);
              }
            }


            &.speedup {
              display: flex;
              flex-direction: column;
              justify-content: center;
              align-items: center;
              color: #fff;
              font-size: 10px;
              padding: 12px 20px;
              background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
                linear-gradient(to left, #e757ec, #9851ec, #5e7cea);

              &:active {
                background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
                  linear-gradient(to left, #e757ec90, #9851ec90, #5e7cea90);
              }
            }

            &.forever {
              display: flex;
              flex-direction: column;
              justify-content: center;
              align-items: center;
              color: #000;
              font-size: 10px;
              padding: 5px 10px;
              background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
                linear-gradient(to bottom, #FCD909, #FEA400);

              &:active {
                background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
                  linear-gradient(to bottom, #FCD90990, #FEA40090);
              }
            }

            &.bought {
              display: flex;
              flex-direction: column;
              justify-content: center;
              align-items: center;
              color: #000;
              font-size: 10px;
              padding: 12px 20px;
              background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
                linear-gradient(to bottom, #FCD90980, #FEA40080);

              &:active {
                background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
                  linear-gradient(to bottom, #FCD90990, #FEA40090);
              }
            }

            &.disabled {
              background: linear-gradient(to bottom, #e2e2e2, #646464);
            }
          }

          .always-text {
            color: #fff;
            font-family: 'Inter', sans-serif;
            font-size: 12px;
            font-weight: 700;
          }
        }
      }

      &-notif {
        width: 100%;
        color: #fff;
        text-align: left;
        display: flex;
        justify-content: center;
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

  .boost-toggle {
    width: 100%;
    display: flex;
    justify-content: center;
  }

  .payment-radio-container {
    display: flex;
    margin-top: 10px;
    align-items: center;
    gap: 24px;
  }

  .radio-payment {
    display: inline-block;
    position: relative;
    cursor: pointer;
  }

  .radio-payment__input {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
  }

  .radio-payment__label {
    display: flex;
    align-items: center;
    height: 30px;
    justify-content: center;
    gap: 10px;
    padding-right: 30px;
    margin-bottom: 10px;
    position: relative;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 13px;
    color: #fff;
    cursor: pointer;
    background:
      linear-gradient(to right, transparent, #0000003C) padding-box,
      linear-gradient(to right, transparent, #00000080) border-box;
    border: 2px solid transparent;
    border-radius: 20px;
    transition: all 0.3s cubic-bezier(0.23, 1, 0.320, 1);
  }

  .radio-payment__custom {
    position: absolute;
    top: 50%;
    right: 8px;
    transform: translateY(-50%);
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 1px solid #B3B3B3;
    transition: all 0.3s cubic-bezier(0.23, 1, 0.320, 1);

    &::before {
      content: "";
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #B3B3B3;
      z-index: 50;
    }
  }

  .radio-payment__input:checked+.radio-payment__label .radio-payment__custom {
    transform: translateY(-50%) scale(0.9);
    border: 2px solid #FCD909;
    color: #FCD909;

    &::before {
      background: #FCD909;
    }
  }

  .radio-payment__input:checked+.temp .radio-payment__custom {
    transform: translateY(-50%) scale(0.9);
    border: 2px solid #31CFFF;
    color: #31CFFF;

    &::before {
      background: #31CFFF;
    }
  }

  .radio-payment__input:checked+.radio-payment__label {
    border-radius: 20px;
    background: linear-gradient(to right, transparent, #FCD90980) padding-box;

    &::before {
      content: "";
      position: absolute;
      inset: 0;
      border-radius: 20px;
      padding: 2px;
      /* control the border thickness */
      background: linear-gradient(to right, transparent, #FCD90980);
      mask:
        linear-gradient(#fff 0 0) content-box,
        linear-gradient(#fff 0 0);
      -webkit-mask-composite: xor;
      mask-composite: exclude;
      pointer-events: none;
      z-index: -1;
    }
  }

  .radio-payment__input:checked+.temp {
    background-image: linear-gradient(to right, transparent, #31CFFF80);
    border-radius: 20px;

    &::before {
      content: "";
      position: absolute;
      inset: 0;
      border-radius: 20px;
      padding: 2px;
      /* control the border thickness */
      background: linear-gradient(to right, transparent, #31CFFF80);
      mask:
        linear-gradient(#fff 0 0) content-box,
        linear-gradient(#fff 0 0);
      -webkit-mask-composite: xor;
      mask-composite: exclude;
      pointer-events: none;
      z-index: -1;
    }
  }

  .radio-payment__input:checked+.radio-payment__label {
    color: #FFF;
  }

  .radio-payment__label:hover .radio-payment__custom {
    border-color: #FCD909;
    box-shadow: 0 0 10px #FCD90980;
  }

  .temp:hover .radio-payment__custom {
    border-color: #31CFFF;
    box-shadow: 0 0 10px #31CFFF80;
  }
}

.switch {
  --_switch-bg-clr: #00000080;
  --_switch-padding: 0px;
  /* padding around button*/
  --_slider-bg-clr: #31cfff;
  /* slider color unchecked */
  --_slider-bg-clr-on: #31cfff;
  /* slider color checked */
  --_slider-txt-clr: #000000;
  --_label-padding: 0.5rem 0.7rem;
  /* padding around the labels -  this gives the switch it's global width and height */
  --_switch-easing: cubic-bezier(0.47, 1.64, 0.41, 0.8);
  /* easing on toggle switch */
  color: white;
  width: fit-content;
  display: flex;
  justify-content: center;
  position: relative;
  border-radius: 9999px;
  cursor: pointer;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  position: relative;
  isolation: isolate;
  font-family: 'Inter';
  font-size: 13px;
  font-weight: 600;
  line-height: auto;
  letter-spacing: 0px;
}

.switch input[type='checkbox'] {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

.switch>span {
  display: grid;
  place-content: center;
  transition: opacity 200ms ease-in-out 100ms;
  padding: var(--_label-padding);
}

.switch::before,
.switch::after {
  content: '';
  position: absolute;
  border-radius: inherit;
  transition: inset 100ms ease-in-out;
}

/* switch slider */
.switch::before {
  background-color: var(--_slider-bg-clr);
  inset: var(--_switch-padding) 50% var(--_switch-padding) var(--_switch-padding);
  transition:
    inset 500ms var(--_switch-easing),
    background-color 500ms ease-in-out;
  z-index: -1;
}

.switch::after {
  background-color: var(--_switch-bg-clr);
  inset: 0;
  z-index: -2;
}

/* checked - move slider to right */
.switch:has(input:checked)::before {
  background-color: var(--_slider-bg-clr-on);
  inset: var(--_switch-padding) var(--_switch-padding) var(--_switch-padding) 50%;
}

/* checked - set opacity */
.switch>span:last-of-type,
.switch>input:checked+span:first-of-type {
  opacity: 0.75;
}

.switch>input:checked~span:last-of-type {
  opacity: 1;
  color: var(--_slider-txt-clr);
}

.switch>input:not(:checked)~span:first-of-type {
  color: var(--_slider-txt-clr);
}
</style>
