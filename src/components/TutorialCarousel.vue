<template>
  <swiper ref="swiperRef" class="swp" :modules="modules" :effect="'fade'" :speed="0" :slides-per-view="1"
    :pagination="true" @swiper="onSwiper" @slideChange="onSlideChange">
    <swiper-slide class="slide" v-for="(slide, index) in slides" :key="index">
      <div class="main-area">
        <div class="grouping">
          <h1 v-if="slide.title" v-html="slide.title"></h1>
          <p v-if="slide.description" v-html="slide?.description"></p>
        </div>
        <img class="item-image" :class="{ animation: index !== 0 }" :src="slide.image" rel="preload" />
        <button v-if="index < slides.length - 1" @click="swiperNextSlide" class="tutor-btn">
          {{ t('modals.tutorial_carousel.next') }}
        </button>
        <button v-if="index == slides.length - 1" @click="emitClose" class="tutor-btn">
          {{ t('modals.tutorial_carousel.join') }}
        </button>
      </div>
    </swiper-slide>
  </swiper>
</template>

<script setup>
import { Pagination, Navigation, A11y, EffectFade } from 'swiper/modules'
import { Swiper, SwiperSlide } from 'swiper/vue'
import 'swiper/css'
import 'swiper/css/effect-fade'
import 'swiper/css/pagination'

import tutor1 from '@/assets/tutor-1.png'
import tutor2 from '@/assets/tutor-2.png'
import tutor3 from '@/assets/tutor-3.png'
import tutor4 from '@/assets/tutor-4.png'
import tutor5 from '@/assets/tutor-5.png'

import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const updColors = () => {
  const elements = document.querySelectorAll('.slide')

  elements.forEach((element, index) => {
    // Приклад динамічних кольорів (залежно від індексу або інших даних)
    const startColor = slides[index].overlay1
    const endColor = slides[index].overlay2
    const backColor = slides[index].back

    // Задаємо кольори через CSS-перемінні
    element.style.setProperty('--start-color', startColor)
    element.style.setProperty('--end-color', endColor)
    element.style.setProperty('--back-color', backColor)
  })
}

const modules = ref([Pagination, A11y, Navigation, EffectFade])

const slides = [
  {
    title: t('modals.tutorial_carousel.slide_1_title'),
    description: t('modals.tutorial_carousel.slide_1_description'),
    back: '#0E1323',
    overlay1: '#31CFFF',
    overlay2: '#0E112A',
    image: tutor1,
  },
  {
    title: t('modals.tutorial_carousel.slide_2_title'),
    description: t('modals.tutorial_carousel.slide_2_description'),
    back: '#0E1323',
    overlay1: '#31CFFF',
    overlay2: '#0E112A',
    image: tutor2,
  },
  {
    title: t('modals.tutorial_carousel.slide_3_title'),
    description: t('modals.tutorial_carousel.slide_3_description'),
    back: '#0E1323',
    overlay1: '#31FF80',
    overlay2: '#0E112A',
    image: tutor3,
  },
  {
    title: t('modals.tutorial_carousel.slide_4_title'),
    description: t('modals.tutorial_carousel.slide_4_description'),
    back: '#0E1323',
    overlay1: '#8143FC',
    overlay2: '#0E112A',
    image: tutor4,
  },
  {
    title: t('modals.tutorial_carousel.slide_5_title'),
    description: null,
    back: '#0E1323',
    overlay1: '#31CFFF',
    overlay2: '#0E112A',
    image: tutor5,
  },
]

const emit = defineEmits(['close'])

const emitClose = () => {
  emit('close')
}

const swiperInstance = ref()

const onSwiper = (swiper) => {
  updColors()
  swiperInstance.value = swiper
}
const onSlideChange = () => {
  updColors()
}

const swiperNextSlide = () => {
  swiperInstance.value.slideNext()
}
</script>

<style lang="scss" scoped>
.animation {
  /*-webkit-animation: vibrate 0.1s linear infinite both;*/
  /*animation: vibrate 0.1s linear infinite both; */
  animation-name: vibrate;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
  animation-direction: both;
  animation-duration: 8s;
}

@-webkit-keyframes vibrate {
  0% {
    -webkit-transform: translate(0);
    transform: translate(0);
  }

  20% {
    -webkit-transform: translate(-5px, 5px);
    transform: translate(-5px, 5px);
  }

  40% {
    -webkit-transform: translate(-5px, -5px);
    transform: translate(-5px, -5px);
  }

  60% {
    -webkit-transform: translate(5px, 5px);
    transform: translate(5px, 5px);
  }

  80% {
    -webkit-transform: translate(5px, -5px);
    transform: translate(5px, -5px);
  }

  100% {
    -webkit-transform: translate(0);
    transform: translate(0);
  }
}

@keyframes vibrate {
  0% {
    -webkit-transform: translate(0);
    transform: translate(0);
  }

  20% {
    -webkit-transform: translate(-5px, 5px);
    transform: translate(-5px, 5px);
  }

  40% {
    -webkit-transform: translate(-5px, -5px);
    transform: translate(-5px, -5px);
  }

  60% {
    -webkit-transform: translate(5px, 5px);
    transform: translate(5px, 5px);
  }

  80% {
    -webkit-transform: translate(5px, -5px);
    transform: translate(5px, -5px);
  }

  100% {
    -webkit-transform: translate(0);
    transform: translate(0);
  }
}

.swp {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  margin: 0 auto;
  z-index: 9998;
}

.slide {
  .main-area {
    position: relative;
    width: 100%;
    height: 100%;
    padding-top: 3rem;
    display: flex;
    flex-direction: column;
    justify-content: start;
    align-items: center;
    background: var(--back-color);

    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: radial-gradient(ellipse 100% 60% at right bottom,
          var(--start-color),
          var(--end-color));
      z-index: 50;
    }

    .grouping {
      width: 90%;
      display: flex;
      flex-direction: column;
      justify-content: start;
      align-items: start;
      gap: 1rem;
      z-index: 500;

      h1 {
        white-space: pre-wrap;
        color: #fff;
        font-family: 'Inter' !important;
        font-weight: bold;
        font-size: 30px;
      }

      p {
        white-space: pre-wrap;
        color: #fff;
        font-family: 'Inter' !important;
        font-weight: 400;
        font-size: 1rem;
      }
    }

    .item-image {
      position: absolute;
      width: 100%;
      bottom: 12%;
      z-index: 450;
    }

    .tutor-btn {
      position: absolute;
      bottom: 2.5rem;
      width: 70%;
      margin: 0 auto;
      padding: 0.5rem 1rem;
      border-radius: 0.5rem;
      background: radial-gradient(ellipse 80% 20% at bottom, #ffffff70, transparent),
        linear-gradient(to bottom, #e2f974, #009600);
      font-family: 'Inter' !important;
      font-weight: bold;
      font-size: 18px;
      z-index: 500;
    }
  }
}

.swiper-horizontal>.swiper-pagination-bullets .swiper-pagination-bullet,
.swiper-pagination-horizontal.swiper-pagination-bullets .swiper-pagination-bullet {
  width: 30px !important;
  height: 4px !important;
  background: #ccc !important;
  border-radius: 0 !important;
  opacity: 1 !important;
  transition: background-color 0.3s !important;
}

.swiper-pagination-bullet-active {
  background: #000 !important;
}

.swiper-pagination .swiper-pagination-bullets .swiper-pagination-horizontal {
  width: 100% !important;
  position: absolute !important;
  top: 10px !important;
}
</style>
