<script setup>
import { useAppStore } from '@/stores/app'
import { ref, onMounted, watch, computed, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const app = useAppStore()
// const CurrBase = defineAsyncComponent(() => import(`@/assets/${app.user.station_type}-${app.user.storage_level}.png`))
const currBase = computed(() => {
  if (app?.user?.has_orbital_station && !app?.user?.orbital_force_basic) {
    return new URL(`../assets/Orbital Power Plant.webp`, import.meta.url).href
  }
  if (app?.user?.has_singularity_station) {
    return new URL(`../assets/gems/singularity_power_plant.webp`, import.meta.url).href
  }
  if (app?.user?.has_hydro_station) {
    return new URL(`../assets/Hydroelectric power plant.webp`, import.meta.url).href
  }
  return new URL(`../assets/${app?.user?.station_type}-${app?.user?.storage_level}.webp`, import.meta.url).href
})

const otherBasePath = (base, lvl) => {
  const com = computed(() => new URL(`../assets/${base}-${lvl}.webp`,
    import.meta.url).href)
  return com
}

const allStationsFiltered = computed(() => [...new Set((app.stations?.storage_configs || []).filter(el => {
  if (app.user?.has_hydro_station) return el?.station_type !== 'Hydroelectric power plant'
  if (app.user?.has_orbital_station) return el?.station_type !== 'Orbital power plant'
  return true
}).map((el) => el?.station_type))])

const allStations = computed(() => {
  const list = allStationsFiltered.value
  const current = app.user?.station_type
  if (!current || list.includes(current)) return list
  return [...list, current]
})

const currStation = ref(app.user?.station_type)

function makeElementCentral(array, targetElement) {
  if (!array?.length) return array || []
  const targetIndex = array.indexOf(targetElement)
  if (targetIndex === -1) return array
  const middleIndex = Math.floor(array.length / 2)
  const offset = (targetIndex - middleIndex + array.length) % array.length
  return [...array.slice(offset), ...array.slice(0, offset)]
}

const slides = ref([])
function updateSlides() {
  slides.value = makeElementCentral(allStations.value, app.user?.station_type) || []
}

const sliderContent = ref(null)

const activeSlide = ref(null)

const emit = defineEmits(['input', 'buystation', 'mintstation'])

let sliders = ref(null)
let center, leftEndBack, leftEnd, leftMid, rightMid, rightEnd, rightEndBack

function initializePositions() {
  sliders.value = sliderContent.value?.querySelectorAll('.slide');
  center = Math.floor(sliders.value.length / 2);
  activeSlide.value = slides.value[center];
  leftEndBack = center - 3 >= 0 ? center - 3 : undefined;
  leftEnd = center - 2 >= 0 ? center - 2 : undefined;
  leftMid = center - 1 >= 0 ? center - 1 : undefined;
  rightMid = center + 1 < sliders.value.length ? center + 1 : undefined;
  rightEnd = center + 2 < sliders.value.length ? center + 2 : undefined;
  rightEndBack = center + 3 < sliders.value.length ? center + 3 : undefined;
  updateSliderClasses();
}

function updateSliderClasses() {
  sliders.value?.forEach((slider, index) => {
    slider.classList.remove('position-none', 'position-1', 'position-2', 'position-3', 'position-4', 'position-5');
    if (index === leftEndBack) slider.classList.add('position-none');
    else if (index === leftEnd) slider.classList.add('position-1');
    else if (index === leftMid) slider.classList.add('position-2');
    else if (index === center) slider.classList.add('position-3');
    else if (index === rightMid) slider.classList.add('position-4');
    else if (index === rightEnd) slider.classList.add('position-5');
    else if (index === rightEndBack) slider.classList.add('position-none');
  })
}

function leftScroll() {
  leftEndBack = updateIndex(leftEndBack, -1)
  leftEnd = updateIndex(leftEnd, -1)
  leftMid = updateIndex(leftMid, -1)
  center = updateIndex(center, -1)
  rightMid = updateIndex(rightMid, -1)
  rightEnd = updateIndex(rightEnd, -1)
  rightEndBack = updateIndex(rightEndBack, -1)
  updateSliderClasses()
  activeSlide.value = slides.value[center]
}

function rightScroll() {
  leftEndBack = updateIndex(leftEndBack, 1)
  leftEnd = updateIndex(leftEnd, 1)
  leftMid = updateIndex(leftMid, 1)
  center = updateIndex(center, 1)
  rightMid = updateIndex(rightMid, 1)
  rightEnd = updateIndex(rightEnd, 1)
  rightEndBack = updateIndex(rightEndBack, 1)
  updateSliderClasses()
  activeSlide.value = slides.value[center]
}

function updateIndex(index, increment) {
  if (index === undefined) return index
  index += increment
  if (index < 0) return sliders.value.length - 1
  if (index >= sliders.value.length) return 0
  return index
}

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
  const interval = setInterval(updateTime, 1000)

  // Очищаємо інтервал при завершенні (опціонально, залежить від фреймворку)
  onUnmounted(() => clearInterval(interval))

  return { time: timeRemaining.value, remain: timeRemainingMs.value }
}

