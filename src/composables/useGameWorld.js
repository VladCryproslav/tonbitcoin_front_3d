import { ref } from 'vue'
import {
  BoxGeometry,
  MeshStandardMaterial,
  MeshLambertMaterial,
  MeshBasicMaterial,
  Mesh,
  PlaneGeometry,
  Color
} from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

const BARRIER_PATHS = {
  jump: '/models/jump_barrier.glb',
  roll: '/models/roll_barrier.glb',
  impassable: '/models/impassable_barrier.glb'
}

export function useGameWorld(scene, camera) {
  // Длина одного сегмента дороги и количество сегментов.
  // Чуть увеличены, чтобы дорога рисовалась дальше без разрывов.
  const roadLength = 25
  const segmentCount = 7
  const roadSegments = []
  const obstacles = []
  const collectibles = []
  const roadSpeed = ref(0.3)
  const lanes = [-2, 0, 2] // Позиции полос (левая, центр, правая)

  // Секции дороги: меньше дистанция — спавн чаще
  const SECTION_SPACING = 4 // мин. «расстояние» (по playerZ) между секциями
  const SECTION_WORLD_LENGTH = 14
  const COLLECTIBLE_MIN_Z_DISTANCE = 5 // мин. расстояние по Z между коллектами (избегаем наложения)
  let lastSpawnPlayerZ = -999
  let nextSectionWorldZ = -48
  let lastCollectibleZ = -9999

  const laneMarkings = []

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

  // GLB-барьеры: шаблоны для клонирования (fallback — боксы)
  const barrierTemplates = {
    [OBSTACLE_KIND.JUMP]: null,
    [OBSTACLE_KIND.ROLL]: null,
    [OBSTACLE_KIND.IMPASSABLE]: null
  }

  const loadBarrierModels = () => {
    const loader = new GLTFLoader()
    const load = (kind) =>
      loader.loadAsync(BARRIER_PATHS[kind]).then((gltf) => {
        const template = gltf.scene
        template.traverse((child) => {
          if (child.isMesh) {
            child.castShadow = true
          }
        })
        barrierTemplates[kind] = template
      }).catch((err) => {
        console.warn(`Barrier ${kind} load failed:`, err)
      })
    return Promise.all([
      load(OBSTACLE_KIND.JUMP),
      load(OBSTACLE_KIND.ROLL),
      load(OBSTACLE_KIND.IMPASSABLE)
    ])
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
    // Небо - простое, без освещения (MeshBasicMaterial).
    for (let i = 0; i < 3; i++) {
      const skyGeometry = new PlaneGeometry(50, 30)
      const skyColor = new Color()
      skyColor.setHSL(0.55, 0.5, 0.75 + i * 0.08)
      const skyMaterial = new MeshBasicMaterial({
        color: skyColor,
        side: 2 // DoubleSide
      })
      const sky = new Mesh(skyGeometry, skyMaterial)
      sky.position.set(0, 15 - i * 5, -20 - i * 10)
      sky.rotation.x = -Math.PI / 3
      sky.castShadow = false
      sky.receiveShadow = false
      scene.add(sky)
    }

    // Боковые барьеры - Lambert, без лишней физики материала.
    const barrierGeometry = new BoxGeometry(0.5, 2.5, 200)
    const barrierMaterial = new MeshLambertMaterial({
      color: 0x666666
    })

    // Левый барьер
    const leftBarrier = new Mesh(barrierGeometry, barrierMaterial)
    leftBarrier.position.set(-3.5, 1.25, 0)
    leftBarrier.castShadow = false
    leftBarrier.receiveShadow = false
    scene.add(leftBarrier)

    // Правый барьер
    const rightBarrier = new Mesh(barrierGeometry, barrierMaterial)
    rightBarrier.position.set(3.5, 1.25, 0)
    rightBarrier.castShadow = false
    rightBarrier.receiveShadow = false
    scene.add(rightBarrier)

    // Барьерные маркеры как декоративный шум убраны для снижения нагрузки.
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
      roadSegments.push(road)
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
        laneMarkings.push(marking)
      })
    }
  }

  // Обновление разметки: двигаем с roadSpeed, ушедшие (z>10) телепортируем за хвост полосы.
  // Два прохода вместо трёх; логика та же — одна скорость, один массив, без расслоения «два шара».
  const updateLaneMarkings = () => {
    const minZByLane = {}
    const speed = roadSpeed.value
    const stepZ = MARKING_LENGTH * 2
    laneMarkings.forEach(marking => {
      marking.position.z += speed
      if (marking.position.z <= 10) {
        const laneKey = Math.round(marking.position.x * 10) / 10
        const z = marking.position.z
        if (minZByLane[laneKey] === undefined || z < minZByLane[laneKey]) {
          minZByLane[laneKey] = z
        }
      }
    })
    laneMarkings.forEach(marking => {
      if (marking.position.z > 10) {
        const laneKey = Math.round(marking.position.x * 10) / 10
        const minZ = minZByLane[laneKey]
        marking.position.z = minZ !== undefined ? minZ - stepZ + 0.05 : -50
      }
    })
  }

  // Создание препятствия по типу: jump (прыжок), roll (кувырок), impassable (непроходимая — кувырок)
  const inactiveObstaclesByKind = {
    [OBSTACLE_KIND.IMPASSABLE]: [],
    [OBSTACLE_KIND.JUMP]: [],
    [OBSTACLE_KIND.ROLL]: []
  }

  const createObstacle = (lane, z, kind) => {
    const def = OBSTACLE_DEF[kind]
    if (!def) return null

    const halfY = def.height / 2
    const bounds = { halfX: 0.5, halfY, halfZ: 0.5 }
    const pool = inactiveObstaclesByKind[kind]
    const template = barrierTemplates[kind]

    let obstacle
    if (pool.length > 0) {
      obstacle = pool.pop()
      if (obstacle.isMesh) {
        const geo = kind === OBSTACLE_KIND.ROLL ? sharedObstacleGeometry.roll : sharedObstacleGeometry[def.height]
        obstacle.geometry = geo
        obstacle.material = sharedObstacleMaterial[kind]
      }
    } else if (template) {
      obstacle = template.clone(true)
      obstacle.traverse((child) => {
        if (child.isMesh) child.castShadow = true
      })
      obstacle.renderOrder = 1
      obstacle.userData.bounds = bounds
      obstacle.userData.type = 'obstacle'
      scene.add(obstacle)
    } else {
      const geo = kind === OBSTACLE_KIND.ROLL ? sharedObstacleGeometry.roll : sharedObstacleGeometry[def.height]
      obstacle = new Mesh(geo, sharedObstacleMaterial[kind])
      obstacle.userData.bounds = bounds
      obstacle.userData.type = 'obstacle'
      obstacle.castShadow = true
      obstacle.renderOrder = 1
      scene.add(obstacle)
    }

    // GLB из Blender: origin внизу модели → position.y = низ. BoxGeometry: origin в центре.
    const isGLB = !obstacle.isMesh
    const posY = isGLB
      ? (def.bottomY ?? 0)
      : (def.bottomY != null ? def.bottomY + halfY : halfY)

    obstacle.position.set(lanes[lane], posY, z)
    obstacle.visible = true
    obstacle.userData.lane = lane
    obstacle.userData.height = def.height
    obstacle.userData.kind = kind
    obstacle.userData.hit = false
    // Для коллизии: центр AABB (у GLB position = низ, у Box = центр)
    obstacle.userData.collisionCenterY = isGLB ? posY + halfY : posY

    obstacles.push(obstacle)
    return obstacle
  }

  // Общая геометрия и материалы коллектов (простой зелёный куб).
  const sharedCollectibleGeo = new BoxGeometry(0.6, 0.6, 0.6)
  const sharedCollectibleMat = new MeshStandardMaterial({
    color: 0x00ff00,
    emissive: 0x00ff00,
    emissiveIntensity: 0.7
  })
  const sharedCollectibleMatGlow = new MeshStandardMaterial({
    color: 0x00ff55,
    emissive: 0x00ff55,
    emissiveIntensity: 1.2
  })

  const inactiveCollectibles = []
  const COLLECTIBLE_HALF = 0.3

  // Создание собираемого предмета (энергия). point = { value, isGlowing }
  const createCollectible = (lane, z, point) => {
    let mesh
    const isGlow = point?.isGlowing ?? false
    const mat = isGlow ? sharedCollectibleMatGlow : sharedCollectibleMat

    if (inactiveCollectibles.length > 0) {
      mesh = inactiveCollectibles.pop()
      mesh.material = mat
    } else {
      mesh = new Mesh(sharedCollectibleGeo, mat)
      mesh.userData.bounds = { half: COLLECTIBLE_HALF }
      mesh.userData.type = 'collectible'
      scene.add(mesh)
    }

    mesh.position.set(lanes[lane], 1, z)
    mesh.visible = true
    mesh.userData.lane = lane
    mesh.userData.collected = false
    mesh.userData.energyValue = point?.value ?? 0.5
    collectibles.push(mesh)
    return mesh
  }

  // Генерация по секциям: дорога — прямоугольники, каждый прямоугольник — 3 сектора (полосы).
  // В каждом секторе один из 4 типов: нет преграды, непроходимая (кувырок), прыжок, кувырок.
  // Правило: три в ряд непроходимых (IMPASSABLE) быть не может — максимум 2 в секции.
  // Между секциями — минимальное расстояние SECTION_SPACING по playerZ.
  // getNextEnergyPoint: () => { value, isGlowing } | null — очередь поинтов из useGameRun
  const spawnObjects = (playerZ, getNextEnergyPoint) => {
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

    // Собираемые предметы: из очереди поинтов (1–2 за секцию), мин. расстояние между ними
    if (typeof getNextEnergyPoint === 'function') {
      const point = getNextEnergyPoint()
      if (point) {
        const lane = Math.floor(Math.random() * 3)
        const baseZ = lastCollectibleZ < -9000 ? sectionZ - 5 : lastCollectibleZ - COLLECTIBLE_MIN_Z_DISTANCE
        const firstCollectibleZ = Math.min(sectionZ - 5, baseZ) - Math.random() * 4
        createCollectible(lane, firstCollectibleZ, point)
        lastCollectibleZ = firstCollectibleZ
      }
      if (Math.random() < 0.4) {
        const point2 = getNextEnergyPoint()
        if (point2) {
          const lane = Math.floor(Math.random() * 3)
          const secondZ = lastCollectibleZ - COLLECTIBLE_MIN_Z_DISTANCE - Math.random() * 3
          if (secondZ < sectionZ + 2) {
            createCollectible(lane, secondZ, point2)
            lastCollectibleZ = secondZ
          }
        }
      }
    }
  }

  // Обновление дорожки (бесконечная прокрутка). minZ один раз за вызов — без reduce в цикле (меньше микрофризов при высокой скорости).
  const updateRoad = () => {
    const segments = roadSegments
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

  const _obstaclesToRemove = []
  const _collectiblesToRemove = []

  // Обновление препятствий.
  // Коллизия через ручной AABB по известной геометрии куба.
  // ROLL: не бьём при isSliding, по высоте (underBar) или в окне по времени.
  const updateObstacles = (playerBox, onCollision, isSliding = false, inRollImmuneWindow = false) => {
    _obstaclesToRemove.length = 0
    const obstaclesToRemove = _obstaclesToRemove

    obstacles.forEach((obstacle, index) => {
      obstacle.position.z += roadSpeed.value

      const inCollideZone = obstacle.position.z >= COLLIDE_Z_MIN && obstacle.position.z <= COLLIDE_Z_MAX

      if (playerBox && inCollideZone) {
        const kind = obstacle.userData.kind

        // Ручной AABB препятствия: знаем, что это куб 1xH x1, центр в obstacle.position.
        const { halfX, halfY, halfZ } = obstacle.userData.bounds || { halfX: 0.5, halfY: (obstacle.userData.height || 1) / 2, halfZ: 0.5 }

        const cx = obstacle.position.x
        const cy = obstacle.userData.collisionCenterY ?? obstacle.position.y
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
        obstacle.visible = false
        const k = obstacle.userData.kind
        if (k && inactiveObstaclesByKind[k]) {
          inactiveObstaclesByKind[k].push(obstacle)
        }
      }
    })

    if (obstaclesToRemove.length > 0) {
      obstaclesToRemove.sort((a, b) => b - a)
      obstaclesToRemove.forEach((i) => obstacles.splice(i, 1))
    }
  }

  // Обновление собираемых предметов.
  // onCollect(energy) — при сборе, onPassed() — при уходе за экран без сбора.
  const updateCollectibles = (playerBox, onCollect, onPassed) => {
    _collectiblesToRemove.length = 0
    const collectiblesToRemove = _collectiblesToRemove

    collectibles.forEach((collectible, index) => {
      if (collectible.userData.collected) {
        collectiblesToRemove.push(index)
        return
      }

      collectible.position.z += roadSpeed.value
      collectible.rotation.y += 0.05

      const inCollideZone = collectible.position.z >= COLLIDE_Z_MIN && collectible.position.z <= COLLIDE_Z_MAX

      if (playerBox && inCollideZone) {
        const half = collectible.userData.bounds?.half ?? COLLECTIBLE_HALF
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
          collectible.visible = false
          collectible.position.y = -9999
          collectible.position.z = -9999

          const energy = collectible.userData.energyValue ?? 0.5
          onCollect(energy)
          if (typeof onPassed === 'function') onPassed()
          collectiblesToRemove.push(index)
          inactiveCollectibles.push(collectible)
          return
        }
      }

      if (collectible.position.z > 6) {
        if (typeof onPassed === 'function') onPassed()
        collectiblesToRemove.push(index)
        collectible.visible = false
        inactiveCollectibles.push(collectible)
      }
    })

    if (collectiblesToRemove.length > 0) {
      collectiblesToRemove.sort((a, b) => b - a)
      collectiblesToRemove.forEach((i) => collectibles.splice(i, 1))
    }
  }

  // Очистка всех объектов
  const clearAll = () => {
    obstacles.forEach(obstacle => {
      obstacle.visible = false
      const k = obstacle.userData.kind
      if (k && inactiveObstaclesByKind[k]) {
        inactiveObstaclesByKind[k].push(obstacle)
      }
    })
    collectibles.forEach(collectible => {
      collectible.visible = false
      collectible.userData.collected = false
      inactiveCollectibles.push(collectible)
    })
    obstacles.length = 0
    collectibles.length = 0
    lastSpawnPlayerZ = -999
    nextSectionWorldZ = -48
    lastCollectibleZ = -9999
  }

  // Обновление скорости дороги
  const setRoadSpeed = (speed) => {
    roadSpeed.value = speed
  }

  return {
    createRoad,
    loadBarrierModels,
    spawnObjects,
    updateRoad,
    updateObstacles,
    updateCollectibles,
    clearAll,
    setRoadSpeed,
    roadSpeed
  }
}
