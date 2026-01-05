# Инструкция по разработке буста "Рем. Комплект"

## Описание задачи

Создать новый буст "Рем. Комплект" по аналогии с бустом "Криокамера". 

**Функционал:**
- Криокамера предотвращает перегрев электростанции
- Рем. Комплект фиксирует параметр Power на уровне активации и не дает ему падать

**Логика работы Рем. Комплекта:**
1. При активации буста сохраняется текущий уровень Power в поле `repair_kit_power_level`
   - Пример: если Power был 77, то `repair_kit_power_level = 77`
2. При активном бусте Power **не уменьшается** при:
   - Обычных тапах (строка 371)
   - Перегреве (строка 319)
3. Power может быть **больше** зафиксированного уровня (например, после ремонта)
   - Если Power стал 100 после ремонта, то `repair_kit_power_level` обновляется на 100
   - После этого Power не будет падать ниже 100, пока буст активен
4. Power **не может быть меньше** зафиксированного уровня при активном бусте
   - Если по какой-то причине Power упал ниже `repair_kit_power_level`, он автоматически восстанавливается

**Места уменьшения Power:**
1. При перегреве (overheat) - `edit/core/views.py:319`
2. При обычном тапе - `edit/core/views.py:371`

## Структура проекта

- **Backend код (локально):** `/edit`
- **Backend код (на сервере):** папки `core/` и `tasks/` в корне проекта (без папки `edit`)
- **Frontend код:** `/src`
- **Тестовый сервер:** `/home/admsrv/tbtc_dev`
- **Продакшн сервер:** `/home/admsrv/tbtc`
- **Виртуальное окружение:** `.venv`

**Важно:** На сервере структура отличается от локальной - нет папки `edit`, файлы находятся напрямую в `core/` и `tasks/`.

## Шаги разработки

### 1. Backend: Добавление поля в модель UserProfile

**Файл:** `edit/core/models.py`

Добавить поле после строки 287 (после `premium_sub_expires`):

```python
repair_kit_expires = models.DateTimeField(null=True, blank=True)
```

**Расположение:** В секции `# ====== BOOSTERS ======` около строки 269-287

### 2. Backend: Добавление буста в модель Booster

**Файл:** `edit/tasks/models.py`

В классе `Booster`, в поле `BOOSTER_CHOICES` (строка 209-219), добавить:

```python
("repair_kit", "Рем. Комплект | фиксирует Power"),
```

### 3. Backend: Создание миграции

#### 3.1. Локально (на вашей машине)

**Команды:**
```bash
cd edit
source .venv/bin/activate  # или .venv\Scripts\activate на Windows
python manage.py makemigrations core
python manage.py makemigrations tasks
```

Проверить созданные миграции:
```bash
python manage.py showmigrations core
python manage.py showmigrations tasks
```

#### 3.2. На тестовом сервере

**Подключение:**
```bash
ssh projects-srv
cd tbtc_dev
```

**Активация виртуального окружения:**
```bash
# Если используется bash/zsh
source .venv/bin/activate

# Если используется fish shell
.venv/bin/activate.fish

# Или напрямую использовать python из venv
.venv/bin/python manage.py makemigrations core
.venv/bin/python manage.py makemigrations tasks
```

**Создание миграций:**
```bash
.venv/bin/python manage.py makemigrations core
.venv/bin/python manage.py makemigrations tasks
```

**Проверка миграций:**
```bash
.venv/bin/python manage.py showmigrations core
.venv/bin/python manage.py showmigrations tasks
```

**Проверка последних миграций (для определения номера новой):**
```bash
# Последняя миграция core
ls -t core/migrations/0*.py | head -1

# Последняя миграция tasks
ls -t tasks/migrations/0*.py | head -1
```

**Применение миграций:**
```bash
.venv/bin/python manage.py migrate
```

#### 3.3. На продакшн сервере

**Подключение:**
```bash
ssh projects-srv
cd tbtc
```

