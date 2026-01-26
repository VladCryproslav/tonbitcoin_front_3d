# Инструкция по добавлению 3D моделей

## Шаг 1: Скачайте модель

1. Перейдите на один из сайтов:
   - https://sketchfab.com (фильтр: Free Download, GLTF/GLB)
   - https://quaternius.com
   - https://www.mixamo.com

2. Скачайте модель в формате **GLB** (предпочтительно) или **GLTF**

3. Примеры поиска:
   - "low poly runner character"
   - "cartoon character glb"
   - "game character free"

## Шаг 2: Разместите модель

Создайте папку и поместите модель:

```
public/
  models/
    player/
      character.glb
```

Или:

```
src/
  assets/
    models/
      character.glb
```

## Шаг 3: Используйте в коде

### Вариант 1: Автоматическая загрузка при создании игрока

В `GameRunView.vue` измените:

```javascript
// Вместо:
gamePhysics.value.createPlayer(scene)

// Используйте:
gamePhysics.value.createPlayer(scene, '/models/player/character.glb')
```

### Вариант 2: Загрузка отдельно

```javascript
// После создания сцены
await gamePhysics.value.loadPlayerModel(scene, '/models/player/character.glb')
```

## Шаг 4: Настройка масштаба и позиции

Если модель слишком большая/маленькая, в `useGamePhysics.js`:

```javascript
model.scale.set(0.5, 0.5, 0.5) // Уменьшить в 2 раза
model.position.set(0, -1, 0) // Сместить вниз
```

## Анимации

Если модель содержит анимации:
- Анимация "run" или "walk" будет автоматически проигрываться
- Для других анимаций можно добавить в код:

```javascript
// В loadPlayerModel после mixer = new AnimationMixer(model)
const jumpAnim = gltf.animations.find(anim => anim.name.includes('jump'))
if (jumpAnim) {
  // Сохранить для использования при прыжке
}
```

## Рекомендации

1. **Размер файла**: Старайтесь использовать модели < 2MB для быстрой загрузки
2. **Полигоны**: Low poly модели лучше для производительности
3. **Текстуры**: Убедитесь, что текстуры включены в GLB файл
4. **Тестирование**: Проверьте модель в браузере перед использованием

## Примеры готовых моделей

### Mixamo (рекомендуется)
1. Зайдите на https://www.mixamo.com
2. Выберите персонажа
3. Выберите анимацию "Running"
4. Экспорт: Format = glTF, Pose = T-Pose, Format = Binary (.glb)
5. Скачайте и используйте

### Quaternius Universal Base
1. https://quaternius.com/packs/universalbasecharacters.html
2. Скачайте пак (бесплатно)
3. Используйте файлы из папки `gltf/`
