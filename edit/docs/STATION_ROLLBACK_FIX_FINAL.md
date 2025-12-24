# ФИНАЛЬНАЯ ИНСТРУКЦИЯ: Исправление массового отката станций

## 📊 Анализ инцидента

### Факты из базы данных

**Дата:** 24 декабря 2025 года  
**Время:** 09:17:45 - 09:18:12 UTC (27 секунд)  
**Количество откатов:** 261 станция

**Распределение по типам:**
- Nuclear power plant: 183 отката
- Thermonuclear power plant: 64 отката
- Dyson Sphere: 13 откатов
- Neutron star: 1 откат

**Характеристики:**
- Все откаты произошли в течение 27 секунд
- Пик: 09:18 (158 откатов за минуту)
- Каждый пользователь потерял по 1 станции (нет множественных откатов у одного пользователя)
- Это указывает на системную проблему, а не на индивидуальные случаи

### Корневая причина

Массовый откат произошел из-за **проблем с TON API**:
1. API вернул ошибку 500 (Internal Server Error) или неполные данные
2. Код не обрабатывает ошибки API (нет try/except)
3. При ошибке запросы падают, но код продолжает работу
4. `all_nfts` становится неполным - не все NFT попали в список
5. `users` dict становится неполным - только те пользователи, чьи NFT попали в ответ
6. При проверке станций: для всех станций, чьи NFT не попали в ответ:
   - `user = users.get(station_nft.wallet)` возвращает `None`
   - `mint_string = ""` (пустая строка)
   - `station_nft.nft not in mint_string` = `True`
   - Вызывается `reset_station()` → станция откачена

## 🔍 Проблемный код

**Файл:** `edit/t.py`  
**Функция:** `main_mint()`  
**Строки:** 309-577

### Проблемный участок 1: Запросы к API без обработки ошибок (строки 318-333)

```318:333:edit/t.py
i = 0
while True:
    # Fetch 4 pages in batch
    pages = list(range(i, i + PAGES))
    results = [async_to_sync(get_nfts)(collection_addr, page) for page in pages]

    has_short_page = False
    for data in results:
        all_nfts.extend(data.nft_items)
        logging.info(f"{len(data.nft_items)}")
        if len(data.nft_items) < 1000:
            has_short_page = True

    if has_short_page:
        break
    i += PAGES
```

**Проблемы:**
- Нет обработки ошибок - если `get_nfts()` упадет, весь скрипт упадет или вернет неполные данные
- Нет проверки на полноту данных
- Нет retry механизма

### Проблемный участок 2: Проверка станций без защиты (строки 552-577)

```552:577:edit/t.py
logging.info("")
logging.info("checking nfts")
for station_nft in StationNFTOwner.objects.filter(nft__isnull=False).exclude(
    nft=""
):
    try:
        user = users.get(station_nft.wallet or "")
        if user is None:
            mint_string = ""
        else:
            mint_string = ";".join(user["mint_string"])
        if (
            station_nft.nft not in mint_string
            or nfts_info[station_nft.nft]["nft"].sale is not None
        ):
            Notification.objects.create(
                user=station_nft.user, notif_type="nft_not_found"
            )
            station_nft.user.reset_station()
            logger.info(
                f"station_nft not in mint string {station_nft.nft} | {mint_string}"
            )
            logger.info(station_nft)

    except Exception:
        logger.exception("err profile")
```

**Проблемы:**
- Нет проверки полноты данных перед проверкой станций
- Если `users` dict неполный (из-за ошибки API), все станции откатываются
- Нет защиты от массового отката

## 🛠️ Решение: Пошаговая инструкция

### Шаг 1: Добавить функцию retry для запросов к API

Добавить перед функцией `main_mint()` (после строки 308):

