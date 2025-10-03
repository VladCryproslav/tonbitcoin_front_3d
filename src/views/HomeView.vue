<script setup>
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref } from 'vue'
import { useTabsStore } from '@/stores/tabs'
import { useAppStore } from '@/stores/app'
const Investor = defineAsyncComponent(() => import('./InvestorView.vue'))
const Miner = defineAsyncComponent(() => import('./MinerView.vue'))
const Boost = defineAsyncComponent(() => import('@/components/Boost.vue'))
const Rocket = defineAsyncComponent(() => import('@/assets/rocket_launch.svg'))
import Energizer from './EnergizerView.vue'
import { TonConnectButton } from '@townsquarelabs/ui-vue'
import { useTelegram } from '@/services/telegram'
import TutorialCarousel from '@/components/TutorialCarousel.vue'
import Dashboard from '@/components/Dashboard.vue'
import { getInvestorNav } from '@/utils/asics'
import asicsSheet from '@/services/data'
import LanguageSwitch from '@/components/LanguageSwitch.vue'
import { useI18n } from 'vue-i18n'
import { useTimeRemaining } from '@/composables/useTimeRemaining'
import SpeedUpModal from '@/components/SpeedUpModal.vue'

const { tg } = useTelegram()
const { t } = useI18n()

const tabs = useTabsStore()
const app = useAppStore()
const all_asics = computed(() => app.getAsicsFromStorage())
const unlockedWallet = computed(() => {
  if (app.wallet_info) {
    return { bool: new Date(app?.wallet_info?.block_until) < new Date(), time: app?.wallet_info?.block_until }
  }
  return { bool: true, time: new Date().toISOString() }
})
const openWalletSpeedUp = ref(false)
const premiumActive = computed(() => new Date(app.user?.premium_sub_expires) >= new Date())

const showTutorial = ref(false)

const offTutorial = () => {
  showTutorial.value = false
  localStorage.setItem('showTutorial', false)
  app.setShowTutorial(false)
}

