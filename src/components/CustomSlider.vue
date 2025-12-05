<template>
  <div class="slider-root" @click="handleTrackClick" @touchstart="handleTrackClick">
    <div class="slider-rail"></div>
    <!-- Зелена -->
    <div class="slider-process" :style="{
      left: percent(min) + '%',
      width: (percent(modelValue) - percent(min)) + '%'
    }"></div>
    <!-- Сіра -->
    <div class="slider-interval" :style="{
      left: percent(modelValue) + '%',
      width: (Math.min(percent(props.available), 100) - percent(modelValue)) + '%'
    }"></div>
    <!-- Бордова -->
    <div class="slider-rail slider-rail-right" :style="{
      left: Math.min(percent(props.available), 100) + '%',
      width: (100 - Math.min(percent(props.available), 100)) + '%'
    }"></div>
    <!-- Перша ручка -->
    <div class="slider-dot" :style="{ left: percent(modelValue) + '%' }" tabindex="0" @mousedown="startDrag"
      @touchstart="startDrag" :class="{ 'slider-dot-disabled': props.disabled }"></div>
    <!-- Друга ручка (фіксована) -->
    <div class="slider-dot slider-dot-fixed" :style="{ left: Math.min(percent(props.available), 100) + '%' }"></div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted } from 'vue'

const props = defineProps({
  min: { type: Number, default: 0 },
  max: { type: Number, required: true },
  available: { type: Number, required: true },
  modelValue: { type: Number, required: true },
  disabled: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue'])

function percent(val) {
  // Используем max для расчета процентов (ползунок ограничен max)
  return ((val - props.min) / (props.max - props.min)) * 100
}

function percentAvailable(val) {
  // Для визуализации available используем max, если available больше max
  // Это позволяет показывать, что доступно больше, но ползунок останавливается на max
  const visualMax = Math.max(props.max, props.available)
  return ((val - props.min) / (visualMax - props.min)) * 100
}

let dragging = false

function startDrag(e) {
  if (props.disabled) return
  dragging = true
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('touchmove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchend', stopDrag)
  e.preventDefault()
  e.stopPropagation()
}

function handleTrackClick(e) {
  if (props.disabled || dragging) return

  let clientX
  if (e.touches) clientX = e.touches[0].clientX
  else clientX = e.clientX

  const slider = e.currentTarget
  const rect = slider.getBoundingClientRect()
  let percentPos = (clientX - rect.left) / rect.width
  percentPos = Math.max(0, Math.min(1, percentPos))
  let newValue = Math.round(props.min + percentPos * (props.max - props.min))

  // Обмежуємо рух до min і max (max може бути менше available)
  if (newValue > props.max) newValue = props.max
  if (newValue < props.min) newValue = props.min

  emit('update:modelValue', newValue)
}

function onDrag(e) {
  if (!dragging) return
  let clientX
  if (e.touches) clientX = e.touches[0].clientX
  else clientX = e.clientX
  const slider = document.querySelector('.slider-root')
  const rect = slider.getBoundingClientRect()
  let percentPos = (clientX - rect.left) / rect.width
  percentPos = Math.max(0, Math.min(1, percentPos))
  let newValue = Math.round(props.min + percentPos * (props.max - props.min))
  // Обмежуємо рух до min і max (max може бути менше available)
  if (newValue > props.max) newValue = props.max
  if (newValue < props.min) newValue = props.min
  emit('update:modelValue', newValue)
}

function stopDrag() {
  dragging = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchend', stopDrag)
}
onMounted(() => {
  console.log(props.min)
  console.log(props.modelValue)
})
onBeforeUnmount(stopDrag)
</script>

<style scoped>
.slider-root {
  position: relative;
  width: 100%;
  height: 20px;
  user-select: none;
}

.slider-rail {
  position: absolute;
  top: 50%;
  left: 0;
  height: 8px;
  background: #502024;
  border-radius: 8px;
  transform: translateY(-50%);
  z-index: 1;
}

.slider-rail-right {
  background: #502024;
  z-index: 3;
}

.slider-process {
  position: absolute;
  top: 50%;
  height: 8px;
  background: #31FF80;
  border-radius: 8px 0 0 8px;
  transform: translateY(-50%);
  z-index: 2;
}

.slider-interval {
  position: absolute;
  top: 50%;
  height: 8px;
  background: #6c6c6c;
  border-radius: 0;
  transform: translateY(-50%);
  z-index: 2;
}

.slider-dot {
  position: absolute;
  top: 50%;
  width: 25px;
  height: 25px;
  background: #fff;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  z-index: 10;
  box-shadow: 0 2px 8px #0002;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.slider-dot-fixed {
  width: 16px;
  height: 16px;
  background: #fff;
  z-index: 4;
  box-shadow: 0 2px 8px #0002;
  cursor: default;
}

.slider-dot-disabled {
  width: 16px;
  height: 16px;
  cursor: not-allowed;
}
</style>