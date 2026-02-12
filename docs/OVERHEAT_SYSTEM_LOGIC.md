# Анализ логики работы системы перегревов (Overheat)

## Обзор

Система перегревов предотвращает чрезмерное использование электростанции и наказывает игроков за использование станции во время перегрева. Данный документ описывает детальную логику работы системы перегревов.

## Основные компоненты

### Модель данных

**Поля в `UserProfile`:**
- `overheated_until` (DateTimeField) - время окончания перегрева (NULL если перегрев не активен)
- `tap_count_since_overheat` (PositiveIntegerField) - счетчик тапов с момента начала перегрева
- `overheat_energy_collected` (FloatField) - накопленная энергия для расчета перегрева
- `overheat_goal` (FloatField, nullable) - случайная цель для активации перегрева
- `was_overheated` (BooleanField) - флаг, что станция уже была перегрета

**Модель `OverheatConfig`:**
- `min_duration` (PositiveIntegerField, default=15) - минимальная длительность перегрева в минутах
- `max_duration` (PositiveIntegerField, default=300) - максимальная длительность перегрева в минутах
- `taps_before_power_reduction` (PositiveIntegerField, default=5) - количество тапов до начала снижения power
- `power_reduction_percentage` (FloatField, default=1.0) - процент снижения power за каждый тап после лимита

**Конфигурация по типам станций:**
```python
overheat_hours_by_type = {
    "Thermal power plant": 4,        # station #3 - 1 перегрев за 4 часа (6 перегревов в сутки)
    "Geothermal power plant": 2,     # station #4 - 1 перегрев за 2 часа (12 перегревов в сутки)
    "Nuclear power plant": 2,        # station #5 - 1 перегрев за 2 часа (12 перегревов в сутки)
    "Thermonuclear power plant": 1,  # station #6 - 1 перегрев за 1 час (24 перегрева в сутки)
    "Dyson Sphere": 1,               # station #7 - 1 перегрев за 1 час (24 перегрева в сутки)
}
```

**Частота перегревов согласно ТЗ:**
- **Станция №3** (Thermal power plant): 1 перегрев за каждые 4 часа видобутой энергии = **6 перегревов в сутки**
- **Станция №4-5** (Geothermal/Nuclear): 1 перегрев за каждые 2 часа видобутой энергии = **12 перегревов в сутки**
- **Станция №6-7** (Thermonuclear/Dyson Sphere): 1 перегрев за каждый час згенерованой энергии = **24 перегрева в сутки**

## Логика активации перегрева

### Условия для активации

Перегрев активируется только если выполняются **ВСЕ** условия:

1. ✅ Станция имеет тип из `overheat_hours_by_type` (не все типы станций могут перегреваться)
2. ✅ Cryo Chamber **НЕ активен** (`cryo_expires IS NULL` ИЛИ `cryo_expires < now`)
3. ✅ Игрок собирает энергию через тапы (не через Jarvis)

### Механизм активации

**Согласно ТЗ:** Станция перегрівається один раз на одну годину генерації у випадковий момент (для кожної станції є визначена частота активацій).

**Шаг 1: Установка цели перегрева (первый перегрев)**

При первом тапе после охлаждения (если `overheat_goal IS NULL`):
```python
overheat_goal = random.uniform(
    0,
    generation_rate * needed_hours * (power / 100)
)
```

**Где:**
- `generation_rate` - скорость генерации станции (kW/час)
- `needed_hours` - количество часов из `overheat_hours_by_type` для данного типа станции
- `power / 100` - текущий процент power (0.0-1.0)

**Логика:** Перегрев происходит в **случайный момент** в пределах периода `needed_hours`. Например:
- Для станции №6-7 (`needed_hours = 1`): перегрев может произойти в любой момент от 0 до 1 часа генерации
- Для станции №4-5 (`needed_hours = 2`): перегрев может произойти в любой момент от 0 до 2 часов генерации
- Для станции №3 (`needed_hours = 4`): перегрев может произойти в любой момент от 0 до 4 часов генерации

