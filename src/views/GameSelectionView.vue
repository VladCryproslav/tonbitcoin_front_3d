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
    <!-- Header -->
    <div class="header">
      <div class="header-content">
        <div class="header-left">
          <button class="cancel-btn" @click="goBack">
            {{ t('common.cancel') }}
          </button>
        </div>
        <div class="header-center">
          <h1 class="header-title">{{ t('games.title') }}</h1>
          <p class="header-subtitle">{{ t('games.subtitle') }}</p>
        </div>
        <div class="header-right">
          <button class="close-btn" @click="goBack">
            ✕
          </button>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="main-content">
      <div class="games-container">
        <!-- Колесо Фортуны -->
        <div class="game-card wheel-card" @click="goToWheel">
          <div class="game-card-bg"></div>
          <h2 class="game-title">{{ t('games.wheel_of_fortune') }}</h2>
          <div class="game-icon">
            <img src="@/assets/wheel-icon.webp" alt="Wheel" />
          </div>
        </div>

        <!-- Лотерея -->
        <div class="game-card lottery-card" @click="goToLottery">
          <div class="game-card-bg"></div>
          <h2 class="game-title">{{ t('games.lottery') }}</h2>
          <div class="game-icon">
            <img src="@/assets/wheel-icon.webp" alt="Lottery" />
          </div>
        </div>

        <!-- В разработке -->
        <div class="game-card development-card" @click="goToInDevelopment">
          <div class="game-card-bg"></div>
          <div class="development-overlay"></div>
          <h2 class="game-title">{{ t('games.in_development') }}</h2>
          <div class="game-icon">
            <img src="@/assets/wheel-icon.webp" alt="Development" />
          </div>
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

.header {
  background: rgba(16, 21, 27, 0.25);
  backdrop-filter: blur(9px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 44px; // Status bar height

  .header-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 16px;
    height: 36px;

    .header-left {
      min-width: 80px;

      .cancel-btn {
        background: none;
        border: none;
        color: #FFFFFF;
        font-family: 'SF Pro', sans-serif;
        font-weight: 400;
        font-size: 17px;
        cursor: pointer;
        padding: 11px 16px;

        &:hover {
          opacity: 0.7;
        }
      }
    }

    .header-center {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1px;

      .header-title {
        color: #FFFFFF;
        font-family: 'Inter', sans-serif;
        font-weight: 400;
        font-size: 17px;
        margin: 0;
        text-align: center;
      }

      .header-subtitle {
        color: #707579;
        font-family: 'Roboto', sans-serif;
        font-weight: 400;
        font-size: 13px;
        margin: 0;
        text-align: center;
      }
    }

    .header-right {
      min-width: 80px;
      display: flex;
      justify-content: flex-end;

      .close-btn {
        background: none;
        border: none;
        color: #FFFFFF;
        font-size: 18px;
        cursor: pointer;
        padding: 11px 16px;

        &:hover {
          opacity: 0.7;
        }
      }
    }
  }
}

.main-content {
  flex: 1;
  padding: 48px 15px;
  overflow-y: auto;

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

  .game-icon {
    position: absolute;
    top: 9px;
    right: 10px;
    z-index: 2;

    img {
      width: 24px;
      height: 24px;
      filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.5));
    }
  }
}

.wheel-card {
  .game-card-bg {
    background: radial-gradient(circle at 50% 0%, rgba(129, 67, 252, 0) 0%, rgba(129, 67, 252, 1) 100%),
                rgba(0, 0, 0, 0.2),
                rgba(129, 67, 252, 0.2);
    background-image: url('@/assets/wheel-back.webp');
  }
}

.lottery-card {
  .game-card-bg {
    background: radial-gradient(circle at 50% 0%, rgba(129, 67, 252, 0) 0%, rgba(129, 67, 252, 1) 100%),
                rgba(0, 0, 0, 0.2),
                rgba(129, 67, 252, 0.2);
    background-image: url('@/assets/wheel-back.webp');
  }
}

.development-card {
  .game-card-bg {
    background: radial-gradient(circle at 50% 0%, rgba(129, 67, 252, 0) 0%, rgba(129, 67, 252, 1) 100%),
                rgba(0, 0, 0, 0.2),
                rgba(129, 67, 252, 0.2);
    background-image: url('@/assets/wheel-back.webp');
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
  padding: 16px;
  background: rgba(16, 21, 27, 0.25);
  backdrop-filter: blur(9px);
  border-top: 1px solid rgba(255, 255, 255, 0.1);

  .back-button {
    width: 100%;
    height: 50px;
    background: linear-gradient(135deg, #8143FC 0%, #FFFFFF 100%);
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
    padding: 32px 15px;
  }

  .game-card {
    height: 120px;

    .game-title {
      font-size: 24px;
    }
  }
}
</style>
