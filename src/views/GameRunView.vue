<template>
  <div class="game-run-view">
    <!-- Three.js сцена -->
    <GameScene
      ref="gameSceneRef"
      @scene-ready="onSceneReady"
    />

    <!-- UI поверх игры: только после старта забега -->
    <GameUI
      v-if="gameRun.isRunning || gameRun.isPaused"
      :energy="gameRun.energyCollected"
      :distance="gameRun.distance"
      :power="gameRun.currentPower"
      :lives="livesLeft"
      :max-lives="MAX_LIVES"
      :show-pause="gameRun.isRunning && !gameRun.isPaused && !showGameOver"
      @pause="openPauseOverlay"
    />

    <!-- Управление (свайпы + тап для старта на мобильных) -->
    <GameControls
      @swipe-left="handleSwipeLeft"
      @swipe-right="handleSwipeRight"
      @swipe-up="handleSwipeUp"
      @swipe-down="handleSwipeDown"
      @tap="handleTap"
    />

    <!-- Стартовый оверлей лаунчера -->
    <div
      v-if="launcherOverlayMode === 'idle' && !showGameOver"
      class="game-over-overlay"
    >
      <div class="game-over-card">
        <div class="game-over-title">
          {{ t('game.run_start_title') }}
        </div>
        <div class="game-over-subtitle">
          {{ t('game.run_start_subtitle') }}
        </div>
        <div class="game-over-actions">
          <button
            class="btn-primary btn-primary--wide"
            @click.stop.prevent="handleStartClick"
          >
            {{ t('game.run_start_button') }}
          </button>
          <button
            class="btn-primary btn-secondary btn-primary--wide"
            @click.stop.prevent="toggleGraphicsQuality"
          >
            {{ graphicsLabel }}
          </button>
          <button
            class="btn-primary btn-secondary btn-primary--wide"
            @click.stop.prevent="exitToMain"
          >
            {{ t('game.back_to_main') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Пауза -->
    <div
      v-if="launcherOverlayMode === 'pause' && !showGameOver"
      class="game-over-overlay"
    >
      <div class="game-over-card">
        <div class="game-over-title">
          {{ t('game.pause_title') }}
        </div>
        <div class="game-over-subtitle">
          {{ t('game.pause_subtitle') }}
        </div>
        <div class="game-over-actions">
          <button
            class="btn-primary btn-primary--wide"
            @click.stop.prevent="handleResumeClick"
          >
            {{ t('game.resume') }}
          </button>
          <button
            class="btn-primary btn-secondary btn-primary--wide"
            @click.stop.prevent="exitToMain"
          >
          {{ t('game.back_to_main') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Экран окончания забега -->
    <div
      v-if="showGameOver"
      class="game-over-overlay"
    >
      <div class="game-over-card">
        <div class="game-over-title">
          {{
            gameOverType === 'win'
              ? t('game.win_title')
              : t('game.lose_title')
          }}
        </div>
        <div class="game-over-subtitle">
          {{
            gameOverType === 'win'
              ? t('game.win_subtitle')
              : t('game.lose_subtitle')
          }}
        </div>
        <div class="game-over-actions">
          <button
            class="btn-primary btn-primary--wide"
            @click.stop.prevent="exitToMain"
          >
            {{ t('game.back_to_main') }}
          </button>
        </div>
      </div>
    </div>

    <InfoModal
      v-if="showGraphicsInfoModal"
      @close="handleGraphicsInfoClose"
    >
      <template #header>
        {{ t('game.graphics_modal_title') }}
      </template>
      <template #modal-body>
        {{ t('game.graphics_modal_body') }}
      </template>
    </InfoModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import GameScene from '@/components/game/GameScene.vue'
import GameUI from '@/components/game/GameUI.vue'
import GameControls from '@/components/game/GameControls.vue'
import InfoModal from '@/components/InfoModal.vue'
import { useGameRun } from '@/composables/useGameRun'
import { useGamePhysics } from '@/composables/useGamePhysics'
import { useGameWorld } from '@/composables/useGameWorld'
import { useGameEffects } from '@/composables/useGameEffects'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const { t } = useI18n()
const app = useAppStore()

const gameSceneRef = ref(null)
const gameRun = useGameRun()
const gamePhysics = ref(null)
const gameWorld = ref(null)
const gameEffects = ref(null)
let scene = null
let camera = null
let renderer = null
// Экран окончания забега (win/lose)
const showGameOver = ref(false)
const gameOverType = ref('lose') // 'win' | 'lose'

// Режим оверлея лаунчера: старт до забега или пауза.
// 'idle' — до первого старта, 'pause' — пауза, 'none' — нет оверлея.
const launcherOverlayMode = ref('idle')

let threeLoop = null
let lastUpdateTime = 0
let shakeFramesLeft = 0
const FIXED_STEP_MS = 1000 / 60
const MAX_STEPS = 3
const ROLL_IMMUNE_MS = 950
const gameSpeed = ref(0.15)
const playerZ = ref(0)
const lastSpeedIncrease = ref(0)
const hitCount = ref(0)
const MAX_LIVES = 3
const livesLeft = computed(() => Math.max(0, MAX_LIVES - hitCount.value))

// Настройки графики: normal | low
const graphicsQuality = ref('normal')
const isWeakDevice = ref(false)
const showGraphicsInfoModal = ref(false)
const pendingGraphicsQuality = ref(null)

const graphicsLabel = computed(() =>
  graphicsQuality.value === 'normal' ? t('game.graphics_label_normal') : t('game.graphics_label_low')
)

const onSceneReady = ({ scene: threeScene, camera: threeCamera, renderer: threeRenderer }) => {
  scene = threeScene
  camera = threeCamera
  renderer = threeRenderer

  // Камера: чуть ближе (Z), чуть выше (Y), взгляд чуть сверху вниз (lookAt Y ниже)
  camera.position.set(0, 2.5, 4.4)
  camera.lookAt(0, -0.15, -18)

  // Инициализация игрового мира
  gameWorld.value = useGameWorld(scene, camera)
  gameWorld.value.createRoad()

  // Инициализация физики и создание игрока
  gamePhysics.value = useGamePhysics(scene)
  // Загружаем основную модель с полным набором анимаций (standing/running/jump/roll/fall)
  gamePhysics.value.createPlayer(scene, '/models/main.glb')

  // Инициализация эффектов
  gameEffects.value = useGameEffects(scene)

  // Запуск рендеринга Three.js
  startThreeLoop()

  applyGraphicsQuality()
}

// Очень плавное следование камеры: без рывков, незаметный дрейф от центра при смене полосы
const CAMERA_SMOOTH_TIME = 0.55 // секунд до ~95% к цели (frame-rate independent)
let lastCameraTime = 0

const startThreeLoop = () => {
  const animate = () => {
    threeLoop = requestAnimationFrame(animate)

    // 1) Сначала физика (позиция персонажа, смена полосы) — потом рендер, без кадра задержки
    if (gamePhysics.value) {
      gamePhysics.value.update()
    }

    // 2) Игровая логика в том же rAF (фикс. шаг). playerBox один раз за кадр — меньше setFromObject при наборе скорости.
    if (gameRun.isRunning.value && !gameRun.isPaused.value) {
      const now = performance.now()
      if (lastUpdateTime <= 0) lastUpdateTime = now
      let frameTime = Math.min(now - lastUpdateTime, 100)
      lastUpdateTime = now
      const nowMs = Date.now()
      const slideStartTime = gamePhysics.value?.getSlideStartTime?.() ?? 0
      const inRollImmuneWindow = slideStartTime > 0 && nowMs - slideStartTime < ROLL_IMMUNE_MS
      const framePlayerBox = gamePhysics.value?.getPlayerBox?.() ?? null
      let steps = 0
      while (frameTime >= FIXED_STEP_MS && steps < MAX_STEPS) {
        doOneStep(framePlayerBox, inRollImmuneWindow, nowMs)
        frameTime -= FIXED_STEP_MS
        steps++
      }
      if (gameWorld.value) gameWorld.value.spawnObjects(playerZ.value)
      if (gameEffects.value && graphicsQuality.value === 'normal') {
        gameEffects.value.updateEffects()
      }
      if (hitCount.value >= 3) {
        if (gameWorld.value) gameWorld.value.setRoadSpeed(0)
        gameSpeed.value = 0
        if (gamePhysics.value?.setAnimationState) gamePhysics.value.setAnimationState('fall')
        setTimeout(() => {
          gameOverType.value = 'lose'
          showGameOver.value = true
          launcherOverlayMode.value = 'none'
          endGame(false)
        }, 1000)
      }
    }

    // 3) Камера: цель из физики напрямую (не из game loop), плавное следование
    if (camera && gamePhysics.value?.getCameraLaneX) {
      const now = performance.now() / 1000
      const dt = lastCameraTime > 0 ? Math.min(now - lastCameraTime, 0.05) : 0.016
      lastCameraTime = now
      const laneX = gamePhysics.value.getCameraLaneX()
      const targetCamX = laneX === 0 ? 0 : laneX * 0.95
      const k = -Math.log(0.05) / CAMERA_SMOOTH_TIME
      const t = 1 - Math.exp(-k * dt)
      camera.position.x += (targetCamX - camera.position.x) * t
      const cameraBob = Math.sin(Date.now() * 0.003) * 0.08
      camera.position.y = 2.5 + cameraBob
      camera.lookAt(camera.position.x, -0.15 + cameraBob * 0.5, -18)
    }
    if (camera && shakeFramesLeft > 0) {
      camera.position.x += (Math.random() - 0.5) * 0.3
      camera.position.y += (Math.random() - 0.5) * 0.3
      shakeFramesLeft--
    }

    // 4) Рендер после обновления позиции и камеры
    if (renderer && scene && camera) {
      renderer.render(scene, camera)
    }
  }
  animate()
}

const applyGraphicsQuality = () => {
  if (!renderer || !scene) return

  const isLow = graphicsQuality.value === 'low'

  // Тени и качество рендера
  renderer.shadowMap.enabled = !isLow
  if (isLow) {
    renderer.setPixelRatio(1)
  } else {
    const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1
    renderer.setPixelRatio(Math.min(dpr, 2))
  }

  // Отключаем castShadow/receiveShadow у объектов и источников света на низкой графике
  scene.traverse?.((obj) => {
    if ('castShadow' in obj) {
      obj.castShadow = !isLow
    }
    if ('receiveShadow' in obj && isLow) {
      obj.receiveShadow = false
    }
  })
}

const applyGraphicsQualityAndSave = () => {
  applyGraphicsQuality()
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      window.localStorage.setItem('game_graphics_quality', graphicsQuality.value)
    } catch {
      // ignore quota / privacy errors
    }
  }
}

const startGame = () => {
  // Если забег уже идёт — игнорируем повторный старт
  if (gameRun.isRunning.value && !gameRun.isPaused.value) return

  playerZ.value = 0
  gameSpeed.value = 0.15
  lastSpeedIncrease.value = 0
  if (gameWorld.value) {
    // Очищаем объекты прошлого забега и пересоздаём дорожку/разметку
    gameWorld.value.clearAll()
    gameWorld.value.createRoad()
  }
  if (gamePhysics.value) {
    gamePhysics.value.resetSlideState?.()
    gamePhysics.value.resetLaneTransition?.()
    const mesh = gamePhysics.value.playerMesh()
    if (mesh) {
      mesh.position.set(0, 0, 0)
    }
    // Сбрасываем вычислительную позицию игрока
    if (gamePhysics.value.playerPosition?.value) {
      gamePhysics.value.playerPosition.value.x = 0
      gamePhysics.value.playerPosition.value.y = 0
      gamePhysics.value.playerPosition.value.z = 0
    }
    // Сбрасываем полосу только если это именно ref,
    // иначе не трогаем (во избежание ошибок типа "Cannot create property 'value' on number '1'")
    const laneRef = gamePhysics.value.playerLane
    if (laneRef && typeof laneRef === 'object' && 'value' in laneRef) {
      laneRef.value = 1
    }
    lastCameraTime = 0
  }
  gameRun.startRun()
  hitCount.value = 0
  showGameOver.value = false
  launcherOverlayMode.value = 'none'
  if (gamePhysics.value?.setAnimationState) {
    gamePhysics.value.setAnimationState('running')
  }
  lastUpdateTime = 0
}

const pauseGame = () => {
  gameRun.pauseRun()
  stopGameLoop()
  launcherOverlayMode.value = 'pause'
}

const resumeGame = () => {
  gameRun.resumeRun()
  lastUpdateTime = 0
  launcherOverlayMode.value = 'none'
}

function doOneStep(playerBox, inRollImmuneWindow, nowMs) {
  playerZ.value += gameSpeed.value
  gameRun.updateDistance(gameRun.distance.value + gameSpeed.value * 10)

  if (gamePhysics.value) {
      if (gameWorld.value) {
        gameWorld.value.setRoadSpeed(gameSpeed.value)
        gameWorld.value.updateRoad()

        gameWorld.value.updateObstacles(
          playerBox,
          () => {
            hitCount.value += 1
            gameRun.hitObstacle()
            const newPower = gameRun.currentPower.value - 10
            app.setPower(Math.max(0, newPower))
            shakeFramesLeft = 10
          },
          gamePhysics.value.isSliding?.value === true,
          inRollImmuneWindow
        )

        gameWorld.value.updateCollectibles(
          playerBox,
          (energy) => {
            gameRun.collectEnergy(energy)
          },
          nowMs
        )
      }
    }

  // Увеличение скорости: каждые 80 дистанции +0.008, макс 0.45
  const distanceCheck = Math.floor(gameRun.distance.value / 80)
  if (distanceCheck > 0 && distanceCheck !== lastSpeedIncrease.value) {
    lastSpeedIncrease.value = distanceCheck
    gameSpeed.value = Math.min(gameSpeed.value + 0.008, 0.45)
  }
}

const stopGameLoop = () => {
  lastUpdateTime = 0
}

const toggleGraphicsQuality = () => {
  const current = graphicsQuality.value
  const next = current === 'normal' ? 'low' : 'normal'

  // Слабое устройство и попытка включить "Нормально" — показываем рекомендацию.
  if (isWeakDevice.value && current === 'low' && next === 'normal') {
    pendingGraphicsQuality.value = next
    showGraphicsInfoModal.value = true
    return
  }

  graphicsQuality.value = next
  applyGraphicsQualityAndSave()
}

const endGame = async (isWinByState = false) => {
  stopGameLoop()

  // Полная очистка объектов мира и эффектов, чтобы собранные кубы/препятствия
  // не "зависали" возле персонажа после удара/завершения забега.
  if (gameWorld.value) {
    gameWorld.value.clearAll()
  }
  if (gameEffects.value) {
    gameEffects.value.clearAll()
  }

  const result = await gameRun.completeRun().catch((e) => {
    console.error('Ошибка завершения забега:', e)
    return null
  })

  const isSuccess = isWinByState || (result && result.success)

  if (isSuccess) {
    // Успешное завершение забега — проигрываем победную анимацию
    if (gamePhysics.value?.setAnimationState) {
      gamePhysics.value.setAnimationState('win')
    }
    gameOverType.value = 'win'
    showGameOver.value = true
    launcherOverlayMode.value = 'none'
  }
}

// Обработчики кнопок из оверлеев
const handleStartClick = () => {
  startGame()
}

const handleResumeClick = () => {
  resumeGame()
}

const openPauseOverlay = () => {
  pauseGame()
}

const handleSwipeLeft = () => {
  // Игрок реагирует на свайпы только во время активного забега
  if (!gameRun.isRunning.value || gameRun.isPaused.value) return
  if (gamePhysics.value) {
    gamePhysics.value.moveLeft()
  }
}

const handleSwipeRight = () => {
  if (!gameRun.isRunning.value || gameRun.isPaused.value) return
  if (gamePhysics.value) {
    gamePhysics.value.moveRight()
  }
}

const handleSwipeUp = () => {
  if (!gameRun.isRunning.value || gameRun.isPaused.value) return
  if (gamePhysics.value) {
    gamePhysics.value.jump()
  }
}

const handleSwipeDown = () => {
  if (!gameRun.isRunning.value || gameRun.isPaused.value) return
  if (gamePhysics.value) {
    gamePhysics.value.slide()
  }
}

// Тап по экрану: если игра ещё не запущена — стартуем забег
// Тап по экрану:
// - только стартует игру, чтобы не конфликтовать с кнопкой.
const handleTap = () => {
  if (!gameRun.isRunning.value) {
    startGame()
  }
}

// Выход из лаунчера обратно в основное приложение.
const exitToMain = () => {
  stopGameLoop()
  if (threeLoop) {
    cancelAnimationFrame(threeLoop)
  }
  if (gameRun.isRunning.value) {
    gameRun.stopRun()
  }
  if (gameWorld.value) {
    gameWorld.value.clearAll()
  }
  if (gameEffects.value) {
    gameEffects.value.clearAll()
  }
  showGameOver.value = false
  launcherOverlayMode.value = 'none'
  router.push('/')
}

const detectWeakDevice = () => {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return false

  const ua = navigator.userAgent || ''
  const cores = navigator.hardwareConcurrency || 4
  const dpr = window.devicePixelRatio || 1
  const mem = navigator.deviceMemory || 0
  const width = window.innerWidth || 0
  const height = window.innerHeight || 0
  const shortSide = Math.min(width, height)

  const isIOS = /iPhone|iPad|iPod/.test(ua)

  // Современные iOS‑устройства с высоким DPI и >=4 потоками считаем достаточно мощными,
  // не форсим для них low по умолчанию — пользователь сам может переключиться.
  if (isIOS && dpr >= 3 && cores >= 4) {
    return false
  }

  // Явно слабые устройства: очень мало ядер или мало памяти (там, где она доступна).
  if (cores && cores <= 2) return true
  if (mem && mem <= 2) return true

  // Старые/маленькие телефоны: маленький экран + низкий DPI + не больше 4 ядер.
  // Это, в частности, бьёт по типичным 4.7" устройствам вроде iPhone SE 1‑го поколения.
  if (!isIOS && cores <= 4 && dpr <= 2 && shortSide && shortSide <= 640) {
    return true
  }

  return false
}

const handleGraphicsInfoClose = (e) => {
  showGraphicsInfoModal.value = false
  if (e?.check && pendingGraphicsQuality.value) {
    graphicsQuality.value = pendingGraphicsQuality.value
    applyGraphicsQualityAndSave()
  }
  pendingGraphicsQuality.value = null
}

onMounted(() => {
  // Инициализация при монтировании
  isWeakDevice.value = detectWeakDevice()

  if (typeof window !== 'undefined') {
    try {
      const saved = window.localStorage?.getItem('game_graphics_quality')
      if (saved === 'normal' || saved === 'low') {
        graphicsQuality.value = saved
      } else {
        graphicsQuality.value = isWeakDevice.value ? 'low' : 'normal'
      }
    } catch {
      graphicsQuality.value = isWeakDevice.value ? 'low' : 'normal'
    }
  }
})

onUnmounted(() => {
  stopGameLoop()
  if (threeLoop) {
    cancelAnimationFrame(threeLoop)
  }
  if (gameRun.isRunning.value) {
    gameRun.stopRun()
  }
  if (gameWorld.value) {
    gameWorld.value.clearAll()
  }
  if (gameEffects.value) {
    gameEffects.value.clearAll()
  }
})
</script>

<style lang="scss" scoped>
.game-run-view {
  // Полноэкранный лаунчер раннера: занимаем всю область окна.
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100dvh;
  overflow: hidden;
  background: #000;
  z-index: 9999; // Выше всего остального интерфейса приложения
}

.game-top-bar {
  position: absolute;
  top: calc(env(safe-area-inset-top, 0px) + 72px);
  right: 20px;
  z-index: 450; // чуть выше GameUI, но ниже финального оверлея
  display: flex;
  gap: 8px;
}

.btn-exit {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  border: none;
  background: rgba(15, 23, 42, 0.8);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  transition: transform 0.15s ease, opacity 0.15s ease, background 0.15s ease;

  &:active {
    transform: scale(0.9);
    opacity: 0.85;
  }
}

.game-controls-ui {
  position: absolute;
  bottom: 96px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 200;
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

  &:active {
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

.game-over-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at top, rgba(15, 23, 42, 0.7), rgba(15, 23, 42, 0.95));
  z-index: 400;
  padding: 24px;
}

.game-over-card {
  width: 100%;
  max-width: 360px;
  border-radius: 24px;
  padding: 24px 20px 20px;
  background: radial-gradient(circle at top, rgba(30, 64, 175, 0.35), rgba(15, 23, 42, 0.95));
  border: 1px solid rgba(148, 163, 184, 0.35);
  box-shadow:
    0 18px 45px rgba(15, 23, 42, 0.9),
    0 0 0 1px rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(20px);
  color: #e5e7eb;
  text-align: center;
}

.game-over-title {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 8px;
}

.game-over-subtitle {
  font-size: 14px;
  color: #9ca3af;
  margin-bottom: 20px;
}

.game-over-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
