<script setup>
import { defineAsyncComponent, onMounted, onUnmounted, ref } from 'vue'
// const UpTrend = defineAsyncComponent(() => import('@/assets/up-trend.svg'))
// const DownTrend = defineAsyncComponent(() => import('@/assets/down-trend.svg'))
const DeDust = defineAsyncComponent(() => import('@/assets/dedust.svg'))
const Stonfi = defineAsyncComponent(() => import('@/assets/stonfi.svg'))
import { useTelegram } from '@/services/telegram'
import axios from 'axios'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'


const app = useAppStore()
const { tg } = useTelegram()
const { t } = useI18n()

const stonfiFBTCPrice = ref(0)
const stonfiKwPrice = ref(0)
let controller = null

const direct = (link) => {
  return link.includes('t.me') ? tg?.openTelegramLink(link) : tg?.openLink(link)
}

function roundToFirstSignificantDecimal(num) {
  if (num === 0) return 0 // Для 0 возвращаем 0

  const magnitude = Math.pow(10, -Math.floor(Math.log10(Math.abs(num))))
  return Math.round(num * magnitude) / magnitude
}

let intervalId

const fetchData = async () => {
  let controller1 = new AbortController()
  let controller2 = new AbortController()

  const promises = [
    // Первый запрос
    axios.get('https://api.ston.fi/v1/assets/EQBhF8jWase_Cn1dNTTe_3KMWQQzDbVw_lUUkvW5k6s61ikb', {
      signal: controller1.signal
    }),

    // Второй запрос
    axios.get('https://api.ston.fi/v1/assets/EQBOqBiArR45GUlifxdzZ40ZahdVhjtU7GjY-lVtqruHvQEc', {
      signal: controller2.signal
    })
  ]

  const results = await Promise.allSettled(promises)

  // Обработка результатов
  results.forEach((result, index) => {
    if (result.status === 'fulfilled') {
      switch (index) {
        case 0:
          stonfiKwPrice.value = result.value?.data?.asset?.dex_usd_price
          break
        case 1:
          stonfiFBTCPrice.value = result.value?.data?.asset?.dex_usd_price
          break
      }
    } else {
      console.error(`Ошибка в запросе ${index + 1}:`, result.reason)
    }
  })

  // Очистка контроллеров
  controller1 = null
  controller2 = null
}

const startInterval = () => {
  intervalId = setInterval(fetchData, 10000)
}

const stopInterval = () => {
  clearInterval(intervalId)
}

onMounted(() => {
  // window.addEventListener('focus', startInterval())
  // window.addEventListener('blur', stopInterval())
  fetchData()
  startInterval()
})

onUnmounted(() => {
  clearInterval(intervalId)
  window.removeEventListener('focus', startInterval())
  window.removeEventListener('blur', stopInterval())
  if (controller) {
    controller.abort()
  }
})
</script>

