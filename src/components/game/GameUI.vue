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
              {{ formatEnergy(energy) }} / {{ formatEnergy(maxEnergy) }} kW
            </span>
          </div>
          <div v-if="compactDistance" class="energy-counter-distance">
            <div class="distance-bar">
              <div
                class="distance-fill"
                :style="{ width: `${Math.max(0, Math.min(100, Number.isFinite(power) ? power : 0))}%` }"
              ></div>
            </div>
            <span class="distance-value">{{ Number.isFinite(power) ? Math.round(power) : 0 }}%</span>
          </div>
        </div>
        <div v-if="!compactDistance" class="distance-status">
          <div class="distance-label">Дистанция</div>
          <div class="distance-bar-wrapper">
            <div class="distance-bar">
              <div
                class="distance-fill"
                :style="{ width: `${Math.max(0, Math.min(100, Number.isFinite(power) ? power : 0))}%` }"
              ></div>
            </div>
            <div class="distance-value">{{ Number.isFinite(power) ? Math.round(power) : 0 }}%</div>
          </div>
        </div>
        <div class="lives-counter">
          <img
            class="icon energy-icon"
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

  </div>
</template>

<script setup>
import { computed } from 'vue'

const { energy, maxEnergy, power, lives, maxLives, compactDistance } = defineProps({
  energy: { type: Number, default: 0 },
  maxEnergy: { type: Number, default: 0 },
  power: { type: Number, default: 100 },
  lives: { type: Number, default: 3 },
  maxLives: { type: Number, default: 3 },
  compactDistance: { type: Boolean, default: false }
})

const isLastLife = computed(() => lives === 1)

defineEmits(['pause'])

const formatEnergy = (value) => {
  const v = Number(value ?? 0)
  return Number.isFinite(v) ? v.toFixed(1) : '0.0'
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
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;

  &.top-left--compact {
    flex-direction: row;
    align-items: center;
    gap: 10px;
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

.distance-status {
  background: rgba(0, 0, 0, 0.7);
  padding: 8px 12px;
  border-radius: 12px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  min-width: 140px;
}

.distance-label {
  color: rgba(255, 255, 255, 0.7);
  font-size: 11px;
  margin-bottom: 4px;
  text-align: left;
}

.distance-bar-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
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
