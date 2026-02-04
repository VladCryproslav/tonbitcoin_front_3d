import { ref } from 'vue'
import {
  BoxGeometry,
  MeshStandardMaterial,
  MeshLambertMaterial,
  MeshBasicMaterial,
  Mesh,
  PlaneGeometry,
  Color,
  InstancedMesh,
  Matrix4,
  Quaternion,
  Vector3
} from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

const BARRIER_PATHS = {
  jump: '/models/jump_barrier.glb',
  roll: '/models/roll_barrier.glb',
  impassable: '/models/impassable_barrier.glb'
}
const TOKEN_PATHS = {
  v1: '/models/token_v1.glb',
  v2: '/models/token_v2.glb'
}
const FENCE_MODEL_PATH = '/models/fence_V1.glb'

export function useGameWorld(scene) {
  // Длина одного сегмента дороги и количество сегментов.
  // Чуть увеличены, чтобы дорога рисовалась дальше без разрывов.
  const roadLength = 25
  const segmentCount = 7
  const roadSegments = []
  const obstacles = []
  const collectibles = []
  const roadSpeed = ref(0.3)
  const lanes = [-2, 0, 2] // Позиции полос (левая, центр, правая)

  // Боковые барьеры: простые боксы как фолбек + GLB-забор как декор
  let leftBarrier = null
  let rightBarrier = null
  let fenceTemplate = null
  const fences = []
  let fenceEnabled = true

  // Секции дороги: меньше дистанция — спавн чаще. При разгоне увеличиваем spacing — меньше спавна, меньше clone/GC
  const SECTION_SPACING = 4
  const SECTION_SPACING_HIGH_SPEED = 6 // при speed > 0.4
  const SECTION_WORLD_LENGTH = 14
  const COLLECTIBLE_MIN_Z_DISTANCE = 5 // мин. расстояние по Z между коллектами (избегаем наложения)
  let lastSpawnPlayerZ = -999
  let nextSectionWorldZ = -48
  let lastCollectibleZ = -9999
  let roadOffsetZ = 0

  // Лёгкий RNG-пул, чтобы не дёргать Math.random() в hot-path
  const RNG_SIZE = 2048
  const rngValues = new Float32Array(RNG_SIZE)
  let rngIndex = 0
  const refillRng = () => {
    for (let i = 0; i < RNG_SIZE; i++) {
      rngValues[i] = Math.random()
    }
  }
  refillRng()
  const nextRand = () => {
    const v = rngValues[rngIndex++]
    if (rngIndex >= RNG_SIZE) {
      rngIndex = 0
      refillRng()
    }
    return v
  }

  // Разметка полос – данные по инстансам + один InstancedMesh
  const laneMarkings = [] // { laneX, z }
  let laneMarkingsMesh = null
  const _laneMatrix = new Matrix4()
  const _laneQuat = new Quaternion()
  const _laneScale = new Vector3(1, 1, 1)
  const _lanePos = new Vector3()

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

  // GLB‑забор: один шаблон клонируем вдоль оси Z по обеим сторонам
  // Берём шаг чуть меньше длины сегмента, чтобы не было заметных щелей.
  const FENCE_SECTION_STEP = 18
  const FENCE_SEGMENT_COUNT = 5
  const FENCE_WORLD_LENGTH = FENCE_SECTION_STEP * FENCE_SEGMENT_COUNT
  const createFenceInstances = () => {
    if (!fenceTemplate || !leftBarrier || !rightBarrier) return

    const halfLen = FENCE_WORLD_LENGTH / 2
    for (let z = -halfLen; z <= halfLen; z += FENCE_SECTION_STEP) {
      const leftFence = fenceTemplate.clone()
      leftFence.position.set(leftBarrier.position.x, 0, z)
      leftFence.visible = fenceEnabled
      scene.add(leftFence)
      fences.push(leftFence)

      const rightFence = fenceTemplate.clone()
      rightFence.position.set(rightBarrier.position.x, 0, z)
      // Правый забор разворачиваем "лицом" к дороге
      rightFence.rotation.y = Math.PI
      rightFence.visible = fenceEnabled
      scene.add(rightFence)
      fences.push(rightFence)
    }
  }

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
  let tokenV1Template = null
  let tokenV2Template = null

  const loadBarrierModels = () => {
    const loader = new GLTFLoader()
    const loadBarrier = (kind) =>
      loader.loadAsync(BARRIER_PATHS[kind]).then((gltf) => {
        const template = gltf.scene
        template.traverse((child) => {
          if (child.isMesh) child.castShadow = false
        })
        barrierTemplates[kind] = template
      }).catch((err) => {
        console.warn(`Barrier ${kind} load failed:`, err)
      })
    const loadToken = (key) =>
      loader.loadAsync(TOKEN_PATHS[key]).then((gltf) => {
        const tmpl = gltf.scene
        tmpl.traverse((child) => {
          if (child.isMesh) child.castShadow = false
        })
        if (key === 'v1') tokenV1Template = tmpl
        else tokenV2Template = tmpl
      }).catch((err) => {
        console.warn(`Token ${key} load failed:`, err)
      })
    return Promise.all([
      loadBarrier(OBSTACLE_KIND.JUMP),
      loadBarrier(OBSTACLE_KIND.ROLL),
      loadBarrier(OBSTACLE_KIND.IMPASSABLE),
      loadToken('v1'),
      loadToken('v2')
    ]).then(() => {
      prewarmPools()
      return undefined
    })
  }

  // Предзаполнение пулов — меньше clone() при разгоне
  const PREWARM_OBSTACLES_PER_KIND = 4
  const PREWARM_COLLECTIBLES = 6
  const prewarmPools = () => {
    for (const kind of [OBSTACLE_KIND.IMPASSABLE, OBSTACLE_KIND.JUMP, OBSTACLE_KIND.ROLL]) {
      const def = OBSTACLE_DEF[kind]
      if (!def) continue
      const template = barrierTemplates[kind]
      const halfY = def.height / 2
      const bounds = { halfX: 0.5, halfY, halfZ: 0.5 }
      const pool = inactiveObstaclesByKind[kind]
      for (let i = 0; i < PREWARM_OBSTACLES_PER_KIND; i++) {
        let obstacle
        if (template) {
          obstacle = template.clone(true)
          obstacle.traverse((child) => {
            if (child.isMesh) child.castShadow = false
          })
        } else {
          const geo = kind === OBSTACLE_KIND.ROLL ? sharedObstacleGeometry.roll : sharedObstacleGeometry[def.height]
          obstacle = new Mesh(geo, sharedObstacleMaterial[kind])
        }
        obstacle.visible = false
        obstacle.position.set(-999, -999, -999)
        obstacle.userData = { bounds, type: 'obstacle', kind, collisionCenterY: def.bottomY != null ? def.bottomY + halfY : halfY }
        scene.add(obstacle)
        pool.push(obstacle)
      }
    }
    const tmpl = tokenV1Template || tokenV2Template
    for (let i = 0; i < PREWARM_COLLECTIBLES; i++) {
      let mesh
      if (tmpl) {
        mesh = tmpl.clone(true)
        mesh.traverse((child) => { if (child.isMesh) child.castShadow = false })
      } else {
        mesh = new Mesh(sharedCollectibleGeo, sharedCollectibleMat)
      }
      mesh.visible = false
      mesh.position.set(-999, -999, -999)
      mesh.userData = { bounds: { half: COLLECTIBLE_HALF }, type: 'collectible' }
      scene.add(mesh)
      inactiveCollectibles.push(mesh)
    }
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
    let r = nextRand() * 100
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
    // Небо — одна плоскость, один материал, однородный цвет (1 draw call вместо 3)
    const skyGeometry = new PlaneGeometry(100, 60)
    const skyMaterial = new MeshBasicMaterial({
      color: new Color().setHSL(0.55, 0.5, 0.82),
      side: 2 // DoubleSide
    })
    const sky = new Mesh(skyGeometry, skyMaterial)
    sky.position.set(0, 14, -55)
    sky.rotation.x = -Math.PI / 3
    sky.castShadow = false
    sky.receiveShadow = false
    sky.matrixAutoUpdate = false
    sky.updateMatrix()
    scene.add(sky)

    // Боковые барьеры - Lambert, без лишней физики материала.
    const barrierGeometry = new BoxGeometry(0.5, 2.5, 200)
    const barrierMaterial = new MeshLambertMaterial({
      color: 0x666666
    })

    // Левый барьер (фолбек, если GLB-забор не загрузится)
    leftBarrier = new Mesh(barrierGeometry, barrierMaterial)
    // Ещё чуть дальше от дороги — даём место широкому бордюру
    leftBarrier.position.set(-4.0, 1.25, 0)
    leftBarrier.castShadow = false
    leftBarrier.receiveShadow = false
    leftBarrier.matrixAutoUpdate = false
    leftBarrier.updateMatrix()
    scene.add(leftBarrier)

    // Правый барьер (фолбек)
    rightBarrier = new Mesh(barrierGeometry, barrierMaterial)
    rightBarrier.position.set(4.0, 1.25, 0)
    rightBarrier.castShadow = false
    rightBarrier.receiveShadow = false
    rightBarrier.matrixAutoUpdate = false
    rightBarrier.updateMatrix()
    scene.add(rightBarrier)

    // Простой широкий бордюр между дорогой (±3) и забором (±4.0), без эффектов и теней
    // Цвет чуть светлее, чем у забора
    // Делаем чуть шире в сторону забора: внутренняя кромка остаётся у дороги, внешняя уходит под забор.
    const curbGeometry = new BoxGeometry(1.3, 0.3, 200)
    const curbMaterial = new MeshLambertMaterial({ color: 0x777777 })

    const leftCurb = new Mesh(curbGeometry, curbMaterial)
    // Центр на -3.65: бордюр закрывает от -3.0 (край дороги) примерно до -4.3 (чуть под забор)
    leftCurb.position.set(-3.65, 0.15, 0)
    leftCurb.castShadow = false
    leftCurb.receiveShadow = false
    leftCurb.matrixAutoUpdate = false
    leftCurb.updateMatrix()
    scene.add(leftCurb)

    const rightCurb = new Mesh(curbGeometry, curbMaterial)
    rightCurb.position.set(3.65, 0.15, 0)
    rightCurb.castShadow = false
    rightCurb.receiveShadow = false
    rightCurb.matrixAutoUpdate = false
    rightCurb.updateMatrix()
    scene.add(rightCurb)

    // Пытаемся загрузить детализированный забор из GLB. Если что-то пойдёт не так — остаются боксы выше.
    const fenceLoader = new GLTFLoader()
    fenceLoader.load(
      FENCE_MODEL_PATH,
      (gltf) => {
        fenceTemplate = gltf.scene
        fenceTemplate.traverse((child) => {
          if (child.isMesh) {
            child.castShadow = false
            child.receiveShadow = false
          }
        })
        createFenceInstances()
      },
      undefined,
      (err) => {
        console.warn('Fence GLB load failed:', err)
      }
    )

    // Барьерные маркеры как декоративный шум убраны для снижения нагрузки.
  }

  // Создание дорожки
  const createRoad = () => {
    createBackground()
    const roadWidth = 6

    roadOffsetZ = 0
    for (let i = 0; i < segmentCount; i++) {
      const roadGeometry = new PlaneGeometry(roadWidth, roadLength)
      const roadMaterial = new MeshStandardMaterial({
        color: 0x2A2A2A, // Темно-серый асфальт
        roughness: 0.9,
        flatShading: true // Cartoon стиль
      })
      const road = new Mesh(roadGeometry, roadMaterial)
      road.rotation.x = -Math.PI / 2
      road.position.z = -i * roadLength + roadOffsetZ
      road.position.y = 0
      road.userData.type = 'road'
      scene.add(road)
      roadSegments.push(road)
    }

    // Разметка полос
    createLaneMarkings()
  }

  // Разметка полос. Одна геометрия/материал и один InstancedMesh — логика спавна по Z и полосам та же.
  // Обновление только в updateLaneMarkings (вызов из updateRoad), одна скорость roadSpeed.
  const createLaneMarkings = () => {
    const stepZ = MARKING_LENGTH * 2
    laneMarkings.length = 0

    // Подготовка данных по позициям
    for (let z = -80; z < 15; z += stepZ) {
      lanes.forEach((laneX) => {
        laneMarkings.push({ laneX, z })
      })
    }

    // Пересоздаём InstancedMesh, если уже был
    if (laneMarkingsMesh) {
      scene.remove(laneMarkingsMesh)
      laneMarkingsMesh.geometry.dispose()
      laneMarkingsMesh = null
    }

    laneMarkingsMesh = new InstancedMesh(
      sharedMarkingGeometry,
      sharedMarkingMaterial,
      laneMarkings.length
    )

    for (let i = 0; i < laneMarkings.length; i++) {
      const { laneX, z } = laneMarkings[i]
      _lanePos.set(laneX, 0.01, z)
      _laneQuat.identity()
      _laneMatrix.compose(_lanePos, _laneQuat, _laneScale)
      laneMarkingsMesh.setMatrixAt(i, _laneMatrix)
    }

    laneMarkingsMesh.instanceMatrix.needsUpdate = true
    scene.add(laneMarkingsMesh)
  }

  // Обновление разметки: двигаем с roadSpeed, ушедшие (z>10) телепортируем за хвост полосы.
  const updateLaneMarkings = (speed = roadSpeed.value) => {
    if (!laneMarkingsMesh || laneMarkings.length === 0) return

    const minZByLane = {}
    const stepZ = MARKING_LENGTH * 2

    // Шаг 1: обновляем Z и находим минимальный Z по полосам
    for (let i = 0; i < laneMarkings.length; i++) {
      const entry = laneMarkings[i]
      entry.z += speed
      if (entry.z <= 10) {
        const laneKey = Math.round(entry.laneX * 10) / 10
        const z = entry.z
        if (minZByLane[laneKey] === undefined || z < minZByLane[laneKey]) {
          minZByLane[laneKey] = z
        }
      }
    }

    // Шаг 2: телепорт + обновление матриц инстансов
    for (let i = 0; i < laneMarkings.length; i++) {
      const entry = laneMarkings[i]
      if (entry.z > 10) {
        const laneKey = Math.round(entry.laneX * 10) / 10
        const minZ = minZByLane[laneKey]
        entry.z = minZ !== undefined ? minZ - stepZ + 0.05 : -50
      }

      _lanePos.set(entry.laneX, 0.01, entry.z)
      _laneQuat.identity()
      _laneMatrix.compose(_lanePos, _laneQuat, _laneScale)
      laneMarkingsMesh.setMatrixAt(i, _laneMatrix)
    }

    laneMarkingsMesh.instanceMatrix.needsUpdate = true
  }

  // Движение сегментов GLB-забора вместе с дорогой.
  // Используем тот же speed, что и для дороги/разметки.
  const updateFences = (speed = roadSpeed.value) => {
    if (!fences.length) return

    const halfLen = FENCE_WORLD_LENGTH / 2
    const fullLen = FENCE_WORLD_LENGTH

    for (let i = 0; i < fences.length; i++) {
      const obj = fences[i]
      obj.position.z += speed

      // Когда сегмент ушёл слишком далеко вперёд — перекидываем его назад,
      // сохраняя бесшовный коридор.
      if (obj.position.z > halfLen) {
        obj.position.z -= fullLen
      }
    }
  }

  // Включение / отключение забора (GLB + фолбек-боксы), например, для low-графики.
  const setFenceEnabled = (enabled) => {
    fenceEnabled = !!enabled

    // GLB‑забор
    if (fences.length) {
      for (let i = 0; i < fences.length; i++) {
        fences[i].visible = fenceEnabled
      }
    }

    // Фолбек‑боксы: показываем только если нет GLB и не low.
    const showFallback = fenceEnabled && fences.length === 0
    if (leftBarrier) leftBarrier.visible = showFallback
    if (rightBarrier) rightBarrier.visible = showFallback
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
        if (child.isMesh) child.castShadow = false
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
      obstacle.castShadow = false
      obstacle.renderOrder = 1
      scene.add(obstacle)
    }

    // Центр AABB для коллизии: низ (bottomY) + половина высоты, либо просто половина высоты.
    const collisionCenterY = def.bottomY != null ? def.bottomY + halfY : halfY
    // GLB из Blender: origin внизу модели → визуально ставим низ на дорогу (y=0).
    // BoxGeometry: origin в центре → ставим центр туда же, где и центр AABB.
    const isGLB = !obstacle.isMesh
    const posY = isGLB ? 0 : collisionCenterY

    obstacle.position.set(lanes[lane], posY, z)
    obstacle.visible = true
    obstacle.userData.lane = lane
    obstacle.userData.height = def.height
    obstacle.userData.kind = kind
    obstacle.userData.hit = false
    // Для коллизии: центр AABB (один и тот же для GLB и боксов)
    obstacle.userData.collisionCenterY = collisionCenterY

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

  // Создание собираемого предмета (энергия). point = { value, isGlowing }.
  // token_v1.glb/token_v2.glb: origin по центру модели. Box: origin в центре.
  const createCollectible = (lane, z, point) => {
    const isGlow = point?.isGlowing ?? false
    const mat = isGlow ? sharedCollectibleMatGlow : sharedCollectibleMat
    const bounds = { half: COLLECTIBLE_HALF }

    let mesh
    if (inactiveCollectibles.length > 0) {
      mesh = inactiveCollectibles.pop()
      // Если в пуле старый куб, а токены уже есть — избавляемся от него и создаём GLB.
      if (mesh.isMesh && (tokenV1Template || tokenV2Template)) {
        scene.remove(mesh)
        mesh = null
      } else if (mesh.isMesh) {
        mesh.material = mat
      }
    }

    if (!mesh) {
      const template = isGlow ? (tokenV2Template || tokenV1Template) : (tokenV1Template || tokenV2Template)
      if (template) {
        mesh = template.clone(true)
        mesh.traverse((child) => {
          if (child.isMesh) child.castShadow = false
        })
        mesh.userData.bounds = bounds
        mesh.userData.type = 'collectible'
        scene.add(mesh)
      } else {
        mesh = new Mesh(sharedCollectibleGeo, mat)
        mesh.userData.bounds = bounds
        mesh.userData.type = 'collectible'
        scene.add(mesh)
      }
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
    const speed = roadSpeed.value
    const spacing = speed > 0.4 ? SECTION_SPACING_HIGH_SPEED : SECTION_SPACING
    if (playerZ - lastSpawnPlayerZ < spacing) return

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
        const lane = Math.floor(nextRand() * 3)
        const baseZ = lastCollectibleZ < -9000 ? sectionZ - 5 : lastCollectibleZ - COLLECTIBLE_MIN_Z_DISTANCE
        const firstCollectibleZ = Math.min(sectionZ - 5, baseZ) - nextRand() * 4
        createCollectible(lane, firstCollectibleZ, point)
        lastCollectibleZ = firstCollectibleZ
      }
      if (nextRand() < 0.4) {
        const point2 = getNextEnergyPoint()
        if (point2) {
          const lane = Math.floor(nextRand() * 3)
          const secondZ = lastCollectibleZ - COLLECTIBLE_MIN_Z_DISTANCE - nextRand() * 3
          if (secondZ < sectionZ + 2) {
            createCollectible(lane, secondZ, point2)
            lastCollectibleZ = secondZ
          }
        }
      }
    }
  }

  // Обновление дорожки (бесконечная прокрутка). Кэшируем roadSpeed — меньше обращений к ref.
  const updateRoad = () => {
    const speed = roadSpeed.value
    const segments = roadSegments
    if (!segments.length) return

    // Сдвигаем общий оффсет и замыкаем его в пределах длины одного сегмента,
    // чтобы позиции не уплывали в большие числа.
    roadOffsetZ += speed
    if (roadOffsetZ > roadLength) {
      roadOffsetZ -= roadLength
    }

    // Каждый сегмент жёстко стоит в сетке: непрерывная полоса без щелей.
    for (let i = 0; i < segments.length; i++) {
      const segment = segments[i]
      segment.position.z = -i * roadLength + roadOffsetZ
    }
    updateLaneMarkings(speed)
    updateFences(speed)
  }

  const _obstaclesToRemove = []
  const _collectiblesToRemove = []

  // Обновление препятствий. Кэшируем speed.
  const updateObstacles = (playerBox, onCollision, isSliding = false, inRollImmuneWindow = false) => {
    _obstaclesToRemove.length = 0
    const obstaclesToRemove = _obstaclesToRemove
    const speed = roadSpeed.value

    for (let i = 0; i < obstacles.length; i++) {
      const obstacle = obstacles[i]
      obstacle.position.z += speed

      if (obstacle.position.z > 6) {
        obstaclesToRemove.push(i)
        continue
      }

      const inCollideZone = obstacle.position.z >= COLLIDE_Z_MIN && obstacle.position.z <= COLLIDE_Z_MAX
      if (!inCollideZone) continue

      if (playerBox) {
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
          const barBottom = minY
          const underBar = pMax.y < barBottom
          const safeFromRoll = isSliding || underBar || inRollImmuneWindow
          if (!safeFromRoll && !obstacle.userData.hit && intersects) {
            obstacle.userData.hit = true
            onCollision(obstacle)
          }
        } else {
          if (!obstacle.userData.hit && intersects) {
            obstacle.userData.hit = true
            onCollision(obstacle)
          }
        }
      }
    }

    if (obstaclesToRemove.length > 0) {
      obstaclesToRemove.sort((a, b) => b - a)
      obstaclesToRemove.forEach((idx) => {
        const obstacle = obstacles[idx]
        obstacle.visible = false
        const k = obstacle.userData.kind
        if (k && inactiveObstaclesByKind[k]) {
          inactiveObstaclesByKind[k].push(obstacle)
        }
        obstacles.splice(idx, 1)
      })
    }
  }

  // Обновление собираемых предметов.
  // onCollect(energy) — при сборе, onPassed() — при уходе за экран без сбора.
  const updateCollectibles = (playerBox, onCollect, onPassed) => {
    _collectiblesToRemove.length = 0
    const collectiblesToRemove = _collectiblesToRemove
    const speed = roadSpeed.value

    collectibles.forEach((collectible, index) => {
      if (collectible.userData.collected) {
        collectiblesToRemove.push(index)
        return
      }

      collectible.position.z += speed
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
    roadSpeed,
    setFenceEnabled
  }
}
