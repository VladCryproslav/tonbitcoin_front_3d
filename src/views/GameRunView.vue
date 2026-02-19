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
        
        <!-- Индикатор загрузки моделей -->
        <div v-if="isLoadingModels" class="models-loading-container">
          <div class="loading-spinner"></div>
          <div class="loading-text">{{ t('game.loading_models') }}</div>
        </div>
        
        <!-- Кнопки действий (показываются после загрузки) -->
        <div v-else class="game-over-actions">
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
            <div class="training-button-content">
              {{ t('game.run_training') }} {{ trainingRunsAvailable ?? 5 }}/{{ maxTrainingRunsPerHour }}
            </div>
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
          <div v-else class="training-warning-container">
            <p class="training-warning-text">
              {{ t('game.training_warning') }}
            </p>
            <button
              class="btn-primary btn-primary--wide"
              @click.stop.prevent="exitToMain"
            >
              {{ t('game.back_to_main') }}
            </button>
          </div>
          
          <!-- Кнопка покупки дополнительной жизни -->
          <button
            v-if="canBuyExtraLife && extraLifePrice > 0"
            class="btn-primary btn-primary--wide btn-extra-life"
            :disabled="isBuyingExtraLife"
            @click.stop.prevent="handleBuyExtraLife"
          >
            <span v-if="!isBuyingExtraLife" style="display: inline-flex; align-items: center; gap: 6px; white-space: nowrap;">
              <span>{{ t('game.buy_extra_life') }}</span>
              <span style="display: inline-flex; align-items: center; gap: 4px;">
                {{ extraLifePrice }}
                <img src="@/assets/stars.png" width="16px" alt="Stars" style="display: inline-block; vertical-align: middle;" />
              </span>
            </span>
            <span v-else>{{ t('game.processing') }}</span>
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

    <!-- Модалка предупреждения о лимите тренировочных забегов -->
    <ModalNew
      v-if="showTrainingLimitModal"
      status="warning"
      :title="t('notification.st_attention')"
      :body="t('game.training_run_limit_exceeded', { used: trainingRunsUsedThisHour, max: maxTrainingRunsPerHour })"
      @close="showTrainingLimitModal = false"
    />

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

    <!-- Модальное окно предупреждения перед стартом забега -->
    <StartRunWarningModal
      v-if="showStartRunWarning"
      :control-mode="controlMode"
      @update:control-mode="handleStartRunControlModeUpdate"
      @confirm="handleStartRunWarningConfirm"
      @cancel="handleStartRunWarningCancel"
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
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import GameScene from '@/components/game/GameScene.vue'
import GameUI from '@/components/game/GameUI.vue'
import GameControls from '@/components/game/GameControls.vue'
import VirtualControls from '@/components/game/VirtualControls.vue'
import InfoModal from '@/components/InfoModal.vue'
import OverheatGameRunModal from '@/components/OverheatGameRunModal.vue'
import StartRunWarningModal from '@/components/StartRunWarningModal.vue'
import ModalNew from '@/components/ModalNew.vue'
import { useGameRun } from '@/composables/useGameRun'
import { useGamePhysics } from '@/composables/useGamePhysics'
import { useGameWorld } from '@/composables/useGameWorld'
import { useGameEffects } from '@/composables/useGameEffects'
import { useAppStore } from '@/stores/app'
import { host } from '@/../axios.config'
import { useTelegram } from '@/services/telegram'
import { runnerExtraLifeStarsEnabled } from '@/services/data'

const router = useRouter()
const { t } = useI18n()
const app = useAppStore()
const { tg } = useTelegram()

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
// Данные о доступности тренировочных забегов
const trainingRunsAvailable = ref(5) // По умолчанию 5
const maxTrainingRunsPerHour = ref(5)
const trainingRunsUsedThisHour = ref(0)
const canRunTraining = ref(true)
// Модалка предупреждения о лимите тренировочных забегов
const showTrainingLimitModal = ref(false)
// Данные завершенного забега для начисления при нажатии "Забрать"
const completedRunData = ref(null) // { energy_collected, is_win, energy_gained }
// Сохраненное значение собранной энергии для отображения в модалке (не обнуляется до нажатия "Забрать")
const savedEnergyCollectedForModal = ref(0)
// Сохраненное значение начального storage для расчета цены дополнительной жизни
const savedStartStorageForExtraLife = ref(0)
// Логика расчета уровней инженеров для модалки проигрыша
// Используем engineer_level и past_engineer_level для определения белых и золотых инженеров
const getWorkers = computed(() => {
  const engineerLevel = app?.user?.engineer_level ?? 0
  const pastEngineerLevel = app?.user?.past_engineer_level ?? 0
  
  let simple = 0
  let gold = 0
  
  // Логика согласно требованиям:
  if (engineerLevel <= 49 && engineerLevel < pastEngineerLevel) {
    // Случай 1: engineer_level <= 49 и < past_engineer_level
    // Белые: уровень = engineer_level (например, 38)
    simple = engineerLevel
    // Золотые: уровень = past_engineer_level - 49
    gold = pastEngineerLevel > 49 ? pastEngineerLevel - 49 : 0
  } else if (engineerLevel > 49 && engineerLevel < pastEngineerLevel) {
    // Случай 2: engineer_level > 49 но < past_engineer_level
    // Белые: уровень 49, процент 49%
    simple = 49
    // Золотые: уровень = past_engineer_level - 49 (используем past_engineer_level, а не engineer_level)
    gold = pastEngineerLevel > 49 ? pastEngineerLevel - 49 : 0
  } else if (engineerLevel > 49 && engineerLevel >= pastEngineerLevel) {
    // Случай 3: engineer_level > 49 и >= past_engineer_level
    // Белые: уровень 49, процент 49%
    simple = 49
    // Золотые: уровень = engineer_level - 49
    gold = engineerLevel - 49
  } else {
    // Остальные случаи (engineer_level <= 49 и >= past_engineer_level или past_engineer_level отсутствует)
    // Белые: уровень = engineer_level (если <= 49), иначе 49
    simple = engineerLevel <= 49 ? engineerLevel : 49
    gold = 0
  }
  
  return { simple, gold, all: simple + gold }
})

const whiteEngineerLevel = computed(() => getWorkers.value.simple)
const goldEngineerLevel = computed(() => getWorkers.value.gold)

// Процент сохранения для белых инженеров
// Берем процент с уровня белых инженеров (может быть engineer_level или 49)
const whiteEngineerSavedPercent = computed(() => {
  const level = getWorkers.value.simple
  if (!level) return 0
  // Используем процент с уровня белых инженеров
  const cfg = app.stations?.eng_configs?.find((el) => el?.level === level)
  return Number(cfg?.saved_percent_on_lose ?? 0)
})

