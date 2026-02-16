<template>
  <div class="game-ui">
    <div class="ui-top">
      <div class="top-left" :class="{ 'top-left--compact': compactDistance }">
        <div class="energy-counter" :class="{ 'energy-counter--with-distance': compactDistance }">
          <div class="energy-counter-row">
            <img
              class="icon energy-icon"
              src="@/assets/kW.png"
              alt="energy"
            />
            <span class="value energy-value">
              {{ formatEnergy(Math.min(energy, maxEnergy)) }} / {{ formatEnergy(maxEnergy) }} kW
            </span>
          </div>
          <div v-if="compactDistance" class="energy-counter-distance">
            <div class="distance-bar">
              <div
                v-if="overheatCountdown === null"
                class="distance-fill"
                :style="{ width: `${Math.max(0, Math.min(100, Number.isFinite(power) ? power : 0))}%` }"
              ></div>
              <div
                v-else
                class="distance-fill distance-fill--overheat"
                :style="{ width: '100%' }"
              ></div>
            </div>
            <span class="distance-value" v-if="overheatCountdown === null">{{ Number.isFinite(power) ? Math.round(power) : 0 }}%</span>
            <span class="distance-value distance-value--overheat" v-else>{{ overheatCountdown }}</span>
          </div>
        </div>
        <div class="lives-counter" :class="{ 'lives-counter--compact': compactDistance }">
          <img
            class="icon energy-icon lives-icon"
            src="@/assets/engineer.webp"
            alt="lives"
          />
          <div class="lives-hearts">
            <span
              v-for="n in maxLives"
              :key="n"
              class="life-heart"
              :class="{
                'life-heart--lost': n > lives,
                'life-heart--critical': isLastLife && n === lives
              }"
            >
              ♥
            </span>
          </div>
        </div>
        <div v-if="isCryoActive" class="cryochamber-counter">
          <img
            class="icon cryochamber-icon"
            src="@/assets/cryochamber_icon.webp"
            alt="cryochamber"
            @error="handleCryoIconError"
          />
        </div>
      </div>
      <div class="top-right">
        <button
          class="pause-button"
          @click.stop="$emit('pause')"
        >
          ❚❚
        </button>
      </div>
    </div>

    <div v-if="!compactDistance" class="ui-bottom">
      <div class="power-bar-container">
        <div class="power-label" v-if="overheatCountdown === null">Дистанция</div>
        <div class="power-label" v-else>{{ t('game.overheat_countdown_label') }}</div>
        <div class="power-bar">
          <div
            v-if="overheatCountdown === null"
            class="power-fill power-fill--distance"
            :style="{ width: `${Math.max(0, Math.min(100, Number.isFinite(power) ? power : 0))}%` }"
          ></div>
          <div
            v-else
            class="power-fill power-fill--overheat"
            :style="{ width: '100%' }"
          ></div>
        </div>
        <div class="power-value" v-if="overheatCountdown === null">{{ Number.isFinite(power) ? Math.round(power) : 0 }}%</div>
        <div class="power-value power-value--overheat" v-else>{{ overheatCountdown }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { energy, maxEnergy, power, lives, maxLives, compactDistance, overheatCountdown, isCryoActive } = defineProps({
  energy: { type: Number, default: 0 },
  maxEnergy: { type: Number, default: 0 },
  power: { type: Number, default: 100 },
  lives: { type: Number, default: 3 },
  maxLives: { type: Number, default: 3 },
  compactDistance: { type: Boolean, default: false },
  overheatCountdown: { type: Number, default: null },
  isCryoActive: { type: Boolean, default: false }
})

const { t } = useI18n()
const isLastLife = computed(() => lives === 1)

defineEmits(['pause'])

const formatEnergy = (value) => {
  const v = Number(value ?? 0)
  return Number.isFinite(v) ? v.toFixed(1) : '0.0'
}

const handleCryoIconError = (event) => {
  // Пробуем альтернативные форматы для иконки криокамеры
  const img = event.target
  if (img.src.includes('.webp')) {
    img.src = img.src.replace('.webp', '.png')
  } else if (img.src.includes('.png')) {
    img.src = img.src.replace('.png', '.svg')
  }
}

// formatDistance оставлен на будущее, когда блок дистанции переедет вниз
// и будет связан с логикой.
</script>

<style lang="scss" scoped>
.game-ui {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 100;
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.ui-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.top-left {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;

  &.top-left--compact {
    align-items: stretch;
  }
}

.top-right {
  display: flex;
  align-items: center;
}

.energy-counter-row {
  display: inline-flex;
  align-items: center;
}

.energy-counter,
.lives-counter {
  background: rgba(0, 0, 0, 0.7);
  padding: 6px 10px;
  border-radius: 12px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  min-width: 100px;
  display: inline-flex;
  align-items: center;

  .label {
    color: rgba(255, 255, 255, 0.7);
    font-size: 12px;
    margin-right: 8px;
  }

  .value {
    color: #fff;
    font-size: 16px;
    font-weight: 700;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
  }

  &.energy-counter--with-distance {
    flex-direction: column;
    align-items: stretch;
    min-width: 120px;

    .energy-counter-row {
      margin-bottom: 6px;
    }
  }
}

.lives-counter--compact {
  padding: 8px 12px;
  align-self: stretch;
  display: inline-flex;
  align-items: center;

  .lives-icon {
    width: 22px;
    height: 22px;
    margin-right: 8px;
  }

  .life-heart {
    font-size: 20px;
  }
}

.cryochamber-counter {
  background: rgba(0, 0, 0, 0.7);
  padding: 6px 10px;
  border-radius: 12px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 255, 136, 0.5);
  box-shadow: 0 4px 12px rgba(0, 255, 136, 0.3);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  min-height: 44px;

  .cryochamber-icon {
    width: 24px;
    height: 24px;
    filter: drop-shadow(0 0 4px rgba(0, 255, 136, 0.8));
  }
}

.energy-counter-distance {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;

  .distance-bar {
    flex: 1;
    height: 5px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
    overflow: hidden;
  }

  .distance-fill {
    height: 100%;
    background: linear-gradient(90deg, #00ff00, #ffff00);
    transition: width 0.3s ease;
    border-radius: 3px;
  }

  .distance-value {
    color: #fff;
    font-size: 11px;
    font-weight: 600;
    min-width: 28px;
    text-align: right;
  }
}

.ui-bottom {
  display: flex;
  justify-content: center;
}

.power-bar-container {
  background: rgba(0, 0, 0, 0.7);
  padding: 12px 24px;
  border-radius: 12px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  min-width: 320px;
  width: 320px;
}

.power-label {
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
  margin-bottom: 6px;
  text-align: center;
}

.power-bar {
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 6px;
}

.power-fill {
  height: 100%;
  transition: width 0.3s ease;
  border-radius: 4px;

  &--distance {
    background: linear-gradient(90deg, #00ff00, #ffff00);
  }
}

.power-value {
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  text-align: center;
  
  &--overheat {
    color: #ff3b59;
    font-size: 24px;
    font-weight: 700;
    animation: overheat-countdown-pulse 0.5s ease-in-out infinite;
  }
}

.power-fill--overheat {
  background: linear-gradient(90deg, #ff3b59, #ff6b7a);
  animation: overheat-bar-pulse 0.5s ease-in-out infinite;
}

.distance-fill--overheat {
  background: linear-gradient(90deg, #ff3b59, #ff6b7a);
  animation: overheat-bar-pulse 0.5s ease-in-out infinite;
}

.distance-value--overheat {
  color: #ff3b59;
  font-size: 14px;
  font-weight: 700;
  animation: overheat-countdown-pulse 0.5s ease-in-out infinite;
}

@keyframes overheat-countdown-pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.9;
  }
}

@keyframes overheat-bar-pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.distance-bar {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.distance-fill {
  height: 100%;
  background: linear-gradient(90deg, #00ff00, #ffff00);
  transition: width 0.3s ease;
  border-radius: 3px;
}

.distance-value {
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  min-width: 32px;
  text-align: right;
}

.icon {
  width: 18px;
  height: 18px;
  margin-right: 6px;
  flex-shrink: 0;
}

.energy-value {
  color: #00FF88;
}

.pause-button {
  pointer-events: auto;
  width: 52px;
  height: 52px;
  border-radius: 999px;
  border: none;
  background: radial-gradient(circle at 30% 0%, #38bdf8, #4c1d95);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  cursor: pointer;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(12px);
  transition: transform 0.15s ease, opacity 0.15s ease, background 0.15s ease;

  &:active {
    transform: scale(0.9);
    opacity: 0.85;
  }
}


.lives-hearts {
  display: inline-flex;
  gap: 4px;
}

.life-heart {
  font-size: 16px;
  color: #f97373;
  text-shadow: 0 0 6px rgba(248, 113, 113, 0.8);
  transition:
    transform 0.2s ease,
    opacity 0.2s ease,
    filter 0.2s ease;
}

.life-heart--lost {
  opacity: 0.25;
  filter: grayscale(1);
  transform: scale(0.7) translateY(2px);
  text-shadow: none;
}

.life-heart--critical {
  animation: life-critical-pulse 0.7s ease-in-out infinite;
}


@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

@keyframes life-critical-pulse {
  0% {
    transform: scale(1) translateY(0);
    text-shadow: 0 0 6px rgba(248, 113, 113, 0.8);
  }
  50% {
    transform: scale(1.3) translateY(-1px);
    text-shadow: 0 0 16px rgba(248, 113, 113, 1);
  }
  100% {
    transform: scale(1) translateY(0);
    text-shadow: 0 0 6px rgba(248, 113, 113, 0.8);
  }
}
</style>