class Swipe {
  constructor(element) {
    this.xDown = null
    this.yDown = null
    this.element = typeof element === 'string' ? document.querySelector(element) : element

    // Ініціалізація колбеків
    this.onLeftCallback = null
    this.onRightCallback = null

    this.element.addEventListener('touchstart', this.handleTouchStart.bind(this), false)
    this.element.addEventListener('touchmove', this.handleTouchMove.bind(this), false)
  }

  handleTouchStart(evt) {
    if (!this.xDown && !this.yDown) {
      this.xDown = evt.touches[0].clientX
      this.yDown = evt.touches[0].clientY
    }
  }

  handleTouchMove(evt) {
    if (!this.xDown || !this.yDown) return

    const xUp = evt.touches[0].clientX
    const yUp = evt.touches[0].clientY

    const xDiff = this.xDown - xUp
    const yDiff = this.yDown - yUp

    // Перевірка на горизонтальний свайп
    if (Math.abs(xDiff) > Math.abs(yDiff)) {
      if (xDiff > 0 && this.onLeftCallback) {
        this.onLeftCallback() // Визначаємо лівий свайп
      } else if (xDiff < 0 && this.onRightCallback) {
        this.onRightCallback() // Визначаємо правий свайп
      }
    }

    // Скидаємо координати після завершення свайпу
    this.xDown = null
    this.yDown = null
  }

  onLeft(callback) {
    this.onLeftCallback = callback
    return this
  }

  onRight(callback) {
    this.onRightCallback = callback
    return this
  }
}

onMounted(() => {
  updateSlides()
  initializePositions()
  const swipe = new Swipe(sliderContent.value)
  swipe.onRight(() => leftScroll()).onLeft(() => rightScroll())
})

watch(app, (newApp) => {
  if (currStation.value !== newApp?.user?.station_type) {
    currStation.value = newApp?.user?.station_type
    updateSlides()
    initializePositions()
  }
}, { deep: true })

watch(allStations, () => {
  updateSlides()
  if (sliderContent.value) initializePositions()
}, { immediate: false })