**Создание и применение миграций (аналогично тестовому серверу):**
```bash
.venv/bin/python manage.py makemigrations core
.venv/bin/python manage.py makemigrations tasks
.venv/bin/python manage.py showmigrations core
.venv/bin/python manage.py showmigrations tasks
.venv/bin/python manage.py migrate
```

### 4. Backend: Логика активации буста в services.py

**Файл:** `edit/tasks/services.py`

В функции `activate_booster()` (начинается со строки 84), добавить обработку после блока `premium_sub`:

```python
elif booster.slug == "repair_kit":
    discount = max(1 - day_count * 0.01, 0.7) if day_count >= 5 else 1
    return math.ceil(get_booster_price(user, booster, fbtc) * day_count * discount)
```

**Примечание:** Использовать ту же логику ценообразования, что и у криокамеры.

### 5. Backend: Обработка активации в ActivateBoosterFTBCView

**Файл:** `edit/tasks/views.py`

В классе `ActivateBoosterFTBCView`, метод `post()` (около строки 569-588), добавить после блока `cryo`:

```python
elif booster.slug == "repair_kit":
    now = timezone.now()
    repair_kit_expires = user_profile.repair_kit_expires
    is_active = repair_kit_expires and repair_kit_expires > now

    if not is_active:
        repair_kit_expires = now

    repair_kit_expires += timedelta(days=int(days))

    if repair_kit_expires > now + timedelta(days=31):
        return Response(
            {"status": "Booster cannot be activated for more than 31 days"},
            status=status.HTTP_400_BAD_REQUEST,
        )
        repair_kit_expires = now + timedelta(days=31)

    # Сохраняем текущий уровень power при активации
    UserProfile.objects.filter(id=user_profile.id).update(
        repair_kit_expires=repair_kit_expires,
        repair_kit_power_level=user_profile.power,  # Новое поле для хранения уровня
    )
```

**ВАЖНО:** Нужно добавить поле `repair_kit_power_level` в модель UserProfile для хранения уровня power на момент активации.

### 6. Backend: Обработка активации в ActivateBoosterView

**Файл:** `edit/tasks/views.py`

В классе `ActivateBoosterView`, метод `post()` (около строки 733), логика уже обрабатывается через `activate_booster()` из services.py, но нужно добавить обработку в `tgbot/views.py` для платежей через Telegram.

### 7. Backend: Обработка в Telegram боте

**Файл:** `edit/tgbot/views.py`

В функции `got_payment()` (около строки 249), добавить после блока `cryo`:

```python
elif booster.slug == "repair_kit":
    now = timezone.now()
    repair_kit_expires = user_profile.repair_kit_expires
    is_active = repair_kit_expires and repair_kit_expires > now

    if not is_active:
        repair_kit_expires = now

    repair_kit_expires += timedelta(days=int(days))

    if repair_kit_expires > now + timedelta(days=31):
        repair_kit_expires = now + timedelta(days=31)

    UserProfile.objects.filter(id=user_profile.id).update(
        repair_kit_expires=repair_kit_expires,
        repair_kit_power_level=user_profile.power,
    )
    action_logger.info(
        f"user {user_id} | bought booster {payload} | was {user_profile.repair_kit_expires} | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
    )
```

### 8. Backend: Защита от уменьшения Power при перегреве

**Файл:** `edit/core/views.py`

В классе `TapEnergyView`, метод `post()`, в блоке OVERHEAT (строка 310-341), изменить логику уменьшения power:

