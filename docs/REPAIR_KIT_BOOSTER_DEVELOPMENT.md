# Инструкция по разработке буста "Рем. Комплект"

## Описание задачи

Создать новый буст "Рем. Комплект" по аналогии с бустом "Криокамера". 

**Функционал:**
- Криокамера предотвращает перегрев электростанции
- Рем. Комплект фиксирует параметр Power на уровне активации и не дает ему падать

**Важно:** Все настройки буста (цены, тексты, описания) настраиваются через админку Django. В коде не должно быть захардкоженных значений - все берется из модели `Booster` через API.

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

### 12. Backend: Добавление проверки NFT для вечного буста

**Файл:** `edit/t.py`

В функции `main_boosters()` (около строки 810), нужно добавить проверку NFT "Repair Kit":

#### 12.1. Добавить в список проверяемых NFT

В строке 892, где проверяется список NFT, добавить "Repair Kit":

```python
if name in ["Jarvis Bot", "Cryochamber", "ASIC Manager", "Magnetic ring", "Repair Kit"]:
```

#### 12.2. Добавить словарь для владельцев

После строки 876 (где создаются словари), добавить:

```python
repair_kit_owners = dict()
```

#### 12.3. Добавить проверку NFT Repair Kit

После блока проверки "Magnetic ring" (около строки 965), добавить:

```python
elif name == "Repair Kit":
    station_level = user.get_station_level() + 1
    good = False
    # Логика классов такая же как у Jarvis Bot
    if full_name == "Repair Kit (4 class)" and 1 <= station_level <= 3:
        good = True
    elif full_name == "Repair Kit (3 class)" and 4 <= station_level <= 5:
        good = True
    elif full_name == "Repair Kit (2 class)" and 6 <= station_level <= 7:
        good = True
    elif full_name == "Repair Kit (1 class)" and 8 <= station_level <= 9:
        good = True
    if good:
        repair_kit_owners[user.user_id] = True
```

#### 12.4. Добавить обновление repair_kit_expires

После блока обновления `magnit_expires` (около строки 1019-1022), добавить:

```python
UserProfile.objects.filter(
    repair_kit_expires__year=2100,
).exclude(user_id__in=list(repair_kit_owners.keys())).update(
    repair_kit_expires=None,
)
UserProfile.objects.filter(
    user_id__in=list(repair_kit_owners.keys())
).exclude(repair_kit_expires__year=2100).update(
    repair_kit_expires=infinite_date,
)
```

**Логика работы:**
- Функция `main_boosters()` запускается периодически (через celery или cron)
- Проверяет все NFT на кошельках пользователей из официальных коллекций
- Если найден NFT "Repair Kit" нужного класса для уровня станции пользователя - устанавливает `repair_kit_expires` в 2100-01-01 (вечный буст)
- Если NFT не найден, но `repair_kit_expires` был в 2100 году - сбрасывает в None
- Проверка классов NFT Repair Kit:
  - **4 class:** для уровней станции 1-3 (Boiler house, Coal power plant, Thermal power plant)
  - **3 class:** для уровней станции 4-5 (Geothermal power plant, Nuclear power plant)
  - **2 class:** для уровней станции 6-7 (Thermonuclear power plant, Dyson Sphere)
  - **1 class:** для уровней станции 8-9 (Neutron star, Antimatter)

**Важно:** 
- Функция использует `LinkedUserNFT` для связи NFT с пользователем
- Проверяет `TimedUserNFT` для блокировки NFT после подключения нового кошелька
- Если NFT заблокирован (`block_until > now`), он не учитывается при проверке

**Классы NFT Repair Kit (по аналогии с Jarvis Bot):**
- **4 class:** для уровней станции 1-3
- **3 class:** для уровней станции 4-5
- **2 class:** для уровней станции 6-7
- **1 class:** для уровней станции 8-9

### 13. Backend: Обновление сериализатора

**Файл:** `edit/core/serializers.py`

Сериализатор `UserProfileSerializer` использует `exclude` для исключения некоторых полей, поэтому новые поля `repair_kit_expires` и `repair_kit_power_level` автоматически будут включены. Никаких изменений не требуется.

