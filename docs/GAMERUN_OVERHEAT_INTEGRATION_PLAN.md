# План интеграции системы перегревов в забег (GameRun)

## Обзор

Данный документ описывает план интеграции системы перегревов в режим забега (GameRun). Перегрев должен происходить во время забега на определенной станции в соответствии с требованиями из `OVERHEAT_SYSTEM_LOGIC.md`.

## Требования

### Функциональные требования:

1. **Триггер перегрева:** Определенное количество собранных kW (поинты) во время забега, аналогично логике тапов
2. **Остановка забега:** При перегреве персонаж останавливается как при нажатии кнопки паузы
3. **Модальное окно:** Показывается модальное окно уведомления о перегреве с кнопкой "Продолжить"
4. **Визуальный эффект:** Экран пульсирует красным цветом во время перегрева
5. **Кнопка "Продолжить":** 
   - Неактивна во время активного перегрева
   - Становится активной когда перегрев закончился
   - При нажатии персонаж продолжает бежать (как при отключении паузы)

### Технические требования:

- Использовать существующую логику перегрева из `OVERHEAT_SYSTEM_LOGIC.md`
- Не изменять логику расчета перегрева (использовать те же формулы)
- Интегрировать с существующей системой паузы/возобновления забега
- **Power больше не участвует в системе перегрева** - перегрев не влияет на power
- **Криокамера предотвращает перегрев** - если активна, перегрев не может активироваться
- **Азот можно использовать в модалке** - если доступен, показать кнопку для мгновенного снятия перегрева
- **Работа бустеров** - такая же как в текущей системе (Cryo, Autostart, Азот)

## Архитектура решения

### Компоненты системы:

1. **Отслеживание перегрева** - в `useGameRun.js` или `GameRunView.vue`
2. **Модальное окно перегрева** - новый компонент или модификация существующего
3. **Визуальный эффект пульсации** - CSS анимация
4. **API интеграция** - получение/обновление данных перегрева

## Детальный план реализации

### Этап 1: Добавление логики отслеживания перегрева

**Файл:** `src/composables/useGameRun.js` или `src/views/GameRunView.vue`

#### 1.1. Добавление состояния перегрева

```javascript
// В useGameRun.js или GameRunView.vue
const isOverheated = ref(false)
const overheatedUntil = ref(null) // DateTime когда перегрев закончится
const overheatEnergyCollected = ref(0) // Накопленная энергия для перегрева
const overheatGoal = ref(null) // Цель перегрева (null если не установлена)
const wasOverheated = ref(false) // Флаг что перегрев уже был
```

#### 1.2. Конфигурация перегревов по типам станций

```javascript
// Константа (можно вынести в отдельный файл или получить с сервера)
const OVERHEAT_HOURS_BY_TYPE = {
  "Thermal power plant": 4,        // station #3 - 6 перегревов в сутки
  "Geothermal power plant": 2,     // station #4 - 12 перегревов в сутки
  "Nuclear power plant": 2,       // station #5 - 12 перегревов в сутки
  "Thermonuclear power plant": 1,  // station #6 - 24 перегрева в сутки
  "Dyson Sphere": 1,               // station #7 - 24 перегрева в сутки
}
```

#### 1.3. Инициализация перегрева при старте забега

**Место:** В функции `startRun()` в `useGameRun.js` или `handleStartClick()` в `GameRunView.vue`

**Важно:** Используем данные из `app.user`, которые уже содержат состояние перегрева с сервера.

```javascript
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
```

#### 1.4. Обновление накопленной энергии при сборе поинтов

**Место:** В функции `collectEnergy()` в `useGameRun.js` НЕ изменяем. Вместо этого создаем отдельную функцию для обработки сбора поинтов с проверкой перегрева.

**Важно:** Проверка перегрева происходит через API при каждом сборе поинта. Логика перегрева полностью на сервере.
```

#### 1.5. Проверка триггера перегрева через API

**Место:** Новая функция в `useGameRun.js` или `GameRunView.vue`

**Важно:** Используем существующий endpoint для обновления перегрева. Логика перегрева полностью на сервере, фронтенд только отправляет количество собранной энергии.

```javascript
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

