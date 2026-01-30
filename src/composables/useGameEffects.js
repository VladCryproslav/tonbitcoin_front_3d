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
  const _toRemove = []
  const _deferredDispose = []

  // Создание эффекта сбора энергии
  const createEnergyCollectEffect = (position) => {
    // Защита от некорректных координат (NaN/Infinity),
    // которые приводят к ошибке THREE.BufferGeometry.computeBoundingSphere().
    const safePos = {
      x: Number.isFinite(position?.x) ? position.x : 0,
      y: Number.isFinite(position?.y) ? position.y : 0,
      z: Number.isFinite(position?.z) ? position.z : 0
    }

    const particleCount = 20
    const geometry = new BufferGeometry()
    const positions = new Float32Array(particleCount * 3)
    const colors = new Float32Array(particleCount * 3)
    const velocity = []
    
    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3
      positions[i3] = safePos.x + (Math.random() - 0.5) * 0.5
      positions[i3 + 1] = safePos.y + (Math.random() - 0.5) * 0.5
      positions[i3 + 2] = safePos.z + (Math.random() - 0.5) * 0.5
      
      // Зеленый цвет для энергии
      colors[i3] = 0
      colors[i3 + 1] = 1
      colors[i3 + 2] = 0
      // Отдельный вектор скорости для каждой частицы
      velocity.push({
        x: (Math.random() - 0.5) * 0.02,
        y: (Math.random() - 0.5) * 0.02 + 0.01,
        z: (Math.random() - 0.5) * 0.02
      })
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
      velocity
    }
    
    scene.add(points)
    particles.value.push(points)
    
    return points
  }
  
  // Создание эффекта столкновения
  const createCollisionEffect = (position) => {
    const safePos = {
      x: Number.isFinite(position?.x) ? position.x : 0,
      y: Number.isFinite(position?.y) ? position.y : 0,
      z: Number.isFinite(position?.z) ? position.z : 0
    }

    const particleCount = 15
    const geometry = new BufferGeometry()
    const positions = new Float32Array(particleCount * 3)
    const colors = new Float32Array(particleCount * 3)
    const velocity = []
    
    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3
      positions[i3] = safePos.x + (Math.random() - 0.5) * 0.8
      positions[i3 + 1] = safePos.y + (Math.random() - 0.5) * 0.8
      positions[i3 + 2] = safePos.z + (Math.random() - 0.5) * 0.8
      
      // Красный цвет для столкновения
      colors[i3] = 1
      colors[i3 + 1] = 0
      colors[i3 + 2] = 0
      // Вектор скорости для каждой частицы
      velocity.push({
        x: (Math.random() - 0.5) * 0.03,
        y: (Math.random() - 0.5) * 0.03,
        z: (Math.random() - 0.5) * 0.03
      })
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
      velocity
    }
    
    scene.add(points)
    particles.value.push(points)
    
    return points
  }
  
  // Обновление всех эффектов. Dispose откладываем на следующий кадр — меньше микрофриза при наборе скорости.
  const updateEffects = () => {
    _deferredDispose.forEach(({ geometry, material }) => {
      geometry.dispose()
      material.dispose()
    })
    _deferredDispose.length = 0

    const now = Date.now()
    _toRemove.length = 0
    const toRemove = _toRemove

    particles.value.forEach((particle, index) => {
      const elapsed = now - particle.userData.startTime
      const progress = elapsed / particle.userData.duration

      if (progress >= 1) {
        scene.remove(particle)
        _deferredDispose.push({ geometry: particle.geometry, material: particle.material })
        toRemove.push(index)
      } else {
        const positions = particle.geometry.attributes.position.array
        const velArray = particle.userData.velocity
        for (let i = 0; i < positions.length; i += 3) {
          const vel = velArray[Math.floor(i / 3)]
          if (!vel) continue
          positions[i] += vel.x
          positions[i + 1] += vel.y
          positions[i + 2] += vel.z
        }
        particle.geometry.attributes.position.needsUpdate = true
        particle.material.opacity = 1 - progress
      }
    })

    toRemove.sort((a, b) => b - a).forEach((index) => {
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
    _deferredDispose.forEach(({ geometry, material }) => {
      geometry.dispose()
      material.dispose()
    })
    _deferredDispose.length = 0
  }
  
  return {
    createEnergyCollectEffect,
    createCollisionEffect,
    updateEffects,
    clearAll
  }
}
