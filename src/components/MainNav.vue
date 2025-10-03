<script setup>
import { defineAsyncComponent } from 'vue'
import { RouterLink } from 'vue-router'
import { useTabsStore } from '@/stores/tabs'
import { useI18n } from 'vue-i18n'
import { useTelegram } from '@/services/telegram'
const WalletIcon = defineAsyncComponent(() => import('@/assets/wallet-nav.svg'))
const BoostIcon = defineAsyncComponent(() => import('@/assets/boost-nav.svg'))
const HomeIcon = defineAsyncComponent(() => import('@/assets/home-nav.svg'))
const MarketIcon = defineAsyncComponent(() => import('@/assets/market-nav.svg'))
const FriendsIcon = defineAsyncComponent(() => import('@/assets/friends-nav.svg'))
const TasksIcon = defineAsyncComponent(() => import('@/assets/tasks-nav.svg'))

const tab = useTabsStore()
const { tg } = useTelegram()
const { t } = useI18n()

function setNav(navig) {
  if (navig !== 'boost') {
    tab.setTab(navig)
  } else {
    tab.setTab('home')
    tab.category = navig
  }
  if (navig == 'home' && tab.category === 'boost') {
    tab.category = 'energizer'
  }
  let categColor =
    tab.category == 'energizer'
      ? '#141e36'
      : tab.category == 'miner'
        ? '#0B150F'
        : tab.category == 'boost'
          ? '#0B150F'
          : '#1b1436'
  switch (navig) {
    case 'home':
      tab.setBackground(categColor)
      document.body.style.background = tab.background
      tg?.setHeaderColor(tab.background)
      break
    case 'wallet':
      tab.setBackground('#000000')
      document.body.style.background = tab.background
      tg?.setHeaderColor(tab.background)
      break
    case 'market':
      tab.setBackground('#000000')
      document.body.style.background = tab.background
      tg?.setHeaderColor(tab.background)
      break
    case 'friends':
      tab.setBackground('#141e36')
      document.body.style.background = tab.background
      tg?.setHeaderColor(tab.background)
      break
    case 'tasks':
      tab.setBackground('#000000')
      document.body.style.background = tab.background
      tg?.setHeaderColor(tab.background)
      break
    case 'boost':
      tab.setBackground('#0B150F')
      document.body.style.background = tab.background
      tg?.setHeaderColor(tab.background)
      break
  }
}

// onMounted(() => {
//   setNav('home')
// })
</script>

<template>
  <div class="menu">
    <RouterLink to="/wallet" class="button-container" :class="{ active: tab.tab === 'wallet' }"
      @click="setNav('wallet')" v-slot="{ isActive, navigate }">
      <WalletIcon :width="22" :height="22" class="menu-button" :class="{ active: isActive }" @click="navigate"
        aria-hidden="true" />
      <span class="menu-label" :class="{ active: isActive }">{{ t('general.bottom_nav.wallet') }}</span>
    </RouterLink>
    <RouterLink to="/" class="button-container" :class="{ active: tab.tab === 'home' && tab.category === 'boost' }"
      @click="setNav('boost')" v-slot="{ isActive, navigate }">
      <BoostIcon :width="22" :height="22" class="menu-button" :class="{ active: isActive && tab.category === 'boost' }"
        @click="navigate" aria-hidden="true" />
      <span class="menu-label" :class="{ active: isActive && tab.category === 'boost' }">{{
        t('general.bottom_nav.boost') }}</span>
    </RouterLink>
    <RouterLink to="/" class="button-container" :class="{ active: tab.tab === 'home' && tab.category !== 'boost' }"
      @click="setNav('home')" v-slot="{ isActive, navigate }">
      <HomeIcon :width="22" :height="22" class="menu-button" :class="{ active: isActive && tab.category !== 'boost' }"
        @click="navigate" aria-hidden="true" />
      <span class="menu-label" :class="{ active: isActive && tab.category !== 'boost' }">{{ t('general.bottom_nav.home')
        }}</span>
    </RouterLink>
    <RouterLink to="/market" class="button-container" :class="{ active: tab.tab === 'market' }"
      @click="setNav('market')" v-slot="{ isActive, navigate }">
      <MarketIcon :width="22" :height="22" class="menu-button" :class="{ active: isActive }" @click="navigate"
        aria-hidden="true" />
      <span class="menu-label" :class="{ active: isActive }">{{ t('general.bottom_nav.market') }}</span>
    </RouterLink>
    <RouterLink to="/friends" class="button-container" :class="{ active: tab.tab === 'friends' }"
      @click="setNav('friends')" v-slot="{ isActive, navigate }">
      <FriendsIcon :width="22" :height="22" class="menu-button" :class="{ active: isActive }" @click="navigate"
        aria-hidden="true" />
      <span class="menu-label" :class="{ active: isActive }">{{ t('general.bottom_nav.friends') }}</span>
    </RouterLink>
    <RouterLink to="/tasks" class="button-container" :class="{ active: tab.tab === 'tasks' }" @click="setNav('tasks')"
      v-slot="{ isActive, navigate }">
      <TasksIcon :width="22" :height="22" class="menu-button" :class="{ active: isActive }" @click="navigate"
        aria-hidden="true" />
      <span class="menu-label" :class="{ active: isActive }">{{ t('general.bottom_nav.tasks') }}</span>
    </RouterLink>
  </div>
</template>

<style lang="scss" scoped>
.menu {
  background: #10151b25;
  border-top: 1px solid #ffffff20;
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  position: absolute;
  left: 0;
  right: 0;
  justify-content: space-around;
  height: 120px;
  font-size: 1.5rem;
  z-index: 150;
}

.menu-button {
  color: #ffffff90;
  cursor: pointer;
  transition: color 0.3s;

  &:hover,
  &.active {
    color: #fff;
    cursor: pointer;
  }

  &.unactive {
    color: #ffffff25;
    cursor: default;
  }
}

.menu-label {
  color: #ffffff90;
  font-size: 0.6rem;
  cursor: pointer;

  &:hover,
  &.active {
    color: #fff;
    cursor: pointer;
  }

  &.unactive {
    color: #ffffff25;
    cursor: default;
  }
}

.button-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.7rem;
  border-radius: 1rem;

  &.active {
    padding: 1rem;
    background:
      radial-gradient(ellipse 70% 25%, #31cfff90, #31cfff50 50%, transparent 100%) padding-box,
      linear-gradient(to bottom, #31cfff, #31cfff50 50%, #31cfff05 90%, transparent 100%) padding-box,
      linear-gradient(to bottom, #ffffff, #ffffff10 60%, transparent 100%) border-box;
    border: 2px solid transparent;
  }
}
</style>
