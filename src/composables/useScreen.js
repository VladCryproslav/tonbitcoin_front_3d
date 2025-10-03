import { ref, onMounted, onUnmounted } from 'vue'

/**
 * Vue composable для отримання розширення екрану та типу пристрою
 * @returns {Object} Об'єкт з реактивними властивостями розміру екрану
 */
export function useScreen() {
  // Реактивні змінні
  const width = ref(0)
  const height = ref(0)
  const isMobile = ref(false)
  const isTablet = ref(false)
  const isLaptop = ref(false)
  const isDesktop = ref(false)
  const deviceType = ref('')

  // Брейкпоінти (можна налаштувати під потреби проєкту)
  const breakpoints = {
    mobile: 768,
    tablet: 1024,
    laptop: 1366,
    desktop: 1920
  }

  // Функція для оновлення розмірів
  const updateSize = () => {
    width.value = window.innerWidth
    height.value = window.innerHeight

    // Визначення типу пристрою
    if (width.value < breakpoints.mobile) {
      isMobile.value = true
      isTablet.value = false
      isLaptop.value = false
      isDesktop.value = false
      deviceType.value = 'mobile'
    } else if (width.value < breakpoints.tablet) {
      isMobile.value = false
      isTablet.value = true
      isLaptop.value = false
      isDesktop.value = false
      deviceType.value = 'tablet'
    } else if (width.value < breakpoints.laptop) {
      isMobile.value = false
      isTablet.value = false
      isLaptop.value = true
      isDesktop.value = false
      deviceType.value = 'laptop'
    } else {
      isMobile.value = false
      isTablet.value = false
      isLaptop.value = false
      isDesktop.value = true
      deviceType.value = 'desktop'
    }
  }

  // Додатковий хелпер для перевірки конкретних розмірів
  const isSize = (size) => {
    switch (size) {
      case 'xs': return width.value < 576
      case 'sm': return width.value >= 576 && width.value < 768
      case 'md': return width.value >= 768 && width.value < 992
      case 'lg': return width.value >= 992 && width.value < 1200
      case 'xl': return width.value >= 1200 && width.value < 1400
      case 'xxl': return width.value >= 1400
      default: return false
    }
  }

  // Перевірка мінімальної ширини
  const isMinWidth = (minWidth) => width.value >= minWidth

  // Перевірка максимальної ширини
  const isMaxWidth = (maxWidth) => width.value <= maxWidth

  // Перевірка діапазону ширини
  const isBetween = (min, max) => width.value >= min && width.value <= max

  onMounted(() => {
    updateSize()
    window.addEventListener('resize', updateSize)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', updateSize)
  })

  return {
    // Розміри екрану
    width,
    height,
    
    // Типи пристроїв
    isMobile,
    isTablet,
    isLaptop,
    isDesktop,
    deviceType,
    
    // Брейкпоінти
    breakpoints,
    
    // Хелпери
    isSize,
    isMinWidth,
    isMaxWidth,
    isBetween
  }
}