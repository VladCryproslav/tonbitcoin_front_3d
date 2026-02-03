<template>
  <div ref="container" class="game-scene-container"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { Scene, PerspectiveCamera, WebGLRenderer, Color, AmbientLight, DirectionalLight, Fog } from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

const props = defineProps({
  width: { type: Number, default: window.innerWidth },
  height: { type: Number, default: window.innerHeight },
  backgroundColor: { type: [String, Number], default: 0x87CEEB }, // Sky blue
  autoRender: { type: Boolean, default: false }, // Отключить автоматический рендеринг для игры
  graphicsQuality: { type: String, default: 'normal' } // normal | medium | low — для antialias и shadow map
})

const emit = defineEmits(['scene-ready'])

const container = ref(null)
let scene = null
let camera = null
let renderer = null
let controls = null
let animationId = null

const initScene = () => {
  if (!container.value) return

  // Создание сцены
  scene = new Scene()
  scene.background = new Color(props.backgroundColor)
  scene.fog = new Fog(props.backgroundColor, 6, 40) // Туман слабее: дальше старт и полная плотность

  // Камера
  camera = new PerspectiveCamera(
    75,
    props.width / props.height,
    0.1,
    1000
  )
  camera.position.set(0, 5, 10)
  camera.lookAt(0, 0, 0)

  // Рендерер: antialias только на normal — на mobile даёт фризы
  const useAntialias = props.graphicsQuality === 'normal'
  renderer = new WebGLRenderer({
    antialias: useAntialias,
    alpha: true,
    powerPreference: 'high-performance'
  })
  renderer.setSize(props.width, props.height)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = props.graphicsQuality !== 'low'
  if (props.graphicsQuality !== 'low') {
    renderer.shadowMap.type = 0 // BasicShadowMap — быстрее PCFSoft
  }
  container.value.appendChild(renderer.domElement)

  // Освещение - яркое как в Subway Surfers
  const ambientLight = new AmbientLight(0xffffff, 0.8) // Ярче для cartoon стиля
  scene.add(ambientLight)

  const directionalLight = new DirectionalLight(0xffffff, 1.0) // Очень яркое
  directionalLight.position.set(5, 10, 5)
  directionalLight.castShadow = props.graphicsQuality !== 'low'
  const shadowSize = props.graphicsQuality === 'normal' ? 2048 : 1024
  if (props.graphicsQuality !== 'low') {
    directionalLight.shadow.mapSize.width = shadowSize
    directionalLight.shadow.mapSize.height = shadowSize
  }
  scene.add(directionalLight)

  // Дополнительный свет спереди для яркости
  const frontLight = new DirectionalLight(0xffffff, 0.5)
  frontLight.position.set(0, 5, 10)
  scene.add(frontLight)

  // Анимационный цикл (только если autoRender включен)
  if (props.autoRender) {
    const animate = () => {
      animationId = requestAnimationFrame(animate)
      if (controls) controls.update()
      renderer.render(scene, camera)
    }
    animate()
  }

  emit('scene-ready', { scene, camera, renderer })
}

const handleResize = () => {
  if (!camera || !renderer) return

  camera.aspect = window.innerWidth / window.innerHeight
  camera.updateProjectionMatrix()
  renderer.setSize(window.innerWidth, window.innerHeight)
}

onMounted(() => {
  initScene()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)

  if (animationId) {
    cancelAnimationFrame(animationId)
  }

  if (renderer) {
    renderer.dispose()
    if (container.value && renderer.domElement) {
      container.value.removeChild(renderer.domElement)
    }
  }

  // Очистка сцены
  if (scene) {
    while (scene.children.length > 0) {
      scene.remove(scene.children[0])
    }
  }
})

watch(() => [props.width, props.height], () => {
  handleResize()
})

defineExpose({
  scene,
  camera,
  renderer,
  controls
})
</script>

<style scoped>
.game-scene-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}

.game-scene-container canvas {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
