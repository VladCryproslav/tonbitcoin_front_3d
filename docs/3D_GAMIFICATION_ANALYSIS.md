# Анализ проекта и рекомендации по реализации 3D геймификации типа Subway Surfers

## Дата анализа: 26 января 2026

---

## 1. ТЕКУЩАЯ АРХИТЕКТУРА ПРОЕКТА

### 1.1 Фронтенд
- **Фреймворк**: Vue 3 (Composition API)
- **Сборщик**: Vite 6.0.1
- **Стейт-менеджмент**: Pinia
- **Роутинг**: Vue Router 4
- **Стилизация**: Tailwind CSS + SCSS
- **Платформа**: Telegram Mini App (WebView)
- **Ориентация**: Portrait (заблокирована через Telegram WebApp API)

### 1.2 Бекенд
- **Фреймворк**: Django 5.1.4 + Django REST Framework
- **База данных**: PostgreSQL (через dj_database_url)
- **Кэширование**: Redis
- **Аутентификация**: Custom Token через заголовок `X-Custom-Token` (Telegram initData)
- **API**: RESTful с Swagger документацией

### 1.3 Текущая игровая механика

#### Система сбора энергии:
- **Эндпоинт**: `POST /tap-energy/`
- **Лимит запросов**: 5 запросов/сек (TapEnergyThrottle)
- **Минимальный интервал**: 150ms между тапами
- **Механика**: Тапы по станции для сбора энергии из storage

#### Основные игровые параметры:
- `energy` - накопленная энергия (кВт)
- `storage` - текущее хранилище энергии (кВт)
- `storage_limit` - максимальное хранилище
- `power` - мощность станции (0-100%)
- `generation_rate` - скорость генерации энергии (кВт/час)
- `engineer_level` - уровень инженера (влияет на kw_per_tap)
- `kw_per_tap` - количество энергии за тап

#### Система перегрева:
- При перегреве станция блокируется на определенное время
- `overheated_until` - время окончания перегрева
- `tap_count_since_overheat` - счетчик тапов после перегрева
- При превышении лимита тапов снижается `power`

#### Система инженеров:
- `engineer_level` - основной уровень (1-49)
- `past_engineer_level` - уровень выше 49 (золотые инженеры)
- `electrics_expires` - временные синие инженеры
- Каждый уровень влияет на `tap_power` через `EngineerConfig`

#### Бустеры и NFT:
- Repair Kit - защита от снижения power
- Jarvis Bot - автоматический сбор энергии
- Cryochamber - защита от перегрева
- ASIC Manager, Magnetic Ring - для майнинга
- Различные типы станций (Hydro, Orbital)

---

## 2. ВЫБОР ДВИЖКА ДЛЯ 3D ГЕЙМИФИКАЦИИ

### 2.1 Требования к движку

**Ограничения Telegram Mini App:**
- Работает в WebView браузера
- Ограниченная производительность на мобильных устройствах
- Портретная ориентация (portrait)
- Размер бандла критичен (быстрая загрузка)
- Поддержка touch-управления

**Требования к геймплею (Subway Surfers style):**
- Бесконечный раннер (endless runner)
- 3D графика с простыми моделями
- Сбор предметов (энергия) во время бега
- Плавная анимация и движение камеры
- Оптимизация для 60 FPS на средних устройствах

### 2.2 Сравнение движков

#### Вариант 1: Three.js + Vue 3 (РЕКОМЕНДУЕТСЯ)

**Плюсы:**
- ✅ Нативный веб-стек, идеально интегрируется с Vue 3
- ✅ Легковесный (~500KB gzipped)
- ✅ Отличная производительность для простых 3D сцен
- ✅ Большое комьюнити и документация
- ✅ Поддержка WebGL и fallback на Canvas
- ✅ Легко интегрируется с существующим Vue проектом
- ✅ Поддержка touch-событий из коробки
- ✅ Можно использовать готовые библиотеки (cannon.js для физики)

**Минусы:**
- ⚠️ Нужно писать игровую логику самостоятельно
- ⚠️ Меньше готовых решений для игр

