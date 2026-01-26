# Three.js Game Setup - Инструкция

## Установленные зависимости

- **three** - основной 3D движок
- **troisjs** - Vue 3 wrapper для Three.js (опционально, можно использовать напрямую)
- **gsap** - библиотека для анимаций
- **cannon-es** - физический движок (опционально)

## Структура файлов

```
src/
├── components/
│   └── game/
│       ├── GameScene.vue          # Основная Three.js сцена
│       ├── GameUI.vue              # UI элементы поверх игры
│       ├── GameControls.vue        # Обработка свайпов и тапов
│       └── RunCompleteModal.vue    # Модалка результатов забега
├── composables/
│   ├── useGameRun.js              # Логика забега и API интеграция
│   ├── useGamePhysics.js          # Физика и управление игроком
│   └── useGameAPI.js              # API запросы
└── views/
    └── GameRunView.vue            # Главный компонент игры
```

## Использование

### Запуск игры

Игра доступна по роуту `/game-run`. Можно добавить кнопку в `GameSelectionView.vue`:

```vue
<router-link to="/game-run" class="game-card">
  <h2>3D Забег</h2>
</router-link>
```

### Базовый пример использования GameScene

```vue
<template>
  <GameScene 
    @scene-ready="onSceneReady"
  />
</template>

<script setup>
import GameScene from '@/components/game/GameScene.vue'

const onSceneReady = ({ scene, camera, renderer }) => {
  // Здесь можно добавить объекты в сцену
  // Например, создать дорожку, препятствия и т.д.
}
</script>
```

## Следующие шаги

1. **Создание дорожки** - добавить бесконечную дорожку с текстурами
2. **Модель игрока** - создать/загрузить модель инженера
3. **Препятствия** - добавить систему генерации препятствий
4. **Собираемые предметы** - добавить предметы энергии
5. **Анимации** - использовать GSAP для плавных переходов
6. **Оптимизация** - настройка производительности для мобильных устройств

## API интеграция

Для работы игры нужен бекенд эндпоинт `POST /game-run-complete/` который принимает:

```json
{
  "distance": 1250.5,
  "energy_collected": 15.3,
  "run_duration": 45.2,
  "obstacles_hit": 2,
  "power_used": 5.0,
  "bonus_multiplier": 1.2
}
```

И возвращает:

```json
{
  "success": true,
  "energy_gained": 12.5,
  "total_energy": 23.0,
  "storage": 8.5,
  "power": 90.0,
  "bonuses": {
    "distance_bonus": 2.0,
    "collection_bonus": 5.3
  }
}
```

## Производительность

Для оптимизации на мобильных устройствах:

1. Используйте простые геометрии (Box, Plane)
2. Ограничьте количество объектов на сцене
3. Используйте object pooling для препятствий
4. Настройте адаптивное качество графики
5. Ограничьте FPS на слабых устройствах

## Документация

- [Three.js Documentation](https://threejs.org/docs/)
- [GSAP Documentation](https://greensock.com/docs/)
- [TroisJS Documentation](https://troisjs.github.io/)