```python
# OVERHEAT
if user_profile.overheated_until:
    # Проверяем активен ли Рем. Комплект
    is_repair_kit_active = (
        user_profile.repair_kit_expires and 
        timezone.now() < user_profile.repair_kit_expires
    )
    
    if user_profile.tap_count_since_overheat >= (
        overheat_config.taps_before_power_reduction
    ):
        # Если Рем. Комплект активен, не уменьшаем power, но обновляем счетчик
        if not is_repair_kit_active:
            UserProfile.objects.filter(
                user_id=request.user_profile.user_id
            ).update(
                tap_count_since_overheat=F("tap_count_since_overheat") + 1,
                power=F("power") - overheat_config.power_reduction_percentage,
            )
        else:
            UserProfile.objects.filter(
                user_id=request.user_profile.user_id
            ).update(
                tap_count_since_overheat=F("tap_count_since_overheat") + 1,
            )
        UserProfile.objects.filter(
            user_id=request.user_profile.user_id, power__lt=0
        ).update(power=0)
    else:
        UserProfile.objects.filter(
            user_id=request.user_profile.user_id
        ).update(
            tap_count_since_overheat=F("tap_count_since_overheat") + 1,
        )
    user_profile.refresh_from_db()
    return Response(
        {
            "message": "Station is overheated. Please wait until it cools down.",
            "overheated_until": user_profile.overheated_until,
            "total_energy": user_profile.energy,
            "power": user_profile.power,
            "storage": user_profile.storage,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )
# END OVERHEAT
```

### 9. Backend: Защита от уменьшения Power при обычном тапе

**Файл:** `edit/core/views.py`

В том же методе `post()`, после блока OVERHEAT (около строки 371), изменить логику уменьшения power:

```python
# Проверяем активен ли Рем. Комплект
is_repair_kit_active = (
    user_profile.repair_kit_expires and 
    timezone.now() < user_profile.repair_kit_expires
)

# Вычисляем уменьшение power
final_power_minus = (
    tapped_kw / F("generation_rate") / 2 * user_profile.sbt_get_power()
)

# Обновляем данные пользователя
update_data = {
    "energy": F("energy") + tapped_kw,
    "tap_count": F("tap_count") + 1,
    "storage": F("storage") - tapped_kw,
    "overheat_energy_collected": F("overheat_energy_collected") + tapped_kw,
}

# Если Рем. Комплект активен, не уменьшаем power вообще
# Power может быть больше зафиксированного (если был ремонт), но не меньше
if is_repair_kit_active and user_profile.repair_kit_power_level:
    # Не уменьшаем power, но если он упал ниже зафиксированного - восстанавливаем
    update_data["power"] = Case(
        When(power__lt=user_profile.repair_kit_power_level, then=user_profile.repair_kit_power_level),
        default=F("power")
    )
else:
    update_data["power"] = F("power") - final_power_minus

UserProfile.objects.filter(user_id=request.user_profile.user_id).update(**update_data)
UserProfile.objects.filter(
    user_id=request.user_profile.user_id, power__lt=0
).update(power=0)
```

**Примечание:** Нужно добавить импорт `Case` и `When` из `django.db.models`. Проверить существующие импорты в начале файла (около строки 100) и добавить:

```python
from django.db.models import Case, F, When
```

Если `F` уже импортирован, просто добавить `Case, When` к существующему импорту.

**Логика работы:**
- При активном Рем. Комплекте power **не уменьшается** при тапах
- Если power стал меньше зафиксированного уровня (например, из-за бага или прямого изменения в БД), он восстанавливается до зафиксированного
- Если power больше зафиксированного (например, после ремонтa), он остается на этом уровне

### 10. Backend: Добавление поля repair_kit_power_level в модель

**Файл:** `edit/core/models.py`

Добавить поле после `repair_kit_expires`:

```python
repair_kit_power_level = models.DecimalField(
    max_digits=36, 
    decimal_places=16, 
    null=True, 
    blank=True,
    default=None
)
```

**Назначение поля:**
- Хранит уровень power на момент активации буста
- При активном бусте power не может быть меньше этого значения
- При ремонте станции (power становится 100) это поле обновляется на 100

### 11. Backend: Обновление repair_kit_power_level при ремонте станции

**Файл:** `edit/core/views.py`

В классе `RepairStationView`, метод `post()` (около строки 604-690), нужно:

