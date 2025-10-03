<script setup>
import { computed, onMounted, ref, defineAsyncComponent, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import bg1 from '@/assets/loading_1.webp'
import bg2 from '@/assets/loading_2.webp'
import bg3 from '@/assets/loading_3.webp'
import { useTelegram } from '@/services/telegram'
import { useI18n } from 'vue-i18n'
const IconDone = defineAsyncComponent(() => import('@/assets/done.svg'))
const IconWait = defineAsyncComponent(() => import('@/assets/wait.svg'))
const IconComming = defineAsyncComponent(() => import('@/assets/comming.svg'))
const Logo = defineAsyncComponent(() => import('@/assets/fBTC.svg'))

const app = useAppStore()
const { tg } = useTelegram()
const { t, locale } = useI18n()

const TECH_MAINTENANCE = false;
const opacityLevels = ref([])

const scrollHandler = () => {
  const container = document.querySelector('.roadmap-container')
  const containerRect = container.getBoundingClientRect()
  const items = document.querySelectorAll('.roadmap-item')
  items.forEach((item, index) => {
    const rect = item.getBoundingClientRect()
    const elementHeight = rect.height // Висота елемента
    const startFadeDistance = elementHeight * 1.8 // Відстань для початку зникнення
    const distanceToTop = Math.max(0, containerRect.top - rect.top + startFadeDistance) // Відстань до верхнього краю
    const distanceToBottom = Math.max(0, rect.bottom - containerRect.bottom + startFadeDistance) // Відстань до нижнього краю

    let opacity = 1

    // Розрахунок прозорості для верхнього краю
    if (distanceToTop > 0 && distanceToTop <= startFadeDistance) {
      opacity = 1 - distanceToTop / startFadeDistance
      if (opacity < 0.5) opacity = 0.5
    }
    // Розрахунок прозорості для нижнього краю
    else if (distanceToBottom > 0 && distanceToBottom <= startFadeDistance) {
      opacity = 1 - distanceToBottom / startFadeDistance
      if (opacity < 0.5) opacity = 0.5
    }
    // Повністю прозорий, якщо елемент торкнувся краю
    else if (distanceToTop > startFadeDistance || distanceToBottom > startFadeDistance) {
      opacity = 0
    }

    opacityLevels.value[index] = opacity
  })
}

const images = [bg1, bg2, bg3]
const labels = [
  t('preloader.slider.energizer'),
  t('preloader.slider.miner'),
  t('preloader.slider.investor')
]

const rand = Math.floor(Math.random() * 3)
const currImage = ref(rand)
const currLabel = ref(rand)

// Dynamically update the background style
const backgroundStyle = computed(() => ({
  background: `linear-gradient(to bottom, #000000, #00000090 10%, transparent 25% 55%, #000000), url(${images[currImage.value]}) no-repeat bottom center`,
  backgroundSize: 'cover',
}))

const changeImage = () => {
  let rand = Math.floor(Math.random() * 3) + 1
  while (rand == 3) {
    rand = Math.floor(Math.random() * 3) + 1
  }

  currImage.value = (currImage.value + rand) % images.length
  currLabel.value = (currLabel.value + rand) % labels.length
}

// const progress = ref(0)
const emit = defineEmits(['progress-complete'])

const openMaintenance = () => {
  tg.openTelegramLink('https://t.me/ton4btc/720')
}

const endLoader = () => {
  if (tg.platform === 'android') {
   tg?.HapticFeedback.notificationOccurred('success');
  } else {
   tg?.HapticFeedback.impactOccurred('medium');
  }
  tg?.setHeaderColor('#141e36')
  emit('progress-complete')
}

// const makeProgress = () => {
//   // Функція для генерації випадкового числа від min до max включно
//   const getRandomIncrement = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min

//   const incrementProgress = () => {
//     if (progress.value < 100) {
//       // Перевіряємо, чи минуло 10 секунд і чи прогрес досяг 100%
//       if (progress.value >= 100) {
//         progress.value = 100 // Гарантуємо, що прогресбар буде на 100%
//         return
//       }
//       // Інкрементуємо прогрес випадковим числом від 1 до 10
//       progress.value += getRandomIncrement(5, 20)
//       // Переконуємося, що значення прогресу не перевищує 100
//       if (progress.value > 100) {
//         progress.value = 100
//       }
//       // Повторюємо інкрементацію через випадковий час від 100 до 500 мс
//       setTimeout(incrementProgress, getRandomIncrement(100, 300))
//     }
//   }
//   incrementProgress()
// }

onMounted(async () => {
  // window.onload = makeProgress
  setTimeout(() => {
    scrollHandler() // Гарантовано правильні розміри
  }, 150)
  setInterval(changeImage, 10000) // Change image every 10 seconds
})
</script>

<template>
  <div class="loader" :class="{ blocked: app?.blocked, maintenance: TECH_MAINTENANCE }">
    <header :style="app?.blocked || TECH_MAINTENANCE ? 'z-index: -1;' : ''">
      <Logo width="90px" />
      <h1>TonBitcoin Mine</h1>
      <div class="roadmap">
        <ul class="roadmap-container" @scroll="scrollHandler">
          <li class="roadmap-item" v-for="(item, index) in app?.roadmap" :key="index" :style="{
            opacity: opacityLevels[index],
            background:
              item.status == 3
                ? 'transparent'
                : item.status == 2
                  ? 'radial-gradient(ellipse 100% 30% at bottom, #FFFFFF70, transparent), linear-gradient(to bottom, #FCD909, #FEA400)'
                  : 'radial-gradient(ellipse 100% 30% at bottom, #FFFFFF70, transparent), linear-gradient(to bottom, #E2F974, #009600)',
            color: item.status == 3 ? '#ffffff50' : '#000',
            border: item.status == 3 ? '1px solid #ffffff25' : 'none',
          }">
            <IconDone :width="18" :height="18" v-show="item.status == 1" style="color: #000" />
            <IconWait :width="18" :height="18" v-show="item.status == 2" style="color: #000" />
            <IconComming :width="18" :height="18" v-show="item.status == 3" style="color: #ffffff50" />
            {{ item?.[`title${locale == 'uk' ? '' :  `_${locale}`}`] }}
            <span class="item-date">{{
              item.status == 3
                ? `Q${Math.ceil(new Date(item.item_date).getMonth() / 3)} ${new Date(item.item_date).getFullYear()}`
                : new Date(item.item_date).toLocaleDateString(
                  'ru-RU',
                  item.status == 1
                    ? {
                      year: '2-digit',
                      month: '2-digit',
                      day: '2-digit',
                    }
                    : {
                      year: 'numeric',
                      month: '2-digit',
                    },
                ) || 'SOON'
            }}</span>
          </li>
        </ul>
      </div>
    </header>
    <div class="content">
      <div v-if="!app?.blocked && !TECH_MAINTENANCE" class="slider" :style="backgroundStyle"></div>
      <div v-if="app?.blocked" class="user-ban">
        <img src="@/assets/blocked user.webp" />
        <div class="ban-data">
          <h1>{{ t('preloader.agent') }}</h1>
          <span v-html="t('preloader.agent_text')"></span>
        </div>
      </div>
      <div v-if="TECH_MAINTENANCE" class="user-maintenance">
        <img src="@/assets/maintenance.webp" />
        <div class="maintenance-data">
          <h1>{{ t('preloader.maintenance') }}</h1>
          <span v-html="t('preloader.maintenance_text')"></span>
          <!-- <span>Бот версии 2.4 закрыт с 27.06.2025 19.00</span>
          <span>Обновленный бот версии 3.0 будет открыт 03.07.2025</span>
          <br>
          <span>Подробнее на канале TonBitcoin:</span>
          <span style="opacity: 1;" @click="openMaintenance">t.me/ton4btc/720</span> -->
        </div>
      </div>
    </div>
    <footer>
      <h2 v-show="!app?.blocked && !TECH_MAINTENANCE">{{ labels[currLabel] }}</h2>
      <div v-show="app.loadingProgress < 100 || app?.blocked || TECH_MAINTENANCE" class="shell">
        <div class="bar" :class="{ blocked: app?.blocked }"
          :style="{ width: (app?.blocked || TECH_MAINTENANCE) ? '100%' : app.loadingProgress + '%' }">
        </div>
      </div>
      <Transition name="slide-fade">
        <button v-show="app.loadingProgress == 100 && !app?.blocked && !TECH_MAINTENANCE" class="start-btn"
          @click="endLoader">
          {{ t('preloader.start_btn') }}
        </button>
      </Transition>
      <h1 v-show="app.loadingProgress < 100 && !app?.blocked && !TECH_MAINTENANCE">{{ t('preloader.loading') }}</h1>
      <h1 v-show="app?.blocked || TECH_MAINTENANCE">{{ t('preloader.unpossible') }}</h1>
      <span>TonBitcoin Ver. 3.0</span>
    </footer>
  </div>