**Библиотеки для дополнения:**
- `@react-three/fiber` (но это React) - не подходит
- `troisjs` - Vue 3 wrapper для Three.js (хороший вариант)
- `cannon.js` или `rapier` - физика
- `gsap` - анимации

**Размер бандла:** ~150-200KB (Three.js) + ~50KB (troisjs)

---

#### Вариант 2: Babylon.js

**Плюсы:**
- ✅ Более мощный движок с лучшей производительностью
- ✅ Встроенная физика (Cannon.js интегрирован)
- ✅ Отличные инструменты для разработки
- ✅ Поддержка PBR материалов
- ✅ Лучше для сложных 3D сцен

**Минусы:**
- ⚠️ Тяжелее (~1MB gzipped)
- ⚠️ Сложнее интеграция с Vue (нужны обертки)
- ⚠️ Избыточен для простого раннера
- ⚠️ Больше времени на загрузку

**Размер бандла:** ~800KB-1MB

---

#### Вариант 3: PlayCanvas

**Плюсы:**
- ✅ Специализированный игровой движок
- ✅ Визуальный редактор
- ✅ Хорошая оптимизация

**Минусы:**
- ❌ Платная подписка для коммерческих проектов
- ❌ Сложная интеграция с Vue
- ❌ Избыточен для задачи

---

#### Вариант 4: Phaser 3D (экспериментальный)

**Плюсы:**
- ✅ Легковесный
- ✅ Хорошо для 2D/2.5D игр

**Минусы:**
- ❌ 3D поддержка ограничена
- ❌ Не подходит для полноценного 3D раннера

---

### 2.3 ФИНАЛЬНАЯ РЕКОМЕНДАЦИЯ: Three.js + TroisJS

**Почему Three.js:**
1. Идеальная интеграция с Vue 3 через TroisJS
2. Оптимальный размер бандла для Telegram Mini App
3. Достаточная производительность для раннера
4. Простота разработки и поддержки
5. Можно использовать существующие Vue компоненты для UI

**Стек:**
```javascript
// Основные зависимости
- three (^0.160.0) - основной движок
- troisjs (^0.0.140) - Vue 3 wrapper
- gsap (^3.12.0) - анимации
- cannon-es (^0.20.0) - физика (опционально, для коллизий)
```

---

## 3. АРХИТЕКТУРА ИНТЕГРАЦИИ С БЕКЕНДОМ

### 3.1 Текущий API для сбора энергии

**Эндпоинт:** `POST /tap-energy/`

**Текущая логика:**
1. Проверка throttling (5 req/sec)
2. Проверка перегрева (`overheated_until`)
3. Проверка строительства станции (`is_building()`)
4. Проверка Jarvis активности
5. Расчет энергии на основе `engineer_level` и `kw_per_tap`
6. Обновление `energy`, `storage`, `power`
7. Применение реферальных бонусов
8. Возврат обновленных данных

**Response:**
```json
{
  "message": "Energy updated",
  "energy_added": 0.1,
  "total_energy": 10.5,
  "storage": 9.5,
  "power": 95.0
}
```

### 3.2 Новая логика для 3D геймификации

#### Вариант A: Новый эндпоинт для завершения забега (РЕКОМЕНДУЕТСЯ)

**Эндпоинт:** `POST /game-run-complete/`

**Request:**
```json
{
  "distance": 1250.5,        // Пройденное расстояние
  "energy_collected": 15.3,  // Собранная энергия (клиентская валидация)
  "run_duration": 45.2,      // Длительность забега в секундах
  "obstacles_hit": 2,        // Количество препятствий
  "power_used": 5.0,         // Использованная мощность
  "bonus_multiplier": 1.2    // Множитель бонусов (если есть)
}
```

**Логика на бекенде:**
1. Валидация данных (защита от читерства)
2. Расчет энергии на основе:
   - `distance` (чем дальше - тем больше)
   - `energy_collected` (собранные предметы)
   - `engineer_level` (множитель)
   - `run_duration` (время влияет на бонусы)