1. **Добавить проверку активности буста в начале метода** (после строки 612, где получаем `user_profile`):

```python
# Проверяем активен ли Рем. Комплект
is_repair_kit_active = (
    user_profile.repair_kit_expires and 
    timezone.now() < user_profile.repair_kit_expires
)
```

2. **Обновить все три места, где устанавливается `power=100`:**

**Первое место (строка 633-636) - оплата из energy:**
```python
update_data = {
    "energy": F("energy") - repair_cost_kw,
    "power": 100,
}

# Если Рем. Комплект активен, обновляем зафиксированный уровень на 100
if is_repair_kit_active:
    update_data["repair_kit_power_level"] = 100

UserProfile.objects.filter(user_id=user_profile.user_id).update(**update_data)
```

**Второе место (строка 651-654) - оплата из kw_wallet:**
```python
update_data = {
    "kw_wallet": F("kw_wallet") - repair_cost_kw,
    "power": 100,
}

# Если Рем. Комплект активен, обновляем зафиксированный уровень на 100
if is_repair_kit_active:
    update_data["repair_kit_power_level"] = 100

UserProfile.objects.filter(user_id=user_profile.user_id).update(**update_data)
```

**Третье место (строка 669-672) - оплата из tbtc_wallet:**
```python
update_data = {
    "tbtc_wallet": F("tbtc_wallet") - repair_cost_tbtc,
    "power": 100,
}

# Если Рем. Комплект активен, обновляем зафиксированный уровень на 100
if is_repair_kit_active:
    update_data["repair_kit_power_level"] = 100

UserProfile.objects.filter(user_id=user_profile.user_id).update(**update_data)
```

**Логика работы:**
- При ремонте станции power всегда становится 100
- Если Рем. Комплект активен, то `repair_kit_power_level` также обновляется на 100
- После ремонта power не будет падать ниже 100, пока буст активен

### 12. Backend: Обновление сериализатора

**Файл:** `edit/core/serializers.py`

Сериализатор `UserProfileSerializer` использует `exclude` для исключения некоторых полей, поэтому новые поля `repair_kit_expires` и `repair_kit_power_level` автоматически будут включены. Никаких изменений не требуется.

### 13. Frontend: Добавление буста в компонент Boost.vue

**Файл:** `src/components/Boost.vue`

#### 13.1. Добавить computed для проверки активности

После строки 42 (после `managerIsForever`), добавить:

```javascript
const repairKitIsForever = computed(() => {
  const date = new Date(app?.user?.repair_kit_expires)
  return date.getFullYear() === 2100
})
const repairKitBlocked = computed(() => {
  const repairKitBlock = app.timed_nfts.find(el => el.name == 'Repair Kit')
  return new Date(repairKitBlock?.block_until) > new Date()
})
```

#### 13.2. Добавить в foreverBoosts

После строки 87, добавить:

```javascript
'repair_kit': {
  name: 'Repair Kit',
  price: 89,
  old_price: 99,
  link: 'https://getgems.io/tbtc?filter=%7B%22attributes%22%3A%7B%7D%2C%22q%22%3A%22Repair%20Kit%22%7D#items'
}
```

#### 13.3. Добавить обработку в parseBoosterInfo

После блока `asic_manager` (около строки 349), добавить:

