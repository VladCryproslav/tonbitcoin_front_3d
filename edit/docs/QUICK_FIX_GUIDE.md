# Быстрая инструкция по исправлению проблемы с откатом станций

## 🚨 Проблема в двух словах

24.12.2025 произошел массовый откат 261 станции из-за ошибки TON API (500). Код не обрабатывает ошибки API и откатывает все станции, чьи NFT не попали в ответ.

## 📍 Где проблема

**Файл:** `t.py`  
**Функция:** `main_mint()`  
**Строки:** 309-577

## 🔧 Что нужно сделать

### 1. Добавить обработку ошибок (строки 318-339)

```python
# БЫЛО:
results = [async_to_sync(get_nfts)(collection_addr, page) for page in pages]

# ДОЛЖНО БЫТЬ:
results = []
for page in pages:
    try:
        result = async_to_sync(get_nfts)(collection_addr, page)
        results.append(result)
    except Exception as e:
        logger.error(f"Error fetching NFTs page {page}: {e}")
        # Решение: retry или использовать кэш
        raise  # или обработать иначе
```

### 2. Добавить проверку полноты данных (после строки 335)

```python
logging.info(f"FINAL {len(all_nfts)}")

# ДОБАВИТЬ:
# Проверка на полноту данных
expected_nft_count = get_expected_nft_count()  # из кэша или БД
if expected_nft_count and len(all_nfts) < expected_nft_count * 0.9:
    logger.warning(f"API returned incomplete data: {len(all_nfts)}/{expected_nft_count}")
    logger.warning("Skipping station check to prevent mass rollback")
    return  # НЕ проверяем станции при неполных данных
```

### 3. Добавить защиту перед проверкой станций (перед строкой 552)

```python
# ДОБАВИТЬ ПЕРЕД:
logging.info("")
logging.info("checking nfts")

# Проверка полноты данных перед проверкой станций
if not is_data_complete(all_nfts):
    logger.warning("API data incomplete, skipping station check")
    return
```

### 4. Добавить retry механизм

Создать функцию:
```python
def get_nfts_with_retry(addr, page, max_retries=3):
    for attempt in range(max_retries):
        try:
            return async_to_sync(get_nfts)(addr, page)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {wait_time}s")
            time.sleep(wait_time)
```

### 5. Добавить кэширование

```python
from django.core.cache import cache

# Сохранять успешный ответ
cache.set('last_successful_nfts', all_nfts, timeout=600)  # 10 минут

# Использовать при ошибке
if error:
    cached_nfts = cache.get('last_successful_nfts')
    if cached_nfts:
        all_nfts = cached_nfts
        logger.info("Using cached NFT data due to API error")
```

## ✅ Чеклист

- [ ] Обернуть запросы API в try/except
- [ ] Добавить проверку полноты данных
- [ ] Пропускать проверку станций при неполных данных
- [ ] Добавить retry механизм
- [ ] Добавить кэширование
- [ ] Протестировать с симуляцией ошибки API

## 🎯 Главное правило

**НИКОГДА не откатывать станции, если данные API неполные или есть ошибки!**

---

Подробная документация: `STATION_ROLLBACK_ISSUE.md`