// Процент сохранения для золотых инженеров
// Вычисляем как разницу между процентом для уровня золотых инженеров и процентом для уровня 49
const goldEngineerBonusPercent = computed(() => {
  const engineerLevel = app?.user?.engineer_level ?? 0
  const pastEngineerLevel = app?.user?.past_engineer_level ?? 0
  
  let goldLevel = 0
  let totalLevel = 0 // Общий уровень для расчета процента
  
  // Определяем уровень золотых инженеров и общий уровень согласно логике
  if (engineerLevel <= 49 && engineerLevel < pastEngineerLevel) {
    // Случай 1: engineer_level <= 49 и < past_engineer_level
    // Золотые = past_engineer_level - 49, общий = past_engineer_level
    goldLevel = pastEngineerLevel > 49 ? pastEngineerLevel - 49 : 0
    totalLevel = pastEngineerLevel
  } else if (engineerLevel > 49 && engineerLevel < pastEngineerLevel) {
    // Случай 2: engineer_level > 49 но < past_engineer_level
    // Золотые = past_engineer_level - 49, общий = past_engineer_level (используем past_engineer_level, а не engineer_level)
    goldLevel = pastEngineerLevel > 49 ? pastEngineerLevel - 49 : 0
    totalLevel = pastEngineerLevel
  } else if (engineerLevel > 49 && engineerLevel >= pastEngineerLevel) {
    // Случай 3: engineer_level > 49 и >= past_engineer_level
    // Золотые = engineer_level - 49, общий = engineer_level
    goldLevel = engineerLevel - 49
    totalLevel = engineerLevel
  } else {
    // Нет золотых инженеров
    return 0
  }
  
  if (goldLevel === 0) return 0
  
  // Получаем процент для общего уровня (past_engineer_level или engineer_level)
  const totalLevelCfg = app.stations?.eng_configs?.find((el) => el?.level === totalLevel)
  const totalLevelPercent = Number(totalLevelCfg?.saved_percent_on_lose ?? 0)
  
  // Для случая 1: вычитаем процент уровня 49
  // Для случаев 2 и 3: также вычитаем процент уровня 49
  const level49Cfg = app.stations?.eng_configs?.find((el) => el?.level === 49)
  const level49Percent = Number(level49Cfg?.saved_percent_on_lose ?? 0)
  
  // Бонус золотых = процент общего уровня - процент уровня 49
  return Math.max(0, totalLevelPercent - level49Percent)
})

