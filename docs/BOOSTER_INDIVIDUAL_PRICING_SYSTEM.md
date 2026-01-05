# Инструкция: Система индивидуальных цен для каждого буста

## Краткое резюме

**Проблема:** Все бусты используют одни и те же поля `price1-price10` в модели `Booster`, что не позволяет установить разные цены для разных бустов.

**Решение:** Создать модель `BoosterPriceLevel` для хранения индивидуальных цен каждого буста на каждом уровне (1-10).

**Важно:** 
- ✅ Логика определения уровня хешрейта **НЕ изменяется**
- ✅ Логика определения уровня станции **НЕ изменяется**
- ✅ Frontend **НЕ требует изменений** (если оставить старую систему в API)
- ✅ Обратная совместимость через fallback на старую систему

## Анализ текущей системы ценообразования

### Текущая архитектура

**Проблема:** Все бусты используют одни и те же поля `price1-price10` и `price1_fbtc-price10_fbtc` в модели `Booster`. Это означает, что невозможно установить разные цены для разных бустов.

**Текущая структура модели Booster:**
```python
class Booster(models.Model):
    # ... другие поля ...
    price1 = models.IntegerField()
    price2 = models.IntegerField()
    # ... price3-price10 ...
    price1_fbtc = models.FloatField(default=0)
    price2_fbtc = models.FloatField(default=0)
    # ... price3_fbtc-price10_fbtc ...
```

**Две системы определения цены:**

1. **Для бустов с уровнями станций** (jarvis, cryo, repair_kit, electrics, premium_sub):
   - Используется функция `get_booster_price(user, booster, fbtc)`
   - Определяет уровень станции через `STATION_LEVELS.index(user.station_type) + 1`
   - Берет цену из `booster.price{station_index}` или `booster.price{station_index}_fbtc`

2. **Для бустов с хешрейтом** (magnit, asic_manager, powerbank):
   - Используется функция `get_booster_price_hashrate(mining_speed, booster, fbtc)`
   - Определяет уровень хешрейта через `HashrateInfo.objects.order_by("hashrate")`
   - Берет цену из `booster.price{hashrate_level}` или `booster.price{hashrate_level}_fbtc`

### Проблема

Если у нас есть:
- Буст A (jarvis) с ценами: price1=100, price2=200, price3=300
- Буст B (cryo) с ценами: price1=150, price2=250, price3=350

Они оба используют одни и те же поля `price1`, `price2`, `price3` в одной записи модели `Booster`. Невозможно установить разные цены для разных бустов.

## Решение: Модель BoosterPriceLevel

Создать отдельную модель для хранения цен каждого буста на каждом уровне.

### Преимущества:
- ✅ Каждый буст может иметь свои уникальные цены для каждого уровня
- ✅ Не затронет существующую логику (только изменим функции получения цены)
- ✅ Легко настраивать через админку
- ✅ Масштабируемо (можно добавить новые бусты без изменения структуры)

### Недостатки:
- ⚠️ Требует миграцию базы данных
- ⚠️ Нужно перенести существующие цены из модели Booster в новую модель
- ⚠️ Нужно обновить функции получения цены

## Шаги реализации

### Шаг 1: Создать модель BoosterPriceLevel

**Файл:** `edit/tasks/models.py`

Добавить после модели `Booster`:

```python
class BoosterPriceLevel(models.Model):
    """Модель для хранения цен каждого буста на каждом уровне"""
    booster = models.ForeignKey(Booster, on_delete=models.CASCADE, related_name='price_levels')
    level = models.IntegerField(help_text="Уровень станции (1-10) или уровень хешрейта (1-10)")
    price_stars = models.IntegerField(help_text="Цена в Stars")
    price_fbtc = models.FloatField(default=0, help_text="Цена в fBTC")
    
    class Meta:
        unique_together = ['booster', 'level']
        ordering = ['booster', 'level']
        verbose_name = "Уровень цены буста"
        verbose_name_plural = "Уровни цен бустов"
    
    def __str__(self):
        return f"{self.booster.title} - Level {self.level}: {self.price_stars} Stars / {self.price_fbtc} fBTC"
```

### Шаг 2: Обновить функции получения цены

**Файл:** `edit/tasks/services.py`

#### 2.1. Обновить `get_booster_price()`

Заменить функцию:

```python
def get_booster_price(user: UserProfile, booster: Booster, fbtc=False):
    station_index = STATION_LEVELS.index(user.station_type) + 1
    
    # Пытаемся получить цену из новой модели BoosterPriceLevel
    try:
        price_level = BoosterPriceLevel.objects.get(booster=booster, level=station_index)
        if fbtc:
            return price_level.price_fbtc
        else:
            return price_level.price_stars
    except BoosterPriceLevel.DoesNotExist:
        # Fallback на старую систему (для обратной совместимости)
        return getattr(booster, f"price{station_index}_fbtc" if fbtc else f"price{station_index}")
```

