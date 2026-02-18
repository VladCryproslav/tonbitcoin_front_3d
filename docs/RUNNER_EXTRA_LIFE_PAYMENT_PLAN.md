# План разработки покупки дополнительной жизни за STARS в раннере

## Обзор

Данный документ описывает план реализации покупки дополнительной жизни за STARS в модалке проигрыша раннера. После использования 3 жизней пользователь может купить 4-ю жизнь за STARS, рассчитанную на основе остатка не собранной энергии.

## Требования

### Функциональные требования:

1. **Модалка проигрыша:** После использования 3 жизней показывается модалка проигрыша
2. **Кнопка покупки жизни:** Под кнопками "Забрать" (для обычного забега) или "Вернуться назад" (для тренировки) добавляется кнопка покупки дополнительной жизни за STARS
3. **Расчет цены:** Цена рассчитывается на основе остатка не собранной энергии (например, 100 kW = 1 STAR)
4. **Округление:** Всегда округляем вверх (2.4 → 3, 0.1 → 1)
5. **Оплата:** Используется существующая логика оплаты через Telegram WebApp (как в WheelView.vue, SpeedUpModal.vue)
6. **Фиксация использования:** После успешной оплаты фиксируется в UserProfile, что 4-я жизнь использована в этом забеге
7. **Восстановление забега:** После успешной оплаты забег восстанавливается как выход из перегрева (таймер 3-2-1, защита от коллизий 2 секунды)

### Технические требования:

- Использовать существующую логику оплаты через `tg.openInvoice()`
- Добавить модель `RunnerConfig` в админку (по типу `WithdrawalConfig`)
- Добавить поле в `UserProfile` для отслеживания использования 4-й жизни в текущем забеге
- Использовать ту же логику восстановления забега, что и при выходе из перегрева

## Архитектура решения

### Компоненты системы:

1. **Frontend (Vue):**
   - Модификация модалки проигрыша в `GameRunView.vue`
   - Добавление кнопки покупки жизни
   - Расчет цены на основе остатка энергии
   - Интеграция с Telegram WebApp для оплаты
   - Восстановление забега после успешной оплаты

2. **Backend (Django):**
   - Модель `RunnerConfig` для хранения конфигурации цен
   - API endpoint для создания invoice ссылки на покупку жизни
   - API endpoint для обработки успешной оплаты
   - Поле в `UserProfile` для отслеживания использования 4-й жизни
   - Обработчик платежа в Telegram Bot (`edit/tgbot/views.py`)

3. **Админка:**
   - Страница `RunnerConfig` в админке (по типу `WithdrawalConfig`)

## Детальный план реализации

### Этап 1: Backend - Модель и конфигурация

#### 1.1. Создание модели RunnerConfig

**Файл:** `edit/core/models.py`

```python
class RunnerConfig(models.Model):
    """Конфигурация для раннера"""
    # Цена 1 STAR в kW (например, 100 kW = 1 STAR)
    stars_per_kw = models.FloatField(
        default=100,
        help_text="Количество kW за 1 STAR (например, 100 означает 100 kW = 1 STAR)"
    )
    
    class Meta:
        verbose_name = "Runner Config"
        verbose_name_plural = "Runner Configs"
    
    def __str__(self):
        return f"Runner Config: {self.stars_per_kw} kW = 1 STAR"
```

#### 1.2. Добавление поля в UserProfile

**Файл:** `edit/core/models.py`

```python
class UserProfile(models.Model):
    # ... существующие поля ...
    
    # Флаг использования 4-й жизни в текущем забеге
    energy_run_extra_life_used = models.BooleanField(
        default=False,
        help_text="Использована ли 4-я жизнь в текущем забеге"
    )
```

#### 1.3. Миграция базы данных

**Команда:**
```bash
python manage.py makemigrations
python manage.py migrate
```

#### 1.4. Регистрация в админке

**Файл:** `edit/core/admin.py`

```python
from .models import RunnerConfig

@admin.register(RunnerConfig)
class RunnerConfigAdmin(admin.ModelAdmin):
    list_display = ['stars_per_kw']
    list_editable = ['stars_per_kw']
```

### Этап 2: Backend - API endpoints

#### 2.1. Endpoint для создания invoice ссылки

**Файл:** `edit/core/views.py`

