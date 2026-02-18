# План разработки ограничения тренировочных забегов в день

## Обзор

Данный документ описывает план реализации ограничения количества тренировочных забегов в день для каждого пользователя. По умолчанию разрешено до 5 тренировочных забегов в день. Настройка количества доступных забегов должна быть настраиваемой через админку в `RunnerConfig`.

## Требования

### Функциональные требования:

1. **Ограничение тренировочных забегов:** Каждый пользователь может проходить до N тренировочных забегов в день (по умолчанию 5)
2. **Настройка лимита:** Количество допустимых тренировочных забегов в день настраивается в админке через `RunnerConfig`
3. **Отображение доступности:** В кнопке "Тренировка" под текстом "Тренировка" отображается маленьким шрифтом "доступно X" (где X - количество оставшихся забегов)
4. **Блокировка при исчерпании:** Если лимит исчерпан, кнопка "Тренировка" должна быть заблокирована или показывать соответствующее сообщение
5. **Сброс счетчика:** Счетчик тренировочных забегов сбрасывается каждый день в 00:00 по UTC

### Технические требования:

- Использовать существующую модель `RunnerConfig` для хранения настройки лимита
- Добавить поля в `UserProfile` для отслеживания тренировочных забегов:
  - `training_run_last_date` - дата последнего тренировочного забега (DateField)
  - `training_run_count_today` - количество тренировочных забегов сегодня (IntegerField)
- Создать API endpoint для проверки доступности тренировочного забега
- Обновить логику старта тренировочного забега для проверки и обновления счетчика
- Обновить фронтенд для отображения количества доступных забегов

## Референс логики

По аналогии с `energy_run_last_started_at` в `UserProfile`:
- Поле `energy_run_last_started_at` хранит время последнего старта забега
- Используется для проверки cooldown между забегами (60 минут)
- Аналогично, для тренировочных забегов нужно отслеживать дату последнего забега и количество забегов в текущий день

## Архитектура решения

### Компоненты системы:

1. **Backend (Django):**
   - Добавление поля `max_training_runs_per_day` в модель `RunnerConfig`
   - Добавление полей `training_run_last_date` и `training_run_count_today` в модель `UserProfile`
   - Создание API endpoint для проверки доступности тренировочного забега
   - Обновление логики старта тренировочного забега для проверки лимита
   - Обновление админки для настройки лимита

2. **Frontend (Vue):**
   - Обновление компонента `GameRunView.vue` для отображения количества доступных забегов
   - Добавление проверки доступности перед запуском тренировочного забега
   - Обновление стилей кнопки "Тренировка" для отображения счетчика

3. **Админка:**
   - Добавление поля `max_training_runs_per_day` в `RunnerConfigAdmin`

## Детальный план реализации

### Этап 1: Backend - Модель и миграции

#### 1.1. Обновление модели RunnerConfig

**Файл:** `edit/core/models.py`

Добавить поле `max_training_runs_per_day` в модель `RunnerConfig`:

```python
class RunnerConfig(models.Model):
    """Конфигурация для раннера"""
    stars_per_kw = models.FloatField(
        default=100,
        help_text="Количество kW за 1 STAR (например, 100 означает 100 kW = 1 STAR)"
    )
    max_training_runs_per_day = models.IntegerField(
        default=5,
        help_text="Максимальное количество тренировочных забегов в день для каждого пользователя"
    )
    
    class Meta:
        verbose_name = "Runner Config"
        verbose_name_plural = "Runner Configs"
    
    def __str__(self):
        return f"Runner Config: {self.stars_per_kw} kW = 1 STAR, {self.max_training_runs_per_day} training runs/day"
```

#### 1.2. Добавление полей в UserProfile

**Файл:** `edit/core/models.py`

Добавить поля для отслеживания тренировочных забегов в модель `UserProfile`:

