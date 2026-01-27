<template>
  <div class="game-run-view">
    <!-- Three.js сцена -->
    <GameScene
      ref="gameSceneRef"
      @scene-ready="onSceneReady"
    />

    <!-- UI поверх игры -->
    <GameUI
      :energy="gameRun.energyCollected"
      :distance="gameRun.distance"
      :power="gameRun.currentPower"
    />

    <!-- Управление (свайпы + тап для старта на мобильных) -->
    <GameControls
      @swipe-left="handleSwipeLeft"
      @swipe-right="handleSwipeRight"
      @swipe-up="handleSwipeUp"
      @swipe-down="handleSwipeDown"
      @tap="handleTap"
    />

    <!-- Кнопка старта/паузы (главное управление игрой) -->
    <div class="game-controls-ui">
      <button
        v-if="!gameRun.isRunning"
        class="btn-start"
        @click.stop.prevent="togglePlayPause"
        @touchstart.stop.prevent="togglePlayPause"
      >
        {{ t('game.start') }}
      </button>
      <button 
        v-else-if="gameRun.isPaused"
        class="btn-resume"
        @click.stop.prevent="togglePlayPause"
        @touchstart.stop.prevent="togglePlayPause"
      >
        {{ t('game.start') }}
      </button>
      <button
        v-else
        class="btn-pause"
        @click.stop.prevent="togglePlayPause"
        @touchstart.stop.prevent="togglePlayPause"
      >
        {{ t('game.pause') }}
      </button>
    </div>

    <!-- Модалка результатов -->
    <RunCompleteModal
      :visible="showResults"
      :results="runResults"
      @close="handleRunComplete"
    />
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
const showResults = ref(false)
const runResults = ref({
  distance: 0,
  energyCollected: 0,
  energyGained: 0,
  bonuses: null
})

let gameLoop = null
let threeLoop = null
const gameSpeed = ref(0.15)
const playerZ = ref(0)
const lastSpeedIncrease = ref(0)

const onSceneReady = ({ scene: threeScene, camera: threeCamera, renderer: threeRenderer }) => {
  scene = threeScene
  camera = threeCamera
  renderer = threeRenderer

  // Настройка камеры для раннера
  camera.position.set(0, 4, 8)
  camera.lookAt(0, 1, 0)

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
  // При старте забега переключаемся на анимацию бега
  if (gamePhysics.value?.setAnimationState) {
    gamePhysics.value.setAnimationState('running')
  }
  startGameLoop()
}

const pauseGame = () => {
  gameRun.pauseRun()
  stopGameLoop()
}

const resumeGame = () => {
  gameRun.resumeRun()
  startGameLoop()
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
          () => {
            // Коллизия с препятствием
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

            if (newPower <= 0) {
              if (gamePhysics.value?.setAnimationState) {
                gamePhysics.value.setAnimationState('fall')
              }
              endGame()
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

    // Плавное движение камеры за игроком
    if (camera && gamePhysics.value) {
      const playerPosRef = gamePhysics.value.playerPosition
      const baseX = (playerPosRef && playerPosRef.value)
        ? playerPosRef.value.x
        : 0
      const targetX = baseX * 0.3
      camera.position.x += (targetX - camera.position.x) * 0.1

      // Небольшое покачивание камеры для динамики
      const cameraBob = Math.sin(Date.now() * 0.003) * 0.1
      camera.position.y = 4 + cameraBob

      // Камера следит за игроком
      const lookAtX = baseX * 0.2
      camera.lookAt(lookAtX, 1 + cameraBob * 0.5, 0)
    }

    // Увеличение скорости со временем (чуть медленнее)
    const distanceCheck = Math.floor(gameRun.distance.value / 120)
    if (distanceCheck > 0 && distanceCheck !== lastSpeedIncrease.value) {
      lastSpeedIncrease.value = distanceCheck
      gameSpeed.value = Math.min(gameSpeed.value + 0.006, 0.38)
    }

    // Проверка условий окончания забега
    if (gameRun.currentPower.value <= 0) {
      if (gamePhysics.value?.setAnimationState) {
        gamePhysics.value.setAnimationState('fall')
      }
      endGame()
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

const endGame = async () => {
  stopGameLoop()

  // Возвращаем стоячую анимацию
  if (gamePhysics.value?.setAnimationState) {
    gamePhysics.value.setAnimationState('standing')
  }

  const result = await gameRun.completeRun()

  if (result && result.success) {
    // Успешное завершение забега — проигрываем победную анимацию
    if (gamePhysics.value?.setAnimationState) {
      gamePhysics.value.setAnimationState('win')
    }
    runResults.value = {
      distance: gameRun.distance,
      energyCollected: gameRun.energyCollected,
      energyGained: result.energyGained,
      bonuses: result.bonuses
    }
    showResults.value = true
  } else {
    // Обработка ошибки
    console.error('Ошибка завершения забега:', result?.error)
  }
}

const handleSwipeLeft = () => {
  if (gamePhysics.value) {
    gamePhysics.value.moveLeft()
  }
}

const handleSwipeRight = () => {
  if (gamePhysics.value) {
    gamePhysics.value.moveRight()
  }
}

const handleSwipeUp = () => {
  if (gamePhysics.value) {
    gamePhysics.value.jump()
  }
}

const handleSwipeDown = () => {
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

const handleRunComplete = () => {
  showResults.value = false
  // Небольшая задержка перед возвратом для плавности
  setTimeout(() => {
    router.push('/')
  }, 300)
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
  width: 100%;
  height: 100vh;
  position: relative;
  overflow: hidden;
  background: #000;
}

.game-controls-ui {
  position: absolute;
  bottom: 100px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 200;
}

.btn-start,
.btn-resume,
.btn-pause {
  background: #8143FC;
  color: #fff;
  border: none;
  padding: 14px 28px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(129, 67, 252, 0.4);
  transition: all 0.2s;

  &:active {
    transform: scale(0.95);
    opacity: 0.8;
  }
}

.btn-pause {
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
}
</style>