3. Применение штрафов за препятствия (`obstacles_hit`)
4. Снижение `power` на основе `power_used`
5. Проверка перегрева (если `power` упал ниже порога)
6. Обновление статистики забегов
7. Возврат результатов

**Response:**
```json
{
  "success": true,
  "energy_gained": 12.5,
  "total_energy": 23.0,
  "storage": 8.5,
  "power": 90.0,
  "overheated_until": null,
  "bonuses": {
    "distance_bonus": 2.0,
    "collection_bonus": 5.3,
    "engineer_bonus": 5.2
  },
  "penalties": {
    "obstacles": -2.0
  }
}
```

**Преимущества:**
- ✅ Одна транзакция вместо множества тапов
- ✅ Меньше нагрузки на сервер
- ✅ Защита от спама тапов
- ✅ Возможность валидации на сервере

**Защита от читерства:**
- Валидация `energy_collected` не должна превышать разумные пределы
- Проверка `run_duration` vs `distance` (физическая валидность)
- Лимит на количество забегов в единицу времени
- Серверная валидация максимально возможной энергии за забег

---

#### Вариант B: Гибридный подход (альтернатива)

**Во время забега:**
- Клиентская симуляция сбора энергии
- Локальное обновление UI
- Нет запросов к серверу

**По завершении забега:**
- Отправка итоговых данных на сервер
- Серверная валидация и расчет
- Обновление состояния пользователя

**Плюсы:**
- Плавный геймплей без задержек
- Меньше нагрузка на сервер
- Лучший UX

**Минусы:**
- Нужна защита от читерства
- Клиентская логика может рассинхронизироваться

---

### 3.3 Новые поля в UserProfile (опционально)

```python
class UserProfile(models.Model):
    # ... существующие поля ...
    
    # Статистика забегов
    total_runs = models.IntegerField(default=0)
    total_distance = models.FloatField(default=0.0)
    best_distance = models.FloatField(default=0.0)
    total_energy_from_runs = models.FloatField(default=0.0)
    last_run_at = models.DateTimeField(null=True, blank=True)
    
    # Настройки геймификации
    game_mode_enabled = models.BooleanField(default=False)  # Переключение режима
```

### 3.4 Интеграция с существующей системой

**Совместимость с текущей механикой:**
- ✅ Сохранение системы тапов как альтернативного способа
- ✅ Использование тех же параметров (`energy`, `storage`, `power`)
- ✅ Применение тех же бустеров и NFT
- ✅ Общая система перегрева и мощности

**Переключение режимов:**
- Добавить настройку в UI для выбора режима:
  - "Классический" (тапы)
  - "3D Забег" (новая геймификация)
- Или автоматическое переключение по завершении забега

---

## 4. СТРУКТУРА КОМПОНЕНТОВ ВО ФРОНТЕНДЕ

### 4.1 Структура файлов

```
src/
├── views/
│   └── GameRunView.vue          # Основной компонент забега
├── components/
│   ├── game/
│   │   ├── GameScene.vue        # Three.js сцена
│   │   ├── Player.vue           # Компонент игрока (инженер)
│   │   ├── Obstacle.vue         # Препятствия
│   │   ├── EnergyCollectible.vue # Собираемые предметы
│   │   ├── GameUI.vue           # UI поверх игры (счет, энергия)
│   │   └── GameControls.vue      # Управление (swipe/tap)
│   └── modals/
│       └── RunCompleteModal.vue # Модалка результатов
├── composables/
│   ├── useGameRun.js            # Логика забега
│   ├── useGamePhysics.js       # Физика и коллизии
│   └── useGameAPI.js            # API запросы
└── stores/
    └── game.js                   # Pinia store для игры
```

### 4.2 Основной компонент GameRunView.vue