#### 2.2. Обновить `get_booster_price_hashrate()`

Заменить функцию:

```python
def get_booster_price_hashrate(mining_speed, booster: Booster, fbtc=False):
    infos = HashrateInfo.objects.order_by("hashrate").values_list("hashrate", flat=True)
    level = None
    
    for i, info in enumerate(infos, start=1):
        if mining_speed < info:
            level = i
            break
    
    if level is None:
        level = len(infos) + 1
    
    # Пытаемся получить цену из новой модели BoosterPriceLevel
    try:
        price_level = BoosterPriceLevel.objects.get(booster=booster, level=level)
        if fbtc:
            return price_level.price_fbtc
        else:
            return price_level.price_stars
    except BoosterPriceLevel.DoesNotExist:
        # Fallback на старую систему (для обратной совместимости)
        return getattr(booster, f"price{level}_fbtc" if fbtc else f"price{level}")
```

### Шаг 3: Добавить импорт модели

**Файл:** `edit/tasks/services.py`

В начале файла добавить:

```python
from tasks.models import Booster, BoosterPriceLevel, Task, UserReward, UserTask, WheelSlot
```

### Шаг 4: Обновить админку

**Файл:** `edit/tasks/admin.py` (или где регистрируются модели)

Добавить:

```python
from tasks.models import BoosterPriceLevel

@admin.register(BoosterPriceLevel)
class BoosterPriceLevelAdmin(admin.ModelAdmin):
    list_display = ('booster', 'level', 'price_stars', 'price_fbtc')
    list_filter = ('booster', 'level')
    search_fields = ('booster__title',)
    ordering = ('booster', 'level')
```

### Шаг 5: Создать миграцию

```bash
cd edit
source .venv/bin/activate
python manage.py makemigrations tasks
```

### Шаг 6: Создать скрипт для переноса данных

**Файл:** `edit/tasks/management/commands/migrate_booster_prices.py`

Создать папку структуру:
```
edit/tasks/management/
edit/tasks/management/__init__.py
edit/tasks/management/commands/
edit/tasks/management/commands/__init__.py
edit/tasks/management/commands/migrate_booster_prices.py
```

Содержимое `migrate_booster_prices.py`:

```python
from django.core.management.base import BaseCommand
from tasks.models import Booster, BoosterPriceLevel

class Command(BaseCommand):
    help = 'Переносит цены из модели Booster в BoosterPriceLevel'

    def handle(self, *args, **options):
        boosters = Booster.objects.all()
        
        for booster in boosters:
            for level in range(1, 11):
                price_stars = getattr(booster, f'price{level}', None)
                price_fbtc = getattr(booster, f'price{level}_fbtc', 0)
                
                if price_stars is not None and price_stars > 0:
                    BoosterPriceLevel.objects.get_or_create(
                        booster=booster,
                        level=level,
                        defaults={
                            'price_stars': price_stars,
                            'price_fbtc': price_fbtc or 0
                        }
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Создан уровень {level} для буста {booster.title}: '
                            f'{price_stars} Stars / {price_fbtc} fBTC'
                        )
                    )
        
        self.stdout.write(self.style.SUCCESS('Перенос данных завершен!'))
```

Запустить команду:
```bash
python manage.py migrate_booster_prices
```

### Шаг 7: Обновить frontend (опционально)

**Важно:** Frontend НЕ требует изменений, если оставить старую систему в API!

**Текущая логика frontend:**
- Frontend использует `item?.[price]` где `price` формируется динамически
- Для бустов с уровнями станций: `price = "price${level}"` или `"price${level}_fbtc"`
- Для бустов с хешрейтом: `price = "price${priceByHash}"` или `"price${priceByHash}_fbtc"`
- API возвращает объект буста с полями `price1`, `price2`, ..., `price1_fbtc`, `price2_fbtc`, ...

**Вариант 1: Оставить старую систему в API (рекомендуется)**
- Не нужно менять сериализатор
- Frontend продолжит работать без изменений
- Backend будет использовать новую модель `BoosterPriceLevel` для расчетов
- API будет продолжать возвращать старые поля `price1-price10` из модели `Booster`
- Можно синхронизировать данные: при сохранении `BoosterPriceLevel` обновлять поля `price1-price10` в `Booster`

**Вариант 2: Обновить API для использования новой модели**

**Файл:** `edit/tasks/serializers.py`

Обновить `BoosterSerializer` чтобы включить цены из `BoosterPriceLevel`:

```python
class BoosterPriceLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoosterPriceLevel
        fields = ['level', 'price_stars', 'price_fbtc']

class BoosterSerializer(serializers.ModelSerializer):
    # Добавляем price_levels для новой системы
    price_levels = BoosterPriceLevelSerializer(many=True, read_only=True, source='price_levels.all')
    
    class Meta:
        model = Booster
        fields = '__all__'
    
    def to_representation(self, instance):
        """Синхронизируем старые поля price1-price10 с новой моделью для обратной совместимости"""
        data = super().to_representation(instance)
        
        # Если есть price_levels, синхронизируем старые поля
        if hasattr(instance, 'price_levels'):
            for price_level in instance.price_levels.all():
                level = price_level.level
                data[f'price{level}'] = price_level.price_stars
                data[f'price{level}_fbtc'] = price_level.price_fbtc
        
        return data
```

**Рекомендация:** Использовать Вариант 1 (оставить старую систему в API) для максимальной обратной совместимости. Frontend не требует изменений вообще.

## Важные замечания

### 1. Обратная совместимость

Функции `get_booster_price()` и `get_booster_price_hashrate()` имеют fallback на старую систему. Это означает:
- Если для буста нет записей в `BoosterPriceLevel`, будут использоваться старые поля `price1-price10`
- Это позволяет постепенно мигрировать бусты
- Можно мигрировать один буст за раз

### 2. Логика с хешрейтом НЕ затронута

Функция `get_booster_price_hashrate()` работает точно так же:
- Определяет уровень хешрейта через `HashrateInfo`
- Берет цену из `BoosterPriceLevel` по уровню
- Если нет записи - fallback на старую систему

**Никаких изменений в логике определения уровня хешрейта!**

### 3. Логика с уровнями станций НЕ затронута

Функция `get_booster_price()` работает точно так же:
- Определяет уровень станции через `STATION_LEVELS.index(user.station_type) + 1`
- Берет цену из `BoosterPriceLevel` по уровню
- Если нет записи - fallback на старую систему

**Никаких изменений в логике определения уровня станции!**

### 4. Миграция данных

Скрипт `migrate_booster_prices.py` переносит все существующие цены из модели `Booster` в `BoosterPriceLevel`. После миграции:
- Все бусты будут иметь свои индивидуальные цены
- Можно будет изменять цены каждого буста независимо
- Старые поля `price1-price10` можно оставить для обратной совместимости или удалить позже

## Чеклист реализации

- [ ] Создать модель `BoosterPriceLevel` в `edit/tasks/models.py`
- [ ] Обновить функции `get_booster_price()` и `get_booster_price_hashrate()` в `edit/tasks/services.py`
- [ ] Добавить импорт `BoosterPriceLevel` в `services.py`
- [ ] Зарегистрировать модель в админке `edit/tasks/admin.py`
- [ ] Создать структуру папок для management команды
- [ ] Создать скрипт миграции данных `edit/tasks/management/commands/migrate_booster_prices.py`
- [ ] Создать миграцию: `python manage.py makemigrations tasks`
- [ ] Применить миграцию на тестовом сервере: `python manage.py migrate`
- [ ] Запустить скрипт миграции данных: `python manage.py migrate_booster_prices`
- [ ] Проверить работу на тестовом сервере (бусты с хешрейтом и уровнями станций)
- [ ] Обновить сериализатор (опционально, если нужно изменить API)
- [ ] Применить на продакшн

## Пример использования в админке

После реализации, в админке можно будет:

1. Создать буст "Repair Kit"
2. Добавить уровни цен:
   - Level 1: 100 Stars / 50 fBTC
   - Level 2: 150 Stars / 75 fBTC
   - Level 3: 200 Stars / 100 fBTC
   - ... и т.д.

3. Создать буст "Jarvis Bot"
4. Добавить уровни цен:
   - Level 1: 120 Stars / 60 fBTC
   - Level 2: 180 Stars / 90 fBTC
   - Level 3: 240 Stars / 120 fBTC
   - ... и т.д.

Каждый буст будет иметь свои независимые цены!

## Файлы для изменения

1. `edit/tasks/models.py` - добавить модель `BoosterPriceLevel`
2. `edit/tasks/services.py` - обновить функции получения цены
3. `edit/tasks/admin.py` - зарегистрировать модель в админке
4. `edit/tasks/serializers.py` - обновить сериализатор (опционально)
5. `edit/tasks/management/commands/migrate_booster_prices.py` - скрипт миграции данных

## Проверка безопасности

### ✅ Логика с хешрейтом НЕ затронута

