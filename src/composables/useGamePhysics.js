import { ref } from 'vue'
import {
  BoxGeometry,
  MeshStandardMaterial,
  Mesh,
  Vector3,
  PlaneGeometry,
  RepeatWrapping,
  TextureLoader,
  Group,
  AnimationMixer,
  Clock
} from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js'
import * as THREE from 'three'

export function useGamePhysics(scene) {
  const playerPosition = ref(new Vector3(0, 0, 0))
  const playerLane = ref(1) // 0 = left, 1 = center, 2 = right
  const isJumping = ref(false)
  const isSliding = ref(false)
  const playerY = ref(0)

  const lanes = [-2, 0, 2] // Позиции полос
  let playerMesh = null
  let jumpStartTime = 0
  let slideStartTime = 0
  let mixer = null // Для анимаций из GLTF
  let clock = new Clock()
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

          // Если у меша нет текстурной карты — зададим базовый цвет,
          // чтобы он не выглядел просто серым.
          if (!child.material.map) {
            child.material.color.set(0xEB7D26)
            child.material.metalness = 0.1
            child.material.roughness = 0.9
          }
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

      if (playerMesh && !mixer) {
        const targetX = lanes[playerLane.value]
        animatePosition(playerMesh.position, 'x', targetX, 0.18)
      }
    }
  }

  const moveRight = () => {
    if (playerLane.value < 2) {
      playerLane.value++
      playerPosition.value.x = lanes[playerLane.value]

      if (playerMesh) {
        const targetX = lanes[playerLane.value]
        animatePosition(playerMesh.position, 'x', targetX, 0.18)
      }
    }
  }

  const jump = () => {
    if (!isJumping.value) {
      isJumping.value = true
      // Если во время прыжка был активный слайд — сбрасываем его,
      // чтобы новое действие не блокировалось старым состоянием.
      isSliding.value = false
      jumpStartTime = Date.now()

      // Переключаемся на анимацию прыжка, если есть
      playAnimationState('jump')

      if (playerMesh) {
        // Анимация прыжка
        const jumpHeight = 2.5
        const jumpDuration = 600

        animateJump(jumpHeight, jumpDuration)
      }
    }
  }

  const slide = () => {
    // Разрешаем слайд в любой момент, даже во время прыжка.
    // Если игрок был в прыжке — прерываем его и переходим в roll/slide.
    if (!isSliding.value) {
      // Сначала мягко "приземляем" персонажа, если он был в воздухе,
      // чтобы переход из прыжка в слайд не выглядел рваным.
      if (playerMesh) {
        const startY = playerMesh.position.y
        const startRotX = playerMesh.rotation.x
        const targetY = 0
        const targetRotX = 0
        const landDuration = 150 // мс
        const landStart = Date.now()

        const land = () => {
          const t = Math.min((Date.now() - landStart) / landDuration, 1)
          // плавное сглаживание (smoothstep)
          const k = t * t * (3 - 2 * t)
          playerMesh.position.y = startY + (targetY - startY) * k
          playerMesh.rotation.x = startRotX + (targetRotX - startRotX) * k
          if (t < 1 && isSliding.value) {
            requestAnimationFrame(land)
          }
        }
        // Стартуем приземление параллельно с roll
        requestAnimationFrame(land)
      }

      isSliding.value = true
      isJumping.value = false
      slideStartTime = Date.now()

      // Переключаемся на анимацию переката/скольжения, если есть
      playAnimationState('roll')

      // Для GLB‑модели (mixer существует) всё скольжение делается только скелетной
      // анимацией клипа 3. Ни масштаб, ни позицию/вращение вручную не трогаем.
      // По завершении клипа возвращаемся в бег и снимаем isSliding.
      if (mixer) {
        const rollClip = animations[animationIndexByState.roll]
        const rollDuration = rollClip ? rollClip.duration * 1000 : 600
        setTimeout(() => {
          isSliding.value = false
          playAnimationState('running')
        }, rollDuration)
      } else if (playerMesh && !mixer) {
        // Плавная анимация скольжения для кубического фоллбэка
        const startY = playerMesh.position.y
        const startScaleY = playerMesh.scale.y
        const startTime = Date.now()
        const duration = 500

        const animate = () => {
          const elapsed = Date.now() - startTime
          const progress = Math.min(elapsed / duration, 1)

          if (progress < 1) {
            // Плавное уменьшение
            const scaleProgress = progress < 0.3 ? progress / 0.3 : 1
            playerMesh.scale.y = startScaleY - (startScaleY - 0.5) * scaleProgress
            playerMesh.position.y = startY - (startY - 0.3) * scaleProgress

            // Наклон вперед
            playerMesh.rotation.x = progress * 0.5

            requestAnimationFrame(animate)
          } else {
            // Возврат в исходное положение
            const returnStart = Date.now()
            const returnDuration = 200
            const returnAnimate = () => {
              const returnElapsed = Date.now() - returnStart
              const returnProgress = Math.min(returnElapsed / returnDuration, 1)

              if (returnProgress < 1) {
                playerMesh.scale.y = 0.5 + (startScaleY - 0.5) * returnProgress
                playerMesh.position.y = 0.3 + (startY - 0.3) * returnProgress
                playerMesh.rotation.x = 0.5 * (1 - returnProgress)
                requestAnimationFrame(returnAnimate)
              } else {
                playerMesh.scale.y = startScaleY
                playerMesh.position.y = startY
                playerMesh.rotation.x = 0
                isSliding.value = false
                // Возвращаем анимацию бега (только для кубического фоллбэка)
                playAnimationState('running')
              }
            }
            returnAnimate()
          }
        }
        animate()
      } else if (mixer) {
        // Для GLTF‑модели просто ждём завершения анимации roll по клипу.
        // Флаг скольжения сбросится извне, когда игра сочтёт нужным.
        // Здесь ничего не трогаем, чтобы не мешать скелетной анимации.
      }
    }
  }

  const animatePosition = (position, axis, target, duration) => {
    const start = position[axis]
    const startTime = Date.now()

    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / (duration * 1000), 1)

      // Easing функция
      const ease = progress < 0.5
        ? 2 * progress * progress
        : 1 - Math.pow(-2 * progress + 2, 2) / 2

      position[axis] = start + (target - start) * ease

      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }
    animate()
  }

  const animateJump = (height, duration) => {
    const startY = playerMesh.position.y
    const startTime = Date.now()

    const animate = () => {
      // Прыжок мог быть отменён (например, начался slide) — в этом случае
      // просто прекращаем дальнейшую анимацию подъёма/спуска.
      if (!isJumping.value) return
      const elapsed = Date.now() - startTime
      const progress = elapsed / duration

      if (progress < 1) {
        // Параболическая траектория с более реалистичной физикой
        const jumpCurve = Math.sin(progress * Math.PI)
        const y = startY + height * jumpCurve

        // Небольшой наклон при прыжке
        playerMesh.rotation.x = -progress * 0.3

        playerMesh.position.y = y

        requestAnimationFrame(animate)
      } else {
        playerMesh.position.y = startY
        playerMesh.rotation.x = 0
        isJumping.value = false
        // После прыжка возвращаемся к бегу
        playAnimationState('running')
      }
    }
    animate()
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
    // Обновление анимаций из GLTF модели
    if (mixer) {
      mixer.update(clock.getDelta())
    }

    if (playerMesh) {
      // Обновляем позицию игрока по X
      const targetX = playerPosition.value.x
      playerMesh.position.x += (targetX - playerMesh.position.x) * 0.2

      // Анимация бега - движение рук и ног (только для простой модели)
      // Для GLTF моделей анимации управляются через AnimationMixer
      if (playerMesh.children && playerMesh.children.length > 0 && !mixer) {
        if (!isJumping.value && !isSliding.value) {
        const time = Date.now() * 0.008
        const runSpeed = 1.5

        // Покачивание тела при беге
        playerMesh.rotation.z = Math.sin(time * runSpeed) * 0.05

        // Находим части тела по имени
        const leftArm = playerMesh.children.find(child => child.name === 'leftArm')
        const rightArm = playerMesh.children.find(child => child.name === 'rightArm')
        const leftLeg = playerMesh.children.find(child => child.name === 'leftLeg')
        const rightLeg = playerMesh.children.find(child => child.name === 'rightLeg')

        // Движение рук
        if (leftArm && rightArm) {
          leftArm.rotation.x = Math.sin(time * runSpeed) * 0.8
          rightArm.rotation.x = -Math.sin(time * runSpeed) * 0.8
        }

        // Движение ног
        if (leftLeg && rightLeg) {
          leftLeg.rotation.x = -Math.sin(time * runSpeed) * 0.5
          rightLeg.rotation.x = Math.sin(time * runSpeed) * 0.5
        }

        // Небольшое вертикальное покачивание при беге
        const baseY = isSliding.value ? 0.3 : 0
        playerMesh.position.y = baseY + Math.abs(Math.sin(time * runSpeed * 2)) * 0.1
      } else {
        // Сброс анимации при прыжке/скольжении
        playerMesh.rotation.z = 0
        const leftArm = playerMesh.children.find(child => child.name === 'leftArm')
        const rightArm = playerMesh.children.find(child => child.name === 'rightArm')
        const leftLeg = playerMesh.children.find(child => child.name === 'leftLeg')
        const rightLeg = playerMesh.children.find(child => child.name === 'rightLeg')

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

  // Ось‑aligned bounding box игрока для точной коллизии с препятствиями
  const getPlayerBox = () => {
    if (!playerMesh) return null
    const box = new THREE.Box3()
    box.setFromObject(playerMesh)
    return box
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
    createPlayer,
    loadPlayerModel,
    setAnimationState: playAnimationState,
    update,
    playerMesh: () => playerMesh,
    getPlayerBox
  }
}
