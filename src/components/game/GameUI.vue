<template>
  <div class="game-ui">
    <div class="ui-top">
      <div class="energy-counter">
        <span class="label">{{ t('game.energy') }}:</span>
        <span class="value energy-value">{{ formatEnergy(energy) }} kW</span>
      </div>
      <div class="distance-counter">
        <span class="label">{{ t('game.distance') }}:</span>
        <span class="value distance-value">{{ formatDistance(distance) }}m</span>
      </div>
    </div>
    
    <div class="ui-bottom">
      <div class="power-bar-container">
        <div class="power-label">{{ t('game.power') }}</div>
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
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  energy: { type: Number, default: 0 },
  distance: { type: Number, default: 0 },
  power: { type: Number, default: 100 }
})

const formatEnergy = (value) => {
  const v = Number(value ?? 0)
  return v.toFixed(1)
}

const formatDistance = (value) => {
  const v = Number(value ?? 0)
  if (v >= 1000) {
    return (v / 1000).toFixed(2) + 'k'
  }
  return Math.round(v)
}
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
  align-items: flex-start;
}

.energy-counter,
.distance-counter {
  background: rgba(0, 0, 0, 0.7);
  padding: 10px 16px;
  border-radius: 12px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  
  .label {
    color: rgba(255, 255, 255, 0.7);
    font-size: 12px;
    margin-right: 8px;
  }
  
  .value {
    color: #fff;
    font-size: 18px;
    font-weight: 700;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
  }
}

.energy-value {
  color: #00FF88;
  animation: pulse-glow 2s ease-in-out infinite;
}

.distance-value {
  color: #8143FC;
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
</style>