function formatNumber(value) {
  if (value >= 1000000) {
    return (value / 1000000).toFixed(1).replace(/\.?0+$/, '') + 'm';
  } else if (value >= 1000) {
    return (value / 1000).toFixed(1).replace(/\.?0+$/, '') + 'k';
  } else {
    return +(value).toFixed(2).toString();
  }
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

function showSection(block) {
  tabs.setCategory(block)
  switch (block) {
    case 'energizer':
      tabs.setBackground('#141e36')
      document.body.style.background = tabs.background
      tg.setHeaderColor(tabs.background)
      // document.querySelector('.button-container.active').style.background =
      // 'radial-gradient(ellipse 70% 25%, #31cfff, transparent 90%) padding-box, linear-gradient(to bottom, #31cfff, transparent 75%) padding-box, linear-gradient(to bottom, #ffffff, transparent 80%) border-box'
      break
    case 'miner':
      tabs.setBackground('#0B150F')
      document.body.style.background = tabs.background
      tg.setHeaderColor(tabs.background)
      // document.querySelector('.button-container.active').style.background =
      // 'radial-gradient(ellipse 70% 25%, #31ff80, transparent 90%) padding-box, linear-gradient(to bottom, #31ff80, transparent 75%) padding-box, linear-gradient(to bottom, #ffffff, transparent 80%) border-box'
      break
    case 'investor':
      tabs.setBackground('#1b1436')
      document.body.style.background = tabs.background
      tg.setHeaderColor(tabs.background)
      // document.querySelectorAll('.button-container.active').style.background =
      // 'radial-gradient(ellipse 70% 25%, #8143fc, transparent 90%) padding-box, linear-gradient(to bottom, #8143fc, transparent 75%) padding-box, linear-gradient(to bottom, #ffffff, transparent 80%) border-box'
      break
    default:
      break
  }
}
const StatEnergizer = computed(() => {
  return +(app?.user?.generation_rate * (app.user?.power / 100) * (premiumActive.value ? 1.05 : 1)).toFixed(2) || 0
})

const rentedNftTimes = computed(() =>
  (app?.rentedNfts || [])?.map(nft => useTimeRemaining(nft?.end_date))
)

const rentedPlusSpeed = computed(() => {
  return (app?.rentedNfts?.reduce((sum, item, idx) => {
    const remain = rentedNftTimes.value[idx]?.timeRemainingMs?.value ?? 0
    if (remain > 0) {
      return sum + (+item.mining_speed_tbtc * (100 - +item.owner_percentage) / 100)
    }
    return sum
  }, 0)) || 0
})

const StatMiner = computed(() => {
  if (app.user.is_mining) {
    return +(app?.user?.total_mining_speed - app?.user?.rent_total_mining_speed_minus + rentedPlusSpeed.value).toFixed(2) || 0
  } else {
    return 0
  }
})
const StatInvestor = computed(() => {
  return +(app?.staking?.filter((el) => el?.status == 'active')?.reduce((sum, item) => { return (sum += item?.reward / item?.days) }, 0) + getInvestorNav(app?.rentOutNfts, all_asics.value, asicsSheet))?.toFixed(2) || 0
})

const getDashboardFrameInfo = (side) => {
  if (side == 'energizer' || side == 'boost') {
    const latest = computed(() => app?.dashboard_info?.total_active_generation || 0)
    if (latest.value >= 100000000000000 && latest.value < 99900000000000) {
      return `${(latest.value / 1000000000000000).toFixed(2)} eW`;
    } else if (latest.value >= 100000000000 && latest.value < 99900000000000) {
      return `${(latest.value / 1000000000000).toFixed(2)} pW`;
    } else if (latest.value >= 100000000 && latest.value < 99900000000) {
      return `${(latest.value / 1000000000).toFixed(2)} tW`;
    } else if (latest.value >= 100000 && latest.value < 99900000) {
      return `${(latest.value / 1000000).toFixed(2)} gW`;
    } else if (latest.value >= 100 && latest.value < 99900) {
      return `${(latest.value / 1000).toFixed(2)} mW`;
    } else {
      return `${(latest.value).toFixed(2)} kW`;
    }
  }
  if (side == 'miner') {
    const hashrate = computed(() => app?.dashboard_info?.total_active_asic_hashrate || 0);

    if (hashrate.value >= 100000000 && hashrate.value < 99900000000) {
      return `${(hashrate.value / 1000000000).toFixed(2)} ${t('common.per_s', { value: 'Eh' })}`;
    } else if (hashrate.value >= 100000 && hashrate.value < 99900000) {
      return `${(hashrate.value / 1000000).toFixed(2)} ${t('common.per_s', { value: 'Ph' })}`;
    } else if (hashrate.value >= 100 && hashrate.value < 99900) {
      return `${(hashrate.value / 1000).toFixed(2)} ${t('common.per_s', { value: 'Th' })}`;
    } else if (hashrate.value >= 0.1 && hashrate.value < 99.9) {
      return `${(hashrate.value).toFixed(2)} ${t('common.per_s', { value: 'Gh' })}`;
    } else if (hashrate.value >= 0.0001 && hashrate.value < 0.099) {
      return `${(hashrate.value * 1000).toFixed(2)} ${t('common.per_s', { value: 'Mh' })}`;
    } else {
      return `${(hashrate.value * 1000000).toFixed(2)} ${t('common.per_s', { value: 'h' })}`;
    }
  }
  if (side == 'investor') {
    const latest = computed(() => app?.dashboard_info?.total_investor_wallet_balance || 0)
    return `${formatNumber(latest.value)} fBTC`
  }
};

onMounted(() => {
  if (app) {
    showTutorial.value = app.showTutorial
  }
})

onUnmounted(() => {
  if (timeRemainingInterval) {
    clearInterval(timeRemainingInterval)
  }
})
</script>

<template>
  <SpeedUpModal v-if="openWalletSpeedUp" @close="openWalletSpeedUp = false" wallet />
  <TutorialCarousel v-if="showTutorial" @close="offTutorial" />
  <Dashboard v-if="tabs.openDashboard" :tab="tabs.category" @close="tabs.setDashboard(false)" />
  <div class="game-container">
    <div class="header">
      <div class="first-row-panel">
        <!-- @click="tabs.setDashboard(true)" -->
        <div class="dashboard" @click="tabs.setDashboard(true)">
          <div class="dash-gradient"
            :class="{ energ: tabs.category === 'energizer' || tabs.category === 'boost', mine: tabs.category === 'miner', inv: tabs.category === 'investor' }">
          </div>
          <img class="dash-logo" src="@/assets/dash_icon.webp" alt="" />
          <div class="dashboard-info">
            <span class="dashboard-info-name">{{ t('general.top_nav.dashboard') }}</span>
            <span class="dashboard-info-score">{{ getDashboardFrameInfo(tabs.category) }}</span>
          </div>
          <img v-if="tabs.category === 'miner'" class="open-dash" src="@/assets/dash_mine.png" alt="" />
          <img v-else-if="tabs.category === 'investor'" class="open-dash" src="@/assets/dash_inv.png" alt="" />
          <img v-else class="open-dash" src="@/assets/dash_energ.png" alt="" />
        </div>
        <!-- <div class="league">
          <img src="@/assets/gold_league.png" alt="gold league" />
          <div class="league-info">
            <span class="leag-name">Silver</span>
            <span class="leag-score">0th</span>
          </div>
          <PlayLeagueIcon :width="30" style="color: #fcbb43" />
        </div> -->

        <TonConnectButton v-if="unlockedWallet.bool" />
        <div v-else class="wallet-proc-btn" @click="openWalletSpeedUp = true">
          <div class="wallet-proc-btn-info">
            <span class="label">{{ t('common.connect') }}</span>
            <span class="time">{{ getTimeRemaining(unlockedWallet.time).time }}</span>
          </div>
          <Rocket class="proc-icon" />
        </div>

        <!-- <div class="questions" @click="tg?.openTelegramLink('https://t.me/tBTCapp_bot')">?</div> -->
        <div class="questions" @click="showTutorial = true">?</div>
        <LanguageSwitch />
      </div>
      <div class="second-row-panel">
        <div class="energizer" :class="{ active: tabs.category === 'energizer' }" @click="showSection('energizer')">
          <span class="label">{{ t('general.top_nav.energizer') }}</span>
          <span class="points">+{{ StatEnergizer }} {{ t('common.per_h', { value: 'kW' }) }}</span>
        </div>
        <div class="miner" :class="{ active: tabs.category === 'miner' }" @click="showSection('miner')">
          <span class="label">{{ t('general.top_nav.miner') }}</span>
          <span class="points">+{{ StatMiner }} {{ t('common.per_h', { value: 'fBTC' }) }}</span>
        </div>
        <div class="investor" :class="{ active: tabs.category === 'investor' }" @click="showSection('investor')">
          <span class="label">{{ t('general.top_nav.investor') }}</span>
          <span class="points">+{{ StatInvestor }} {{ t('common.per_d', { value: 'fBTC' }) }}</span>
        </div>
      </div>
    </div>
    <div v-if="tabs.category === 'boost'">
      <Boost />
    </div>
    <div v-if="tabs.category === 'energizer'">
      <Energizer />
    </div>
    <div v-if="tabs.category === 'miner'">
      <Miner />
    </div>
    <div class="relative" v-if="tabs.category === 'investor'">
      <Investor />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.slide-fade-enter-active {
  transition: all 0.7s ease-out;
}

.slide-fade-enter-from {
  transform: translateX(20px);
  opacity: 0;
}

.scale-enter-active {
  transition: all .3s ease-in-out;
  transform: scale(1);
  opacity: 1;
}

.scale-enter-from {
  transform: scale(0);
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.5s ease-in-out;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100vh);
}

