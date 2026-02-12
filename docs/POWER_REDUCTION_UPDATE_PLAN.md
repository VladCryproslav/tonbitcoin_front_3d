# План обновления системы снижения Power при генерации энергии

## Обзор

Данный документ описывает план обновления системы снижения процента Power электростанции при автоматической генерации энергии. После обновления система будет работать аналогично логике Jarvis, но только до момента достижения Storage limit.

## Текущее состояние

### Текущая логика генерации энергии

**Файл:** `edit/generation.py`

- Генерация происходит каждую минуту (цикл каждые 60 секунд)
- Формула генерации: `storage = storage + generation_rate * power / 100 / 60`
- Power **НЕ снижается** при генерации
- Генерация останавливается когда `storage >= storage_limit`
- Условия генерации:
  - `storage < storage_limit`
  - `overheated_until IS NULL`
  - `jarvis_expires < now` ИЛИ `jarvis_expires IS NULL` (Jarvis не активен)
  - `building_until < now` ИЛИ `building_until IS NULL` (станция не строится)

### Текущая логика снижения Power

**При ручном тапе** (`edit/core/views.py:TapEnergyView`):
- Power снижается по формуле: `power = power - (tapped_kw / generation_rate / 2 * sbt_get_power())`
- Снижение пропорционально количеству собранной энергии

**При работе Jarvis** (`edit/boosters.py`):
- Power снижается равномерно по времени: `power = power - (1 / 3600 * sbt_get_power())` каждые 2 секунды
- Снижение не зависит от генерации энергии

## Целевое состояние

### Новая логика снижения Power при генерации

1. **Power снижается при генерации** аналогично системе Jarvis
2. **По умолчанию**: Power снижается **ВСЕГДА**, даже когда `storage = storage_limit`
3. **Опционально**: Можно переключить на логику снижения только пока `storage < storage_limit` через флаг `POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL`
4. **Взаимодействие с Repair Kit**: когда активен, power не снижается
5. **Приоритет Jarvis**: когда работает Jarvis, используется его логика снижения power

### Формула снижения Power

Аналогично Jarvis, применяется в цикле генерации (каждую минуту):

```
power_reduction_per_minute = 1 / 120 * sbt_get_power()
```

**Компоненты:**
- `1 / 120` - снижение на 0.5% за час (аналогично Jarvis)
- `sbt_get_power()` - модификатор от SBT/premium:
  - `0.9` для Gold SBT или Premium подписки (снижение на 10% медленнее)
  - `0.95` для Silver SBT (снижение на 5% медленнее)
  - `1.0` для обычных пользователей

**Примеры снижения:**
- Без бонусов: `1/120 * 1.0 = 0.00833% в минуту` или `0.5% в час` или `12% в сутки`
- С Premium/Gold SBT: `1/120 * 0.9 = 0.0075% в минуту` или `0.45% в час` или `10.8% в сутки`
- С Silver SBT: `1/120 * 0.95 = 0.00792% в минуту` или `0.475% в час` или `11.4% в сутки`

**Примечание:** Скорость снижения power идентична Jarvis (0.5% в час без бонусов)

## План реализации

### Этап 1: Обновление файла генерации энергии

**Файл:** `edit/generation.py`

#### Изменения:

1. **Добавить импорт функций для работы с Repair Kit:**
   ```python
   from django.db.models.functions import Greatest
   ```

2. **ВАЖНО: Логика генерации энергии НЕ ИЗМЕНЕНА**
   - Оригинальная логика генерации остается без изменений
   - Генерация работает через массовое обновление как раньше

3. **Добавить отдельный блок для снижения power:**
   - Снижение power происходит отдельно от генерации
   - Добавлена защита: power не снижается если `power = 0`
   - Учтена активность Repair Kit
   - Исключены станции с активным Jarvis (они обрабатываются отдельно)

3. **Новый код:**

