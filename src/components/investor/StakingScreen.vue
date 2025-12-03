<script setup>
import { useTelegram } from '@/services/telegram';
import { useAppStore } from '@/stores/app';
import { useTonAddress, useTonConnectUI } from '@townsquarelabs/ui-vue';
import { Address, beginCell, toNano } from '@ton/core'
import { JettonMaster, TonClient } from '@ton/ton'
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import ModalNew from '../ModalNew.vue';
import StakingPercentModal from '../StakingPercentModal.vue';
import StakingHistoryModal from '../StakingHistoryModal.vue';
import { host, tonapi } from '../../../axios.config';


let controller = null
const app = useAppStore()
const emit = defineEmits(['back'])
const { t } = useI18n()
const { tonConnectUI, setOptions } = useTonConnectUI()
const { networkFee, userAddress } = useTelegram()
const connectedAddressString = useTonAddress(false)
const ton_address = useTonAddress()

const premiumActive = computed(() => new Date(app.user?.premium_sub_expires) >= new Date())
const stakingDays = ref(app?.staking_config?.[0]?.days || 30)
const stakingTBTC = ref(null)

const myTBTC = computed(() => {
  return app.jettons?.find((el) => el?.jetton?.symbol == 'fBTC')
    ? app.jettons?.find((el) => el?.jetton?.symbol == 'fBTC')?.balance /
    10 ** app.jettons?.find((el) => el?.jetton?.symbol == 'fBTC')?.jetton?.decimals
    : 0
})

const stakingConfig = computed(() => {
  return app?.staking_config || [
    { days: 30, apr: 5 },
    { days: 60, apr: 7 },
    { days: 90, apr: 10 }
  ];
});

const openPercentModal = ref(false)
const openHistoryModal = ref(false)

const openModal = ref(false)
const modalBody = ref('')
const modalTitle = ref('')
const modalStatus = ref('')

const showModal = (status, title, body) => {
  modalStatus.value = status
  modalTitle.value = title
  modalBody.value = body
  openModal.value = true
}

const getFutureDate = (days) => {
  const now = new Date()
  now.setDate(now.getDate() + days)

  const day = String(now.getDate()).padStart(2, '0')
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const year = now.getFullYear()
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  const seconds = String(now.getSeconds()).padStart(2, '0')

  return `${day}.${month}.${year} ${hours}:${minutes}:${seconds}`
}

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

const isProcessing = ref(false)

const createStaking = async () => {
  if (!stakingDays.value || !stakingTBTC.value) return

  if (!ton_address.value) {
    showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }

  if (stakingTBTC.value < app?.withdraw_config?.min_staking) {
    stakingTBTC.value = app?.withdraw_config?.min_staking
  }

  if (myTBTC.value < stakingTBTC.value) {
    showModal(
      'error',
      t('notification.st_error'),
      t('notification.no_money_to_stake', { value: stakingTBTC.value }),
    )
    return
  }

  if (isProcessing.value) return
  isProcessing.value = true

  // Скидаємо стан модального вікна перед новою транзакцією
  try {
    await tonConnectUI.closeModal()
  } catch {
    // Ігноруємо помилки закриття модального вікна
  }

  try {
    const jettonWalletContract = 'EQBOqBiArR45GUlifxdzZ40ZahdVhjtU7GjY-lVtqruHvQEc'
    const receiveWallet = 'UQBeklJltNcujGHOMI_yJsAQKJLxR4QfzAqp9Wu1Rp1Y9TAj'
    const address = await getJettonWalletAddress(jettonWalletContract)

    if (!address) throw new Error('Не удалось получить адрес кошелька')

    const transfer_cell = beginCell()
      .storeUint(0xf8a7ea5, 32) // jetton transfer operation
      .storeUint(Date.now(), 64) // query ID
      .storeCoins(toNano(stakingTBTC.value / 10 ** 5)) // jetton amount (decimal: 4 | 9-5)
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

    try {
      await tonConnectUI.sendTransaction(transData)
    } catch (err) {
      console.log(err)
      showModal('error', t('notification.st_error'), t('notification.failed_transaction'))
    }

    const staking_data = {
      token_amount: stakingTBTC.value,
      staking_period_days: stakingDays.value,
    }

    controller = new AbortController()
    const res = await host.post('create-user-staking/', staking_data, { signal: controller.signal })
    if (res.status === 200) {
      showModal(
        'success',
        t('notification.st_success'),
        t('notification.success_stake', { value: stakingTBTC.value }),
      )
    }
  } catch (err) {
    console.error(err)
    const errorMsg =
      err.response?.data?.error || err.message || t('notification.was_error')
    showModal('error', t('notification.st_error'), errorMsg)
  } finally {
    controller = null
    isProcessing.value = false
  }
}

