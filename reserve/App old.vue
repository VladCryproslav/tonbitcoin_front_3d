<script setup>
import { ref, onMounted, watch, onUnmounted, onBeforeMount } from 'vue'
import { RouterView } from 'vue-router'
import MainNav from '@/components/MainNav.vue'
import PreLoader from '@/views/PreLoader.vue'
import { useAppStore } from './stores/app'
import { host, tonapi } from '../axios.config'
import {
  useIsConnectionRestored,
  useTonAddress,
  useTonConnectUI,
  useTonWallet,
} from '@townsquarelabs/ui-vue'
import { Address, JettonMaster, TonClient } from '@ton/ton'
import { useTabsStore } from './stores/tabs'
import { useTelegram } from './services/telegram'
import { useSmartPolling } from './composables/useSmartPolling'

const isMobile = ref(true)
const app = useAppStore()
const loading = ref(true)
const tabs = useTabsStore()

let intervalId = null

const { tonConnectUI, setOptions } = useTonConnectUI()
const { tg, initUpdate, setUpdate } = useTelegram()
const connectedAddressString = useTonAddress(false)
const connectionRestored = useIsConnectionRestored()
const connectedAddress = useTonAddress()
const wallet = useTonWallet()

async function getJettonWalletAddress(contract, wallet) {
  const client = new TonClient({
    apiKey: '90ff1e63f54f82220c606905fd294f2c0253abf4a16d7bfa159c1c0c48252167',
    endpoint: 'https://toncenter.com/api/v2/jsonRPC',
  })
  const jettonMaster = client.open(JettonMaster.create(Address.parse(contract)))
  const userJettonWalletAddress = await jettonMaster.getWalletAddress(Address.parse(wallet))
  return userJettonWalletAddress
}

const handleProgressComplete = () => {
  if (!app?.user?.blocked) {
    loading.value = false
  }
}

const checkMobileDevice = () => {
  if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
    isMobile.value = true
  } else {
    isMobile.value = false
  }
}
// const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function updateData() {
  if (connectedAddressString.value && !app.pauseUpdate) {
    try {
      if (!app.user.ton_wallet || !app.user.kw_address || !app.user.tbtc_address) {
        const kwWallet = await getJettonWalletAddress(
          'EQBhF8jWase_Cn1dNTTe_3KMWQQzDbVw_lUUkvW5k6s61ikb',
          connectedAddressString.value,
        )
        const fbtcWallet = await getJettonWalletAddress(
          'EQBOqBiArR45GUlifxdzZ40ZahdVhjtU7GjY-lVtqruHvQEc',
          connectedAddressString.value,
        )
        await host
          .post('add-ton-wallet/', {
            ton_wallet: connectedAddressString.value,
            kw_address: kwWallet.toString(),
            tbtc_address: fbtcWallet.toString(),
            proof: wallet?.connectItems?.tonProof?.proof,
            account: wallet?.account,
          })
          .catch(async (e) => {
            console.log(e)
            await tonConnectUI.disconnect()
          })
      }
      await app.initUser()
    } catch (err) {
      console.error('Error fetching account jettons balances:', err)
    }
  }
}

let isUpdating = false

async function startDataUpdate() {
  if (isUpdating) return // Запобігає одночасним запускам
  isUpdating = true
  try {
        const headResponse = await fetch('/updDate.json', { cache: 'no-cache', method: 'HEAD' });
        const lastModified = headResponse.headers.get('Last-Modified');
        if (lastModified !== localStorage.getItem('updDate')) {
          setUpdate(lastModified)
          window.location.reload()
        }
    await updateData()
  } catch (err) {
    console.error('Error during data update:', err)
  } finally {
    isUpdating = false
    if (intervalId !== null) {
      setTimeout(startDataUpdate, 3000)
    }
  }
}

// const {
//   data: upd_data,
// } = useSmartPolling('/updDate.json', {
//   initialInterval: 5000,     // Початкові n секунди
//   maxInterval: 10000,        // Максимум 30 секунд
//   backoffMultiplier: 2,    // Множник збільшення
//   unchangedThreshold: 1,      // Після 3 незмін збільшуємо інтервал
//   checkLastModified: true
// })

