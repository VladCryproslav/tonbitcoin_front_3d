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
// import { useSmartPolling } from './composables/useSmartPolling'
import axios from 'axios'
import { usePeriodicCheck } from './composables/usePeriodicCheck'
import { useGeneratePayload } from './composables/useGeneratePayload'
import { useI18n } from 'vue-i18n'
import InfoModal from './components/InfoModal.vue'

const isMobile = ref(true)
const isUpdateModalOpen = ref(false)
const app = useAppStore()
const { t } = useI18n()
const loading = ref(true)
const tabs = useTabsStore()
const { generatePayload } = useGeneratePayload()
const { tonConnectUI, setOptions } = useTonConnectUI()

tonConnectUI.setConnectRequestParameters({ state: 'loading' });
const tonProofPayload = generatePayload(3600)
if (!tonProofPayload) {
  tonConnectUI.setConnectRequestParameters(null)
} else {
  tonConnectUI.setConnectRequestParameters({
    state: "ready",
    value: { tonProof: tonProofPayload }
  });
}
const { tg, initUpdate, setUpdate } = useTelegram()
const connectedAddressString = useTonAddress(false)
const connectionRestored = useIsConnectionRestored()
const wallet = useTonWallet()
let controller = null

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

async function checkForUpdates() {
  try {
    const headResponse = await fetch('/updDate.json', { cache: 'no-cache', method: 'HEAD' });
    const lastModified = headResponse.headers.get('Last-Modified');

    // Перевіряємо, чи існує lastModified і чи він не співпадає зі збереженим
    if (lastModified && lastModified !== localStorage.getItem('updDate')) {
      setUpdate(lastModified); // Оновлюємо значення в localStorage через composable
      app.clearAsicsCache()
      isUpdateModalOpen.value = true
      // tonConnectUI.disconnect()
      setTimeout(() => {
        window.location.reload(); // Примусово перезавантажуємо сторінку
      }, 5000);
    }
  } catch (error) {
    console.error('Не вдалося перевірити оновлення:', error);
  }
}

