<template>
  <div
    class="game-controls"
    @touchstart="handleTouchStart"
    @touchend="handleTouchEnd"
    @touchmove="handleTouchMove"
  >
    <!-- Невидимая область для управления -->
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['swipe-left', 'swipe-right', 'swipe-up', 'swipe-down', 'tap'])

const touchStart = ref({ x: 0, y: 0, time: 0 })
const minSwipeDistance = 36
const maxSwipeTime = 420

const handleTouchStart = (e) => {
  const touch = e.touches[0]
  touchStart.value = {
    x: touch.clientX,
    y: touch.clientY,
    time: Date.now()
  }
}

const handleTouchEnd = (e) => {
  if (!touchStart.value.x) return

  const touch = e.changedTouches[0]
  const deltaX = touch.clientX - touchStart.value.x
  const deltaY = touch.clientY - touchStart.value.y
  const deltaTime = Date.now() - touchStart.value.time
  const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY)

  // Тап: короткое касание без заметного движения
  if (distance < 12 && deltaTime < 200) {
    emit('tap', { x: touch.clientX, y: touch.clientY })
    touchStart.value = { x: 0, y: 0, time: 0 }
    return
  }

  // Проверка на свайп
  if (distance > minSwipeDistance && deltaTime < maxSwipeTime) {
    const absX = Math.abs(deltaX)
    const absY = Math.abs(deltaY)

    if (absX > absY) {
      // Горизонтальный свайп
      if (deltaX > 0) {
        emit('swipe-right')
      } else {
        emit('swipe-left')
      }
    } else {
      // Вертикальный свайп
      if (deltaY > 0) {
        emit('swipe-down')
      } else {
        emit('swipe-up')
      }
    }
  }

  touchStart.value = { x: 0, y: 0, time: 0 }
}

const handleTouchMove = (e) => {
  // Предотвращаем скролл страницы во время игры
  e.preventDefault()
}
</script>

<style scoped>
.game-controls {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 10;
  touch-action: none;
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  user-select: none;
}
</style>