**Пример расчета:**
Для Dyson Sphere (станция №7) с `generation_rate = 1000 kW/час`, `power = 80%`, `needed_hours = 1`:
```
overheat_goal = random.uniform(0, 1000 * 1 * 0.8) = random.uniform(0, 800) kW
```
Перегрев произойдет когда будет собрано от 0 до 800 kW (случайное значение в пределах 1 часа генерации).

**Пример из ТЗ:**
Атомна електростанція 3 рівня з 3 рівнем генерації:
- Storage = 980 kW
- Генерація в годину = 245 kW
- Для заповнення сховища необхідно 4 години (980 / 245 = 4)
- Станция №4-5: `needed_hours = 2`
- За 4 години генерації перегрів має з'явитися **2 рази** (4 / 2 = 2)
- Перший перегрев: случайный момент от 0 до 2 часов генерации (0-490 kW)
- Второй перегрев: через 2 часа после первого (490-980 kW)

**Шаг 2: Накопление энергии**

При каждом тапе энергия добавляется в `overheat_energy_collected`:
```python
overheat_energy_collected = overheat_energy_collected + tapped_kw
```

**Шаг 3: Активация перегрева**

Когда `overheat_energy_collected >= overheat_goal`:
```python
duration = random.randint(min_duration, max_duration)  # в минутах
overheated_until = now + timedelta(minutes=duration)
was_overheated = True
```

**Пример:**
- `min_duration = 15` минут
- `max_duration = 300` минут (5 часов)
- `duration = random.randint(15, 300)` = например, 120 минут (2 часа)
- `overheated_until = now + 2 часа`

### Логика после первого перегрева

После первого перегрева (`was_overheated = True`), цель перегрева меняется:

**Новая цель (фиксированная):**
```python
overheat_goal = generation_rate * needed_hours
```

**Отличия:**
- Цель больше не зависит от `power`
- Цель фиксированная (не случайная) - точно через `needed_hours` часов генерации
- Обычно выше, чем первая случайная цель (так как не умножается на `power / 100`)

**Логика:** После первого перегрева последующие перегревы происходят **точно** через `needed_hours` часов генерации, без случайности.

**Сброс состояния:**
Когда `overheat_energy_collected >= overheat_goal`:
```python
was_overheated = False
overheat_energy_collected = 0
overheat_goal = None
```

После этого цикл начинается заново с новой случайной целью (первый перегрев снова будет случайным).

**Пример:**
Для станции №6-7 (`needed_hours = 1`):
- Первый перегрев: случайный момент от 0 до 1 часа генерации
- Второй перегрев: точно через 1 час генерации после первого
- Третий перегрев: точно через 1 час генерации после второго
- И так далее...

Для станции №4-5 (`needed_hours = 2`):
- Первый перегрев: случайный момент от 0 до 2 часов генерации
- Второй перегрев: точно через 2 часа генерации после первого
- Третий перегрев: точно через 2 часа генерации после второго
- И так далее...

## Поведение во время перегрева

### Блокировка генерации энергии

**Файл:** `edit/generation.py`

Когда `overheated_until > now`:
- ❌ Станция **НЕ генерирует** энергию автоматически
- ❌ Условие: `Q(overheated_until=None)` в фильтре генерации

**Код:**
```python
UserProfile.objects.filter(
    ~Q(storage=F("storage_limit"))
    & Q(overheated_until=None)  # Перегрев блокирует генерацию
    & ...
).update(...)
```

### Поведение при тапах во время перегрева

**Файл:** `edit/core/views.py:TapEnergyView`

Когда игрок пытается тапать во время перегрева (`overheated_until > now`):

**1. Всегда увеличивается счетчик тапов:**
```python
tap_count_since_overheat = tap_count_since_overheat + 1
```

**2. Проверка лимита тапов:**

Если `tap_count_since_overheat >= taps_before_power_reduction` (по умолчанию 5):
- **Без Repair Kit:** Power снижается на `power_reduction_percentage` (по умолчанию 1%)
- **С Repair Kit:** Power **НЕ снижается**, только счетчик увеличивается