```javascript
if (booster?.slug == 'repair_kit') {
  const repairKitBlock = app.timed_nfts.find(el => el.name == 'Repair Kit')
  if (new Date(repairKitBlock?.block_until) > new Date()) {
    status = `<span class="!text-[#FCD909]">${t('common.connect')}</span>`
    additional = `<img src="${timeImg}" style="width: 12px; height: 13px;"/> ${getTimeRemaining(repairKitBlock?.block_until).time}`
  } else if (app?.user?.repair_kit_expires) {
    const daysDiff = Math.max(0, Math.round((new Date(app?.user?.repair_kit_expires) - new Date()) / (1000 * 60 * 60 * 24)))
    if (daysDiff > 0) {
      status = booster?.[`status2${loc_add.value}`]
      additional = repairKitIsForever.value
        ? `<img src="${mintableImg}" style="width: 12px; height: 13px;"/> ${t('common.forever')}`
        : booster?.[`additional_info2${loc_add.value}`]?.replace('{N}', t('common.days', { n: +daysDiff }))
    } else {
      status = booster?.[`status1${loc_add.value}`]
      additional = paymentRadio.value == 'ton' ? t('common.not_bought') : booster?.[`additional_info1${loc_add.value}`]
    }
  } else {
    status = booster?.[`status1${loc_add.value}`]
    additional = paymentRadio.value == 'ton' ? t('common.not_bought') : booster?.[`additional_info1${loc_add.value}`]
  }
}
```

#### 13.4. Добавить в getTotalStarsPrice

После блока `premium_sub` (около строки 436), добавить:

```javascript
else if (item?.slug == 'repair_kit') {
  price = `price${app?.user?.station_type ? (Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3) >= 7 ? 7 : Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3)) : 1}${paymentRadio.value == 'fbtc' ? "_fbtc" : ""}`
  sum = item?.[price] * boosters_count.value[item?.slug]
  if (((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) && paymentRadio.value == 'stars') {
    sum = Math.floor(sum * (100 - ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 5 : ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 10 : 0)) / 100)
  }
  if (boosters_count.value[item?.slug] >= 5) {
    sum *= (100 - Math.min(boosters_count.value[item?.slug], 30)) / 100
  }
}
```

#### 13.5. Добавить в isActiveBooster

После строки 550, добавить:

```javascript
if (
  booster?.slug == 'repair_kit' &&
  app?.user?.repair_kit_expires &&
  (new Date(app?.user?.repair_kit_expires) - new Date()) / (1000 * 60 * 60 * 24) >= 0
)
  return true
```

#### 13.6. Добавить в boosters_count

После строки 564, добавить:

```javascript
repair_kit: 1,
```

#### 13.7. Добавить в filteredBoosters

В computed `filteredBoosters` (строка 567-572), добавить `'repair_kit'` в соответствующие массивы `inclSlug` в зависимости от `isMiners` и `paymentRadio`.

#### 13.8. Добавить в increment

В функции `increment()` (строка 594-620), добавить в `expiresMap`:

```javascript
repair_kit: 'repair_kit_expires',
```

### 14. Frontend: Добавление локализации

**Файлы:** 
- `src/locales/ru.json`
- `src/locales/en.json`
- `src/locales/uk.json`

Добавить переводы для буста "Рем. Комплект" (по аналогии с другими бустами).

### 15. Админка: Настройка буста

1. Войти в админку Django: `/admin/tasks/booster/add/`
2. Создать новый буст со следующими параметрами:
   - **Slug:** `repair_kit`
   - **Title:** "Рем. Комплект" (и соответствующие переводы)
   - **Description:** Описание функционала
   - **Prices:** Установить цены для разных уровней станций (price1-price7, price1_fbtc-price7_fbtc)
   - **Status1/Status2:** Статусы для неактивного/активного состояния
   - **Additional info1/Additional info2:** Дополнительная информация

### 16. Передача файлов на серверы

#### 16.1. Передача файлов на тестовый сервер

**Из локальной папки `edit/` на тестовый сервер:**

```bash
# Передача файлов core
scp edit/core/models.py projects-srv:/home/admsrv/tbtc_dev/core/models.py
scp edit/core/views.py projects-srv:/home/admsrv/tbtc_dev/core/views.py
scp edit/core/serializers.py projects-srv:/home/admsrv/tbtc_dev/core/serializers.py

# Передача файлов tasks
scp edit/tasks/models.py projects-srv:/home/admsrv/tbtc_dev/tasks/models.py
scp edit/tasks/services.py projects-srv:/home/admsrv/tbtc_dev/tasks/services.py
scp edit/tasks/views.py projects-srv:/home/admsrv/tbtc_dev/tasks/views.py

# Передача файлов tgbot
scp edit/tgbot/views.py projects-srv:/home/admsrv/tbtc_dev/tgbot/views.py

# Передача миграций (если созданы локально)
scp edit/core/migrations/0XXX_*.py projects-srv:/home/admsrv/tbtc_dev/core/migrations/
scp edit/tasks/migrations/0XXX_*.py projects-srv:/home/admsrv/tbtc_dev/tasks/migrations/
```

