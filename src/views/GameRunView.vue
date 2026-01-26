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
        @click="startGame"
      >
        {{ t('game.start') }}
      </button>
      <button 
        v-else-if="gameRun.isPaused"
        class="btn-resume"
        @click="resumeGame"
      >
        {{ t('game.resume') }}
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
import GameScene from '@/components/game/GameScene.vue'
import GameUI from '@/components/game/GameUI.vue'
import GameControls from '@/components/game/GameControls.vue'
import RunCompleteModal from '@/components/game/RunCompleteModal.vue'
import { useGameRun } from '@/composables/useGameRun'
import { useGamePhysics } from '@/composables/useGamePhysics'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const { t } = useI18n()
const app = useAppStore()

const gameSceneRef = ref(null)
const gameRun = useGameRun()
const gamePhysics = ref(null)
const showResults = ref(false)
const runResults = ref({
  distance: 0,
  energyCollected: 0,
  energyGained: 0,
  bonuses: null
})

let gameLoop = null
let speed = 0.1

const onSceneReady = ({ scene, camera, renderer }) => {
  // Инициализация физики после готовности сцены
  gamePhysics.value = useGamePhysics(scene)
  
  // Здесь можно добавить создание дорожки, препятствий и т.д.
  setupGameScene(scene)
}

const setupGameScene = (scene) => {
  // Базовая настройка сцены
  // TODO: Добавить дорожку, препятствия, собираемые предметы
}

const startGame = () => {
  gameRun.startRun()
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
    
    // Обновление дистанции
    gameRun.updateDistance(gameRun.distance + speed)
    
    // Обновление позиции игрока
    if (gamePhysics.value) {
      // TODO: Обновление позиции игрока в 3D сцене
    }
    
    // Проверка условий окончания забега
    if (gameRun.currentPower <= 0) {
      endGame()
      return
    }
    
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
  router.push('/')
}

onMounted(() => {
  // Инициализация при монтировании
})

onUnmounted(() => {
  stopGameLoop()
  if (gameRun.isRunning) {
    gameRun.stopRun()
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