```python
class RunnerExtraLifeStarsView(APIView):
    """Получение ссылки для покупки дополнительной жизни за STARS"""
    
    @swagger_auto_schema(
        tags=["game"],
        operation_description="Получить ссылку для покупки дополнительной жизни за STARS",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["remaining_energy"],
            properties={
                "remaining_energy": openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    description="Остаток не собранной энергии в kW"
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Ссылка для оплаты",
                examples={
                    "application/json": {
                        "link": "https://example.com/invoice_link",
                        "price": 10,
                    }
                },
            ),
            400: "Ошибка валидации",
        },
    )
    @require_auth
    def post(self, request):
        try:
            user_profile: UserProfile = request.user_profile
            
            # Проверка что забег активен
            if not user_profile.energy_run_last_started_at:
                return Response(
                    {"error": "Run not started"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Проверка что 4-я жизнь еще не использована
            if user_profile.energy_run_extra_life_used:
                return Response(
                    {"error": "Extra life already used in this run"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            remaining_energy = float(request.data.get("remaining_energy", 0))
            if remaining_energy <= 0:
                return Response(
                    {"error": "Invalid remaining energy"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Получаем конфигурацию
            runner_config = RunnerConfig.objects.first()
            if not runner_config:
                return Response(
                    {"error": "Runner config not found"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            
            # Расчет цены: остаток энергии / цена за 1 STAR, округляем вверх
            stars_per_kw = runner_config.stars_per_kw
            price = math.ceil(remaining_energy / stars_per_kw)
            
            # Минимальная цена - 1 STAR
            if price < 1:
                price = 1
            
            # Применяем скидку пользователя (если есть)
            final_price = int(price * user_profile.sbt_get_stars_discount())
            
            # Создаем invoice ссылку
            link = bot.create_invoice_link(
                title="Дополнительная жизнь",
                description=f"Покупка дополнительной жизни за {final_price} Stars",
                currency="XTR",
                provider_token="",
                prices=[LabeledPrice(label="XTR", amount=final_price)],
                payload=f"runner_extra_life:{user_profile.user_id}",
            )
            
            return Response(
                {
                    "link": link,
                    "price": final_price,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            action_logger.exception(f"Error creating extra life invoice: {e}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
```

#### 2.2. Endpoint для восстановления забега после оплаты

**Файл:** `edit/core/views.py`

```python
class RunnerExtraLifeActivateView(APIView):
    """Активация дополнительной жизни после успешной оплаты"""
    
    @swagger_auto_schema(
        tags=["game"],
        operation_description="Активировать дополнительную жизнь после оплаты",
        responses={
            200: openapi.Response(
                description="Жизнь успешно активирована",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Extra life activated",
                    }
                },
            ),
            400: "Ошибка валидации",
        },
    )
    @require_auth
    def post(self, request):
        try:
            user_profile: UserProfile = request.user_profile
            
            # Проверка что забег активен
            if not user_profile.energy_run_last_started_at:
                return Response(
                    {"error": "Run not started"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Проверка что 4-я жизнь еще не использована
            if user_profile.energy_run_extra_life_used:
                return Response(
                    {"error": "Extra life already used in this run"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Активируем 4-ю жизнь
            UserProfile.objects.filter(id=user_profile.id).update(
                energy_run_extra_life_used=True
            )
            
            action_logger.info(
                f"Extra life activated for user {user_profile.user_id}"
            )
            
            return Response(
                {
                    "success": True,
                    "message": "Extra life activated",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            action_logger.exception(f"Error activating extra life: {e}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
```

#### 2.3. Обработчик платежа в Telegram Bot

**Файл:** `edit/tgbot/views.py`

```python
@bot.message_handler(content_types=["successful_payment"])
def got_payment(message: Message):
    # ... существующий код ...
    
    elif payload.startswith("runner_extra_life:"):
        try:
            user_id = int(payload.replace("runner_extra_life:", ""))
            user_profile = UserProfile.objects.get(user_id=user_id)
            
            # Проверяем что забег активен
            if not user_profile.energy_run_last_started_at:
                action_logger.warning(
                    f"user {user_id} | Extra life payment but run not started | {payment_info.telegram_payment_charge_id}"
                )
                return
            
            # Проверяем что 4-я жизнь еще не использована
            if user_profile.energy_run_extra_life_used:
                action_logger.warning(
                    f"user {user_id} | Extra life already used | {payment_info.telegram_payment_charge_id}"
                )
                return
            
            # Активируем 4-ю жизнь
            UserProfile.objects.filter(user_id=user_id).update(
                energy_run_extra_life_used=True
            )
            
            action_logger.info(
                f"user {user_id} | Extra life activated | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
            )
        except Exception as e:
            action_logger.exception(
                f"user {user_id} | Error activating extra life | {payment_info.telegram_payment_charge_id}"
            )
```

#### 2.4. Добавление URL маршрутов

**Файл:** `edit/core/urls.py`

```python
urlpatterns = [
    # ... существующие маршруты ...
    path('runner-extra-life-stars/', RunnerExtraLifeStarsView.as_view(), name='runner-extra-life-stars'),
    path('runner-extra-life-activate/', RunnerExtraLifeActivateView.as_view(), name='runner-extra-life-activate'),
]
```

### Этап 3: Frontend - Модификация модалки проигрыша

#### 3.1. Добавление кнопки покупки жизни

**Файл:** `src/views/GameRunView.vue`

**Место:** В секции модалки проигрыша (строки 207-226)

```vue
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
    v-if="canBuyExtraLife"
    class="btn-primary btn-primary--wide btn-extra-life"
    :disabled="isBuyingExtraLife"
    @click.stop.prevent="handleBuyExtraLife"
  >
    <span v-if="!isBuyingExtraLife">
      <img src="@/assets/stars.png" width="16px" alt="Stars" />
      {{ t('game.buy_extra_life') }} ({{ extraLifePrice }})
    </span>
    <span v-else>{{ t('game.processing') }}</span>
  </button>
</div>
```