```vue
<template>
  <div class="game-run-container">
    <!-- Three.js Canvas -->
    <GameScene 
      ref="gameScene"
      @energy-collected="onEnergyCollected"
      @obstacle-hit="onObstacleHit"
      @run-ended="onRunEnded"
    />
    
    <!-- UI поверх игры -->
    <GameUI 
      :energy="currentEnergy"
      :distance="distance"
      :power="power"
    />
    
    <!-- Управление -->
    <GameControls 
      @swipe-left="swipeLeft"
      @swipe-right="swipeRight"
      @swipe-up="swipeUp"
      @swipe-down="swipeDown"
    />
    
    <!-- Модалка результатов -->
    <RunCompleteModal 
      v-if="showResults"
      :results="runResults"
      @close="handleRunComplete"
    />
  </div>
</template>
```

### 4.3 Интеграция с существующим роутингом

**Добавить в router/index.js:**
```javascript
{
  path: '/game-run',
  name: 'game-run',
  component: () => import('@/views/GameRunView.vue'),
}
```

**Добавить кнопку в EnergizerView.vue:**
- Кнопка "Забег" рядом с основными элементами
- Или замена тапов на забег по настройкам

---

## 5. ГЕЙМПЛЕЙ И МЕХАНИКА

### 5.1 Основная механика забега

**Цель:** Инженер бежит по дорожке, собирает энергию, избегает препятствий

**Управление:**
- Swipe Left/Right - смена полосы (3 полосы)
- Swipe Up - прыжок
- Swipe Down - скольжение (уклонение)

**Сбор энергии:**
- Предметы энергии появляются на дорожке
- При сборе добавляется энергия в локальный счетчик
- Визуальная обратная связь (+X кВт)

**Препятствия:**
- Столкновение снижает `power`
- При `power` < 0 - конец забега
- Визуальная обратная связь (экран трясется, эффект удара)

**Длительность забега:**
- Бесконечный раннер
- Завершается при:
  - Столкновении с препятствием при `power` = 0
  - Ручной остановке пользователем
  - Достижении определенной дистанции (опционально)

### 5.2 Расчет энергии

**Формула (клиентская для предпросмотра):**
```javascript
energyGained = (
  distance * distanceMultiplier +
  energyCollected * collectionMultiplier +
  runDuration * timeBonus
) * engineerMultiplier - obstaclesPenalty
```

**Где:**
- `distanceMultiplier` = 0.01 (1 кВт за 100 единиц расстояния)
- `collectionMultiplier` = 1.0 (1:1 за собранные предметы)
- `timeBonus` = 0.1 (бонус за время)
- `engineerMultiplier` = зависит от `engineer_level` (1.0 - 2.0)
- `obstaclesPenalty` = -2.0 за каждое препятствие

**Серверная валидация:**
- Максимальная энергия за забег = `storage_limit * 2`
- Минимальная энергия = 0
- Проверка разумности `distance` vs `run_duration`

### 5.3 Влияние существующих систем

**Инженеры:**
- Уровень инженера влияет на множитель энергии
- Золотые инженеры дают больший бонус
- Синие инженеры дают временный бонус

**Бустеры:**
- **Repair Kit** - препятствия не снижают `power` (или снижают меньше)
- **Jarvis Bot** - автоматический сбор энергии (опционально)
- **Cryochamber** - защита от перегрева после забега

**Тип станции:**
- Влияет на базовые параметры (`generation_rate`, `storage_limit`)
- Визуально может отображаться в игре

---

## 6. ОПТИМИЗАЦИЯ ПРОИЗВОДИТЕЛЬНОСТИ

### 6.1 Three.js оптимизации

**Геометрия:**
- Использовать простые примитивы (Box, Plane)
- Low-poly модели для инженера и препятствий
- Объединение геометрий (BufferGeometry)

**Материалы:**
- Простые материалы (MeshBasicMaterial или MeshStandardMaterial)
- Избегать сложных шейдеров
- Использовать текстуры низкого разрешения (512x512)

**Рендеринг:**
- Ограничить количество объектов на сцене (pooling)
- Использовать frustum culling
- LOD (Level of Detail) для дальних объектов
- Ограничить количество источников света (1-2)

**Анимации:**
- Использовать GSAP для плавных анимаций
- Анимация через матрицы вместо отдельных свойств
- Object pooling для препятствий и собираемых предметов

### 6.2 Оптимизация для мобильных