onBeforeMount(() => {
  initUpdate()
})

onMounted(() => {
  app.preload()
  tg.setHeaderColor('#000')
  checkMobileDevice()
  if (isMobile.value == false) {
    loading.value = false
    return
  }
  tabs.setTab('home')
  app.initScreen()
  app.setPauseUpdate(false)
  app.init()

  watch(
    loading,
    (newLoading) => {
      if (newLoading == false) {
        watch(
          [connectionRestored, connectedAddressString],
          async ([isRestored, newAddress]) => {
            if (isRestored && newAddress) {
              if (intervalId === null) {
                intervalId = true // Активуємо оновлення
                try {
                  await tonConnectUI.setConnectRequestParameters({
                    state: 'ready',
                    value: { tonProof: 'CL8FjGpvbL' },
                  })
                } catch (err) {
                  console.error('Error in setConnectRequestParameters:', err);
                }
                startDataUpdate()
              }
            } else {
              if (intervalId) {
                intervalId = null
              }

              if (!newAddress) {
                await host.post('delete-ton-wallet/')
                await app.initUser()
              }
            }
          },
          { immediate: true },
        )
      }
    },
    { immediate: true },
  )
})

onUnmounted(() => {
  intervalId = null
})
</script>

<template>
  <PreLoader v-if="loading" @progress-complete="handleProgressComplete" />
  <main v-if="isMobile & !loading" class="game">
    <!-- <main v-if="!loading" class="game"> -->
    <!-- <main class="game"> -->
    <div class="page">
      <RouterView />
    </div>
    <MainNav />
  </main>
  <main v-if="!isMobile">
    <div class="error-notice">
      <span v-show="!isMobile"
        class="text-white text-[2rem] text-center flex flex-col items-center gap-5 font-bold px-10 z-50">
        <img src="@/assets/fBTC.png" class="w-[100px]">
        You must use a mobile device to log in.
      </span>

      <a href="https://t.me/tBTCminer_bot?start"
        class="bg-blue-500 text-white rounded-full py-4 px-10 mt-10 uppercase font-semibold animate-bounce">View in
        Telegram</a>
    </div>
  </main>
</template>

<style lang="scss" scoped>
.error-notice {
  position: relative;
  height: 100vh;
  width: 100vw;
  background:
    url('@/assets/energizer_bg.svg') no-repeat bottom right,
    linear-gradient(45deg, #000, #161616);
  background-size: contain;
  display: flex;
  flex-direction: column;
  font-family: 'Inter' !important;
  justify-content: center;
  align-items: center;

  &:before,
  & :after {
    content: '';
    display: block;
    position: absolute;
    width: 1px;
    height: 1px;
    border-radius: 100%;
    opacity: 0.6;
  }

  &:before {
    box-shadow: 0 0 30vmax 30vmax #f00;
    animation:
      hue 5s 0s linear infinite,
      move1 10s 0s linear infinite;
  }

  &:after {
    box-shadow: 0 0 30vmax 30vmax #0ff;
    animation:
      hue 5s 0s linear infinite,
      move2 20s 0s linear infinite;
  }

  @keyframes hue {
    0% {
      filter: hue-rotate(0deg);
    }

    100% {
      filter: hue-rotate(360deg);
    }
  }

  @keyframes move1 {
    0% {
      top: 0vh;
      left: 50vw;
    }

    25% {
      left: 0vw;
    }

    50% {
      top: 100vh;
    }

    75% {
      left: 100vw;
    }

    100% {
      top: 0vh;
      left: 50vw;
    }
  }

  @keyframes move2 {
    0% {
      top: 50vh;
      left: 100vw;
    }

    25% {
      top: 100vh;
    }

    50% {
      left: 0vw;
    }

    75% {
      top: 0vh;
    }

    100% {
      top: 50vh;
      left: 100vw;
    }
  }
}
</style>
