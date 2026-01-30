import { ref } from 'vue'
import {
  BoxGeometry,
  MeshStandardMaterial,
  Mesh,
  PlaneGeometry,
  Group,
  Color
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

  // Общая геометрия и материал для разметки полос (один draw call на тип, меньше памяти).
  // Логику спавна/телепорта не меняем: разметка движется только в updateLaneMarkings с roadSpeed.
  const MARKING_LENGTH = 2
  const MARKING_WIDTH = 0.1
  const sharedMarkingGeometry = new BoxGeometry(MARKING_WIDTH, 0.01, MARKING_LENGTH)
  const sharedMarkingMaterial = new MeshStandardMaterial({
    color: 0xFEFF28,
    emissive: 0xFEFF28,
    emissiveIntensity: 0.3,
    flatShading: true
  })

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

  // Общая геометрия и материалы препятствий. ROLL — отдельная геометрия 2.5, чтобы не было артефакта «появление сверху вниз» при shared с IMPASSABLE.
  const sharedObstacleGeometry = {
    0.9: new BoxGeometry(1, 0.9, 1),
    2.5: new BoxGeometry(1, 2.5, 1),
    roll: new BoxGeometry(1, 2.5, 1)
  }
  const sharedObstacleMaterial = {
    [OBSTACLE_KIND.IMPASSABLE]: new MeshStandardMaterial({
      color: 0xDE2126,
      metalness: 0.1,
      roughness: 0.9,
      flatShading: true
    }),
    [OBSTACLE_KIND.JUMP]: new MeshStandardMaterial({
      color: 0xEB7D26,
      metalness: 0.1,
      roughness: 0.9,
      flatShading: true
    }),
    [OBSTACLE_KIND.ROLL]: new MeshStandardMaterial({
      color: 0x2288CC,
      metalness: 0.1,
      roughness: 0.9,
      flatShading: true
    })
  }

  // Глобальная зона по Z, где вообще возможна коллизия с игроком
  // (игрок условно у z≈0, препятствия/коллекты едут к +z).
  const COLLIDE_Z_MIN = -24
  const COLLIDE_Z_MAX = 5

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

  // Фон создаём один раз; при повторном createRoad только дорога и разметка пересоздаются.
  let backgroundCreated = false
  const createBackground = () => {
    if (backgroundCreated) return
    backgroundCreated = true
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

  // Разметка полос. Одна геометрия и один материал на все меши — логика спавна по Z и полосам та же.
  // Обновление только в updateLaneMarkings (вызов из updateRoad), одна скорость roadSpeed — без «двух шаров».
  const createLaneMarkings = () => {
    const stepZ = MARKING_LENGTH * 2
    for (let z = -80; z < 15; z += stepZ) {
      lanes.forEach(laneX => {
        const marking = new Mesh(sharedMarkingGeometry, sharedMarkingMaterial)
        marking.position.set(laneX, 0.01, z)
        marking.userData = { type: 'marking' }
        scene.add(marking)
        laneMarkings.value.push(marking)
      })
    }
  }

  // Обновление разметки: двигаем с roadSpeed, ушедшие (z>10) телепортируем за хвост полосы.
  // Два прохода вместо трёх; логика та же — одна скорость, один массив, без расслоения «два шара».
  const updateLaneMarkings = () => {
    const minZByLane = {}
    const speed = roadSpeed.value
    const stepZ = MARKING_LENGTH * 2
    laneMarkings.value.forEach(marking => {
      marking.position.z += speed
      if (marking.position.z <= 10) {
        const laneKey = Math.round(marking.position.x * 10) / 10
        const z = marking.position.z
        if (minZByLane[laneKey] === undefined || z < minZByLane[laneKey]) {
          minZByLane[laneKey] = z
        }
      }
    })
    laneMarkings.value.forEach(marking => {
      if (marking.position.z > 10) {
        const laneKey = Math.round(marking.position.x * 10) / 10
        const minZ = minZByLane[laneKey]
        marking.position.z = minZ !== undefined ? minZ - stepZ + 0.05 : -50
      }
    })
  }

  // Создание препятствия по типу: jump (прыжок), roll (кувырок), impassable (непроходимая — кувырок)
  const createObstacle = (lane, z, kind) => {
    const def = OBSTACLE_DEF[kind]
    if (!def) return null
    const geo = kind === OBSTACLE_KIND.ROLL ? sharedObstacleGeometry.roll : sharedObstacleGeometry[def.height]
    const obstacle = new Mesh(geo, sharedObstacleMaterial[kind])
    const posY = def.bottomY != null ? def.bottomY + def.height / 2 : def.height / 2
    obstacle.position.set(lanes[lane], posY, z)
    obstacle.userData = { type: 'obstacle', lane, height: def.height, kind }
    obstacle.castShadow = true
    obstacle.renderOrder = 1
    scene.add(obstacle)
    obstacle.updateMatrixWorld(true)
    obstacles.value.push(obstacle)
    return obstacle
  }

  // Общая геометрия и материалы коллектов (внешний куб 0.6, внутренний 0.4).
  const sharedCollectibleOuterGeo = new BoxGeometry(0.6, 0.6, 0.6)
  const sharedCollectibleOuterMat = new MeshStandardMaterial({
    color: 0x00FF00,
    emissive: 0x00FF00,
    emissiveIntensity: 0.8,
    transparent: true,
    opacity: 0.9
  })
  const sharedCollectibleInnerGeo = new BoxGeometry(0.4, 0.4, 0.4)
  const sharedCollectibleInnerMat = new MeshStandardMaterial({
    color: 0xFFFFFF,
    emissive: 0xFFFFFF,
    emissiveIntensity: 1
  })

  // Создание собираемого предмета (энергия)
  const createCollectible = (lane, z) => {
    const group = new Group()
    const collectible = new Mesh(sharedCollectibleOuterGeo, sharedCollectibleOuterMat)
    group.add(collectible)
    const inner = new Mesh(sharedCollectibleInnerGeo, sharedCollectibleInnerMat)
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

  // Обновление дорожки (бесконечная прокрутка). minZ один раз за вызов — без reduce в цикле (меньше микрофризов при высокой скорости).
  const updateRoad = (playerZ) => {
    const segments = roadSegments.value
    const cameraZ = camera ? camera.position.z : 8
    const cutoffZ = cameraZ + roadLength * 1.5
    let minZ = segments.length ? segments[0].position.z : 0
    for (let i = 1; i < segments.length; i++) {
      const z = segments[i].position.z
      if (z < minZ) minZ = z
    }
    segments.forEach((segment) => {
      segment.position.z += roadSpeed.value
      if (segment.position.z > cutoffZ) {
        segment.position.z = minZ - roadLength + 0.1
        minZ = segment.position.z
      }
    })
    updateLaneMarkings()
  }

  // Окно неуязвимости к синему блоку (мс): после свайпа вниз не бьём по ROLL, не зависим от порядка rAF.
  const ROLL_IMMUNE_MS = 950
  const _obstaclesToRemove = []
  const _collectiblesToRemove = []

  // Обновление препятствий.
  // Коллизия через ручной AABB по известной геометрии куба.
  // ROLL: не бьём при isSliding, по высоте (underBar) или в окне по времени.
  const updateObstacles = (playerBox, onCollision, isSliding = false, slideStartTime = 0) => {
    _obstaclesToRemove.length = 0
    const obstaclesToRemove = _obstaclesToRemove
    const inRollImmuneWindow = slideStartTime > 0 && Date.now() - slideStartTime < ROLL_IMMUNE_MS

    obstacles.value.forEach((obstacle, index) => {
      obstacle.position.z += roadSpeed.value

      const inCollideZone = obstacle.position.z >= COLLIDE_Z_MIN && obstacle.position.z <= COLLIDE_Z_MAX

      if (playerBox && inCollideZone) {
        const kind = obstacle.userData.kind

        // Ручной AABB препятствия: знаем, что это куб 1xH x1, центр в obstacle.position.
        const halfX = 0.5
        const halfZ = 0.5
        const halfY = (obstacle.userData.height || 1) / 2

        const cx = obstacle.position.x
        const cy = obstacle.position.y
        const cz = obstacle.position.z

        const minX = cx - halfX
        const maxX = cx + halfX
        const minY = cy - halfY
        const maxY = cy + halfY
        const minZ = cz - halfZ
        const maxZ = cz + halfZ

        const pMin = playerBox.min
        const pMax = playerBox.max

        const intersects =
          pMax.x >= minX && pMin.x <= maxX &&
          pMax.y >= minY && pMin.y <= maxY &&
          pMax.z >= minZ && pMin.z <= maxZ

        if (kind === OBSTACLE_KIND.ROLL) {
          // Синий блок: не бьём при кувырке, по высоте под баром или в окне неуязвимости по времени.
          const bottomY = minY
          const underBar = pMax.y < bottomY + 0.4
          const safeFromRoll = isSliding || underBar || inRollImmuneWindow
          if (!safeFromRoll && !obstacle.userData.hit && intersects) {
            obstacle.userData.hit = true
            onCollision(obstacle)
            return
          }
        } else {
          if (!obstacle.userData.hit && intersects) {
            obstacle.userData.hit = true
            onCollision(obstacle)
            return
          }
        }
      }

      if (obstacle.position.z > 6) {
        obstaclesToRemove.push(index)
        scene.remove(obstacle)
      }
    })

    if (obstaclesToRemove.length > 0) {
      obstaclesToRemove.sort((a, b) => b - a)
      obstaclesToRemove.forEach((i) => obstacles.value.splice(i, 1))
    }
  }

  // Обновление собираемых предметов
  // Аналогично препятствиям, используем ручной AABB по известным размерам куба.
  const updateCollectibles = (playerBox, onCollect) => {
    _collectiblesToRemove.length = 0
    const collectiblesToRemove = _collectiblesToRemove
    const now = Date.now()
    const pulse = 1 + Math.sin(now * 0.01) * 0.15
    const offsetY = Math.sin(now * 0.005) * 0.3

    collectibles.value.forEach((collectible, index) => {
      if (collectible.userData.collected) {
        collectiblesToRemove.push(index)
        return
      }

      collectible.position.z += roadSpeed.value
      collectible.rotation.y += 0.05
      collectible.rotation.x += 0.03

      collectible.scale.setScalar(pulse)
      collectible.position.y = 1 + offsetY

      const inCollideZone = collectible.position.z >= COLLIDE_Z_MIN && collectible.position.z <= COLLIDE_Z_MAX

      if (playerBox && inCollideZone) {
        // Внешний куб энергии 0.6x0.6x0.6, центр в collectible.position.
        const half = 0.3
        const cx = collectible.position.x
        const cy = collectible.position.y
        const cz = collectible.position.z

        const minX = cx - half
        const maxX = cx + half
        const minY = cy - half
        const maxY = cy + half
        const minZ = cz - half
        const maxZ = cz + half

        const pMin = playerBox.min
        const pMax = playerBox.max

        const intersects =
          pMax.x >= minX && pMin.x <= maxX &&
          pMax.y >= minY && pMin.y <= maxY &&
          pMax.z >= minZ && pMin.z <= maxZ

        if (intersects) {
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

      if (collectible.position.z > 6) {
        collectiblesToRemove.push(index)
        scene.remove(collectible)
      }
    })

    if (collectiblesToRemove.length > 0) {
      collectiblesToRemove.sort((a, b) => b - a)
      collectiblesToRemove.forEach((i) => collectibles.value.splice(i, 1))
    }
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
