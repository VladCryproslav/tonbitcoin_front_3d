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
  --control-pad: 20px;
  --btn-lr-w: 105px;
  --btn-lr-h: 115px;
  --btn-ud-w: 137px;
  --btn-ud-h: 80px; /* Увеличена высота кнопок вверх/вниз */
  --control-gap: clamp(12px, 3vw, 24px); /* Отступ между кнопками */

  position: absolute;
  bottom: calc(var(--control-pad) + 15px); /* Подняты кнопки вверх */
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  align-items: center; /* Центрируем все кнопки по высоте */
  padding: 0 var(--control-pad);
  pointer-events: none;
  z-index: 50;
  gap: var(--control-gap);
}

.control-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center; /* Центрируем кнопки вверх/вниз по вертикали */
  align-items: center;
  max-width: min(var(--btn-ud-w), 40vw);
  margin: 0 auto;
  min-height: 0;
  gap: var(--control-gap); /* Отступ между кнопками вверх и вниз такой же как между другими кнопками */
}

.control-btn {
  pointer-events: auto;
  border-radius: 20px;
  border: none;
  background: rgba(15, 23, 42, 0.40); /* Увеличена прозрачность */
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
  opacity: 0.55; /* Увеличена прозрачность кнопок */

  &:active,
  &:focus {
    outline: none;
  }

  svg {
    transition: transform 0.15s ease;
  }

  &:active {
    transform: scale(0.92);
    background: rgba(30, 64, 175, 0.40); /* Увеличена прозрачность при активном состоянии */
    border-color: rgba(148, 163, 184, 0.4);
    box-shadow: 0 4px 16px rgba(56, 189, 248, 0.25);
    opacity: 1; /* Полная непрозрачность при нажатии */

    svg {
      transform: scale(1.1);
    }
  }
}

.control-btn--left,
.control-btn--right {
  flex-shrink: 0;
  width: clamp(60px, 27vw, var(--btn-lr-w));
  height: clamp(70px, 30vw, var(--btn-lr-h));
}

.control-btn--up,
.control-btn--down {
  width: clamp(80px, 36vw, var(--btn-ud-w));
  height: clamp(50px, 18vw, var(--btn-ud-h)); /* Увеличена высота кнопок вверх/вниз */
}

@media (max-width: 400px) {
  .virtual-controls {
    --control-pad: 14px;
  }
}
</style>
