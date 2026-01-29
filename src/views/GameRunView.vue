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
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Vector3 } from 'three'
import GameScene from '@/components/game/GameScene.vue'
import GameUI from '@/components/game/GameUI.vue'
import GameControls from '@/components/game/GameControls.vue'
import RunCompleteModal from '@/components/game/RunCompleteModal.vue'
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

let gameLoop = null
let threeLoop = null
const gameSpeed = ref(0.15)
const playerZ = ref(0)
const lastSpeedIncrease = ref(0)
const hitCount = ref(0)

const onSceneReady = ({ scene: threeScene, camera: threeCamera, renderer: threeRenderer }) => {
  scene = threeScene
  camera = threeCamera
  renderer = threeRenderer

  // Настройка камеры для раннера: ниже, ближе, персонаж ближе к нижнему краю кадра
  camera.position.set(0, 2.5, 5.5)
  camera.lookAt(0, 0.2, 0)

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
}

const startThreeLoop = () => {
  const animate = () => {
    threeLoop = requestAnimationFrame(animate)
    if (renderer && scene && camera) {
      renderer.render(scene, camera)
    }
    // Обновляем анимации игрока (standing/running) каждый кадр
    if (gamePhysics.value) {
      gamePhysics.value.update()
    }
  }
  animate()
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
    const mesh = gamePhysics.value.playerMesh()
    if (mesh) {
      // Сбрасываем позицию меша
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
  }
  gameRun.startRun()
  hitCount.value = 0
  showGameOver.value = false
  launcherOverlayMode.value = 'none'
  // При старте забега переключаемся на анимацию бега
  if (gamePhysics.value?.setAnimationState) {
    gamePhysics.value.setAnimationState('running')
  }
  startGameLoop()
}

const pauseGame = () => {
  gameRun.pauseRun()
  stopGameLoop()
  launcherOverlayMode.value = 'pause'
}

const resumeGame = () => {
  gameRun.resumeRun()
  startGameLoop()
  launcherOverlayMode.value = 'none'
}

// Унифицированный обработчик для кнопки:
// - если ещё не запущено — старт;
// - если идёт забег — пауза;
// - если стоит на паузе — продолжение.
const togglePlayPause = () => {
  if (!gameRun.isRunning.value) {
    startGame()
  } else if (gameRun.isPaused.value) {
    resumeGame()
  } else {
    pauseGame()
  }
}

const startGameLoop = () => {
  if (gameLoop) return

  const update = () => {
    if (!gameRun.isRunning.value || gameRun.isPaused.value) {
      gameLoop = null
      return
    }

    const deltaTime = 0.016 // ~60 FPS

    // Обновление дистанции
    playerZ.value += gameSpeed.value
    gameRun.updateDistance(gameRun.distance.value + gameSpeed.value * 10)

    // Обновление игрока (позиции и коллизии)
    if (gamePhysics.value) {
      const playerY = gamePhysics.value.getPlayerY()
      // Защита от ситуаций, когда playerPosition или его value ещё не инициализированы
      const playerPosRef = gamePhysics.value.playerPosition
      const playerX = (playerPosRef && playerPosRef.value)
        ? playerPosRef.value.x
        : 0

      // Обновление мира
      if (gameWorld.value) {
        // Синхронизируем скорость дороги с игровой скоростью
        gameWorld.value.setRoadSpeed(gameSpeed.value)

        gameWorld.value.updateRoad(playerZ.value)
        gameWorld.value.spawnObjects(playerZ.value)

        // Реальный AABB игрока для точной коллизии (без привязки к индексам полос).
        const playerBox = gamePhysics.value.getPlayerBox
          ? gamePhysics.value.getPlayerBox()
          : null

        // Обновление препятствий и проверка коллизий
        gameWorld.value.updateObstacles(
          playerBox,
          (hitObstacle) => {
            // Коллизия с препятствием
            hitCount.value += 1
            gameRun.hitObstacle()
            const newPower = gameRun.currentPower.value - 10
            app.setPower(Math.max(0, newPower))

            // Эффект частиц при столкновении
            if (gameEffects.value) {
              gameEffects.value.createCollisionEffect(new Vector3(playerX, playerY, playerZ.value))
            }

            // Эффект тряски камеры при столкновении
            if (camera) {
              const originalX = camera.position.x
              const originalY = camera.position.y
              let shakeCount = 0
              const shake = () => {
                if (shakeCount < 10) {
                  camera.position.x = originalX + (Math.random() - 0.5) * 0.3
                  camera.position.y = originalY + (Math.random() - 0.5) * 0.3
                  shakeCount++
                  requestAnimationFrame(shake)
                } else {
                  camera.position.x = originalX
                  camera.position.y = originalY
                }
              }
              shake()
            }
          }
        )

        // Обновление собираемых предметов
        gameWorld.value.updateCollectibles(
          playerBox,
          (energy) => {
            gameRun.collectEnergy(energy)
            // Визуальный эффект при сборе
            if (gameEffects.value) {
              gameEffects.value.createEnergyCollectEffect(new Vector3(playerX, playerY, playerZ.value))
            }
          }
        )

        // Обновление эффектов
        if (gameEffects.value) {
          gameEffects.value.updateEffects()
        }
      }
    }

    // Камера плавно следует за персонажем по горизонтали (при смене полосы)
    if (camera && gamePhysics.value) {
      const playerPosRef = gamePhysics.value.playerPosition
      const baseX = (playerPosRef && playerPosRef.value)
        ? playerPosRef.value.x
        : 0
      const followFactor = 0.6
      const targetCamX = baseX * followFactor
      const smooth = 0.07
      camera.position.x += (targetCamX - camera.position.x) * smooth

      const cameraBob = Math.sin(Date.now() * 0.003) * 0.08
      camera.position.y = 2.5 + cameraBob

      const lookAtX = baseX * 0.55
      camera.lookAt(lookAtX, 0.2 + cameraBob * 0.5, 0)
    }

    // Увеличение скорости со временем (ещё медленнее)
    const distanceCheck = Math.floor(gameRun.distance.value / 200)
    if (distanceCheck > 0 && distanceCheck !== lastSpeedIncrease.value) {
      lastSpeedIncrease.value = distanceCheck
      gameSpeed.value = Math.min(gameSpeed.value + 0.003, 0.32)
    }

    // Проверка условий окончания забега:
    // персонажу даётся 3 удара по препятствиям, на третьем забег останавливается.
    if (hitCount.value >= 3) {
      if (gameWorld.value) {
        gameWorld.value.setRoadSpeed(0)
      }
      gameSpeed.value = 0
      if (gamePhysics.value?.setAnimationState) {
        gamePhysics.value.setAnimationState('fall')
      }

      // Даём анимации падения отыграть, затем показываем модалку и завершаем забег.
      setTimeout(() => {
        gameOverType.value = 'lose'
        showGameOver.value = true
        launcherOverlayMode.value = 'none'
        endGame(false)
      }, 1000)
      return
    }

    // Автоматическое завершение при достижении максимальной дистанции (опционально)
    // if (gameRun.distance >= 10000) {
    //   endGame()
    //   return
    // }

    gameLoop = requestAnimationFrame(update)
  }

  gameLoop = requestAnimationFrame(update)
}

const stopGameLoop = () => {
  if (gameLoop) {
    cancelAnimationFrame(gameLoop)
    gameLoop = null
  }
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

onMounted(() => {
  // Инициализация при монтировании
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
