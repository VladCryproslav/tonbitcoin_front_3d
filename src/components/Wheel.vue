<script setup>
import _random from 'lodash/random'
import { computed, onMounted, ref, watch } from 'vue'
import { canvasDefaultConfig } from './canvasConfig'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  type: {
    type: String,
    default: 'canvas',
  },
  canvas: {
    type: Object,
    default: () => canvasDefaultConfig,
  },
  disabled: {
    type: Boolean,
    default: false, // следует ли отключить
  },
  prizes: {
    type: Array,
    default: () => [], // Список призов
  },
  prizeId: {
    type: Number
  },
  angleBase: {
    type: Number,
    default: 7, // Основание угла поворота, количество витков 360*10
  },
  duration: {
    type: Number,
    default: 5000, // Время от одного оборота, в миллисекундах
  },
})

const imagePath = (path) => {
  const com = computed(
    () => new URL(`../assets/slots/${path}.webp`, import.meta.url).href,
  )
  return com
}

const emit = defineEmits(['rotate-start', 'rotate-end'])

const wheel = ref(null)
const isRotating = ref(false) // он крутится?
const rotateEndDeg = ref(0) // угол на который поворачивается барабан
const prizeId = ref(props.prizeId) // id приза, который выпадет
const prizeRes = ref({}) // Результаты вращения поворотного стола

watch(() => props.prizeId, (newPrizeId) => {
  prizeId.value = newPrizeId
})

onMounted(() => {
  if (props.type === 'canvas' && props.prizes?.length > 0) {
    drawCanvas()
  }
})

const { t } = useI18n()

const canRotate = computed(() => { return !props.disabled && !isRotating.value })
const canvasConfig = computed(() => { return Object.assign(canvasDefaultConfig, props.canvas) })
const prizesIdArr = computed(() => {
  const idArr = []
  props.prizes?.forEach((row) => {
    const count = 0
    const arr = new Array(count).fill(row.id)
    idArr.push(...arr)
  })
  return idArr
})
const rotateBase = computed(() => {
  let angle = props.angleBase * 360
  if (props.angleBase < 0) angle -= 360
  return angle
})
const rotateStyle = computed(() => {
  return {
    '-webkit-transform': `rotateZ(${rotateEndDeg.value}deg)`,
    'transform': `rotateZ(${rotateEndDeg.value}deg)`,
    '-webkit-transition-duration': `${rotateDuration.value}ms`,
    'transition-duration': `${rotateDuration.value}ms`,
    '-webkit-transition-timing-function': isRotating.value
      ? `cubic-bezier(0.22, 0.95, 0.24, ${_random(0.95, 1.03, true)})`
      : 'ease-in',
    'transition-timing-function': isRotating.value
      ? `cubic-bezier(0.22, 0.95, 0.24, ${_random(0.95, 1.03, true)})`
      : 'ease-in',
  }
})
const rotateDuration = computed(() => {
  return isRotating.value ? props.duration : 0
})

function getStrArray(str, len) {
  const arr = []
  while (str !== '') {
    let text = str.substr(0, len)
    if (str.charAt(len) !== '' && str.charAt(len) !== ' ') {
      // Если следующая строка существует и первый символ следующей
      // строки не является пробелом
      const index = text.lastIndexOf(' ')
      if (index !== -1) text = text.substr(0, index)
    }
    str = str.replace(text, '').trim()
    arr.push(text)
  }
  return arr
}

function handleClick() {
  if (!canRotate.value) return
  emit('rotate-start')
  onRotateStart()
}

defineExpose({ handleClick, prizeId })

function onRotateStart() {
  isRotating.value = true
  const prize_id = prizeId.value ?? getRandomPrize()
  const baseDeg = rotateBase.value + getTargetDeg(prize_id)

  // const slotAngle = 360 / this.prizes.length;
  // const overshootDeg = !Math.round(Math.random()) ? (baseDeg + slotAngle / _random(2, 2.2, true)) : (baseDeg - slotAngle / _random(1.6, 1.9, true));
  rotateEndDeg.value = baseDeg
  // this.rotateEndDeg = overshootDeg;

  // setTimeout(() => {
  //   this.rotateEndDeg = baseDeg;
  // }, this.duration * 0.80);
}
function getRandomPrize() {
  const len = prizesIdArr.value?.length || 0
  const prizeId = prizesIdArr.value?.[_random(0, len - 1)]
  return prizeId
}

