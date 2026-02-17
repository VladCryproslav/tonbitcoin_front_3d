<template>
  <div class="warning-modal-mask" @click.self="handleBackdropClick">
    <div class="warning-modal-wrapper">
      <div class="warning-modal-container">
        <div class="warning-modal-header">
          <img src="@/assets/warning.png" class="warning-icon" alt="Warning" />
          <h1 class="warning-title">{{ t('game.start_run_warning_title') }}</h1>
          <img src="@/assets/warning.png" class="warning-icon" alt="Warning" />
        </div>
        <div class="warning-modal-body">
          <div class="warning-message" v-html="t('game.start_run_warning_message')"></div>
          <div class="warning-checkbox">
            <label class="checkbox-label">
              <input
                type="checkbox"
                v-model="dontShowAgain"
                class="checkbox-input"
              />
              <span class="checkbox-text">{{ t('game.start_run_warning_dont_show') }}</span>
            </label>
          </div>
        </div>
        <div class="warning-modal-actions">
          <button
            class="btn-primary btn-primary--wide"
            @click.stop.prevent="handleConfirm"
          >
            {{ t('game.start_run_warning_confirm') }}
          </button>
          <button
            class="btn-primary btn-secondary btn-primary--wide"
            @click.stop.prevent="toggleControlMode"
          >
            {{ controlModeLabel }}
          </button>
          <button
            class="btn-primary btn-secondary btn-primary--wide"
            @click.stop.prevent="handleCancel"
          >
            {{ t('common.cancel') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  controlMode: {
    type: String,
    default: 'swipes' // 'swipes' | 'buttons'
  }
})

const emit = defineEmits(['confirm', 'cancel', 'update:controlMode'])

const { t } = useI18n()

const dontShowAgain = ref(false)

const controlModeLabel = computed(() =>
  props.controlMode === 'swipes' ? t('game.control_swipes') : t('game.control_buttons')
)

const toggleControlMode = () => {
  const next = props.controlMode === 'swipes' ? 'buttons' : 'swipes'
  emit('update:controlMode', next)
}

const handleConfirm = () => {
  emit('confirm', dontShowAgain.value)
}

const handleCancel = () => {
  emit('cancel')
}

const handleBackdropClick = () => {
  // Не закрываем при клике на backdrop
}
</script>

<style lang="scss" scoped>
.warning-modal-mask {
  position: fixed;
  z-index: 9999;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
}

.warning-modal-wrapper {
  width: 90%;
  max-width: 400px;
}

.warning-modal-container {
  background: #10151b;
  border-radius: 1rem;
  padding: 2rem;
  box-shadow: inset 0 0 0 1px #ffc300;
}

.warning-modal-header {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 1.5rem;

  .warning-icon {
    height: 28px;
    width: auto;
    object-fit: contain;
    flex-shrink: 0;
  }

  .warning-title {
    color: #ffc300;
    font-size: 18px;
    font-weight: 700;
    margin: 0;
    white-space: nowrap;
  }
}

.warning-modal-body {
  text-align: center;
  margin-bottom: 1.5rem;
  
  .warning-message {
    color: #fff;
    font-size: 14px;
    line-height: 1.6;
    margin-bottom: 1.25rem;
    text-align: left;
  }
  
  .warning-checkbox {
    display: flex;
    justify-content: flex-start;
    align-items: center;
    margin-top: 1rem;
    
    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      cursor: pointer;
      user-select: none;
      
      .checkbox-input {
        width: 18px;
        height: 18px;
        cursor: pointer;
        accent-color: #ffc300;
      }
      
      .checkbox-text {
        color: rgba(255, 255, 255, 0.9);
        font-size: 13px;
        line-height: 1.4;
      }
    }
  }
}

.warning-modal-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  align-items: center;
  width: 100%;
}

.btn-primary {
  min-width: 220px;
  padding: 14px 32px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(135deg, #7c3aed, #22d3ee);
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 12px 30px rgba(56, 189, 248, 0.45);
  letter-spacing: 0.02em;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;

  &:active:not(:disabled) {
    transform: scale(0.96);
    box-shadow: 0 6px 18px rgba(56, 189, 248, 0.35);
    opacity: 0.9;
  }
}

.btn-primary--wide {
  width: 100%;
}

.btn-secondary {
  background: rgba(15, 23, 42, 0.9);
  color: #e5e7eb;
  border: 1px solid rgba(148, 163, 184, 0.5);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.85);

  &:active {
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.85);
    opacity: 0.95;
  }
}
</style>
