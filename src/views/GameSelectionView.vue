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
        </div>

        <!-- В разработке -->
        <div class="game-card development-card" @click="goToInDevelopment">
          <div class="game-card-bg"></div>
          <div class="development-overlay"></div>
          <h2 class="game-title">{{ t('games.in_development') }}</h2>
        </div>
      </div>
    </div>

    <!-- Back Button -->
    <div class="back-button-container">
      <button class="back-button" @click="goBack">
        {{ t('games.go_back') }}
      </button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.game-selection-screen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100vh;
  background: #11151A;
  display: flex;
  flex-direction: column;
  z-index: 1000;
}

.main-content {
  flex: 1;
  padding: 48px 15px 120px;
  overflow-y: auto;
  background: radial-gradient(circle at 50% 0%, rgba(103, 98, 240, 1) 0%, rgba(103, 98, 240, 0) 100%), #0B150F;

  .games-container {
    display: flex;
    flex-direction: column;
    gap: 20px;
    max-width: 358px;
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
    background: url('@/assets/wheel-icon.svg'),
                radial-gradient(circle at 50% 0%, rgba(129, 67, 252, 0) 0%, rgba(129, 67, 252, 1) 100%),
                rgba(0, 0, 0, 0.2),
                rgba(129, 67, 252, 0.2);
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
  }
}

.lottery-card {
  .game-card-bg {
    background: url('@/assets/lottery-icon.svg'),
                radial-gradient(circle at 50% 0%, rgba(129, 67, 252, 0) 0%, rgba(129, 67, 252, 1) 100%),
                rgba(0, 0, 0, 0.2),
                rgba(129, 67, 252, 0.2);
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
  }
}

.development-card {
  .game-card-bg {
    background: url('@/assets/development-icon.svg'),
                radial-gradient(circle at 50% 0%, rgba(129, 67, 252, 0) 0%, rgba(129, 67, 252, 1) 100%),
                rgba(0, 0, 0, 0.2),
                rgba(129, 67, 252, 0.2);
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
  }

  .development-overlay {
    position: absolute;
    top: 2px;
    left: 1px;
    right: 1px;
    bottom: 2px;
    background: radial-gradient(circle at 50% 0%, rgba(129, 67, 252, 0) 0%, rgba(129, 67, 252, 1) 100%),
                rgba(0, 0, 0, 0.2),
                rgba(129, 67, 252, 0.2);
    backdrop-filter: blur(10px);
    border-radius: 13px;
    z-index: 1;
  }
}

.back-button-container {
  position: fixed;
  bottom: 120px;
  left: 0;
  right: 0;
  padding: 16px;
  background: rgba(16, 21, 27, 0.25);
  backdrop-filter: blur(9px);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  z-index: 1002;

  .back-button {
    width: 100%;
    height: 50px;
    background: #8143FC;
    border: none;
    border-radius: 10px;
    color: #FFFFFF;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 18px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: opacity 0.2s ease;

    &:hover {
      opacity: 0.8;
    }

    &:active {
      opacity: 0.6;
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
</style>
