<template>
  <div class="game-run-view">
    <!-- Three.js сцена -->
    <GameScene
      ref="gameSceneRef"
      :graphics-quality="graphicsQuality"
      @scene-ready="onSceneReady"
    />

    <!-- UI поверх игры: только после старта забега -->
    <GameUI
      v-if="gameRun.isRunning || gameRun.isPaused"
      :energy="Math.min(gameRun.energyCollected?.value ?? 0, gameRun.startStorage?.value ?? gameRun.currentStorage?.value ?? 0)"
      :max-energy="gameRun.startStorage?.value ?? gameRun.currentStorage?.value ?? 0"
      :power="overheatCountdown !== null ? null : gameRun.distanceProgress?.value ?? 0"
      :overheat-countdown="overheatCountdown"
      :lives="livesLeft"
      :max-lives="MAX_LIVES"
      :compact-distance="controlMode === 'buttons'"
      :show-pause="gameRun.isRunning && !gameRun.isPaused && !showGameOver"
      :is-cryo-active="app.user?.cryo_expires && new Date(app.user.cryo_expires) > new Date()"
      @pause="openPauseOverlay"
    />

    <!-- Управление (свайпы + тап для старта на мобильных) -->
    <GameControls
      v-if="controlMode === 'swipes'"
      @swipe-left="handleSwipeLeft"
      @swipe-right="handleSwipeRight"
      @swipe-up="handleSwipeUp"
      @swipe-down="handleSwipeDown"
      @tap="handleTap"
    />

    <!-- Виртуальные кнопки управления -->
    <VirtualControls
      v-if="controlMode === 'buttons' && (gameRun.isRunning || gameRun.isPaused)"
      @swipe-left="handleSwipeLeft"
      @swipe-right="handleSwipeRight"
      @swipe-up="handleSwipeUp"
      @swipe-down="handleSwipeDown"
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
            class="btn-primary btn-primary--training btn-primary--wide"
            @click.stop.prevent="handleTrainingClick"
          >
            {{ t('game.run_training') }}
          </button>
          <button
            class="btn-primary btn-secondary btn-primary--wide"
            @click.stop.prevent="openSettings"
          >
            {{ t('game.settings') }}
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

    <!-- Оверлей настроек -->
    <div
      v-if="launcherOverlayMode === 'settings' && !showGameOver"
      class="game-over-overlay"
    >
      <div class="game-over-card">
        <div class="game-over-title">
          {{ t('game.settings') }}
        </div>
        <div class="game-over-actions">
          <button
            class="btn-primary btn-secondary btn-primary--wide"
            @click.stop.prevent="toggleGraphicsQuality"
          >
            {{ graphicsLabel }}
          </button>
          <button
            class="btn-primary btn-secondary btn-primary--wide"
            @click.stop.prevent="toggleVibration"
          >
            {{ vibrationLabel }}
          </button>
          <button
            class="btn-primary btn-secondary btn-primary--wide"
            @click.stop.prevent="toggleHitFlash"
          >
            {{ hitFlashLabel }}
          </button>
          <button
            class="btn-primary btn-secondary btn-primary--wide"
            @click.stop.prevent="toggleControlMode"
          >
            {{ controlModeLabel }}
          </button>
          <button
            class="btn-primary btn-secondary btn-primary--wide"
            @click.stop.prevent="closeSettings"
          >
            {{ t('game.back') }}
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
            :class="{ 'btn-disabled': !isTrainingRun }"
            :disabled="!isTrainingRun"
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
        <div class="game-over-results">
          <div class="game-over-result-row">
            <img src="@/assets/kW.png" alt="" class="game-over-result-icon" />
            <span class="game-over-result-label">{{ t('game.run_result_collected') }}</span>
            <span class="game-over-result-value">{{ formatEnergy(displayedEnergyCollected, true) }} / {{ formatEnergy(gameRun.startStorage?.value ?? gameRun.currentStorage?.value ?? 0) }} kW</span>
          </div>
          <div v-if="gameOverType !== 'win'" class="game-over-result-row">
            <img src="@/assets/engineer.webp" alt="" class="game-over-result-icon" />
            <span class="game-over-result-label">{{ t('game.run_result_saved_by_level', { level: whiteEngineerLevel }) }}</span>
            <span class="game-over-result-value">{{ formatPercent(whiteEngineerSavedPercent) }}</span>
          </div>
          <div v-if="gameOverType !== 'win' && goldEngineerLevel" class="game-over-result-row">
            <img src="@/assets/gold.webp" alt="" class="game-over-result-icon" />
            <span class="game-over-result-label">{{ t('game.run_result_saved_by_level', { level: goldEngineerLevel }) }}</span>
            <span class="game-over-result-value">{{ formatPercent(goldEngineerBonusPercent) }}</span>
          </div>
          <div v-if="gameOverType !== 'win'" class="game-over-result-row">
            <img src="@/assets/save.webp" alt="" class="game-over-result-icon" />
            <span class="game-over-result-label">{{ t('game.run_result_saved_total') }}</span>
            <span class="game-over-result-value">{{ formatPercent(effectiveSavedPercentOnLose) }}</span>
          </div>
          <div class="game-over-result-row">
            <img src="@/assets/kW.png" alt="" class="game-over-result-icon" />
            <span class="game-over-result-label">{{ t('game.run_result_for_claim') }}</span>
            <span class="game-over-result-value">{{ formatEnergy(claimableEnergy) }} kW</span>
          </div>
        </div>
        <div class="game-over-actions">
          <button
            v-if="!isTrainingRun"
            class="btn-primary btn-primary--wide"
            @click.stop.prevent="handleClaim"
          >
            {{ t('game.run_claim') }}
          </button>
          <button
            v-else
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

    <!-- Красная вспышка по краям экрана при ударе (CSS-анимация, без JS-таймеров) -->
    <div
      v-if="hitFlashEnabled && hitFlashTick"
      :key="hitFlashTick"
      class="hit-flash-overlay"
    />
    
    <!-- Модальное окно перегрева -->
    <OverheatGameRunModal
      v-if="showOverheatModal"
      :overheated-until="overheatedUntil"
      @continue="handleOverheatContinue"
      @close="handleOverheatModalClose"
    />
    
    <!-- Пульсация экрана красным цветом во время перегрева -->
    <div
      v-if="isOverheated && showOverheatModal"
      class="overheat-screen-pulse"
    />
    
    <!-- Таймер обратного отсчета перед началом забега -->
    <div
      v-if="showCountdown"
      class="countdown-overlay"
    >
      <div class="countdown-number">{{ countdownNumber }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import GameScene from '@/components/game/GameScene.vue'
import GameUI from '@/components/game/GameUI.vue'
import GameControls from '@/components/game/GameControls.vue'
import VirtualControls from '@/components/game/VirtualControls.vue'
import InfoModal from '@/components/InfoModal.vue'
import OverheatGameRunModal from '@/components/OverheatGameRunModal.vue'
import { useGameRun } from '@/composables/useGameRun'
import { useGamePhysics } from '@/composables/useGamePhysics'
import { useGameWorld } from '@/composables/useGameWorld'
import { useGameEffects } from '@/composables/useGameEffects'
import { useAppStore } from '@/stores/app'
import { host } from '@/../axios.config'

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
// Тренировочный забег: та же логика, в конце не начисляем энергию (только «Вернуться назад»)
const isTrainingRun = ref(false)
// Данные завершенного забега для начисления при нажатии "Забрать"
const completedRunData = ref(null) // { energy_collected, is_win, energy_gained }
// Сохраненное значение собранной энергии для отображения в модалке (не обнуляется до нажатия "Забрать")
const savedEnergyCollectedForModal = ref(0)
// Та же логика уровней, что в EnergizerView: 49 белых, остаток — золотые
const getWorkers = computed(() => {
  const simple = Math.min(app?.user?.engineer_level ?? 0, 49) || 0
  const gold = (app?.user?.past_engineer_level ?? 0) > 49 ? app.user.past_engineer_level - 49 : 0
  return { simple, gold, all: simple + gold }
})

const whiteEngineerLevel = computed(() => getWorkers.value.simple)
const goldEngineerLevel = computed(() => getWorkers.value.gold)

// Процент сохранения при проигрыше из eng_configs (saved_percent_on_lose)
const whiteEngineerSavedPercent = computed(() => {
  const level = getWorkers.value.simple
  if (!level) return 0
  const cfg = app.stations?.eng_configs?.find((el) => el?.level === level)
  return Number(cfg?.saved_percent_on_lose ?? 0)
})
const goldEngineerSavedPercent = computed(() => {
  const level = getWorkers.value.all
  if (level < 50) return 0
  const cfg = app.stations?.eng_configs?.find((el) => el?.level === level)
  return Number(cfg?.saved_percent_on_lose ?? 0)
})
// Бонус золотого над белым: напр. 62% − 49% = 13%
const goldEngineerBonusPercent = computed(() => {
  const gold = goldEngineerSavedPercent.value
  const white = whiteEngineerSavedPercent.value
  return Math.max(0, gold - white)
})
// Эффективный процент при проигрыше — по суммарному уровню (all)
const effectiveSavedPercentOnLose = computed(() => {
  const level = getWorkers.value.all
  if (!level) return 0
  const cfg = app.stations?.eng_configs?.find((el) => el?.level === level)
  return Number(cfg?.saved_percent_on_lose ?? 0)
})
// Вычисляем собранную энергию для отображения в модалке - используем ту же логику, что и в счетчике энергии
const displayedEnergyCollected = computed(() => {
  // Если модалка показана, всегда используем сохраненное значение
  // Это гарантирует, что значение не изменится после показа модалки
  if (showGameOver.value) {
    // КРИТИЧЕСКИ ВАЖНО: При проигрыше приоритет у сохраненного значения при смерти
    // Это значение было сохранено до любых изменений состояния и является самым надежным
    const savedValue = savedEnergyCollectedForModal.value
    console.log('displayedEnergyCollected COMPUTED: showGameOver=true, savedValue=', savedValue, 'completedRunData.value=', completedRunData.value, 'completedRunData.value?.energy_collected=', completedRunData.value?.energy_collected)
    
    if (savedValue > 0) {
      console.log('displayedEnergyCollected: Using savedEnergyCollectedForModal =', savedValue, '(saved at death)')
      return savedValue
    }
    
    // Приоритет 2: Используем значение из completedRunData если оно есть и больше 0
    // Если сервер вернул 0, это может быть ошибка, поэтому мы уже проверили сохраненное значение выше
    if (completedRunData.value?.energy_collected !== undefined && 
        completedRunData.value?.energy_collected !== null &&
        completedRunData.value.energy_collected > 0) {
      const value = completedRunData.value.energy_collected
      console.log('displayedEnergyCollected: Using completedRunData.energy_collected =', value)
      return value
    }
    
    // Приоритет 3: Fallback - используем значение из completedRunData даже если оно 0
    // (может быть валидным случаем, если игрок действительно не собрал энергию)
    if (completedRunData.value?.energy_collected !== undefined && 
        completedRunData.value?.energy_collected !== null) {
      const value = completedRunData.value.energy_collected
      console.log('displayedEnergyCollected: Using completedRunData.energy_collected (fallback, value=', value, ')')
      return value
    }
    
    // Приоритет 4: Последний fallback - текущее значение из счетчика (может быть 0, если уже обнулено)
    const currentValue = Math.min(gameRun.energyCollected?.value ?? 0, gameRun.startStorage?.value ?? gameRun.currentStorage?.value ?? 0)
    console.log('displayedEnergyCollected: Using current value from gameRun =', currentValue, '(fallback, savedValue=', savedValue, ')')
    return currentValue
  }
  // Во время забега используем значение из счетчика энергии (та же логика, что в GameUI)
  return Math.min(gameRun.energyCollected?.value ?? 0, gameRun.startStorage?.value ?? gameRun.currentStorage?.value ?? 0)
})

// Сколько энергии можно забрать: при победе — всё собранное (но не больше storage), при проигрыше — по проценту уровня
const claimableEnergy = computed(() => {
  const collected = displayedEnergyCollected.value
  
  // При выигрыше всегда начисляется вся собранная энергия
  if (gameOverType.value === 'win') {
    // Используем данные с сервера если они есть и больше 0, иначе используем собранное значение
    if (completedRunData.value?.energy_gained !== undefined && completedRunData.value.energy_gained > 0) {
      return completedRunData.value.energy_gained
    }
    // Fallback: при выигрыше начисляется всё собранное
    return collected
  }
  
  // При проигрыше используем данные с сервера или вычисляем на фронтенде
  if (completedRunData.value?.energy_gained !== undefined && completedRunData.value.energy_gained > 0) {
    return completedRunData.value.energy_gained
  }
  
  // Fallback: вычисляем на фронтенде для проигрыша
  const pct = effectiveSavedPercentOnLose.value
  // Добавляем +2% если есть активные синие электрики
  const electricsBonus = (app?.user?.electrics_expires && new Date(app.user.electrics_expires) > new Date()) ? 2 : 0
  return (collected * (pct + electricsBonus)) / 100
})

const formatEnergy = (value, compareWithStorage = false) => {
  const v = Number(value ?? 0)
  if (!Number.isFinite(v)) {
    console.log('formatEnergy: value is not finite, value=', value, 'returning "0"')
    return '0'
  }

  // Если нужно сравнить со storage и значение >= storage, показываем storage (точное значение)
  // Используем startStorage если currentStorage обнулен (при показе модалки)
  const storageValue = gameRun.startStorage?.value ?? gameRun.currentStorage?.value ?? 0
  if (compareWithStorage && storageValue > 0) {
    const storage = Number(storageValue)
    if (v >= storage) {
      // Показываем storage с точностью до 1 знака после запятой (если есть дробная часть)
      const result = storage % 1 === 0 ? storage.toString() : storage.toFixed(1)
      console.log('formatEnergy: compareWithStorage=true, v >= storage, v=', v, 'storage=', storage, 'returning', result)
      return result
    }
  }

  // Иначе показываем точное значение с одним знаком после запятой (если есть дробная часть)
  const result = v % 1 === 0 ? v.toString() : v.toFixed(1)
  if (showGameOver.value) {
    console.log('formatEnergy: showGameOver=true, value=', value, 'v=', v, 'compareWithStorage=', compareWithStorage, 'storageValue=', storageValue, 'returning', result)
  }
  return result
}

const formatPercent = (value) => {
  const v = Number(value ?? 0)
  return Number.isFinite(v) ? `${v.toFixed(1)}%` : '0.0%'
}

// Режим оверлея лаунчера: старт до забега или пауза.
// 'idle' — до первого старта, 'pause' — пауза, 'none' — нет оверлея.
const launcherOverlayMode = ref('idle')

// Состояние перегрева
const showOverheatModal = ref(false)
const overheatedUntil = ref(null)
const isOverheated = ref(false)
let overheatCheckInterval = null
const overheatEnergyCollected = ref(0)
const overheatGoal = ref(null)
const wasOverheated = ref(false)
const overheatCountdown = ref(null) // Обратный отсчет перед показом модалки (5, 4, 3, 2, 1)
let overheatCountdownInterval = null
const overheatDecelerating = ref(false) // Флаг плавной остановки при перегреве (с 3 до 1 секунды)

// Таймер обратного отсчета перед началом забега
const showCountdown = ref(false)
const countdownNumber = ref(3)
let countdownInterval = null

// Конфигурация перегревов по типам станций
const OVERHEAT_HOURS_BY_TYPE = {
  "Thermal power plant": 4,        // station #3 - 6 перегревов в сутки
  "Geothermal power plant": 2,     // station #4 - 12 перегревов в сутки
  "Nuclear power plant": 2,       // station #5 - 12 перегревов в сутки
  "Thermonuclear power plant": 1,  // station #6 - 24 перегрева в сутки
  "Dyson Sphere": 1,               // station #7 - 24 перегрева в сутки
}

let threeLoop = null
let lastUpdateTime = 0
let shakeFramesLeft = 0
let shakeBaseX = 0
let shakeBaseY = 0
const SHAKE_DURATION_FRAMES = 10
const hitFlashTick = ref(0)
const FIXED_STEP_MS = 1000 / 60
const MAX_STEPS = 3
const ROLL_IMMUNE_MS = 950
const gameSpeed = ref(0.15)
const playerZ = ref(0)
const hitCount = ref(0)
const MAX_LIVES = 3
const livesLeft = computed(() => Math.max(0, MAX_LIVES - hitCount.value))
const isDead = ref(false)
let winTriggered = false
let winDecelerating = false
let winAnimationStartTime = 0
let obstaclesHidden = false
const WIN_DECEL_RATE = 0.88
const WIN_SPEED_THRESHOLD = 0.04
const WIN_ANIMATION_DURATION_MS = 1700

// Адаптивный DPR: целевое и текущее значение, регулируем по средней длительности кадра
let targetPixelRatio = 1
let minPixelRatio = 1
let dynamicPixelRatio = 1
let frameTimeEMA = 16.7
let dprAdjustCounter = 0

// Настройки графики: normal | medium | low. Читаем из localStorage синхронно — GameScene нужен при первом рендере.
const isWeakDevice = ref(false)
const graphicsQuality = ref('normal')
const vibrationEnabled = ref(true)
const hitFlashEnabled = ref(true)
const controlMode = ref('swipes') // 'swipes' | 'buttons'
if (typeof window !== 'undefined') {
  try {
    const saved = window.localStorage?.getItem('game_graphics_quality')
    if (['normal', 'medium', 'low'].includes(saved)) graphicsQuality.value = saved
    const vib = window.localStorage?.getItem('game_vibration_enabled')
    if (vib === '0') vibrationEnabled.value = false
    const flash = window.localStorage?.getItem('game_hit_flash_enabled')
    if (flash === '0') hitFlashEnabled.value = false
    const control = window.localStorage?.getItem('game_control_mode')
    if (['swipes', 'buttons'].includes(control)) controlMode.value = control
  } catch {
    // ignore
  }
}
const showGraphicsInfoModal = ref(false)
const pendingGraphicsQuality = ref(null)

const graphicsLabels = {
  normal: 'game.graphics_label_normal',
  medium: 'game.graphics_label_medium',
  low: 'game.graphics_label_low'
}
const graphicsLabel = computed(() => t(graphicsLabels[graphicsQuality.value] || graphicsLabels.normal))
const vibrationLabel = computed(() => (vibrationEnabled.value ? t('game.vibration_on') : t('game.vibration_off')))
const hitFlashLabel = computed(() => (hitFlashEnabled.value ? t('game.hit_flash_on') : t('game.hit_flash_off')))
const controlModeLabel = computed(() => (controlMode.value === 'swipes' ? t('game.control_swipes') : t('game.control_buttons')))

let directionalLight = null

const onSceneReady = async ({ scene: threeScene, camera: threeCamera, renderer: threeRenderer }) => {
  scene = threeScene
  camera = threeCamera
  renderer = threeRenderer
  // Кэшируем directional light один раз — без traverse при каждом applyGraphicsQuality
  directionalLight = threeScene.children.find((obj) => obj.isDirectionalLight) ?? null

  // Настройка камеры:
  // camera.position.set(X, Y, Z)
  //   X: горизонтальная позиция (0 = центр, меняется при смене полосы)
  //   Y: высота камеры (больше = выше) - текущее значение: 2.7
  //   Z: расстояние от персонажа (меньше = ближе к персонажу) - текущее значение: 4.2
  // camera.lookAt(X, Y, Z)
  //   X: горизонтальная точка взгляда (0 = центр, меняется при смене полосы)
  //   Y: вертикальная точка взгляда (меньше = больше вниз на дорогу) - текущее значение: -0.25
  //   Z: дальность взгляда по оси Z - текущее значение: -18
  camera.position.set(0, 2.6, 3.8)
  camera.lookAt(0, -0.25, -18)

  // Инициализация игрового мира
  gameWorld.value = useGameWorld(scene)
  gameWorld.value.createRoad()
  await gameWorld.value.loadBarrierModels()

  // Инициализация физики и создание игрока
  gamePhysics.value = useGamePhysics(scene)
  // Загружаем основную модель с полным набором анимаций (standing/running/jump/roll/fall)
  gamePhysics.value.createPlayer(scene, '/models/main.glb')

  // Инициализация эффектов
  gameEffects.value = useGameEffects(scene, graphicsQuality.value)

  // Запуск рендеринга Three.js
  startThreeLoop()

  applyGraphicsQuality()
}

// Очень плавное следование камеры: без рывков, незаметный дрейф от центра при смене полосы
const CAMERA_SMOOTH_TIME = 0.42 // немного быстрее реакции без рывков (~95% за 0.42 c)
let lastFrameDtSec = 0.016

const startThreeLoop = () => {
  const animate = () => {
    threeLoop = requestAnimationFrame(animate)

    const nowGlobal = performance.now()
    const baseFrameContext = { nowMs: nowGlobal, deltaMs: FIXED_STEP_MS, fixedSteps: 1 }

    // 1) Сначала физика (позиция персонажа, смена полосы) — потом рендер, без кадра задержки
    if (gamePhysics.value) {
      gamePhysics.value.update(baseFrameContext)
    }

    // 2) Игровая логика в том же rAF (фикс. шаг). playerBox один раз за кадр — меньше setFromObject при наборе скорости.
    if (gameRun.isRunning.value && !gameRun.isPaused.value && !isDead.value) {
      const now = nowGlobal
      if (lastUpdateTime <= 0) lastUpdateTime = now
      const frameTime = Math.min(now - lastUpdateTime, 100)
      lastUpdateTime = now
      // EMA по времени кадра для адаптивного DPR
      frameTimeEMA = frameTimeEMA * 0.9 + frameTime * 0.1
      lastFrameDtSec = frameTime / 1000

      const nowMs = now
      const slideStartTime = gamePhysics.value?.getSlideStartTime?.() ?? 0
      const inRollImmuneWindow = slideStartTime > 0 && nowMs - slideStartTime < ROLL_IMMUNE_MS
      const framePlayerBox = gamePhysics.value?.getPlayerBox?.() ?? null
      let stepsCount = Math.floor(frameTime / FIXED_STEP_MS)
      if (stepsCount < 1) stepsCount = 1
      else if (stepsCount > MAX_STEPS) stepsCount = MAX_STEPS
      const frameContext = { nowMs, deltaMs: frameTime, fixedSteps: stepsCount }
      let distanceDelta = 0
      let accumulatedSpeed = 0
      for (let i = 0; i < stepsCount; i++) {
        const s = gameSpeed.value
        accumulatedSpeed += s
        distanceDelta += s * 10
        doOneStep(framePlayerBox, inRollImmuneWindow)
      }
      if (gameWorld.value && accumulatedSpeed !== 0) {
        const avgSpeed = accumulatedSpeed / stepsCount
        gameWorld.value.setRoadSpeed(avgSpeed)
      }
      if (distanceDelta !== 0) {
        gameRun.updateDistance(gameRun.distance.value + distanceDelta)
      }
      if (!winTriggered && !winDecelerating && winAnimationStartTime === 0) {
        // Плавный набор: к 55% дистанции выходим на чуть меньшую макс. скорость (один раз на кадр, не на шаг)
        const progress = (gameRun.distanceProgress?.value ?? 0) / 100
        const maxSpeed = 0.36
        const rampProgress = Math.min(1, progress / 0.55)
        const baseSpeed = 0.15
        const targetSpeed = baseSpeed + (maxSpeed - baseSpeed) * rampProgress
        gameSpeed.value = 0.92 * gameSpeed.value + 0.08 * targetSpeed
      }
      if (gameWorld.value) gameWorld.value.spawnObjects(playerZ.value, gameRun.getNextEnergyPoint)
      if (gameEffects.value) {
        const q = graphicsQuality.value
        if (q === 'normal' || q === 'medium') {
          gameEffects.value.updateEffects(frameContext)
        }
      }
      if (hitCount.value >= 3 && !isDead.value) {
        isDead.value = true
        // Сохраняем energyCollected ДО остановки игрового цикла
        // Ограничиваем значение максимумом storage (та же логика, что в счетчике энергии)
        const savedEnergyBeforeStop = Math.min(
          gameRun.energyCollected?.value ?? 0,
          gameRun.startStorage?.value ?? gameRun.currentStorage?.value ?? 0
        )
        // Сохраняем значение для модалки сразу при смерти
        savedEnergyCollectedForModal.value = savedEnergyBeforeStop
        console.log('Player died: hitCount=', hitCount.value, 'energyCollected BEFORE stop=', savedEnergyBeforeStop, 'startStorage=', gameRun.startStorage?.value, 'savedEnergyCollectedForModal=', savedEnergyCollectedForModal.value)
        
        // НЕ вызываем stopRun() здесь, чтобы не сбросить startStorage и energyCollected
        // Останавливаем только игровой цикл и физику
        stopGameLoop()
        if (gameWorld.value) gameWorld.value.setRoadSpeed(0)
        gameSpeed.value = 0
        // Останавливаем физику персонажа - запускаем анимацию падения
        if (gamePhysics.value?.onFinalHit) {
          gamePhysics.value.onFinalHit()
        } else if (gamePhysics.value?.setAnimationState) {
          gamePhysics.value.setAnimationState('lose')
        }
        // Устанавливаем тип проигрыша, но НЕ показываем модалку сразу
        // Модалка появится после завершения анимации падения в endGame
        gameOverType.value = 'lose'
        launcherOverlayMode.value = 'none'
        
        // Проверяем energyCollected после остановки игрового цикла
        console.log('Player died: energyCollected AFTER stop=', gameRun.energyCollected?.value, 'startStorage=', gameRun.startStorage?.value, 'savedEnergyCollectedForModal=', savedEnergyCollectedForModal.value)
        
        // Вызываем endGame после задержки для завершения анимации падения
        setTimeout(() => {
          console.log('Calling endGame after delay: energyCollected=', gameRun.energyCollected?.value, 'startStorage=', gameRun.startStorage?.value, 'savedEnergyCollectedForModal=', savedEnergyCollectedForModal.value)
          if (!endGame._isProcessing) {
            endGame(false)
          }
        }, 2000) // Увеличиваем задержку до 2 секунд для завершения анимации падения
      }
    }

    // 3) Камера: цель из физики напрямую (не из game loop), плавное следование без качания
    if (camera && gamePhysics.value?.getCameraLaneX) {
      const dt = lastFrameDtSec > 0 ? Math.min(lastFrameDtSec, 0.05) : 0.016
      const laneX = gamePhysics.value.getCameraLaneX()
      const targetCamX = laneX === 0 ? 0 : laneX * 0.95
      const k = -Math.log(0.05) / CAMERA_SMOOTH_TIME
      const t = 1 - Math.exp(-k * dt)
      const desiredStepX = (targetCamX - camera.position.x) * t
      const maxStepX = 0.25
      const clampedStepX = Math.max(-maxStepX, Math.min(maxStepX, desiredStepX))
      camera.position.x += clampedStepX
      // Высота камеры (больше = выше) - текущее значение: 2.7
      camera.position.y = 2.7
      // Точка взгляда: (X, Y, Z)
      //   Y: вертикальная точка взгляда (меньше = больше вниз на дорогу) - текущее значение: -0.25
      //   Z: дальность взгляда по оси Z - текущее значение: -18
      camera.lookAt(camera.position.x, -0.25, -18)
    }
    if (camera && shakeFramesLeft > 0) {
      const t = shakeFramesLeft / SHAKE_DURATION_FRAMES
      const intensity = t * t // плавное затухание
      camera.position.x += shakeBaseX * intensity
      camera.position.y += shakeBaseY * intensity
      shakeFramesLeft--
    }

    // 4) Адаптивный DPR на основе средней длительности кадра (только для normal/medium)
    if (renderer) {
      const q = graphicsQuality.value
      const isLow = q === 'low'
      if (!isLow) {
        if (++dprAdjustCounter >= 30) {
          dprAdjustCounter = 0
          if (frameTimeEMA > 18 && dynamicPixelRatio > minPixelRatio) {
            dynamicPixelRatio = Math.max(minPixelRatio, dynamicPixelRatio - 0.1)
            renderer.setPixelRatio(dynamicPixelRatio)
          } else if (frameTimeEMA < 15 && dynamicPixelRatio < targetPixelRatio) {
            dynamicPixelRatio = Math.min(targetPixelRatio, dynamicPixelRatio + 0.1)
            renderer.setPixelRatio(dynamicPixelRatio)
          }
        }
      }
    }

    // 5) Рендер после обновления позиции и камеры
    if (renderer && scene && camera) {
      renderer.render(scene, camera)
    }
  }
  animate()
}

const applyGraphicsQuality = () => {
  if (!renderer || !scene) return

  const q = graphicsQuality.value
  const isLow = q === 'low'
  const isMedium = q === 'medium'

  // Тени: low — выкл, medium — 1024, normal — 2048
  renderer.shadowMap.enabled = !isLow
  if (!isLow) {
    renderer.shadowMap.type = 0 // BasicShadowMap
    if (directionalLight) {
      const size = isMedium ? 1024 : 2048
      directionalLight.castShadow = true
      directionalLight.shadow.mapSize.width = size
      directionalLight.shadow.mapSize.height = size
      // Жёстко переустанавливаем направление света и таргет,
      // чтобы тень персонажа не "уплывала" после смены качества.
      directionalLight.position.set(0, 12, -6)
      if (directionalLight.target) {
        directionalLight.target.position.set(0, 0, 0)
        directionalLight.target.updateMatrixWorld()
      }
      // Полностью пересоздаём shadow map, чтобы не было артефактов/смещений
      if (directionalLight.shadow && directionalLight.shadow.map) {
        directionalLight.shadow.map.dispose()
        directionalLight.shadow.map = null
      }
      directionalLight.shadow.needsUpdate = true
      if (directionalLight.shadow.camera && directionalLight.shadow.camera.updateProjectionMatrix) {
        directionalLight.shadow.camera.updateProjectionMatrix()
      }
    }
  } else if (directionalLight) {
    directionalLight.castShadow = false
    if (directionalLight.shadow && directionalLight.shadow.map) {
      directionalLight.shadow.map.dispose()
      directionalLight.shadow.map = null
    }
  }

  // DPR: low=1 (фикс), medium/normal — целевые значения, дальше адаптируем по frameTimeEMA
  const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1
  if (isLow) {
    targetPixelRatio = 1
    minPixelRatio = 1
  } else if (isMedium) {
    targetPixelRatio = Math.min(dpr, 1.5)
    minPixelRatio = 1
  } else {
    targetPixelRatio = Math.min(dpr, 2)
    minPixelRatio = 1
  }
  dynamicPixelRatio = targetPixelRatio
  renderer.setPixelRatio(dynamicPixelRatio)

  // На смене настроек графики обновляем качество эффектов (количество частиц)
  if (gameEffects.value) {
    gameEffects.value.clearAll()
    gameEffects.value = useGameEffects(scene, graphicsQuality.value)
  }

  // receiveShadow только у дороги (normal/medium) — без traverse по всей сцене
  if (gameWorld.value?.setRoadReceiveShadow) {
    gameWorld.value.setRoadReceiveShadow(!isLow)
  }

  // Частота обновления анимаций скелета: medium/low — легче
  if (gamePhysics.value?.setMixerRate) {
    // Возвращаем полную частоту обновления на всех уровнях качества,
    // чтобы не было ощущения "тормознутости" анимаций.
    gamePhysics.value.setMixerRate(1)
  }
  const player = gamePhysics.value?.playerMesh?.()
  if (player && !isLow) {
    player.traverse?.((child) => {
      if (child.isMesh) child.castShadow = true
    })
  }

  // На low отключаем забор (GLB + фолбек-боксы), оставляем только бордюр.
  if (gameWorld.value?.setFenceEnabled) {
    gameWorld.value.setFenceEnabled(!isLow)
  }
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

const startGame = (training = false, initialStorage = null) => {
  // Если забег уже идёт — игнорируем повторный старт
  if (gameRun.isRunning.value && !gameRun.isPaused.value) return

  isTrainingRun.value = training
  playerZ.value = 0
  gameSpeed.value = 0.15
  if (gameWorld.value) {
    gameWorld.value.clearAll()
    gameWorld.value.createRoad()
  }
  applyGraphicsQuality()
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
  }
  // Передаем начальное значение storage в startRun, чтобы использовать его для генерации поинтов
  // даже если сервер уже обнулил storage
  gameRun.startRun(initialStorage)
  hitCount.value = 0
  isDead.value = false
  winTriggered = false
  winDecelerating = false
  winAnimationStartTime = 0
  obstaclesHidden = false
  showGameOver.value = false
  launcherOverlayMode.value = 'none'
  // Сбрасываем сохраненное значение энергии для модалки при старте нового забега
  savedEnergyCollectedForModal.value = 0
  completedRunData.value = null
  // Сбрасываем флаг обработки завершения игры
  if (endGame._isProcessing) {
    endGame._isProcessing = false
  }
  
  // Инициализируем перегрев при старте забега
  initializeOverheat()
  
  if (gamePhysics.value?.setAnimationState) {
    gamePhysics.value.setAnimationState('running')
  }
  lastUpdateTime = 0
}

// Инициализация перегрева при старте забега
const initializeOverheat = () => {
  const stationType = app.user?.station_type
  const neededHours = OVERHEAT_HOURS_BY_TYPE[stationType]
  const isCryoActive = app.user?.cryo_expires && new Date(app.user.cryo_expires) > new Date()
  
  // Перегрев возможен только для определенных типов станций и если Cryo не активен
  if (!neededHours || isCryoActive) {
    isOverheated.value = false
    overheatEnergyCollected.value = 0
    overheatGoal.value = null
    wasOverheated.value = false
    overheatedUntil.value = null
    showOverheatModal.value = false
    overheatDecelerating.value = false
    return
  }
  
  // Инициализируем состояние перегрева из app.user (данные с сервера)
  overheatEnergyCollected.value = app.user?.overheat_energy_collected || 0
  wasOverheated.value = app.user?.was_overheated || false
  overheatGoal.value = app.user?.overheat_goal || null
  
  // Проверяем активный перегрев
  if (app.user?.overheated_until) {
    const overheatedUntilDate = new Date(app.user.overheated_until)
    if (overheatedUntilDate > new Date()) {
      // Перегрев уже активен
      isOverheated.value = true
      overheatedUntil.value = overheatedUntilDate
      // Показываем модальное окно сразу при старте забега
      showOverheatModal.value = true
      pauseGame()
    } else {
      // Перегрев закончился
      isOverheated.value = false
      overheatedUntil.value = null
    }
  } else {
    isOverheated.value = false
    overheatedUntil.value = null
  }
}

// Проверка триггера перегрева через API
const checkOverheatTrigger = async (amount) => {
  const stationType = app.user?.station_type
  const neededHours = OVERHEAT_HOURS_BY_TYPE[stationType]
  const isCryoActive = app.user?.cryo_expires && new Date(app.user.cryo_expires) > new Date()
  
  // Проверяем условия для перегрева
  if (!neededHours || isCryoActive) {
    return false
  }
  
  try {
    // Отправляем количество собранной энергии на сервер
    // Сервер обновит overheat_energy_collected и проверит активацию перегрева
    const response = await host.post('game-run-update-overheat/', {
      amount: amount
    })
    
    if (response.data.overheated) {
      // Перегрев активирован на сервере
      activateOverheat(response.data)
      return true
    }
    
    // Обновляем локальное состояние из ответа сервера
    overheatEnergyCollected.value = response.data.overheat_energy_collected || 0
    overheatGoal.value = response.data.overheat_goal
    wasOverheated.value = response.data.was_overheated || false
    
    return false
  } catch (error) {
    console.error('Error checking overheat:', error)
    return false
  }
}

// Активация перегрева
const activateOverheat = (serverData) => {
  // Устанавливаем состояние перегрева из ответа сервера
  isOverheated.value = true
  
  if (serverData.overheated_until) {
    overheatedUntil.value = new Date(serverData.overheated_until)
  }
  
  wasOverheated.value = serverData.was_overheated || false
  overheatEnergyCollected.value = serverData.overheat_energy_collected || 0
  overheatGoal.value = serverData.overheat_goal
  
  // НЕ останавливаем игру сразу - персонаж продолжает бежать
  // Вибрация при перегреве
  if (vibrationEnabled.value) {
    try {
      const tg = window.Telegram?.WebApp
      tg?.HapticFeedback?.impactOccurred?.('heavy')
    } catch {
      // ignore
    }
    if (typeof navigator !== 'undefined' && navigator.vibrate) {
      navigator.vibrate([100, 50, 100]) // Двойная вибрация для перегрева
    }
  }
  
  // Запускаем обратный отсчет 5 секунд перед остановкой персонажа
  overheatCountdown.value = 5
  
  // Очищаем предыдущий интервал если есть
  if (overheatCountdownInterval) {
    clearInterval(overheatCountdownInterval)
  }
  
  overheatCountdownInterval = setInterval(() => {
    if (overheatCountdown.value === null || overheatCountdown.value <= 0) {
      clearInterval(overheatCountdownInterval)
      overheatCountdownInterval = null
      return
    }
    
    // Когда таймер показывает 2 секунды - начинаем плавное замедление
    if (overheatCountdown.value === 2) {
      console.log('[GameRunView] Overheat countdown at 2, starting smooth deceleration. Current speed:', gameSpeed.value)
      overheatDecelerating.value = true
    }
    
    // Когда таймер показывает 1 секунду - останавливаем и показываем модалку
    if (overheatCountdown.value === 1) {
      console.log('[GameRunView] Overheat countdown at 1, stopping and showing modal')
      
      // Останавливаем плавное замедление
      overheatDecelerating.value = false
      gameSpeed.value = 0
      if (gameWorld.value) {
        gameWorld.value.setRoadSpeed(0)
      }
      stopGameLoop()
      gameRun.pauseRun()
      
      // Переводим персонажа в состояние idle (standing) - анимация покоя
      if (gamePhysics.value?.setAnimationState) {
        gamePhysics.value.setAnimationState('idle')
      }
      
      // Убеждаемся что перегрев активен
      if (!isOverheated.value) {
        isOverheated.value = true
      }
      
      // Показываем модалку перегрева
      showOverheatModal.value = true
      launcherOverlayMode.value = 'none' // Не показываем модалку паузы
      
      clearInterval(overheatCountdownInterval)
      overheatCountdownInterval = null
      overheatCountdown.value = null
      
      console.log('[GameRunView] Overheat modal shown. showOverheatModal:', showOverheatModal.value, 'isOverheated:', isOverheated.value)
      return
    }
    
    // Уменьшаем таймер
    if (overheatCountdown.value > 1) {
      overheatCountdown.value--
    }
  }, 1000)
}

// Обработчик кнопки "Продолжить" в модалке перегрева
const handleOverheatContinue = async () => {
  // Обновляем данные пользователя с сервера (на случай если азот был использован)
  await app.initUser()
  
  // Проверяем состояние перегрева после обновления данных
  const now = new Date()
  
  // Проверяем локальное состояние перегрева
  if (overheatedUntil.value) {
    const until = new Date(overheatedUntil.value)
    if (until > now) {
      // Перегрев еще активен по локальному времени, кнопка должна быть неактивна
      // Но если пользователь нажал кнопку, значит она стала активной, проверяем серверные данные
      if (app.user?.overheated_until) {
        const serverUntil = new Date(app.user.overheated_until)
        if (serverUntil > now) {
          // Перегрев еще активен на сервере
          return
        }
      }
    }
  }
  
  // Проверяем серверные данные перегрева
  if (app.user?.overheated_until) {
    const serverUntil = new Date(app.user.overheated_until)
    if (serverUntil > now) {
      // Перегрев еще активен на сервере
      return
    }
  }
  
  // Перегрев закончился или был снят азотом, продолжаем забег
  isOverheated.value = false
  showOverheatModal.value = false
  overheatedUntil.value = app.user?.overheated_until ? new Date(app.user.overheated_until) : null
  overheatCountdown.value = null // Сбрасываем таймер
  overheatDecelerating.value = false // Сбрасываем флаг замедления
  
  // Возобновляем забег
  resumeGame()
}

// Обработчик закрытия модалки перегрева
const handleOverheatModalClose = () => {
  // Закрываем модалку только если перегрев закончился
  const now = new Date()
  const until = overheatedUntil.value ? new Date(overheatedUntil.value) : null
  
  if (!until || until <= now) {
    // Перегрев закончился, можно закрыть модалку
    showOverheatModal.value = false
    isOverheated.value = false
    launcherOverlayMode.value = 'none'
  }
  // Если перегрев еще активен, не закрываем модалку
}

const pauseGame = () => {
  gameRun.pauseRun()
  stopGameLoop()
  
  // Устанавливаем анимацию стояния при паузе
  if (gamePhysics.value?.setAnimationState) {
    gamePhysics.value.setAnimationState('idle')
  }
  
  // Если модалка перегрева открыта (активна или только что закончилась), не показываем модалку паузы
  if (showOverheatModal.value) {
    launcherOverlayMode.value = 'none' // Не показываем обычную паузу
    return
  }
  
  // Если перегрев активен, показываем модалку перегрева
  if (isOverheated.value) {
    launcherOverlayMode.value = 'none' // Не показываем обычную паузу
    showOverheatModal.value = true
  } else {
    launcherOverlayMode.value = 'pause'
  }
}

const resumeGame = async () => {
  // Обновляем данные пользователя с сервера (на случай если азот был использован)
  await app.initUser()
  
  // Проверяем состояние перегрева после обновления данных
  const now = new Date()
  
  // Проверяем локальное состояние перегрева
  if (overheatedUntil.value) {
    const until = new Date(overheatedUntil.value)
    if (until > now) {
      // Перегрев еще активен по локальному времени, не возобновляем
      // Но если пользователь нажал кнопку, значит она стала активной, проверяем серверные данные
      if (app.user?.overheated_until) {
        const serverUntil = new Date(app.user.overheated_until)
        if (serverUntil > now) {
          // Перегрев еще активен на сервере
          return
        }
      }
    }
  }
  
  // Проверяем серверные данные перегрева
  if (app.user?.overheated_until) {
    const serverUntil = new Date(app.user.overheated_until)
    if (serverUntil > now) {
      // Перегрев еще активен на сервере
      return
    }
  }
  
  // Перегрев закончился или был снят азотом, показываем таймер обратного отсчета
  isOverheated.value = false
  showOverheatModal.value = false
  overheatedUntil.value = app.user?.overheated_until ? new Date(app.user.overheated_until) : null
  overheatCountdown.value = null // Сбрасываем таймер
  overheatDecelerating.value = false // Сбрасываем флаг замедления
  
  // Показываем таймер обратного отсчета 3-2-1
  showCountdown.value = true
  countdownNumber.value = 3
  
  // Вибрация при каждом числе
  const triggerVibration = () => {
    if (vibrationEnabled.value) {
      try {
        const tg = window.Telegram?.WebApp
        tg?.HapticFeedback?.impactOccurred?.('medium')
      } catch {
        // ignore
      }
      if (typeof navigator !== 'undefined' && navigator.vibrate) {
        navigator.vibrate(50)
      }
    }
  }
  
  triggerVibration()
  
  countdownInterval = setInterval(() => {
    countdownNumber.value--
    
    if (countdownNumber.value > 0) {
      triggerVibration()
    } else {
      // Таймер закончился, начинаем забег
      clearInterval(countdownInterval)
      countdownInterval = null
      showCountdown.value = false
      
      gameRun.resumeRun()
      lastUpdateTime = 0
      launcherOverlayMode.value = 'none'
      
      // Активируем анимацию бега персонажа
      if (gamePhysics.value?.setAnimationState) {
        gamePhysics.value.setAnimationState('running')
      }
      
      // Финальная вибрация
      if (vibrationEnabled.value) {
        try {
          const tg = window.Telegram?.WebApp
          tg?.HapticFeedback?.impactOccurred?.('heavy')
        } catch {
          // ignore
        }
        if (typeof navigator !== 'undefined' && navigator.vibrate) {
          navigator.vibrate([100, 50, 100])
        }
      }
    }
  }, 1000)
}

function doOneStep(playerBox, inRollImmuneWindow) {
  playerZ.value += gameSpeed.value

  if (gamePhysics.value) {
      if (gameWorld.value) {
        gameWorld.value.updateRoad()

        // Не обновляем препятствия если игрок уже победил (с начала замедления)
        // Скрываем препятствия и останавливаем их движение
        if (winTriggered || winDecelerating || winAnimationStartTime > 0) {
          // Скрываем все препятствия при победе (только один раз)
          if (!obstaclesHidden && gameWorld.value.hideAllObstacles) {
            gameWorld.value.hideAllObstacles()
            obstaclesHidden = true
          }
        } else {
          // Не проверяем коллизии если игрок уже победил (во время анимации победы)
          gameWorld.value.updateObstacles(
            playerBox,
            () => {
              hitCount.value += 1
              hitFlashTick.value++
              gameRun.hitObstacle()
              const newPower = gameRun.currentPower.value - 10
              app.setPower(Math.max(0, newPower))
              if (!isDead.value && livesLeft.value <= 0) {
                isDead.value = true
                // Сохраняем energyCollected ДО остановки игрового цикла
                // Ограничиваем значение максимумом storage (та же логика, что в счетчике энергии)
                const savedEnergyBeforeStop = Math.min(
                  gameRun.energyCollected?.value ?? 0,
                  gameRun.startStorage?.value ?? gameRun.currentStorage?.value ?? 0
                )
                // Сохраняем значение для модалки сразу при смерти
                savedEnergyCollectedForModal.value = savedEnergyBeforeStop
                console.log('Player died (livesLeft=0): energyCollected BEFORE stop=', savedEnergyBeforeStop, 'startStorage=', gameRun.startStorage?.value, 'savedEnergyCollectedForModal=', savedEnergyCollectedForModal.value)
                
                // НЕ вызываем stopRun() здесь, чтобы не сбросить startStorage и energyCollected
                // Останавливаем только игровой цикл и физику
                stopGameLoop()
                if (gameWorld.value) gameWorld.value.setRoadSpeed(0)
                gameSpeed.value = 0
                // Останавливаем физику персонажа - запускаем анимацию падения
                if (gamePhysics.value?.onFinalHit) {
                  gamePhysics.value.onFinalHit()
                } else if (gamePhysics.value?.setAnimationState) {
                  // Fallback: просто включаем анимацию падения
                  gamePhysics.value.setAnimationState('lose')
                }
                // Устанавливаем тип проигрыша, но НЕ показываем модалку сразу
                // Модалка появится после завершения анимации падения в endGame
                gameOverType.value = 'lose'
                launcherOverlayMode.value = 'none'
                
                // Проверяем energyCollected после остановки игрового цикла
                console.log('Player died (livesLeft=0): energyCollected AFTER stop=', gameRun.energyCollected?.value, 'startStorage=', gameRun.startStorage?.value, 'savedEnergyCollectedForModal=', savedEnergyCollectedForModal.value)
                
                // Вызываем endGame после задержки для завершения анимации падения
                setTimeout(() => {
                  console.log('Calling endGame after delay (livesLeft=0): energyCollected=', gameRun.energyCollected?.value, 'startStorage=', gameRun.startStorage?.value, 'savedEnergyCollectedForModal=', savedEnergyCollectedForModal.value)
                  if (!endGame._isProcessing) {
                    endGame(false)
                  }
                }, 2000) // Увеличиваем задержку до 2 секунд для завершения анимации падения
              }
              // Мягкая тряска камеры только при ударе: статичный вертикальный "рывок"
              shakeFramesLeft = SHAKE_DURATION_FRAMES
              const amp = 0.28
              shakeBaseX = 0
              shakeBaseY = amp

              if (vibrationEnabled.value) {
                // Haptic feedback: Telegram WebApp + fallback через navigator.vibrate
                try {
                  const tg = window.Telegram?.WebApp
                  tg?.HapticFeedback?.impactOccurred?.('medium')
                } catch {
                  // ignore
                }
                if (typeof navigator !== 'undefined' && navigator.vibrate) {
                  navigator.vibrate(30)
                }
              }
            },
            gamePhysics.value.isSliding?.value === true,
            inRollImmuneWindow
          )
        }

        gameWorld.value.updateCollectibles(
          playerBox,
          async (energy) => {
            // При сборе токена: увеличиваем собранную энергию и счетчик собранных токенов
            // Также помечаем токен как пройденный (для прогресса дистанции)
            gameRun.collectEnergy(energy)
            gameRun.markPointPassed()
            
            // Проверяем перегрев через API (только если перегрев еще не активен)
            if (!isOverheated.value) {
              const overheated = await checkOverheatTrigger(energy)
              if (overheated) {
                // Перегрев активирован, забег уже остановлен в activateOverheat()
                return
              }
            }
          },
          () => {
            // Когда токен проходит мимо без сбора: только помечаем как пройденный
            gameRun.markPointPassed()
          }
        )
      }

      if (!winTriggered && gameRun.isRunComplete()) {
        winTriggered = true
        winDecelerating = true
      }
    }

    // Плавная остановка при перегреве (с 2 до 1 секунды, как при победе)
    if (overheatDecelerating.value) {
      gameSpeed.value *= WIN_DECEL_RATE
      if (gameWorld.value) gameWorld.value.setRoadSpeed(gameSpeed.value)
      
      // Обновляем дистанцию даже во время замедления, если игра еще работает
      if (gameRun.isRunning.value && !gameRun.isPaused.value && !isDead.value) {
        const distanceDelta = gameSpeed.value * 10
        if (distanceDelta > 0) {
          gameRun.updateDistance(gameRun.distance.value + distanceDelta)
        }
      }
    }

    // Плавная остановка при победе
    if (winDecelerating) {
      gameSpeed.value *= WIN_DECEL_RATE
      if (gameWorld.value) gameWorld.value.setRoadSpeed(gameSpeed.value)
      if (gameSpeed.value < WIN_SPEED_THRESHOLD) {
        gameSpeed.value = 0
        if (gameWorld.value) gameWorld.value.setRoadSpeed(0)
        winDecelerating = false
        if (gamePhysics.value?.setAnimationState) gamePhysics.value.setAnimationState('win')
        if (gamePhysics.value?.onWin) {
          gamePhysics.value.onWin()
        }
        winAnimationStartTime = performance.now()
      }
    } else if (winAnimationStartTime > 0) {
        if (performance.now() - winAnimationStartTime >= WIN_ANIMATION_DURATION_MS) {
          if (!endGame._isProcessing) {
            // Сохраняем значение энергии перед показом модалки выигрыша
            // Ограничиваем значение максимумом storage (та же логика, что в счетчике энергии)
            const winEnergy = Math.min(
              gameRun.energyCollected?.value ?? 0,
              gameRun.startStorage?.value ?? gameRun.currentStorage?.value ?? 0
            )
            // Всегда обновляем значение при выигрыше, если оно больше сохраненного или сохраненное равно 0
            if (savedEnergyCollectedForModal.value === 0 || winEnergy > savedEnergyCollectedForModal.value) {
              savedEnergyCollectedForModal.value = winEnergy
            }
          gameOverType.value = 'win'
          showGameOver.value = true
          launcherOverlayMode.value = 'none'
          endGame(true)
        }
        winAnimationStartTime = 0
      }
    }
}

const stopGameLoop = () => {
  lastUpdateTime = 0
}

const toggleGraphicsQuality = () => {
  const current = graphicsQuality.value
  const next = current === 'normal' ? 'medium' : current === 'medium' ? 'low' : 'normal'

  if (isWeakDevice.value && current === 'low' && (next === 'normal' || next === 'medium')) {
    pendingGraphicsQuality.value = next
    showGraphicsInfoModal.value = true
    return
  }

  graphicsQuality.value = next
  applyGraphicsQualityAndSave()
}

const toggleVibration = () => {
  vibrationEnabled.value = !vibrationEnabled.value
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      window.localStorage.setItem('game_vibration_enabled', vibrationEnabled.value ? '1' : '0')
    } catch {
      // ignore
    }
  }
}

