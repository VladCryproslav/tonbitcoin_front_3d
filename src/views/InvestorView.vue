<script setup>
import CraftScreen from '@/components/investor/CraftScreen.vue'
import RentScreen from '@/components/investor/RentScreen.vue'
import StakingScreen from '@/components/investor/StakingScreen.vue'
import { useAppStore } from '@/stores/app'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const app = useAppStore()
const { t } = useI18n()
const currInvestorScreen = ref(null) // 'staking', 'rent', 'craft'
</script>

<template>
  <div class="screen-box">
    <div class="investor">
      <div v-if="!currInvestorScreen" class="select-pannel">
        <div class="staking-pan" @click="currInvestorScreen = 'staking'">
          <h1>{{ t('investor.staking_tab') }}</h1>
        </div>
        <div class="rent-pan" @click="currInvestorScreen = 'rent'">
          <h1>{{ t('investor.rental_tab') }}</h1>
        </div>
        <!-- @click="currInvestorScreen = 'craft'" -->
        <div class="unk-pan spoiler">
          <div class="spoiler"></div>
          <h1>{{ true ? "UNKNOWN" : t('investor.craft_tab') }}</h1>
        </div>
      </div>
      <StakingScreen v-if="currInvestorScreen == 'staking'" @back="currInvestorScreen = null" />
      <RentScreen v-else-if="currInvestorScreen == 'rent'" @back="currInvestorScreen = null" />
      <CraftScreen v-else-if="currInvestorScreen == 'craft'" @back="currInvestorScreen = null" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100vh);
  opacity: 0;
}

.screen-box {
  position: absolute;
  top: 0;
  width: 100%;
  height: 100vh;
  margin: 0 auto;
  padding: 0 0 300px 0;
  display: flex;
  flex-direction: column;
  justify-content: start;
  align-items: center;
  overflow-y: scroll;
  -ms-overflow-style: none;
  /* Internet Explorer 10+ */
  scrollbar-width: none;
  /* Firefox */

  &::-webkit-scrollbar {
    display: none;
    /* Safari and Chrome */
  }

  .investor {
    width: 90%;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;

    .select-pannel {
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: clamp(10px, 2.2vh, 20px);
      padding: 17px 0 0;

      .staking-pan,
      .rent-pan,
      .unk-pan {
        position: relative;
        width: 100%;
        height: min(17dvh, 140px);
        display: flex;
        justify-content: center;
        align-items: center;
        border: 2px solid #8143FC;
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0px 0px 7px #8143FC;
        transition: all 150ms ease-in-out;

        &::before {
          position: absolute;
          content: '';
          width: 100%;
          height: 100%;
          background: #8143FC33;
          top: 0;
          left: 0;
          z-index: 10;
        }

        &:active {
          opacity: 0.8;
          scale: 0.97;
          box-shadow: none;
        }

        >h1 {
          width: 100%;
          text-align: center;
          color: #fff;
          font-family: 'Inter', sans-serif;
          font-weight: bold;
          font-size: 30px;
          letter-spacing: 0px;
          z-index: 11;
        }
      }

      .staking-pan {
        background:
          linear-gradient(to bottom, #00000055, #00000055),
          url('@/assets/staking_pan.webp') no-repeat center;
        background-size: cover;
      }

      .rent-pan {
        background:
          linear-gradient(to bottom, #00000055, #00000055),
          url('@/assets/rent_pan.webp') no-repeat center;
        background-size: cover;
      }

      .unk-pan {
        background:
          url('@/assets/unk_pan.webp') no-repeat center;
        background-size: cover;

        &.spoiler{
          border-radius: 15px;
          overflow: hidden;
          &::before {
          position: absolute;
          content: '';
          width: 100%;
          height: 100%;
          background: #8143FC33;
          border-radius: 15px;
          top: 0;
          left: 0;
          z-index: 50;
          backdrop-filter: blur(8px);
        }
        }

        .spoiler {
  transition: 200ms;
  z-index: 51;
  width:300px;
  height: 300px;
  background-image: url("@/assets/turbulence.png");
  background-size: 300px;
  position:absolute;
  height: 100%;
  width: 100%;
  border-radius: 15px;
  overflow: hidden;
  background-position-x: 0px;
  background-position-y: 0px;
  animation: down 20s linear infinite ;

  &::before {
  content:'';
  top:0;
  left:0;
  background-image: url("@/assets/turbulence.png");
  position:absolute;
  background-size: 300px;
  height: 100%;
  width: 100%;
  background-position-x: 0px;
  background-position-y: 0px;
  border-radius: 15px;
  animation: up 21s linear infinite;
}
&::after {
  content:'';
  top:0;
  left:0;
  background-image: url("https://web.telegram.org/a/turbulence_1x.29559632f446607390d2.png");
  position:absolute;
  background-size: 300px;
  height: 100%;
  width: 100%;
  background-position-x: 0px;
  background-position-y: 0px;
  border-radius: 15px;
  animation: right 22s linear infinite;
}
}

@keyframes down {
  0% {
    background-position: 0% 0%;
  }
  100% {
    background-position: 0px 300px;
  }
}

@keyframes right {
  0% {
    background-position: 0% 0%;
  }
  100% {
    background-position: 300px 0px;
  }
}

@keyframes up {
  0% {
    background-position: 0% 0%;
  }
  100% {
    background-position: -300px -300px;
  }
}
      }
    }
  }
}
</style>
