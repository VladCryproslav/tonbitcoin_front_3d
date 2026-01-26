import { ref } from 'vue'
import { 
  BoxGeometry, 
  MeshStandardMaterial, 
  Mesh, 
  Vector3,
  PlaneGeometry,
  RepeatWrapping,
  TextureLoader,
  Group
} from 'three'
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
  
  // Создание модели игрока (простой куб для начала)
  const createPlayer = (gameScene) => {
    const gameSceneToUse = gameScene || scene
    if (!gameSceneToUse) return null
    
    const group = new Group()
    
    // Тело (инженер)
    const bodyGeometry = new BoxGeometry(0.8, 1.2, 0.6)
    const bodyMaterial = new MeshStandardMaterial({ 
      color: 0x8143FC,
      metalness: 0.3,
      roughness: 0.7
    })
    const body = new Mesh(bodyGeometry, bodyMaterial)
    body.position.y = 0.6
    body.castShadow = true
    group.add(body)
    
    // Голова (шлем инженера)
    const headGeometry = new BoxGeometry(0.6, 0.6, 0.6)
    const headMaterial = new MeshStandardMaterial({ 
      color: 0xFFD700,
      metalness: 0.8,
      roughness: 0.2,
      emissive: 0x332200,
      emissiveIntensity: 0.2
    })
    const head = new Mesh(headGeometry, headMaterial)
    head.position.y = 1.5
    head.castShadow = true
    group.add(head)
    
    // Руки
    const armGeometry = new BoxGeometry(0.2, 0.8, 0.2)
    const armMaterial = new MeshStandardMaterial({ color: 0x8143FC })
    
    const leftArm = new Mesh(armGeometry, armMaterial)
    leftArm.position.set(-0.5, 0.8, 0)
    group.add(leftArm)
    
    const rightArm = new Mesh(armGeometry, armMaterial)
    rightArm.position.set(0.5, 0.8, 0)
    group.add(rightArm)
    
    // Ноги
    const legGeometry = new BoxGeometry(0.25, 0.6, 0.25)
    const legMaterial = new MeshStandardMaterial({ color: 0x5A2FA0 })
    
    const leftLeg = new Mesh(legGeometry, legMaterial)
    leftLeg.position.set(-0.25, 0, 0)
    group.add(leftLeg)
    
    const rightLeg = new Mesh(legGeometry, legMaterial)
    rightLeg.position.set(0.25, 0, 0)
    group.add(rightLeg)
    
    group.position.set(0, 0, 0)
    gameSceneToUse.add(group)
    playerMesh = group
    
    return group
  }
  
  const moveLeft = () => {
    if (playerLane.value > 0 && !isJumping.value && !isSliding.value) {
      playerLane.value--
      playerPosition.value.x = lanes[playerLane.value]
      
      // Плавная анимация перемещения
      if (playerMesh) {
        const targetX = lanes[playerLane.value]
        animatePosition(playerMesh.position, 'x', targetX, 0.3)
      }
    }
  }
  
  const moveRight = () => {
    if (playerLane.value < 2 && !isJumping.value && !isSliding.value) {
      playerLane.value++
      playerPosition.value.x = lanes[playerLane.value]
      
      if (playerMesh) {
        const targetX = lanes[playerLane.value]
        animatePosition(playerMesh.position, 'x', targetX, 0.3)
      }
    }
  }
  
  const jump = () => {
    if (!isJumping.value && !isSliding.value) {
      isJumping.value = true
      jumpStartTime = Date.now()
      
      if (playerMesh) {
        // Анимация прыжка
        const jumpHeight = 2.5
        const jumpDuration = 600
        
        animateJump(jumpHeight, jumpDuration)
      }
    }
  }
  
  const slide = () => {
    if (!isSliding.value && !isJumping.value) {
      isSliding.value = true
      slideStartTime = Date.now()
      
      if (playerMesh) {
        // Плавная анимация скольжения
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
              }
            }
            returnAnimate()
          }
        }
        animate()
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
    if (playerMesh) {
      // Обновляем позицию игрока по X
      const targetX = playerPosition.value.x
      playerMesh.position.x += (targetX - playerMesh.position.x) * 0.2
      
      // Небольшая анимация бега (покачивание)
      if (!isJumping.value && !isSliding.value) {
        playerMesh.rotation.z = Math.sin(Date.now() * 0.01) * 0.1
      }
    }
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
    update,
    playerMesh: () => playerMesh
  }
}