```python
class UserProfile(models.Model):
    # ... существующие поля ...
    
    # Energy Run (Раннер)
    energy_run_last_started_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Время последнего старта забега (для cooldown 60 минут)"
    )
    energy_run_start_storage = models.DecimalField(...)
    energy_run_extra_life_used = models.BooleanField(...)
    
    # Training Run (Тренировочные забеги)
    training_run_last_date = models.DateField(
        blank=True,
        null=True,
        help_text="Дата последнего тренировочного забега (для сброса счетчика)"
    )
    training_run_count_today = models.IntegerField(
        default=0,
        help_text="Количество тренировочных забегов сегодня"
    )
    
    # ... остальные поля ...
```

#### 1.3. Создание миграции

**Команда:**
```bash
python manage.py makemigrations core
python manage.py migrate
```

### Этап 2: Backend - API endpoints

#### 2.1. Endpoint для проверки доступности тренировочного забега

**Файл:** `edit/core/views.py`

Создать новый endpoint `TrainingRunCheckView`:

```python
class TrainingRunCheckView(APIView):
    """Проверка доступности тренировочного забега"""
    
    @require_auth
    def get(self, request):
        try:
            user_profile = request.user_profile
            now = timezone.now()
            today = now.date()
            
            # Получаем конфигурацию (или создаем дефолтную если нет)
            runner_config = RunnerConfig.objects.first()
            if not runner_config:
                runner_config = RunnerConfig.objects.create(
                    stars_per_kw=100,
                    max_training_runs_per_day=5
                )
            
            max_runs = runner_config.max_training_runs_per_day
            
            # Проверяем нужно ли сбросить счетчик (если последний забег был не сегодня)
            if user_profile.training_run_last_date != today:
                # Сбрасываем счетчик если это новый день
                UserProfile.objects.filter(user_id=user_profile.user_id).update(
                    training_run_count_today=0,
                    training_run_last_date=today
                )
                user_profile.refresh_from_db()
            
            available_runs = max(0, max_runs - user_profile.training_run_count_today)
            can_run = available_runs > 0
            
            return Response({
                "can_run": can_run,
                "available_runs": available_runs,
                "max_runs_per_day": max_runs,
                "runs_used_today": user_profile.training_run_count_today,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            action_logger.error(f"TrainingRunCheckView error: {str(e)}")
            return Response(
                {"error": f"Internal server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
```

#### 2.2. Обновление логики старта тренировочного забега

**Файл:** `edit/core/views.py`

Создать новый endpoint `TrainingRunStartView` или обновить существующий `EnergyRunStartView` для обработки тренировочных забегов:

```python
class TrainingRunStartView(APIView):
    """Записывает старт тренировочного забега. Проверяет лимит на количество забегов в день."""
    
    @require_auth
    def post(self, request):
        try:
            user_profile = request.user_profile
            now = timezone.now()
            today = now.date()
            
            # Получаем конфигурацию
            runner_config = RunnerConfig.objects.first()
            if not runner_config:
                runner_config = RunnerConfig.objects.create(
                    stars_per_kw=100,
                    max_training_runs_per_day=5
                )
            
            max_runs = runner_config.max_training_runs_per_day
            
            # Проверяем нужно ли сбросить счетчик
            if user_profile.training_run_last_date != today:
                UserProfile.objects.filter(user_id=user_profile.user_id).update(
                    training_run_count_today=0,
                    training_run_last_date=today
                )
                user_profile.refresh_from_db()
            
            # Проверяем лимит
            if user_profile.training_run_count_today >= max_runs:
                return Response(
                    {
                        "error": "training_run_limit_exceeded",
                        "max_runs_per_day": max_runs,
                        "runs_used_today": user_profile.training_run_count_today,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Увеличиваем счетчик тренировочных забегов
            UserProfile.objects.filter(user_id=user_profile.user_id).update(
                training_run_count_today=models.F('training_run_count_today') + 1,
                training_run_last_date=today
            )
            
            user_profile.refresh_from_db()
            serializer_data = UserProfileSerializer(user_profile).data
            
            return Response(
                {
                    "message": "Training run started",
                    "user": serializer_data,
                    "runs_used_today": user_profile.training_run_count_today,
                    "available_runs": max_runs - user_profile.training_run_count_today,
                },
                status=status.HTTP_200_OK,
            )
            
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            action_logger.error(f"TrainingRunStartView error: {str(e)}")
            return Response(
                {"error": f"Internal server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
```