**Или передать всю папку core/tasks целиком:**
```bash
# Передача папки core (исключая __pycache__)
rsync -av --exclude='__pycache__' --exclude='*.pyc' edit/core/ projects-srv:/home/admsrv/tbtc_dev/core/

# Передача папки tasks (исключая __pycache__)
rsync -av --exclude='__pycache__' --exclude='*.pyc' edit/tasks/ projects-srv:/home/admsrv/tbtc_dev/tasks/

# Передача папки tgbot
rsync -av --exclude='__pycache__' --exclude='*.pyc' edit/tgbot/ projects-srv:/home/admsrv/tbtc_dev/tgbot/
```

#### 16.2. Передача файлов на продакшн сервер

**Аналогично тестовому, но путь `/home/admsrv/tbtc`:**

```bash
# Передача файлов core
scp edit/core/models.py projects-srv:/home/admsrv/tbtc/core/models.py
scp edit/core/views.py projects-srv:/home/admsrv/tbtc/core/views.py
scp edit/core/serializers.py projects-srv:/home/admsrv/tbtc/core/serializers.py

# Передача файлов tasks
scp edit/tasks/models.py projects-srv:/home/admsrv/tbtc/tasks/models.py
scp edit/tasks/services.py projects-srv:/home/admsrv/tbtc/tasks/services.py
scp edit/tasks/views.py projects-srv:/home/admsrv/tbtc/tasks/views.py

# Передача файлов tgbot
scp edit/tgbot/views.py projects-srv:/home/admsrv/tbtc/tgbot/views.py

# Передача миграций
scp edit/core/migrations/0XXX_*.py projects-srv:/home/admsrv/tbtc/core/migrations/
scp edit/tasks/migrations/0XXX_*.py projects-srv:/home/admsrv/tbtc/tasks/migrations/
```

**Или через rsync:**
```bash
rsync -av --exclude='__pycache__' --exclude='*.pyc' edit/core/ projects-srv:/home/admsrv/tbtc/core/
rsync -av --exclude='__pycache__' --exclude='*.pyc' edit/tasks/ projects-srv:/home/admsrv/tbtc/tasks/
rsync -av --exclude='__pycache__' --exclude='*.pyc' edit/tgbot/ projects-srv:/home/admsrv/tbtc/tgbot/
```

#### 16.3. Передача frontend файлов

**На тестовый сервер:**
```bash
scp src/components/Boost.vue projects-srv:/home/admsrv/tbtc_dev/frontend/src/components/Boost.vue
scp src/locales/ru.json projects-srv:/home/admsrv/tbtc_dev/frontend/src/locales/ru.json
scp src/locales/en.json projects-srv:/home/admsrv/tbtc_dev/frontend/src/locales/en.json
scp src/locales/uk.json projects-srv:/home/admsrv/tbtc_dev/frontend/src/locales/uk.json
```

**На продакшн сервер:**
```bash
scp src/components/Boost.vue projects-srv:/home/admsrv/tbtc/frontend/src/components/Boost.vue
scp src/locales/ru.json projects-srv:/home/admsrv/tbtc/frontend/src/locales/ru.json
scp src/locales/en.json projects-srv:/home/admsrv/tbtc/frontend/src/locales/en.json
scp src/locales/uk.json projects-srv:/home/admsrv/tbtc/frontend/src/locales/uk.json
```

