<script setup>
import i18n from '@/utils/i18n';
import { useTonConnectUI } from '@townsquarelabs/ui-vue';
import { ref, watch } from 'vue';

const { tonConnectUI, setOptions } = useTonConnectUI()

const curr_locale = ref(localStorage.getItem('locale'))

const changeLang = () => {
  if (curr_locale.value == 'ru') {
    curr_locale.value = 'uk'
    setOptions({ language: 'en' })
  } else if (curr_locale.value == 'uk') {
    curr_locale.value = 'en'
    setOptions({ language: 'en' })
  } else {
    curr_locale.value = 'ru'
    setOptions({ language: 'ru' })
  }
}

watch(curr_locale, () => {
  i18n.global.locale.value = curr_locale.value
  localStorage.setItem('locale', curr_locale.value)
})

</script>

<template>
  <div class="lang-switch" :class="curr_locale" @click="changeLang">
    {{ curr_locale.toUpperCase() == 'UK' ? 'UA' : curr_locale.toUpperCase() }}
  </div>
</template>

<style lang="scss" scoped>
.lang-switch {
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 100%;
  font-family: 'Inter', sans-serif !important;
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  text-align: center;
  line-height: 0;
  width: 40px;
  height: 40px;
  min-width: 40px;
  z-index: 0;

  &.en {
    position: relative;

    &::before {
      position: absolute;
      content: '';
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      z-index: -1;
      border-radius: 100%;
      border: solid 3px transparent;
      background:
        linear-gradient(to bottom, #000000BB, #000000BB) padding-box,
        url("@/assets/en.webp") border-box;
      background-repeat: no-repeat;
      background-position: center;
      background-size: cover;
      opacity: .80;
    }
  }

  &.uk {
    position: relative;

    &::before {
      position: absolute;
      content: '';
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      z-index: -1;
      border-radius: 100%;
      border: solid 3px transparent;
      background:
        linear-gradient(to bottom, #000000BB, #000000BB) padding-box,
        url("@/assets/uk.webp") border-box;
      background-repeat: no-repeat;
      background-position: center;
      background-size: cover;
      opacity: .80;
    }
  }

  &.ru {
    position: relative;

    &::before {
      position: absolute;
      content: '';
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      z-index: -1;
      border-radius: 100%;
      border: solid 3px transparent;
      background:
        linear-gradient(to bottom, #000000BB, #000000BB) padding-box,
        url("@/assets/ru.webp") border-box;
      background-repeat: no-repeat;
      background-position: center;
      background-size: cover;
      opacity: .80;
    }
  }
}
</style>