const toggleHitFlash = () => {
  hitFlashEnabled.value = !hitFlashEnabled.value
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      window.localStorage.setItem('game_hit_flash_enabled', hitFlashEnabled.value ? '1' : '0')
    } catch {
      // ignore
    }
  }
}

const toggleControlMode = () => {
  controlMode.value = controlMode.value === 'swipes' ? 'buttons' : 'swipes'
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      window.localStorage.setItem('game_control_mode', controlMode.value)
    } catch {
      // ignore
    }
  }
}

const endGame = async (isWinByState = false) => {
  // Защита от повторных вызовов
  if (endGame._isProcessing) {
    console.warn('endGame already processing, ignoring duplicate call')
    return
  }
  endGame._isProcessing = true

  try {
    stopGameLoop()

    // Полная очистка объектов мира и эффектов, чтобы собранные кубы/препятствия
    // не "зависали" возле персонажа после удара/завершения забега.
    if (gameWorld.value) {
      gameWorld.value.clearAll()
    }
    if (gameEffects.value) {
      gameEffects.value.clearAll()
    }

    // Сохраняем данные ДО вызова completeRun, так как они могут быть изменены
    // Ограничиваем значение максимумом storage (та же логика, что в счетчике энергии)
    const savedEnergyBeforeComplete = Math.min(
      gameRun.energyCollected?.value ?? 0,
      gameRun.startStorage?.value ?? gameRun.currentStorage?.value ?? 0
    )
    const savedStartStorageBeforeComplete = gameRun.startStorage?.value ?? gameRun.currentStorage?.value ?? 0
    
    // Сохраняем для отображения в модалке (не будет обнулено до нажатия "Забрать")
    // ВАЖНО: НЕ перезаписываем значение, если оно уже было установлено при смерти
    // Обновляем только если сохраненное значение равно 0 ИЛИ новое значение больше сохраненного
    // Это гарантирует, что значение, сохраненное при смерти, не будет перезаписано меньшим значением
    if (savedEnergyCollectedForModal.value === 0) {
      // Если значение еще не было сохранено, сохраняем текущее
      savedEnergyCollectedForModal.value = savedEnergyBeforeComplete
    } else if (savedEnergyBeforeComplete > savedEnergyCollectedForModal.value) {
      // Если новое значение больше сохраненного, обновляем (например, при выигрыше)
      savedEnergyCollectedForModal.value = savedEnergyBeforeComplete
    }
    // Иначе оставляем сохраненное значение без изменений
    
    console.log('endGame called, isWinByState:', isWinByState, 'energyCollected BEFORE completeRun:', savedEnergyBeforeComplete, 'startStorage BEFORE completeRun:', savedStartStorageBeforeComplete, 'savedEnergyCollectedForModal=', savedEnergyCollectedForModal.value, 'isRunning:', gameRun.isRunning.value, 'runStartTime:', gameRun.runStartTime?.value)
    
    // Вызываем completeRun для сохранения данных забега на сервере (без начисления энергии)
    const result = await gameRun.completeRun(isWinByState).catch((e) => {
      console.error('Ошибка завершения забега:', e)
      console.error('Error details:', e.response?.data, e.message)
      return null
    })
    console.log('endGame completeRun result:', result)

    // Сохраняем данные завершенного забега для последующего начисления при нажатии "Забрать"
    
    if (result && result.success) {
      // Определяем финальное значение собранной энергии
      // Приоритет: сохраненное значение при смерти > значение с сервера > значение до completeRun
      // НО: если сервер вернул 0, это может быть ошибка, поэтому используем сохраненное значение
      let finalEnergyCollected
      if (savedEnergyCollectedForModal.value > 0) {
        // Если значение было сохранено при смерти, используем его (самый надежный источник)
        finalEnergyCollected = savedEnergyCollectedForModal.value
        // Обновляем только если сервер вернул значение больше сохраненного (например, при выигрыше)
        if (result.energy_collected !== undefined && result.energy_collected > savedEnergyCollectedForModal.value) {
          finalEnergyCollected = result.energy_collected
          savedEnergyCollectedForModal.value = result.energy_collected
        }
      } else if (result.energy_collected !== undefined && result.energy_collected > 0) {
        // Если значение не было сохранено при смерти, но сервер вернул валидное значение
        finalEnergyCollected = result.energy_collected
        savedEnergyCollectedForModal.value = result.energy_collected
      } else {
        // Fallback: используем значение до completeRun
        finalEnergyCollected = savedEnergyBeforeComplete
        if (savedEnergyCollectedForModal.value === 0) {
          savedEnergyCollectedForModal.value = savedEnergyBeforeComplete
        }
      }
      
      // При выигрыше energy_gained должно быть равно energy_collected (вся собранная энергия)
      // Если сервер вернул 0 или undefined, используем собранное значение
      let energyGained = result.energy_gained
      if ((result.is_win ?? isWinByState) && (!energyGained || energyGained === 0)) {
        energyGained = finalEnergyCollected
      } else if (!energyGained) {
        energyGained = 0
      }
      
      completedRunData.value = {
        energy_collected: finalEnergyCollected,
        is_win: result.is_win ?? isWinByState,
        energy_gained: energyGained
      }
      console.log('endGame: saved completedRunData:', completedRunData.value, 'savedEnergyBeforeComplete=', savedEnergyBeforeComplete, 'savedEnergyCollectedForModal=', savedEnergyCollectedForModal.value, 'result.energy_collected=', result.energy_collected)
      // Принудительно обновляем реактивность перед показом модалки
      await nextTick()
      console.log('endGame: After nextTick, completedRunData.value.energy_collected=', completedRunData.value?.energy_collected, 'savedEnergyCollectedForModal=', savedEnergyCollectedForModal.value)
    } else {
      // Если result не получен, используем сохраненное значение при смерти или значение до completeRun
      // Приоритет: сохраненное значение при смерти > значение до completeRun
      const finalEnergyCollected = savedEnergyCollectedForModal.value > 0 ? savedEnergyCollectedForModal.value : savedEnergyBeforeComplete
      
      // При выигрыше energy_gained должно быть равно energy_collected (вся собранная энергия)
      const energyGainedFallback = (isWinByState && finalEnergyCollected > 0) ? finalEnergyCollected : 0
      
      completedRunData.value = {
        energy_collected: finalEnergyCollected,
        is_win: isWinByState ?? false,
        energy_gained: energyGainedFallback
      }
      // Убеждаемся что savedEnergyCollectedForModal содержит правильное значение
      // НЕ перезаписываем если значение уже было установлено при смерти
      if (savedEnergyCollectedForModal.value === 0 && savedEnergyBeforeComplete > 0) {
        savedEnergyCollectedForModal.value = savedEnergyBeforeComplete
      }
      console.log('endGame: saved completedRunData (fallback):', completedRunData.value, 'savedEnergyBeforeComplete=', savedEnergyBeforeComplete, 'savedEnergyCollectedForModal=', savedEnergyCollectedForModal.value)
      // Принудительно обновляем реактивность перед показом модалки
      await nextTick()
      console.log('endGame: After nextTick (fallback), completedRunData.value.energy_collected=', completedRunData.value?.energy_collected, 'savedEnergyCollectedForModal=', savedEnergyCollectedForModal.value)
    }

    // НЕ обновляем состояние приложения здесь - энергия еще не начислена
    // Обновление произойдет после нажатия "Забрать" в handleClaim()

    // Определяем результат забега: приоритет у isWinByState (переданного параметра)
    // Если isWinByState явно передан (true или false), используем его
    // Иначе используем данные из result
    let isWin = false
    if (isWinByState !== undefined && isWinByState !== null) {
      // Явно передан параметр - используем его
      isWin = isWinByState === true
    } else if (result && result.is_win !== undefined) {
      // Используем данные с сервера
      isWin = result.is_win === true
    }
    console.log('endGame: isWinByState=', isWinByState, 'result.is_win=', result?.is_win, 'final isWin=', isWin, 'gameOverType.value=', gameOverType.value)

    // Устанавливаем модалку только если она еще не установлена
    // (при проигрыше она НЕ устанавливается в игровом цикле - только тип, модалка показывается здесь после анимации)
    console.log('endGame: showGameOver.value=', showGameOver.value, 'isWin=', isWin, 'gameOverType.value=', gameOverType.value)
    
    if (!showGameOver.value) {
      if (isWin) {
        // Успешное завершение забега — проигрываем победную анимацию
        // Убеждаемся что savedEnergyCollectedForModal содержит правильное значение перед показом модалки
        // Ограничиваем значение максимумом storage (та же логика, что в счетчике энергии)
        const winEnergy = Math.min(
          gameRun.energyCollected?.value ?? 0,
          gameRun.startStorage?.value ?? gameRun.currentStorage?.value ?? 0
        )
        // Всегда обновляем значение при выигрыше, если оно больше сохраненного или сохраненное равно 0
        if (savedEnergyCollectedForModal.value === 0 || winEnergy > savedEnergyCollectedForModal.value) {
          savedEnergyCollectedForModal.value = winEnergy
        }
        console.log('endGame: Before showing WIN modal, savedEnergyCollectedForModal=', savedEnergyCollectedForModal.value, 'winEnergy=', winEnergy, 'gameRun.energyCollected?.value=', gameRun.energyCollected?.value)
        if (gamePhysics.value?.setAnimationState) {
          gamePhysics.value.setAnimationState('win')
        }
        gameOverType.value = 'win'
        showGameOver.value = true
        launcherOverlayMode.value = 'none'
        console.log('endGame: Set gameOverType to WIN')
      } else {
        // При проигрыше показываем экран завершения после анимации падения
        // Убеждаемся что gameOverType установлен как 'lose'
        // НЕ перезаписываем savedEnergyCollectedForModal здесь - оно уже должно быть установлено при смерти
        // Только проверяем что значение установлено, если нет - устанавливаем из текущего состояния
        if (savedEnergyCollectedForModal.value === 0) {
          // Если значение не было сохранено при смерти, пытаемся восстановить из текущего состояния
          const loseEnergy = Math.min(
            gameRun.energyCollected?.value ?? 0,
            gameRun.startStorage?.value ?? gameRun.currentStorage?.value ?? 0
          )
          savedEnergyCollectedForModal.value = loseEnergy
          console.log('endGame: Restored savedEnergyCollectedForModal from current state:', loseEnergy)
        }
        console.log('endGame: Before showing LOSE modal, savedEnergyCollectedForModal=', savedEnergyCollectedForModal.value, 'completedRunData.energy_collected=', completedRunData.value?.energy_collected, 'gameRun.energyCollected?.value=', gameRun.energyCollected?.value)
        // Убеждаемся что данные установлены перед показом модалки
        await nextTick()
        console.log('endGame: After nextTick before showing modal, displayedEnergyCollected computed value would be:', savedEnergyCollectedForModal.value > 0 ? savedEnergyCollectedForModal.value : (completedRunData.value?.energy_collected ?? 0))
        gameOverType.value = 'lose'
        showGameOver.value = true
        launcherOverlayMode.value = 'none'
        console.log('endGame: Set gameOverType to LOSE, showGameOver=', showGameOver.value)
      }
    } else {
      // Если модалка уже показана, убеждаемся что gameOverType правильный
      // НО не перезаписываем если он уже установлен правильно
      if (isWin && gameOverType.value !== 'win') {
        gameOverType.value = 'win'
        console.log('endGame: Updated gameOverType to WIN (modal already shown)')
      } else if (!isWin && gameOverType.value !== 'lose') {
        gameOverType.value = 'lose'
        console.log('endGame: Updated gameOverType to LOSE (modal already shown)')
      }
    }
  } finally {
    endGame._isProcessing = false
  }
}