**3. Возврат ошибки:**

API всегда возвращает ошибку 400:
```python
{
    "message": "Station is overheated. Please wait until it cools down.",
    "overheated_until": "2026-02-12T15:30:00Z",
    "total_energy": 1000.5,
    "power": 80.0,
    "storage": 500.0
}
```

**Код:**
```python
if user_profile.overheated_until:
    is_repair_kit_active = (
        user_profile.repair_kit_expires and
        timezone.now() < user_profile.repair_kit_expires
    )
    
    if user_profile.tap_count_since_overheat >= overheat_config.taps_before_power_reduction:
        if not is_repair_kit_active:
            # Снижение power
            power = power - overheat_config.power_reduction_percentage
        # С Repair Kit: power не снижается
    
    tap_count_since_overheat = tap_count_since_overheat + 1
    return Response({...}, status=400)  # Ошибка
```

### Пример поведения

**Сценарий:** Игрок тапает во время перегрева

1. **Тап 1-4:** Только счетчик увеличивается, power не снижается
2. **Тап 5+:** 
   - Без Repair Kit: `power = power - 1%` за каждый тап
   - С Repair Kit: power не снижается

**Пример:**
- Начальный power: 80%
- Тапы 1-4: power остается 80%
- Тап 5: power = 79% (без Repair Kit)
- Тап 6: power = 78% (без Repair Kit)
- И так далее...

## Охлаждение станции

### Автоматическое охлаждение

Перегрев автоматически заканчивается когда `overheated_until <= now`.

**Проверка в коде:**
```python
if user_profile.overheated_until and user_profile.overheated_until <= now:
    # Перегрев закончился
```

### Ручное охлаждение через Autostart

**Файл:** `edit/boosters.py`

Autostart может автоматически снять перегрев:
```python
UserProfile.objects.filter(
    autostart_count__gt=0,
    overheated_until__lt=now  # Перегрев уже закончился
).update(
    overheated_until=None,
    tap_count_since_overheat=0,
    autostart_count=F("autostart_count") - 1,
)
```

**Примечание:** Autostart снимает перегрев только если он уже закончился (`overheated_until < now`), но счетчик тапов не был сброшен.

### Ручное охлаждение через API

**Файл:** `edit/core/views.py` (около строки 3178)

Существует endpoint для ручного снятия перегрева (вероятно, для админки или специальных действий):
```python
if user_profile.overheated_until > timezone.now():
    return Response({"error": "Station is overheated"}, status=400)
    
UserProfile.objects.filter(user_id=user_profile.user_id).update(
    overheated_until=None,
    tap_count_since_overheat=0
)
```

## Взаимодействие с другими системами

### 1. Cryo Chamber

**Защита от перегрева:**
- Когда Cryo активен (`cryo_expires > now`), перегрев **НЕ может активироваться**
- Условие: `if needed_hours and not is_cryo_active`

**Код:**
```python
is_cryo_active = (
    user_profile.cryo_expires and
    timezone.now() < user_profile.cryo_expires
)

if needed_hours and not is_cryo_active:
    # Логика перегрева только если Cryo НЕ активен
```

### 2. Repair Kit

**Защита от снижения power:**
- Когда Repair Kit активен, power **НЕ снижается** при тапах во время перегрева
- Счетчик тапов все равно увеличивается

**Код:**
```python
if is_repair_kit_active:
    # Power не снижается
    tap_count_since_overheat = tap_count_since_overheat + 1
else:
    # Power снижается
    power = power - power_reduction_percentage
    tap_count_since_overheat = tap_count_since_overheat + 1
```

### 3. Jarvis

**Полная защита:**
- Когда Jarvis активен, игрок **НЕ может тапать** вручную
- Перегрев **НЕ может активироваться**, так как нет тапов
- Условие в `TapEnergyView`: `if jarvis_expires > now: return error`