### 14. Frontend: Добавление буста в компонент Boost.vue

**Файл:** `src/components/Boost.vue`

#### 14.1. Добавить computed для проверки активности

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

**Примечание:** 
- `repairKitIsForever` проверяет, установлен ли `repair_kit_expires` на год 2100 (вечный буст через NFT)
- `repairKitBlocked` проверяет, заблокирован ли NFT на определенное время (через TimedUserNFT)

#### 14.2. Добавить в foreverBoosts

После строки 87, добавить:

```javascript
'repair_kit': {
  name: 'Repair Kit',
  price: 89,  // Пример значения, можно изменить
  old_price: 99,  // Пример значения, можно изменить
  link: 'https://getgems.io/tbtc?filter=%7B%22attributes%22%3A%7B%7D%2C%22q%22%3A%22Repair%20Kit%22%7D#items'
}
```

**Примечание:** 
- `name` должно совпадать с именем NFT в метаданных (без класса, например "Repair Kit")
- `link` - ссылка на GetGems для покупки NFT
- `price` и `old_price` - это примеры значений для вечного буста через TON (используется только для отображения в интерфейсе при выборе paymentRadio == 'ton')
- **Важно:** Эти значения используются только для вечных NFT бустов через TON. Для временных бустов (Stars/fBTC) все цены берутся из модели `Booster` через API

#### 14.3. Добавить обработку в parseBoosterInfo

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

**Логика работы:**
- Сначала проверяется, заблокирован ли NFT (TimedUserNFT)
- Затем проверяется, активен ли буст (`repair_kit_expires`)
- Если `repairKitIsForever` = true, показывается иконка "forever" вместо количества дней
- Если буст не активен, показывается статус "не куплен"

#### 14.4. Добавить в getTotalStarsPrice

После блока `premium_sub` (около строки 436), добавить:

```javascript
else if (item?.slug == 'repair_kit') {
  // Используем ту же логику градации что и для jarvis/cryo/electrics/premium_sub
  // Цена зависит от уровня станции через gen_config
  price = `price${app?.user?.station_type ? (Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3) >= 7 ? 7 : Math.ceil(app.gen_config.find((el) => el?.station_type == app?.user?.station_type)?.id / 3)) : 1}${paymentRadio.value == 'fbtc' ? "_fbtc" : ""}`
  sum = item?.[price] * boosters_count.value[item?.slug]
  // Применяем скидку SBT/Premium для Stars
  if (((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) && paymentRadio.value == 'stars') {
    sum = Math.floor(sum * (100 - ((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) ? 5 : ((app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft) || premiumActive.value) ? 10 : 0)) / 100)
  }
  // Применяем скидку за количество (от 5 дней)
  if (boosters_count.value[item?.slug] >= 5) {
    sum *= (100 - Math.min(boosters_count.value[item?.slug], 30)) / 100
  }
}
```

**Логика градации:**
- Используется `gen_config` для определения уровня станции
- `id` из `gen_config` делится на 3 и округляется вверх
- Если результат >= 7, используется price7 (максимум)
- Иначе используется price{результат}
- Поддерживаются price1-price10 для Stars и price1_fbtc-price10_fbtc для fBTC

#### 14.5. Добавить в isActiveBooster

После строки 550, добавить:

```javascript
if (
  booster?.slug == 'repair_kit' &&
  app?.user?.repair_kit_expires &&
  (new Date(app?.user?.repair_kit_expires) - new Date()) / (1000 * 60 * 60 * 24) >= 0
)
  return true
```

#### 14.6. Добавить в boosters_count

После строки 564, добавить:

```javascript
repair_kit: 1,
```

#### 14.7. Добавить в filteredBoosters

В computed `filteredBoosters` (строка 567-572), добавить `'repair_kit'` в соответствующие массивы `inclSlug` в зависимости от `isMiners` и `paymentRadio`.

