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
const swipeFired = ref(false)
const minSwipeDistance = 36
const maxSwipeTime = 420

const handleTouchStart = (e) => {
  const touch = e.touches[0]
  touchStart.value = {
    x: touch.clientX,
    y: touch.clientY,
    time: Date.now()
  }
  swipeFired.value = false
}

function tryEmitSwipe(deltaX, deltaY, deltaTime) {
  const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY)
  if (distance < minSwipeDistance || deltaTime > maxSwipeTime) return false
  const absX = Math.abs(deltaX)
  const absY = Math.abs(deltaY)
  if (absX > absY) {
    if (deltaX > 0) emit('swipe-right')
    else emit('swipe-left')
  } else {
    if (deltaY > 0) emit('swipe-down')
    else emit('swipe-up')
  }
  return true
}

const handleTouchEnd = (e) => {
  if (!touchStart.value.x) return

  const touch = e.changedTouches[0]
  const deltaX = touch.clientX - touchStart.value.x
  const deltaY = touch.clientY - touchStart.value.y
  const deltaTime = Date.now() - touchStart.value.time
  const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY)

  if (!swipeFired.value) {
    if (distance < 12 && deltaTime < 200) {
      emit('tap', { x: touch.clientX, y: touch.clientY })
    } else {
      tryEmitSwipe(deltaX, deltaY, deltaTime)
    }
  }

  touchStart.value = { x: 0, y: 0, time: 0 }
  swipeFired.value = false
}

const handleTouchMove = (e) => {
  e.preventDefault()
  if (!touchStart.value.x || swipeFired.value) return
  const touch = e.touches[0]
  const deltaX = touch.clientX - touchStart.value.x
  const deltaY = touch.clientY - touchStart.value.y
  const deltaTime = Date.now() - touchStart.value.time
  if (tryEmitSwipe(deltaX, deltaY, deltaTime)) {
    swipeFired.value = true
  }
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