**Текущая логика:**
1. `get_booster_price_hashrate(mining_speed, booster, fbtc)` получает хешрейт пользователя
2. Сравнивает с `HashrateInfo.objects.order_by("hashrate")`
3. Определяет уровень (1-10) на основе хешрейта
4. Берет цену из `booster.price{level}` или `booster.price{level}_fbtc`

**После изменений:**
1. `get_booster_price_hashrate(mining_speed, booster, fbtc)` получает хешрейт пользователя
2. Сравнивает с `HashrateInfo.objects.order_by("hashrate")` - **БЕЗ ИЗМЕНЕНИЙ**
3. Определяет уровень (1-10) на основе хешрейта - **БЕЗ ИЗМЕНЕНИЙ**
4. Берет цену из `BoosterPriceLevel.objects.get(booster=booster, level=level)` - **ТОЛЬКО ИСТОЧНИК ДАННЫХ ИЗМЕНЕН**
5. Если нет записи - fallback на старую систему

**Вывод:** Логика определения уровня хешрейта остается полностью неизменной. Изменен только источник данных (откуда берется цена).

### ✅ Логика с уровнями станций НЕ затронута

**Текущая логика:**
1. `get_booster_price(user, booster, fbtc)` получает тип станции пользователя
2. Определяет индекс через `STATION_LEVELS.index(user.station_type) + 1`
3. Берет цену из `booster.price{station_index}` или `booster.price{station_index}_fbtc`

**После изменений:**
1. `get_booster_price(user, booster, fbtc)` получает тип станции пользователя
2. Определяет индекс через `STATION_LEVELS.index(user.station_type) + 1` - **БЕЗ ИЗМЕНЕНИЙ**
3. Берет цену из `BoosterPriceLevel.objects.get(booster=booster, level=station_index)` - **ТОЛЬКО ИСТОЧНИК ДАННЫХ ИЗМЕНЕН**
4. Если нет записи - fallback на старую систему

**Вывод:** Логика определения уровня станции остается полностью неизменной. Изменен только источник данных (откуда берется цена).

### ✅ Frontend логика НЕ затронута

**Текущая логика в Boost.vue:**
- Для бустов с уровнями станций: использует `gen_config` для определения уровня, затем `item?.[price]` где `price = "price${level}"` или `"price${level}_fbtc"`
- Для бустов с хешрейтом: использует `priceByHash` для определения уровня, затем `item?.[price]` где `price = "price${priceByHash}"` или `"price${priceByHash}_fbtc"`

**После изменений:**
- Если API будет возвращать цены из `BoosterPriceLevel` через сериализатор, frontend продолжит работать так же
- Если оставить старую систему в API (для обратной совместимости), frontend не нужно менять вообще

**Вывод:** Frontend не требует изменений, если оставить старую систему в API. Если обновить сериализатор - frontend продолжит работать автоматически.

### ✅ Обратная совместимость

- Если для буста нет записей в `BoosterPriceLevel`, используются старые поля `price1-price10`
- Можно мигрировать постепенно, один буст за раз
- Старые поля можно оставить для совместимости или удалить позже
- Все существующие бусты продолжат работать без изменений до миграции данных

## Тестирование

### Тест 1: Бусты с хешрейтом (magnit, asic_manager)

**До изменений:**
- Пользователь с хешрейтом 500
- HashrateInfo: [100, 250, 500, 1000, 2000]
- Определяется level = 3 (500 < 1000, но >= 500)
- Берется `booster.price3`

**После изменений:**
- Пользователь с хешрейтом 500
- HashrateInfo: [100, 250, 500, 1000, 2000] - **БЕЗ ИЗМЕНЕНИЙ**
- Определяется level = 3 - **БЕЗ ИЗМЕНЕНИЙ**
- Берется `BoosterPriceLevel.objects.get(booster=booster, level=3).price_stars` - **ТОЛЬКО ИСТОЧНИК ИЗМЕНЕН**

**Результат:** Логика определения уровня хешрейта работает идентично.

### Тест 2: Бусты с уровнями станций (jarvis, cryo, repair_kit)

**До изменений:**
- Пользователь с станцией "Nuclear power plant"
- STATION_LEVELS.index("Nuclear power plant") = 4
- station_index = 4 + 1 = 5
- Берется `booster.price5`

**После изменений:**
- Пользователь с станцией "Nuclear power plant"
- STATION_LEVELS.index("Nuclear power plant") = 4 - **БЕЗ ИЗМЕНЕНИЙ**
- station_index = 4 + 1 = 5 - **БЕЗ ИЗМЕНЕНИЙ**
- Берется `BoosterPriceLevel.objects.get(booster=booster, level=5).price_stars` - **ТОЛЬКО ИСТОЧНИК ИЗМЕНЕН**

**Результат:** Логика определения уровня станции работает идентично.

