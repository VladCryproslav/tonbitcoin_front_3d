# Премиальные электростанции: анализ и план обновления (Orbital → Thermonuclear, Singularity Reactor)

## 1. Текущее состояние

### 1.1 Две премиальные станции в приложении

| В игре (подключение) | Реальное название NFT / отображение |
|----------------------|-------------------------------------|
| **Hydroelectric**    | Nuclear power plant (атомная)       |
| **Orbital**          | Dyson Sphere (сфера Дайсона)        |

### 1.2 Текущие характеристики (бэкенд)

**Hydro (Nuclear):**
- Целевое/ожидаемое старое значение: storage **1000**, generation **250**, engineer 30.
- В коде сейчас: `models.py` — `calc_storage_limit()` → 1000, `calc_generation_rate()` → **278** (должно быть 250?); при подключении (`edit/t.py`) — `generation_rate=278`, `engineer_level=30`. Если эталон — 250, в коде нужно заменить 278 → 250.

**Orbital (Dyson Sphere):**
- `models.py`:
  - `calc_storage_limit()` → **2320**
  - `calc_generation_rate()`:
    - `orbital_first_owner` + `orbital_is_blue` → **580**
    - `orbital_first_owner` + не blue → **290**
    - не first owner → **580**
- При подключении (`edit/t.py`): `engineer_level=45`, `storage_limit=2320`, `generation_rate=290` (first owner) или **580** (не first owner)
- При переключении на орбитальную (`SwitchOrbitalStationView` в `views.py` / `edit/core/views.py`): те же 2320, 290/580, engineer 45

### 1.3 Где завязана логика

- **Модели:** `UserProfile`: `has_hydro_station`, `has_orbital_station`, `orbital_first_owner`, `orbital_is_blue`, `orbital_force_basic`, `current_station_nft`, поля `hydro_prev_*`.
- **Расчёт лимитов/генерации:** `UserProfile.calc_storage_limit()`, `UserProfile.calc_generation_rate()` в `models.py` (и дубликат в `edit/core/models.py`).
- **Подключение/отключение по NFT:** `edit/t.py` (и `edit/t copy.py`): парсинг NFT по имени `"Hydroelectric Power Station"` и `"Orbital Power Station"`; гидро — через `LinkedUserNFT`, орбитальная — через модель `OrbitalOwner`.
- **Переключение орбитальная ↔ базовая:** `SwitchOrbitalStationView`, `SwitchOrbitalView` (переключение blue/yellow) в `views.py` и `edit/core/views.py`.
- **Инженеры:** наградой инженеров нельзя пользоваться при активной орбитальной (Special) или гидро: `edit/tasks/views.py`, `edit/tasks/services.py`.
- **Фронт:** `EnergizerView.vue`, `StationSlider.vue`, `MarketView.vue` — проверки `has_orbital_station`, `has_hydro_station`; отображение типа станции (Dyson Sphere / Nuclear power plant); для орбитальной используется фон/картинка `Orbital Power Plant.webp`. В `data.js` уже есть карточка **Singularity Reactor** (описание/benefits), но бэкенд под неё не реализован.

---

## 2. Планируемые изменения (без правок в коде)

### 2.1 Переименование и флаг «старый владелец»

- **Orbital** в игре переименовать в **Thermonuclear power plant** (термоядерная), при этом NFT по-прежнему «Orbital Power Station».
- Ввести в профиль пользователя флаг по аналогии с `orbital_first_owner`, например: **`prem_power_plant_old_owner`** (или `premium_power_plant_old_owner`).
  - **True** — использовать **старые** характеристики премиальных станций (текущие значения).
  - **False** — использовать **новые** характеристики (см. ниже).

### 2.2 Новые характеристики (при `prem_power_plant_old_owner = False`)

**Hydroelectric (Nuclear):**
- storage: **1000** (без изменений)
- generation: **250** (сейчас 278)
- engineer: **25** уровень (сейчас при подключении 30)