watch(activeSlide, (newActiveSlide) => {
  emit('input', newActiveSlide)
})
</script>
<template>
  <div class="main-container">
    <div class="slider-container">
      <div class="slider-content" ref="sliderContent">
        <div class="slide" v-for="(slide, index) in slides" :key="index">
          <div class="media">
            <!-- <img :src="slide.img" alt=""> -->
            <!-- <CurrBase v-if="slide == app.user.station_type" :width="200" class="station" /> -->
            <img :src="currBase" v-if="slide == app.user.station_type" width="200px" class="station object-contain" />
            <img :src="otherBasePath(slide, 1)?.value" v-if="
              slide !== app.user.station_type &&
              allStations.indexOf(slide) > allStations.indexOf(app.user.station_type)
            " width="200px" class="station object-contain" :class="{
              unavailable:
                allStations.indexOf(slide) > allStations.indexOf(app.user.station_type),
            }" />
            <img :src="otherBasePath(slide, 1)?.value" v-if="
              slide !== app.user.station_type &&
              allStations.indexOf(slide) == allStations.indexOf(app.user.station_type) + 1 &&
              app.user.storage_level == 3 &&
              app.user.generation_level == 3
            " width="200px" class="station object-contain" :class="{
              unavailable: app.user.has_hydro_station || app.user?.has_orbital_station
            }" />
            <img :src="otherBasePath(slide, 3)?.value" v-if="
              slide !== app.user.station_type &&
              allStations.indexOf(slide) < allStations.indexOf(app.user.station_type)
            " width="200px" class="station object-contain" :class="{
              unavailable:
                allStations.indexOf(slide) > allStations.indexOf(app.user.station_type),
            }" />
          </div>
          <div class="card-sections">
            <div class="lower-section">
              <div v-if="
                !app.user.has_orbital_station &&
                !app.user.has_hydro_station &&
                allStations.indexOf(slide) == allStations.indexOf(app.user.station_type) + 1 &&
                app.user.storage_level == 3 &&
                app.user.generation_level == 3 &&
                allStations.indexOf(app.user?.station_type) < 3
              " class="card-button" @click="emit('buystation')">
                {{ t('common.buy') }}
              </div>
              <div v-if="
                !app.user.has_orbital_station &&
                !app.user.has_hydro_station &&
                allStations.indexOf(slide) == allStations.indexOf(app.user.station_type) + 1 &&
                app.user.storage_level == 3 &&
                app.user.generation_level == 3 &&
                allStations.indexOf(app.user?.station_type) >= 3
              " class="card-button mint"
                :class="{ disabled: (app.user?.building_until && getTimeRemaining(app.user?.building_until).remain > 0) || ((!app.stationsNft.length || !app.user?.current_mint) && allStations?.indexOf(app.user?.station_type) !== 3) }"
                @click="() => {
                  if ((app.user?.building_until && getTimeRemaining(app.user?.building_until).remain > 0) || ((!app.stationsNft.length || !app.user?.current_mint) && allStations?.indexOf(app.user?.station_type) !== 3)) return;
                  emit('mintstation')
                }">
                {{ allStations?.indexOf(app.user?.station_type) == 3 ? t('modals.station_slider.mint_nft') :
                  t('modals.station_slider.craft_nft') }}
              </div>
              <!-- <div v-if="allStations.indexOf(slide) > allStations.indexOf(app.user.station_type)" class="error-button">
                {{ t('modals.station_slider.unavailable') }}
              </div> -->
              <div v-if="allStations.indexOf(slide) > allStations.indexOf(app?.user?.station_type)" class="level"
                :class="{ mint: allStations.indexOf(slide) > 3 }">
                {{ t('modals.station_slider.level') }} 1
              </div>
              <div v-if="allStations.indexOf(slide) < allStations.indexOf(app?.user?.station_type)" class="level"
                :class="{ mint: allStations.indexOf(slide) > 3 }">
                {{ t('modals.station_slider.level') }} 3
              </div>
              <div v-if="allStations.indexOf(slide) == allStations.indexOf(app?.user?.station_type)" class="level"
                :class="{ mint: allStations.indexOf(slide) > 3 }">
                {{ t('modals.station_slider.level') }} {{ app.user?.storage_level ?? 0 }}
              </div>
            </div>
          </div>
        </div>
        <div class="slider-content-background"></div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.main-container {
  display: flex;
  justify-content: center;
  align-items: center;
}

.slider-container {
  height: 10rem;
  width: 100vw;
  display: flex;
  justify-content: center;
  align-items: center;
  user-select: none;
  position: relative;
}

.slider-content {
  height: 100%;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: end;
  flex-direction: row;
  overflow: visible;
  position: relative;
  perspective: 100px;
  will-change: transform, filter;
  contain: layout;
}

.slider-content .slide {
  position: absolute;
  left: 50%;
  height: 10rem;
  max-height: 400px;
  width: 15rem;
  /*   border: 1px solid; */
  border-radius: 25px;
  left: 50%;
  z-index: 0;
  /*   opacity: 0; */
  transform: translate(-50%, 0) rotateY(0deg) scale(1, 1);
  transform-style: preserve-3d;
  will-change: transform, filter;
  display: flex;
  justify-content: center;
  align-items: center;
  transition:
    transform 0.5s ease-in-out,
    opacity 0.5s ease-in-out,
    left 0.5s ease-in-out,
    z-index 0s 0.25s ease-in-out,
    box-shadow 0.5s ease-in-out,
    filter 0.5s ease-in-out;
}

.slide.position-1 {
  left: 20% !important;
  z-index: 1 !important;
  transform: translate(-50%, 0) rotateY(-2deg) scale(0.8, 0.8) !important;
  opacity: 1 !important;
  box-shadow: 0px 0.4rem 1.6rem rgba(0, 0, 0, 0.1) !important;
  filter: blur(5px);
  overflow: visible;
}

.slide.position-2 {
  left: 35% !important;
  z-index: 2 !important;
  transform: translate(-50%, 0) rotateY(-1deg) scale(0.9, 0.9) !important;
  opacity: 1 !important;
  filter: blur(2px);
  overflow: visible;
}

.slide.position-3 {
  left: 50% !important;
  z-index: 4 !important;
  transform: translate(-50%, 0) rotateY(0deg) scale(1.05, 1.05) !important;
  opacity: 1 !important;
  cursor: pointer;
  filter: blur(0px);
  overflow: visible;
}

.slide.position-4 {
  left: 65% !important;
  z-index: 2 !important;
  transform: translate(-50%, 0) rotateY(1deg) scale(0.9, 0.9) !important;
  opacity: 1 !important;
  filter: blur(2px);
  overflow: visible;
}