#### 2.3. Добавление URL маршрутов

**Файл:** `edit/core/urls.py`

Добавить новые маршруты:

```python
urlpatterns = [
    # ... существующие маршруты ...
    path("training-run-check/", TrainingRunCheckView.as_view(), name="training_run_check"),
    path("training-run-start/", TrainingRunStartView.as_view(), name="training_run_start"),
    # ... остальные маршруты ...
]
```

### Этап 3: Backend - Админка

#### 3.1. Обновление RunnerConfigAdmin

**Файл:** `edit/core/admin.py`

Обновить админку для отображения нового поля:

```python
@admin.register(RunnerConfig)
class RunnerConfigAdmin(admin.ModelAdmin):
    list_display = ['stars_per_kw', 'max_training_runs_per_day']
    list_editable = ['stars_per_kw', 'max_training_runs_per_day']
    list_display_links = None
```

### Этап 4: Frontend - Обновление компонента GameRunView.vue

#### 4.1. Добавление проверки доступности тренировочных забегов

**Файл:** `src/views/GameRunView.vue`

Добавить реактивные переменные и функции для проверки доступности:

```javascript
// Добавить в script setup
const trainingRunsAvailable = ref(5) // По умолчанию 5
const maxTrainingRunsPerDay = ref(5)
const trainingRunsUsedToday = ref(0)
const canRunTraining = ref(true)

// Функция для проверки доступности тренировочных забегов
const checkTrainingRunAvailability = async () => {
  try {
    const response = await host.get('training-run-check/')
    if (response.data) {
      trainingRunsAvailable.value = response.data.available_runs || 0
      maxTrainingRunsPerDay.value = response.data.max_runs_per_day || 5
      trainingRunsUsedToday.value = response.data.runs_used_today || 0
      canRunTraining.value = response.data.can_run || false
    }
  } catch (error) {
    console.error('Error checking training run availability:', error)
    // В случае ошибки разрешаем запуск (fallback)
    canRunTraining.value = true
  }
}

// Вызывать при монтировании компонента и после завершения тренировочного забега
onMounted(() => {
  checkTrainingRunAvailability()
})
```

#### 4.2. Обновление функции handleTrainingClick

**Файл:** `src/views/GameRunView.vue`

Обновить функцию для проверки доступности перед запуском:

```javascript
const handleTrainingClick = async () => {
  // Проверяем доступность перед запуском
  if (!canRunTraining.value || trainingRunsAvailable.value <= 0) {
    alert(t('game.training_run_limit_exceeded', { 
      max: maxTrainingRunsPerDay.value,
      used: trainingRunsUsedToday.value 
    }))
    return
  }
  
  try {
    // Вызываем API для записи старта тренировочного забега
    const response = await host.post('training-run-start/')
    console.log('training-run-start response:', response.data)
    
    if (response.data.user) {
      // Обновляем данные пользователя если нужно
      if (response.data.user.training_run_count_today !== undefined) {
        app.user.training_run_count_today = response.data.user.training_run_count_today
      }
      if (response.data.user.training_run_last_date !== undefined) {
        app.user.training_run_last_date = response.data.user.training_run_last_date
      }
    }
    
    // Обновляем счетчик доступных забегов
    trainingRunsAvailable.value = response.data.available_runs || 0
    trainingRunsUsedToday.value = response.data.runs_used_today || 0
    
    // Запускаем тренировочный забег
    startGame(true)
  } catch (error) {
    // Если ошибка лимита - показываем сообщение
    if (error.response?.status === 400 && error.response?.data?.error === 'training_run_limit_exceeded') {
      const maxRuns = error.response.data.max_runs_per_day || 5
      const usedRuns = error.response.data.runs_used_today || 0
      alert(t('game.training_run_limit_exceeded', { 
        max: maxRuns,
        used: usedRuns 
      }))
      // Обновляем данные о доступности
      await checkTrainingRunAvailability()
      return
    }
    // Другие ошибки - запускаем игру всё равно (fallback)
    console.error('Error starting training run:', error)
    startGame(true)
  }
}
```

