# Инструкция: Использование всех 10 уровней цен для бустов

## Краткое резюме

**Проблема:** Frontend ограничивает максимальный уровень цен до 7 (`price7`), хотя в модели `Booster` есть поля `price1-price10`. Уровни станций 8-10 используют `price7` вместо `price8`, `price9`, `price10`.

**Решение:** Изменить логику в frontend, чтобы каждый уровень станции (1-10) использовал свой соответствующий price (price1-price10), как это уже работает в backend.

**Важно:**
- ✅ Backend уже работает правильно (использует `STATION_LEVELS.index() + 1`)
- ✅ Логика с хешрейтом НЕ затронута (использует `priceByHash`)
- ⚠️ Нужно исправить только frontend логику

## Анализ текущей проблемы

### Текущая ситуация

**Проблема:** В frontend используется логика, которая ограничивает максимальный уровень до 7:
```javascript
Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3) >= 7 ? 7 : Math.ceil(...)
```

Это означает, что:
- Уровни станций 1-7 используют price1-price7
- Уровни станций 8-10 также используют price7 (максимум) ❌

**Backend логика (правильная):**
- В `get_booster_price()` используется `STATION_LEVELS.index(user.station_type) + 1`
- Это дает правильный индекс от 1 до 10
- Backend уже работает правильно ✅

**Frontend логика (неправильная):**
- Использует `Math.ceil(gen_config.id / 3) >= 7 ? 7 : ...`
- Ограничивает максимум до 7
- Не соответствует backend логике ❌

### Требование

**Нужно:** Каждый уровень станции (1-10) должен использовать свой соответствующий price (price1-price10):
- Уровень станции 1 → price1
- Уровень станции 2 → price2
- Уровень станции 3 → price3
- ...
- Уровень станции 10 → price10

**Важно:** 
- ✅ Логика с хешрейтом НЕ затронута (использует `priceByHash` который основан на `HashrateInfo`)
- ✅ Backend уже работает правильно (использует `STATION_LEVELS.index() + 1`)
- ⚠️ Нужно исправить только frontend логику, чтобы она соответствовала backend

## Решение

### Изменить логику в frontend

**Файл:** `src/components/Boost.vue`

#### Текущая логика (неправильная):
```javascript
// Ограничивает максимум до 7
price = `price${app?.user?.station_type ? (Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3) >= 7 ? 7 : Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3)) : 1}${paymentRadio.value == 'fbtc' ? "_fbtc" : ""}`
```

#### Новая логика (правильная):

**Использовать соответствие station_type → уровень (как в backend)**

Backend использует:
```python
STATION_LEVELS = [
    "Boiler house",           # индекс 0 → уровень 1
    "Coal power plant",       # индекс 1 → уровень 2
    "Thermal power plant",    # индекс 2 → уровень 3
    "Geothermal power plant", # индекс 3 → уровень 4
    "Nuclear power plant",    # индекс 4 → уровень 5
    "Thermonuclear power plant", # индекс 5 → уровень 6
    "Dyson Sphere",           # индекс 6 → уровень 7
    "Neutron star",           # индекс 7 → уровень 8
    "Antimatter",             # индекс 8 → уровень 9
    "Galactic core"           # индекс 9 → уровень 10
]
station_index = STATION_LEVELS.index(user.station_type) + 1  # от 1 до 10
```

**Frontend должен использовать ту же логику!**

## Рекомендуемое решение

Использовать соответствие `station_type` → уровень напрямую, как в backend.

### Шаг 1: Добавить константу STATION_LEVELS в Boost.vue

**Файл:** `src/components/Boost.vue`

После импортов (около строки 15), добавить:

```javascript
const STATION_LEVELS = [
  "Boiler house",
  "Coal power plant",
  "Thermal power plant",
  "Geothermal power plant",
  "Nuclear power plant",
  "Thermonuclear power plant",
  "Dyson Sphere",
  "Neutron star",
  "Antimatter",
  "Galactic core"
]
```

### Шаг 2: Создать функцию для определения уровня станции

**Файл:** `src/components/Boost.vue`

После константы `STATION_LEVELS`, добавить функцию:

```javascript
const getStationLevel = (stationType) => {
  if (!stationType) return 1
  const index = STATION_LEVELS.indexOf(stationType)
  return index >= 0 ? index + 1 : 1  // от 1 до 10
}
```

### Шаг 3: Обновить логику ценообразования в getTotalStarsPrice

**Файл:** `src/components/Boost.vue`

В функции `getTotalStarsPrice`, для всех бустов с уровнями станций, заменить сложную логику на простую:

**Было (для jarvis, строка 407):**
```javascript
price = `price${app?.user?.station_type ? (Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3) >= 7 ? 7 : Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3)) : 1}${paymentRadio.value == 'fbtc' ? "_fbtc" : ""}`
```

**Стало:**
```javascript
const stationLevel = getStationLevel(app?.user?.station_type)
price = `price${Math.min(stationLevel, 10)}${paymentRadio.value == 'fbtc' ? "_fbtc" : ""}`
```

**Применить для всех бустов с уровнями станций:**
- `jarvis` (строка 407)
- `cryo` (строка 416)
- `electrics` (строка 454)
- `premium_sub` (строка 463)
- `repair_kit` (строка 474)

