import { ref } from 'vue'
import { 
  BoxGeometry, 
  MeshStandardMaterial, 
  Mesh, 
  Vector3,
  PlaneGeometry,
  Group,
  Color
} from 'three'

export function useGameWorld(scene, camera) {
  const roadSegments = ref([])
  const obstacles = ref([])
  const collectibles = ref([])
  const roadSpeed = ref(0.3)
  const spawnDistance = ref(0)
  const lanes = [-2, 0, 2] // Позиции полос
  const laneMarkings = ref([])
  
  // Создание фона
  const createBackground = () => {
    // Небо (градиентный фон через несколько плоскостей)
    for (let i = 0; i < 3; i++) {
      const skyGeometry = new PlaneGeometry(50, 30)
      const skyColor = new Color()
      skyColor.setHSL(0.55, 0.3, 0.7 + i * 0.1) // От светлого к темному
      const skyMaterial = new MeshStandardMaterial({ 
        color: skyColor,
        side: 2 // DoubleSide
      })
      const sky = new Mesh(skyGeometry, skyMaterial)
      sky.position.set(0, 15 - i * 5, -20 - i * 10)
      sky.rotation.x = -Math.PI / 3
      scene.add(sky)
    }
    
    // Боковые барьеры с текстурами
    const barrierGeometry = new BoxGeometry(0.5, 2.5, 200)
    const barrierMaterial = new MeshStandardMaterial({ 
      color: 0x444444,
      metalness: 0.2,
      roughness: 0.8
    })
    
    // Левый барьер
    const leftBarrier = new Mesh(barrierGeometry, barrierMaterial)
    leftBarrier.position.set(-3.5, 1.25, 0)
    scene.add(leftBarrier)
    
    // Правый барьер
    const rightBarrier = new Mesh(barrierGeometry, barrierMaterial)
    rightBarrier.position.set(3.5, 1.25, 0)
    scene.add(rightBarrier)
    
    // Декоративные элементы на барьерах
    for (let i = 0; i < 10; i++) {
      const markerGeometry = new BoxGeometry(0.1, 0.3, 0.1)
      const markerMaterial = new MeshStandardMaterial({ color: 0xFFFF00 })
      
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
    const roadLength = 20
    const segmentCount = 5
    
    for (let i = 0; i < segmentCount; i++) {
      const roadGeometry = new PlaneGeometry(roadWidth, roadLength)
      const roadMaterial = new MeshStandardMaterial({ 
        color: 0x333333,
        roughness: 0.8
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
    
    for (let z = -50; z < 10; z += markingLength * 2) {
      lanes.forEach(laneX => {
        const markingGeometry = new BoxGeometry(markingWidth, 0.01, markingLength)
        const markingMaterial = new MeshStandardMaterial({ color: 0xFFFF00 })
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
          marking.position.z = lastMarking.position.z - markingLength * 2
        } else {
          marking.position.z = -50
        }
      }
    })
  }
  
  // Создание препятствия
  const createObstacle = (lane, z) => {
    const obstacleTypes = [
      { height: 1.5, color: 0xFF0000 }, // Низкое препятствие
      { height: 2.5, color: 0xCC0000 }, // Высокое препятствие
    ]
    
    const type = obstacleTypes[Math.floor(Math.random() * obstacleTypes.length)]
    const obstacleGeometry = new BoxGeometry(1, type.height, 1)
    const obstacleMaterial = new MeshStandardMaterial({ 
      color: type.color,
      metalness: 0.3,
      roughness: 0.7
    })
    const obstacle = new Mesh(obstacleGeometry, obstacleMaterial)
    obstacle.position.set(lanes[lane], type.height / 2, z)
    obstacle.userData = { type: 'obstacle', lane, height: type.height }
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
  
  // Генерация препятствий и предметов
  const spawnObjects = (playerZ) => {
    if (spawnDistance.value >= playerZ - 5) return
    
    spawnDistance.value = playerZ
    
    // Генерация препятствий (более часто при увеличении скорости)
    const obstacleChance = Math.min(0.5, 0.25 + (roadSpeed.value - 0.15) * 2)
    if (Math.random() < obstacleChance) {
      const lane = Math.floor(Math.random() * 3)
      createObstacle(lane, playerZ + 25)
      
      // Иногда создаем препятствие в соседней полосе (более сложно)
      if (Math.random() < 0.3) {
        const nextLane = (lane + (Math.random() < 0.5 ? 1 : -1) + 3) % 3
        createObstacle(nextLane, playerZ + 25)
      }
    }
    
    // Генерация собираемых предметов (чаще чем препятствия)
    const collectibleChance = 0.7 - (roadSpeed.value - 0.15) * 0.5
    if (Math.random() < collectibleChance) {
      const lane = Math.floor(Math.random() * 3)
      createCollectible(lane, playerZ + 20)
    }
    
    // Иногда генерируем несколько предметов подряд (бонусная линия)
    if (Math.random() < 0.15) {
      const startLane = Math.floor(Math.random() * 3)
      for (let i = 0; i < 3; i++) {
        const lane = (startLane + i) % 3
        createCollectible(lane, playerZ + 18 + i * 2)
      }
    }
    
    // Редко генерируем препятствие и предмет рядом (сложная ситуация)
    if (Math.random() < 0.1) {
      const lane = Math.floor(Math.random() * 3)
      createObstacle(lane, playerZ + 25)
      const collectibleLane = (lane + (Math.random() < 0.5 ? 1 : -1) + 3) % 3
      createCollectible(collectibleLane, playerZ + 22)
    }
  }
  
  // Обновление дорожки (бесконечная прокрутка)
  const updateRoad = (playerZ) => {
    roadSegments.value.forEach((segment, index) => {
      segment.position.z += roadSpeed.value
      
      // Перемещаем сегмент вперед когда он уходит назад
      if (segment.position.z > 10) {
        const lastSegment = roadSegments.value.reduce((min, seg) => 
          seg.position.z < min.position.z ? seg : min
        )
        segment.position.z = lastSegment.position.z - 20
      }
    })
    
    // Обновляем разметку
    updateLaneMarkings()
  }
  
  // Обновление препятствий
  const updateObstacles = (playerZ, playerX, playerY, onCollision) => {
    const obstaclesToRemove = []
    
    obstacles.value.forEach((obstacle, index) => {
      obstacle.position.z += roadSpeed.value
      
      // Проверка коллизии (улучшенная)
      const dx = obstacle.position.x - playerX
      const dz = obstacle.position.z - playerZ
      const dy = obstacle.position.y - playerY
      const distance = Math.sqrt(dx * dx + dz * dz)
      
      // Учитываем размер препятствия
      const obstacleHeight = obstacle.userData.height || 1.5
      const collisionRadius = 0.6
      
      if (distance < collisionRadius && Math.abs(dy) < obstacleHeight / 2 + 0.5) {
        onCollision()
        obstaclesToRemove.push(index)
        scene.remove(obstacle)
      } else if (obstacle.position.z > 10) {
        // Удаление ушедших препятствий
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
  const updateCollectibles = (playerZ, playerX, playerY, onCollect) => {
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
      
      // Проверка сбора
      const distance = Math.sqrt(
        Math.pow(collectible.position.x - playerX, 2) +
        Math.pow(collectible.position.z - playerZ, 2)
      )
      
      if (distance < 0.8 && Math.abs(collectible.position.y - playerY) < 1) {
        collectible.userData.collected = true
        onCollect(0.5) // Количество энергии
        collectiblesToRemove.push(index)
        scene.remove(collectible)
      } else if (collectible.position.z > 10) {
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
    spawnDistance.value = 0
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
