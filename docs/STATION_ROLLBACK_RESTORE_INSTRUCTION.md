# Инструкция: Восстановление станций через админку Django

## 📋 Обзор задачи

Создать функционал в админке Django для восстановления станций пользователей, которые были откачены из-за ошибки TON API 24.12.2025.

## 🎯 Требования

1. **Action в админке** для модели `StationRollbackLog`
2. **Восстановление станции** с актуальными параметрами по уровням
3. **Возврат энергии** на баланс `energy` в `UserProfile`
4. **Удаление building_until** - установить в `None`, чтобы не было стройки
5. **Создание записи** в `StationNFTOwner` с данными пользователя и NFT
6. **Добавление полей** в `StationRollbackLog`: статус восстановления и дата восстановления
7. **Миграции выполняются на сервере** - не локально

## 📊 Анализ текущей структуры

### Модель StationRollbackLog (текущая)

```python
class StationRollbackLog(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    from_station = models.CharField(max_length=50)  # Тип станции до отката
    generation_level = models.PositiveSmallIntegerField(null=True, blank=True)
    storage_level = models.PositiveSmallIntegerField(null=True, blank=True)
    engineer_level = models.PositiveSmallIntegerField(null=True, blank=True)
    energy = models.FloatField(null=True, blank=True)  # Энергия до отката
    date = models.DateTimeField(auto_now_add=True)  # Дата отката
```

**Что хранится:**
- Тип станции до отката (`from_station`)
- Уровни: generation, storage, engineer
- Энергия до отката (`energy`)
- Дата отката (`date`)

**Чего не хватает:**
- NFT адрес станции (нужен для `StationNFTOwner`)
- Статус восстановления (был ли откат назад)
- Дата восстановления

### Модель StationNFTOwner

```python
class StationNFTOwner(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    wallet = models.CharField(max_length=255)  # TON wallet пользователя
    nft = models.CharField(max_length=255, null=True, blank=True)  # NFT адрес
```

**Назначение:** Хранит связь пользователя с NFT станции. Используется в `t.py` для проверки владения NFT.

### Модель UserProfile (релевантные поля)

```python
class UserProfile(models.Model):
    user_id = models.BigIntegerField(unique=True)
    energy = models.FloatField(default=0)  # Текущая энергия
    ton_wallet = models.CharField(max_length=255, null=True, blank=True)
    
    station_type = models.CharField(max_length=255, default="Boiler house")
    storage_level = models.PositiveIntegerField(default=1)
    generation_level = models.PositiveIntegerField(default=1)
    engineer_level = models.PositiveIntegerField(default=1)
    current_station_nft = models.CharField(max_length=255, default="", blank=True)
    
    storage = models.DecimalField(max_digits=36, decimal_places=16, default=10)
    storage_limit = models.DecimalField(max_digits=36, decimal_places=16, default=10)
    generation_rate = models.DecimalField(max_digits=36, decimal_places=16, default=5)
    kw_per_tap = models.FloatField(default=0.025)
```

### Конфигурации станций

**StoragePowerStationConfig:**
```python
class StoragePowerStationConfig(models.Model):
    station_type = models.CharField(max_length=50)
    level = models.PositiveSmallIntegerField()  # 1, 2, 3
    storage_limit = models.FloatField()
    duration = models.DurationField()
```

**GenPowerStationConfig:**
```python
class GenPowerStationConfig(models.Model):
    station_type = models.CharField(max_length=50)
    level = models.PositiveSmallIntegerField()  # 1, 2, 3
    generation_rate = models.FloatField()
```

**EngineerConfig:**
```python
class EngineerConfig(models.Model):
    level = models.PositiveSmallIntegerField()
    tap_power = models.FloatField()  # kw_per_tap для уровня
```

## 🛠️ Шаг 1: Добавить поля в StationRollbackLog

### 1.1 Создать миграцию

**⚠️ ВАЖНО: Миграции будут выполняться на сервере!**

Создать файл миграции на сервере: `tbtc/core/migrations/XXXX_add_rollback_restore_fields.py`