// Обработчики кнопок из оверлеев
const handleStartClick = async () => {
  // Вызываем API для записи времени старта (если не тренировка)
  try {
    // Сохраняем начальное значение storage ДО обнуления на сервере
    const initialStorage = app.storage ?? 70
    console.log('Starting energy run, current storage:', initialStorage)
    const response = await host.post('energy-run-start/')
    console.log('energy-run-start response:', response.data)
    if (response.status === 200 && response.data?.user) {
      // Обновляем данные пользователя
      app.user = response.data.user
      // Обновляем storage и другие поля из ответа сервера
      if (response.data.user.storage !== undefined) {
        app.setStorage(response.data.user.storage)
        console.log('Storage updated to:', response.data.user.storage)
      }
      if (response.data.user.power !== undefined) {
        app.setPower(response.data.user.power)
      }
      if (response.data.user.energy_run_last_started_at !== undefined) {
        app.user.energy_run_last_started_at = response.data.user.energy_run_last_started_at
        console.log('energy_run_last_started_at updated to:', response.data.user.energy_run_last_started_at)
      }
    }
    // Передаем начальное значение storage в startGame, чтобы использовать его для генерации поинтов
    startGame(false, initialStorage)
  } catch (error) {
    // Если ошибка cooldown - показываем сообщение и не запускаем игру
    if (error.response?.status === 400 && error.response?.data?.error === 'energy_run_cooldown') {
      const nextAvailable = error.response.data.next_available_in_seconds
      const minutes = Math.floor(nextAvailable / 60)
      const seconds = nextAvailable % 60
      const timeStr = `${minutes}:${String(seconds).padStart(2, '0')}`
      alert(t('energizer.energy_run_cooldown_message', { time: timeStr }))
      return
    }
    // Другие ошибки - запускаем игру всё равно (fallback)
    console.error('Error starting energy run:', error)
    startGame(false)
  }
}

