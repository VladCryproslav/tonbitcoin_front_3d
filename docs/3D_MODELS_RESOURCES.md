# Ресурсы для 3D моделей

## Бесплатные сайты с 3D моделями

### 1. **Sketchfab** (https://sketchfab.com)
- Огромная коллекция моделей
- Фильтр по лицензии (CC0, CC-BY - бесплатные)
- Форматы: GLTF, GLB, OBJ, FBX
- Поиск: "runner character", "game character", "low poly character"

### 2. **Quaternius** (https://quaternius.com)
- Бесплатные игровые модели (CC0 лицензия)
- Universal Base Characters - 26 готовых персонажей
- Форматы: GLTF, FBX, OBJ
- Анимации включены

### 3. **itch.io** (https://itch.io/game-assets/free/tag-3d-model)
- Множество бесплатных 3D моделей
- Фильтр по форматам (GLTF, GLB)
- Часто с анимациями

### 4. **3D Model Free** (https://3d-model.org)
- Бесплатные модели в разных форматах
- Категории: Characters, People, Animals

### 5. **Poly Haven** (https://polyhaven.com/models)
- Высококачественные бесплатные модели
- CC0 лицензия

### 6. **Mixamo** (https://www.mixamo.com) - от Adobe
- Бесплатные персонажи с анимациями
- Автоматическая риггинг
- Экспорт в GLTF/GLB

### 7. **Kenney Assets** (https://kenney.nl/assets)
- Бесплатные игровые ассеты
- Low poly стиль
- Много персонажей и объектов

## Рекомендуемые форматы для Three.js

1. **GLB** (бинарный GLTF) - лучший выбор
   - Один файл (модель + текстуры)
   - Быстрая загрузка
   - Поддержка анимаций

2. **GLTF** (JSON формат)
   - Текстовый формат
   - Легко редактировать
   - Может требовать отдельные текстуры

3. **FBX** - нужно конвертировать в GLTF/GLB

## Как использовать модели в игре

1. Скачайте модель в формате GLB или GLTF
2. Поместите в `public/models/` или `src/assets/models/`
3. Используйте GLTFLoader для загрузки (уже реализовано)

## Примеры поиска

- "low poly runner character gltf"
- "game character glb free"
- "subway surfers style character"
- "cartoon runner 3d model"

## Лицензии

- **CC0** - можно использовать без ограничений
- **CC-BY** - нужно указать автора
- **CC-BY-SA** - можно использовать с указанием автора
- Всегда проверяйте лицензию перед использованием!