```python
# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', 'XXXX_previous_migration'),  # Заменить на последнюю миграцию
    ]

    operations = [
        migrations.AddField(
            model_name='stationrollbacklog',
            name='nft_address',
            field=models.CharField(
                max_length=255,
                blank=True,
                null=True,
                verbose_name='NFT Address',
                help_text='Адрес NFT станции для восстановления'
            ),
        ),
        migrations.AddField(
            model_name='stationrollbacklog',
            name='is_restored',
            field=models.BooleanField(
                default=False,
                verbose_name='Восстановлено',
                help_text='Была ли станция восстановлена'
            ),
        ),
        migrations.AddField(
            model_name='stationrollbacklog',
            name='restored_at',
            field=models.DateTimeField(
                null=True,
                blank=True,
                verbose_name='Дата восстановления',
                help_text='Дата и время восстановления станции'
            ),
        ),
    ]
```

### 1.2 Обновить модель

В `edit/core/models.py`, обновить `StationRollbackLog`:

```python
class StationRollbackLog(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    from_station = models.CharField(max_length=50)
    generation_level = models.PositiveSmallIntegerField(null=True, blank=True)
    storage_level = models.PositiveSmallIntegerField(null=True, blank=True)
    engineer_level = models.PositiveSmallIntegerField(null=True, blank=True)
    energy = models.FloatField(null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    
    # Новые поля для восстановления
    nft_address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='NFT Address',
        help_text='Адрес NFT станции для восстановления'
    )
    is_restored = models.BooleanField(
        default=False,
        verbose_name='Восстановлено',
        help_text='Была ли станция восстановлена'
    )
    restored_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата восстановления',
        help_text='Дата и время восстановления станции'
    )

    def __str__(self):
        status = "✅ Восстановлено" if self.is_restored else "❌ Не восстановлено"
        return f"StationRollbackLog(user={self.user.user_id}, from_station={self.from_station}, {status})"
```

## 🛠️ Шаг 2: Создать функцию восстановления станции

В `edit/core/admin.py`, добавить функцию восстановления:

```python
from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone
from django.db.models import F

def restore_station_action(modeladmin, request, queryset):
    """
    Восстановить станцию пользователя из StationRollbackLog.
    
    Действия:
    1. Восстанавливает тип станции и уровни
    2. Возвращает энергию на баланс
    3. Удаляет building_until (чтобы не было стройки)
    4. Создает запись в StationNFTOwner
    5. Обновляет статус в StationRollbackLog
    """
    restored_count = 0
    errors = []
    
    for rollback_log in queryset:
        # Проверка: уже восстановлено?
        if rollback_log.is_restored:
            errors.append(
                f"User {rollback_log.user.user_id}: станция уже восстановлена"
            )
            continue
        
        # Проверка: есть ли NFT адрес?
        if not rollback_log.nft_address:
            errors.append(
                f"User {rollback_log.user.user_id}: отсутствует NFT адрес. "
                f"Добавьте NFT адрес в поле 'nft_address' перед восстановлением."
            )
            continue
        
        # Проверка: есть ли данные для восстановления?
        if not rollback_log.from_station:
            errors.append(
                f"User {rollback_log.user.user_id}: отсутствует тип станции"
            )
            continue
        
        try:
            with transaction.atomic():
                user = rollback_log.user
                
                # 1. Получить конфигурации станции по уровням
                storage_config = StoragePowerStationConfig.objects.filter(
                    station_type=rollback_log.from_station,
                    level=rollback_log.storage_level or 1
                ).first()
                
                gen_config = GenPowerStationConfig.objects.filter(
                    station_type=rollback_log.from_station,
                    level=rollback_log.generation_level or 1
                ).first()
                
                engineer_config = EngineerConfig.objects.filter(
                    level=rollback_log.engineer_level or 1
                ).first()
                
                if not storage_config or not gen_config or not engineer_config:
                    errors.append(
                        f"User {rollback_log.user.user_id}: не найдены конфигурации для "
                        f"станции {rollback_log.from_station}, уровни "
                        f"storage={rollback_log.storage_level}, "
                        f"gen={rollback_log.generation_level}, "
                        f"engineer={rollback_log.engineer_level}"
                    )
                    continue
                
                # 2. Восстановить станцию в UserProfile
                UserProfile.objects.filter(user_id=user.user_id).update(
                    station_type=rollback_log.from_station,
                    storage_level=rollback_log.storage_level or 1,
                    generation_level=rollback_log.generation_level or 1,
                    engineer_level=rollback_log.engineer_level or 1,
                    storage_limit=storage_config.storage_limit,
                    generation_rate=gen_config.generation_rate,
                    kw_per_tap=engineer_config.tap_power,
                    current_station_nft=rollback_log.nft_address,
                    # Возвращаем энергию на баланс
                    energy=F('energy') + (rollback_log.energy or 0),
                    # Удаляем building_until, чтобы не было стройки
                    building_until=None,
                )
                
                # 3. Создать запись в StationNFTOwner
                StationNFTOwner.objects.update_or_create(
                    user=user,
                    defaults={
                        'wallet': user.ton_wallet or '',
                        'nft': rollback_log.nft_address,
                    }
                )
                
                # 4. Обновить статус в StationRollbackLog
                rollback_log.is_restored = True
                rollback_log.restored_at = timezone.now()
                rollback_log.save(update_fields=['is_restored', 'restored_at'])
                
                restored_count += 1
                
        except Exception as e:
            errors.append(
                f"User {rollback_log.user.user_id}: ошибка при восстановлении - {str(e)}"
            )
            import traceback
            traceback.print_exc()
    
    # Вывести результаты
    if restored_count > 0:
        modeladmin.message_user(
            request,
            f"✅ Успешно восстановлено станций: {restored_count}",
            messages.SUCCESS
        )
    
    if errors:
        modeladmin.message_user(
            request,
            f"❌ Ошибки ({len(errors)}):\n" + "\n".join(errors[:10]),  # Показать первые 10
            messages.ERROR
        )

restore_station_action.short_description = "🔄 Восстановить станцию (Restore Station)"
```

## 🛠️ Шаг 3: Зарегистрировать action в админке

В `edit/core/admin.py`, обновить `StationRollbackLogAdmin`:

```python
@admin.register(StationRollbackLog)
class StationRollbackLogAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'from_station',
        'generation_level',
        'storage_level',
        'engineer_level',
        'energy',
        'date',
        'is_restored',
        'restored_at',
        'nft_address',
    )
    list_filter = (
        'from_station',
        'is_restored',
        'date',
    )
    search_fields = (
        'user__user_id',
        'user__username',
        'nft_address',
    )
    readonly_fields = (
        'date',
        'is_restored',
        'restored_at',
    )
    autocomplete_fields = ['user']
    
    # Добавить action
    actions = [restore_station_action]
    
    fieldsets = (
        ('Информация о пользователе', {
            'fields': ('user',)
        }),
        ('Данные до отката', {
            'fields': (
                'from_station',
                'generation_level',
                'storage_level',
                'engineer_level',
                'energy',
            )
        }),
        ('NFT для восстановления', {
            'fields': ('nft_address',),
            'description': 'Введите адрес NFT станции для восстановления. '
                          'Этот адрес будет использован в StationNFTOwner.'
        }),
        ('Статус восстановления', {
            'fields': (
                'is_restored',
                'restored_at',
                'date',
            ),
            'classes': ('collapse',)
        }),
    )
```

## 🛠️ Шаг 4: Добавить валидацию NFT адреса (опционально)

Можно добавить валидацию NFT адреса в форме админки:

