<script setup>
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const { t } = useI18n()

const goToWheel = () => {
  router.push('/wheel')
}

const goToLottery = () => {
  // TODO: Создать страницу лотереи
  console.log('Lottery coming soon')
}

const goToInDevelopment = () => {
  // TODO: Показать модальное окно "В разработке"
  console.log('In development')
}

const goBack = () => {
  router.back()
}
</script>

<template>
  <div class="game-selection-screen">
    <!-- Main Content -->
    <div class="main-content">
      <div class="games-container">
        <!-- Колесо Фортуны -->
        <div class="game-card wheel-card" @click="goToWheel">
          <div class="game-card-bg"></div>
          <h2 class="game-title">{{ t('games.wheel_of_fortune') }}</h2>
        </div>

        <!-- Лотерея -->
        <div class="game-card lottery-card" @click="goToLottery">
          <div class="game-card-bg"></div>
          <h2 class="game-title">{{ t('games.lottery') }}</h2>
          <div class="new-badge">New!</div>
        </div>

        <!-- В разработке -->
        <div class="game-card development-card" @click="goToInDevelopment">
          <div class="game-card-bg"></div>
          <div class="development-overlay"></div>
          <h2 class="game-title">{{ t('games.in_development') }}</h2>
        </div>
      </div>

      <!-- Back Button -->
      <div class="back-button-container">
        <button class="back-button" @click="goBack">
          {{ t('games.go_back') }}
        </button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.game-selection-screen {
  width: 100%;
  min-height: 100vh;
  background: #11151A;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  padding: 48px 15px 120px;
  overflow-y: auto;
  background: radial-gradient(circle at 50% 0%, rgba(103, 98, 240, 0.6) 0%, rgba(103, 98, 240, 0) 100%), #080A08;
  display: flex;
  flex-direction: column;

  .games-container {
    display: flex;
    flex-direction: column;
    gap: 20px;
    width: 100%;
    margin: 0 auto;
  }
}

.game-card {
  position: relative;
  width: 100%;
  height: 140px;
  border: 2px solid #8143FC;
  border-radius: 15px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  overflow: hidden;
  box-shadow: 0px 0px 7px 0px rgba(129, 67, 252, 0.8);
  transition: transform 0.2s ease, box-shadow 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0px 4px 15px 0px rgba(129, 67, 252, 1);
  }

  &:active {
    transform: translateY(0);
  }

  .game-card-bg {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
  }

  .game-title {
    position: relative;
    z-index: 2;
    color: #FFFFFF;
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    font-size: 30px;
    text-align: center;
    margin: 0;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
  }
}

.wheel-card {
  .game-card-bg {
    background: url('@/assets/wheelgamebutton.jpg');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
  }
}

.lottery-card {
  .game-card-bg {
    background: url('@/assets/lotgamebutton.jpg');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
  }

  .new-badge {
    position: absolute;
    top: 10px;
    left: 10px;
    background: #ff0000;
    color: #fff;
    padding: 6px 12px;
    border-radius: 20px;
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(255, 0, 0, 0.3);
    animation: pulse-glow 2s ease-in-out infinite;
    z-index: 10;
    min-width: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

.development-card {
  .game-card-bg {
    background: url('@/assets/indevgamebutton.jpg');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
  }

  .development-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(circle at 50% 0%, rgba(129, 67, 252, 0) 0%, rgba(129, 67, 252, 1) 100%),
                rgba(0, 0, 0, 0.4),
                rgba(129, 67, 252, 0.4);
    backdrop-filter: blur(8px);
    border-radius: 15px;
    z-index: 1;
  }

  .game-title {
    overflow: hidden;
    background: linear-gradient(90deg, transparent, #fff, transparent);
    background-repeat: no-repeat;
    background-size: 80%;
    animation: shine 3s linear infinite;
    background-clip: text;
    -webkit-background-clip: text;
    -webkit-text-fill-color: rgba(255, 255, 255, 0);
  }
}

.back-button-container {
  position: fixed;
  bottom: 120px;
  left: 0;
  right: 0;
  padding: 16px;
  z-index: 1002;

  .back-button {
    width: 100%;
    height: 48px;
    padding: 10px 0;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
    border: 1px solid #8143fc;
    border-radius: 10px;
    color: #fff;
    font-family: 'Inter';
    font-weight: 600;
    font-size: clamp(14px, 4dvw, 18px);
    letter-spacing: 0px;
    transition: all 100ms ease;
    background: #8143fc;

    &:active {
      opacity: 0.5;
      scale: 0.95;
    }
  }
}


// Responsive adjustments
@media (max-width: 390px) {
  .main-content {
    padding: 48px 15px 120px;
  }

  .game-card {
    height: 140px;

    .game-title {
      font-size: 30px;
    }
  }
}

// Animation keyframes
@keyframes shine {
  0% {
    background-position: -500%;
  }

  100% {
    background-position: 500%;
  }
}

@keyframes pulse-glow {
  0% {
    opacity: 0.7;
    transform: scale(1);
    box-shadow: 0 2px 8px rgba(255, 0, 0, 0.3);
  }

  50% {
    opacity: 1;
    transform: scale(1.05);
    box-shadow: 0 4px 16px rgba(255, 0, 0, 0.6);
  }

  100% {
    opacity: 0.7;
    transform: scale(1);
    box-shadow: 0 2px 8px rgba(255, 0, 0, 0.3);
  }
}
</style>
