import { ref } from 'vue'
import { 
  BoxGeometry, 
  MeshStandardMaterial, 
  Mesh, 
  Vector3,
  Group,
  BufferGeometry,
  Float32BufferAttribute,
  Points,
  PointsMaterial,
  Color
} from 'three'

export function useGameEffects(scene) {
  const particles = ref([])
  
  // Создание эффекта сбора энергии
  const createEnergyCollectEffect = (position) => {
    const particleCount = 20
    const geometry = new BufferGeometry()
    const positions = new Float32Array(particleCount * 3)
    const colors = new Float32Array(particleCount * 3)
    
    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3
      positions[i3] = position.x + (Math.random() - 0.5) * 0.5
      positions[i3 + 1] = position.y + (Math.random() - 0.5) * 0.5
      positions[i3 + 2] = position.z + (Math.random() - 0.5) * 0.5
      
      // Зеленый цвет для энергии
      colors[i3] = 0
      colors[i3 + 1] = 1
      colors[i3 + 2] = 0
    }
    
    geometry.setAttribute('position', new Float32BufferAttribute(positions, 3))
    geometry.setAttribute('color', new Float32BufferAttribute(colors, 3))
    
    const material = new PointsMaterial({
      size: 0.2,
      vertexColors: true,
      transparent: true,
      opacity: 1
    })
    
    const points = new Points(geometry, material)
    points.userData = {
      type: 'energyEffect',
      startTime: Date.now(),
      duration: 500,
      velocity: positions.map((_, i) => ({
        x: (Math.random() - 0.5) * 0.02,
        y: (Math.random() - 0.5) * 0.02 + 0.01,
        z: (Math.random() - 0.5) * 0.02
      }))
    }
    
    scene.add(points)
    particles.value.push(points)
    
    return points
  }
  
  // Создание эффекта столкновения
  const createCollisionEffect = (position) => {
    const particleCount = 15
    const geometry = new BufferGeometry()
    const positions = new Float32Array(particleCount * 3)
    const colors = new Float32Array(particleCount * 3)
    
    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3
      positions[i3] = position.x + (Math.random() - 0.5) * 0.8
      positions[i3 + 1] = position.y + (Math.random() - 0.5) * 0.8
      positions[i3 + 2] = position.z + (Math.random() - 0.5) * 0.8
      
      // Красный цвет для столкновения
      colors[i3] = 1
      colors[i3 + 1] = 0
      colors[i3 + 2] = 0
    }
    
    geometry.setAttribute('position', new Float32BufferAttribute(positions, 3))
    geometry.setAttribute('color', new Float32BufferAttribute(colors, 3))
    
    const material = new PointsMaterial({
      size: 0.3,
      vertexColors: true,
      transparent: true,
      opacity: 1
    })
    
    const points = new Points(geometry, material)
    points.userData = {
      type: 'collisionEffect',
      startTime: Date.now(),
      duration: 300,
      velocity: positions.map((_, i) => ({
        x: (Math.random() - 0.5) * 0.03,
        y: (Math.random() - 0.5) * 0.03,
        z: (Math.random() - 0.5) * 0.03
      }))
    }
    
    scene.add(points)
    particles.value.push(points)
    
    return points
  }
  
  // Обновление всех эффектов
  const updateEffects = () => {
    const now = Date.now()
    const toRemove = []
    
    particles.value.forEach((particle, index) => {
      const elapsed = now - particle.userData.startTime
      const progress = elapsed / particle.userData.duration
      
      if (progress >= 1) {
        scene.remove(particle)
        particle.geometry.dispose()
        particle.material.dispose()
        toRemove.push(index)
      } else {
        // Обновление позиций частиц
        const positions = particle.geometry.attributes.position.array
        for (let i = 0; i < positions.length; i += 3) {
          const vel = particle.userData.velocity[i / 3]
          positions[i] += vel.x
          positions[i + 1] += vel.y
          positions[i + 2] += vel.z
        }
        particle.geometry.attributes.position.needsUpdate = true
        
        // Затухание
        particle.material.opacity = 1 - progress
      }
    })
    
    // Удаляем завершенные эффекты
    toRemove.sort((a, b) => b - a).forEach(index => {
      particles.value.splice(index, 1)
    })
  }
  
  // Очистка всех эффектов
  const clearAll = () => {
    particles.value.forEach(particle => {
      scene.remove(particle)
      particle.geometry.dispose()
      particle.material.dispose()
    })
    particles.value = []
  }
  
  return {
    createEnergyCollectEffect,
    createCollisionEffect,
    updateEffects,
    clearAll
  }
}