```python
from django import forms
from django.core.exceptions import ValidationError

class StationRollbackLogAdminForm(forms.ModelForm):
    class Meta:
        model = StationRollbackLog
        fields = '__all__'
    
    def clean_nft_address(self):
        nft_address = self.cleaned_data.get('nft_address')
        if nft_address:
            # Базовая валидация формата TON адреса
            if not nft_address.startswith('0:') and not nft_address.startswith('EQ'):
                raise ValidationError(
                    'NFT адрес должен быть в формате TON адреса (начинаться с 0: или EQ)'
                )
        return nft_address

@admin.register(StationRollbackLog)
class StationRollbackLogAdmin(admin.ModelAdmin):
    form = StationRollbackLogAdminForm
    # ... остальной код
```

## 📝 Шаг 5: Получение NFT адресов

### 5.1 Автоматическое получение NFT адресов из TON API

**✅ РЕКОМЕНДУЕМЫЙ СПОСОБ:** Создать скрипт миграции, который автоматически получит NFT адреса из TON API.

#### Вариант 1: Скрипт для заполнения NFT адресов

Создать файл `edit/core/management/commands/fill_rollback_nft_addresses.py`:

```python
from django.core.management.base import BaseCommand
from core.models import StationRollbackLog, UserProfile
from pytonapi import AsyncTonapi
from asgiref.sync import async_to_sync
import time

# Коллекция станций
STATION_COLLECTION = "EQB-pBhnWEYPbIu25uM1Yp5MqGFjQ-8Jes5CT2Dr-OVd705u"

# API ключ (использовать тот же, что в t.py)
API_KEY = "AHNKO56KDTDIYGIAAAAKPVWGBLOQ2J4Z6W4ZYIP35GPCI6BSG647XSPXK6YEJHY4MTVHRFA"

tonapi = AsyncTonapi(api_key=API_KEY)


async def get_user_nft_by_station_type(wallet_address, station_type):
    """
    Получить NFT адрес конкретной станции пользователя из TON API.
    
    Args:
        wallet_address: TON wallet адрес пользователя
        station_type: Тип станции из StationRollbackLog.from_station
    
    Returns:
        NFT адрес или None если не найден
    """
    try:
        # Маппинг типов станций из БД в названия в NFT метаданных
        # В БД: "Nuclear power plant", "Thermonuclear power plant", "Dyson Sphere", "Neutron star"
        # В NFT metadata: может быть с уровнями в скобках, например "Nuclear power plant (Level 3)"
        station_type_mapping = {
            "Nuclear power plant": "Nuclear power plant",
            "Thermonuclear power plant": "Thermonuclear power plant",
            "Dyson Sphere": "Dyson Sphere",
            "Neutron star": "Neutron star",
            "Boiler house": "Boiler house",
        }
        
        # Получить ожидаемое название из метаданных
        expected_name = station_type_mapping.get(station_type, station_type)
        
        # Получить все NFT из коллекции станций
        # Нужно пройти по всем страницам
        all_nfts = []
        offset = 0
        limit = 1000
        
        while True:
            nfts = await tonapi.nft.get_items_by_collection_address(
                STATION_COLLECTION,
                limit=limit,
                offset=offset,
            )
            
            if not nfts.nft_items:
                break
            
            all_nfts.extend(nfts.nft_items)
            
            # Если получили меньше limit, значит это последняя страница
            if len(nfts.nft_items) < limit:
                break
            
            offset += limit
        
        # Найти NFT, принадлежащий этому wallet и соответствующего типа станции
        for nft in all_nfts:
            if nft.owner.address.root == wallet_address:
                # Получить метаданные NFT
                meta = nft.metadata or {}
                name = meta.get("name", "")
                
                # Убрать уровень в скобках (например "Nuclear power plant (Level 3)" -> "Nuclear power plant")
                name_clean = name.split("(")[0].strip()
                
                # Пропускаем Hydroelectric и Orbital (они в другой коллекции)
                if name_clean in ["Hydroelectric Power Station", "Orbital Power Station"]:
                    continue
                
                # Проверить, что тип станции совпадает
                if name_clean == expected_name:
                    return nft.address.root
        
        return None
    except Exception as e:
        print(f"Ошибка при получении NFT для {wallet_address}, станция {station_type}: {e}")
        return None


class Command(BaseCommand):
    help = 'Заполнить NFT адреса в StationRollbackLog из TON API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать, что будет сделано, без изменений',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Получить все записи без NFT адреса
        rollback_logs = StationRollbackLog.objects.filter(
            nft_address__isnull=True
        ).exclude(nft_address='').select_related('user')
        
        total = rollback_logs.count()
        self.stdout.write(f"Найдено записей без NFT адреса: {total}")
        
        filled = 0
        not_found = 0
        errors = 0
        
        for i, rollback_log in enumerate(rollback_logs, 1):
            user = rollback_log.user
            
            if not user.ton_wallet:
                self.stdout.write(
                    self.style.WARNING(
                        f"[{i}/{total}] User {user.user_id}: нет TON wallet"
                    )
                )
                not_found += 1
                continue
            
            self.stdout.write(
                f"[{i}/{total}] Обработка User {user.user_id} (wallet: {user.ton_wallet})..."
            )
            
            if not dry_run:
                # Получить NFT адрес конкретной станции из TON API
                nft_address = async_to_sync(get_user_nft_by_station_type)(
                    user.ton_wallet,
                    rollback_log.from_station
                )
                
                if nft_address:
                    rollback_log.nft_address = nft_address
                    rollback_log.save(update_fields=['nft_address'])
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✅ Найден NFT для {rollback_log.from_station}: {nft_address}"
                        )
                    )
                    filled += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠️  NFT не найден в TON API для станции '{rollback_log.from_station}'"
                        )
                    )
                    not_found += 1
                
                # Rate limiting: 10ms между запросами
                time.sleep(0.01)
            else:
                # Dry run: только показать
                self.stdout.write(
                    f"  [DRY RUN] Будет запрошен NFT для wallet: {user.ton_wallet}, "
                    f"станция: {rollback_log.from_station}"
                )
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"✅ Заполнено: {filled}"))
        self.stdout.write(self.style.WARNING(f"⚠️  Не найдено: {not_found}"))
        if errors > 0:
            self.stdout.write(self.style.ERROR(f"❌ Ошибок: {errors}"))
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("\nЭто был dry-run. Запустите без --dry-run для применения изменений.")
            )
```