const handleTrainingClick = () => {
  startGame(true)
}

const handleResumeClick = () => {
  // Закрываем модалку паузы
  launcherOverlayMode.value = 'none'
  
  // Показываем таймер обратного отсчета 3-2-1 (как после перегрева)
  showCountdown.value = true
  countdownNumber.value = 3
  
  // Вибрация при каждом числе
  const triggerVibration = () => {
    if (vibrationEnabled.value) {
      try {
        const tg = window.Telegram?.WebApp
        tg?.HapticFeedback?.impactOccurred?.('medium')
      } catch {
        // ignore
      }
      if (typeof navigator !== 'undefined' && navigator.vibrate) {
        navigator.vibrate(50)
      }
    }
  }
  
  triggerVibration()
  
  // Очищаем предыдущий интервал если есть
  if (countdownInterval) {
    clearInterval(countdownInterval)
  }
  
  countdownInterval = setInterval(() => {
    countdownNumber.value--
    
    if (countdownNumber.value > 0) {
      triggerVibration()
    } else {
      // Таймер закончился, начинаем забег
      clearInterval(countdownInterval)
      countdownInterval = null
      showCountdown.value = false
      
      gameRun.resumeRun()
      lastUpdateTime = 0
      
      // Активируем анимацию бега персонажа (из стоячего положения)
      if (gamePhysics.value?.setAnimationState) {
        gamePhysics.value.setAnimationState('running')
      }
      
      // Финальная вибрация
      if (vibrationEnabled.value) {
        try {
          const tg = window.Telegram?.WebApp
          tg?.HapticFeedback?.impactOccurred?.('heavy')
        } catch {
          // ignore
        }
        if (typeof navigator !== 'undefined' && navigator.vibrate) {
          navigator.vibrate([100, 50, 100])
        }
      }
    }
  }, 1000)
}