### Шаг 4: Обновить логику в шаблоне (зачеркнутая цена)

**Файл:** `src/components/Boost.vue`

В шаблоне, где используется та же логика для отображения зачеркнутой цены (около строки 936-956), также заменить:

**Было:**
```javascript
`price${app?.user?.station_type
  ? Math.ceil(
    app.gen_config.find(
      (el) => el?.station_type == app?.user?.station_type,
    )?.id / 3,
  ) >= 7
    ? 7
    : Math.ceil(
      app.gen_config.find(
        (el) => el?.station_type == app?.user?.station_type,
      )?.id / 3,
    )
  : 1
}${paymentRadio == 'fbtc' ? "_fbtc" : ""}`
```

**Стало:**
```javascript
`price${getStationLevel(app?.user?.station_type)}${paymentRadio == 'fbtc' ? "_fbtc" : ""}`
```

**Применить в двух местах:**
- Первое место (строка 936-956) - для jarvis, cryo, repair_kit
- Второе место (около строки 980-1000) - аналогичная логика

## Важные замечания

### ✅ Логика с хешрейтом НЕ затронута

**Бусты с хешрейтом (magnit, asic_manager, powerbank):**
- Используют `priceByHash` который основан на `app.hashrate` и `HashrateInfo`
- Логика: `price = "price${priceByHash}"`
- Эта логика **НЕ изменяется**

**Вывод:** Бусты с хешрейтом продолжат работать как раньше.

### ✅ Backend логика НЕ изменяется

**Backend уже работает правильно:**
- `get_booster_price()` использует `STATION_LEVELS.index(user.station_type) + 1`
- Это дает правильный индекс от 1 до 10
- **Никаких изменений в backend не требуется**

**Вывод:** Backend продолжит работать как раньше, но теперь frontend будет использовать те же уровни.

### ⚠️ Проверка соответствия

**Важно проверить:**
1. Что `gen_config.id` в frontend соответствует уровню станции
2. Или использовать прямое соответствие через `STATION_LEVELS` (рекомендуется)

**Рекомендация:** Использовать прямое соответствие через `STATION_LEVELS`, как в backend. Это гарантирует правильную работу.

## Чеклист реализации

- [ ] Добавить константу `STATION_LEVELS` в `src/components/Boost.vue`
- [ ] Создать функцию `getStationLevel()` в `src/components/Boost.vue`
- [ ] Обновить логику для `jarvis` в `getTotalStarsPrice`
- [ ] Обновить логику для `cryo` в `getTotalStarsPrice`
- [ ] Обновить логику для `electrics` в `getTotalStarsPrice`
- [ ] Обновить логику для `premium_sub` в `getTotalStarsPrice`
- [ ] Обновить логику для `repair_kit` в `getTotalStarsPrice`
- [ ] Обновить логику в шаблоне (зачеркнутая цена) если используется
- [ ] Проверить, что бусты с хешрейтом (magnit, asic_manager) не затронуты
- [ ] Протестировать на тестовом сервере

## Файлы для изменения

1. **`src/components/Boost.vue`** - обновить логику ценообразования для бустов с уровнями станций

**Файлы, которые НЕ нужно менять:**
- ❌ `edit/tasks/services.py` - уже работает правильно
- ❌ Логика для бустов с хешрейтом - не изменяется
- ❌ Backend код - не требует изменений

## Пример изменений

### До изменений:
```javascript
// Используется максимум 7 уровней
price = `price${Math.ceil(gen_config.id / 3) >= 7 ? 7 : Math.ceil(gen_config.id / 3)}`
// Уровни 8-10 используют price7
```

### После изменений:
```javascript
// Используются все 10 уровней
const stationLevel = getStationLevel(app?.user?.station_type)  // от 1 до 10
price = `price${Math.min(stationLevel, 10)}`
// Уровень 8 → price8, уровень 9 → price9, уровень 10 → price10
```

## Тестирование

### Тест 1: Уровень станции 8 (Neutron star)

**До изменений:**
- `STATION_LEVELS.index("Neutron star") = 7`
- `station_index = 7 + 1 = 8`
- Frontend: `Math.ceil(id/3) >= 7 ? 7` → используется `price7` ❌

**После изменений:**
- `STATION_LEVELS.index("Neutron star") = 7`
- `station_index = 7 + 1 = 8`
- Frontend: `getStationLevel("Neutron star") = 8` → используется `price8` ✅

### Тест 2: Уровень станции 10 (Galactic core)

**До изменений:**
- `STATION_LEVELS.index("Galactic core") = 9`
- `station_index = 9 + 1 = 10`
- Frontend: `Math.ceil(id/3) >= 7 ? 7` → используется `price7` ❌

**После изменений:**
- `STATION_LEVELS.index("Galactic core") = 9`
- `station_index = 9 + 1 = 10`
- Frontend: `getStationLevel("Galactic core") = 10` → используется `price10` ✅

### Тест 3: Бусты с хешрейтом (magnit, asic_manager)

**До и после изменений:**
- Используют `priceByHash` который основан на `HashrateInfo`
- Логика не изменяется
- Продолжают работать как раньше ✅