**Использование:**
```bash
# На сервере
cd tbtc
.venv/bin/python manage.py fill_rollback_nft_addresses --dry-run  # Проверка
.venv/bin/python manage.py fill_rollback_nft_addresses  # Применение
```

#### Вариант 2: Получение из LinkedUserNFT (для Hydroelectric/Orbital)

Если станция была Hydroelectric или Orbital, можно попробовать найти в `LinkedUserNFT`:

```python
# В скрипте выше, добавить проверку LinkedUserNFT перед запросом к API
from core.models import LinkedUserNFT

# Для Hydroelectric/Orbital станций
if rollback_log.from_station in ["Hydroelectric Power Station", "Orbital Power Station"]:
    linked = LinkedUserNFT.objects.filter(
        user=user,
        wallet=user.ton_wallet
    ).first()
    
    if linked:
        rollback_log.nft_address = linked.nft_address
        rollback_log.save(update_fields=['nft_address'])
        self.stdout.write(
            self.style.SUCCESS(
                f"  ✅ Найден NFT в LinkedUserNFT: {linked.nft_address}"
            )
        )
        filled += 1
        continue  # Пропустить запрос к API
```

**Важно:** Скрипт автоматически получает NFT адрес **именно той станции**, которая была откачена, сравнивая тип станции из `from_station` с метаданными NFT из TON API.

### 5.2 Ручное заполнение NFT адресов

Если автоматическое получение не сработало, можно заполнить вручную:

1. **Открыть админку** → `Station Rollback Logs`
2. **Найти запись** пользователя
3. **Ввести NFT адрес** в поле "NFT Address"
4. **Сохранить**

**Источники NFT адресов:**
- Запросить у пользователя (если он знает)
- Проверить в блокчейне TON по wallet адресу
- Использовать TON API напрямую через браузер/Postman