.slide.position-5 {
  left: 80% !important;
  z-index: 1 !important;
  transform: translate(-50%, 0) rotateY(2deg) scale(0.8, 0.8) !important;
  opacity: 1 !important;
  filter: blur(5px);
  overflow: visible;
}

.slide.position-none {
  left: 50%;
  z-index: 0;
  transform: translate(-50%, 0) rotateY(0deg) scale(0.7, 0.7);
  opacity: 1;
  overflow: visible;
}

.slider-container i {
  width: 2rem;
  height: 2rem;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  border-radius: 50%;
}

.slider-content .slide .card-sections .upper-section,
.slider-content .slide .card-button {
  opacity: 1;
  transition: opacity 0.6s ease-in-out;
}

.slider-content .slide .card-sections .upper-section,
.slider-content .slide .error-button {
  opacity: 0;
  transition: opacity 0.6s ease-in-out;
}

.slider-content .slide.position-3 .card-sections .upper-section,
.slider-content .slide.position-3 .card-button {
  opacity: 1;
  transition: opacity 0.6s ease-in-out;
}

.slider-content .slide.position-3 .card-sections .upper-section,
.slider-content .slide.position-3 .error-button {
  opacity: 1;
  transition: opacity 0.6s ease-in-out;
}

.slide>* {
  color: white;
  font-family: 'Inter' !important;
  font-size: 90%;
  letter-spacing: -0.001em;
}

.media,
.card-sections {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.media {
  display: flex;
  align-items: center;
  justify-content: center;
  will-change: transform, filter;
}

.station {
  position: absolute;
  height: 100%;
  will-change: transform, filter;
  filter: drop-shadow(0 0 50px #436efc);

  &.unavailable {
    filter: grayscale(1) drop-shadow(0 0 50px #436efc);
  }
}

.card-sections {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  box-sizing: border-box;
}

.upper-section {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
}

.lower-section {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 1rem;

  .level {
    position: absolute;
    bottom: 0;
    color: #212121;
    font-family: 'Inter' !important;
    font-weight: 600;
    font-size: 8px;
    border-radius: .5rem;
    padding: 0.2rem 0.5rem;
    background: radial-gradient(ellipse 80% 20% at bottom, #ffffff70, transparent),
      linear-gradient(to bottom, #e2f974, #009600);

    &.mint {
      color: #fff;
      border: 1px solid #ffffff50;
      background: radial-gradient(ellipse 80% 20% at bottom, #ffffff25, transparent),
        linear-gradient(to bottom, #6478DB, #5045C1);
    }
  }
}

.card-sections .lower-section .card-button {
  color: #000;
  background: linear-gradient(to bottom, #e2f974, #009600);
  box-shadow: inset 0 0 2px 2px #ffffff50;
  padding: 0.7rem 1rem;
  border-radius: 0.3rem;
  font-family: 'Inter' !important;
  font-weight: 600;
  font-size: 13px;

  &.mint {
    background: linear-gradient(to bottom, #fcd909, #fea400);
  }

  &.disabled {
    background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent), linear-gradient(to bottom, #e2e2e2, #646464);
  }

  &:active {
    opacity: 0.8;
  }
}

.card-sections .lower-section .error-button {
  color: #fff;
  background: linear-gradient(to bottom, #ff424e, #a10f0f95);
  box-shadow: inset 0 0 2px 2px #ffffff50;
  padding: 0.7rem 1rem;
  border-radius: 0.3rem;
  font-family: 'Inter' !important;
  font-weight: 600;
  font-size: 13px;
}

@media screen and (max-width: 620px) {

  .slide.position-1,
  .slide.position-5 {
    opacity: 0.5 !important;
  }

  .slide.position-2,
  .slide.position-4 {
    opacity: 0.95 !important;
  }
}

@media screen and (max-width: 445px) {

  .slide.position-1,
  .slide.position-5 {
    opacity: 0 !important;
  }

  .slide.position-2,
  .slide.position-4 {
    opacity: 0.5 !important;
  }
}

@media screen and (max-width: 435px) {
  .slide {
    opacity: 0 !important;
    box-shadow: none !important;
  }

  .slide.position-3 {
    box-shadow: none !important;
    opacity: 1 !important;
  }

  .slide.position-1,
  .slide.position-2 {
    left: 10% !important;
    transform: translate(-50%, 0) rotateY(0deg) scale(0.7, 0.7) !important;
  }

  .slide.position-4,
  .slide.position-5 {
    left: 90% !important;
    transform: translate(-50%, 0) rotateY(0deg) scale(0.7, 0.7) !important;
  }
}
</style>