**Производительность:**
- Целевой FPS: 60 на средних устройствах, 30 на слабых
- Адаптивное качество графики
- Отключение эффектов на слабых устройствах

**Память:**
- Загрузка ресурсов по требованию
- Очистка неиспользуемых объектов
- Оптимизация текстур (сжатие, размер)

**Батарея:**
- Ограничение частоты обновления при паузе
- Эффективное использование requestAnimationFrame

---

## 7. ПЛАН РЕАЛИЗАЦИИ

### Этап 1: Подготовка (1-2 дня)
- [ ] Установка зависимостей (three, troisjs, gsap)
- [ ] Настройка базовой Three.js сцены
- [ ] Интеграция с Vue компонентами

### Этап 2: Базовый геймплей (3-5 дней)
- [ ] Создание дорожки и камеры
- [ ] Реализация движения инженера
- [ ] Система управления (swipe)
- [ ] Базовые препятствия

### Этап 3: Сбор энергии (2-3 дня)
- [ ] Генерация собираемых предметов
- [ ] Система коллизий
- [ ] Визуальная обратная связь
- [ ] Подсчет собранной энергии

### Этап 4: Интеграция с бекендом (2-3 дня)
- [ ] Создание API эндпоинта `/game-run-complete/`
- [ ] Валидация данных на сервере
- [ ] Расчет энергии и обновление UserProfile
- [ ] Обработка ошибок

### Этап 5: UI и полировка (2-3 дня)
- [ ] UI элементы поверх игры
- [ ] Модалка результатов
- [ ] Интеграция с существующим UI
- [ ] Анимации и эффекты

### Этап 6: Тестирование и оптимизация (2-3 дня)
- [ ] Тестирование на разных устройствах
- [ ] Оптимизация производительности
- [ ] Багфиксы
- [ ] Балансировка геймплея

**Общее время:** 12-19 дней разработки

---

## 8. РИСКИ И МИТИГАЦИЯ

### 8.1 Технические риски

**Риск:** Низкая производительность на слабых устройствах
**Митигация:** 
- Адаптивное качество графики
- Оптимизация рендеринга
- Fallback на упрощенную версию

**Риск:** Большой размер бандла
**Митигация:**
- Lazy loading компонентов игры
- Оптимизация текстур и моделей
- Code splitting

**Риск:** Проблемы с WebView в Telegram
**Митигация:**
- Тестирование на реальных устройствах
- Fallback на 2D версию при проблемах

### 8.2 Игровые риски

**Риск:** Читерство (модификация клиентского кода)
**Митигация:**
- Серверная валидация всех данных
- Лимиты на максимальную энергию
- Проверка физической валидности (distance vs time)

**Риск:** Дисбаланс экономики
**Митигация:**
- Тестирование с реальными пользователями
- Настройка множителей через админку
- A/B тестирование

**Риск:** Пользователи предпочтут старую систему тапов
**Митигация:**
- Сделать оба режима доступными
- Дать выбор пользователю
- Возможно, сделать забег более выгодным

---

## 9. ДОПОЛНИТЕЛЬНЫЕ ВОЗМОЖНОСТИ

### 9.1 Социальные функции
- Лидерборды по дистанции
- Ежедневные челленджи
- Достижения за забеги

### 9.2 Монетизация
- Бустеры для забегов (увеличение скорости, защита)
- Скины для инженера
- Специальные трассы (премиум)

### 9.3 Прогрессия
- Разблокировка новых типов забегов
- Улучшение характеристик инженера
- Специальные события

---

## 10. ЗАКЛЮЧЕНИЕ

**Рекомендуемый стек:**
- **Three.js** + **TroisJS** для 3D рендеринга
- **GSAP** для анимаций
- **Vue 3 Composition API** для логики

**Рекомендуемый подход к интеграции:**
- Новый эндпоинт `/game-run-complete/` для завершения забега
- Серверная валидация всех данных
- Сохранение совместимости с текущей системой тапов

**Приоритеты:**
1. Базовый геймплей и интеграция с бекендом
2. Оптимизация производительности
3. Полировка UI/UX
4. Дополнительные функции