const openPauseOverlay = () => {
  pauseGame()
}

const openSettings = () => {
  launcherOverlayMode.value = 'settings'
}

const closeSettings = () => {
  launcherOverlayMode.value = 'idle'
}

const handleSwipeLeft = () => {
  // Игрок реагирует на свайпы только во время активного забега
  // Блокируем свайпы если игрок победил (с начала замедления до конца анимации победы)
  if (!gameRun.isRunning.value || gameRun.isPaused.value || isDead.value || winTriggered || winDecelerating || winAnimationStartTime > 0) return
  if (gamePhysics.value) {
    gamePhysics.value.moveLeft()
  }
}

const handleSwipeRight = () => {
  if (!gameRun.isRunning.value || gameRun.isPaused.value || isDead.value || winTriggered || winDecelerating || winAnimationStartTime > 0) return
  if (gamePhysics.value) {
    gamePhysics.value.moveRight()
  }
}

const handleSwipeUp = () => {
  if (!gameRun.isRunning.value || gameRun.isPaused.value || isDead.value || winTriggered || winDecelerating || winAnimationStartTime > 0) return
  if (gamePhysics.value) {
    gamePhysics.value.jump()
  }
}

const handleSwipeDown = () => {
  if (!gameRun.isRunning.value || gameRun.isPaused.value || isDead.value || winTriggered || winDecelerating || winAnimationStartTime > 0) return
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

// Забрать: начисление энергии через отдельный эндпоинт
const handleClaim = async () => {
  if (!completedRunData.value) {
    console.error('handleClaim: completedRunData is null')
    exitToMain()
    return
  }

  try {
    console.log('handleClaim: calling game-run-claim with data:', completedRunData.value)
    
    const response = await host.post('game-run-claim/', {
      energy_collected: completedRunData.value.energy_collected,
      is_win: completedRunData.value.is_win
    })
    
    console.log('handleClaim: response:', response.data)
    
    if (response.status === 200 && response.data.success) {
      // Обновляем состояние приложения после успешного начисления
      if (response.data.total_energy !== undefined) {
        app.setScore(response.data.total_energy)
      }
      if (response.data.storage !== undefined) {
        app.setStorage(response.data.storage)
      }
      if (response.data.power !== undefined) {
        app.setPower(response.data.power)
      }
      
      // Очищаем данные забега только после успешного начисления
      completedRunData.value = null
      savedEnergyCollectedForModal.value = 0
      // Очищаем startStorage и energyCollected только после успешного начисления
      if (gameRun.startStorage) {
        gameRun.startStorage.value = 0
      }
      if (gameRun.energyCollected) {
        gameRun.energyCollected.value = 0
      }
      console.log('handleClaim: Cleared run data after successful claim', 'startStorage=', gameRun.startStorage?.value, 'energyCollected=', gameRun.energyCollected?.value, 'savedEnergyCollectedForModal=', savedEnergyCollectedForModal.value)
    }
  } catch (error) {
    console.error('Ошибка при начислении энергии:', error)
    console.error('Error response:', error.response?.data)
    // Показываем сообщение об ошибке пользователю
    alert(error.response?.data?.error || 'Ошибка при начислении энергии')
  }
  
  // Выходим из игры после начисления (или ошибки)
  exitToMain()
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

  // iOS: сначала обрабатываем отдельно, потому что Safari не даёт deviceMemory
  if (isIOS) {
    // Современные iPhone (14 Pro и т.п.): высокий DPI + достаточно потоков
    if (dpr >= 3 && cores >= 4) {
      return false
    }
    // Старые/маленькие iPhone (SE 1, 6/7/8 и т.п.): маленький логический экран и низкий DPI
    if (shortSide && shortSide <= 375 && dpr <= 2) {
      return true
    }
    // Остальные iOS считаем средними — не считаем их заведомо слабыми
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
  isWeakDevice.value = detectWeakDevice()
  if (typeof window !== 'undefined') {
    try {
      const saved = window.localStorage?.getItem('game_graphics_quality')
      if (!['normal', 'medium', 'low'].includes(saved)) {
        const isMobile = 'ontouchstart' in window
        graphicsQuality.value = isWeakDevice.value ? 'low' : (isMobile ? 'medium' : 'normal')
        applyGraphicsQuality()
      }
    } catch {
      graphicsQuality.value = isWeakDevice.value ? 'low' : 'normal'
      applyGraphicsQuality()
    }
  }
  
  // Периодическая проверка состояния перегрева (каждую секунду)
  overheatCheckInterval = setInterval(async () => {
    if (showOverheatModal.value && overheatedUntil.value) {
      const now = new Date()
      const until = new Date(overheatedUntil.value)
      
      // Если перегрев закончился, обновляем состояние (но не закрываем модалку)
      if (until <= now) {
        isOverheated.value = false
        
        // Обновляем данные пользователя с сервера для подтверждения
        try {
          await app.initUser()
          // Обновляем overheatedUntil из серверных данных
          if (app.user?.overheated_until) {
            const serverUntil = new Date(app.user.overheated_until)
            if (serverUntil > now) {
              // На сервере перегрев еще активен (возможна рассинхронизация времени)
              overheatedUntil.value = serverUntil
              isOverheated.value = true
            } else {
              // На сервере перегрев закончился
              overheatedUntil.value = null
              isOverheated.value = false
              // Обновляем модалку, но НЕ закрываем её и НЕ переключаем на паузу
              launcherOverlayMode.value = 'none'
            }
          } else {
            // На сервере нет перегрева
            overheatedUntil.value = null
            isOverheated.value = false
            // Обновляем модалку, но НЕ закрываем её и НЕ переключаем на паузу
            launcherOverlayMode.value = 'none'
          }
        } catch (error) {
          console.error('[GameRunView] Ошибка при обновлении состояния перегрева:', error)
        }
        // НЕ закрываем модалку автоматически - она остается открытой с зеленой подсветкой
        // НЕ переключаем на паузу - модалка перегрева остается активной
        // Пользователь должен нажать кнопку "Продолжить"
      } else {
        // Убрана отладочная информация о времени
      }
    }
  }, 1000)
})

onUnmounted(() => {
  stopGameLoop()
  if (threeLoop) {
    cancelAnimationFrame(threeLoop)
  }
  if (gameRun.isRunning.value) {
    gameRun.stopRun()
  }
  // Очищаем интервал проверки перегрева
  if (overheatCheckInterval) {
    clearInterval(overheatCheckInterval)
    overheatCheckInterval = null
  }
  // Очищаем таймер обратного отсчета перед началом забега
  if (countdownInterval) {
    clearInterval(countdownInterval)
    countdownInterval = null
  }
  // Очищаем таймер обратного отсчета перегрева
  if (overheatCountdownInterval) {
    clearInterval(overheatCountdownInterval)
    overheatCountdownInterval = null
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

.btn-primary--training {
  background: linear-gradient(135deg, #f59e0b 0%, #ea580c 50%, #c2410c 100%);
  color: #fff;
  box-shadow: 0 12px 30px rgba(234, 88, 12, 0.4);
  border: 1px solid rgba(251, 146, 60, 0.4);

  &:active {
    box-shadow: 0 6px 18px rgba(234, 88, 12, 0.35);
  }
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

.btn-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
  
  &:active {
    transform: none;
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

.game-over-results {
  margin-bottom: 20px;
  padding: 12px 0;
  border-top: 1px solid rgba(148, 163, 184, 0.2);
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.game-over-result-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 14px;
}

.game-over-result-row .game-over-result-label {
  flex: 1;
  text-align: left;
  color: #9ca3af;
}

.game-over-result-row:first-child .game-over-result-label {
  padding-left: 0;
}

.game-over-result-value {
  font-weight: 600;
  color: #e5e7eb;
  white-space: nowrap;
}

.game-over-result-icon {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  object-fit: contain;
}


.game-over-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.overheat-screen-pulse {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 9998;
  background: rgba(255, 59, 89, 0.1);
  animation: screenPulse 1s ease-in-out infinite;
}

.countdown-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  pointer-events: none;
}

.countdown-number {
  font-size: 120px;
  font-weight: 700;
  color: #fff;
  text-shadow: 0 0 30px rgba(255, 255, 255, 0.8), 0 0 60px rgba(255, 255, 255, 0.5);
  animation: countdownPulse 0.8s ease-out;
  font-family: 'Inter', sans-serif;
}

@keyframes countdownPulse {
  0% {
    transform: scale(0.5);
    opacity: 0;
  }
  50% {
    transform: scale(1.2);
    opacity: 1;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes screenPulse {
  0%, 100% {
    opacity: 0.1;
  }
  50% {
    opacity: 0.3;
  }
}

.hit-flash-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 350; // выше сцены/GUI, но ниже оверлеев
  background:
    linear-gradient(to right, rgba(255, 0, 0, 0.45) 0%, rgba(255, 0, 0, 0.25) 8%, transparent 20%),
    linear-gradient(to left, rgba(255, 0, 0, 0.45) 0%, rgba(255, 0, 0, 0.25) 8%, transparent 20%),
    linear-gradient(to bottom, rgba(255, 0, 0, 0.32) 0%, rgba(255, 0, 0, 0.18) 7%, transparent 20%),
    linear-gradient(to top, rgba(255, 0, 0, 0.32) 0%, rgba(255, 0, 0, 0.18) 7%, transparent 20%);
  animation: hit-flash-pulse 260ms ease-out forwards;
}

@keyframes hit-flash-pulse {
  0% {
    opacity: 0.0;
  }
  25% {
    opacity: 1.0;
  }
  100% {
    opacity: 0.0;
  }
}
</style>
