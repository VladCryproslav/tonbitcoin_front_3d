<template>
  <div class="game-ui">
    <div
      v-if="isLastLife"
      class="low-life-vignette"
    ></div>
    <div class="ui-top">
      <div class="top-left">
        <div class="energy-counter">
          <img
            class="icon energy-icon"
            src="@/assets/kW.png"
            alt="energy"
          />
          <span class="value energy-value">{{ formatEnergy(energy) }} kW</span>
        </div>
        <div class="lives-counter">
          <svg
            class="icon lives-icon"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              d="M12.1 21.35 10 19.45C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8 10.95l-1.9 1.9Z"
              fill="currentColor"
            />
          </svg>
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

    <div class="ui-bottom">
      <div class="power-bar-container">
        <div class="power-label">Дистанция</div>
        <div class="power-bar">
          <div
            class="power-fill"
            :style="{ width: `${Math.max(0, Math.min(100, power))}%` }"
            :class="{ 'low-power': power < 30, 'critical-power': power < 10 }"
          ></div>
        </div>
        <div class="power-value">{{ Math.round(power) }}%</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const { energy, power, lives, maxLives } = defineProps({
  energy: { type: Number, default: 0 },
  power: { type: Number, default: 100 },
  lives: { type: Number, default: 3 },
  maxLives: { type: Number, default: 3 }
})

const isLastLife = computed(() => lives === 1)

defineEmits(['pause'])

const formatEnergy = (value) => {
  const v = Number(value ?? 0)
  return v.toFixed(1)
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
  align-items: center;
  gap: 10px;
}

.top-right {
  display: flex;
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
  max-width: 140px;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;

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
}

.icon {
  width: 18px;
  height: 18px;
  margin-right: 6px;
  flex-shrink: 0;
}

.energy-value {
  color: #00FF88;
  animation: pulse-glow 2s ease-in-out infinite;
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

@keyframes pulse-glow {
  0%, 100% {
    text-shadow: 0 0 5px rgba(0, 255, 136, 0.5);
  }
  50% {
    text-shadow: 0 0 15px rgba(0, 255, 136, 0.8);
  }
}

.ui-bottom {
  display: flex;
  justify-content: center;
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

.low-life-vignette {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at top left, rgba(248, 113, 113, 0.7), transparent 55%),
    radial-gradient(circle at top right, rgba(248, 113, 113, 0.7), transparent 55%),
    radial-gradient(circle at bottom left, rgba(248, 113, 113, 0.7), transparent 55%),
    radial-gradient(circle at bottom right, rgba(248, 113, 113, 0.7), transparent 55%);
  mix-blend-mode: screen;
  opacity: 0.75;
  animation: vignette-pulse 1s ease-in-out infinite;
  z-index: -1;
}

.power-bar-container {
  background: rgba(0, 0, 0, 0.7);
  padding: 12px 20px;
  border-radius: 12px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  min-width: 200px;
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
  background: linear-gradient(90deg, #00ff00, #ffff00);
  transition: width 0.3s ease;
  border-radius: 4px;

  &.low-power {
    background: linear-gradient(90deg, #ffff00, #ff8800);
  }

  &.critical-power {
    background: linear-gradient(90deg, #ff8800, #ff0000);
    animation: pulse 1s ease-in-out infinite;
  }
}

.power-value {
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  text-align: center;
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

@keyframes vignette-pulse {
  0%, 100% {
    opacity: 0.5;
  }
  50% {
    opacity: 0.9;
  }
}
</style>