function getTargetDeg(prizeId) {
  const angle = 360 / props.prizes?.length
  const num = props.prizes?.findIndex((row) => row.id === prizeId)
  prizeRes.value = props.prizes?.find((el) => el.id == prizeId)
  return 180 - (angle * num + angle / 2)
}
function drawCanvas() {
  const canvasEl = wheel.value
  if (canvasEl.getContext) {
    const { radius, textRadius, borderWidth, fontSize, fontFamily } = canvasConfig.value
    const arc = Math.PI / (props.prizes.length / 2)
    const ctx = canvasEl.getContext('2d')
    ctx.clearRect(0, 0, radius * 2, radius * 2)
    ctx.font = `600 ${fontSize}px ${fontFamily}`
    props.prizes.forEach((row, i) => {
      const angle = i * arc - Math.PI / 2
      if (row.color == 'superprize') {
        let xStart, yStart, xEnd, yEnd
        xStart = radius
        yStart = 0
        xEnd = radius
        yEnd = radius * 2.5
        const grd = ctx.createLinearGradient(xStart, yStart, xEnd, yEnd)
        const colors = {
          asic_manager: ['#FCD909', '#FEA400'],
          jarvis: ['#D340FF', '#DD1E1E'],
          ASIC: ['#74F98A', '#0EA65A'],
          magnit: ['#FCD909', '#FEA400'],
          // kW: ['#09ECFC', '#0050FE'],
        }
        colors[row.asset_name].forEach((color, index) => {
          grd.addColorStop(index, color.trim())
        })
        ctx.fillStyle = grd
      } else {
        ctx.fillStyle = i % 2 ? '#6762F0' : '#4D49AA'
      }
      ctx.beginPath()
      ctx.arc(radius, radius, radius - borderWidth, angle, angle + arc, false)
      ctx.stroke()
      ctx.arc(radius, radius, 0, angle + arc, angle, true)
      ctx.fill()
      if (row.asset_image) {
        const img = new Image()
        img.src = row.asset_image
        img.onload = () => {
          const maxImageSize = 90
          const imageX = radius + Math.cos(angle + arc / 2) * (textRadius - 110)
          const imageY = radius + Math.sin(angle + arc / 2) * (textRadius - 110)
          ctx.save()
          ctx.translate(imageX, imageY)
          ctx.rotate(angle + arc / 2 - Math.PI / 2)
          ctx.beginPath()
          ctx.arc(0, 0, maxImageSize / 2, 0, Math.PI * 2)
          ctx.clip()
          ctx.drawImage(img, -maxImageSize / 2, -maxImageSize / 2, maxImageSize, maxImageSize) // Center the scaled image
          ctx.restore()
        }
      }
      ctx.save()
      ctx.fillStyle =
        (row.asset_name == 'magnit' || row.asset_name == 'asic_manager') && row.color == 'superprize' ? '#00000090' : '#fff'
      ctx.translate(
        radius + Math.cos(angle + arc / 2) * textRadius,
        radius + Math.sin(angle + arc / 2) * textRadius,
      )
      drawPrizeText(ctx, angle, arc, row)
      ctx.restore()
    })
  }
}
function onRotateEnd() {
  isRotating.value = false
  rotateEndDeg.value %= 360
  emit('rotate-end', prizeRes.value)
}
function drawPrizeText(ctx, angle, arc, item) {
  const { lineHeight, textLength, fontFamily } = canvasConfig.value
  let item_text = item.asset_quantity !== null ?
    ['azot', 'powerbank', 'autostart'].includes(item.asset_name) ?
      String(t('common.pcs', { n: item.asset_quantity }).slice(0, -1)) :
      item.asset_name == 'electrics' ?
        String(t('common.pers', { n: item.asset_quantity })) :
        String(t('common.days', { n: item.asset_quantity })) :
    item.n_parameter
  const content = getStrArray(item_text, textLength)
  if (content === null) return
  ctx.rotate(angle + arc / 2 - Math.PI / 2)
  // ctx.scale(-1, -1);
  if (item.asset_quantity >= 3 && item.color !== 'superprize') {
    // Calculate the maximum text width and total height for the frame
    let maxTextWidth = 0
    content.forEach((text) => {
      maxTextWidth = Math.max(maxTextWidth, ctx.measureText(text).width)
    })
    const textHeight = content.length * lineHeight
    const padding = 8 // Padding around text for the frame
    const frameWidth = maxTextWidth + padding * 2
    const frameHeight = textHeight + padding * 2
    const frameX = -frameWidth / 2
    const frameY = -textHeight / 1.2 - padding
    // Draw gradient-filled rounded rectangle
    const borderRadius = 20 // Set border-radius for rounded corners
    const grd = ctx.createLinearGradient(frameX, frameY, frameX + frameWidth, frameY)
    grd.addColorStop(0, item.asset_quantity == 3 ? '#FCD909' : '#DD1E1E')
    grd.addColorStop(1, item.asset_quantity == 3 ? '#FEA400' : '#D340FF')
    ctx.fillStyle = grd
    ctx.beginPath()
    ctx.roundRect(frameX, frameY, frameWidth, frameHeight, borderRadius)
    ctx.fill()
    // Draw border
    ctx.strokeStyle = item.asset_quantity == 3 ? '#FCD007' : '#D340FF'
    ctx.lineWidth = 0
    ctx.beginPath()
    ctx.roundRect(frameX, frameY, frameWidth, frameHeight, borderRadius)
    ctx.stroke()
    ctx.fillStyle = item.asset_quantity == 3 ? '#00000090' : '#ffffff'
  }
  content.forEach((text, idx) => {
    let textX = -ctx.measureText(text).width / 2
    let textY = (idx - (content.length - 1) / 2) * lineHeight
    ctx.fillText(text, textX, textY)
  })
  ctx.restore()
  if (item.color == "superprize") {
    ctx.save();
    ctx.translate(
      canvasConfig.value.radius + Math.cos(angle + arc / 2) * (canvasConfig.value.textRadius - 20),
      canvasConfig.value.radius + Math.sin(angle + arc / 2) * (canvasConfig.value.textRadius - 20)
    )
    ctx.rotate(angle + arc / 2.1);

    let text = t('wheel.superprize');
    let textWidth = ctx.measureText(text).width;
    let textHeight = text.length * lineHeight; // Total height of the text
    let textX = -textWidth * 1.6
    let textY = textHeight / 50; // Adjust offset to position below the main text
    ctx.fillStyle = ['ASIC', 'jarvis'].includes(item.asset_name) ? '#ffffff' : '#00000090'
    ctx.font = `700 45px ${fontFamily}`
    ctx.fillText(text, textX, textY);
    ctx.restore();
  }
}
</script>