**Код:**
```python
if user_profile.jarvis_expires and user_profile.jarvis_expires > timezone.now():
    return Response(
        {"error": "Jarvis is active. Please wait until it expires."},
        status=400
    )
```

### 4. Автоматическая генерация

**Блокировка генерации:**
- Когда `overheated_until > now`, автоматическая генерация **останавливается**
- Условие в `generation.py`: `Q(overheated_until=None)`

### 5. Autostart

**Автоматическое снятие:**
- Autostart может автоматически сбросить `overheated_until` и `tap_count_since_overheat`
- Использует один заряд `autostart_count`
- Работает только если перегрев уже закончился по времени

## Примеры работы системы

### Пример 1: Первый перегрев (станция №7 - Dyson Sphere)

**Условия:**
- Тип станции: Dyson Sphere (`needed_hours = 1`)
- `generation_rate = 1000 kW/час`
- `power = 80%`
- `was_overheated = False`

**Процесс:**

1. **Установка цели (случайный момент в пределах 1 часа):**
   ```
   overheat_goal = random.uniform(0, 1000 * 1 * 0.8) = random.uniform(0, 800)
   Допустим: overheat_goal = 450 kW
   ```
   Перегрев произойдет когда будет собрано 450 kW (случайный момент от 0 до 800 kW).

2. **Накопление энергии:**
   - Тап 1: `overheat_energy_collected = 50 kW` (50/450)
   - Тап 2: `overheat_energy_collected = 120 kW` (120/450)
   - ...
   - Тап N: `overheat_energy_collected = 450 kW` (450/450) ✅

3. **Активация перегрева:**
   ```
   duration = random.randint(15, 300) = 120 минут (2 часа)
   overheated_until = now + 2 часа
   was_overheated = True
   ```

**Результат:** Перегрев произошел в случайный момент (на 450 kW из возможных 800 kW) в пределах 1 часа генерации.

### Пример 2: Повторный перегрев (станция №7 - Dyson Sphere)

**Условия:**
- `was_overheated = True` (уже был перегрев)
- `generation_rate = 1000 kW/час`
- `needed_hours = 1`

**Процесс:**

1. **Новая цель (фиксированная - точно через 1 час):**
   ```
   overheat_goal = 1000 * 1 = 1000 kW
   ```
   Перегрев произойдет точно через 1 час генерации (1000 kW), без случайности.

2. **Накопление энергии:**
   - Нужно собрать 1000 kW энергии через тапы
   - После первого перегрева счетчик начинается с 0

3. **Активация перегрева:**
   ```
   duration = random.randint(15, 300)
   overheated_until = now + duration
   ```

4. **После перегрева:**
   ```
   was_overheated = False
   overheat_energy_collected = 0
   overheat_goal = None
   ```
   Цикл начинается заново с новой случайной целью (следующий перегрев снова будет случайным).

**Результат:** После первого перегрева последующие перегревы происходят точно через 1 час генерации (24 перегрева в сутки для станции №7).

### Пример 3: Пример из ТЗ (Атомна електростанція)

**Условия из ТЗ:**
- Тип станции: Атомна електростанція (станция №5, `needed_hours = 2`)
- Рівень генерації: 3
- Storage = 980 kW
- Генерація в годину = 245 kW
- Для заповнення сховища необхідно: 980 / 245 = **4 години**

**Процесс:**

1. **За 4 часа генерации должно произойти 2 перегрева** (4 / 2 = 2)

2. **Первый перегрев (случайный момент):**
   ```
   overheat_goal = random.uniform(0, 245 * 2 * (power/100))
   Допустим: overheat_goal = 300 kW (случайное значение от 0 до 490 kW при power=100%)
   ```
   Перегрев произойдет когда будет собрано 300 kW (в случайный момент от 0 до 2 часов генерации).

3. **Второй перегрев (фиксированный):**
   ```
   overheat_goal = 245 * 2 = 490 kW
   ```
   Перегрев произойдет точно через 2 часа генерации после первого (на 490 kW).