```python
from pytonapi.exceptions import TONAPIError
from django.core.cache import cache
import asyncio

def get_nfts_with_retry(addr, page, max_retries=3, delay=1):
    """
    Получить NFT с повторными попытками при ошибке.
    
    Args:
        addr: Адрес коллекции
        page: Номер страницы
        max_retries: Максимальное количество попыток
        delay: Начальная задержка между попытками (секунды)
    
    Returns:
        Результат запроса или None при неудаче
    """
    for attempt in range(max_retries):
        try:
            result = async_to_sync(get_nfts)(addr, page)
            return result
        except (TONAPIError, Exception) as e:
            if attempt == max_retries - 1:
                logger.error(
                    f"Failed to fetch NFTs page {page} after {max_retries} attempts: {e}"
                )
                return None
            wait_time = delay * (2 ** attempt)  # Экспоненциальная задержка: 1s, 2s, 4s
            logger.warning(
                f"Error fetching NFTs page {page}, attempt {attempt + 1}/{max_retries}: {e}. "
                f"Retrying in {wait_time}s..."
            )
            time.sleep(wait_time)
    return None
```

### Шаг 2: Добавить функцию проверки полноты данных

Добавить после функции `get_nfts_with_retry`:

```python
def is_data_complete(all_nfts, collection_addr):
    """
    Проверить полноту данных NFT.
    
    Args:
        all_nfts: Список полученных NFT
        collection_addr: Адрес коллекции
    
    Returns:
        True если данные полные, False если неполные
    """
    # Получить ожидаемое количество из кэша
    cache_key = f"expected_nft_count_{collection_addr}"
    expected_count = cache.get(cache_key)
    
    if expected_count is None:
        # Если нет кэша, считаем данные полными (первый запуск)
        logger.info(f"No cached NFT count for {collection_addr}, assuming data is complete")
        return True
    
    # Проверяем, что получено не менее 90% ожидаемого количества
    threshold = expected_count * 0.9
    actual_count = len(all_nfts)
    
    if actual_count < threshold:
        logger.warning(
            f"API returned incomplete data: {actual_count}/{expected_count} "
            f"({actual_count/expected_count*100:.1f}%)"
        )
        return False
    
    logger.info(
        f"Data completeness check passed: {actual_count}/{expected_count} "
        f"({actual_count/expected_count*100:.1f}%)"
    )
    return True

def save_expected_nft_count(collection_addr, count):
    """
    Сохранить ожидаемое количество NFT в кэш.
    
    Args:
        collection_addr: Адрес коллекции
        count: Количество NFT
    """
    cache_key = f"expected_nft_count_{collection_addr}"
    cache.set(cache_key, count, timeout=86400)  # 24 часа
    logger.info(f"Saved expected NFT count for {collection_addr}: {count}")
```

### Шаг 3: Исправить запросы к API с обработкой ошибок

Заменить строки 318-333 в `main_mint()`:

```python
i = 0
failed_pages = []
while True:
    # Fetch pages in batch
    pages = list(range(i, i + PAGES))
    results = []
    
    for page in pages:
        result = get_nfts_with_retry(collection_addr, page)
        if result is None:
            failed_pages.append(page)
            logger.error(f"Failed to fetch page {page} after all retries")
        else:
            results.append(result)
    
    # Если все страницы не удалось получить, прерываем
    if not results:
        logger.error(f"Failed to fetch any pages starting from {i}, aborting")
        break
    
    has_short_page = False
    for data in results:
        if data is not None:
            all_nfts.extend(data.nft_items)
            logging.info(f"{len(data.nft_items)}")
            if len(data.nft_items) < 1000:
                has_short_page = True
    
    # Если были ошибки, но получили хотя бы часть данных, продолжаем
    if failed_pages:
        logger.warning(f"Some pages failed: {failed_pages}, but continuing with available data")
    
    if has_short_page:
        break
    i += PAGES
```

### Шаг 4: Добавить проверку полноты данных после получения NFT

Добавить после строки 335 (после `logging.info(f"FINAL {len(all_nfts)}")`):