<template>
  <div class="fw-container">
    <div class="fw-wheel" :style="rotateStyle" @transitionend="onRotateEnd" @webkitTransitionend="onRotateEnd">
      <canvas ref="wheel" :width="canvasConfig.radius * 2" :height="canvasConfig.radius * 2"></canvas>
    </div>

    <div class="fw-mark">
      <img src="@/assets/mark.png" width="55px" height="55px" />
    </div>

    <div class="fw-btn">
      <div v-if="type === 'canvas'" class="fw-btn__btn" :style="{
        width: '25%',
        height: '25%',
      }">
        <img src="@/assets/slots/fBTC.webp" width="70px" height="70px" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.fw-container {
  position: relative;
  display: inline-block;
  font-size: 0;
  /* overflow: hidden; */
}

.fw-container canvas,
img {
  display: block;
  width: 100%;
}

.fw-btn {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.fw-btn__btn {
  position: relative;
  width: 100%;
  height: 100%;
  border: 10px solid #fcd007;
  border-radius: 50%;
  background: #fcd007;
  display: flex;
  justify-content: center;
  align-items: center;
  box-shadow: 0px 10px 0px 0px #00000050;
}

.fw-mark {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translate(-50%, 50px);
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.fw-mark img {
  width: 55px !important;
  height: 55px !important;
}
</style>