// Эффективный процент при проигрыше — сумма белых и золотых инженеров
const effectiveSavedPercentOnLose = computed(() => {
  const whitePercent = whiteEngineerSavedPercent.value
  const goldPercent = goldEngineerBonusPercent.value
  return whitePercent + goldPercent
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

// Состояние загрузки моделей раннера
const isLoadingModels = ref(true)

// Состояние перегрева
const showOverheatModal = ref(false)
const showStartRunWarning = ref(false)

// Проверка настройки "не показывать предупреждение"
const shouldShowStartRunWarning = () => {
  try {
    const saved = localStorage.getItem('startRunWarningDontShow')
    const result = saved !== 'true'
    console.log('[GameRunView] shouldShowStartRunWarning check:', { saved, result })
    return result
  } catch (e) {
    console.error('[GameRunView] Error checking localStorage:', e)
    return true // По умолчанию показываем предупреждение
  }
}

const overheatedUntil = ref(null)
const isOverheated = ref(false)
let overheatCheckInterval = null
const overheatEnergyCollected = ref(0)
const overheatGoal = ref(null)
const wasOverheated = ref(false)
const overheatCountdown = ref(null) // Обратный отсчет перед показом модалки (5, 4, 3, 2, 1)
let overheatCountdownInterval = null
const overheatDecelerating = ref(false) // Флаг плавной остановки при перегреве (с 3 до 1 секунды)
const overheatProtectionActive = ref(false) // Флаг защиты от коллизий и мигания во время перегрева и после
let overheatProtectionEndTime = 0 // Время окончания защиты (3 секунды после таймера 3-2-1)

// Плавное ускорение после паузы/перегрева
const isAccelerating = ref(false) // Флаг плавного разгона после таймера
const targetSpeed = ref(0.15) // Целевая скорость для разгона
const savedSpeed = ref(0.15) // Сохраненная скорость перед остановкой
const accelerationStartTime = ref(0) // Время начала ускорения
const ACCELERATION_DURATION_MS = 3000 // Длительность разгона (3 секунды)

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
let timeAccumulator = 0 // Аккумулятор времени для фиксированного шага (исправление проблемы с разным FPS на iOS/Android)
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

// Предзагрузка всех моделей раннера (включая персонажа)
const preloadAllModels = async () => {
  if (!scene) {
    console.warn('Scene not ready for model preloading')
    isLoadingModels.value = false
    return
  }

  // Если модели уже загружены, пропускаем загрузку
  if (!isLoadingModels.value && gameWorld.value && gamePhysics.value?.playerMesh?.()) {
    return
  }

  try {
    isLoadingModels.value = true

    // Инициализация игрового мира (если еще не инициализирован)
    if (!gameWorld.value) {
      gameWorld.value = useGameWorld(scene)
      gameWorld.value.createRoad()
    }

    // Инициализация физики (если еще не инициализирована)
    if (!gamePhysics.value) {
      gamePhysics.value = useGamePhysics(scene)
    }

    // Загружаем все модели параллельно для ускорения (включая персонажа)
    await Promise.all([
      // Барьеры и токены
      gameWorld.value.loadBarrierModels(),
      // Забор
      gameWorld.value.loadFenceModel(),
      // Модель игрока (загружаем и добавляем в сцену сразу)
      (async () => {
        // Загружаем модель игрока только если еще не загружена
        const currentMesh = gamePhysics.value.playerMesh?.()
        if (!currentMesh) {
          console.log('Loading player model in preload...')
          const model = await gamePhysics.value.loadPlayerModel(scene, '/models/main.glb')
          if (model) {
            console.log('Player model loaded successfully in preload:', model)
            // Убеждаемся, что модель видна
            model.visible = true
          } else {
            console.warn('Player model failed to load in preload')
          }
          return model
        }
        console.log('Player model already loaded:', currentMesh)
        return currentMesh
      })()
    ])

    console.log('All runner models preloaded successfully (including player)')
  } catch (error) {
    console.error('Error preloading models:', error)
    // Продолжаем работу даже при ошибке загрузки моделей
  } finally {
    isLoadingModels.value = false
  }
}

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

  // Инициализация физики (нужна для предзагрузки персонажа)
  gamePhysics.value = useGamePhysics(scene)
  
  // Предзагрузка всех моделей (барьеры, токены, забор, персонаж)
  await preloadAllModels()

  // Проверяем, что персонаж загрузился, и если нет - создаем fallback
  const playerMesh = gamePhysics.value.playerMesh?.()
  if (!playerMesh) {
    console.warn('Player model not loaded in preload, creating fallback')
    gamePhysics.value.createPlayer(scene, '/models/main.glb')
  } else {
    console.log('Player model loaded successfully in preload:', playerMesh)
    // Убеждаемся, что модель видна и находится в правильной позиции
    playerMesh.visible = true
    playerMesh.position.set(0, 0, 0)
  }

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

    // Обновляем время кадра всегда (нужно для камеры и других систем)
    const now = nowGlobal
    if (lastUpdateTime <= 0) {
      lastUpdateTime = now
      timeAccumulator = 0 // Сбрасываем аккумулятор при первом кадре
    }

    // Защита от аномальных значений frameTime (слишком маленькие или большие скачки)
    let frameTime = now - lastUpdateTime
    // Ограничиваем сверху для защиты от больших скачков (например, при переключении вкладок)
    frameTime = Math.min(frameTime, 100)
    // Ограничиваем снизу для защиты от слишком маленьких значений (может вызывать проблемы)
    frameTime = Math.max(frameTime, 1)
    lastUpdateTime = now

    // EMA по времени кадра для адаптивного DPR (используем реальный frameTime)
    frameTimeEMA = frameTimeEMA * 0.9 + frameTime * 0.1
    lastFrameDtSec = frameTime / 1000

    // 1) Физика всегда обновляется (для камеры, анимаций персонажа и т.д.)
    // ИСПРАВЛЕНИЕ: Используем реальный frameTime для анимаций, чтобы они синхронизировались с частотой кадров экрана
    // На Android с 120Hz анимации будут обновляться чаще, но с меньшим deltaTime, что даст правильную скорость
    if (gamePhysics.value) {
      const baseFrameContext = { nowMs: nowGlobal, deltaMs: frameTime, fixedSteps: 1 }
      gamePhysics.value.update(baseFrameContext)
    }

    // 2) Игровая логика в том же rAF (фикс. шаг). playerBox один раз за кадр — меньше setFromObject при наборе скорости.
    if (gameRun.isRunning.value && !gameRun.isPaused.value && !isDead.value) {
      // ИСПРАВЛЕНИЕ: Используем аккумулятор времени для фиксированного шага
      // Это гарантирует одинаковую скорость независимо от FPS (60Hz на iPhone vs 120Hz на Android)
      // На Android с 120 FPS frameTime будет ~8ms, но мы накапливаем время и выполняем шаги только когда накопилось достаточно
      timeAccumulator += frameTime

      const nowMs = now
      const slideStartTime = gamePhysics.value?.getSlideStartTime?.() ?? 0
      const inRollImmuneWindow = slideStartTime > 0 && nowMs - slideStartTime < ROLL_IMMUNE_MS

      // Выполняем фиксированные шаги только когда накопилось достаточно времени
      // Это гарантирует одинаковую скорость на всех платформах независимо от FPS
      let stepsCount = 0
      while (timeAccumulator >= FIXED_STEP_MS && stepsCount < MAX_STEPS) {
        timeAccumulator -= FIXED_STEP_MS
        stepsCount++
      }

      // ОПТИМИЗАЦИЯ: На iPhone с 60Hz предотвращаем микрофризы
      // Если frameTime близок к фиксированному шагу (нормальный 60Hz), всегда выполняем минимум 1 шаг
      // Это гарантирует плавность - на iPhone frameTime ≈ 16.67ms, что равно FIXED_STEP_MS
      // На Android с 120Hz frameTime будет ~8ms, поэтому это условие не сработает и аккумулятор будет работать правильно
      if (stepsCount === 0 && frameTime >= FIXED_STEP_MS * 0.85) {
        // Выполняем 1 шаг, вычитая из аккумулятора (может уйти в небольшой минус, но компенсируется в следующих кадрах)
        stepsCount = 1
        timeAccumulator -= FIXED_STEP_MS
        // Ограничиваем аккумулятор снизу, чтобы не накапливать слишком большой долг
        // Используем более мягкое ограничение для плавности
        if (timeAccumulator < -FIXED_STEP_MS * 0.3) {
          timeAccumulator = -FIXED_STEP_MS * 0.3
        }
      }

      // Защита от накопления слишком большого долга в аккумуляторе
      // Если аккумулятор ушел слишком далеко в минус, постепенно компенсируем
      if (timeAccumulator < -FIXED_STEP_MS * 2) {
        timeAccumulator = -FIXED_STEP_MS * 2
      }

      // Выполняем шаги только если они есть (оптимизация: не вызываем getPlayerBox лишний раз)
      if (stepsCount > 0) {
        const framePlayerBox = gamePhysics.value?.getPlayerBox?.() ?? null
        const frameContext = { nowMs, deltaMs: FIXED_STEP_MS * stepsCount, fixedSteps: stepsCount }

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

        if (gameEffects.value) {
          const q = graphicsQuality.value
          if (q === 'normal' || q === 'medium') {
            gameEffects.value.updateEffects(frameContext)
          }
        }
      }
      // Плавное ускорение после паузы/перегрева (за 3 секунды до целевой скорости)
      // Обновляем скорость один раз за кадр (не в фиксированных шагах)
      // Скорость дороги и дистанция обновляются автоматически в фиксированных шагах выше
      if (isAccelerating.value) {
        const elapsed = nowGlobal - accelerationStartTime.value
        const progress = Math.min(elapsed / ACCELERATION_DURATION_MS, 1) // От 0 до 1

        // Начальная скорость разгона = сохраненная скорость - 40%, но не меньше минимальной 0.15
        const MIN_START_SPEED = 0.15
        const startAccelSpeed = Math.max(savedSpeed.value * 0.6, MIN_START_SPEED)

        // Упрощенная плавная интерполяция (квадратичная ease-out - быстрее чем кубическая)
        // Используем простую формулу без Math.pow для оптимизации производительности
        const easeOutProgress = progress < 1 ? progress * (2 - progress) : 1
        gameSpeed.value = startAccelSpeed + (targetSpeed.value - startAccelSpeed) * easeOutProgress

        // Если достигли целевой скорости - завершаем разгон
        if (progress >= 1) {
          gameSpeed.value = targetSpeed.value
          isAccelerating.value = false
        }
      }

      // Проверяем окончание защиты от коллизий (2 секунды после таймера 3-2-1)
      if (overheatProtectionActive.value && overheatProtectionEndTime > 0) {
        const now = performance.now()
        if (now >= overheatProtectionEndTime) {
          // Защита закончилась - выключаем мигание и включаем коллизии
          overheatProtectionActive.value = false
          overheatProtectionEndTime = 0
          if (gamePhysics.value?.setBlinking) {
            gamePhysics.value.setBlinking(false)
          }
        }
      } else if (!winTriggered && !winDecelerating && winAnimationStartTime === 0) {
        // Плавный набор скорости на основе прогресса дистанции (один раз на кадр, не на шаг)
        // Не применяем если идет плавное ускорение после паузы/перегрева

        // НАСТРОЙКА СКОРОСТИ - можно менять эти значения:
        const BASE_SPEED = 0.15        // Минимальная скорость (старт)
        const MID_SPEED = 0.30         // Скорость на 60% дистанции
        const MAX_SPEED = 0.36         // Максимальная скорость (с 90%)
        const FIRST_RAMP_END = 60      // Процент дистанции, до которого идет первый набор (0% -> 60%)
        const SECOND_RAMP_END = 90     // Процент дистанции, до которого идет второй набор (60% -> 90%)

        const progress = (gameRun.distanceProgress?.value ?? 0) / 100

        let targetSpeed
        if (progress <= FIRST_RAMP_END / 100) {
          // Этап 1: от 0% до 60% - набор с BASE_SPEED до MID_SPEED
          const rampProgress = progress / (FIRST_RAMP_END / 100)
          targetSpeed = BASE_SPEED + (MID_SPEED - BASE_SPEED) * rampProgress
        } else if (progress <= SECOND_RAMP_END / 100) {
          // Этап 2: от 60% до 90% - набор с MID_SPEED до MAX_SPEED
          const rampProgress = (progress - FIRST_RAMP_END / 100) / ((SECOND_RAMP_END - FIRST_RAMP_END) / 100)
          targetSpeed = MID_SPEED + (MAX_SPEED - MID_SPEED) * rampProgress
        } else {
          // Этап 3: с 90% и далее - постоянная MAX_SPEED
          targetSpeed = MAX_SPEED
        }

        gameSpeed.value = 0.92 * gameSpeed.value + 0.08 * targetSpeed
      }
      // ОПТИМИЗАЦИЯ: Спавн объектов только когда есть шаги (экономит вычисления на Android с 120Hz)
      // На Android с 120Hz это предотвращает лишние вызовы spawnObjects при stepsCount = 0
      if (gameWorld.value && stepsCount > 0) {
        gameWorld.value.spawnObjects(playerZ.value, gameRun.getNextEnergyPoint)
      }
      if (hitCount.value >= 3 && !isDead.value) {
        isDead.value = true
        // Сохраняем скорость перед смертью (для восстановления после покупки жизни)
        savedSpeed.value = gameSpeed.value || 0.15
        // Сохраняем начальный storage для расчета цены дополнительной жизни
        if (gameRun.startStorage?.value) {
          savedStartStorageForExtraLife.value = gameRun.startStorage.value
        }
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
    // ОПТИМИЗАЦИЯ: Используем кэшированное значение lastFrameDtSec для стабильности
    if (camera && gamePhysics.value?.getCameraLaneX) {
      // Ограничиваем dt для защиты от аномальных значений (например, при переключении вкладок)
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
    // ОПТИМИЗАЦИЯ: Проверяем только когда игра запущена (экономит вычисления)
    if (renderer && gameRun.isRunning.value) {
      const q = graphicsQuality.value
      const isLow = q === 'low'
      if (!isLow) {
        if (++dprAdjustCounter >= 30) {
          dprAdjustCounter = 0
          // Более консервативные пороги для предотвращения частых изменений DPR
          // Это улучшает стабильность и предотвращает визуальные артефакты
          if (frameTimeEMA > 20 && dynamicPixelRatio > minPixelRatio) {
            dynamicPixelRatio = Math.max(minPixelRatio, dynamicPixelRatio - 0.1)
            renderer.setPixelRatio(dynamicPixelRatio)
          } else if (frameTimeEMA < 14 && dynamicPixelRatio < targetPixelRatio) {
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
  savedSpeed.value = 0.15 // Инициализируем сохраненную скорость
  isAccelerating.value = false // Сбрасываем флаг ускорения при новом старте
  overheatProtectionActive.value = false // Сбрасываем флаг защиты при новом старте
  overheatProtectionEndTime = 0 // Сбрасываем время окончания защиты
  // Выключаем мигающую прозрачность при новом старте
  if (gamePhysics.value?.setBlinking) {
    gamePhysics.value.setBlinking(false)
  }
  timeAccumulator = 0 // Сбрасываем аккумулятор времени при старте игры
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
  savedStartStorageForExtraLife.value = 0
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
    isAccelerating.value = false // Сбрасываем флаг ускорения
    overheatProtectionActive.value = false // Сбрасываем флаг защиты
    overheatProtectionEndTime = 0 // Сбрасываем время окончания защиты
    // Выключаем мигающую прозрачность
    if (gamePhysics.value?.setBlinking) {
      gamePhysics.value.setBlinking(false)
    }
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
      // Перегрев закончился - сбрасываем все флаги перегрева
      isOverheated.value = false
      overheatedUntil.value = null
      wasOverheated.value = false  // Сбрасываем флаг перегрева когда перегрев закончился
    }
  } else {
    // Нет активного перегрева - сбрасываем флаг если перегрев закончился
    isOverheated.value = false
    overheatedUntil.value = null
    // Если перегрев закончился, но флаг был установлен, сбрасываем его
    if (wasOverheated.value && !app.user?.overheated_until) {
      wasOverheated.value = false
    }
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

    // Когда таймер показывает 4 секунды - включаем защиту от коллизий и мигание
    if (overheatCountdown.value === 4) {
      overheatProtectionActive.value = true
      if (gamePhysics.value?.setBlinking) {
        gamePhysics.value.setBlinking(true)
      }
    }

    // Когда таймер показывает 2 секунды - начинаем плавное замедление
    if (overheatCountdown.value === 2) {
      console.log('[GameRunView] Overheat countdown at 2, starting smooth deceleration. Current speed:', gameSpeed.value)
      // Сохраняем текущую скорость перед началом замедления (для плавного разгона после возобновления)
      savedSpeed.value = gameSpeed.value
      overheatDecelerating.value = true
      // Мигание и защита от коллизий уже включены с начала таймера
    }

    // Когда таймер показывает 1 секунду - останавливаем и показываем модалку
    if (overheatCountdown.value === 1) {
      console.log('[GameRunView] Overheat countdown at 1, stopping and showing modal')

      // Скорость уже сохранена на 2 секунде (перед началом замедления)
      // Вычисляем целевую скорость на основе текущего прогресса дистанции
      // НАСТРОЙКА СКОРОСТИ - можно менять эти значения:
      const BASE_SPEED = 0.15        // Минимальная скорость (старт)
      const MID_SPEED = 0.30         // Скорость на 60% дистанции
      const MAX_SPEED = 0.36         // Максимальная скорость (с 90%)
      const FIRST_RAMP_END = 60      // Процент дистанции, до которого идет первый набор (0% -> 60%)
      const SECOND_RAMP_END = 90     // Процент дистанции, до которого идет второй набор (60% -> 90%)

      const progress = (gameRun.distanceProgress?.value ?? 0) / 100

      if (progress <= FIRST_RAMP_END / 100) {
        // Этап 1: от 0% до 60% - набор с BASE_SPEED до MID_SPEED
        const rampProgress = progress / (FIRST_RAMP_END / 100)
        targetSpeed.value = BASE_SPEED + (MID_SPEED - BASE_SPEED) * rampProgress
      } else if (progress <= SECOND_RAMP_END / 100) {
        // Этап 2: от 60% до 90% - набор с MID_SPEED до MAX_SPEED
        const rampProgress = (progress - FIRST_RAMP_END / 100) / ((SECOND_RAMP_END - FIRST_RAMP_END) / 100)
        targetSpeed.value = MID_SPEED + (MAX_SPEED - MID_SPEED) * rampProgress
      } else {
        // Этап 3: с 90% и далее - постоянная MAX_SPEED
        targetSpeed.value = MAX_SPEED
      }

      // Останавливаем плавное замедление
      overheatDecelerating.value = false
      // Мигание и защита от коллизий продолжаются (не выключаем здесь)
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

  // Перегрев закончился или был снят азотом - сбрасываем флаг was_overheated на сервере
  try {
    await host.post('game-run-reset-overheat-flag/', {})
  } catch (error) {
    console.error('[GameRunView] Ошибка при сбросе флага перегрева:', error)
  }

  // Обновляем данные пользователя после сброса флага
  await app.initUser()

  // Перегрев закончился или был снят азотом, продолжаем забег
  isOverheated.value = false
  showOverheatModal.value = false
  overheatedUntil.value = app.user?.overheated_until ? new Date(app.user.overheated_until) : null
  wasOverheated.value = false // Сбрасываем локальный флаг перегрева
  overheatCountdown.value = null // Сбрасываем таймер
  overheatDecelerating.value = false // Сбрасываем флаг замедления
  isAccelerating.value = false // Сбрасываем флаг ускорения
  // Защита от коллизий и мигание продолжаются (не выключаем здесь)

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

  // Сохраняем текущую скорость перед паузой (для плавного разгона после возобновления)
  savedSpeed.value = gameSpeed.value

  // Вычисляем целевую скорость на основе текущего прогресса дистанции
  // НАСТРОЙКА СКОРОСТИ - можно менять эти значения:
  const BASE_SPEED = 0.15        // Минимальная скорость (старт)
  const MID_SPEED = 0.30         // Скорость на 60% дистанции
  const MAX_SPEED = 0.36         // Максимальная скорость (с 90%)
  const FIRST_RAMP_END = 60      // Процент дистанции, до которого идет первый набор (0% -> 60%)
  const SECOND_RAMP_END = 90     // Процент дистанции, до которого идет второй набор (60% -> 90%)

  const progress = (gameRun.distanceProgress?.value ?? 0) / 100

  if (progress <= FIRST_RAMP_END / 100) {
    // Этап 1: от 0% до 60% - набор с BASE_SPEED до MID_SPEED
    const rampProgress = progress / (FIRST_RAMP_END / 100)
    targetSpeed.value = BASE_SPEED + (MID_SPEED - BASE_SPEED) * rampProgress
  } else if (progress <= SECOND_RAMP_END / 100) {
    // Этап 2: от 60% до 90% - набор с MID_SPEED до MAX_SPEED
    const rampProgress = (progress - FIRST_RAMP_END / 100) / ((SECOND_RAMP_END - FIRST_RAMP_END) / 100)
    targetSpeed.value = MID_SPEED + (MAX_SPEED - MID_SPEED) * rampProgress
  } else {
    // Этап 3: с 90% и далее - постоянная MAX_SPEED
    targetSpeed.value = MAX_SPEED
  }

  // Сбрасываем флаг ускорения при паузе
  isAccelerating.value = false

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
  isAccelerating.value = false // Сбрасываем флаг ускорения
  // Защита от коллизий и мигание продолжаются (не выключаем здесь)

      // Мигание и защита от коллизий продолжаются во время таймера 3-2-1
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

      // Устанавливаем время окончания защиты только если защита активна (т.е. при перегреве)
      if (overheatProtectionActive.value) {
        overheatProtectionEndTime = performance.now() + 2000
      }

      gameRun.resumeRun()
      lastUpdateTime = 0
      launcherOverlayMode.value = 'none'

      // Вычисляем целевую скорость на основе текущего прогресса дистанции
      // НАСТРОЙКА СКОРОСТИ - можно менять эти значения:
      const BASE_SPEED = 0.15        // Минимальная скорость (старт)
      const MID_SPEED = 0.30         // Скорость на 60% дистанции
      const MAX_SPEED = 0.36         // Максимальная скорость (с 90%)
      const FIRST_RAMP_END = 60      // Процент дистанции, до которого идет первый набор (0% -> 60%)
      const SECOND_RAMP_END = 90     // Процент дистанции, до которого идет второй набор (60% -> 90%)

      const progress = (gameRun.distanceProgress?.value ?? 0) / 100

      if (progress <= FIRST_RAMP_END / 100) {
        // Этап 1: от 0% до 60% - набор с BASE_SPEED до MID_SPEED
        const rampProgress = progress / (FIRST_RAMP_END / 100)
        targetSpeed.value = BASE_SPEED + (MID_SPEED - BASE_SPEED) * rampProgress
      } else if (progress <= SECOND_RAMP_END / 100) {
        // Этап 2: от 60% до 90% - набор с MID_SPEED до MAX_SPEED
        const rampProgress = (progress - FIRST_RAMP_END / 100) / ((SECOND_RAMP_END - FIRST_RAMP_END) / 100)
        targetSpeed.value = MID_SPEED + (MAX_SPEED - MID_SPEED) * rampProgress
      } else {
        // Этап 3: с 90% и далее - постоянная MAX_SPEED
        targetSpeed.value = MAX_SPEED
      }

      // Начинаем плавное ускорение от -40% сохраненной скорости до целевой за 3 секунды
      // Но не меньше минимальной стартовой скорости 0.15
      const MIN_START_SPEED = 0.15
      const startAccelSpeed = Math.max(savedSpeed.value * 0.6, MIN_START_SPEED)
      gameSpeed.value = startAccelSpeed
      if (gameWorld.value) {
        gameWorld.value.setRoadSpeed(gameSpeed.value)
      }
      accelerationStartTime.value = performance.now() // Запоминаем время начала ускорения
      isAccelerating.value = true // Включаем флаг плавного разгона

      // Активируем анимацию бега персонажа
      // Мигание и защита от коллизий продолжаются еще 3 секунды
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
          // Также отключаем коллизии только во время защиты при перегреве (таймер 4-1, таймер 3-2-1, и 2 секунды после)
          // При паузе коллизии работают нормально
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
                // Сохраняем скорость перед смертью (для восстановления после покупки жизни)
                savedSpeed.value = gameSpeed.value || 0.15
                // Сохраняем начальный storage для расчета цены дополнительной жизни
                if (gameRun.startStorage?.value) {
                  savedStartStorageForExtraLife.value = gameRun.startStorage.value
                }
                // Сохраняем energyCollected ДО остановки игрового цикла
                // Ограничиваем значение максимумом storage (та же логика, что в счетчике энергии)
                const savedEnergyBeforeStop = Math.min(
                  gameRun.energyCollected?.value ?? 0,
                  gameRun.startStorage?.value ?? gameRun.currentStorage?.value ?? 0
                )
                // Сохраняем значение для модалки сразу при смерти
                savedEnergyCollectedForModal.value = savedEnergyBeforeStop

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
            inRollImmuneWindow,
            overheatProtectionActive.value || overheatDecelerating.value
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
  timeAccumulator = 0 // Сбрасываем аккумулятор времени при остановке
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

    // Обновляем доступность тренировочных забегов после завершения тренировочного забега
    if (isTrainingRun.value) {
      await checkTrainingRunAvailability()
    }

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
        }
        // Сохраняем startStorage если еще не сохранен
        if (!savedStartStorageForExtraLife.value && gameRun.startStorage?.value) {
          savedStartStorageForExtraLife.value = gameRun.startStorage.value
        }
        // Убеждаемся что данные установлены перед показом модалки
        await nextTick()
        gameOverType.value = 'lose'
        showGameOver.value = true
        launcherOverlayMode.value = 'none'
        // Вызываем расчет цены после показа модалки (только если не тренировочный забег)
        await nextTick()
        if (canBuyExtraLife.value && !isTrainingRun.value) {
          calculateExtraLifePrice()
        }
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
  console.log('[GameRunView] handleStartClick called')
  // Проверяем нужно ли показывать предупреждение
  const shouldShow = shouldShowStartRunWarning()
  console.log('[GameRunView] shouldShowStartRunWarning:', shouldShow)
  if (shouldShow) {
    console.log('[GameRunView] Showing warning modal')
    showStartRunWarning.value = true
    return
  }

  // Если предупреждение не нужно показывать, сразу запускаем забег
  console.log('[GameRunView] Starting run without warning')
  await startRun()
}

// Функция для запуска забега (вынесена отдельно для использования из модалки)
const startRun = async () => {
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

// Обработчик подтверждения предупреждения
const handleStartRunWarningConfirm = (dontShowAgain) => {
  showStartRunWarning.value = false

  // Сохраняем настройку если пользователь выбрал "не показывать снова"
  if (dontShowAgain) {
    localStorage.setItem('startRunWarningDontShow', 'true')
  }

  // Запускаем забег
  startRun()
}

// Обработчик отмены предупреждения
const handleStartRunWarningCancel = () => {
  showStartRunWarning.value = false
}

// Обновление режима управления из модалки предупреждения (сохраняем в localStorage)
const handleStartRunControlModeUpdate = (mode) => {
  if (mode === 'swipes' || mode === 'buttons') {
    controlMode.value = mode
    if (typeof window !== 'undefined' && window.localStorage) {
      try {
        window.localStorage.setItem('game_control_mode', mode)
      } catch {
        // ignore
      }
    }
  }
}

// Функция для проверки доступности тренировочных забегов
const checkTrainingRunAvailability = async () => {
  try {
    const response = await host.get('training-run-check/')
    if (response && response.data) {
      trainingRunsAvailable.value = response.data.available_runs ?? 5
      maxTrainingRunsPerHour.value = response.data.max_runs_per_hour ?? 5
      trainingRunsUsedThisHour.value = response.data.runs_used_this_hour ?? 0
      canRunTraining.value = response.data.can_run ?? true
    }
  } catch (error) {
    // В случае ошибки не блокируем интерфейс - используем значения по умолчанию
    console.warn('Training run availability check failed, using defaults:', error?.message || error)
    // Устанавливаем значения по умолчанию, чтобы не блокировать интерфейс
    canRunTraining.value = true
    trainingRunsAvailable.value = 5
    maxTrainingRunsPerHour.value = 5
    trainingRunsUsedThisHour.value = 0
  }
}

const handleTrainingClick = async () => {
  // Проверяем доступность перед запуском
  if (!canRunTraining.value || (trainingRunsAvailable.value ?? 0) <= 0) {
    // Показываем желтую модалку предупреждения
    showTrainingLimitModal.value = true
    return
  }
  
  try {
    // Вызываем API для записи старта тренировочного забега
    const response = await host.post('training-run-start/')
    console.log('training-run-start response:', response.data)
    
    if (response.data.user) {
      // Обновляем данные пользователя если нужно
      if (response.data.user.training_run_count_this_hour !== undefined) {
        app.user.training_run_count_this_hour = response.data.user.training_run_count_this_hour
      }
      if (response.data.user.training_run_last_started_at !== undefined) {
        app.user.training_run_last_started_at = response.data.user.training_run_last_started_at
      }
    }
    
    // Обновляем счетчик доступных забегов
    trainingRunsAvailable.value = response.data.available_runs || 0
    trainingRunsUsedThisHour.value = response.data.runs_used_this_hour || 0
    
    // Запускаем тренировочный забег
    startGame(true)
  } catch (error) {
    // Если ошибка лимита - показываем модалку предупреждения
    if (error.response?.status === 400 && error.response?.data?.error === 'training_run_limit_exceeded') {
      const maxRuns = error.response.data.max_runs_per_hour || 5
      const usedRuns = error.response.data.runs_used_this_hour || 0
      maxTrainingRunsPerHour.value = maxRuns
      trainingRunsUsedThisHour.value = usedRuns
      trainingRunsAvailable.value = 0
      // Показываем желтую модалку предупреждения
      showTrainingLimitModal.value = true
      // Обновляем данные о доступности
      await checkTrainingRunAvailability()
      return
    }
    // Другие ошибки - запускаем игру всё равно (fallback)
    console.error('Error starting training run:', error)
    startGame(true)
  }
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

      // Вычисляем целевую скорость на основе текущего прогресса дистанции
      // НАСТРОЙКА СКОРОСТИ - можно менять эти значения:
      const BASE_SPEED = 0.15        // Минимальная скорость (старт)
      const MID_SPEED = 0.28         // Скорость на 60% дистанции
      const MAX_SPEED = 0.34         // Максимальная скорость (с 90%)
      const FIRST_RAMP_END = 60      // Процент дистанции, до которого идет первый набор (0% -> 60%)
      const SECOND_RAMP_END = 90     // Процент дистанции, до которого идет второй набор (60% -> 90%)

      const progress = (gameRun.distanceProgress?.value ?? 0) / 100

      if (progress <= FIRST_RAMP_END / 100) {
        // Этап 1: от 0% до 60% - набор с BASE_SPEED до MID_SPEED
        const rampProgress = progress / (FIRST_RAMP_END / 100)
        targetSpeed.value = BASE_SPEED + (MID_SPEED - BASE_SPEED) * rampProgress
      } else if (progress <= SECOND_RAMP_END / 100) {
        // Этап 2: от 60% до 90% - набор с MID_SPEED до MAX_SPEED
        const rampProgress = (progress - FIRST_RAMP_END / 100) / ((SECOND_RAMP_END - FIRST_RAMP_END) / 100)
        targetSpeed.value = MID_SPEED + (MAX_SPEED - MID_SPEED) * rampProgress
      } else {
        // Этап 3: с 90% и далее - постоянная MAX_SPEED
        targetSpeed.value = MAX_SPEED
      }

      gameRun.resumeRun()
      lastUpdateTime = 0

      // Начинаем плавное ускорение от -40% сохраненной скорости до целевой за 3 секунды
      // Но не меньше минимальной стартовой скорости 0.15
      const MIN_START_SPEED = 0.15
      const startAccelSpeed = Math.max(savedSpeed.value * 0.6, MIN_START_SPEED)
      gameSpeed.value = startAccelSpeed
      if (gameWorld.value) {
        gameWorld.value.setRoadSpeed(gameSpeed.value)
      }
      accelerationStartTime.value = performance.now() // Запоминаем время начала ускорения
      isAccelerating.value = true // Включаем флаг плавного разгона

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
      savedStartStorageForExtraLife.value = 0
      // Очищаем startStorage и energyCollected только после успешного начисления
      if (gameRun.startStorage) {
        gameRun.startStorage.value = 0
      }
      if (gameRun.energyCollected) {
        gameRun.energyCollected.value = 0
      }
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

// Состояние покупки дополнительной жизни
const isBuyingExtraLife = ref(false)
const extraLifePrice = ref(0)

// Проверка возможности покупки дополнительной жизни
const canBuyExtraLife = computed(() => {
  // Показываем кнопку только если:
  // 1. Забег завершен (showGameOver = true)
  // 2. Проигрыш (gameOverType = 'lose')
  // 3. Использованы все 3 жизни (livesLeft = 0)
  // 4. 4-я жизнь еще не использована (!app.user?.energy_run_extra_life_used)
  // 5. Забег был начат (gameRun.startStorage > 0)
  // 6. НЕ тренировочный забег (в тренировке покупка жизни не имеет смысла)
  if (!showGameOver.value || gameOverType.value !== 'lose') {
    return false
  }
  
  if (livesLeft.value > 0) {
    return false
  }
  
  if (app.user?.energy_run_extra_life_used) {
    return false
  }
  
  // В тренировочном забеге не показываем кнопку покупки жизни
  if (isTrainingRun.value) {
    return false
  }
  
  // Проверяем сохраненное значение или текущее значение startStorage
  const startStorage = savedStartStorageForExtraLife.value || gameRun.startStorage?.value || 0
  if (startStorage <= 0) {
    return false
  }
  
  return true
})

// Расчет остатка энергии и цены
const calculateExtraLifePrice = async () => {
  if (!canBuyExtraLife.value) {
    extraLifePrice.value = 0
    return
  }
  
  try {
    // Остаток = начальный storage - собранная энергия
    // Используем сохраненное значение startStorage, так как оно может быть очищено
    const startStorage = savedStartStorageForExtraLife.value || gameRun.startStorage?.value || 0
    const collectedEnergy = savedEnergyCollectedForModal.value || 0
    const remainingEnergy = Math.max(0, startStorage - collectedEnergy)
    
    if (remainingEnergy <= 0) {
      extraLifePrice.value = 0
      return
    }
    
    // Запрашиваем цену с сервера
    const response = await host.post('runner-extra-life-stars/', {
      remaining_energy: remainingEnergy
    })
    
    if (response.status === 200 && response.data?.price) {
      extraLifePrice.value = response.data.price
    } else {
      extraLifePrice.value = 0
    }
  } catch (error) {
    console.error('[calculateExtraLifePrice] Error calculating extra life price:', error)
    extraLifePrice.value = 0
  }
}

// Обработчик покупки дополнительной жизни
const handleBuyExtraLife = async () => {
  if (isBuyingExtraLife.value || !canBuyExtraLife.value) {
    return
  }
  
  // Проверка флага активности функционала
  if (!runnerExtraLifeStarsEnabled) {
    alert(t('game.extra_life_unavailable'))
    return
  }
  
  isBuyingExtraLife.value = true
  
  try {
    // Расчет остатка энергии
    // Используем сохраненное значение startStorage, так как оно может быть очищено
    const startStorage = savedStartStorageForExtraLife.value || gameRun.startStorage?.value || 0
    const collectedEnergy = savedEnergyCollectedForModal.value || 0
    const remainingEnergy = Math.max(0, startStorage - collectedEnergy)
    
    // Получаем invoice ссылку
    const response = await host.post('runner-extra-life-stars/', {
      remaining_energy: remainingEnergy
    })
    
    if (response.status === 200 && response.data?.link) {
      const invoiceLink = response.data.link
      
      // Сохраняем флаг что мы ожидаем оплату (чтобы не закрывать модалку)
      let paymentInProgress = true
      let paymentProcessed = false
      
      // Функция активации жизни после оплаты
      // ВАЖНО: Согласно документации Telegram, мы должны начислять жизнь ТОЛЬКО после получения
      // successful_payment от Telegram Bot. Эта функция вызывается только когда мы УЖЕ знаем,
      // что Telegram Bot обработал платеж (через polling или callback)
      const activateExtraLife = async () => {
        if (paymentProcessed) {
          return
        }
        paymentProcessed = true
        paymentInProgress = false
        
        try {
          // Проверяем что Telegram Bot действительно обработал платеж
          await app.initUser()
          
          if (!app.user?.energy_run_extra_life_used) {
            // Если Telegram Bot еще не обработал платеж, ждем еще немного
            await new Promise(resolve => setTimeout(resolve, 2000))
            await app.initUser()
            
            if (!app.user?.energy_run_extra_life_used) {
              throw new Error('Telegram Bot has not processed the payment. Please wait or contact support.')
            }
          }
          
          // Telegram Bot обработал платеж, восстанавливаем забег
          await restoreRunAfterExtraLife()
          
          isBuyingExtraLife.value = false
        } catch (error) {
          console.error('[handleBuyExtraLife] Error activating extra life:', error)
          // Показываем ошибку пользователю
          alert(t('game.extra_life_activation_error') + ': ' + (error.response?.data?.error || error.message))
          isBuyingExtraLife.value = false
          paymentProcessed = false
          paymentInProgress = true // Продолжаем polling на случай если платеж обработается позже
        }
      }
      
      tg.openInvoice(invoiceLink, async (status) => {
        // Проверяем статус (может быть 'paid' или другие значения)
        if (status === 'paid' || status === 'PAID' || status === true || status === 'success') {
          await activateExtraLife()
        } else if (status === 'cancelled' || status === 'failed' || status === false) {
          paymentInProgress = false
          isBuyingExtraLife.value = false
        }
      })
      
      // Polling для проверки статуса оплаты (на случай если callback не вызывается)
      let pollingStartTime = Date.now()
      const checkPaymentStatus = async () => {
        if (!paymentInProgress || paymentProcessed) return
        
        try {
          // Обновляем данные пользователя чтобы проверить статус
          await app.initUser()
          
          if (app.user?.energy_run_extra_life_used) {
            await activateExtraLife()
          }
        } catch (error) {
          console.error('[handleBuyExtraLife] Error checking payment status:', error)
        }
      }
      
      // Проверяем статус каждые 2 секунды в течение 60 секунд
      let pollingAttempts = 0
      const maxPollingAttempts = 30 // 60 секунд / 2 секунды
      
      const pollingInterval = setInterval(() => {
        pollingAttempts++
        
        if (!paymentInProgress || paymentProcessed) {
          clearInterval(pollingInterval)
          return
        }
        checkPaymentStatus()
      }, 2000)
      
      // Останавливаем polling через 60 секунд
      setTimeout(() => {
        clearInterval(pollingInterval)
        if (paymentInProgress && !paymentProcessed) {
          paymentInProgress = false
          isBuyingExtraLife.value = false
          alert('Платеж не был обработан. Пожалуйста, проверьте статус в профиле или обратитесь в поддержку.')
        }
      }, 60000)
    } else {
      console.error('Failed to get invoice link')
      isBuyingExtraLife.value = false
    }
  } catch (error) {
    console.error('Error buying extra life:', error)
    isBuyingExtraLife.value = false
  }
}

// Восстановление забега после покупки жизни
const restoreRunAfterExtraLife = async () => {
  // Сохраняем текущую скорость перед восстановлением (если не сохранена)
  if (!savedSpeed.value || savedSpeed.value === 0.15) {
    savedSpeed.value = gameSpeed.value || 0.15
  }
  
  // Закрываем модалку проигрыша
  showGameOver.value = false
  gameOverType.value = null
  
  // Сбрасываем состояние смерти
  isDead.value = false
  hitCount.value = 0 // Восстанавливаем жизни (теперь у нас 1 жизнь)
  
  // Показываем таймер обратного отсчета 3-2-1 (как при выходе из перегрева)
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
      // Таймер закончился, возобновляем забег
      clearInterval(countdownInterval)
      countdownInterval = null
      showCountdown.value = false
      
      // Устанавливаем время окончания защиты от коллизий (2 секунды)
      overheatProtectionActive.value = true
      overheatProtectionEndTime = performance.now() + 2000
      
      // Включаем мигание персонажа
      if (gamePhysics.value?.setBlinking) {
        gamePhysics.value.setBlinking(true)
      }
      
      // Возобновляем забег
      gameRun.resumeRun()
      lastUpdateTime = 0
      launcherOverlayMode.value = 'none'
      
      // Восстанавливаем скорость на основе текущего прогресса
      const BASE_SPEED = 0.15
      const MID_SPEED = 0.30
      const MAX_SPEED = 0.36
      const FIRST_RAMP_END = 60
      const SECOND_RAMP_END = 90
      
      const progress = (gameRun.distanceProgress?.value ?? 0) / 100
      
      if (progress <= FIRST_RAMP_END / 100) {
        const rampProgress = progress / (FIRST_RAMP_END / 100)
        targetSpeed.value = BASE_SPEED + (MID_SPEED - BASE_SPEED) * rampProgress
      } else if (progress <= SECOND_RAMP_END / 100) {
        const rampProgress = (progress - FIRST_RAMP_END / 100) / ((SECOND_RAMP_END - FIRST_RAMP_END) / 100)
        targetSpeed.value = MID_SPEED + (MAX_SPEED - MID_SPEED) * rampProgress
      } else {
        targetSpeed.value = MAX_SPEED
      }
      
      // Начинаем плавное ускорение
      const MIN_START_SPEED = 0.15
      const currentSavedSpeed = savedSpeed.value || 0.15
      const startAccelSpeed = Math.max(currentSavedSpeed * 0.6, MIN_START_SPEED)
      gameSpeed.value = startAccelSpeed
      if (gameWorld.value) {
        gameWorld.value.setRoadSpeed(gameSpeed.value)
      }
      accelerationStartTime.value = performance.now()
      isAccelerating.value = true
      
      // Активируем анимацию бега
      if (gamePhysics.value?.setAnimationState) {
        gamePhysics.value.setAnimationState('running')
      }
      
      // Выключаем мигание через 2 секунды
      setTimeout(() => {
        if (gamePhysics.value?.setBlinking) {
          gamePhysics.value.setBlinking(false)
        }
        overheatProtectionActive.value = false
      }, 2000)
      
      // Финальная вибрация
      if (vibrationEnabled.value) {
        try {
          const tg = window.Telegram?.WebApp
          tg?.HapticFeedback?.impactOccurred?.('heavy')
        } catch {
          // ignore
        }
        if (typeof navigator !== 'undefined' && navigator.vibrate) {
          navigator.vibrate(100)
        }
      }
    }
  }, 1000)
}

// Вычисляем цену при изменении состояния
watch([showGameOver, gameOverType, livesLeft, savedEnergyCollectedForModal, () => gameRun.startStorage?.value, () => app.user?.energy_run_extra_life_used, isTrainingRun], () => {
  console.log('[watch] State changed:', {
    showGameOver: showGameOver.value,
    gameOverType: gameOverType.value,
    livesLeft: livesLeft.value,
    savedEnergyCollectedForModal: savedEnergyCollectedForModal.value,
    startStorage: gameRun.startStorage?.value,
    energy_run_extra_life_used: app.user?.energy_run_extra_life_used,
    isTrainingRun: isTrainingRun.value,
    canBuyExtraLife: canBuyExtraLife.value
  })
  if (canBuyExtraLife.value && !isTrainingRun.value) {
    calculateExtraLifePrice()
  } else {
    extraLifePrice.value = 0
  }
}, { immediate: true })

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

  // Проверяем доступность тренировочных забегов при монтировании (неблокирующий вызов)
  // Используем setTimeout чтобы не блокировать рендеринг
  setTimeout(() => {
    checkTrainingRunAvailability().catch(err => {
      console.error('Failed to check training run availability on mount:', err)
      // Не блокируем интерфейс при ошибке - используем значения по умолчанию
    })
  }, 100)

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

.training-button-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.btn-primary--training {
  background: linear-gradient(135deg, #f59e0b 0%, #ea580c 50%, #c2410c 100%);
  color: #fff;
  box-shadow: 0 12px 30px rgba(234, 88, 12, 0.4);
  border: 1px solid rgba(251, 146, 60, 0.4);

  &:active {
    box-shadow: 0 6px 18px rgba(234, 88, 12, 0.35);
  }

  &.btn-disabled {
    opacity: 0.6;
    cursor: not-allowed;
    pointer-events: none;
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


.btn-extra-life {
  background: linear-gradient(135deg, #e757ec 0%, #9851ec 50%, #5e7cea 100%);
  box-shadow: 0 12px 30px rgba(102, 126, 234, 0.45);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  
  &:hover:not(:disabled) {
    opacity: 0.9;
  }
  
  &:active:not(:disabled) {
    transform: scale(0.96);
    box-shadow: 0 6px 18px rgba(102, 126, 234, 0.35);
  }
  
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.game-over-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.models-loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px 20px;
  min-height: 200px;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(148, 163, 184, 0.2);
  border-top-color: #22d3ee;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-text {
  color: #9ca3af;
  font-size: 14px;
  font-weight: 500;
}

.training-warning-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.training-warning-text {
  color: #ffd700;
  font-size: 14px;
  font-weight: 600;
  text-align: center;
  margin: 0;
  padding: 0 16px;
  line-height: 1.4;
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
