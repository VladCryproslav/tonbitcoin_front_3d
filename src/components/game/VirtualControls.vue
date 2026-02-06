<template>
  <div class="virtual-controls">
    <!-- Левая стрелка -->
    <button
      class="control-btn control-btn--left"
      @touchstart.prevent="handleLeftStart"
      @touchend.prevent="handleLeftEnd"
      @touchcancel.prevent="handleLeftEnd"
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <!-- Центральные кнопки (вверх/вниз) -->
    <div class="control-center">
      <button
        class="control-btn control-btn--up"
        @touchstart.prevent="handleUpStart"
        @touchend.prevent="handleUpEnd"
        @touchcancel.prevent="handleUpEnd"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M18 15L12 9L6 15" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <button
        class="control-btn control-btn--down"
        @touchstart.prevent="handleDownStart"
        @touchend.prevent="handleDownEnd"
        @touchcancel.prevent="handleDownEnd"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M6 9L12 15L18 9" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>

    <!-- Правая стрелка -->
    <button
      class="control-btn control-btn--right"
      @touchstart.prevent="handleRightStart"
      @touchend.prevent="handleRightEnd"
      @touchcancel.prevent="handleRightEnd"
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M9 18L15 12L9 6" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['swipe-left', 'swipe-right', 'swipe-up', 'swipe-down'])

const activeButtons = ref(new Set())

const handleLeftStart = () => {
  activeButtons.value.add('left')
  emit('swipe-left')
}

const handleLeftEnd = () => {
  activeButtons.value.delete('left')
}

const handleRightStart = () => {
  activeButtons.value.add('right')
  emit('swipe-right')
}

const handleRightEnd = () => {
  activeButtons.value.delete('right')
}

const handleUpStart = () => {
  activeButtons.value.add('up')
  emit('swipe-up')
}

const handleUpEnd = () => {
  activeButtons.value.delete('up')
}

const handleDownStart = () => {
  activeButtons.value.add('down')
  emit('swipe-down')
}

const handleDownEnd = () => {
  activeButtons.value.delete('down')
}
</script>

<style lang="scss" scoped>
.virtual-controls {
  position: absolute;
  bottom: 20px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  pointer-events: none;
  z-index: 50;
  gap: 20px;
}

.control-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  max-width: 80px;
  margin: 0 auto;
}

.control-btn {
  pointer-events: auto;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: none;
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(12px);
  border: 2px solid rgba(148, 163, 184, 0.3);
  color: #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  transition: all 0.15s ease;
  touch-action: none;
  -webkit-tap-highlight-color: transparent;

  &:active,
  &:focus {
    outline: none;
  }

  svg {
    transition: transform 0.15s ease;
  }

  &:active {
    transform: scale(0.92);
    background: rgba(30, 64, 175, 0.6);
    border-color: rgba(148, 163, 184, 0.5);
    box-shadow: 0 4px 16px rgba(56, 189, 248, 0.3);

    svg {
      transform: scale(1.1);
    }
  }
}

.control-btn--left,
.control-btn--right {
  flex-shrink: 0;
}

.control-btn--up,
.control-btn--down {
  width: 56px;
  height: 56px;
}

@media (max-width: 480px) {
  .control-btn {
    width: 56px;
    height: 56px;
  }

  .control-btn--up,
  .control-btn--down {
    width: 50px;
    height: 50px;
  }

  .control-center {
    max-width: 70px;
    gap: 10px;
  }
}
</style>