let timeoutId = null
async function updateStaking() {
  try {
    await app.initStaking()
    controller = new AbortController()
    await tonapi.get(`accounts/${connectedAddressString.value}/jettons`, { signal: controller.signal }).then((res) => {
      if (res.status == 200) {
        app.setJettons(res?.data?.balances)
      }
    }).finally(() => {
      controller = null
    })
  } catch (err) {
    console.log(err)
  } finally {
    controller = null
    timeoutId = setTimeout(() => updateStaking(), 3000)
  }
}

onMounted(() => {
  updateStaking()
})

onUnmounted(() => {
  if (controller) {
    controller.abort()
  }
  if (timeoutId) {
    clearTimeout(timeoutId)
    timeoutId = null
  }
})
</script>

<template>
  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
  <StakingPercentModal v-if="openPercentModal" @close="openPercentModal = false" />
  <StakingHistoryModal v-if="openHistoryModal" @close="openHistoryModal = false" />
  <div class="staking">
    <div class="staking-radio-perc">
      <label class="radio" v-for="(day_item, index) in stakingConfig" :key="index">
        <input type="radio" v-model="stakingDays" :value="day_item?.days" />
        <span class="name">{{ t('common.days', { n: day_item?.days }) }}</span>
        <span class="apr">APR {{ day_item?.apr }}%</span>
      </label>
    </div>
    <div class="staking-pannel">
      <div class="staking-pannel-input-labels">
        <label>{{ t('investor.stake_inp_title') }}</label>
        <label>{{ t('investor.stake_inp_avlb') }} <span>{{ myTBTC?.toFixed(2) }} fBTC</span></label>
      </div>
      <div class="input-wrapper">
        <img class="icon" src="@/assets/fBTC.webp" width="24px" />
        <input type="number" inputmode="numeric" :min="app?.withdraw_config?.min_staking" name="text"
          v-model="stakingTBTC" pattern="/d+" autocomplete="off" aria-controls="none" class="input"
          :placeholder="t('common.min') + ' ' + app?.withdraw_config?.min_staking" />
        <button class="max-btn" @click="stakingTBTC = myTBTC?.toFixed(2)">{{ t('common.max') }}</button>
      </div>
      <div class="staking-pannel-input-labels">
        <label>APR:</label>
        <label><span :class="{
          '!text-[#FCD909]': ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ||
            (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive) &&
            app?.staking?.filter((item) => item?.status === 'active')?.reduce((sum, item) => sum + item?.token_amount, 0) + stakingTBTC <= 100000
        }">
            {{app?.staking_config?.find((el) => el?.days == stakingDays)?.apr + ((app?.user?.has_silver_sbt &&
              app?.user?.has_silver_sbt_nft ? 2 :
              ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive) ? 5 : 0))}}%
            {{(app?.staking?.filter(item =>
              item?.status === "active")?.reduce((sum, item) => sum + item?.token_amount, 0) + stakingTBTC <= 100000) ?
              (app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? '(+2% SBT)' : ((app?.user?.has_gold_sbt &&
                app?.user?.has_gold_sbt_nft) || premiumActive) ? `(+5% ${premiumActive ? t('boost.king') : 'SBT'})` : ''
              : ''}}</span></label>
      </div>
      <div class="staking-pannel-input-labels">
        <label>{{ t('investor.stake_inp_unlock') }}</label>
        <label><span>{{ getFutureDate(stakingDays) }}</span></label>
      </div>
      <div class="staking-pannel-input-labels">
        <label>{{ t('investor.stake_inp_perc') }}</label>
        <label><span>{{
          (
            ((stakingTBTC *
              ((app?.staking_config?.find((el) => el?.days == stakingDays)?.apr + (app?.user?.has_silver_sbt &&
                app?.user?.has_silver_sbt_nft && (app?.staking?.filter(item => item?.status === "active")?.reduce((sum,
                  item) => sum + item?.token_amount, 0) + stakingTBTC <= 100000) ? 2 : ((app?.user?.has_gold_sbt &&
                    app?.user?.has_gold_sbt_nft) || premiumActive) && (app?.staking?.filter(item => item?.status ===
                      "active")?.reduce((sum,
                        item) => sum + item?.token_amount, 0) + stakingTBTC <= 100000) ? 5 : 0)) / 100)) / 12) * (stakingDays /
                          30)).toFixed(2) || 0}} fBTC</span></label>
      </div>
      <button class="staking-pannel-btn" :class="{ disabled: stakingTBTC < app?.withdraw_config?.min_staking }"
        @click="createStaking" :disabled="stakingTBTC < app?.withdraw_config?.min_staking">
        {{ t('investor.stake_btn') }}
      </button>
      <div class="staking-pannel-btn-group">
        <button @click="openPercentModal = true">
          {{ t('investor.perc_tab') }} <img src="@/assets/percent.png" width="22px" />
        </button>
        <button @click="openHistoryModal = true">
          {{ t('investor.history_tab') }} <img src="@/assets/history.png" width="22px" />
        </button>
      </div>
      <button class="back-btn" @click="emit('back')">
        {{ t('investor.back') }}
      </button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.staking {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;

  &-radio-perc {
    position: relative;
    display: flex;
    flex-wrap: wrap;
    border-radius: 1rem;
    box-sizing: border-box;
    background: #00000050;
    margin-bottom: 1rem;
    box-shadow: 0 0 0px 1px rgba(0, 0, 0, 0.06);
    width: 100%;
    font-family: 'Inter';
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0px;

    .radio {
      position: relative;
      flex: 1 1 auto;
      text-align: center;

      input {
        display: none;

        &:checked+.name {
          background-color: #8143fc;
          font-weight: 600;
        }
      }

      .name {
        display: flex;
        cursor: pointer;
        align-items: center;
        justify-content: center;
        border-radius: 1rem;
        border: none;
        padding: 0.7rem 0;
        color: #fff;
        transition: all 0.15s ease-in-out;
      }

      .apr {
        position: absolute;
        top: 130%;
        color: #8143fc;
        font-family: 'Inter';
        font-weight: 600;
        font-size: 13px;
        letter-spacing: 0px;
        left: 50%;
        right: 50%;
        width: max-content;
        transform: translate(-50%, -50%);
      }
    }
  }

  &-pannel {
    width: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 0.2em;

    &-input-labels {
      display: flex;
      justify-content: space-between;
      color: #ffffff50;
      font-family: 'Inter';
      font-size: 14px;
      font-weight: 600;

      label {
        span {
          color: #fff;
        }
      }
    }

    &-btn {
      background: #8143fc;
      color: #fff;
      font-family: 'Inter';
      font-weight: 600;
      font-size: 20px;
      letter-spacing: 0px;
      padding: 1rem 0;
      border-radius: 10px;
      margin: 10px 0;
      transition: all 0.3s ease;

      &:active {
        opacity: 0.5;
        scale: 0.95;
      }

      &.disabled {
        opacity: 0.5;
      }
    }

    &-btn-group {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 10px;

      button {
        flex-grow: 1;
        width: 100%;
        height: 48px;
        padding: 10px 0;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 8px;
        border: 1px solid #8143fc;
        border-radius: 10px;
        color: #fff;
        font-family: 'Inter';
        font-weight: 600;
        font-size: clamp(14px, 4dvw, 18px);
        letter-spacing: 0px;
        transition: all 100ms ease;

        &:active {
          opacity: 0.5;
          scale: 0.95;
        }
      }
    }

    .back-btn {
      margin-top: 8px;
      width: 100%;
      height: 48px;
      padding: 10px 0;
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 8px;
      border: 1px solid #8143fc;
      border-radius: 10px;
      color: #fff;
      font-family: 'Inter';
      font-weight: 600;
      font-size: clamp(14px, 4dvw, 18px);
      letter-spacing: 0px;
      transition: all 100ms ease;

      &:active {
        opacity: 0.5;
        scale: 0.95;
      }
    }

    .input-wrapper {
      height: 45px;
      border-radius: 20px;
      border: 1px solid #fff;
      padding: 5px;
      box-sizing: content-box;
      display: flex;
      align-items: center;
      gap: 3px;
      margin: 5px 0;
    }

    .icon {
      width: 30px;
      margin-left: 8px;
      transition: all 0.3s;
    }

    .input {
      height: 100%;
      width: 100%;
      border: none;
      outline: none;
      padding-left: 15px;
      background-color: transparent;
      color: white;
      font-size: 1em;
    }

    .max-btn {
      height: 100%;
      min-width: 95px;
      border: none;
      border-radius: 1rem;
      border: 3px solid #8143fc;
      color: #fff;
      cursor: pointer;
      font-weight: 500;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      transition: all 0.3s;
    }

    .input-wrapper:active .icon {
      transform: scale(1.3);
    }

    .max-btn:active {
      transform: scale(0.9);
    }
  }
}
</style>