</template>

<style lang="scss" scoped>
.slide-fade-enter-active {
  transition: all 0.8s ease-out;
}

.slide-fade-enter-from {
  transform: translateX(30px);
  opacity: 0;
}

.loader {
  position: absolute;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  z-index: 10000;
  background: radial-gradient(ellipse 90% 25% at top, #ffd63175, #ffd63100), #000000;

  &.blocked {
    background-image: url('@/assets/blocked_bg.webp');
    background-position: center;
    background-size: contain;
  }

  &.maintenance {
    background-image: url('@/assets/maintenance_bg.webp');
    background-position: center;
    background-size: contain;
  }
}

.shell {
  margin: 0 auto;
  height: 10px;
  width: 90%;
  border-radius: 13px;
}

.bar {
  background: linear-gradient(to bottom, #fccd08, #fea602);
  height: 100%;
  width: 10px;
  border-radius: 1rem;
  transition: width 0.5s ease-in-out;

  &.blocked {
    background: linear-gradient(to bottom, #ff3b59, #b92b41);
  }
}

header {
  position: absolute;
  width: 100%;
  top: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;

  .roadmap {
    width: 90%;

    ul {
      width: 100%;
      margin: 0 auto;
      height: 260px;
      padding-bottom: 20px;
      display: flex;
      flex-direction: column;
      justify-content: start;
      align-items: start;
      gap: 0.5rem;
      overflow-y: scroll;
      -ms-overflow-style: none;
      scrollbar-width: none;

      &::-webkit-scrollbar {
        display: none;
      }

      .roadmap-item {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: start;
        gap: 0.7rem;
        font-family: 'Inter' !important;
        font-weight: 600;
        font-size: clamp(8px, 3.4vw, 14px);
        width: 100%;
        max-height: 36px;
        padding: 0.5rem 1.5rem;
        border-radius: 1rem;
        transition: opacity 0.5s ease;

        .item-date {
          position: absolute;
          top: 0;
          bottom: 0;
          right: 0.5rem;
          height: max-content;
          margin: auto 0;
          padding: 0.4rem;
          line-height: 1.1;
          border-radius: 5rem;
          font-family: 'Inter' !important;
          font-weight: bold;
          font-size: 9px;
          box-shadow: inset 0 0 0 1px #000;
        }
      }
    }
  }

  h1 {
    font-family: 'Roboto', sans-serif;
    background-image: linear-gradient(to bottom, #fcd909, #fea400);
    color: transparent;
    background-clip: text;
    font-size: 2.2rem;
    font-weight: bold;
  }
}

.content {
  margin-left: auto;
  margin-right: auto;
  width: 100%;

  .user-ban {
    position: absolute;
    bottom: 100px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;

    img {
      position: absolute;
      z-index: -1;
      width: 256px;
      margin-top: -70%;
      filter: drop-shadow(0 30px 40px #ffffffd0);
    }

    .ban-data {
      width: 90%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      padding: 0.5rem 0.6rem;
      background: #10151b;
      border: 1px solid #ff3b59;
      border-radius: 1rem;

      h1 {
        text-align: center;
        font-family: 'Roboto', sans-serif;
        font-weight: 600;
        font-size: 24px;
        color: #fff;
      }

      span {
        text-align: center;
        color: #fff;
        font-family: 'Roboto', sans-serif;
        font-weight: 400;
        font-size: 13px;
        opacity: 0.6;
      }
    }
  }

  .user-maintenance {
    position: absolute;
    bottom: 100px;
    z-index: 9999;
    display: flex;
    width: 100%;
    flex-direction: column;
    justify-content: center;
    align-items: center;

    img {
      position: absolute;
      z-index: -1;
      width: 256px;
      margin-top: -70%;
      filter: drop-shadow(0 30px 40px #ffffffd0);
    }

    .maintenance-data {
      width: 90%;
      display: flex;
      margin: 0 auto;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      padding: 0.5rem 0.6rem;
      background: #10151b;
      border: 1px solid #FFD500;
      border-radius: 1rem;

      h1 {
        text-align: center;
        font-family: 'Roboto', sans-serif;
        font-weight: 600;
        font-size: 24px;
        color: #fff;
      }

      span {
        text-align: center;
        color: #fff;
        font-family: 'Roboto', sans-serif;
        font-weight: 400;
        font-size: 13px;
        opacity: 0.6;
      }

      a {
        text-align: center;
        color: #fff;
        font-family: 'Roboto', sans-serif;
        font-weight: 400;
        font-size: 13px;
      }
    }
  }

  .slider {
    position: absolute;
    bottom: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    width: 100%;
    height: 40%;
    z-index: -1;
  }
}

footer {
  position: absolute;
  width: 100%;
  bottom: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  justify-content: center;

  h2 {
    font-family: 'Inter' !important;
    font-size: 13px;
    font-weight: 600;
    color: #fff;
  }

  h1 {
    font-family: 'Inter' !important;
    font-size: 17px;
    font-weight: 700;
    color: #fff;
  }

  span {
    font-family: 'Inter' !important;
    font-weight: 500;
    font-size: 10px;
    color: #fff;
  }

  .start-btn {
    background: linear-gradient(to bottom, #fcd909, #fea400);
    padding: 0.5rem 1rem;
    border-radius: 2rem;
    border: 2px solid #ffffff70;
    width: 90%;
    font-family: 'Inter' !important;
    font-weight: 700;
    font-size: 17px;

    &:active {
      background: linear-gradient(to bottom, #fcd90990, #fea40090);
    }
  }
}
</style>
