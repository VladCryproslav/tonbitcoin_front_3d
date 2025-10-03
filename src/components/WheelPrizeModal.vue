<script setup>
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'


const { t, locale } = useI18n()

const Asic = (name) => {
  const res = computed(() => {
    return new URL(`../assets/asics/${String(name).toUpperCase()}.webp`, import.meta.url).href
  })
  return res
}

const emit = defineEmits(['close'])

const imagePath = (path) => {
  const com = computed(
    () => new URL(`../assets/slots/${path}.webp`, import.meta.url).href,
  )
  return com
}

const props = defineProps({
  prize: Object,
})

onMounted(() => {
  // console.log("WheelPrizeModal:", props.prize)
})
</script>

<template>
  <div class="wheel-prize-mask" @click="emit('close')">
    <div class="wheel-prize-item" :class="{
      asic: props.prize?.asset_name == 'ASIC',
      yellow_bg: ['asic_manager', 'magnit'].includes(props.prize?.asset_name) && props.prize?.asset_quantity == 3,
      yellow_border: props.prize?.asset_quantity == 3,
      violet_bg: props.prize?.asset_name == 'jarvis' && props.prize?.asset_quantity >= 5,
      violet_border: props.prize?.asset_quantity >= 5,
    }">
      <div class="wheel-prize-item-data">
        <div class="reward-data">
          <span>{{ t('wheel.your_win') }}</span>
          <img v-if="props.prize?.asset_name == 'kW'" src="@/assets/wheel_kw.png" width="160px" height="160px" />
          <img v-else-if="props.prize?.asset_name == 'Stars'" src="@/assets/wheel_stars.png" width="160px"
            height="160px" />
          <img v-else-if="props.prize?.asset_name == 'ASIC'" :src="Asic(props.prize?.n_parameter).value" width="160px"
            height="160px" />
          <img v-else-if="props.prize?.asset_name == 'tBTC'" src="@/assets/slots/fBTC.webp" width="160px"
            height="160px" />
          <img v-else
            :src="imagePath(`${props.prize?.asset_name}${['magnit', 'asic_manager', 'jarvis'].includes(props.prize?.asset_name) ? props.prize?.asset_quantity : ''}`).value"
            width="160px" height="160px" />
          <span>{{ props.prize?.asset_name !== 'ASIC' ? t(`boost.${props.prize?.asset_name}`) : '' }} {{ ['magnit', 'asic_manager',
            'jarvis'].includes(props.prize?.asset_name) ? locale == 'en' ? 'for' : 'на' : '' }} {{
              ['azot', 'powerbank', 'autostart'].includes(props.prize?.asset_name) ?
                String(t('common.pcs', { n: props.prize?.asset_quantity }).slice(0, -1)) :
                props.prize?.asset_name == 'electrics' ?
                  String(t('common.pers', { n: props.prize?.asset_quantity })) :
                  props.prize?.asset_name == 'ASIC' ?
                    String(props.prize?.n_parameter) :
                    String(t('common.days', { n: props.prize?.asset_quantity })) }} </span>
        </div>
      </div>
      <div class="wheel-prize-item-notif">
        {{ t('wheel.modal_bottom') }}
      </div>
    </div>
    <div class="get-btn" @click="emit('close')">{{ t('wheel.modal_btn') }}</div>
  </div>
</template>

<style lang="scss" scoped>
.wheel-prize-mask {
  position: absolute;
  width: 100%;
  height: 100%;
  z-index: 99999;
  padding-top: 50px;
  backdrop-filter: blur(10px);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;

  .get-btn {
    margin-top: 50px;
    font-family: 'Inter';
    font-weight: 600;
    font-size: 28px;
    overflow: hidden;
    background: linear-gradient(90deg, transparent, #fff, transparent);
    background-repeat: no-repeat;
    background-size: 80%;
    animation: animate 3s linear infinite;
    -webkit-background-clip: text;
    -webkit-text-fill-color: rgba(255, 255, 255, 0);
  }

  @keyframes animate {
    0% {
      background-position: -500%;
    }

    100% {
      background-position: 500%;
    }
  }
}

.wheel-prize-item {
  width: 90%;
  height: auto;
  background: #08150a99;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 1rem;
  border: 1px solid #ffffff25;
  overflow: hidden;

  &.asic {
    position: relative;
    background:
      linear-gradient(to left top, #077B41, #135F27CC);
    border: 1px solid #0ea65a;
    box-shadow: 0 0 35px 5px #2ce38499;

    &::before {
      position: absolute;
      content: '';
      width: 150%;
      height: 100%;
      background: radial-gradient(ellipse 60% 50% at 50% 50%, #31FF7D99, transparent);
      transform: rotate(-45deg);
    }
  }

  &.yellow_bg {
    background: linear-gradient(to left top, #A36D00, #EECA0099);
    border: 1px solid #fea400;
    box-shadow: 0 0 35px 5px #fcd90999;
  }

  &.yellow_border {
    border: 1px solid #fea400;
    box-shadow: 0 0 35px 5px #fcd90999;
  }

  &.violet_bg {
    background: linear-gradient(to left, #DD1E1E, #D340FFCC);
    border: 1px solid #d340ff;
    box-shadow: 0 0 35px 5px #d945e899;
  }

  &.violet_border {
    border: 1px solid #d340ff;
    box-shadow: 0 0 35px 5px #d945e899;
  }

  &-data {
    width: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: center;
    padding: 10px 15px;
    gap: 10px;
    z-index: 1;

    .reward-data {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;

      span {
        color: #fff;
        font-family: 'Inter';
        font-weight: bold;
        font-size: 32px;
        text-align: center;
        letter-spacing: 0%;
      }
    }

    .reward-btn {
      color: #212121;
      padding: 12px 20px;
      background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
        linear-gradient(to bottom, #e2f974, #009600);
      border-radius: 12px;
      font-family: 'Inter';
      font-weight: bold;
      font-size: 12px;
      letter-spacing: 0px;
      text-align: center;

      &:active {
        background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
          linear-gradient(to bottom, #e2f97490, #00960090);
      }

      &.asic {
        background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
          linear-gradient(to bottom, #74f98a, #0ea65a);

        &:active {
          background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
            linear-gradient(to bottom, #74f98a90, #0ea65a90);
        }
      }

      &.tbtc {
        background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);

        &:active {
          background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
            linear-gradient(to bottom, #fcd90990, #fea40090);
        }
      }

      &.stars {
        background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
          linear-gradient(to right, #d340ff, #ff7047);

        &:active {
          background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
            linear-gradient(to bottom, #d340ff90, #ff704790);
        }
      }

      &.disabled {
        background: linear-gradient(to bottom, #e2e2e2, #646464);
      }
    }
  }

  &-notif {
    width: 100%;
    color: #fff;
    text-align: left;
    display: flex;
    justify-content: center;
    align-items: center;
    font-family: 'Inter';
    font-weight: 400;
    font-size: 11px;
    letter-spacing: 0%;
    background: #00000050;
    padding: 10px 15px;
  }
}
</style>