#### 3.2. Добавление логики расчета цены и покупки

**Файл:** `src/views/GameRunView.vue`

**Место:** В секции `<script setup>`

```javascript
import { useTelegram } from '@/services/telegram'

const { tg } = useTelegram()

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
  if (!showGameOver.value || gameOverType.value !== 'lose') {
    return false
  }
  
  if (livesLeft.value > 0) {
    return false
  }
  
  if (app.user?.energy_run_extra_life_used) {
    return false
  }
  
  if (!gameRun.startStorage?.value || gameRun.startStorage.value <= 0) {
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
    const startStorage = gameRun.startStorage?.value ?? 0
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
    console.error('Error calculating extra life price:', error)
    extraLifePrice.value = 0
  }
}

// Обработчик покупки дополнительной жизни
const handleBuyExtraLife = async () => {
  if (isBuyingExtraLife.value || !canBuyExtraLife.value) {
    return
  }
  
  isBuyingExtraLife.value = true
  
  try {
    // Расчет остатка энергии
    const startStorage = gameRun.startStorage?.value ?? 0
    const collectedEnergy = savedEnergyCollectedForModal.value || 0
    const remainingEnergy = Math.max(0, startStorage - collectedEnergy)
    
    // Получаем invoice ссылку
    const response = await host.post('runner-extra-life-stars/', {
      remaining_energy: remainingEnergy
    })
    
    if (response.status === 200 && response.data?.link) {
      const invoiceLink = response.data.link
      
      // Открываем invoice
      tg.openInvoice(invoiceLink, async (status) => {
        if (status === 'paid') {
          // Успешная оплата - активируем жизнь
          try {
            await host.post('runner-extra-life-activate/', {})
            
            // Обновляем данные пользователя
            await app.initUser()
            
            // Восстанавливаем забег (как выход из перегрева)
            await restoreRunAfterExtraLife()
          } catch (error) {
            console.error('Error activating extra life:', error)
            // Показываем ошибку пользователю
            alert(t('game.extra_life_activation_error'))
          }
        }
        
        isBuyingExtraLife.value = false
      })
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
      const startAccelSpeed = Math.max(savedSpeed.value * 0.6, MIN_START_SPEED)
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
watch([showGameOver, gameOverType, livesLeft], () => {
  if (canBuyExtraLife.value) {
    calculateExtraLifePrice()
  }
}, { immediate: true })
```

#### 3.3. Добавление стилей для кнопки

**Файл:** `src/views/GameRunView.vue`

**Место:** В секции `<style>`

```scss
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
```

### Этап 4: Сброс флага при новом забеге

#### 4.1. Сброс флага при старте нового забега

**Файл:** `edit/core/views.py`

**Место:** В `GameRunStartView` (или аналогичном endpoint для старта забега)

```python
# При старте нового забега сбрасываем флаг использования 4-й жизни
UserProfile.objects.filter(id=user_profile.id).update(
    energy_run_extra_life_used=False
)
```

### Этап 5: Локализация

#### 5.1. Добавление переводов

**Файлы:** `src/locales/*.json`

```json
{
  "game": {
    "buy_extra_life": "Купить дополнительную жизнь",
    "extra_life_activation_error": "Ошибка активации дополнительной жизни",
    "processing": "Обработка..."
  }
}
```

## Порядок реализации

1. **Backend:**
   - Создать модель `RunnerConfig`
   - Добавить поле `energy_run_extra_life_used` в `UserProfile`
   - Создать миграции и применить их
   - Зарегистрировать `RunnerConfig` в админке
   - Создать API endpoints (`RunnerExtraLifeStarsView`, `RunnerExtraLifeActivateView`)
   - Добавить обработчик платежа в Telegram Bot
   - Добавить URL маршруты
   - Добавить сброс флага при старте нового забега

2. **Frontend:**
   - Добавить кнопку покупки жизни в модалку проигрыша
   - Добавить логику расчета цены
   - Добавить обработчик покупки
   - Добавить функцию восстановления забега
   - Добавить стили для кнопки
   - Добавить локализацию

3. **Тестирование:**
   - Проверить расчет цены (округление вверх)
   - Проверить оплату через Telegram WebApp
   - Проверить активацию жизни после оплаты
   - Проверить восстановление забега
   - Проверить сброс флага при новом забеге
   - Проверить что кнопка не показывается если жизнь уже использована

## Важные замечания

1. **Округление:** Всегда округляем вверх (`Math.ceil()`), даже если получается 0.1 → 1
2. **Минимальная цена:** Минимум 1 STAR (даже если расчет дает меньше)
3. **Защита от повторного использования:** Проверяем флаг `energy_run_extra_life_used` перед показом кнопки и перед активацией
4. **Восстановление забега:** Используем ту же логику, что и при выходе из перегрева (таймер 3-2-1, защита от коллизий 2 секунды)
5. **Сброс флага:** Флаг `energy_run_extra_life_used` сбрасывается при старте нового забега