**Для Energizers (isMiners = false):**
```javascript
: paymentRadio.value == 'ton' ? ['jarvis', 'cryo'] : ['azot', 'jarvis', 'cryo', 'autostart', 'electrics', 'premium_sub', 'repair_kit']
```

**Для Miners (isMiners = true):**
```javascript
: paymentRadio.value == 'ton' ? ['magnit', 'asic_manager'] : ['powerbank', 'magnit', 'asic_manager']
```

**Примечание:** Рем. Комплект доступен только для Energizers (как и jarvis, cryo), не для Miners.

#### 14.8. Добавить в increment

В функции `increment()` (строка 594-620), добавить в `expiresMap`:

```javascript
repair_kit: 'repair_kit_expires',
```

#### 14.9. Добавить в отображение зачеркнутой цены (старая цена без скидки)

В шаблоне, где отображается зачеркнутая цена (около строки 870 и 915), нужно добавить `repair_kit` в условие:

**Первое место (около строки 870):**
```javascript
<span v-if="item?.slug == 'jarvis' || item?.slug == 'cryo' || item?.slug == 'repair_kit'"
  class="text-[8px] text-white font-bold line-through decoration-red-400 decoration-[2px]">{{
    Math.ceil(
      item?.[
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
      ] * boosters_count?.[item?.slug],
    )
  }}</span>
```

**Второе место (около строки 915):**
```javascript
<span v-if="item?.slug == 'jarvis' || item?.slug == 'cryo' || item?.slug == 'repair_kit'"
  class="text-[8px] text-white font-bold line-through decoration-red-400 decoration-[2px]">{{
    Math.ceil(
      item?.[
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
      ] * boosters_count?.[item?.slug],
    )
  }}</span>
```

**Примечание:** Это нужно для правильного отображения старой цены (без скидки) при наличии скидки SBT/Premium или скидки за количество дней.

#### 14.10. Добавить в условие для отображения скидки SBT/Premium

#### 14.11. Добавить проверку вечного буста в условия кнопки

В шаблоне, где проверяется условие для кнопки (около строки 782-786), добавить проверку `repairKitIsForever`:

```javascript
if ((item?.slug == 'cryo' && cryoIsForever && !cryoBlocked) ||
  (item?.slug == 'jarvis' && jarvisIsForever && !jarvisBlocked) ||
  (item?.slug == 'magnit' && magnitIsForever && !magnitBlocked) ||
  (item?.slug == 'asic_manager' && managerIsForever && !managerBlocked) ||
  (item?.slug == 'repair_kit' && repairKitIsForever && !repairKitBlocked)) {
  return;
}
```

#### 14.12. Добавить проверку блокировки NFT в условия кнопки

В том же месте (около строки 788-791), добавить проверку `repairKitBlocked`:

```javascript
else if ((item?.slug == 'cryo' && cryoBlocked) ||
  (item?.slug == 'jarvis' && jarvisBlocked) ||
  (item?.slug == 'magnit' && magnitBlocked) ||
  (item?.slug == 'asic_manager' && managerBlocked) ||
  (item?.slug == 'repair_kit' && repairKitBlocked)) {
  // Логика ускорения разблокировки NFT
  const res = await host.post('timed-nft-stars/', {
    timed_nft_id: app.timed_nfts.find(el => el.name == foreverBoosts?.[item?.slug]?.name)?.id,
  })
  // ... остальная логика
}
```

#### 14.13. Добавить в классы кнопки

В шаблоне, где определяются классы кнопки (около строки 775-780), добавить:

```javascript
:class="{
  speedup: (item?.slug == 'jarvis' && jarvisBlocked) || 
           (item?.slug == 'cryo' && cryoBlocked) || 
           (item?.slug == 'magnit' && magnitBlocked) || 
           (item?.slug == 'asic_manager' && managerBlocked) ||
           (item?.slug == 'repair_kit' && repairKitBlocked),
  forever: paymentRadio == 'ton' && item?.slug !== 'azot' && item?.slug !== 'autostart' && 
           !((item?.slug == 'cryo' && cryoBlocked) || 
             (item?.slug == 'jarvis' && jarvisBlocked) || 
             (item?.slug == 'magnit' && magnitBlocked) || 
             (item?.slug == 'asic_manager' && managerBlocked) ||
             (item?.slug == 'repair_kit' && repairKitBlocked)),
  bought: ((item?.slug == 'cryo' && cryoIsForever && !cryoBlocked) || 
           (item?.slug == 'jarvis' && jarvisIsForever && !jarvisBlocked) || 
           (item?.slug == 'magnit' && magnitIsForever && !magnitBlocked) || 
           (item?.slug == 'asic_manager' && managerIsForever && !managerBlocked) ||
           (item?.slug == 'repair_kit' && repairKitIsForever && !repairKitBlocked)),
  // ... остальные классы
}"
```

#### 14.14. Добавить в условия отображения текста кнопки

В шаблоне, где отображается текст кнопки (около строки 813-853), добавить проверки для `repair_kit`:

**Для вечного буста (bought):**
```javascript
<span class="p-0 m-0 w-full h-full text-nowrap" v-else-if="
  paymentRadio == 'ton' &&
  ((item?.slug == 'cryo' && cryoIsForever && !cryoBlocked) ||
    (item?.slug == 'jarvis' && jarvisIsForever && !jarvisBlocked) ||
    (item?.slug == 'magnit' && magnitIsForever && !magnitBlocked) ||
    (item?.slug == 'asic_manager' && managerIsForever && !managerBlocked) ||
    (item?.slug == 'repair_kit' && repairKitIsForever && !repairKitBlocked))
">{{ t('common.bought') }}</span>
<span class="p-0 m-0 w-full h-full text-nowrap" v-else-if="
  (paymentRadio == 'stars' || paymentRadio == 'fbtc') &&
  ((item?.slug == 'cryo' && cryoIsForever && !cryoBlocked) ||
    (item?.slug == 'jarvis' && jarvisIsForever && !jarvisBlocked) ||
    (item?.slug == 'magnit' && magnitIsForever && !magnitBlocked) ||
    (item?.slug == 'asic_manager' && managerIsForever && !managerBlocked) ||
    (item?.slug == 'repair_kit' && repairKitIsForever && !repairKitBlocked))
">{{ t('common.bought') }}</span>
```

**Для блокированного NFT (speedup):**
```javascript
<span class="flex text-[12px] items-center gap-1"
  v-if="(item?.slug == 'jarvis' && jarvisBlocked) || 
        (item?.slug == 'cryo' && cryoBlocked) || 
        (item?.slug == 'magnit' && magnitBlocked) || 
        (item?.slug == 'asic_manager' && managerBlocked) ||
        (item?.slug == 'repair_kit' && repairKitBlocked)">
  {{ t('common.speedup') }}
  <img src="@/assets/wheel_stars.png" width="18px" height="18px" />
</span>
```

#### 14.15. Добавить в условия для SBT/Premium меток

В шаблоне, где отображаются метки SBT и Premium (около строки 690-701), добавить проверки для `repair_kit`:

```javascript
<span v-if="((app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft) || (app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft)) && 
            (item?.slug !== 'azot' && item?.slug !== 'powerbank' && item?.slug !== 'premium_sub') && 
            paymentRadio == 'stars' && (
              item?.slug === 'cryo' ? !cryoIsForever && !cryoBlocked :
              item?.slug === 'jarvis' ? !jarvisIsForever && !jarvisBlocked :
              item?.slug == 'magnit' ? !magnitIsForever && !magnitBlocked :
              item?.slug === 'asic_manager' ? !managerIsForever && !managerBlocked :
              item?.slug === 'repair_kit' ? !repairKitIsForever && !repairKitBlocked : true
            )" class="!text-[#FCD909] !font-bold">SBT</span>
<span v-if="premiumActive && 
            (item?.slug !== 'azot' && item?.slug !== 'powerbank' && item?.slug !== 'premium_sub') && 
            paymentRadio == 'stars' && (
              item?.slug === 'cryo' ? !cryoIsForever && !cryoBlocked :
              item?.slug === 'jarvis' ? !jarvisIsForever && !jarvisBlocked :
              item?.slug == 'magnit' ? !magnitIsForever && !magnitBlocked :
              item?.slug === 'asic_manager' ? !managerIsForever && !managerBlocked :
              item?.slug === 'repair_kit' ? !repairKitIsForever && !repairKitBlocked : true
            )" class="!text-[#FCD909] !font-bold">{{ t('boost.king') }}</span>
```