### 5.3 Инструкция по использованию восстановления

1. **Заполнить NFT адреса** (автоматически или вручную)
2. **Открыть админку** → `Station Rollback Logs`
3. **Выбрать записи** для восстановления (чекбоксы)
4. **Выбрать action** "🔄 Восстановить станцию (Restore Station)"
5. **Нажать "Go"**
6. **Проверить результаты** в сообщениях админки

### 5.4 Проверка восстановления

После восстановления проверить:
- ✅ `UserProfile.station_type` = восстановленный тип станции
- ✅ `UserProfile.energy` = увеличена на значение из `rollback_log.energy`
- ✅ `UserProfile.current_station_nft` = NFT адрес
- ✅ `UserProfile.building_until` = `None` (стройка удалена)
- ✅ `StationNFTOwner` = создана запись с user, wallet, nft
- ✅ `StationRollbackLog.is_restored` = True
- ✅ `StationRollbackLog.restored_at` = текущая дата

## ⚠️ Важные замечания

1. **NFT адрес обязателен** - без него восстановление невозможно
2. **Автоматическое получение NFT** - рекомендуется использовать скрипт `fill_rollback_nft_addresses` для получения NFT адресов из TON API
3. **Проверка дубликатов** - если `StationNFTOwner` уже существует, она будет обновлена
4. **Транзакции** - все операции выполняются в транзакции для безопасности
5. **Энергия** - добавляется к текущему балансу (не заменяет)
6. **Уровни** - если уровень не указан, используется уровень 1
7. **Стройка удаляется** - `building_until` устанавливается в `None`, чтобы станция была сразу готова к использованию
8. **Миграции на сервере** - все миграции выполняются на сервере, не локально
9. **Rate limiting** - скрипт получения NFT адресов использует задержки между запросами к TON API

## 🧪 Тестирование

### Тест 1: Восстановление одной станции

1. Создать тестовую запись `StationRollbackLog`:
   ```python
   rollback = StationRollbackLog.objects.create(
       user=test_user,
       from_station="Nuclear power plant",
       generation_level=3,
       storage_level=3,
       engineer_level=30,
       energy=1000.0,
       nft_address="0:test_nft_address_123"
   )
   ```

2. Выполнить action восстановления
3. Проверить:
   - Станция восстановлена
   - Энергия добавлена
   - `StationNFTOwner` создана
   - Статус обновлен

### Тест 2: Массовое восстановление

1. Выбрать несколько записей
2. Выполнить action
3. Проверить, что все восстановлены

### Тест 3: Обработка ошибок

1. Попробовать восстановить без NFT адреса
2. Попробовать восстановить уже восстановленную станцию
3. Проверить сообщения об ошибках

## 📋 Чеклист реализации

- [ ] Создать миграцию для новых полей **на сервере**
- [ ] Применить миграцию на сервере (`python manage.py migrate`)
- [ ] Обновить модель `StationRollbackLog` в коде
- [ ] Создать функцию `restore_station_action`
- [ ] Зарегистрировать action в админке
- [ ] Добавить поля в `list_display`
- [ ] Добавить фильтры для `is_restored`
- [ ] Добавить валидацию NFT адреса (опционально)
- [ ] **Создать скрипт `fill_rollback_nft_addresses` для получения NFT адресов**
- [ ] Протестировать скрипт получения NFT адресов (`--dry-run`)
- [ ] Запустить скрипт получения NFT адресов на сервере
- [ ] Проверить заполненные NFT адреса в админке
- [ ] Протестировать восстановление на dev окружении
- [ ] Выполнить восстановление в продакшене

## 🔗 Связанные файлы

- `edit/core/models.py` - модель `StationRollbackLog`
- `edit/core/admin.py` - админка Django
- `edit/core/migrations/` - миграции БД
- `edit/t.py` - скрипт проверки NFT (использует `StationNFTOwner`)

---

**Дата создания:** 2025-12-24  
**Статус:** Требует реализации