```python
logging.info(f"FINAL {len(all_nfts)}")

# Сохранить ожидаемое количество для следующей проверки
if len(all_nfts) > 0:
    save_expected_nft_count(collection_addr, len(all_nfts))

# Проверка на полноту данных
if not is_data_complete(all_nfts, collection_addr):
    logger.error(
        f"API returned incomplete data for collection {collection_addr}. "
        f"Received {len(all_nfts)} NFTs. Skipping station check to prevent mass rollback."
    )
    # Попытка использовать кэш из предыдущего успешного запроса
    cache_key = f"last_successful_nfts_{collection_addr}"
    cached_nfts = cache.get(cache_key)
    if cached_nfts:
        logger.info(f"Using cached NFT data from previous successful request")
        all_nfts = cached_nfts
        # Пересоздаем users dict из кэшированных данных
        users = {}
        for nft in all_nfts:
            address = nft.owner.address.root
            nft_address = nft.address.root
            users.setdefault(address, {"mint_string": []})
            users[address]["mint_string"].append(nft_address)
    else:
        logger.error("No cached data available, aborting to prevent mass rollback")
        return  # НЕ проверяем станции при неполных данных

# Сохранить успешные данные в кэш
if len(all_nfts) > 0:
    cache_key = f"last_successful_nfts_{collection_addr}"
    cache.set(cache_key, all_nfts, timeout=600)  # 10 минут
    logger.info(f"Cached {len(all_nfts)} NFTs for fallback use")
```

### Шаг 5: Добавить защиту перед проверкой станций

Добавить перед строкой 552 (перед `logging.info("checking nfts")`):

```python
# КРИТИЧЕСКАЯ ЗАЩИТА: Проверка полноты данных перед проверкой станций
if not is_data_complete(all_nfts, collection_addr):
    logger.error(
        "CRITICAL: API data incomplete before station check. "
        "Skipping station check to prevent mass rollback."
    )
    # Попытка использовать кэш
    cache_key = f"last_successful_nfts_{collection_addr}"
    cached_nfts = cache.get(cache_key)
    if cached_nfts and len(cached_nfts) > len(all_nfts) * 1.1:
        logger.warning("Using cached data as it's more complete")
        all_nfts = cached_nfts
        # Пересоздаем users dict
        users = {}
        nfts_info = {}
        for nft in all_nfts:
            address = nft.owner.address.root
            nft_address = nft.address.root
            users.setdefault(address, {"mint_string": []})
            users[address]["mint_string"].append(nft_address)
            nfts_info[nft_address] = {"nft": nft}
    else:
        logger.error("No valid cached data available. ABORTING station check.")
        return

logging.info("")
logging.info("checking nfts")
```

### Шаг 6: Улучшить обработку ошибок в проверке станций

Изменить строки 554-577 для более безопасной проверки:

```python
for station_nft in StationNFTOwner.objects.filter(nft__isnull=False).exclude(
    nft=""
):
    try:
        user = users.get(station_nft.wallet or "")
        if user is None:
            # КРИТИЧЕСКАЯ ПРОВЕРКА: Если пользователь не найден, это может быть из-за ошибки API
            # Проверяем, не является ли это массовой проблемой
            missing_users_count = StationNFTOwner.objects.filter(
                nft__isnull=False
            ).exclude(nft="").exclude(wallet__in=users.keys()).count()
            
            if missing_users_count > 50:  # Порог массовой проблемы
                logger.error(
                    f"CRITICAL: {missing_users_count} station owners not found in users dict. "
                    f"This indicates API data incompleteness. ABORTING station check."
                )
                break  # Прерываем проверку, чтобы не откатить все станции
            
            mint_string = ""
        else:
            mint_string = ";".join(user["mint_string"])
        
        # Дополнительная проверка: убедиться, что nft_info содержит этот NFT
        if station_nft.nft not in nfts_info:
            logger.warning(
                f"Station NFT {station_nft.nft} not found in nfts_info. "
                f"This may indicate incomplete API data. Skipping this station."
            )
            continue
        
        if (
            station_nft.nft not in mint_string
            or nfts_info[station_nft.nft]["nft"].sale is not None
        ):
            Notification.objects.create(
                user=station_nft.user, notif_type="nft_not_found"
            )
            station_nft.user.reset_station()
            logger.info(
                f"station_nft not in mint string {station_nft.nft} | {mint_string}"
            )
            logger.info(station_nft)

    except KeyError as e:
        logger.error(f"KeyError in station check: {e}. NFT may be missing from nfts_info.")
        continue
    except Exception:
        logger.exception("err profile")
```