#### 14.16. Добавить в условия для счетчика дней

В шаблоне, где проверяется условие для отображения счетчика дней (около строки 705-716), добавить проверки для `repair_kit`:

```javascript
<div v-if="
  (paymentRadio == 'stars' || paymentRadio == 'fbtc') &&
  isFreeBooster(item) == false &&
  item?.slug !== 'azot' &&
  item?.slug !== 'powerbank' &&
  item?.slug !== 'magnit' &&
  (
    item?.slug === 'cryo' ? !cryoIsForever && !cryoBlocked :
    item?.slug === 'jarvis' ? !jarvisIsForever && !jarvisBlocked :
    item?.slug === 'asic_manager' ? !managerIsForever && !managerBlocked :
    item?.slug === 'repair_kit' ? !repairKitIsForever && !repairKitBlocked : true
  )
" class="boost-counter">
  <!-- ... содержимое счетчика ... -->
</div>
```

#### 14.17. Добавить в условие для отображения "forever" текста (TON payment)

В шаблоне, где отображается текст "forever" для TON payment (около строки 766-772), добавить проверку для `repair_kit`:

```javascript
<div v-if="
  paymentRadio == 'ton'
  && ((item?.slug == 'cryo' && !cryoIsForever && !cryoBlocked) ||
    (item?.slug == 'jarvis' && !jarvisIsForever && !jarvisBlocked) ||
    (item?.slug == 'magnit' && !magnitIsForever && !magnitBlocked) ||
    (item?.slug == 'asic_manager' && !managerIsForever && !managerBlocked) ||
    (item?.slug == 'repair_kit' && !repairKitIsForever && !repairKitBlocked))
">
  <span class="always-text">{{ t('common.forever') }}</span>
</div>
```

#### 14.18. Добавить в условие для кнопки "continue" (продолжить)

В шаблоне, где отображается кнопка "continue" для активного буста (около строки 822), добавить проверку для `repair_kit`:

```javascript
<span
  v-else-if="(paymentRadio == 'stars' || paymentRadio == 'fbtc') && 
              isActiveBooster(item) && 
              (item?.slug == 'jarvis' && !jarvisIsForever) ||
              (item?.slug == 'repair_kit' && !repairKitIsForever)">
  {{ t('common.continue') }}
  <!-- ... остальной код с ценами ... -->
</span>
```

**Примечание:** Кнопка "continue" показывается когда буст активен, но не вечный (можно продлить).

В шаблоне, где проверяется список бустов для отображения скидки SBT/Premium (около строки 904-909), добавить `'repair_kit'`:

```javascript
(item?.slug == 'jarvis' ||
  item?.slug == 'magnit' ||
  item?.slug == 'cryo' ||
  item?.slug == 'asic_manager' ||
  item?.slug == 'electrics' ||
  item?.slug == 'premium_sub' ||
  item?.slug == 'repair_kit'
)
```

**Примечание:** Это условие используется для отображения зачеркнутой цены при наличии скидки SBT/Premium (когда количество дней < 5).

### 15. Backend: Настройка GradationConfig для Repair Kit NFT

**Файл:** Админка Django `/admin/core/gradationconfig/add/`

Для работы системы блокировки NFT (TimedUserNFT) нужно создать конфигурацию:

1. Войти в админку: `/admin/core/gradationconfig/add/`
2. Создать новую конфигурацию:
   - **Name:** `Repair Kit` (должно точно совпадать с именем NFT в метаданных)
   - **Gradation minutes:** Время блокировки в минутах (например, 60 для 1 часа)
   - **Gradation value:** Стоимость ускорения разблокировки в Stars