```python
# ОПЦИОНАЛЬНО: Переключение логики снижения power
# False (по умолчанию): power снижается ВСЕГДА, даже когда storage = storage_limit
# True: power снижается ТОЛЬКО пока storage < storage_limit
POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL = False

while True:
    start_time = time.time()
    with transaction.atomic():
        now = timezone.now()
        
        # ОРИГИНАЛЬНАЯ ЛОГИКА ГЕНЕРАЦИИ ЭНЕРГИИ (не изменена)
        logger.info(
            UserProfile.objects.filter(
                ~Q(storage=F("storage_limit"))
                & Q(overheated_until=None)
                & (Q(jarvis_expires__lt=now) | Q(jarvis_expires__isnull=True))
                & (Q(building_until__lt=now) | Q(building_until__isnull=True))
            ).update(
                storage=F("storage") + F("generation_rate") * F("power") / 100 / 60
            )
        )
        logger.info(
            UserProfile.objects.filter(storage__gt=F("storage_limit")).update(
                storage=F("storage_limit")
            )
        )
        
        # НОВАЯ ЛОГИКА: Снижение power при генерации
        # Получаем пользователей для снижения power (те же условия что и для генерации)
        users_for_power_reduction = UserProfile.objects.filter(
            Q(overheated_until=None)
            & (Q(jarvis_expires__lt=now) | Q(jarvis_expires__isnull=True))
            & (Q(building_until__lt=now) | Q(building_until__isnull=True))
            & Q(power__gt=0)  # Защита: не снижаем если power = 0
        )
        
        # Обрабатываем каждого пользователя для снижения power
        for u in users_for_power_reduction.all():
            # Проверяем активность Repair Kit
            is_repair_kit_active = (
                u.repair_kit_expires and
                now < u.repair_kit_expires
            )
            
            # Определяем нужно ли снижать power
            should_reduce_power = False
            
            if POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL:
                # Опциональная логика: снижение только пока storage < storage_limit
                should_reduce_power = (
                    float(u.storage) < float(u.storage_limit) and
                    not is_repair_kit_active
                )
            else:
                # По умолчанию: снижение всегда (кроме случаев с Repair Kit)
                should_reduce_power = not is_repair_kit_active
            
            # Применяем снижение power
            if should_reduce_power:
                # Снижение power аналогично Jarvis: 1/60 * sbt_get_power() за минуту
                power_reduction = 1 / 60 * u.sbt_get_power()
                UserProfile.objects.filter(id=u.id).update(
                    power=F("power") - power_reduction
                )
            elif is_repair_kit_active and u.repair_kit_power_level is not None:
                # Repair Kit активен: power не снижается, но может быть поднят
                UserProfile.objects.filter(id=u.id).update(
                    power=Greatest(
                        F("power"),
                        u.repair_kit_power_level,
                    )
                )
        
        # Ограничение power до минимума 0 (на всякий случай)
        UserProfile.objects.filter(power__lt=0).update(power=0)
        
        # ... остальной код (burn referral bonuses и т.д.)
```

### Этап 2: Обновление фронтенда (опционально)

**Цель:** Убрать необходимость тапов по экрану для сбора энергии

**Файлы для обновления:**
- `src/views/EnergizerView.vue` - убрать или скрыть кнопку тапа
- `src/composables/useGameRun.js` - обновить логику отображения

**Примечание:** Это изменение не обязательно для работы новой системы снижения power, но соответствует общей концепции автоматической генерации.

### Этап 3: Тестирование

1. **Тест базовой генерации:**
   - Проверить, что storage увеличивается
   - Проверить, что power снижается всегда (по умолчанию)
   - Проверить, что при `POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL = True` power не снижается когда `storage = storage_limit`

2. **Тест с Repair Kit:**
   - Проверить, что power не снижается когда Repair Kit активен
   - Проверить, что power поднимается до `repair_kit_power_level` если ниже

3. **Тест с Jarvis:**
   - Проверить, что станции с активным Jarvis не обрабатываются в цикле генерации
   - Проверить, что Jarvis использует свою логику снижения power

4. **Тест с SBT/Premium:**
   - Проверить разные значения `sbt_get_power()` (0.9, 0.95, 1.0)
   - Проверить правильность расчета снижения power

5. **Тест граничных случаев:**
   - Power = 0 (снижение НЕ должно происходить - защита в фильтре `power__gt=0`)
   - Power < 0 (должен быть установлен в 0 в конце цикла)
   - Storage = storage_limit (при `POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL = True` снижение должно остановиться)
   - Storage = storage_limit (при `POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL = False` снижение должно продолжаться)
   - Перегрев (станция не должна генерировать и снижать power)

## Детальная логика работы

### Условия для снижения Power

**Базовые условия (всегда):**
1. ✅ `overheated_until IS NULL` (станция не перегрета)
2. ✅ `jarvis_expires < now` ИЛИ `jarvis_expires IS NULL` (Jarvis не активен)
3. ✅ `building_until < now` ИЛИ `building_until IS NULL` (станция не строится)
4. ✅ `power > 0` (защита: не снижаем если power уже равен 0)
5. ✅ `repair_kit_expires IS NULL` ИЛИ `repair_kit_expires < now` (Repair Kit не активен)

**Логика снижения power:**

**По умолчанию** (`POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL = False`):
- Power снижается **ВСЕГДА**, если выполняются базовые условия
- Не зависит от заполненности storage

**Опционально** (`POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL = True`):
- Power снижается **ТОЛЬКО** если `storage < storage_limit`
- Когда `storage = storage_limit`, снижение останавливается

### Приоритет систем