**Примечание:** Путь к frontend может отличаться. Проверьте структуру на сервере:
```bash
ssh projects-srv "cd tbtc_dev && find . -name 'Boost.vue' -type f"
```

### 17. Тестирование на тестовом сервере

1. **Подключиться к тестовому серверу:**
   ```bash
   ssh projects-srv
   cd tbtc_dev
   ```

2. **Применить миграции:**
   ```bash
   .venv/bin/python manage.py migrate
   ```

3. **Проверить статус миграций:**
   ```bash
   .venv/bin/python manage.py showmigrations core
   .venv/bin/python manage.py showmigrations tasks
   ```

4. **Перезапустить сервисы (если нужно):**
   ```bash
   # Проверить какие сервисы используются
   ls -la restart.sh
   # Или
   ./restart.sh
   ```

5. **Создать буст в админке:**
   - Открыть админку: `http://your-test-server/admin/tasks/booster/add/`
   - Создать новый буст с slug `repair_kit`

6. **Протестировать:**
   - Активацию буста
   - Проверку фиксации power при тапах
   - Проверку фиксации power при перегреве
   - Проверку обновления `repair_kit_power_level` при ремонте
   - Отображение в интерфейсе

### 18. Деплой на продакшн

После успешного тестирования на тестовом сервере:

1. **Передать файлы на продакшн сервер** (см. раздел 16.2)

2. **Подключиться к продакшн серверу:**
   ```bash
   ssh projects-srv
   cd tbtc
   ```

3. **Создать миграции (если еще не созданы):**
   ```bash
   .venv/bin/python manage.py makemigrations core
   .venv/bin/python manage.py makemigrations tasks
   ```

4. **Проверить созданные миграции:**
   ```bash
   .venv/bin/python manage.py showmigrations core | grep "\[ \]"
   .venv/bin/python manage.py showmigrations tasks | grep "\[ \]"
   ```

5. **Применить миграции:**
   ```bash
   .venv/bin/python manage.py migrate
   ```

6. **Проверить статус миграций:**
   ```bash
   .venv/bin/python manage.py showmigrations core | tail -5
   .venv/bin/python manage.py showmigrations tasks | tail -5
   ```

7. **Перезапустить сервисы:**
   ```bash
   ./restart.sh
   # Или вручную перезапустить gunicorn/uwsgi/nginx
   ```

8. **Создать буст в админке продакшн:**
   - Открыть админку: `http://your-production-server/admin/tasks/booster/add/`
   - Создать новый буст с slug `repair_kit`

9. **Проверить работу:**
   - Активацию буста
   - Проверку фиксации power при тапах
   - Проверку фиксации power при перегреве
   - Проверку обновления `repair_kit_power_level` при ремонте
   - Отображение в интерфейсе

**Важно:** Перед деплоем на продакшн обязательно протестировать на тестовом сервере!

## Команды для быстрого доступа

### Подключение к серверам

**Тестовый сервер:**
```bash
ssh projects-srv "cd tbtc_dev && bash"
```

**Продакшн сервер:**
```bash
ssh projects-srv "cd tbtc && bash"
```

### Работа с миграциями

**Создание миграций (локально):**
```bash
cd edit
source .venv/bin/activate
python manage.py makemigrations core
python manage.py makemigrations tasks
```

**Создание миграций (на сервере):**
```bash
# Тестовый
ssh projects-srv "cd tbtc_dev && .venv/bin/python manage.py makemigrations core && .venv/bin/python manage.py makemigrations tasks"

# Продакшн
ssh projects-srv "cd tbtc && .venv/bin/python manage.py makemigrations core && .venv/bin/python manage.py makemigrations tasks"
```

**Применение миграций (на сервере):**
```bash
# Тестовый
ssh projects-srv "cd tbtc_dev && .venv/bin/python manage.py migrate"

# Продакшн
ssh projects-srv "cd tbtc && .venv/bin/python manage.py migrate"
```

