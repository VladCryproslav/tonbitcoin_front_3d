# План: количество поинтов за энергозабег в зависимости от времени

## Цель

Сделать систему, которая создаёт во время энергозабега количество поинтов в зависимости от времени, прошедшего с момента последнего забега. Забег доступен раз в час; момент последнего старта хранится в `UserProfile.energy_run_last_started_at`.

## Требования (кратко)

| Прошло времени | Базовых поинтов (до запаса) |
|----------------|----------------------------|
| 1 ч            | 120                        |
| 2 ч            | 240                        |
| 3 ч            | 360                        |
| 4 ч            | 480 (максимум)             |
| 1.5 ч          | 180 (1 минута = n поинтов) |

- Формула: **1 минута = n поинтов** (n настраивается, по умолчанию 2).
- Сверху добавляется **статический процент запаса** (например 20%), настраивается в админке.
- Лимит: **не более 4 часов** в расчёте (4 ч × 60 мин × n = 480 при n=2).

## Текущее состояние

### Фронтенд (`src/composables/useGameRun.js`)

- Константы:
  - `ENERGY_POINTS_BASE_COUNT = 150` — базовое количество поинтов за забег.
  - `ENERGY_POINTS_RESERVE_PERCENT = 20` — процент запаса сверх базового.
- `generateEnergyPoints(storageKw)` — строит массив поинтов от `ENERGY_POINTS_BASE_COUNT` и `ENERGY_POINTS_RESERVE_PERCENT`.
- `startRun(initialStorage)` — принимает только `initialStorage`; количество поинтов всегда 150 + 20%.
- Условия завершения забега и логика `pointsFor100Percent` завязаны на это фиксированное число.

### Бэкенд

- `EnergyRunStartView` (POST `energy-run-start/`):
  - Проверяет cooldown 60 минут по `energy_run_last_started_at`.
  - Обновляет `energy_run_last_started_at`, `energy_run_start_storage`, обнуляет `storage`.
  - В ответе отдаёт `user` (сериализованный профиль), без полей про количество поинтов.
- `RunnerConfig` (админка `core/runnerconfig/`):
  - Сейчас: `stars_per_kw`, `max_training_runs_per_hour`.
  - Нет полей для «поинтов за минуту» и «процент запаса» для энергозабега.

### Цепочка вызовов (энергозабег)

1. Пользователь жмёт «Старт» → `startRun()` в `GameRunView.vue`.
2. `POST energy-run-start/` → в ответе `user` (storage, energy_run_last_started_at и т.д.).
3. `startGame(false, initialStorage)` → `gameRun.startRun(initialStorage)`.
4. В `useGameRun.js` генерируются поинты с константами 150 и 20%.

---

## План разработки (без правок в коде)

### 1. Модель и админка RunnerConfig (бэкенд)

**Файлы:** `edit/core/models.py`, `edit/core/admin.py`, миграция.

- В **RunnerConfig** добавить поля:
  - `energy_points_per_minute` (IntegerField, default=2) — сколько базовых поинтов начисляется за 1 минуту ожидания (1 ч → 120 при 2).
  - `energy_points_reserve_percent` (IntegerField, default=20) — процент запаса поинтов сверху (как текущий ENERGY_POINTS_RESERVE_PERCENT).
  - `energy_run_max_hours` (IntegerField, default=4) — максимум часов для расчёта поинтов (4 ч → макс. 480 при 2 поинта/мин).
- В **RunnerConfigAdmin**: вывести и при необходимости сделать редактируемыми эти три поля (list_display / list_editable).
- Создать и применить миграцию.

Итог: в админке `.../core/runnerconfig/` появятся настройки «1 минута = n поинтов» и «процент запаса», плюс лимит по часам.

---

### 2. Расчёт поинтов при старте энергозабега (бэкенд)

**Файл:** `edit/core/views.py`, класс `EnergyRunStartView`.

- **До** обновления профиля в БД:
  - Взять текущее значение `user_profile.energy_run_last_started_at` (момент предыдущего старта).
  - Если поля нет (первый забег или старые данные) — считать «прошло 1 час» (например `prev = now - timedelta(hours=1)`).
  - Вычислить: `elapsed_seconds = (now - prev).total_seconds()`, `elapsed_minutes = elapsed_seconds / 60`.
- Загрузить **RunnerConfig** (один объект, как для training runs). Взять:
  - `points_per_minute = runner_config.energy_points_per_minute`
  - `reserve_percent = runner_config.energy_points_reserve_percent`
  - `max_hours = runner_config.energy_run_max_hours`
- Формула базовых поинтов:
  - `max_base_points = max_hours * 60 * points_per_minute` (например 4*60*2 = 480).
  - `base_points = min(max_base_points, int(elapsed_minutes) * points_per_minute)`  
    (дробные минуты можно отбрасывать или округлять вниз — уточнить в реализации).
- В **ответ** POST `energy-run-start/` добавить два поля (например в корень ответа или в `user`):
  - `energy_run_base_points` — рассчитанное базовое количество поинтов на этот забег.
  - `energy_run_reserve_percent` — процент запаса из RunnerConfig (чтобы фронт не хардкодил).