**Результат:** За 4 часа генерации (980 kW) произойдет 2 перегрева в случайном порядке:
- Первый: случайный момент (например, на 300 kW)
- Второй: точно через 2 часа после первого (на 490 kW от начала второго цикла)

### Пример 4: Тапы во время перегрева

**Условия:**
- `overheated_until > now` (перегрев активен)
- `taps_before_power_reduction = 5`
- `power_reduction_percentage = 1.0`
- `power = 80%`
- Repair Kit **НЕ активен**

**Процесс:**

1. **Тап 1:** `tap_count_since_overheat = 1`, power = 80% (без изменений)
2. **Тап 2:** `tap_count_since_overheat = 2`, power = 80% (без изменений)
3. **Тап 3:** `tap_count_since_overheat = 3`, power = 80% (без изменений)
4. **Тап 4:** `tap_count_since_overheat = 4`, power = 80% (без изменений)
5. **Тап 5:** `tap_count_since_overheat = 5`, power = 79% (снижение на 1%)
6. **Тап 6:** `tap_count_since_overheat = 6`, power = 78% (снижение на 1%)
7. **Тап 7:** `tap_count_since_overheat = 7`, power = 77% (снижение на 1%)

**С Repair Kit активным:**
- Все тапы: power остается 80% (не снижается)

## Влияние на игровой процесс

### Преимущества системы

1. **Балансировка игры** - предотвращает чрезмерное использование станции
2. **Стратегический выбор** - игроки должны решать, когда собирать энергию
3. **Стимул к покупке бустеров** - Cryo, Repair Kit, Jarvis защищают от перегрева

### Недостатки для игрока

1. **Блокировка генерации** - станция не генерирует энергию во время перегрева
2. **Наказание за тапы** - использование станции во время перегрева снижает power
3. **Случайность** - длительность перегрева случайная (15-300 минут)

### Стратегии защиты

1. **Cryo Chamber** - полностью предотвращает перегрев
2. **Repair Kit** - защищает от снижения power во время перегрева
3. **Jarvis** - предотвращает тапы, что предотвращает перегрев
4. **Autostart** - может автоматически снять перегрев (использует заряд)

## Выводы

### Ключевые моменты системы перегревов:

1. **Частота перегревов:** Зависит от типа станции (6/12/24 перегрева в сутки)
2. **Активация:** Первый перегрев происходит в случайный момент в пределах периода `needed_hours`
3. **Повторные перегревы:** Происходят точно через `needed_hours` часов генерации (без случайности)
4. **Поведение:** Блокирует генерацию, наказывает за тапы снижением power
5. **Охлаждение:** Автоматическое по времени или через Autostart
6. **Защита:** Cryo, Repair Kit, Jarvis предоставляют различные уровни защиты
7. **Баланс:** Первый перегрев легче активировать (зависит от power), последующие требуют фиксированного количества энергии

### Формулы:

**Первая цель перегрева (случайный момент):**
```
overheat_goal = random.uniform(0, generation_rate * needed_hours * (power / 100))
```
Перегрев происходит в случайный момент в пределах периода `needed_hours` часов генерации.

**Повторная цель перегрева (фиксированная):**
```
overheat_goal = generation_rate * needed_hours
```
Перегрев происходит точно через `needed_hours` часов генерации после предыдущего перегрева.

**Частота перегревов:**
- Станция №3: 1 перегрев за 4 часа = **6 перегревов в сутки**
- Станция №4-5: 1 перегрев за 2 часа = **12 перегревов в сутки**
- Станция №6-7: 1 перегрев за 1 час = **24 перегрева в сутки**

**Длительность перегрева:**
```
duration = random.randint(min_duration, max_duration) минут
overheated_until = now + duration
```

**Снижение power при тапах:**
```
if tap_count_since_overheat >= taps_before_power_reduction:
    if not repair_kit_active:
        power = power - power_reduction_percentage
```

Система перегревов является важным механизмом балансировки игры и стимулирует использование защитных бустеров.