async function loadInitialData() {
  if (controller) {
    controller.abort()
  }
  controller = new AbortController()
  const { signal } = controller;
  app.setLoadingProgress(0)

  try {
    await app.initUser()
    app.setLoadingProgress(10)

    if (
      connectedAddressString.value &&
      (!app.user.ton_wallet || !app.user.kw_address || !app.user.tbtc_address)
    ) {
      const kwWallet = await getJettonWalletAddress(
        'EQBhF8jWase_Cn1dNTTe_3KMWQQzDbVw_lUUkvW5k6s61ikb',
        connectedAddressString.value,
      )
      const fbtcWallet = await getJettonWalletAddress(
        'EQBOqBiArR45GUlifxdzZ40ZahdVhjtU7GjY-lVtqruHvQEc',
        connectedAddressString.value,
      )
      await host.post('add-ton-wallet/', {
        ton_wallet: connectedAddressString.value,
        kw_address: kwWallet.toString(),
        tbtc_address: fbtcWallet.toString(),
        proof: wallet.value?.connectItems?.tonProof?.proof,
        account: wallet.value?.account
      }).catch(async (e) => {
        console.error('Помилка при реєстрації гаманця, відключаємо:', e);
        await tonConnectUI.disconnect();
        throw new Error("Wallet registration failed, disconnecting.");
      });
      await app.initUser()
    }
    app.setLoadingProgress(25)

    const promises = []
    const promiseTypes = []
    // --- Запити, які не залежать від гаманця ---
    promises.push(host.get('dashboard-info/', { signal }));
    promiseTypes.push('dashboard_info')
    promises.push(host.get(`all-charts-dashboard/?filter_type=all_time`, { signal }));
    promiseTypes.push('all_charts')

    // Запит DeDust, якщо даних немає
    if (!app?.stonfi_kw) {
      promises.push(host.get('gecko/v2/networks/ton/pools/EQAHxCJBgyH8aXBizy3zLnHfZPYBQ4DAlkVXYZ3yrKNHcrX2/', { signal }));
      promiseTypes.push('stonfi_kw')
    }
    // Запит Ston.fi, якщо даних немає
    if (!app?.stonfi_fbtc) {
      promises.push(host.get('gecko/v2/networks/ton/pools/EQDRJ6wZJeaYYcR3FrqaShDgV2SyDtKBwoGI_wChiTrXL9mr/', { signal }));
      promiseTypes.push('stonfi_fbtc')
    }
    // Запит загальної кількості fBTC, якщо даних немає
    if (!app?.all_fbtc_tokens) {
      promises.push(tonapi.get('accounts/0:15e23c5949c7ecff3b8b8dec9f641e4a9dd974d75738912181103bfd0787f27a/jettons', { signal }));
      promiseTypes.push('all_fbtc')
    }

    if (connectedAddressString.value) {
      promises.push(tonapi.get(`accounts/${connectedAddressString.value}`))
      promiseTypes.push('ton_balance')

      // Завантажуємо jettons тільки якщо їх ще немає або якщо змінився адрес
      const lastJettonsAddress = localStorage.getItem('last_jettons_address')
      if (!app.jettons.length || lastJettonsAddress !== connectedAddressString.value) {
        promises.push(tonapi.get(`accounts/${connectedAddressString.value}/jettons`))
        promiseTypes.push('jettons')
        localStorage.setItem('last_jettons_address', connectedAddressString.value)
      }
      // promises.push(host.get('user-rented-nfts/'))
      // promises.push(host.get('user-lent-nfts/'))
    }

    const initialResults = await Promise.allSettled(promises)
    app.setLoadingProgress(50)

    initialResults.forEach((result, index) => {
      const type = promiseTypes[index]
      if (result.status === 'fulfilled' && result.value.status === 200) {
        switch (type) {
          case 'dashboard_info':
            app.setDashboardInfo(result.value.data)
            break
          case 'all_charts':
            app.setDashboard(result.value.data)
            break
          case 'stonfi_kw':
            app?.setStonfiKw(result.value.data?.data?.attributes?.base_token_price_usd)
            break
          case 'stonfi_fbtc':
            app.setStonfiFbtc(result.value.data?.data?.attributes?.base_token_price_usd)
            break
          case 'all_fbtc':
            app.setAllFbtcTokens((result.value.data?.balances?.find(el => el?.jetton?.symbol == 'fBTC')?.balance / (10 ** 4)).toFixed(2))
            break
          case 'ton_balance':
            app.setTonBalance(result.value.data?.balance)
            break
          case 'jettons':
            app.setJettons(result.value.data?.balances)
            break
        }
      }
    })

    // Завантажуємо ASIC'и тільки якщо їх ще немає в localStorage
    const asicsFromStorage = localStorage.getItem('all_asics')
    if (!asicsFromStorage) {
      const collection1Addr = '0:c9511472ee373f1aeb5d2dd12fc5f5cbf43d30cc1c9f0e23ad2f00346ea9e205'
      const collection2Addr = '0:3126dc7f3db3b6901eb79de8d54a308d7ded51396d04d7ebcb218c48b536b25b'

      try {
        const [col1Info, col2Info] = await Promise.all([
          tonapi.get(`nfts/collections/${collection1Addr}`),
          tonapi.get(`nfts/collections/${collection2Addr}`),
        ])
        app.setLoadingProgress(60)

        const nfts1_pages = Math.ceil(col1Info.data?.next_item_index / 1000)
        const nfts2_pages = Math.ceil(col2Info.data?.next_item_index / 1000)

        const allPagesPromises = []
        for (let i = 0; i < nfts1_pages; i++) {
          allPagesPromises.push(
            tonapi.get(`nfts/collections/${collection1Addr}/items?offset=${i * 1000}`),
          )
        }
        for (let i = 0; i < nfts2_pages; i++) {
          allPagesPromises.push(
            tonapi.get(`nfts/collections/${collection2Addr}/items?offset=${i * 1000}`),
          )
        }

        const allPagesResults = await Promise.allSettled(allPagesPromises)
        const allNfts = allPagesResults?.filter((res) => res.status === 'fulfilled' && res.value.status === 200)?.flatMap((res) => res.value.data?.nft_items)

        // Зберігаємо тільки найнеобхідніші дані для зменшення розміру
        const optimizedAsics = allNfts?.map(nft => ({
          a: nft.address, // address
          n: nft.metadata?.name, // name
          at: nft.metadata?.attributes, // attributes
        })) || []

        try {
          // Очищаємо localStorage перед збереженням
          localStorage.removeItem('all_asics')
          localStorage.setItem('all_asics', JSON.stringify(optimizedAsics))
        } catch (error) {
          console.error('Помилка збереження ASIC\'ів в localStorage:', error)
        }
      } catch (error) {
        console.error('Помилка завантаження ASIC\'ів:', error)
      }
    }
    app.setLoadingProgress(90)
  } catch (err) {
    console.error('Помилка під час початкового завантаження:', err)
  } finally {
    app.setLoadingProgress(100)
    controller = null
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

onMounted(async () => {
  const updateChecker = usePeriodicCheck(checkForUpdates, 7500);
  updateChecker.start();

  tg.setHeaderColor('#000')
  checkMobileDevice()
  if (!isMobile.value) {
    loading.value = false
    return
  }

  app.initScreen()
  app.init()
  watch(
    [connectionRestored, connectedAddressString],
    async ([isRestored, newAddress]) => {
      if (isRestored) {
        console.log("Restored:", isRestored)
        console.log("New Address:", newAddress)
        if (newAddress) {
          loadInitialData();
        } else if (!newAddress) {
          host.post('delete-ton-wallet/')
          app.clearAllCaches() // Очищаємо кеш при відключенні гаманця
          app.initUser();
          loadInitialData();
        }
      }
    },
    { immediate: true }
  )
})

onUnmounted(() => {
  if (controller) {
    controller.abort()
  }
})
</script>

<template>
  <InfoModal v-if="isUpdateModalOpen" @close="isUpdateModalOpen = false">
    <template #header>
      {{ t('modals.update.title') }}
    </template>
    <template #modal-body>
      {{ t('modals.update.body') }}
    </template>
  </InfoModal>
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
        <img src="@/assets/fBTC.webp" class="w-[100px]">
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
