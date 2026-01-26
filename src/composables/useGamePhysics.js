import { ref, onMounted, onUnmounted } from 'vue'
import { BoxGeometry, MeshStandardMaterial, Mesh, Vector3 } from 'three'

export function useGamePhysics(scene) {
  const playerPosition = ref(new Vector3(0, 0, 0))
  const playerLane = ref(1) // 0 = left, 1 = center, 2 = right
  const isJumping = ref(false)
  const isSliding = ref(false)
  
  const lanes = [-2, 0, 2] // Позиции полос
  
  const moveLeft = () => {
    if (playerLane.value > 0) {
      playerLane.value--
      playerPosition.value.x = lanes[playerLane.value]
    }
  }
  
  const moveRight = () => {
    if (playerLane.value < 2) {
      playerLane.value++
      playerPosition.value.x = lanes[playerLane.value]
    }
  }
  
  const jump = () => {
    if (!isJumping.value && !isSliding.value) {
      isJumping.value = true
      setTimeout(() => {
        isJumping.value = false
      }, 600) // Длительность прыжка
    }
  }
  
  const slide = () => {
    if (!isSliding.value && !isJumping.value) {
      isSliding.value = true
      setTimeout(() => {
        isSliding.value = false
      }, 500) // Длительность скольжения
    }
  }
  
  const getPlayerY = () => {
    if (isJumping.value) return 1.5
    if (isSliding.value) return 0.3
    return 0
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
    getPlayerY
  }
}