**Проверка статуса миграций:**
```bash
# Тестовый
ssh projects-srv "cd tbtc_dev && .venv/bin/python manage.py showmigrations core && .venv/bin/python manage.py showmigrations tasks"

# Продакшн
ssh projects-srv "cd tbtc && .venv/bin/python manage.py showmigrations core && .venv/bin/python manage.py showmigrations tasks"
```

**Проверка последних миграций (для определения номера):**
```bash
# Тестовый - последняя миграция core
ssh projects-srv "cd tbtc_dev && ls -t core/migrations/0*.py | head -1"

# Тестовый - последняя миграция tasks
ssh projects-srv "cd tbtc_dev && ls -t tasks/migrations/0*.py | head -1"

# Продакшн - последняя миграция core
ssh projects-srv "cd tbtc && ls -t core/migrations/0*.py | head -1"

# Продакшн - последняя миграция tasks
ssh projects-srv "cd tbtc && ls -t tasks/migrations/0*.py | head -1"
```

### Передача файлов одной командой

**Backend файлы на тестовый:**
```bash
scp edit/core/models.py edit/core/views.py edit/core/serializers.py projects-srv:/home/admsrv/tbtc_dev/core/ && \
scp edit/tasks/models.py edit/tasks/services.py edit/tasks/views.py projects-srv:/home/admsrv/tbtc_dev/tasks/ && \
scp edit/tgbot/views.py projects-srv:/home/admsrv/tbtc_dev/tgbot/
```

**Backend файлы на продакшн:**
```bash
scp edit/core/models.py edit/core/views.py edit/core/serializers.py projects-srv:/home/admsrv/tbtc/core/ && \
scp edit/tasks/models.py edit/tasks/services.py edit/tasks/views.py projects-srv:/home/admsrv/tbtc/tasks/ && \
scp edit/tgbot/views.py projects-srv:/home/admsrv/tbtc/tgbot/
```

## Важные замечания

1. **Поле repair_kit_power_level** - критически важно для фиксации уровня power. Без него буст не будет работать корректно.

2. **Проверка активности** - нужно проверять `repair_kit_expires` во всех местах, где уменьшается power.

3. **Совместимость с другими бустами** - Рем. Комплект должен работать независимо от других бустов (криокамера, джарвис и т.д.).

4. **Логика фиксации** - power фиксируется на уровне активации и не должен падать ниже этого уровня. Если пользователь отремонтирует станцию (power станет 100), то `repair_kit_power_level` обновляется на 100, и теперь power не должен падать ниже 100.

5. **Ограничение 31 день** - как и у других бустов, максимальный срок активации 31 день.

6. **Структура на сервере** - на сервере нет папки `edit`, файлы находятся в `core/` и `tasks/` напрямую. Учитывайте это при передаче файлов.

7. **Виртуальное окружение** - на сервере используйте `.venv/bin/python` вместо `python` для выполнения команд Django.

## Чеклист перед деплоем

- [ ] Добавлено поле `repair_kit_expires` в UserProfile
- [ ] Добавлено поле `repair_kit_power_level` в UserProfile
- [ ] Созданы и применены миграции
- [ ] Добавлен буст в модель Booster
- [ ] Реализована логика активации в services.py
- [ ] Реализована обработка в ActivateBoosterFTBCView
- [ ] Реализована обработка в ActivateBoosterView
- [ ] Реализована обработка в tgbot/views.py
- [ ] Добавлена защита от уменьшения power при перегреве
- [ ] Добавлена защита от уменьшения power при обычном тапе
- [ ] Обновлена логика ремонта станции (обновление repair_kit_power_level при ремонте)
- [ ] Обновлен сериализатор
- [ ] Добавлен буст в Boost.vue (все необходимые места)
- [ ] Добавлена локализация
- [ ] Создан буст в админке тестового сервера
- [ ] Протестировано на тестовом сервере
- [ ] Деплой на продакшн выполнен
- [ ] Создан буст в админке продакшн