<template>
  <div class="screen-box">
    <h1 class="title">{{ t('market.title') }}</h1>

    <div class="market-grid">
      <div class="item">
        <span class="comm">{{ t('common.comming') }}</span>
        <div class="label-group" style="filter: blur(3px); opacity: 0.5">
          <span class="label-text">{{ t('market.rate', { pair: "kW/TON" }) }}
            <DeDust :width="14" /> DeDust
          </span>
        </div>
        <div class="price-group" style="filter: blur(3px); opacity: 0.5">
          <div class="indicator-row">
            <!-- <UpTrend /> -->
            <!-- <h3>${{ +(+dedustKWPrice * 1000)?.toFixed(6) || '0.000000' }}</h3> -->
            <h3>$0.0000</h3>
            <!-- <p>{{ t('market.per_k') }}</p> -->
          </div>
          <button class="trade-btn">
            {{ t('market.trade_btn') }}<img src="@/assets/kW_token.png" width="18px" height="18px" />
          </button>
        </div>
      </div>
      <div class="item">
        <div class="label-group">
          <span class="label-text">{{ t('market.rate', { pair: "kW/TON" }) }}
            <Stonfi :width="14" />Stonfi
          </span>
        </div>
        <div class="price-group">
          <div class="indicator-row" style="line-height: 22px;">
            <!-- <DownTrend /> -->
            <h3>${{ +(+stonfiKwPrice * 1000)?.toFixed(4) || +(+app?.stonfi_kw * 1000)?.toFixed(4) || '0.0000' }}</h3>
            <p>{{ t('market.per_k') }}</p>
          </div>
          <button class="trade-btn" @click="
            direct(
              'https://app.ston.fi/swap?chartVisible=true&ft=TON&tt=EQBhF8jWase_Cn1dNTTe_3KMWQQzDbVw_lUUkvW5k6s61ikb&chartInterval=1w',
            )
            ">{{ t('market.trade_btn') }}<img src="@/assets/kW_token.png" width="18px" height="18px" /></button>
        </div>
      </div>
      <div class="item">
        <div class="label-group">
          <span class="comm">{{ t('common.comming') }}</span>
          <span class="label-text" style="filter: blur(3px); opacity: 0.5">
            {{ t('market.rate', { pair: "tBTC/TON" }) }}
            <DeDust :width="14" /> DeDust
          </span>
        </div>
        <div class="price-group" style="filter: blur(3px); opacity: 0.5">
          <div class="indicator-row">
            <!-- <UpTrend /> -->
            <h3>$0.0000</h3>
          </div>
          <button class="trade-btn">
            {{ t('market.trade_btn') }}
            <img src="@/assets/tBTC.png" width="18px" height="18px" />
          </button>
        </div>
      </div>
      <div class="item">
        <div class="label-group">
          <span class="label-text">{{ t('market.rate', { pair: "fBTC/TON" }) }}
            <Stonfi :width="14" />Stonfi
          </span>
        </div>
        <div class="price-group">
          <div class="indicator-row">
            <!-- <UpTrend /> -->
            <h3>${{ +(+stonfiFBTCPrice)?.toFixed(4) || +(+app?.stonfi_fbtc)?.toFixed(4) || '0.0000' }}</h3>
          </div>
          <button class="trade-btn"
            @click="direct('https://app.ston.fi/swap?chartVisible=true&ft=TON&tt=EQBOqBiArR45GUlifxdzZ40ZahdVhjtU7GjY-lVtqruHvQEc&chartInterval=1w')">{{
              t('market.trade_btn') }} <img src="@/assets/fBTC.webp" width="18px" height="18px" /></button>
        </div>
      </div>
      <button class="view-btn" @click="
        direct(
          'https://www.geckoterminal.com/ton/pools/EQDRJ6wZJeaYYcR3FrqaShDgV2SyDtKBwoGI_wChiTrXL9mr',
        )
        ">
        {{ t('market.look_chart_btn', { pair: "fBTC/TON" }) }}
      </button>
      <button class="view-btn" @click="
        direct(
          'https://www.geckoterminal.com/ton/pools/EQAHxCJBgyH8aXBizy3zLnHfZPYBQ4DAlkVXYZ3yrKNHcrX2',
        )
        ">
        {{ t('market.look_chart_btn', { pair: "kW/TON" }) }}
      </button>
      <div class="item comming">
        <span>{{ t('market.more_dex') }}</span>
      </div>
      <button class="check-news" @click="direct('https://t.me/ton4btc')">{{ t('market.check_news_btn') }}</button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.screen-box {
  position: absolute;
  top: 0;
  width: 100%;
  height: 100vh;
  background: radial-gradient(ellipse 90% 50% at top right, #ffbe3150, transparent) #000;
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

.market-grid {
  display: grid;
  width: 90%;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.7rem;

  .item {
    position: relative;
    width: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    background: #151408;
    border: 1px solid #ffffff25;
    border-radius: 1rem;
    padding: 0.5rem 1rem;
    gap: 0.5rem;
    overflow: hidden;

    .comm {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      color: #fff;
      font-family: 'Inter' !important;
      font-weight: 700;
      font-size: 20px;
      text-align: center;
      width: 100%;
    }

    .label-group {
      display: flex;

      .label-text {
        color: #fff;
        font-family: 'Inter' !important;
        font-weight: 700;
        font-size: 2.3vw;
        display: flex;
        align-items: center;
        justify-content: center;
        text-wrap: nowrap;
        gap: 0.2rem;
      }
    }

    .price-group {
      display: flex;
      flex-direction: column;
      width: 100%;

      .indicator-row {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0;

        h3 {
          color: #fff;
          font-family: 'Inter' !important;
          font-weight: 700;
          font-size: 27px;
        }

        p {
          color: #ffffff50;
          font-family: 'Inter' !important;
          font-weight: 600;
          font-size: 12px;
        }
      }

      button {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0.5rem;
        font-family: 'Inter' !important;
        font-size: clamp(11px, 4vw, 16px);
        font-weight: 600;
        height: 30px;
        width: 100%;
        border-radius: 5px;
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);

        &:active {
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
            linear-gradient(to bottom, #fcd90990, #fea40090);
        }
      }
    }
  }

  .view-btn {
    grid-column: span 2 / span 2;
    font-family: 'Inter' !important;
    font-size: clamp(11px, 5vw, 18px);
    font-weight: 700;
    height: 38px;
    width: 100%;
    border-radius: 0.8rem;
    background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
      linear-gradient(to bottom, #fcd909, #fea400);

    &:active {
      background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
        linear-gradient(to bottom, #fcd90990, #fea40090);
    }
  }

  .comming {
    position: relative;
    grid-column: span 2 / span 2;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    width: 100%;
    padding: 1rem 3rem;
    background:
      linear-gradient(to bottom, #15140890, #15140890),
      url('@/assets/comming-trend.svg') no-repeat center,
      linear-gradient(to bottom, #fcd90925, #fea40025);
    background-size: cover;

    span {
      color: #fff;
      font-family: 'Inter' !important;
      font-size: clamp(11px, 5vw, 24px);
      font-weight: 700;
    }
  }

  .check-news {
    grid-column: span 2 / span 2;
    font-family: 'Inter' !important;
    font-size: clamp(11px, 5vw, 24px);
    font-weight: 700;
    height: 69px;
    width: 100%;
    padding-left: 5rem;
    border-radius: 0.8rem;
    background:
      url('@/assets/btn-paper.png') no-repeat left,
      radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
      linear-gradient(to bottom, #fcd909, #fea400);

    &:active {
      background:
        url('@/assets/btn-paper.png') no-repeat left,
        radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
        linear-gradient(to bottom, #fcd90990, #fea40090);
    }
  }
}
</style>
