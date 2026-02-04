import { ref } from 'vue'
import {
  BoxGeometry,
  MeshStandardMaterial,
  Mesh,
  Vector3,
  Group,
  AnimationMixer,
  Clock,
  Box3
} from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js'
import * as THREE from 'three'

export function useGamePhysics(scene) {
  const playerPosition = ref(new Vector3(0, 0, 0))
  const playerLane = ref(1) // 0 = left, 1 = center, 2 = right
  const isJumping = ref(false)
  const isSliding = ref(false)

  const lanes = [-2, 0, 2] // Позиции полос
  const LANE_CHANGE_DURATION_MS = 180 // длительность смены полосы, time-based в update()
  let playerMesh = null
  let jumpStartTime = 0
  let jumpHeight = 1.7
  let jumpDuration = 600
  let jumpStartY = 0
  let slideStartTime = 0
  let rollDurationMs = 600
  let slideLandState = null // { startY, startRotX, startTime, duration } — приземление при slide из прыжка
  let slideFallbackState = null // { startTime, startY, startScaleY, phase, returnStartTime } — анимация кубика
  let mixer = null // Для анимаций из GLTF
  let clock = new Clock()
  // Смена полосы в одном цикле (update), без отдельного rAF — убирает микрофризы
  let laneTransitionStartTime = 0
  let laneTransitionStartX = 0
  let laneTransitionTargetX = null
  let currentAnimation = null
  let animations = []

  // Маппинг логических состояний на индексы клипов в main.glb:
  // 0: standing, 1: running, 2: jump, 3: roll, 4: fall, 5: win, 6: dodge (свайп влево/вправо)
  const animationIndexByState = {
    standing: 0,
    idle: 0,
    run: 1,
    running: 1,
    jump: 2,
    roll: 3,
    slide: 3,
    fall: 4,
    death: 4,
    win: 5,
    victory: 5,
    success: 5,
    dodge: 6,
    sidestep: 6
  }

  const playAnimationState = (state) => {
    if (!mixer || !animations || animations.length === 0) return

    const idx = animationIndexByState[state]
    const clip =
      (typeof idx === 'number' && animations[idx]) ||
      animations[0]
    if (!clip) return

    const action = mixer.clipAction(clip)
    if (currentAnimation === action) return

    if (currentAnimation) {
      currentAnimation.fadeOut(0.1)
    }

    // Для "fall/death", "roll/slide" и "dodge" играем анимацию один раз.
    if (state === 'fall' || state === 'death' || state === 'roll' || state === 'slide') {
      action.setLoop(THREE.LoopOnce, 1)
      action.clampWhenFinished = true
    } else if (state === 'dodge' || state === 'sidestep') {
      action.setLoop(THREE.LoopOnce, 1)
      action.clampWhenFinished = true
      const onFinished = (e) => {
        if (e.action !== action) return
        mixer.removeEventListener('finished', onFinished)
        playAnimationState('running')
      }
      mixer.addEventListener('finished', onFinished)
    } else {
      // Все остальные состояния (run/standing/win и т.д.) крутятся в цикле.
      action.setLoop(THREE.LoopRepeat, Infinity)
      action.clampWhenFinished = false
    }

    action.reset().fadeIn(0.1).play()
    currentAnimation = action
  }

  // Загрузка 3D модели игрока (опционально)
  const loadPlayerModel = async (gameScene, modelPath) => {
    if (!modelPath) return null

    try {
      const loader = new GLTFLoader()
      // Поддержка meshopt-компрессии из Blender
      loader.setMeshoptDecoder(MeshoptDecoder)
      const gltf = await loader.loadAsync(modelPath)

      const model = gltf.scene
      // При необходимости подправь масштаб/позицию под конкретную модель
      model.scale.set(1, 1, 1)
      model.position.set(0, 0, 0)
      // Разворачиваем модель спиной к камере (камера стоит с +Z и смотрит в 0)
      model.rotation.y = Math.PI

      // Настройка мешей и материалов
      model.traverse((child) => {
        if (child.isMesh) {
          child.castShadow = true
          child.receiveShadow = true

          if (!child.material.map) {
            child.material.color.set(0xEB7D26)
          }
          // Как в Blender: Metallic 0, Roughness 0.85 (IOR в Three.js нет — оставляем дефолт)
          child.material.metalness = 0
          child.material.roughness = 0.85
        }
      })

      // Настройка анимаций если есть
      if (gltf.animations && gltf.animations.length > 0) {
        animations = gltf.animations
        mixer = new AnimationMixer(model)
        // По умолчанию включаем standing/первый клип
        playAnimationState('standing')
      }

      const targetScene = gameScene || scene
      if (targetScene) {
        // Удаляем предыдущую модель игрока, если была
        if (playerMesh) {
          targetScene.remove(playerMesh)
        }
        targetScene.add(model)
      }
      playerMesh = model

      return model
    } catch (error) {
      console.error('Ошибка загрузки модели:', error)
      return null
    }
  }

  // Внутренняя утилита: создать кубического игрока (фоллбек)
  const createFallbackPlayer = (gameSceneToUse) => {
    const group = new Group()

    // Тело (инженер) - Subway Surfers стиль: яркие цвета
    const bodyGeometry = new BoxGeometry(0.8, 1.2, 0.6)
    const bodyMaterial = new MeshStandardMaterial({
      color: 0xEB7D26, // Оранжевый как в Subway Surfers
      metalness: 0.1,
      roughness: 0.9,
      flatShading: true // Cartoon стиль
    })
    const body = new Mesh(bodyGeometry, bodyMaterial)
    body.position.y = 0.6
    body.castShadow = true
    body.name = 'body'
    group.add(body)

    // Голова (шлем инженера) - яркий желтый
    const headGeometry = new BoxGeometry(0.6, 0.6, 0.6)
    const headMaterial = new MeshStandardMaterial({
      color: 0xFEFF28, // Яркий желтый Subway Surfers
      metalness: 0.2,
      roughness: 0.8,
      flatShading: true,
      emissive: 0xFFFF00,
      emissiveIntensity: 0.1
    })
    const head = new Mesh(headGeometry, headMaterial)
    head.position.y = 1.5
    head.castShadow = true
    head.name = 'head'
    group.add(head)

    // Руки - яркие цвета
    const armGeometry = new BoxGeometry(0.2, 0.8, 0.2)
    const armMaterial = new MeshStandardMaterial({
      color: 0xEB7D26,
      flatShading: true
    })

    const leftArm = new Mesh(armGeometry, armMaterial)
    leftArm.position.set(-0.5, 0.8, 0)
    leftArm.name = 'leftArm'
    group.add(leftArm)

    const rightArm = new Mesh(armGeometry, armMaterial)
    rightArm.position.set(0.5, 0.8, 0)
    rightArm.name = 'rightArm'
    group.add(rightArm)

    // Ноги - темно-синий/фиолетовый
    const legGeometry = new BoxGeometry(0.25, 0.6, 0.25)
    const legMaterial = new MeshStandardMaterial({
      color: 0x1E3A8A, // Темно-синий
      flatShading: true
    })

    const leftLeg = new Mesh(legGeometry, legMaterial)
    leftLeg.position.set(-0.25, 0, 0)
    leftLeg.name = 'leftLeg'
    group.add(leftLeg)

    const rightLeg = new Mesh(legGeometry, legMaterial)
    rightLeg.position.set(0.25, 0, 0)
    rightLeg.name = 'rightLeg'
    group.add(rightLeg)

    group.position.set(0, 0, 0)
    // Кубический персонаж тоже смотрит от камеры вперёд по -Z
    group.rotation.y = Math.PI
    gameSceneToUse.add(group)
    playerMesh = group

    return group
  }

  // Создание модели игрока (GLB-модель, либо фоллбек-куб)
  const createPlayer = (gameScene, modelPath = null) => {
    const gameSceneToUse = gameScene || scene
    if (!gameSceneToUse) return null

    // Если есть путь до модели — загружаем её.
    // Фоллбек-куб создаём только если путь не указан.
    if (modelPath) {
      return loadPlayerModel(gameSceneToUse, modelPath)
    }

    // Без пути к модели сразу создаём фоллбек
    return createFallbackPlayer(gameSceneToUse)
  }

  const moveLeft = () => {
    if (playerLane.value > 0) {
      playerLane.value--
      playerPosition.value.x = lanes[playerLane.value]
      if (playerMesh) {
        laneTransitionStartTime = performance.now()
        laneTransitionStartX = playerMesh.position.x
        laneTransitionTargetX = lanes[playerLane.value]
      }
    }
  }

  const moveRight = () => {
    if (playerLane.value < 2) {
      playerLane.value++
      playerPosition.value.x = lanes[playerLane.value]
      if (playerMesh) {
        laneTransitionStartTime = performance.now()
        laneTransitionStartX = playerMesh.position.x
        laneTransitionTargetX = lanes[playerLane.value]
      }
    }
  }

  const jump = () => {
    if (!isJumping.value) {
      isJumping.value = true
      isSliding.value = false
      jumpStartTime = performance.now()
      jumpHeight = 1.7
      jumpDuration = 600
      if (playerMesh) jumpStartY = playerMesh.position.y

      playAnimationState('jump')
    }
  }

  const slide = () => {
    if (!isSliding.value) {
      if (playerMesh && (isJumping.value || playerMesh.position.y > 0.1)) {
        slideLandState = {
          startY: playerMesh.position.y,
          startRotX: playerMesh.rotation.x,
          startTime: performance.now(),
          duration: 150
        }
      }

      isSliding.value = true
      isJumping.value = false
      slideStartTime = performance.now()

      playAnimationState('roll')

      if (mixer) {
        const rollClip = animations[animationIndexByState.roll]
        rollDurationMs = rollClip ? rollClip.duration * 1000 : 600
      } else if (playerMesh && !mixer) {
        slideFallbackState = {
          startTime: performance.now(),
          startY: playerMesh.position.y,
          startScaleY: playerMesh.scale.y,
          phase: 'down',
          returnStartTime: 0
        }
      }
    }
  }

  const getPlayerY = () => {
    if (playerMesh) {
      return playerMesh.position.y
    }
    if (isJumping.value) return 1.5
    if (isSliding.value) return 0.3
    return 0
  }

  const update = () => {
    const now = performance.now()

    if (mixer) {
      mixer.update(clock.getDelta())
    }

    if (playerMesh) {
      // Прыжок: всё в update(), без вложенных rAF
      if (isJumping.value && !isSliding.value) {
        const elapsed = now - jumpStartTime
        const progress = elapsed / jumpDuration
        if (progress >= 1) {
          playerMesh.position.y = jumpStartY
          playerMesh.rotation.x = 0
          isJumping.value = false
          playAnimationState('running')
        } else {
          const jumpCurve = Math.sin(progress * Math.PI)
          playerMesh.position.y = jumpStartY + jumpHeight * jumpCurve
          playerMesh.rotation.x = -progress * 0.3
        }
      }

      // Приземление при slide из прыжка
      if (slideLandState) {
        const t = Math.min((now - slideLandState.startTime) / slideLandState.duration, 1)
        const k = t * t * (3 - 2 * t)
        playerMesh.position.y = slideLandState.startY + (0 - slideLandState.startY) * k
        playerMesh.rotation.x = slideLandState.startRotX + (0 - slideLandState.startRotX) * k
        if (t >= 1) slideLandState = null
      }

      // Завершение слайда для GLTF-анимации по времени, без setTimeout
      if (mixer && isSliding.value) {
        const slideElapsed = now - slideStartTime
        if (slideElapsed >= rollDurationMs) {
          isSliding.value = false
          if (!isJumping.value) {
            playAnimationState('running')
          }
        }
      }

      // Слайд кубического фоллбэка
      if (slideFallbackState && !mixer) {
        const s = slideFallbackState
        if (s.phase === 'down') {
          const elapsed = now - s.startTime
          const progress = Math.min(elapsed / 500, 1)
          const scaleProgress = progress < 0.3 ? progress / 0.3 : 1
          playerMesh.scale.y = s.startScaleY - (s.startScaleY - 0.5) * scaleProgress
          playerMesh.position.y = s.startY - (s.startY - 0.3) * scaleProgress
          playerMesh.rotation.x = progress * 0.5
          if (progress >= 1) {
            s.phase = 'return'
            s.returnStartTime = now
          }
        } else {
          const returnElapsed = now - s.returnStartTime
          const returnProgress = Math.min(returnElapsed / 200, 1)
          if (returnProgress >= 1) {
            playerMesh.scale.y = s.startScaleY
            playerMesh.position.y = s.startY
            playerMesh.rotation.x = 0
            isSliding.value = false
            slideFallbackState = null
            playAnimationState('running')
          } else {
            playerMesh.scale.y = 0.5 + (s.startScaleY - 0.5) * returnProgress
            playerMesh.position.y = 0.3 + (s.startY - 0.3) * returnProgress
            playerMesh.rotation.x = 0.5 * (1 - returnProgress)
          }
        }
      }

      // Смена полосы
      if (laneTransitionTargetX !== null) {
        const elapsed = now - laneTransitionStartTime
        const progress = Math.min(elapsed / LANE_CHANGE_DURATION_MS, 1)
        const ease = progress < 0.5
          ? 2 * progress * progress
          : 1 - Math.pow(-2 * progress + 2, 2) / 2
        playerMesh.position.x = laneTransitionStartX + (laneTransitionTargetX - laneTransitionStartX) * ease
        if (progress >= 1) {
          playerMesh.position.x = laneTransitionTargetX
          laneTransitionTargetX = null
        }
      } else {
        playerMesh.position.x = playerPosition.value.x
      }

      // Анимация бега (только для кубического фоллбэка)
      if (playerMesh.children && playerMesh.children.length > 0 && !mixer) {
        let u = playerMesh.userData
        if (!u._leftArm) {
          u._leftArm = playerMesh.children.find(c => c.name === 'leftArm')
          u._rightArm = playerMesh.children.find(c => c.name === 'rightArm')
          u._leftLeg = playerMesh.children.find(c => c.name === 'leftLeg')
          u._rightLeg = playerMesh.children.find(c => c.name === 'rightLeg')
        }
        const leftArm = u._leftArm
        const rightArm = u._rightArm
        const leftLeg = u._leftLeg
        const rightLeg = u._rightLeg

        if (!isJumping.value && !isSliding.value) {
          const time = now * 0.001
          const runSpeed = 1.5
          playerMesh.rotation.z = Math.sin(time * runSpeed) * 0.05
          if (leftArm && rightArm) {
            leftArm.rotation.x = Math.sin(time * runSpeed) * 0.8
            rightArm.rotation.x = -Math.sin(time * runSpeed) * 0.8
          }
          if (leftLeg && rightLeg) {
            leftLeg.rotation.x = -Math.sin(time * runSpeed) * 0.5
            rightLeg.rotation.x = Math.sin(time * runSpeed) * 0.5
          }
          const baseY = isSliding.value ? 0.3 : 0
          playerMesh.position.y = baseY + Math.abs(Math.sin(time * runSpeed * 2)) * 0.1
        } else {
          playerMesh.rotation.z = 0
          if (leftArm && rightArm) {
            leftArm.rotation.x = 0
            rightArm.rotation.x = 0
          }
          if (leftLeg && rightLeg) {
            leftLeg.rotation.x = 0
            rightLeg.rotation.x = 0
          }
        }
      }
    }
  }

  // Простой AABB: от ног (position.y) вверх на 1.5 — без setFromObject (дорого для GLB).
  // Центр смещён вверх на 0.75, чтобы при прыжке (y=1.7) низ бокса был 1.7 и перепрыгивал барьер 0.9.
  const _playerBoxSize = new Vector3(0.8, 1.5, 0.6)
  const _playerBoxCenter = new Vector3()
  let _playerBoxCache = null
  const getPlayerBox = () => {
    if (!playerMesh) return null
    if (!_playerBoxCache) _playerBoxCache = new Box3()
    const feetY = getPlayerY()
    _playerBoxCenter.set(playerMesh.position.x, feetY + 0.75, playerMesh.position.z)
    _playerBoxCache.setFromCenterAndSize(_playerBoxCenter, _playerBoxSize)
    return _playerBoxCache
  }

  /** X-координата камеры по текущей полосе (-2, 0, 2) — для привязки камеры за персонажем */
  const getCameraLaneX = () => lanes[playerLane.value]

  /** Время начала последнего слайда (Date.now()). Нужно для окна неуязвимости к ROLL по времени. */
  const getSlideStartTime = () => slideStartTime

  /** Сброс состояния слайда при старте нового забега. */
  const resetSlideState = () => {
    slideStartTime = 0
    slideLandState = null
    slideFallbackState = null
    isSliding.value = false
  }

  /** Сброс перехода полосы при старте забега. */
  const resetLaneTransition = () => {
    laneTransitionTargetX = null
  }

  return {
    playerPosition,
    playerLane,
    isJumping,
    isSliding,
    moveLeft,
    moveRight,
    jump,
    slide,
    getPlayerY,
    getCameraLaneX,
    getSlideStartTime,
    resetSlideState,
    resetLaneTransition,
    createPlayer,
    loadPlayerModel,
    setAnimationState: playAnimationState,
    update,
    playerMesh: () => playerMesh,
    getPlayerBox
  }
}
