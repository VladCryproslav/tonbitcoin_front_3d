<script setup>
import { useAppStore } from '@/stores/app'
import { TonConnectButton, useTonAddress, useTonConnectUI } from '@townsquarelabs/ui-vue'
import { onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import { host, tonapi } from '../../axios.config'
import { Address, beginCell, toNano } from '@ton/core'
import { useTelegram } from '@/services/telegram'
import { JettonMaster, TonClient } from '@ton/ton'
import ModalNew from '@/components/ModalNew.vue'
import WithdrawModal from '@/components/WithdrawModal.vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const app = useAppStore()
const connectedAddressString = useTonAddress(false)
const ton_address = useTonAddress()
const { t } = useI18n()
const { networkFee, userAddress } = useTelegram()
const { tonConnectUI, setOptions } = useTonConnectUI()

const router = useRouter()
let controller = null

const isChecked = ref('kw')
const topUpAmount = ref(null)

const modalStatus = ref('')
const modalTitle = ref('')
const modalBody = ref('')
const openModal = ref(false)

const showModal = (status, title, body) => {
  modalStatus.value = status
  modalTitle.value = title
  modalBody.value = body
  openModal.value = true
}

const openWithdraw = ref(false)

async function getJettonWalletAddress(contract) {
  const client = new TonClient({
    apiKey: '90ff1e63f54f82220c606905fd294f2c0253abf4a16d7bfa159c1c0c48252167',
    endpoint: 'https://toncenter.com/api/v2/jsonRPC',
  })
  const jettonMaster = client.open(JettonMaster.create(Address.parse(contract)))
  const userJettonWalletAddress = await jettonMaster.getWalletAddress(
    Address.parse(ton_address.value),
  )
  return userJettonWalletAddress
}

async function topup(currency) {
  if (!ton_address.value) {
    showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }
  if (isProcessing.value) return
  isProcessing.value = true
  isPaused.value = true

  // Скидаємо стан модального вікна перед новою транзакцією
  try {
    await tonConnectUI.closeModal()
  } catch {
    // Ігноруємо помилки закриття модального вікна
  }

  if (currency == 'kw') {
    try {
      const jettonWalletContract = 'EQBhF8jWase_Cn1dNTTe_3KMWQQzDbVw_lUUkvW5k6s61ikb'
      const receiveWallet = 'UQA1yfxD2yVTu_1QMycifyLMOhJoY_BiJBktI_dAeFjYHLid'
      const address = await getJettonWalletAddress(jettonWalletContract)

      const transfer_cell = beginCell()
        .storeUint(0xf8a7ea5, 32) // jetton transfer operation
        .storeUint(0, 64) // query ID
        .storeCoins(toNano(topUpAmount.value)) // jetton amount
        .storeAddress(Address.parse(receiveWallet))
        .storeAddress(Address.parse(userAddress))
        .storeUint(0, 1)
        .storeCoins(1)
        .storeUint(0, 1)
        .endCell()

      const transData = {
        validUntil: Date.now() + 1000 * 60 * 5,
        messages: [
          {
            address: address.toString(),
            amount: toNano(networkFee).toString(),
            payload: transfer_cell.toBoc().toString('base64'),
          },
        ],
      }

      const transferTonKw = await tonConnectUI.sendTransaction(transData, {
        modals: ['before', 'success'],
        notifications: [],
      })

      if (transferTonKw && transferTonKw?.boc) {
        await host.post('add-kw-to-wallet/', { kw_amount: topUpAmount.value })
        await app.initUser()
        showModal('success', t('notification.st_success'), t('notification.success_dep', { value: topUpAmount.value, currency: 'kW' }))
        topUpAmount.value = null
      }
    } catch (err) {
      console.log(err)
      // showModal('error', t('notification.st_error'), t('notification.failed_transaction'))
    } finally {
      isProcessing.value = false
      setTimeout(() => {
        isPaused.value = false
      }, 1500)
    }
  }

  if (currency == 'tbtc') {
    try {
      const jettonWalletContract = 'EQBOqBiArR45GUlifxdzZ40ZahdVhjtU7GjY-lVtqruHvQEc'
      const receiveWallet = 'UQB0ukWTZXHQhlhztL91277hD8xbFFKXiHVvSBNw-gcBKHfO'
      const address = await getJettonWalletAddress(jettonWalletContract)

      const transfer_cell = beginCell()
        .storeUint(0xf8a7ea5, 32) // jetton transfer operation
        .storeUint(Date.now(), 64) // query ID
        .storeCoins(toNano(topUpAmount.value / 10 ** 5)) // jetton amount (decimal: 4 | 9-5)
        .storeAddress(Address.parse(receiveWallet))
        .storeAddress(Address.parse(userAddress))
        .storeUint(0, 1)
        .storeCoins(1)
        .storeUint(0, 1)
        .endCell()

      const transData = {
        validUntil: Date.now() + 1000 * 60 * 5,
        messages: [
          {
            address: address.toString(),
            amount: toNano(networkFee).toString(),
            payload: transfer_cell.toBoc().toString('base64'),
          },
        ],
      }

      const transferTonTBTC = await tonConnectUI.sendTransaction(transData, {
        modals: ['before', 'success'],
        notifications: [],
      })

      if (transferTonTBTC && transferTonTBTC.boc) {
        await host.post('add-tbtc-to-wallet/', { tbtc_amount: topUpAmount.value })
        await app.initUser()
        showModal('success', t('notification.st_success'), t('notification.success_dep', { value: topUpAmount.value, currency: 'fBTC' }))
        topUpAmount.value = null
      }
    } catch (err) {
      console.log(err)
      // showModal('error', t('notification.st_error'), t('notification.failed_transaction'))
    } finally {
      isProcessing.value = false
      setTimeout(() => {
        isPaused.value = false
      }, 1500)
    }
  }
}

async function withdrawTBTC() {
  await app.initUser()
  if (!ton_address.value) {
    showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }
  if (app.user.tbtc_wallet < app.withdraw_config?.min_tbtc) {
    showModal(
      'error',
      t('notification.st_error'),
      t('notification.min_withdraw_err', { value: app.withdraw_config?.min_tbtc }),
    )
    return
  }

  openWithdraw.value = true
}

const getWithdrawResponse = (val) => {
  openWithdraw.value = false
  modalStatus.value = val.status
  modalTitle.value = val.title
  modalBody.value = val.body
  openModal.value = true
}

const isPaused = ref(false)
const isProcessing = ref(false)
const wasStopped = ref(false)

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

let timeoutId = null
async function startInfoUpdate() {
  if (isPaused.value) {
    wasStopped.value = true
    return
  }
  app.setPauseUpdate(true)
  try {
    await app.initUser()
    controller = new AbortController()
    await tonapi.get(`accounts/${connectedAddressString.value}`, { signal: controller.signal }).then((res) => {
      if (res.status == 200) {
        app.setTonBalance(res?.data?.balance)
      }
    }).finally(() => {
      controller = null
    })
    await delay(2000) // Затримка між запитами
    await tonapi.get(`accounts/${connectedAddressString.value}/jettons`).then((res) => {
      if (res.status == 200) {
        app.setJettons(res?.data?.balances)
      }
    })
  } catch (err) {
    console.log(err)
  } finally {
    controller = null
    timeoutId = setTimeout(() => startInfoUpdate(), 5000)
  }
}

function stopInfoUpdate() {
  app.setPauseUpdate(false)
}

watch(
  isPaused,
  () => {
    if (isPaused.value == false && wasStopped.value == true) {
      wasStopped.value = false
      startInfoUpdate()
    }
  },
  { immediate: true },
)

const screenBoxRef = ref()
const handleTopUpFocus = async () => {
  const el = screenBoxRef.value
  el.scrollTo({
    top: 550,
    behavior: 'smooth',
  })
}

onMounted(() => {
  startInfoUpdate()
})

onUnmounted(() => {
  if (controller) {
    controller.abort()
  }
  stopInfoUpdate()
  if (timeoutId) {
    clearTimeout(timeoutId)
    timeoutId = null
  }
})
</script>

<template>
  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
  <WithdrawModal v-if="openWithdraw" @close="getWithdrawResponse" />
  <TonConnectButton />
  <div class="screen-box" ref="screenBoxRef">
    <h1 class="title">{{ t('wallet.title') }}</h1>
    <div class="balance">
      <div class="ton">
        <div class="left-side">
          <img src="@/assets/TON.png" width="35px" height="35px" />
          <div class="grouping">
            <h2 class="label">Toncoin</h2>
            <span class="price">{{ app?.tonBalance / 10 ** 9 }} TON</span>
          </div>
        </div>
        <span class="current-val">{{ +(+(app?.tonBalance / 10 ** 9) * +(app.prices?.['TON'] || 0)).toFixed(2) }}
          $</span>
      </div>
      <div class="tbit">
        <div class="left-side">
          <img src="@/assets/fBTC.webp" width="35px" height="35px" />
          <div class="grouping">
            <h2 class="label">TonBitcoin (Fork)</h2>
            <span class="price">{{
              app.jettons?.find((el) => el?.jetton?.symbol == 'fBTC')
                ? app.jettons.find((el) => el.jetton.symbol == 'fBTC')?.balance /
                10 ** app.jettons.find((el) => el.jetton.symbol == 'fBTC')?.jetton.decimals
                : '0'
            }}
              fBTC</span>
          </div>
        </div>
        <span class="current-val">{{
          +(
            +(app.jettons?.find((el) => el?.jetton?.symbol == 'fBTC')
              ? app.jettons.find((el) => el.jetton.symbol == 'fBTC')?.balance /
              10 ** app.jettons.find((el) => el.jetton.symbol == 'fBTC')?.jetton.decimals
              : '0') * (app.prices?.['FBTC'] || +app.stonfi_fbtc || 0)
          ).toFixed(2)
        }}
          $</span>
      </div>
      <div class="energy">
        <div class="left-side">
          <img src="@/assets/kW_token.png" width="35px" height="35px" />
          <div class="grouping">
            <h2 class="label">{{ t('wallet.energy') }}</h2>
            <span class="price">{{
              app.jettons?.find((el) => el?.jetton?.symbol == 'kW')
                ? +(
                  +app.jettons?.find((el) => el?.jetton?.symbol == 'kW')?.balance /
                  10 ** app?.jettons?.find((el) => el?.jetton?.symbol == 'kW')?.jetton?.decimals
                ).toFixed(4)
                : '0'
            }}
              kW</span>
          </div>
        </div>
        <span class="current-val">{{
          +(
            +(app.jettons?.find((el) => el?.jetton?.symbol == 'kW')
              ? app.jettons?.find((el) => el?.jetton?.symbol == 'kW')?.balance /
              10 ** app.jettons?.find((el) => el?.jetton?.symbol == 'kW')?.jetton?.decimals
              : '0') * (app.prices?.['KW'] || +app.stonfi_kw || 0)
          ).toFixed(2)
        }}
          $</span>
      </div>
    </div>
    <div class="top-up">
      <h3>{{ t('wallet.topup_title') }}</h3>
      <div class="switch">
        <input v-model="isChecked" label="kW" type="radio" id="kw" name="currency" value="kw" checked />
        <input v-model="isChecked" label="fBTC" type="radio" id="tbtc" name="currency" value="tbtc" />
      </div>
      <div class="topup-form">
        <input v-model="topUpAmount" type="text" inputmode="decimal" :placeholder="t('wallet.topup_placeholder')"
          id="topup-amount" @focus="handleTopUpFocus" />
        <button class="topup-btn" @click="topup(isChecked)">{{ t('wallet.topup_btn') }}</button>
      </div>
    </div>
    <div class="user-wallet">
      <h3>{{ t('wallet.user_title') }}</h3>
      <div class="grouping">
        <div class="tbit">
          <div class="left-side">
            <img src="@/assets/fBTC.webp" width="40px" height="40px" />
            <h2 class="amount">{{ +(+app.user.tbtc_wallet).toFixed(2) || 0 }} fBTC</h2>
          </div>
          <button @click="() => {
            // modalStatus = 'warning'
            // modalTitle = t('notification.st_attention')
            // modalBody = t('notification.spend_fbtc_discl')
            // openModal = true
            router.push('/wheel')
          }
          ">{{ t('wallet.spend_btn') }}</button>
          <!-- @click="withdrawTBTC" -->
          <!-- router.push('/wheel')-->
        </div>
        <div class="energy">
          <div class="left-side">
            <img src="@/assets/kW_token.png" width="40px" height="40px" />
            <h2 class="amount">{{ +(+app.user.kw_wallet).toFixed(2) || 0 }} kW</h2>
          </div>
          <button @click="() => {
            // modalStatus = 'warning'
            // modalTitle = t('notification.st_attention')
            // modalBody = t('notification.spend_kw_discl')
            // openModal = true
            router.push('/wheel')
          }
          ">{{ t('wallet.spend_btn') }}</button>
          <!--  router.push('/wheel') -->
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.screen-box {
  position: absolute;
  top: 0;
  width: 100%;
  height: 100vh;
  background: radial-gradient(ellipse 80% 40% at top right, #31ff8050, transparent) #000;
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

.balance {
  width: 90%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: #15140850;
  border: 1px solid #ffffff25;
  border-radius: 1rem;
  padding: 0.5rem 1rem;
  margin-bottom: 0.5rem;
  gap: 0.2rem;

  .ton,
  .tbit,
  .energy {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .left-side {
    display: flex;
    align-items: center;
    gap: 1rem;

    .grouping {
      display: flex;
      flex-direction: column;
      font-family: 'Inter' !important;

      .label {
        color: #fff;
        font-size: 5vw;
        font-weight: 600;
      }

      .price {
        color: #ffffff60;
        font-size: 3.5vw;
        font-weight: 400;
      }
    }
  }

  .current-val {
    color: #fff;
    font-family: 'Inter' !important;
    font-size: 6vw;
    font-weight: 700;
  }
}

.top-up {
  width: 90%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  background: #15140850;
  border: 1px solid #ffffff25;
  border-radius: 1rem;
  padding: 1rem;
  margin-bottom: 0.5rem;
  gap: 1rem;
  font-family: 'Inter' !important;

  h3 {
    color: #fff;
    font-weight: 600;
    font-size: 18px;
  }

  .switch {
    position: relative;
    background: transparent;
    border-radius: 0.7rem;
    -webkit-box-shadow: inset 0px 0px 0px 1px #ffffff50;
    -moz-box-shadow: inset 0px 0px 0px 1px #ffffff50;
    box-shadow: inset 0px 0px 0px 1px #ffffff50;

    input {
      width: auto;
      height: 100%;
      -webkit-appearance: none;
      -moz-appearance: none;
      appearance: none;
      outline: none;
      cursor: pointer;
      border-radius: 0.7rem;
      padding: 0.5rem 0.8rem;
      color: #fff;
      font-family: 'Inter' !important;
      font-size: 18px;
      font-weight: 600;
      transition: all 100ms linear;

      &:checked {
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);
        color: #000;
      }

      &:before {
        content: attr(label);
        display: inline-block;
        text-align: center;
        width: 100%;
      }
    }
  }

  .topup-form {
    display: flex;
    width: 100%;
    justify-content: center;
    gap: 0.5rem;
    font-family: 'Inter' !important;

    input {
      width: 95%;
      background: #15140850;
      color: #fff;
      border-radius: 5px;
      -webkit-box-shadow: inset 0px 0px 0px 1px #ffffff25;
      -moz-box-shadow: inset 0px 0px 0px 1px #ffffff25;
      box-shadow: inset 0px 0px 0px 1px #ffffff25;
      padding: 0.5rem 0;
      text-align: center;
      font-family: 'Inter' !important;
      font-size: 16px;
      font-weight: 600;
      outline: none !important;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;

      &::placeholder {
        padding: 10px;
        font-size: 14px;
        font-weight: 400;
      }
    }

    button {
      font-size: 16px;
      font-weight: 600;
      height: 40px;
      padding: 0 15px;
      border-radius: 5px;
      text-wrap: nowrap;
      background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
        linear-gradient(to bottom, #fcd909, #fea400);

      &:active {
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd90990, #fea40090);
      }
    }
  }
}

.user-wallet {
  width: 90%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: #15140850;
  border: 1px solid #ffffff25;
  border-radius: 1rem;
  padding: 1rem;
  gap: 1rem;
  font-family: 'Inter' !important;

  h3 {
    color: #fff;
    font-weight: 600;
    font-size: 18px;
  }

  .grouping {
    width: 100%;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 1rem;

    .tbit,
    .energy {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .left-side {
      display: flex;
      align-items: center;
      gap: 1rem;

      .amount {
        color: #fff;
        font-size: clamp(11px, 4.5vw, 18px);
        font-weight: 600;
      }
    }

    button {
      text-align: center;
      font-size: 16px;
      font-weight: 600;
      height: 40px;
      min-width: 105px;
      width: max-content;
      border-radius: 5px;
      background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
        linear-gradient(to bottom, #fcd909, #fea400);

      &:active {
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd90990, #fea40090);
      }

      &.disabled {
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd90990, #fea40090);
      }
    }
  }
}
</style>
