import {
  BufferGeometry,
  Float32BufferAttribute,
  Points,
  PointsMaterial
} from 'three'

export function useGameEffects(scene, quality = 'normal') {
  const isMedium = quality === 'medium'
  const isLow = quality === 'low'
  // На low эффекты всё равно не обновляем из GameRunView, но количество частиц держим минимальным на medium.
  const ENERGY_PARTICLE_COUNT = isLow ? 10 : (isMedium ? 12 : 20)
  const COLLISION_PARTICLE_COUNT = isLow ? 6 : (isMedium ? 8 : 15)
  // Обычный массив вместо ref — убираем reactivity из hot path (updateEffects вызывается каждый кадр)
  const _particles = []
  const _toRemove = []

  // Пул неактивных эффектов: переиспользуем Points вместо create/dispose
  const inactiveEnergyPool = []
  const inactiveCollisionPool = []

  // Общие материалы — один на тип, без dispose при возврате в пул
  const energyMaterial = new PointsMaterial({
    size: 0.2,
    vertexColors: true,
    transparent: true,
    opacity: 1
  })
  const collisionMaterial = new PointsMaterial({
    size: 0.3,
    vertexColors: true,
    transparent: true,
    opacity: 1
  })

  const createPooledEffect = (position, type) => {
    const safePos = {
      x: Number.isFinite(position?.x) ? position.x : 0,
      y: Number.isFinite(position?.y) ? position.y : 0,
      z: Number.isFinite(position?.z) ? position.z : 0
    }

    const isEnergy = type === 'energy'
    const particleCount = isEnergy ? ENERGY_PARTICLE_COUNT : COLLISION_PARTICLE_COUNT
    const pool = isEnergy ? inactiveEnergyPool : inactiveCollisionPool
    const material = isEnergy ? energyMaterial : collisionMaterial
    const spread = isEnergy ? 0.5 : 0.8
    const velScale = isEnergy ? 0.02 : 0.03
    const velBiasY = isEnergy ? 0.01 : 0
    const duration = isEnergy ? 500 : 300

    let points = pool.pop()
    if (!points) {
      const geometry = new BufferGeometry()
      const positions = new Float32Array(particleCount * 3)
      const colors = new Float32Array(particleCount * 3)
      for (let i = 0; i < particleCount; i++) {
        const i3 = i * 3
        colors[i3] = isEnergy ? 0 : 1
        colors[i3 + 1] = isEnergy ? 1 : 0
        colors[i3 + 2] = 0
      }
      geometry.setAttribute('position', new Float32BufferAttribute(positions, 3))
      geometry.setAttribute('color', new Float32BufferAttribute(colors, 3))
      points = new Points(geometry, material)
      points.userData = {
        type: isEnergy ? 'energyEffect' : 'collisionEffect',
        startTime: 0,
        duration,
        velocity: []
      }
      for (let i = 0; i < particleCount; i++) {
        points.userData.velocity.push({ x: 0, y: 0, z: 0 })
      }
    }

    const posArr = points.geometry.attributes.position.array
    const velArr = points.userData.velocity
    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3
      posArr[i3] = safePos.x + (Math.random() - 0.5) * spread
      posArr[i3 + 1] = safePos.y + (Math.random() - 0.5) * spread
      posArr[i3 + 2] = safePos.z + (Math.random() - 0.5) * spread
      velArr[i].x = (Math.random() - 0.5) * velScale
      velArr[i].y = (Math.random() - 0.5) * velScale + velBiasY
      velArr[i].z = (Math.random() - 0.5) * velScale
    }
    points.geometry.attributes.position.needsUpdate = true
    points.material.opacity = 1
    points.userData.startTime = performance.now()
    points.userData.duration = duration

    scene.add(points)
    _particles.push(points)
    return points
  }

  const createEnergyCollectEffect = (position) => createPooledEffect(position, 'energy')
  const createCollisionEffect = (position) => createPooledEffect(position, 'collision')

  const updateEffects = () => {
    const now = performance.now()
    _toRemove.length = 0
    const toRemove = _toRemove

    for (let i = 0; i < _particles.length; i++) {
      const particle = _particles[i]
      const elapsed = now - particle.userData.startTime
      const progress = elapsed / particle.userData.duration

      if (progress >= 1) {
        scene.remove(particle)
        const pool = particle.userData.type === 'energyEffect' ? inactiveEnergyPool : inactiveCollisionPool
        pool.push(particle)
        toRemove.push(i)
      } else {
        const positions = particle.geometry.attributes.position.array
        const velArray = particle.userData.velocity
        for (let j = 0; j < positions.length; j += 3) {
          const vel = velArray[Math.floor(j / 3)]
          if (!vel) continue
          positions[j] += vel.x
          positions[j + 1] += vel.y
          positions[j + 2] += vel.z
        }
        particle.geometry.attributes.position.needsUpdate = true
        particle.material.opacity = 1 - progress
      }
    }

    toRemove.sort((a, b) => b - a)
    toRemove.forEach((idx) => _particles.splice(idx, 1))
  }

  const clearAll = () => {
    _particles.forEach(particle => {
      scene.remove(particle)
      const pool = particle.userData.type === 'energyEffect' ? inactiveEnergyPool : inactiveCollisionPool
      pool.push(particle)
    })
    _particles.length = 0
  }

  return {
    createEnergyCollectEffect,
    createCollisionEffect,
    updateEffects,
    clearAll
  }
}