#### 4.3. Обновление шаблона кнопки "Тренировка"

**Файл:** `src/views/GameRunView.vue`

Обновить кнопку для отображения счетчика:

```vue
<button
  class="btn-primary btn-primary--training btn-primary--wide"
  :class="{ 'btn-disabled': !canRunTraining || trainingRunsAvailable <= 0 }"
  :disabled="!canRunTraining || trainingRunsAvailable <= 0"
  @click.stop.prevent="handleTrainingClick"
>
  <div class="training-button-content">
    <span>{{ t('game.run_training') }}</span>
    <span class="training-runs-available">
      {{ t('game.training_runs_available', { count: trainingRunsAvailable }) }}
    </span>
  </div>
</button>
```

#### 4.4. Добавление стилей для счетчика

**Файл:** `src/views/GameRunView.vue`

Добавить стили в секцию `<style>`:

```css
.training-button-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.training-runs-available {
  font-size: 0.75rem;
  opacity: 0.8;
  font-weight: normal;
}

.btn-primary--training.btn-disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
```

#### 4.5. Обновление после завершения тренировочного забега

**Файл:** `src/views/GameRunView.vue`

Обновить функцию `endGame` или место где завершается тренировочный забег для обновления счетчика:

```javascript
// После завершения тренировочного забега (в функции endGame или в соответствующем месте)
if (isTrainingRun.value) {
  // Обновляем доступность тренировочных забегов
  await checkTrainingRunAvailability()
}
```

### Этап 5: Локализация

#### 5.1. Добавление переводов

**Файлы:** Файлы локализации (например, `src/locales/ru.json`, `src/locales/en.json`)

Добавить новые ключи переводов:

```json
{
  "game": {
    "training_runs_available": "доступно {{count}}",
    "training_run_limit_exceeded": "Достигнут лимит тренировочных забегов на сегодня. Использовано: {{used}}/{{max}}"
  }
}
```

## Порядок выполнения

1. **Этап 1:** Создание миграций и обновление моделей
2. **Этап 2:** Реализация API endpoints
3. **Этап 3:** Обновление админки
4. **Этап 4:** Обновление фронтенда
5. **Этап 5:** Добавление переводов
6. **Тестирование:** Проверка работы ограничений, сброса счетчика, отображения в UI

## Важные замечания

1. **Сброс счетчика:** Счетчик должен сбрасываться автоматически при переходе на новый день (проверка по UTC)
2. **Fallback логика:** В случае ошибок API на фронтенде должна быть fallback логика, позволяющая запустить тренировочный забег
3. **Производительность:** Проверка доступности должна быть быстрой, использовать индексы в БД если нужно
4. **Безопасность:** Все проверки лимитов должны выполняться на бэкенде, фронтенд только для UX

## Тестирование

### Сценарии для тестирования:

1. ✅ Проверка доступности тренировочных забегов при первом запуске
2. ✅ Увеличение счетчика после каждого тренировочного забега
3. ✅ Блокировка запуска при достижении лимита
4. ✅ Сброс счетчика при переходе на новый день
5. ✅ Отображение количества доступных забегов в кнопке
6. ✅ Обновление счетчика после завершения тренировочного забега
7. ✅ Настройка лимита через админку
8. ✅ Проверка работы с разными значениями лимита (1, 5, 10)