### Шаг 7: Добавить rate limiting для запросов к API

Добавить задержку между запросами (минимум 10ms между запросами):

```python
# В функции get_nfts_with_retry, перед запросом:
if attempt > 0:  # Не задерживаем первую попытку
    time.sleep(0.01)  # 10ms задержка между запросами
```

Или добавить глобальную задержку в цикле запросов (в main_mint, строка 322):

```python
for page in pages:
    result = get_nfts_with_retry(collection_addr, page)
    if result is None:
        failed_pages.append(page)
        logger.error(f"Failed to fetch page {page} after all retries")
    else:
        results.append(result)
    
    # Rate limiting: минимум 10ms между запросами
    if page != pages[-1]:  # Не задерживаем после последнего запроса
        time.sleep(0.01)
```

## ✅ Чеклист исправлений

- [ ] Добавлена функция `get_nfts_with_retry()` с обработкой ошибок
- [ ] Добавлена функция `is_data_complete()` для проверки полноты данных
- [ ] Добавлена функция `save_expected_nft_count()` для кэширования
- [ ] Исправлен цикл запросов к API с обработкой ошибок
- [ ] Добавлена проверка полноты данных после получения NFT
- [ ] Добавлена защита перед проверкой станций
- [ ] Улучшена обработка ошибок в проверке станций
- [ ] Добавлен rate limiting для запросов к API
- [ ] Добавлено кэширование успешных данных
- [ ] Протестировано на dev окружении

## 🧪 Тестирование

### Тест 1: Симуляция ошибки API

1. Временно изменить `get_nfts()` чтобы выбрасывать исключение
2. Убедиться, что скрипт не падает
3. Убедиться, что используется кэш или проверка станций пропускается
4. Убедиться, что станции НЕ откатываются

### Тест 2: Симуляция неполных данных

1. Временно ограничить количество возвращаемых NFT
2. Убедиться, что срабатывает проверка полноты данных
3. Убедиться, что проверка станций пропускается
4. Убедиться, что станции НЕ откатываются

### Тест 3: Проверка retry механизма

1. Временно сделать API нестабильным (возвращать ошибку 50% запросов)
2. Убедиться, что retry работает
3. Убедиться, что после всех попыток используется кэш или проверка пропускается

## 🚨 Критические правила

1. **НИКОГДА не откатывать станции, если данные API неполные или есть ошибки!**
2. **Всегда проверять полноту данных перед проверкой станций**
3. **Использовать кэш при ошибках API**
4. **Логировать все критические действия**
5. **Прерывать проверку станций при обнаружении массовой проблемы**

## 📝 Дополнительные рекомендации

1. **Мониторинг:** Добавить алерты при обнаружении неполных данных API
2. **Метрики:** Отслеживать количество успешных/неуспешных запросов к API
3. **Логирование:** Улучшить логирование для отладки
4. **Тестирование:** Регулярно тестировать сценарии ошибок API

## 🔗 Связанные файлы

- **`edit/t.py`** - основной скрипт с проблемным кодом (строки 309-577)
- **`core/models.py`** - модель `StationRollbackLog` и метод `reset_station()`
- **`core/views.py`** - API endpoint `RollbackStationView`
- **`logs/t.log`** - логи скрипта

## 📅 История изменений

- **2025-12-24:** Массовый откат 261 станции из-за ошибки TON API
- **2025-12-24:** Создана финальная инструкция по исправлению

---

**ВАЖНО:** Это продакшн. Все изменения должны быть осторожными и протестированными на dev окружении перед деплоем.

