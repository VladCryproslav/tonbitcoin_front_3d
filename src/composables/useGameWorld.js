import { ref } from 'vue'
import {
  BoxGeometry,
  MeshStandardMaterial,
  Mesh,
  Vector3,
  PlaneGeometry,
  Group,
  Color,
  Box3
} from 'three'

export function useGameWorld(scene, camera) {
  // Длина одного сегмента дороги и количество сегментов.
  // Чуть увеличены, чтобы дорога рисовалась дальше без разрывов.
  const roadLength = 25
  const segmentCount = 7
  const roadSegments = ref([])
  const obstacles = ref([])
  const collectibles = ref([])
  const roadSpeed = ref(0.3)
  const lanes = [-2, 0, 2] // Позиции полос (левая, центр, правая)

  // Секции дороги: меньше дистанция — спавн чаще
  const SECTION_SPACING = 4 // мин. «расстояние» (по playerZ) между секциями
  const SECTION_WORLD_LENGTH = 14
  let lastSpawnPlayerZ = -999
  let nextSectionWorldZ = -48

  const laneMarkings = ref([])

  // 4 типа: нет преграды, непроходимая (кувырок), прыжок, кувырок (свайп вниз)
  const OBSTACLE_KIND = { NONE: 'none', IMPASSABLE: 'impassable', JUMP: 'jump', ROLL: 'roll' }
  // ROLL: высота как у непроходимого (2.5), бар чуть опущен (зазор снизу ~1.2)
  const OBSTACLE_DEF = {
    [OBSTACLE_KIND.NONE]: null,
    [OBSTACLE_KIND.IMPASSABLE]: { height: 2.5, color: 0xDE2126, name: 'impassable' },
    [OBSTACLE_KIND.JUMP]: { height: 0.9, color: 0xEB7D26, name: 'jump' },
    [OBSTACLE_KIND.ROLL]: { height: 2.5, bottomY: 1.2, color: 0x2288CC, name: 'roll' }
  }
  // Пустых меньше при разгоне: в начале NONE 32–35%, с ростом скорости −5..10%
  const NONE_BASE = 33
  const NONE_SPEED_PENALTY_MAX = 10
  const OBSTACLE_SHARES = [
    { kind: OBSTACLE_KIND.JUMP, share: 23 },
    { kind: OBSTACLE_KIND.ROLL, share: 23 },
    { kind: OBSTACLE_KIND.IMPASSABLE, share: 22 }
  ]
  const OBSTACLE_TOTAL_SHARE = OBSTACLE_SHARES.reduce((s, o) => s + o.share, 0)

  function pickObstacleKind() {
    const speed = roadSpeed.value
    const nonePenalty = Math.min(
      NONE_SPEED_PENALTY_MAX,
      Math.max(0, (speed - 0.15) * 55)
    )
    const noneWeight = Math.max(23, NONE_BASE - nonePenalty)
    let r = Math.random() * 100
    if (r < noneWeight) return OBSTACLE_KIND.NONE
    r = (r - noneWeight) / (100 - noneWeight)
    for (const { kind, share } of OBSTACLE_SHARES) {
      const w = share / OBSTACLE_TOTAL_SHARE
      r -= w
      if (r <= 0) return kind
    }
    return OBSTACLE_KIND.IMPASSABLE
  }

  // Создание фона
  const createBackground = () => {
    // Небо - яркие цвета Subway Surfers (голубое небо)
    for (let i = 0; i < 3; i++) {
      const skyGeometry = new PlaneGeometry(50, 30)
      const skyColor = new Color()
      // Яркое голубое небо как в Subway Surfers
      skyColor.setHSL(0.55, 0.5, 0.75 + i * 0.08) // Более насыщенный и яркий
      const skyMaterial = new MeshStandardMaterial({
        color: skyColor,
        side: 2, // DoubleSide
        flatShading: true
      })
      const sky = new Mesh(skyGeometry, skyMaterial)
      sky.position.set(0, 15 - i * 5, -20 - i * 10)
      sky.rotation.x = -Math.PI / 3
      scene.add(sky)
    }

    // Боковые барьеры - яркие цвета Subway Surfers
    const barrierGeometry = new BoxGeometry(0.5, 2.5, 200)
    const barrierMaterial = new MeshStandardMaterial({
      color: 0x666666, // Светлее для cartoon стиля
      metalness: 0.1,
      roughness: 0.9,
      flatShading: true
    })

    // Левый барьер
    const leftBarrier = new Mesh(barrierGeometry, barrierMaterial)
    leftBarrier.position.set(-3.5, 1.25, 0)
    scene.add(leftBarrier)

    // Правый барьер
    const rightBarrier = new Mesh(barrierGeometry, barrierMaterial)
    rightBarrier.position.set(3.5, 1.25, 0)
    scene.add(rightBarrier)

    // Декоративные элементы на барьерах - яркие цвета Subway Surfers
    for (let i = 0; i < 10; i++) {
      const markerGeometry = new BoxGeometry(0.1, 0.3, 0.1)
      const colors = [0xFEFF28, 0xEB7D26, 0xDE2126] // Желтый, оранжевый, красный
      const color = colors[i % colors.length]
      const markerMaterial = new MeshStandardMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: 0.2,
        flatShading: true
      })

      // Левый барьер
      const leftMarker = new Mesh(markerGeometry, markerMaterial)
      leftMarker.position.set(-3.5, 2, -i * 5)
      scene.add(leftMarker)

      // Правый барьер
      const rightMarker = new Mesh(markerGeometry, markerMaterial)
      rightMarker.position.set(3.5, 2, -i * 5)
      scene.add(rightMarker)
    }
  }

  // Создание дорожки
  const createRoad = () => {
    createBackground()
    const roadWidth = 6

    for (let i = 0; i < segmentCount; i++) {
      const roadGeometry = new PlaneGeometry(roadWidth, roadLength)
      const roadMaterial = new MeshStandardMaterial({
        color: 0x2A2A2A, // Темно-серый асфальт
        roughness: 0.9,
        flatShading: true // Cartoon стиль
      })
      const road = new Mesh(roadGeometry, roadMaterial)
      road.rotation.x = -Math.PI / 2
      road.position.z = -i * roadLength
      road.position.y = 0
      scene.add(road)
      roadSegments.value.push(road)
    }

    // Разметка полос
    createLaneMarkings()
  }

  // Разметка полос
  const createLaneMarkings = () => {
    const markingLength = 2
    const markingWidth = 0.1

    // Увеличиваем диапазон разметки по Z, чтобы дорога рисовалась дальше.
    for (let z = -80; z < 15; z += markingLength * 2) {
      lanes.forEach(laneX => {
        const markingGeometry = new BoxGeometry(markingWidth, 0.01, markingLength)
        const markingMaterial = new MeshStandardMaterial({
          color: 0xFEFF28, // Яркий желтый Subway Surfers
          emissive: 0xFEFF28,
          emissiveIntensity: 0.3,
          flatShading: true
        })
        const marking = new Mesh(markingGeometry, markingMaterial)
        marking.position.set(laneX, 0.01, z)
        marking.userData = { type: 'marking' }
        scene.add(marking)
        laneMarkings.value.push(marking)
      })
    }
  }

  // Обновление разметки
  const updateLaneMarkings = () => {
    const markingLength = 2
    laneMarkings.value.forEach(marking => {
      marking.position.z += roadSpeed.value

      // Перемещаем разметку вперед
      if (marking.position.z > 10) {
        const sameLaneMarkings = laneMarkings.value.filter(
          m => Math.abs(m.position.x - marking.position.x) < 0.1
        )
        if (sameLaneMarkings.length > 0) {
          const lastMarking = sameLaneMarkings.reduce(
            (min, m) => m.position.z < min.position.z ? m : min,
            marking
          )
          // Небольшое перекрытие (‑0.05) чтобы не было видимого разрыва разметки.
          marking.position.z = lastMarking.position.z - markingLength * 2 + 0.05
        } else {
          marking.position.z = -50
        }
      }
    })
  }

  // Создание препятствия по типу: jump (прыжок), roll (кувырок), impassable (непроходимая — кувырок)
  const createObstacle = (lane, z, kind) => {
    const def = OBSTACLE_DEF[kind]
    if (!def) return null
    const obstacleGeometry = new BoxGeometry(1, def.height, 1)
    const obstacleMaterial = new MeshStandardMaterial({
      color: def.color,
      metalness: 0.1,
      roughness: 0.9,
      flatShading: true
    })
    const obstacle = new Mesh(obstacleGeometry, obstacleMaterial)
    const posY = def.bottomY != null ? def.bottomY + def.height / 2 : def.height / 2
    obstacle.position.set(lanes[lane], posY, z)
    obstacle.userData = { type: 'obstacle', lane, height: def.height, kind }
    obstacle.castShadow = true
    scene.add(obstacle)
    obstacles.value.push(obstacle)
    return obstacle
  }

  // Создание собираемого предмета (энергия)
  const createCollectible = (lane, z) => {
    // Создаем группу для вращения
    const group = new Group()

    // Основной куб энергии
    const collectibleGeometry = new BoxGeometry(0.6, 0.6, 0.6)
    const collectibleMaterial = new MeshStandardMaterial({
      color: 0x00FF00,
      emissive: 0x00FF00,
      emissiveIntensity: 0.8,
      transparent: true,
      opacity: 0.9
    })
    const collectible = new Mesh(collectibleGeometry, collectibleMaterial)
    group.add(collectible)

    // Внутреннее свечение
    const innerGeometry = new BoxGeometry(0.4, 0.4, 0.4)
    const innerMaterial = new MeshStandardMaterial({
      color: 0xFFFFFF,
      emissive: 0xFFFFFF,
      emissiveIntensity: 1
    })
    const inner = new Mesh(innerGeometry, innerMaterial)
    group.add(inner)

    group.position.set(lanes[lane], 1, z)
    group.userData = { type: 'collectible', lane, collected: false }
    scene.add(group)
    collectibles.value.push(group)
    return group
  }

  // Генерация по секциям: дорога — прямоугольники, каждый прямоугольник — 3 сектора (полосы).
  // В каждом секторе один из 4 типов: нет преграды, непроходимая (кувырок), прыжок, кувырок.
  // Правило: три в ряд непроходимых (IMPASSABLE) быть не может — максимум 2 в секции.
  // Между секциями — минимальное расстояние SECTION_SPACING по playerZ.
  const spawnObjects = (playerZ) => {
    if (playerZ - lastSpawnPlayerZ < SECTION_SPACING) return

    lastSpawnPlayerZ = playerZ
    const sectionZ = nextSectionWorldZ
    nextSectionWorldZ -= SECTION_WORLD_LENGTH

    const kinds = []
    for (let lane = 0; lane < 3; lane++) {
      let kind = pickObstacleKind()
      kinds.push(kind)
    }
    // Не допускаем три IMPASSABLE в ряд: заменяем один на NONE
    const impassableCount = kinds.filter(k => k === OBSTACLE_KIND.IMPASSABLE).length
    if (impassableCount >= 3) {
      const idx = kinds.findIndex(k => k === OBSTACLE_KIND.IMPASSABLE)
      kinds[idx] = OBSTACLE_KIND.NONE
    }

    for (let lane = 0; lane < 3; lane++) {
      const kind = kinds[lane]
      if (kind !== OBSTACLE_KIND.NONE) {
        createObstacle(lane, sectionZ, kind)
      }
    }

    // Собираемые предметы: чаще спавн и иногда два за секцию
    const collectibleChance = 0.72
    if (Math.random() < collectibleChance) {
      const lane = Math.floor(Math.random() * 3)
      const collectibleZ = sectionZ - 5 - Math.random() * 8
      createCollectible(lane, collectibleZ)
    }
    if (Math.random() < 0.35) {
      const lane = Math.floor(Math.random() * 3)
      const collectibleZ = sectionZ - 3 - Math.random() * 6
      createCollectible(lane, collectibleZ)
    }
  }

  // Обновление дорожки (бесконечная прокрутка)
  const updateRoad = (playerZ) => {
    roadSegments.value.forEach((segment, index) => {
      segment.position.z += roadSpeed.value

      // Перемещаем сегмент вперед только когда он ушёл ДАЛЕКО за камеру,
      // чтобы дорога пропадала уже вне поля зрения.
      const cameraZ = camera ? camera.position.z : 8
      const cutoffZ = cameraZ + roadLength * 1.5
      if (segment.position.z > cutoffZ) {
        const lastSegment = roadSegments.value.reduce((min, seg) =>
          seg.position.z < min.position.z ? seg : min
        )
        // Небольшое перекрытие (‑0.1) между сегментами,
        // чтобы даже при накоплении float‑ошибок не было щели.
        segment.position.z = lastSegment.position.z - roadLength + 0.1
      }
    })

    // Обновляем разметку
    updateLaneMarkings()
  }

  // Окно неуязвимости к синему блоку (мс): после свайпа вниз не бьём по ROLL, не зависим от порядка rAF.
  const ROLL_IMMUNE_MS = 950

  // Обновление препятствий.
  // Коллизия через AABB (Box3). ROLL: не бьём при isSliding, по высоте (underBar) или в окне по времени.
  const updateObstacles = (playerBox, onCollision, isSliding = false, slideStartTime = 0) => {
    const obstaclesToRemove = []
    const inRollImmuneWindow = slideStartTime > 0 && Date.now() - slideStartTime < ROLL_IMMUNE_MS

    // Зона, где возможна коллизия с игроком (игрок условно у z≈0, препятствия едут к +z)
    const COLLIDE_Z_MIN = -24
    const COLLIDE_Z_MAX = 5

    obstacles.value.forEach((obstacle, index) => {
      obstacle.position.z += roadSpeed.value

      const inCollideZone = obstacle.position.z >= COLLIDE_Z_MIN && obstacle.position.z <= COLLIDE_Z_MAX

      if (playerBox && inCollideZone) {
        const kind = obstacle.userData.kind
        const obstacleBox = obstacle.userData.box || (obstacle.userData.box = new Box3())
        obstacleBox.setFromObject(obstacle)

        if (kind === OBSTACLE_KIND.ROLL) {
          // Синий блок: не бьём при кувырке, по высоте под баром или в окне неуязвимости по времени.
          const underBar = playerBox.max.y < obstacleBox.min.y + 0.4
          const safeFromRoll = isSliding || underBar || inRollImmuneWindow
          if (!safeFromRoll && !obstacle.userData.hit && playerBox.intersectsBox(obstacleBox)) {
            obstacle.userData.hit = true
            onCollision(obstacle)
            return
          }
        } else {
          if (!obstacle.userData.hit && playerBox.intersectsBox(obstacleBox)) {
            obstacle.userData.hit = true
            onCollision(obstacle)
            return
          }
        }
      }

      if (obstacle.position.z > 10) {
        // Удаление ушедших препятствий (которые игрок не задел).
        obstaclesToRemove.push(index)
        scene.remove(obstacle)
      }
    })

    // Удаляем в обратном порядке чтобы индексы не сбились
    obstaclesToRemove.sort((a, b) => b - a).forEach(index => {
      obstacles.value.splice(index, 1)
    })
  }

  // Обновление собираемых предметов
  // Аналогично препятствиям, используем реальные AABB.
  const updateCollectibles = (playerBox, onCollect) => {
    const collectiblesToRemove = []

    collectibles.value.forEach((collectible, index) => {
      if (collectible.userData.collected) {
        collectiblesToRemove.push(index)
        return
      }

      collectible.position.z += roadSpeed.value
      collectible.rotation.y += 0.05
      collectible.rotation.x += 0.03

      // Пульсация для привлечения внимания
      const pulse = 1 + Math.sin(Date.now() * 0.01) * 0.15
      collectible.scale.setScalar(pulse)

      // Вертикальное движение
      collectible.position.y = 1 + Math.sin(Date.now() * 0.005) * 0.3

      if (playerBox) {
        const collBox = collectible.userData.box || (collectible.userData.box = new Box3())
        collBox.setFromObject(collectible)

        if (playerBox.intersectsBox(collBox)) {
          collectible.userData.collected = true
          // Мгновенно убираем объект с экрана, даже до remove,
          // чтобы он гарантированно не "ехал" с игроком один-два кадра.
          collectible.visible = false
          collectible.position.y = -9999
          collectible.position.z = -9999

          onCollect(0.5) // Количество энергии
          collectiblesToRemove.push(index)
          scene.remove(collectible)
          return
        }
      }

      if (collectible.position.z > 10) {
        // Удаление ушедших предметов
        collectiblesToRemove.push(index)
        scene.remove(collectible)
      }
    })

    // Удаляем в обратном порядке
    collectiblesToRemove.sort((a, b) => b - a).forEach(index => {
      collectibles.value.splice(index, 1)
    })
  }

  // Очистка всех объектов
  const clearAll = () => {
    obstacles.value.forEach(obstacle => scene.remove(obstacle))
    collectibles.value.forEach(collectible => scene.remove(collectible))
    obstacles.value = []
    collectibles.value = []
    lastSpawnPlayerZ = -999
    nextSectionWorldZ = -48
  }

  // Обновление скорости дороги
  const setRoadSpeed = (speed) => {
    roadSpeed.value = speed
  }

  return {
    createRoad,
    spawnObjects,
    updateRoad,
    updateObstacles,
    updateCollectibles,
    clearAll,
    setRoadSpeed,
    roadSpeed
  }
}