**Примечание:** Эта конфигурация используется для системы блокировки NFT после подключения нового кошелька.

### 16. Frontend: Добавление локализации

**Файлы:** 
- `src/locales/ru.json`
- `src/locales/en.json`
- `src/locales/uk.json`

Добавить переводы для буста "Рем. Комплект" (по аналогии с другими бустами).

### 17. Админка: Настройка буста

**Важно:** Все поля уже существуют в модели `Booster`. Не нужно создавать новые поля, используйте существующие.

1. Войти в админку Django: `/admin/tasks/booster/add/`
2. Создать новый буст со следующими параметрами (используя те же поля что и для Jarvis Bot):

#### 17.1. Основные поля

- **Order number:** `3.0` (или следующий номер после существующих бустов)
- **Slug:** `repair_kit` (выбрать из выпадающего списка: "Рем. Комплект | фиксирует Power")
- **Title:** `Рем. Комплект`
- **Title ru:** `Рем. Комплект`
- **Title en:** `Repair Kit`
- **Icon:** Загрузить иконку буста (например, `booster_icons/Repair_Kit.webp`)

#### 17.2. Статусы

- **Status1:** `Не активний`
- **Status1 ru:** `Не активен`
- **Status1 en:** `Inactive`
- **Status2:** `Активно`
- **Status2 ru:** `Активно`
- **Status2 en:** `Active`

#### 17.3. Дополнительная информация

**Важно:** Все тексты настраиваются в админке. Примеры значений (можно изменить в админке):

- **Additional info1:** `Від 1 до 30 днів` (пример)
- **Additional info1 ru:** `От 1 до 30 дней` (пример)
- **Additional info1 en:** `From 1 to 30 days` (пример)
- **Additional info2:** `Залишилось {N}` (пример)
- **Additional info2 ru:** `Осталось {N}` (пример)
- **Additional info2 en:** `Remaining {N}` (пример)

**Примечание:** 
- `{N}` будет заменено на количество дней в коде автоматически
- Все тексты берутся из модели `Booster` через API, не захардкожены в коде
- Администратор может изменить тексты в любой момент через админку

#### 17.4. Описание

**Важно:** Описания настраиваются в админке. Примеры текстов (можно изменить в админке):

- **Description:** 
  ```
  Завдяки передовим технологіям ремонту, цей бустер фіксує рівень Power вашої електростанції на момент активації та не дозволяє йому знижуватися. Ідеальний вибір для збереження продуктивності станції.
  ```
  (пример, можно изменить в админке)
- **Description ru:**
  ```
  Благодаря передовым технологиям ремонта, данный бустер фиксирует уровень Power вашей электростанции на момент активации и не позволяет ему снижаться. Идеальный выбор для сохранения производительности станции.
  ```
  (пример, можно изменить в админке)
- **Description en:**
  ```
  Thanks to advanced repair technologies, this booster locks your power plant's Power level at the moment of activation and prevents it from decreasing. The perfect choice for maintaining station performance.
  ```
  (пример, можно изменить в админке)

**Примечание:** Все описания берутся из модели `Booster` через API и отображаются в интерфейсе. Администратор может изменить их в любой момент через админку без изменения кода.

#### 17.5. Popup сообщение

**Важно:** Popup сообщения настраиваются в админке. Примеры текстов (можно изменить в админке):

- **Popup:**
  ```
  Ви активували підсилювач «Рем. Комплект», термін його дії {N}.
  ```
  (пример, можно изменить в админке)
- **Popup ru:**
  ```
  Вы активировали усилитель «Рем. Комплект», срок его действия {N}.
  ```
  (пример, можно изменить в админке)
- **Popup en:**
  ```
  You have activated the enhancer «Repair Kit», its expiration date is {N}.
  ```
  (пример, можно изменить в админке)

**Примечание:** 
- `{N}` будет заменено на количество дней в коде автоматически
- Все popup сообщения берутся из модели `Booster` через API
- Администратор может изменить тексты в любой момент через админку без изменения кода

#### 17.6. Цены (Stars)

