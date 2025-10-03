<script setup>
import asicsSheet from '@/services/data';
import { useTelegram } from '@/services/telegram';
import { useAppStore } from '@/stores/app';
const Arrow = defineAsyncComponent(() => import('@/assets/arrow_circle.svg'))
import { computed, defineAsyncComponent, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import CaseModal from './CaseModal.vue';

const app = useAppStore()
const { t } = useI18n()
const { tg } = useTelegram()
const emit = defineEmits(['back'])
const all_asics = computed(() => app.getAsicsFromStorage())
const currSelectFirst = ref(0)
const currSelectSecond = ref(0)
const conditionsToMintFirst = ref(true)
const conditionsToMintSecond = ref(false)

const handleMoveFirst = (bool) => {
  if (bool && currSelectFirst.value >= asicsSheet.filter(el => el.shop).length - 1) {
    currSelectFirst.value = 0
    return
  }
  if (!bool && currSelectFirst.value <= 0) {
    currSelectFirst.value = asicsSheet.filter(el => el.shop).length - 1
    return
  }

  if (bool) {
    currSelectFirst.value++
  } else {
    currSelectFirst.value--
  }
}

const handleMoveSecond = (bool) => {
  if (bool && currSelectSecond.value >= asicsSheet.filter(el => el.shop).length - 1) {
    currSelectSecond.value = 0
    return
  }
  if (!bool && currSelectSecond.value <= 0) {
    currSelectSecond.value = asicsSheet.filter(el => el.shop).length - 1
    return
  }

  if (bool) {
    currSelectSecond.value++
  } else {
    currSelectSecond.value--
  }
}

const imagePathAsics = (asic) => {
  const com = computed(
    () => new URL(`../../assets/asics/${asic?.toString().toUpperCase()}.webp`, import.meta.url).href,
  )
  return com
}

const getRarity = () => {
  const max = Math.max(currSelectFirst.value, currSelectSecond.value);
  if (max > 7) return 'legendary';
  if (max > 4) return 'epic';
  if (max > 1) return 'rare';
  return 'common';
};

const rarityBoxItems = computed(() => {
  const rarityMap = {
    legendary: [
      { name: 'ASIC SX Ultra Pro', percentage: 30 },
      { name: 'ASIC S21 XP+', percentage: 50 },
      { name: 'ASIC S19 XP+', percentage: 15 },
      { name: 'ASIC S17 XP', percentage: 5 },
    ],
    epic: [
      { name: 'ASIC S19 XP+', percentage: 30 },
      { name: 'ASIC S17 XP', percentage: 50 },
      { name: 'ASIC S15 XP', percentage: 15 },
      { name: 'ASIC S11 XP', percentage: 5 },
    ],
    rare: [
      { name: 'ASIC S11 XP', percentage: 30 },
      { name: 'ASIC S9+', percentage: 50 },
      { name: 'ASIC S7+', percentage: 15 },
      { name: 'ASIC S5+', percentage: 5 },
    ],
    common: [
      { name: 'ASIC S7+', percentage: 30 },
      { name: 'ASIC S5+', percentage: 50 },
      { name: 'ASIC S3-', percentage: 15 },
      { name: 'ASIC S1', percentage: 5 },
    ],
  };
  return rarityMap[getRarity()]
})

const imageCase = () => {
  return computed(() => new URL(`../../assets/cases/${getRarity()}.webp`, import.meta.url).href);
};

const showCaseCraft = ref(false)
const craftCase = () => {
  showCaseCraft.value = true
}
</script>

<template>
  <CaseModal v-if="showCaseCraft" :case="getRarity()" @close="showCaseCraft = false"/>
  <div class="craft">
    <div class="mint-cards">
      <div class="card">
        <h1>{{ t('investor.craft.first_nft') }}</h1>
        <div class="content">
          <button v-if="!conditionsToMintFirst" class="buy-asic">
            <img src="@/assets/buy-reveal.webp" :width="41" :height="41" alt="icon" />
          </button>
          <div class="asic-nft">
            <img :src="imagePathAsics(asicsSheet[currSelectFirst].name).value" alt="station" />
          </div>
          <div class="conditions">
            <Arrow class="control-arr" @click="handleMoveFirst(false)" />
            <div class="asic-info">
              <h1>{{ asicsSheet[currSelectFirst].name }}</h1>
              <div class="status">
                <img v-if="conditionsToMintFirst" src="@/assets/green-pin.png" :width="12" />
                <img v-if="!conditionsToMintFirst" src="@/assets/red-pin.png" :width="12" />
                <span v-if="conditionsToMintFirst">{{ t('investor.craft.nft_detected') }}</span>
                <span v-if="!conditionsToMintFirst">{{ t('investor.craft.nft_undetected') }}</span>
              </div>
            </div>
            <Arrow class="control-arr next" @click="handleMoveFirst(true)" />
          </div>
        </div>
      </div>
      <img src="@/assets/plus.png" :width="20" alt="plus" />
      <div class="card">
        <h1>{{ t('investor.craft.second_nft') }}</h1>
        <div class="content">
          <div class="asic-nft">
            <button v-if="!conditionsToMintSecond" class="buy-asic">
              <img src="@/assets/buy-reveal.webp" :width="38" :height="38" alt="icon" />
            </button>
            <img :src="imagePathAsics(asicsSheet[currSelectSecond].name).value" :class="{ disabled: true }"
              alt="station" />
          </div>
          <div class="conditions">
            <Arrow class="control-arr" @click="handleMoveSecond(false)" />
            <div class="asic-info">
              <h1>{{ asicsSheet[currSelectSecond].name }}</h1>
              <div class="status">
                <img v-if="conditionsToMintSecond" src="@/assets/green-pin.png" :width="12" />
                <img v-if="!conditionsToMintSecond" src="@/assets/red-pin.png" :width="12" />
                <span v-if="conditionsToMintSecond">{{ t('investor.craft.nft_detected') }}</span>
                <span v-if="!conditionsToMintSecond">{{ t('investor.craft.nft_undetected') }}</span>
              </div>
            </div>
            <Arrow class="control-arr next" @click="handleMoveSecond(true)" />
          </div>
        </div>
      </div>
    </div>
    <div class="asic-box">
      <div class="asic-img" :class="getRarity()">
        <img :src="imageCase().value" />
      </div>
      <div class="box-info">
        <h1 class="title">{{ t(`asic_shop.${getRarity()}`) }} ASICs BOX </h1>
        <div class="details">
          <span>{{ t('investor.craft.box_text') }}</span>
          <ul v-if="rarityBoxItems.length">
            <li v-for="item in rarityBoxItems" :key="item.name">{{ item.name }} - {{ item.percentage }}%</li>
          </ul>
        </div>
      </div>
    </div>
    <button class="btn" @click="craftCase">
      {{ t('common.craft') }}
      {{ 2500 }}
      <img src="@/assets/fBTC.webp" :width="18" :height="18" alt="" />
    </button>
    <button class="back-btn" @click="emit('back')">
      {{ t('investor.back') }}
    </button>
  </div>
</template>

<style lang="scss" scoped>
.craft {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;

  .asic-box {
    width: 100%;
    height: min(18dvh, 160px);
    display: flex;
    justify-content: center;
    align-items: center;
    border: 2px solid #8143FC;
    border-radius: 20px;
    gap: 6px;
    overflow: hidden;
    background: #080C15CC;
    box-shadow: 0px 0px 7px #8143FC;

    .asic-img {
      position: relative;
      width: min(40vw, 40%);
      height: 100%;
      display: flex;
      justify-content: center;
      align-items: center;

      img {
        position: relative;
        z-index: 50;
      }

      $rarity-colors: (
        "legendary": #FCA643,
        "epic": #437EFC,
        "rare": #43FC5F,
        "common": #FFFFFF
      );

    @each $rarity, $color in $rarity-colors {
      &.#{$rarity} {
        &::before {
          position: absolute;
          content: "";
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          z-index: 1;
          background: radial-gradient(ellipse 50% 45% at center, $color, transparent);
        }
      }
    }

  }

  .box-info {
    display: flex;
    flex-direction: column;
    min-width: 55%;
    gap: 6px;

    .title {
      color: #fff;
      width: 100%;
      text-align: center;
      font-size: 14px;
      font-family: 'Inter', sans-serif;
      font-weight: 500;
      letter-spacing: 0px;
    }

    .details {
      display: flex;
      flex-direction: column;
      width: 100%;
      color: #ffffff80;
      font-size: 11px;
      font-family: 'Inter', sans-serif;
      font-weight: 400;
      letter-spacing: 0px;

      ul {
        list-style: disc;
        list-style-position: inside;

        li {
          margin-left: 5px;
        }
      }
    }
  }
}

.mint-cards {
  display: flex;
  width: 100%;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  padding: .5rem 0 0;
  z-index: 1;

  .card {
    position: relative;
    display: flex;
    flex-direction: column;
    width: 100%;
    padding: 1px;
    background: linear-gradient(to bottom, #8143FC, #8143FC);
    border-radius: 20px;

    h1 {
      color: #fff;
      text-align: center;
      font-family: 'Inter';
      font-weight: 600;
      font-size: 13px;
      letter-spacing: 0px;
      padding: 0.2rem 0;
      z-index: 1;
    }

    .content {
      position: relative;
      width: 100%;
      height: 100%;
      border-radius: 20px;
      background: #080c15;
      overflow: hidden;

      &::before {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: url('@/assets/tapzone_bg.svg') no-repeat center/cover;
        opacity: 0.2;
        z-index: 0;
      }

      h1 {
        color: #fff;
        text-align: center;
        text-transform: capitalize;
        font-family: 'Inter';
        font-weight: 500;
        font-size: 14px;
        letter-spacing: 0px;
        z-index: 1;
      }

      .asic-nft {
        position: relative;
        display: flex;
        width: 70%;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        margin: 0 auto;
        padding: 1rem 0 3.5rem;

        .buy-asic {
          position: absolute;
          left: 50%;
          top: 50%;
          margin: 0 auto;
          border: none;
          padding: 2rem 0;
          z-index: 1;
          transform: translate(-50%, -70%);
        }

        .disabled {
          filter: grayscale(1) brightness(0.5);
        }
      }

      .conditions {
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #080C15;
        padding: 5px 8px 9px;

        .control-arr {
          // width: min(20%, 60px);
          // min-width: 20%;
          transition: all 150ms ease-in-out;

          &.next {
            rotate: 180deg;
          }

          &:active {
            opacity: 0.5;
            scale: 0.95;
          }
        }

        .asic-info {
          display: flex;
          width: 50%;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          margin: 0 auto;

          >h1 {
            font-family: 'Inter';
            font-weight: 500;
            font-size: 12px;
            letter-spacing: 0%;
            color: #fff;
            overflow: hidden;
            max-width: 90%;
            text-wrap: nowrap;
            text-overflow: ellipsis;
          }

          .status {
            display: flex;
            width: 100%;
            align-items: center;
            justify-content: center;
            gap: 0.3rem;

            >span {
              font-family: 'Inter';
              font-weight: 400;
              font-size: 9px;
              letter-spacing: 0%;
              color: #fff;
              opacity: 0.5;
              text-wrap: nowrap;
            }
          }
        }
      }
    }
  }
}
}

.btn {
  width: 100%;
  height: 48px;
  padding: 10px 0;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  border: 1px solid #8143fc;
  background: #8143fc;
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

.back-btn {
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
</style>