<template>
  <div class="run-complete-modal" v-if="visible" @click.self="handleClose">
    <div class="modal-content">
      <div class="modal-header">
        <h2>{{ t('game.run_complete') }}</h2>
      </div>
      
      <div class="modal-body">
        <div class="stat-row">
          <span class="stat-label">{{ t('game.distance') }}:</span>
          <span class="stat-value">{{ formatDistance(results.distance) }}m</span>
        </div>
        
        <div class="stat-row">
          <span class="stat-label">{{ t('game.energy_collected') }}:</span>
          <span class="stat-value energy">{{ formatEnergy(results.energyCollected) }} kW</span>
        </div>
        
        <div class="stat-row" v-if="results.energyGained">
          <span class="stat-label">{{ t('game.energy_gained') }}:</span>
          <span class="stat-value energy-gained">+{{ formatEnergy(results.energyGained) }} kW</span>
        </div>
        
        <div class="stat-row" v-if="results.bonuses">
          <div class="bonuses">
            <div class="bonus-item" v-if="results.bonuses.distance_bonus">
              <span>{{ t('game.distance_bonus') }}:</span>
              <span>+{{ formatEnergy(results.bonuses.distance_bonus) }} kW</span>
            </div>
            <div class="bonus-item" v-if="results.bonuses.collection_bonus">
              <span>{{ t('game.collection_bonus') }}:</span>
              <span>+{{ formatEnergy(results.bonuses.collection_bonus) }} kW</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="modal-footer">
        <button class="btn-primary" @click="handleClose">
          {{ t('game.close') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  visible: { type: Boolean, default: false },
  results: {
    type: Object,
    default: () => ({
      distance: 0,
      energyCollected: 0,
      energyGained: 0,
      bonuses: null
    })
  }
})

const emit = defineEmits(['close'])

const handleClose = () => {
  emit('close')
}

const formatEnergy = (value) => {
  return value.toFixed(1)
}

const formatDistance = (value) => {
  if (value >= 1000) {
    return (value / 1000).toFixed(2) + 'k'
  }
  return Math.round(value)
}
</script>

<style lang="scss" scoped>
.run-complete-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(10px);
}

.modal-content {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border: 2px solid #8143FC;
  border-radius: 20px;
  padding: 24px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 10px 40px rgba(129, 67, 252, 0.3);
}

.modal-header {
  text-align: center;
  margin-bottom: 20px;
  
  h2 {
    color: #fff;
    font-size: 24px;
    font-weight: 700;
    margin: 0;
  }
}

.modal-body {
  margin-bottom: 24px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  
  &:last-child {
    border-bottom: none;
  }
}

.stat-label {
  color: rgba(255, 255, 255, 0.7);
  font-size: 16px;
}

.stat-value {
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  
  &.energy {
    color: #00ff88;
  }
  
  &.energy-gained {
    color: #8143FC;
    font-size: 20px;
  }
}

.bonuses {
  width: 100%;
  
  .bonus-item {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.8);
  }
}

.modal-footer {
  display: flex;
  justify-content: center;
}

.btn-primary {
  background: #8143FC;
  color: #fff;
  border: none;
  padding: 12px 32px;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  
  &:active {
    transform: scale(0.95);
    opacity: 0.8;
  }
}
</style>