**Orbital (Thermonuclear / Dyson Sphere):**
- storage: **1840** (сейчас 2320)
- generation: **460** (сейчас 290/580 в зависимости от first owner и blue)
- engineer: **35** уровень (сейчас 45)

Старые значения (при `prem_power_plant_old_owner = True`) остаются как сейчас.

### 2.3 Новая премиальная станция: Singularity Reactor

- Добавить по аналогии с Hydroelectric:
  - Парсинг NFT **по имени новой электростанции** (как у гидры, но имя — под новую станцию, например `"Singularity Reactor"` или как будет в метаданных NFT).
  - Модель/привязка владельца: по типу гидры (через `LinkedUserNFT` или отдельная модель, например **Has singularity reactor** / `has_singularity_station` в профиле).

**Характеристики Singularity Reactor:**
- storage: **3200**
- generation: **800**
- engineer: **45** уровень

На фронте уже есть карточка Singularity в `src/services/data.js` (тип `'Singularity Reactor'`, `singularity_power_plant_modal`); в документе указаны целевые цифры storage 3200, generation 800, engineer 45 (в data.js сейчас storage 2690 — привести к 3200 при реализации).

### 2.4 Отображение на фронте (Singularity Reactor)

- Показывать Singularity Reactor с **фоном космоса**, как у орбитальной (например, тот же или аналогичный фон, что и для Orbital Power Plant).
- Логика отображения типа станции и фона — по аналогии с орбитальной (проверки `has_orbital_station` / тип «Dyson Sphere»), добавить ветку для `has_singularity_station` и соответствующий тип/название станции.

---

## 3. Сводная таблица целевых характеристик

| Станция            | Старая (old owner) | Новая (не old owner) | Примечание                    |
|-------------------|--------------------|----------------------|-------------------------------|
| **Hydro**         | storage 1000, gen **250**, eng 30  | storage 1000, gen **250**, eng **25**  | Остаётся Nuclear в UI; в коде сейчас gen=278 — привести к 250 при необходимости |
| **Orbital**       | storage 2320, gen 290/580, eng 45 | storage **1840**, gen **460**, eng **35** | В игре — Thermonuclear       |
| **Singularity**   | —                  | storage **3200**, gen **800**, eng **45** | Новая станция, парс по имени NFT; в игре = **Dyson Sphere** (station_type) |

---

## 4. Места в коде для последующих правок (напоминание)

- **Флаг:** `UserProfile` — новое поле (например `prem_power_plant_old_owner`), миграция; при выдаче NFT «старым» владельцам выставлять `True`, новым — `False`.
- **Расчёт:** `calc_storage_limit()`, `calc_generation_rate()` — ветки для hydro/orbital с учётом флага; для Singularity — новая ветка и при необходимости отдельный уровень инженера при подключении.
- **Подключение/откат:** `edit/t.py`: имена NFT `"Hydroelectric Power Station"`, `"Orbital Power Station"`; добавить парсинг имени для Singularity и обновить логику присвоения `has_singularity_station` и параметров (storage 3200, generation 800, engineer 45). При отключении — откат по аналогии с hydro/orbital.
- **Switch-views:** при переключении орбитальной станции использовать новые лимиты/генерацию/уровень инженера, если `prem_power_plant_old_owner = False`.
- **Инженеры (tasks):** при необходимости учесть активную Singularity так же, как hydro/orbital (запрет на награду инженеров при активной премиальной).
- **Фронт:** `premium_station_type` / отображение типа станции — добавить Singularity; маппинг «Orbital Power Plant» → «Thermonuclear power plant»; фон космоса для Singularity по аналогии с Orbital; обновить локали и benefits под новые цифры (в т.ч. orbital 1840/460/35, hydro 250/25, singularity 3200/800/45).

**Реализация выполнена.** Singularity Reactor в игре привязан к типу станции **Dyson Sphere** (station_type, маппинг на фронте, отображение с космическим фоном).