.game-container {
  width: 100%;
  height: calc(100% - 25px);
  margin: 0 auto;
}

.header {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  width: 90%;
  margin: 0 auto 1rem auto;

  img {
    width: 50px;
    height: 50px;
    margin-right: 14px;
  }
}

.dashboard {
  position: relative;
  display: flex;
  justify-content: space-between;
  min-width: fit-content;
  max-width: 150px;
  align-items: center;
  background: #00000040;
  border-radius: 5rem;
  gap: .25rem;
  max-height: 40px;
  border: solid 1px #ffffff1A;
  overflow: hidden;

  .dash-gradient {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 0;
    transition: all .4s ease-in-out;

    &.energ {
      background: linear-gradient(to right, #31cfff50, #31cfff25, transparent);
    }

    &.mine {
      background: linear-gradient(to right, #31FF8050, #31FF8025, transparent);
    }

    &.inv {
      background: linear-gradient(to right, #8143FC50, #8143FC25, transparent);
    }
  }

  .dash-logo {
    width: 38px;
    height: 38px;
    margin: 0;
    padding: 0;
    gap: 0;
    z-index: 1;
  }

  .dashboard-info {
    font-family: 'Inter' !important;
    display: flex;
    flex-direction: column;
    justify-content: center;
    line-height: 95%;
    z-index: 1;
    text-wrap: nowrap;

    &-name {
      font-weight: 600;
      font-size: 13px;
      color: #fff;
      opacity: 0.5;
    }

    &-score {
      font-weight: 900;
      font-size: 14px;
      color: #fff;
    }
  }

  .open-dash {
    width: 11px;
    height: 14px;
  }
}

.wallet-proc-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #0000004D;
  border-radius: 50px;
  border: solid 1px #D29E09;
  font-family: 'Inter', sans-serif !important;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  text-align: center;
  height: 40px;
  overflow: hidden;
  padding: 0 0 0 1rem;
  max-width: fit-content !important;

  &-info {
    display: flex;
    flex-direction: column;
    align-items: start;
    justify-content: center;
    height: 40px;
    width: clamp(55px, 55%, 180px);
    text-align: left;
    color: #fff;

    .label {
      display: inline-block;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
      width: 100%;
    }

    .time {
      opacity: 0.8;
    }
  }

  .proc-icon {
    min-width: 20px;
    min-height: 20px;
  }
}

.questions {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #0000004D;
  border-radius: 100%;
  border: solid 1px #ffffff1A;
  font-family: 'Inter', sans-serif !important;
  font-size: 19px;
  font-weight: 700;
  color: #fff;
  text-align: center;
  line-height: 0;
  width: 40px;
  height: 40px;
  min-width: 40px;
}

.first-row-panel {
  display: flex;
  width: 100%;
  justify-content: space-between;
  gap: 4px;
  overflow: visible;
}

.second-row-panel {
  display: flex;
  width: 100%;
  gap: 0.5rem;
  justify-content: center;

  .energizer {
    display: flex;
    width: 100%;
    flex-direction: column;
    padding: 0.7rem;
    cursor: pointer;
    color: #fff;
    background:
      url('@/assets/energizer_bg.svg') no-repeat right center,
      #00000040;
    background-size: contain;
    border-radius: 1rem;
    border: 1px solid #31cfff50;
    font-family: 'Inter' !important;

    .label {
      font-weight: 600;
      font-size: 13px;
      opacity: 0.5;
    }

    .points {
      font-weight: 900;
      font-size: clamp(0.3rem, 3.3vw, 0.8rem);
      text-wrap: nowrap;
    }

    &.active {
      background:
        radial-gradient(ellipse 80% 80% at top, #31cfff90, transparent 100%),
        url('@/assets/energizer_bg.svg') no-repeat right center,
        #00000040;
      background-size: contain;
      border: 1px solid #31cfff;
      filter: drop-shadow(0 6px 10px #31cfff50);
    }
  }

  .miner {
    display: flex;
    width: 100%;
    flex-direction: column;
    padding: 0.7rem;
    cursor: pointer;
    color: #fff;
    background:
      url('@/assets/miner_bg.svg') no-repeat right center,
      #00000040;
    background-size: contain;
    border-radius: 1rem;
    border: 1px solid #31ff8050;
    font-family: 'Inter' !important;

    .label {
      font-weight: 600;
      font-size: 13px;
      opacity: 0.5;
    }

    .points {
      font-weight: 900;
      font-size: clamp(0.3rem, 3.3vw, 0.8rem);
      text-wrap: nowrap;
    }

    &.active {
      background:
        radial-gradient(ellipse 80% 80% at top, #31ff8090, transparent 100%),
        url('@/assets/miner_bg.svg') no-repeat right center,
        #00000040;
      background-size: contain;
      border: 1px solid #31ff80;
      filter: drop-shadow(0 6px 10px #31ff8050);
    }
  }

  .investor {
    display: flex;
    width: 100%;
    flex-direction: column;
    padding: 0.7rem;
    cursor: pointer;
    color: #fff;
    background:
      url('@/assets/investor_bg.svg') no-repeat right center,
      #00000040;
    background-size: contain;
    border-radius: 1rem;
    border: 1px solid #8143fc50;
    font-family: 'Inter' !important;

    .label {
      font-weight: 600;
      font-size: 13px;
      opacity: 0.5;
    }

    .points {
      font-weight: 900;
      font-size: clamp(0.3rem, 3.3vw, 0.8rem);
      text-wrap: nowrap;
    }

    &.active {
      background:
        radial-gradient(ellipse 80% 80% at top, #8143fc90, transparent 100%),
        url('@/assets/investor_bg.svg') no-repeat right center,
        #00000040;
      background-size: contain;
      border: 1px solid #8143fc;
      filter: drop-shadow(0 6px 10px #8143fc50);
    }
  }
}
</style>