const activateOverheat = (serverData) => {
  // Останавливаем забег (как при паузе)
  pauseGame() // Используем существующую функцию паузы
  
  // Устанавливаем состояние перегрева из ответа сервера
  isOverheated.value = true
  
  if (serverData.overheated_until) {
    overheatedUntil.value = new Date(serverData.overheated_until)
  }
  
  wasOverheated.value = serverData.was_overheated || false
  overheatEnergyCollected.value = serverData.overheat_energy_collected || 0
  overheatGoal.value = serverData.overheat_goal
  
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
  
  // Показываем модальное окно перегрева
  showOverheatModal.value = true
}
```

### Этап 2: Создание модального окна перегрева

**Файл:** `src/components/OverheatGameRunModal.vue` (новый компонент)

#### 2.1. Структура компонента

```vue
<template>
  <div class="overheat-modal-mask" @click.self="handleBackdropClick">
    <div class="overheat-modal-wrapper">
      <div class="overheat-modal-container" :class="{ 'pulsing-red': isOverheatActive }">
        <div class="overheat-modal-header">
          <img src="@/assets/warning.png" width="74px" alt="Warning" />
          <h1>{{ t('game.overheat_title') }}</h1>
        </div>
        <div class="overheat-modal-body">
          <div class="overheat-message" v-html="t('game.overheat_desc')"></div>
          <div v-if="isOverheatActive" class="overheat-timer">
            {{ t('game.overheat_cooling_down') }}: {{ timeRemaining }}
          </div>
        </div>
        <div class="overheat-modal-actions">
          <!-- Кнопка использования азота (если доступен) -->
          <button
            v-if="isOverheatActive && canUseNitrogen"
            class="btn-primary btn-primary--wide btn-nitrogen"
            @click.stop.prevent="handleUseNitrogen"
            :disabled="isUsingNitrogen"
          >
            {{ t('game.use_nitrogen') }} ({{ nitrogenUsesLeft }})
          </button>
          
          <!-- Кнопка "Продолжить" -->
          <button
            class="btn-primary btn-primary--wide"
            :class="{ 'btn-disabled': isOverheatActive }"
            :disabled="isOverheatActive"
            @click.stop.prevent="handleContinue"
          >
            {{ t('game.continue') }}
          </button>
          
          <!-- Кнопка "Назад" (только когда перегрев закончился) -->
          <button
            v-if="!isOverheatActive"
            class="btn-primary btn-secondary btn-primary--wide"
            @click.stop.prevent="$emit('close')"
          >
            {{ t('game.back_to_main') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import { host } from '@/../axios.config'

const props = defineProps({
  overheatedUntil: {
    type: Date,
    required: true
  }
})

const emit = defineEmits(['continue', 'close'])

const { t } = useI18n()
const app = useAppStore()

const isOverheatActive = computed(() => {
  return props.overheatedUntil && new Date(props.overheatedUntil) > new Date()
})

// Проверка доступности азота
const canUseNitrogen = computed(() => {
  const user = app.user
  if (!user) return false
  
  // Проверяем наличие азота (azot_uses_left или azot_reward_balance)
  const totalNitrogen = (user.azot_uses_left || 0) + (user.azot_reward_balance || 0)
  return totalNitrogen > 0
})

const nitrogenUsesLeft = computed(() => {
  const user = app.user
  if (!user) return 0
  return (user.azot_uses_left || 0) + (user.azot_reward_balance || 0)
})

const isUsingNitrogen = ref(false)

const timeRemaining = computed(() => {
  if (!isOverheatActive.value) return ''
  const now = new Date()
  const until = new Date(props.overheatedUntil)
  const diff = until - now
  
  if (diff <= 0) return ''
  
  const minutes = Math.floor(diff / 60000)
  const seconds = Math.floor((diff % 60000) / 1000)
  return `${minutes}:${String(seconds).padStart(2, '0')}`
})

let timerInterval = null

onMounted(() => {
  // Обновляем таймер каждую секунду
  timerInterval = setInterval(() => {
    // Проверяем окончание перегрева
    if (!isOverheatActive.value) {
      clearInterval(timerInterval)
    }
  }, 1000)
})

onUnmounted(() => {
  if (timerInterval) {
    clearInterval(timerInterval)
  }
})

const handleContinue = () => {
  if (!isOverheatActive.value) {
    emit('continue')
  }
}

const handleUseNitrogen = async () => {
  if (isUsingNitrogen.value || !canUseNitrogen.value) {
    return
  }
  
  isUsingNitrogen.value = true
  
  try {
    // Активируем азот через существующий endpoint
    const response = await host.post('tasks/activate_booster/', {
      slug: 'azot',
      day_count: null // Азот не требует day_count
    })
    
    if (response.status === 200) {
      // Обновляем данные пользователя
      await app.initUser()
      
      // Перегрев снят, закрываем модалку и продолжаем забег
      emit('continue')
    } else {
      console.error('Failed to activate nitrogen:', response)
      // Можно показать ошибку пользователю
    }
  } catch (error) {
    console.error('Error activating nitrogen:', error)
    // Можно показать ошибку пользователю
  } finally {
    isUsingNitrogen.value = false
  }
}

const handleBackdropClick = () => {
  // Не закрываем при клике на backdrop во время перегрева
  if (!isOverheatActive.value) {
    emit('close')
  }
}
</script>

<style lang="scss" scoped>
.overheat-modal-mask {
  position: fixed;
  z-index: 9999;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
}

.overheat-modal-wrapper {
  width: 90%;
  max-width: 400px;
}

.overheat-modal-container {
  background: #10151b;
  border-radius: 1rem;
  padding: 2rem;
  box-shadow: inset 0 0 0 1px #ff3b59;
  transition: all 0.3s ease;
  
  &.pulsing-red {
    animation: pulseRed 1s ease-in-out infinite;
  }
}

@keyframes pulseRed {
  0%, 100% {
    box-shadow: inset 0 0 0 1px #ff3b59;
  }
  50% {
    box-shadow: inset 0 0 0 3px #ff3b59, 0 0 20px rgba(255, 59, 89, 0.5);
  }
}

.overheat-modal-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  
  h1 {
    color: #ff3b59;
    font-size: 18px;
    font-weight: 700;
    text-align: center;
  }
}

.overheat-modal-body {
  text-align: center;
  margin-bottom: 1.5rem;
  
  .overheat-message {
    color: #fff;
    font-size: 14px;
    line-height: 1.5;
    margin-bottom: 1rem;
  }
  
  .overheat-timer {
    color: #ff3b59;
    font-size: 16px;
    font-weight: 600;
  }
}

.overheat-modal-actions {
  display: flex;
  justify-content: center;
}

.btn-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
```

### Этап 3: Интеграция в GameRunView.vue

**Файл:** `src/views/GameRunView.vue`

#### 3.1. Добавление состояния перегрева

```javascript
// В секции script setup
const showOverheatModal = ref(false)
const overheatedUntil = ref(null)
const isOverheated = ref(false)
const overheatEnergyCollected = ref(0)
const overheatGoal = ref(null)
const wasOverheated = ref(false)
```

#### 3.2. Инициализация при старте забега

**Место:** В функции `handleStartClick()` или `startGame()`

**Важно:** Используем функцию `initializeOverheat()` из раздела 1.3, которая использует данные из `app.user`.

```javascript
// Вызываем инициализацию перегрева при старте забега
const startGame = async (isTraining = false, initialStorage = null) => {
  // ... существующий код ...
  
  // Инициализируем перегрев
  initializeOverheat()
  
  // ... остальной код ...
}
```
```

#### 3.3. Модификация функции collectEnergy

**Место:** В функции где обрабатывается сбор поинтов (вероятно в `doOneStep` или через callback)

**Важно:** Используем API для проверки перегрева. Логика перегрева полностью на сервере.

```javascript
// В месте где вызывается gameRun.collectEnergy()
// После вызова collectEnergy добавляем проверку перегрева через API
const handleEnergyPointCollected = async (amount) => {
  gameRun.collectEnergy(amount)
  
  // Проверяем перегрев через API (только если перегрев еще не активен)
  if (!isOverheated.value) {
    const overheated = await checkOverheatTrigger(amount)
    if (overheated) {
      // Перегрев активирован, забег уже остановлен в activateOverheat()
      return
    }
  }
}
```

#### 3.4. Функция активации перегрева

**Примечание:** Функция `activateOverheat()` уже определена в разделе 1.5 и вызывается из `checkOverheatTrigger()`. Здесь она используется для активации перегрева из ответа сервера.

Логика активации перегрева полностью на сервере, фронтенд только получает результат и обрабатывает UI.
```

#### 3.5. Обработчик кнопки "Продолжить"

```javascript
const handleOverheatContinue = async () => {
  if (!isOverheated.value || !overheatedUntil.value) {
    return
  }
  
  const now = new Date()
  const until = new Date(overheatedUntil.value)
  
  // Проверяем что перегрев закончился
  if (until > now) {
    // Перегрев еще активен, кнопка должна быть неактивна
    return
  }
  
  // Перегрев закончился, продолжаем забег
  isOverheated.value = false
  showOverheatModal.value = false
  
  // Обновляем состояние из app.user (сервер уже обновил состояние)
  await app.initUser() // Обновляем данные пользователя с сервера
  
  // Возобновляем забег
  resumeGame()
}
```

#### 3.6. Добавление модального окна в template

```vue
<!-- После других модальных окон -->
<OverheatGameRunModal
  v-if="showOverheatModal"
  :overheated-until="overheatedUntil"
  @continue="handleOverheatContinue"
  @close="showOverheatModal = false"
/>
```

#### 3.7. Добавление пульсации экрана

```vue
<!-- В template, поверх всего контента -->
<div
  v-if="isOverheated && showOverheatModal"
  class="overheat-screen-pulse"
/>
```

```scss
// В секции style
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

@keyframes screenPulse {
  0%, 100% {
    opacity: 0.1;
  }
  50% {
    opacity: 0.3;
  }
}
```

### Этап 4: Backend API для синхронизации перегрева

**Файл:** `edit/core/views.py`

#### 4.1. Создание упрощенного endpoint для обновления перегрева во время забега

**Примечание:** 
- Используем существующую логику перегрева из `TapEnergyView` (строки 448-491), но только для обновления `overheat_energy_collected` и проверки активации перегрева
- Не обновляем `energy`, `storage`, `power` (это делается при завершении забега через `game-run-complete/`)
- Можно было бы модифицировать существующий `tap-energy/` endpoint для работы в режиме забега, но создание отдельного endpoint `game-run-update-overheat/` более чистое решение и не влияет на существующую логику тапов

```python
from django.db.models import F
from django.utils import timezone
from datetime import timedelta
import random
from rest_framework.response import Response
from rest_framework import status
from core.decorators import require_auth
from core.models import UserProfile, OverheatConfig

# ... в начале файла views.py должны быть импорты:
# from django.db.models import F, Q
# from django.utils import timezone
# from datetime import timedelta
# import random
# from rest_framework.response import Response
# from rest_framework import status
# from core.decorators import require_auth
# from core.models import UserProfile, OverheatConfig
# overheat_hours_by_type уже определен в views.py (строки 218-224)

class GameRunUpdateOverheatView(APIView):
    """Обновляет состояние перегрева во время забега (только логика перегрева, без обновления energy/storage/power)"""
    
    @require_auth
    def post(self, request):
        user_profile = request.user_profile
        now = timezone.now()
        
        # Получаем количество собранной энергии из забега
        collected_amount = float(request.data.get('amount', 0))
        
        if collected_amount <= 0:
            return Response(
                {"error": "Invalid amount"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем активность Cryo (перегрев невозможен если Cryo активен)
        is_cryo_active = (
            user_profile.cryo_expires and
            timezone.now() < user_profile.cryo_expires
        )
        
        # Получаем конфигурацию перегрева
        overheat_config = OverheatConfig.objects.first() or OverheatConfig(
            taps_before_power_reduction=5,
            power_reduction_percentage=1,
            min_duration=15,
            max_duration=300,
        )
        
        # Проверяем активный перегрев
        if user_profile.overheated_until and user_profile.overheated_until > now:
            # Перегрев уже активен, возвращаем состояние
            user_profile.refresh_from_db()
            return Response({
                "overheated": True,
                "overheated_until": user_profile.overheated_until.isoformat(),
                "overheat_energy_collected": user_profile.overheat_energy_collected,
                "overheat_goal": user_profile.overheat_goal,
                "was_overheated": user_profile.was_overheated,
            })
        
        # ВАЖНО: Power больше не участвует в системе перегрева
        # Не обновляем power при перегреве (в отличие от старой системы тапов)
        
        # Обновляем накопленную энергию для перегрева
        needed_hours = overheat_hours_by_type.get(user_profile.station_type, None)
        
        # ВАЖНО: Если криокамера активна, перегрев не может активироваться
        if needed_hours and not is_cryo_active:
            # Обновляем overheat_energy_collected
            UserProfile.objects.filter(user_id=user_profile.user_id).update(
                overheat_energy_collected=F("overheat_energy_collected") + collected_amount
            )
            user_profile.refresh_from_db()
            
            # Используем существующую логику перегрева из TapEnergyView (строки 448-491)
            if user_profile.was_overheated:
                if (
                    user_profile.overheat_energy_collected
                    >= float(user_profile.generation_rate) * needed_hours
                ):
                    UserProfile.objects.filter(
                        user_id=user_profile.user_id
                    ).update(
                        was_overheated=False,
                        overheat_energy_collected=0,
                        overheat_goal=None,
                    )
            else:
                if user_profile.overheat_goal is None:
                    UserProfile.objects.filter(
                        user_id=user_profile.user_id
                    ).update(
                        overheat_goal=random.uniform(
                            0,
                            float(user_profile.generation_rate)
                            * needed_hours
                            * float(user_profile.power / 100),
                        )
                    )
                user_profile.refresh_from_db()
                if (
                    user_profile.overheat_energy_collected
                    >= user_profile.overheat_goal
                ):
                    duration = random.randint(
                        overheat_config.min_duration, overheat_config.max_duration
                    )
                    UserProfile.objects.filter(
                        user_id=user_profile.user_id
                    ).update(
                        overheated_until=timezone.now()
                        + timedelta(minutes=duration),
                        was_overheated=True,
                    )
        
        user_profile.refresh_from_db()
        
        return Response({
            "overheated": bool(user_profile.overheated_until and user_profile.overheated_until > now),
            "overheated_until": user_profile.overheated_until.isoformat() if user_profile.overheated_until else None,
            "overheat_energy_collected": user_profile.overheat_energy_collected,
            "overheat_goal": user_profile.overheat_goal,
            "was_overheated": user_profile.was_overheated,
        })
```

#### 4.2. Добавление URL маршрута

**Файл:** `edit/core/urls.py`

```python
path('game-run-update-overheat/', views.GameRunUpdateOverheatView.as_view(), name='game-run-update-overheat'),
```

### Этап 5: Локализация

**Файлы:** `src/locales/en.json`, `src/locales/ru.json`, `src/locales/uk.json`

#### 5.1. Добавление переводов

```json
{
  "game": {
    "overheat_title": "Station Overheating",
    "overheat_desc": "Wait for the cooling process to complete, which will take some time. Using the power station when overheated will lead to its <b>breakdown</b>.",
    "overheat_cooling_down": "Cooling down",
    "continue": "Continue",
    "use_nitrogen": "Use Nitrogen",
    "back_to_main": "Back to Main"
  }
}
```

### Этап 6: Интеграция с существующей логикой паузы

**Модификация:** `src/views/GameRunView.vue`

#### 6.1. Обновление функции pauseGame

```javascript
const pauseGame = () => {
  gameRun.pauseRun()
  stopGameLoop()
  
  // Если перегрев активен, показываем модалку перегрева, иначе обычную паузу
  if (isOverheated.value) {
    launcherOverlayMode.value = 'none' // Не показываем обычную паузу
    showOverheatModal.value = true
  } else {
    launcherOverlayMode.value = 'pause'
  }
}
```

#### 6.2. Обновление функции resumeGame

```javascript
const resumeGame = async () => {
  // Проверяем что перегрев закончился (или был снят азотом)
  if (isOverheated.value && overheatedUntil.value) {
    const now = new Date()
    const until = new Date(overheatedUntil.value)
    
    if (until > now) {
      // Перегрев еще активен, не возобновляем
      return
    }
    
    // Перегрев закончился
    isOverheated.value = false
    showOverheatModal.value = false
  }
  
  // Обновляем данные пользователя с сервера (на случай если азот был использован)
  await app.initUser()
  
  gameRun.resumeRun()
  lastUpdateTime = 0
  launcherOverlayMode.value = 'none'
}
```

#### 6.3. Обработка использования азота в модалке

Когда пользователь использует азот в модалке перегрева, модалка должна:
1. Вызвать `handleUseNitrogen()` который активирует азот через API
2. После успешной активации азота, автоматически закрыть модалку и возобновить забег
3. Обновить данные пользователя (`app.initUser()`)

## Последовательность работы системы

### Сценарий 1: Первый перегрев во время забега

1. **Старт забега:**
   - Инициализируется `overheatGoal` (случайное значение)
   - `overheatEnergyCollected = 0`
   - `wasOverheated = false`

2. **Сбор энергии:**
   - При каждом собранном поинте: `overheatEnergyCollected += amount`
   - Проверка: `if (overheatEnergyCollected >= overheatGoal)`

3. **Активация перегрева:**
   - Вызывается `activateOverheatInRun()`
   - Забег останавливается (`pauseGame()`)
   - Генерируется `overheatedUntil` (случайная длительность 15-300 минут)
   - Показывается модальное окно перегрева
   - Экран начинает пульсировать красным

4. **Ожидание охлаждения:**
   - Кнопка "Продолжить" неактивна
   - Таймер показывает оставшееся время
   - Экран пульсирует красным

5. **Окончание перегрева:**
   - Кнопка "Продолжить" становится активной
   - Игрок может нажать "Продолжить"

6. **Продолжение забега:**
   - Вызывается `handleOverheatContinue()`
   - Устанавливается новая цель: `overheatGoal = generationRate * neededHours` (фиксированная)
   - Забег возобновляется (`resumeGame()`)

### Сценарий 2: Повторный перегрев

1. **После первого перегрева:**
   - `wasOverheated = true`
   - `overheatGoal = generationRate * neededHours` (фиксированная)
   - `overheatEnergyCollected` продолжает накапливаться

2. **Активация повторного перегрева:**
   - Когда `overheatEnergyCollected >= overheatGoal`
   - Процесс аналогичен первому перегреву

3. **После повторного перегрева:**
   - Сбрасывается состояние: `wasOverheated = false`, `overheatEnergyCollected = 0`, `overheatGoal = null`
   - Следующий перегрев снова будет случайным

## Взаимодействие с другими системами

### 1. Cryo Chamber

**Защита от перегрева:**
- Когда Cryo активен (`cryo_expires > now`), перегрев **НЕ может активироваться**
- Проверка происходит как на фронтенде (при инициализации), так и на бэкенде (при обновлении перегрева)

**Проверка на фронтенде:**
```javascript
const isCryoActive = app.user?.cryo_expires && new Date(app.user.cryo_expires) > new Date()
if (isCryoActive) {
  // Перегрев невозможен
  return
}
```

**Проверка на бэкенде:**
```python
is_cryo_active = (
    user_profile.cryo_expires and
    timezone.now() < user_profile.cryo_expires
)

if needed_hours and not is_cryo_active:
    # Логика перегрева только если Cryo НЕ активен
```

### 2. Азот (Nitrogen)

**Мгновенное снятие перегрева:**
- Азот можно использовать в модалке перегрева для мгновенного снятия перегрева
- Доступен если `azot_uses_left > 0` или `azot_reward_balance > 0`
- При использовании устанавливает `overheated_until=None` и `tap_count_since_overheat=0`
- Используется через существующий endpoint `tasks/activate_booster/` с `slug: "azot"`

**Интеграция в модалке:**
- Кнопка "Использовать азот" показывается только если азот доступен и перегрев активен
- При использовании автоматически закрывает модалку и возобновляет забег

### 3. Autostart

**Автоматическое снятие:**
- Autostart автоматически снимает перегрев после его окончания (работает в фоне в `boosters.py`)
- Использует один заряд `autostart_count`
- Работает только если перегрев уже закончился по времени

### 4. Power

**ВАЖНО: Power больше не участвует в системе перегрева:**
- Перегрев **НЕ влияет на power** (в отличие от старой системы тапов)
- В новой системе забега нет снижения power во время перегрева
- Power снижается только при обычной генерации энергии (через `generation.py`)

### 5. Пауза забега

**Интеграция:** Перегрев использует существующую систему паузы:
- `pauseGame()` - останавливает забег
- `resumeGame()` - возобновляет забег
- Модальное окно перегрева заменяет обычное модальное окно паузы

### 6. Завершение забега

**Обработка:** Если перегрев активен при завершении забега:
- Состояние перегрева сохраняется на сервере
- При следующем забеге состояние восстанавливается

## Тестирование

### Тестовые сценарии:

1. **Тест первого перегрева:**
   - Запустить забег на станции №6-7
   - Собрать энергию до достижения `overheatGoal`
   - Проверить остановку забега
   - Проверить показ модального окна
   - Проверить пульсацию экрана
   - Дождаться окончания перегрева
   - Проверить активацию кнопки "Продолжить"
   - Проверить возобновление забега

2. **Тест использования азота:**
   - Запустить забег и дождаться перегрева
   - Проверить наличие кнопки "Использовать азот" (если азот доступен)
   - Использовать азот
   - Проверить мгновенное снятие перегрева
   - Проверить автоматическое возобновление забега
   - Проверить уменьшение количества азота

3. **Тест криокамеры:**
   - Активировать криокамеру
   - Запустить забег
   - Проверить что перегрев не активируется даже при достижении цели

4. **Тест повторного перегрева:**
   - После первого перегрева продолжить забег
   - Собрать энергию до фиксированной цели
   - Проверить активацию повторного перегрева

3. **Тест с Cryo:**
   - Активировать Cryo
   - Запустить забег
   - Проверить что перегрев не происходит

4. **Тест с разными типами станций:**
   - Протестировать на станциях №3, №4-5, №6-7
   - Проверить правильность частоты перегревов

## Дополнительные замечания

### Производительность:

- Проверка перегрева происходит при каждом сборе поинта (не критично)
- Таймер обновляется каждую секунду (можно оптимизировать)

### Безопасность:

- Проверка данных на сервере перед обновлением состояния перегрева
- Валидация `overheated_until` и других параметров

### UX улучшения:

- ✅ Вибрация при перегреве (уже добавлена в план)
- Можно добавить предупреждение перед перегревом (например, на 80% от цели)

## Заключение

Данный план описывает полную интеграцию системы перегревов в режим забега. Реализация включает:

- ✅ Использование существующей логики перегрева из `TapEnergyView` (без изменений)
- ✅ Новый упрощенный endpoint `game-run-update-overheat/` для обновления перегрева во время забега
- ✅ Отслеживание накопленной энергии через API при сборе поинтов
- ✅ Активацию перегрева при достижении цели (логика на сервере)
- ✅ Остановку забега при перегреве (использует существующую функцию паузы)
- ✅ Модальное окно с кнопкой "Продолжить"
- ✅ Визуальный эффект пульсации экрана красным цветом
- ✅ Вибрацию при активации перегрева
- ✅ Проверку окончания перегрева для активации кнопки
- ✅ Возобновление забега после перегрева
- ✅ Интеграцию с существующей логикой паузы
- ✅ Синхронизацию с сервером
- ✅ **Power больше не участвует в системе перегрева** - перегрев не влияет на power
- ✅ **Криокамера предотвращает перегрев** - если активна, перегрев не может активироваться
- ✅ **Использование азота в модалке** - кнопка для мгновенного снятия перегрева если азот доступен
- ✅ **Работа бустеров** - такая же как в текущей системе (Cryo, Autostart, Азот)

**Ключевые особенности:**
- Логика перегрева полностью на сервере (используется существующий код)
- Триггером являются поинты забега вместо тапов
- Не изменяется логика расчета перегрева
- Максимальное переиспользование существующего кода
- **Power не снижается** во время перегрева (в отличие от старой системы тапов)
- **Криокамера блокирует** активацию перегрева
- **Азот можно использовать** для мгновенного снятия перегрева через модалку

План готов к реализации.
