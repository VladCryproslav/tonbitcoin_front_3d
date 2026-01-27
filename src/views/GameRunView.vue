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

    <!-- Управление -->
    <GameControls
      @swipe-left="handleSwipeLeft"
      @swipe-right="handleSwipeRight"
      @swipe-up="handleSwipeUp"
      @swipe-down="handleSwipeDown"
    />

    <!-- Кнопка паузы/старта -->
    <div class="game-controls-ui">
      <button
        v-if="!gameRun.isRunning"
        class="btn-start"
        @click.stop.prevent="startGame"
        @touchstart.stop.prevent="startGame"
      >
        {{ t('game.start') }}
      </button>
      <button 
        v-else-if="gameRun.isPaused"
        class="btn-resume"
        @click.stop.prevent="resumeGame"
        @touchstart.stop.prevent="resumeGame"
      >
        {{ t('game.start') }}
      </button>
      <button
        v-else
        class="btn-pause"
        @click="pauseGame"
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
  // При открытом лаунчере показываем стоячую анимацию из standing.glb
  gamePhysics.value.createPlayer(scene, '/models/standing.glb')

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
      mesh.position.set(0, 0, 0)
      gamePhysics.value.playerPosition.value.set(0, 0, 0)
      gamePhysics.value.playerLane.value = 1
    }
  }
  gameRun.startRun()
  // При старте забега переключаемся на модель с анимацией бега
  if (gamePhysics.value?.loadPlayerModel) {
    gamePhysics.value.loadPlayerModel(scene, '/models/running.glb')
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

const startGameLoop = () => {
  if (gameLoop) return

  const update = () => {
    if (!gameRun.isRunning || gameRun.isPaused) {
      gameLoop = null
      return
    }

    const deltaTime = 0.016 // ~60 FPS

    // Обновление дистанции
    playerZ.value += gameSpeed.value
    gameRun.updateDistance(gameRun.distance + gameSpeed.value * 10)

    // Обновление игрока (позиции и коллизии)
    if (gamePhysics.value) {
      const playerY = gamePhysics.value.getPlayerY()
      const playerX = gamePhysics.value.playerPosition.value.x

      // Обновление мира
      if (gameWorld.value) {
        // Синхронизируем скорость дороги с игровой скоростью
        gameWorld.value.setRoadSpeed(gameSpeed.value)

        gameWorld.value.updateRoad(playerZ.value)
        gameWorld.value.spawnObjects(playerZ.value)

        // Обновление препятствий и проверка коллизий
        gameWorld.value.updateObstacles(
          playerZ.value,
          playerX,
          playerY,
          () => {
            // Коллизия с препятствием
            gameRun.hitObstacle()
            const newPower = gameRun.currentPower - 10
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
              endGame()
            }
          }
        )

        // Обновление собираемых предметов
        gameWorld.value.updateCollectibles(
          playerZ.value,
          playerX,
          playerY,
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
      const targetX = gamePhysics.value.playerPosition.value.x * 0.3
      camera.position.x += (targetX - camera.position.x) * 0.1

      // Небольшое покачивание камеры для динамики
      const cameraBob = Math.sin(Date.now() * 0.003) * 0.1
      camera.position.y = 4 + cameraBob

      // Камера следит за игроком
      const lookAtX = gamePhysics.value.playerPosition.value.x * 0.2
      camera.lookAt(lookAtX, 1 + cameraBob * 0.5, 0)
    }

    // Увеличение скорости со временем
    const distanceCheck = Math.floor(gameRun.distance / 100)
    if (distanceCheck > 0 && distanceCheck !== lastSpeedIncrease.value) {
      lastSpeedIncrease.value = distanceCheck
      gameSpeed.value = Math.min(gameSpeed.value + 0.01, 0.4)
    }

    // Проверка условий окончания забега
    if (gameRun.currentPower <= 0) {
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

  const result = await gameRun.completeRun()

  if (result && result.success) {
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
  if (gameRun.isRunning) {
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