**Важно:** Цены настраиваются в админке и могут быть изменены в любой момент без изменения кода. Примеры значений (как у Jarvis Bot):

- **Price1:** `149` (пример для уровней станции 1-3)
- **Price2:** `149` (пример для уровней станции 1-3)
- **Price3:** `149` (пример для уровней станции 1-3)
- **Price4:** `349` (пример для уровня станции 4)
- **Price5:** `449` (пример для уровня станции 5)
- **Price6:** `599` (пример для уровня станции 6)
- **Price7:** `699` (пример для уровня станции 7 и выше)
- **Price8:** `799` (резерв, можно настроить позже)
- **Price9:** `899` (резерв, можно настроить позже)
- **Price10:** `999` (резерв, можно настроить позже)

**Примечание:** Конкретные значения цен устанавливаются администратором в админке в зависимости от бизнес-логики. Код автоматически использует эти значения из модели `Booster`.

#### 17.7. Цены (fBTC)

**Важно:** Цены настраиваются в админке и могут быть изменены в любой момент без изменения кода. Примеры значений (как у Jarvis Bot):

- **Price1 fbtc:** `99.2` (пример для уровней станции 1-3)
- **Price2 fbtc:** `99.2` (пример для уровней станции 1-3)
- **Price3 fbtc:** `118.0` (пример для уровней станции 1-3)
- **Price4 fbtc:** `198.0` (пример для уровня станции 4)
- **Price5 fbtc:** `238.0` (пример для уровня станции 5)
- **Price6 fbtc:** `498.0` (пример для уровня станции 6)
- **Price7 fbtc:** `698.0` (пример для уровня станции 7 и выше)
- **Price8 fbtc:** `918.0` (резерв, можно настроить позже)
- **Price9 fbtc:** `1198.0` (резерв, можно настроить позже)
- **Price10 fbtc:** `1398.0` (резерв, можно настроить позже)

**Примечание:** Конкретные значения цен устанавливаются администратором в админке в зависимости от бизнес-логики. Код автоматически использует эти значения из модели `Booster`.

#### 17.8. Параметры N1, N2, N3

- **N1:** (можно оставить пустым, не используется для repair_kit)
- **N2:** (можно оставить пустым, не используется для repair_kit)
- **N3:** (можно оставить пустым, не используется для repair_kit)

**Примечание:** Поля N1, N2, N3 используются для других бустов (например, azot использует n1 для дополнительной стоимости). Для repair_kit они не нужны.

**Примечание:** Логика градации работает через `gen_config`:
- Уровень определяется как `Math.ceil(gen_config.id / 3)`
- Если результат >= 7, используется price7 (максимум)
- Иначе используется price{результат}
- **Все цены берутся из модели `Booster` через API, не захардкожены в коде**
- Цены должны быть настроены для всех уровней (1-10) для Stars и fBTC в админке
- Пример: если `gen_config.id = 10`, то `Math.ceil(10/3) = 4`, используется `price4` из модели `Booster`
- Пример: если `gen_config.id = 21`, то `Math.ceil(21/3) = 7`, используется `price7` из модели `Booster` (максимум)

**Важно:** 
- В backend используется функция `get_booster_price()` из `tasks/services.py` (строка 70-72), которая автоматически определяет цену на основе уровня станции через `STATION_LEVELS.index(user.station_type) + 1`
- Эта функция **читает цены из модели `Booster`** через `getattr(booster, f"price{station_index}_fbtc" if fbtc else f"price{station_index}")`
- Эта функция уже используется в `activate_booster()` для всех бустов, включая repair_kit (строка 124-126 для cryo, аналогично будет для repair_kit)
- В frontend используется более сложная логика через `gen_config`, которая делит `id` на 3 и округляет вверх, но **цены все равно берутся из `item?.[price]`**, где `item` - это объект буста из API
- **Никакие цены не захардкожены в коде** - все берется из админки через API

### 18. Передача файлов на серверы

#### 18.1. Передача файлов на тестовый сервер

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

# Передача файла для проверки NFT (если изменен)
scp edit/t.py projects-srv:/home/admsrv/tbtc_dev/t.py

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