**Ожидаемый результат:**
- Увлекательная 3D геймификация вместо монотонных тапов
- Увеличение вовлеченности пользователей
- Сохранение баланса экономики игры
- Совместимость с существующими системами

---

## ПРИЛОЖЕНИЯ

### A. Пример кода GameScene.vue (базовая структура)

```vue
<template>
  <div ref="container" class="game-scene-container"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Scene, PerspectiveCamera, WebGLRenderer, AmbientLight, DirectionalLight } from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

const container = ref(null)
let scene, camera, renderer, controls

onMounted(() => {
  // Инициализация сцены
  scene = new Scene()
  
  // Камера
  camera = new PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000)
  camera.position.set(0, 5, 10)
  
  // Рендерер
  renderer = new WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(window.innerWidth, window.innerHeight)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  container.value.appendChild(renderer.domElement)
  
  // Освещение
  const ambientLight = new AmbientLight(0xffffff, 0.6)
  scene.add(ambientLight)
  
  const directionalLight = new DirectionalLight(0xffffff, 0.8)
  directionalLight.position.set(5, 10, 5)
  scene.add(directionalLight)
  
  // Анимационный цикл
  const animate = () => {
    requestAnimationFrame(animate)
    renderer.render(scene, camera)
  }
  animate()
})

onUnmounted(() => {
  if (renderer) {
    renderer.dispose()
  }
})
</script>
```

### B. Пример API эндпоинта (Django)

```python
class GameRunCompleteView(APIView):
    @swagger_auto_schema(
        tags=["game"],
        operation_description="Завершение 3D забега и начисление энергии",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["distance", "energy_collected", "run_duration"],
            properties={
                "distance": openapi.Schema(type=openapi.TYPE_NUMBER),
                "energy_collected": openapi.Schema(type=openapi.TYPE_NUMBER),
                "run_duration": openapi.Schema(type=openapi.TYPE_NUMBER),
                "obstacles_hit": openapi.Schema(type=openapi.TYPE_INTEGER),
                "power_used": openapi.Schema(type=openapi.TYPE_NUMBER),
            },
        ),
    )
    @require_auth
    def post(self, request):
        user_profile = request.user_profile
        
        # Валидация данных
        distance = float(request.data.get("distance", 0))
        energy_collected = float(request.data.get("energy_collected", 0))
        run_duration = float(request.data.get("run_duration", 0))
        obstacles_hit = int(request.data.get("obstacles_hit", 0))
        power_used = float(request.data.get("power_used", 0))
        
        # Защита от читерства
        max_energy_per_run = float(user_profile.storage_limit) * 2
        if energy_collected > max_energy_per_run:
            return Response(
                {"error": "Energy collected exceeds maximum"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Расчет энергии
        distance_bonus = distance * 0.01
        collection_bonus = energy_collected
        engineer_multiplier = 1.0 + (user_profile.engineer_level * 0.02)
        obstacles_penalty = obstacles_hit * 2.0
        
        total_energy = (
            (distance_bonus + collection_bonus) * engineer_multiplier - obstacles_penalty
        )
        total_energy = max(0, min(total_energy, max_energy_per_run))
        
        # Обновление профиля
        UserProfile.objects.filter(id=user_profile.id).update(
            energy=F("energy") + total_energy,
            power=F("power") - power_used,
            total_runs=F("total_runs") + 1,
            total_distance=F("total_distance") + distance,
            best_distance=Case(
                When(best_distance__lt=distance, then=distance),
                default=F("best_distance")
            ),
            total_energy_from_runs=F("total_energy_from_runs") + total_energy,
            last_run_at=timezone.now()
        )
        
        user_profile.refresh_from_db()
        
        return Response({
            "success": True,
            "energy_gained": total_energy,
            "total_energy": float(user_profile.energy),
            "power": float(user_profile.power),
            "bonuses": {
                "distance_bonus": distance_bonus,
                "collection_bonus": collection_bonus,
                "engineer_multiplier": engineer_multiplier
            }
        })
```

---

**Конец документа**