1. **Jarvis** - имеет наивысший приоритет, обрабатывается отдельно в `boosters.py`
2. **Repair Kit** - останавливает снижение power, но не останавливает генерацию
3. **Обычная генерация** - снижает power по умолчанию всегда, опционально только пока `storage < storage_limit`

### Взаимодействие с Repair Kit

Когда Repair Kit активен:
- ✅ Генерация энергии продолжается
- ❌ Power **НЕ снижается**
- ✅ Power может быть поднят до `repair_kit_power_level` если он ниже

**Код:**
```python
if is_repair_kit_active and u.repair_kit_power_level is not None:
    update_data["power"] = Greatest(
        F("power"),
        u.repair_kit_power_level,
    )
```

### Взаимодействие с Jarvis

Когда Jarvis активен:
- ✅ Генерация энергии происходит через `boosters.py` (добавляется в `energy`, не в `storage`)
- ✅ Снижение power происходит через `boosters.py` по своей формуле
- ❌ Станция **НЕ обрабатывается** в цикле `generation.py`

**Условие исключения:**
```python
& (Q(jarvis_expires__lt=now) | Q(jarvis_expires__isnull=True))
```

## Миграция и активация

### Поэтапная активация

**Примечание:** Снижение power включено по умолчанию. Флаг `POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL` только переключает логику между режимами снижения.

1. **Этап 1:** Развернуть код (снижение power включено по умолчанию)
2. **Этап 2:** Протестировать на тестовой среде
3. **Этап 3:** Мониторинг метрик (снижение power, генерация энергии)
4. **Этап 4:** При необходимости переключить `POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL = True` для логики "только пока storage не заполнен"

### Откат

Если потребуется отключить снижение power полностью:
- Закомментировать блок снижения power в коде
- Перезапустить процесс `generation.py`
- Система вернется к логике только генерации без снижения power

## Ожидаемые результаты

### Преимущества новой системы

1. **Автоматическое снижение power** - не требует ручных тапов
2. **Предсказуемое снижение** - равномерное по времени, как у Jarvis
3. **Остановка при заполнении storage** - power не снижается когда storage полон
4. **Совместимость с Repair Kit** - защита от снижения power
5. **Совместимость с Jarvis** - не конфликтует с существующей логикой

### Влияние на игровой процесс

**По умолчанию** (`POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL = False`):
- **Без бонусов:** Power снижается на `0.5% в час` или `12% в сутки` постоянно
- **С Premium/Gold SBT:** Power снижается на `0.45% в час` или `10.8% в сутки` постоянно
- **С Silver SBT:** Power снижается на `0.475% в час` или `11.4% в сутки` постоянно
- Снижение происходит **независимо от заполненности storage**
- **Скорость снижения идентична Jarvis**

**Опционально** (`POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL = True`):
- Снижение происходит только пока `storage < storage_limit`
- Когда storage заполнен, power стабилизируется

## Дополнительные замечания

### Опциональность системы

Система имеет два уровня опциональности:

1. **Флаг `POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL`:**
   - `False` (по умолчанию): power снижается всегда, даже когда storage заполнен
   - `True`: power снижается только пока `storage < storage_limit`

2. **Преимущества опциональности:**
   - Легко переключать между режимами
   - Тестировать разные стратегии снижения power
   - Адаптировать под игровой баланс

### Производительность

Новая логика использует цикл `for u in users_to_update.all()` вместо массового `update()`. Это может быть медленнее для большого количества пользователей. 

**Рекомендация:** Мониторить производительность и при необходимости оптимизировать через:
- Батчинг обновлений
- Использование `bulk_update()` вместо отдельных `update()`
- Индексацию БД для полей `storage`, `storage_limit`, `jarvis_expires`, `repair_kit_expires`

## Важные замечания

### Сохранение оригинальной логики генерации

**КРИТИЧЕСКИ ВАЖНО:** Логика генерации энергии остается полностью неизменной:
- Используется массовое обновление через `.update()` как раньше
- Условия генерации не изменены
- Производительность не ухудшена

### Защита от снижения при power = 0

Добавлена защита в фильтр: `Q(power__gt=0)` - пользователи с `power = 0` исключаются из обработки снижения power. Это предотвращает:
- Попытки снизить power ниже 0
- Лишние запросы к БД для пользователей с нулевым power

## Заключение

Данный план описывает полное обновление системы снижения Power при генерации энергии. Система работает аналогично Jarvis:

- **По умолчанию**: Power снижается всегда, даже когда storage заполнен
- **Опционально**: Можно переключить на логику снижения только пока `storage < storage_limit` через флаг `POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL`
- **Защита**: Power не снижается если `power = 0`
- **Безопасность**: Оригинальная логика генерации не изменена

Реализация включает опциональный флаг для гибкой настройки поведения системы и тестирования разных стратегий игрового баланса.