#### 18.2. Передача файлов на продакшн сервер

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

#### 18.3. Передача frontend файлов

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

### 19. Тестирование на тестовом сервере

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

### 20. Деплой на продакшн

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
scp edit/tgbot/views.py projects-srv:/home/admsrv/tbtc_dev/tgbot/ && \
scp edit/t.py projects-srv:/home/admsrv/tbtc_dev/t.py
```

**Backend файлы на продакшн:**
```bash
scp edit/core/models.py edit/core/views.py edit/core/serializers.py projects-srv:/home/admsrv/tbtc/core/ && \
scp edit/tasks/models.py edit/tasks/services.py edit/tasks/views.py projects-srv:/home/admsrv/tbtc/tasks/ && \
scp edit/tgbot/views.py projects-srv:/home/admsrv/tbtc/tgbot/ && \
scp edit/t.py projects-srv:/home/admsrv/tbtc/t.py
```

## Важные замечания

1. **Поле repair_kit_power_level** - критически важно для фиксации уровня power. Без него буст не будет работать корректно.

2. **Проверка активности** - нужно проверять `repair_kit_expires` во всех местах, где уменьшается power.

3. **Совместимость с другими бустами** - Рем. Комплект должен работать независимо от других бустов (криокамера, джарвис и т.д.).

4. **Логика фиксации** - power фиксируется на уровне активации и не должен падать ниже этого уровня. Если пользователь отремонтирует станцию (power станет 100), то `repair_kit_power_level` обновляется на 100, и теперь power не должен падать ниже 100.

5. **Ограничение 31 день** - как и у других бустов, максимальный срок активации 31 день.

6. **Структура на сервере** - на сервере нет папки `edit`, файлы находятся в `core/` и `tasks/` напрямую. Учитывайте это при передаче файлов.

7. **Виртуальное окружение** - на сервере используйте `.venv/bin/python` вместо `python` для выполнения команд Django.

8. **Вечные NFT бусты** - система проверяет NFT на кошельках пользователей через функцию `main_boosters()` в `edit/t.py`. Эта функция должна запускаться периодически (через celery или cron). Если найден NFT нужного класса - устанавливается `repair_kit_expires` в 2100-01-01 (вечный буст).

9. **Классы NFT Repair Kit** - используются те же классы что и у Jarvis Bot:
   - **4 class:** для уровней станции 1-3
   - **3 class:** для уровней станции 4-5
   - **2 class:** для уровней станции 6-7
   - **1 class:** для уровней станции 8-9

10. **TimedUserNFT** - система блокировки NFT после подключения нового кошелька. Нужно создать `GradationConfig` с именем "Repair Kit" для работы этой системы.

11. **Запуск функции main_boosters()** - эта функция запускается в отдельном потоке в `edit/t.py` (строка 1627). Убедитесь что файл `t.py` запущен на сервере для периодической проверки NFT.

12. **Имя NFT в метаданных** - имя NFT должно быть точно "Repair Kit" (без класса). Класс указывается в скобках: "Repair Kit (4 class)", "Repair Kit (3 class)" и т.д. В коде используется `name.split("(")[0].strip()` для получения базового имени.

13. **КРИТИЧЕСКИ ВАЖНО: Нет захардкоженных значений** - все настройки буста (цены, тексты, описания) настраиваются через админку Django и берутся из модели `Booster` через API:
    - **Цены** - берутся из полей `price1-price10` и `price1_fbtc-price10_fbtc` модели `Booster`
    - **Тексты** - берутся из полей `title`, `status1`, `status2`, `additional_info1`, `additional_info2`, `description`, `popup` модели `Booster`
    - **Иконка** - берется из поля `icon` модели `Booster`
    - В коде используются только `booster.price1`, `booster.title`, `booster.status1` и т.д. - все из модели
    - **Не должно быть** захардкоженных значений типа `price = 149` или `title = "Рем. Комплект"` в коде
    - Все примеры в инструкции - это только примеры для заполнения админки, не для кода

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