Итог: при каждом старте энергозабега бэкенд отдаёт, сколько базовых поинтов и какой процент запаса использовать для этого забега.

---

### 3. Фронтенд: использование динамических значений (useGameRun.js)

**Файл:** `src/composables/useGameRun.js`.

- Оставить константы `ENERGY_POINTS_BASE_COUNT` и `ENERGY_POINTS_RESERVE_PERCENT` как **fallback** (например для тренировочного забега или если бэкенд не вернул значения).
- **generateEnergyPoints(storageKw, baseCount, reservePercent)**:
  - Добавить опциональные аргументы `baseCount`, `reservePercent`.
  - Если не переданы — использовать константы.
  - Внутри: `totalPointsCount = ceil(baseCount * (1 + reservePercent/100))` и далее текущая логика распределения по типам и масштаба процентов от этого количества.
- **startRun(initialStorage, basePoints = null, reservePercent = null)**:
  - Добавить опциональные параметры.
  - При вызове `generateEnergyPoints(storageKw, basePoints ?? ENERGY_POINTS_BASE_COUNT, reservePercent ?? ENERGY_POINTS_RESERVE_PERCENT)` передавать их.
  - Все computed (`pointsFor100Percent`, логика завершения забега и т.д.) уже опираются на фактическое количество сгенерированных поинтов и формулу «базис + запас» — нужно убедиться, что они используют те же `basePoints` и `reservePercent` (или сохранённые при старте значения), а не только константы. При необходимости завести ref’ы под «текущий базис/процент забега» и выставлять их в `startRun`.
- **getNextEnergyPoint** и порционная догенерация поинтов: оставить логику, но она должна опираться на тот же `pointsFor100Percent` (уже считаемый от динамического базиса и процента).

Итог: один энергозабег может стартовать с произвольным базовым количеством и процентом запаса, переданным извне; при отсутствии данных — поведение как сейчас (150 + 20%).

---

### 4. Фронтенд: передача параметров из ответа energy-run-start (GameRunView.vue)

**Файл:** `src/views/GameRunView.vue`.

- В обработчике ответа `POST energy-run-start/`:
  - Из ответа читать `energy_run_base_points` и `energy_run_reserve_percent` (или из `response.data.user`, если бэкенд положит туда).
  - Вызывать `startGame(false, initialStorage, basePoints, reservePercent)` с этими значениями.
- **startGame(training, initialStorage, basePoints, reservePercent)**:
  - Добавить два опциональных аргумента.
  - Для энергозабега (`training === false`) передавать в `gameRun.startRun(initialStorage, basePoints, reservePercent)`.
  - Для тренировочного забега (`training === true`) вызывать `gameRun.startRun(initialStorage)` без base/reserve (или с null), чтобы использовались константы 150 и 20%.

Итог: при старте энергозабега фронт получает от бэкенда «сколько поинтов за этот забег» и «процент запаса» и передаёт их в useGameRun.

---

### 5. Валидация и полная завершённость забега (бэкенд, опционально)

- В **GameRunCompleteView** и при необходимости в **GameRunClaimView** можно добавить проверку: ожидаемое количество поинтов для данного забега (по сохранённому при старте `energy_run_base_points` и `energy_run_reserve_percent`, если их начнём сохранять в профиле) не сильно превышает фактически переданные клиентом данные — для дополнительной защиты от подмены. Это отдельный шаг; минимально достаточно расчёта при старте и передачи на фронт.

---

### 6. Тренировочный забег

- Оставить текущее поведение: фиксированные 150 + 20% из констант в `useGameRun.js`, без передачи `basePoints`/`reservePercent` из GameRunView.

---

## Формулы (итог)

- **Базовых поинтов за забег:**  
  `base_points = min(energy_run_max_hours * 60 * energy_points_per_minute, floor(elapsed_minutes) * energy_points_per_minute)`
- **Всего поинтов (с запасом):**  
  `total_points = ceil(base_points * (1 + energy_points_reserve_percent / 100))`
- Примеры при `energy_points_per_minute=2`, `energy_points_reserve_percent=20`, `energy_run_max_hours=4`:
  - 1 ч → 120 базовых → 144 всего (или сколько вернёт ceil).
  - 1.5 ч → 180 базовых.
  - 4 ч и больше → 480 базовых (максимум).

---

## Порядок внедрения (когда будете делать правки)

1. RunnerConfig: поля + админка + миграция.
2. EnergyRunStartView: расчёт base_points и reserve_percent, добавление полей в ответ.
3. useGameRun.js: параметры в generateEnergyPoints и startRun, fallback на константы.
4. GameRunView.vue: чтение из ответа energy-run-start и передача в startGame → startRun.
5. При необходимости: сохранение base_points/reserve в профиле и валидация в complete/claim.

После выполнения плана настройка «1 минута = n поинтов» и «процент запаса» будет в админке RunnerConfig, а количество поинтов за энергозабег будет зависеть от времени с момента последнего старта (с лимитом 4 часа).
