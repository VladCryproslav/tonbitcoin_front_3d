<template>
  <div class="lottery-screen">
    <!-- Header -->
    <div class="header">
      <div class="header-content">
        <button class="back-button" @click="goBack">
          <span>Cancel</span>
        </button>
        <div class="title-section">
          <h1 class="title">Mining game</h1>
          <span class="subtitle">bot</span>
        </div>
        <div class="menu-button">
          <span>􀍡</span>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="main-content">
      <!-- Lottery Main Section -->
      <div class="lottery-main">
        <div class="lottery-bg"></div>
        <div class="lottery-content">
          <div class="lottery-header">
            <h2 class="lottery-title">Лотерея</h2>
            <div class="close-icon"></div>
          </div>

          <div class="lottery-info">
            <h3 class="station-name">Орбитальная электростанция</h3>
            <div class="ticket-stats">
              <div class="stat-item">
                <span class="stat-label">Всего билетов:</span>
                <div class="stat-value">
                  <span class="stat-number">150</span>
                  <div class="stat-icon"></div>
                </div>
              </div>
              <div class="stat-item">
                <span class="stat-label">Осталось билетов:</span>
                <div class="stat-value">
                  <span class="stat-number">50</span>
                  <div class="stat-icon"></div>
                </div>
              </div>
            </div>
          </div>

          <button class="buy-ticket-btn" @click="buyTicket">
            <span class="btn-text">Купить билет</span>
            <div class="price-section">
              <div class="price-icon"></div>
              <span class="price">10</span>
            </div>
          </button>
        </div>
      </div>

      <!-- Participants List -->
      <div class="participants-section">
        <div class="participants-header">
          <h3 class="participants-title">Список учасников</h3>
          <div class="participants-count">
            <div class="count-icon"></div>
            <span class="count-text">100 чел.</span>
          </div>
        </div>

        <div class="participants-list">
          <div class="participant-card" v-for="(participant, index) in participants" :key="index">
            <div class="participant-info">
              <div class="participant-rank">#{{ participant.rank }}</div>
              <div class="participant-details">
                <div class="participant-name">{{ participant.name }}</div>
                <div class="participant-address">{{ participant.address }}</div>
                <div class="participant-tickets">
                  <div class="ticket-icon"></div>
                  <span class="ticket-count">{{ participant.tickets }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="pagination">
          <div class="page-numbers">
            <div class="page-number active">1</div>
            <div class="page-number">2</div>
            <div class="page-number">3</div>
            <div class="page-number">4</div>
            <div class="page-number">5</div>
            <span class="dots">...</span>
            <div class="page-number">98</div>
            <div class="page-number">99</div>
            <div class="page-number">100</div>
          </div>
          <div class="pagination-controls">
            <button class="page-btn prev">Пред. страница</button>
            <button class="page-btn next">След. страница</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const participants = ref([
  {
    rank: 1,
    name: 'Vadim',
    address: 'UQD4XIdaIRt-42j4d6GIFj7....',
    tickets: 20
  },
  {
    rank: 2,
    name: 'Vadim',
    address: 'UQD4XIdaIRt-42j4d6GIFj7....',
    tickets: 20
  },
  {
    rank: 2,
    name: 'Vadim',
    address: 'UQD4XIdaIRt-42j4d6GIFj7....',
    tickets: 20
  }
])

const goBack = () => {
  router.back()
}

const buyTicket = () => {
  // TODO: Implement TON Connect payment
  console.log('Buy ticket clicked')
}
</script>

<style lang="scss" scoped>
.lottery-screen {
  width: 100%;
  min-height: 100vh;
  background: #11151A;
  display: flex;
  flex-direction: column;
}

.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(50px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);

  .header-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px;
    height: 68px;

    .back-button {
      background: none;
      border: none;
      color: #fff;
      font-family: 'Inter', sans-serif;
      font-size: 17px;
      cursor: pointer;
    }

    .title-section {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1px;

      .title {
        color: #fff;
        font-family: 'Inter', sans-serif;
        font-size: 17px;
        font-weight: 400;
        margin: 0;
      }

      .subtitle {
        color: #707579;
        font-family: 'Roboto', sans-serif;
        font-size: 13px;
        font-weight: 400;
      }
    }

    .menu-button {
      color: #fff;
      font-size: 18px;
      cursor: pointer;
    }
  }
}

.main-content {
  flex: 1;
  padding: 68px 16px 120px;
  background: #0B150F;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.lottery-main {
  position: relative;
  width: 100%;
  height: 465px;
  border-radius: 25px;
  overflow: hidden;
  margin: 20px 0;

  .lottery-bg {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: url('@/assets/Orbital Power Plant.webp');
    background-size: cover;
    background-position: center;
    opacity: 0.4;
  }

  .lottery-content {
    position: relative;
    z-index: 2;
    padding: 15px;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 15px;

    .lottery-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      max-width: 223px;

      .lottery-title {
        color: #fff;
        font-family: 'Inter', sans-serif;
        font-size: 28px;
        font-weight: 600;
        margin: 0;
      }

      .close-icon {
        width: 16px;
        height: 16px;
        background: #fff;
        mask: url('@/assets/close-modal.svg') no-repeat center;
        mask-size: contain;
        cursor: pointer;
      }
    }

    .lottery-info {
      text-align: center;
      max-width: 262px;

      .station-name {
        color: #fff;
        font-family: 'Inter', sans-serif;
        font-size: 20px;
        font-weight: 600;
        margin: 0 0 10px 0;
      }

      .ticket-stats {
        display: flex;
        flex-direction: column;
        gap: 10px;

        .stat-item {
          display: flex;
          justify-content: space-between;
          align-items: center;

          .stat-label {
            color: #fff;
            font-family: 'Inter', sans-serif;
            font-size: 14px;
            font-weight: 400;
            opacity: 0.5;
          }

          .stat-value {
            display: flex;
            align-items: center;
            gap: 5px;

            .stat-number {
              color: #fff;
              font-family: 'Inter', sans-serif;
              font-size: 14px;
              font-weight: 400;
            }

            .stat-icon {
              width: 30px;
              height: 18px;
              background: url('@/assets/fBTC.webp');
              background-size: cover;
              background-position: center;
            }
          }
        }
      }
    }

    .buy-ticket-btn {
      background: linear-gradient(180deg, #FCD909 0%, #FEA400 100%);
      border: none;
      border-radius: 10px;
      padding: 15px 19px;
      width: 100%;
      max-width: 262px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      cursor: pointer;

      .btn-text {
        color: #000;
        font-family: 'Inter', sans-serif;
        font-size: 16px;
        font-weight: 600;
      }

      .price-section {
        display: flex;
        align-items: center;
        gap: 2px;

        .price-icon {
          width: 20px;
          height: 20px;
          background: url('@/assets/fBTC.webp');
          background-size: cover;
          background-position: center;
        }

        .price {
          color: #000;
          font-family: 'Inter', sans-serif;
          font-size: 16px;
          font-weight: 700;
        }
      }
    }
  }
}

.participants-section {
  background: radial-gradient(circle at 48% 5%, rgba(255, 255, 255, 1) 0%, rgba(255, 255, 255, 0) 100%),
              #131313;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 0;
  padding: 12px;
  margin-top: 20px;

  .participants-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    .participants-title {
      color: #fff;
      font-family: 'Inter', sans-serif;
      font-size: 18px;
      font-weight: 700;
      margin: 0;
    }

    .participants-count {
      display: flex;
      align-items: center;
      gap: 4px;

      .count-icon {
        width: 16px;
        height: 16px;
        background: url('@/assets/fBTC.webp');
        background-size: cover;
        background-position: center;
      }

      .count-text {
        color: #FCD909;
        font-family: 'Inter', sans-serif;
        font-size: 14px;
        font-weight: 700;
      }
    }
  }

  .participants-list {
    display: flex;
    flex-direction: column;
    gap: 9px;
    margin-bottom: 20px;

    .participant-card {
      background: rgba(0, 0, 0, 0.5);
      border-radius: 12px;
      padding: 12px;

      .participant-info {
        display: flex;
        align-items: center;
        gap: 10px;

        .participant-rank {
          color: #FCD909;
          font-family: 'Inter', sans-serif;
          font-size: 14px;
          font-weight: 700;
          min-width: 16px;
        }

        .participant-details {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 5px;

          .participant-name {
            color: #fff;
            font-family: 'Inter', sans-serif;
            font-size: 14px;
            font-weight: 500;
          }

          .participant-address {
            color: rgba(255, 255, 255, 0.8);
            font-family: 'Inter', sans-serif;
            font-size: 12px;
            font-weight: 600;
          }

          .participant-tickets {
            display: flex;
            align-items: center;
            gap: 5px;

            .ticket-icon {
              width: 37px;
              height: 22px;
              background: url('@/assets/fBTC.webp');
              background-size: cover;
              background-position: center;
            }

            .ticket-count {
              color: #fff;
              font-family: 'Inter', sans-serif;
              font-size: 14px;
              font-weight: 400;
            }
          }
        }
      }
    }
  }

  .pagination {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;

    .page-numbers {
      display: flex;
      align-items: center;
      gap: 3px;
      flex-wrap: wrap;
      justify-content: center;

      .page-number {
        width: 18px;
        height: 18px;
        background: rgba(8, 21, 10, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-family: 'Inter', sans-serif;
        font-size: 8px;
        font-weight: 500;
        cursor: pointer;

        &.active {
          background: linear-gradient(180deg, #FCD909 0%, #FEA400 100%);
          border: 1px solid linear-gradient(180deg, #DAD69B 0%, #FFBD0A 100%);
          color: #000;
          font-weight: 600;
          font-size: 12px;
        }
      }

      .dots {
        color: #fff;
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        font-weight: 600;
        margin: 0 5px;
      }
    }

    .pagination-controls {
      display: flex;
      gap: 17px;

      .page-btn {
        background: linear-gradient(180deg, #FCD909 0%, #FEA400 100%);
        border: 1px solid linear-gradient(180deg, #DAD69B 0%, #FFBD0A 100%);
        border-radius: 7px;
        padding: 11px 17px;
        color: #212121;
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;

        &.prev {
          opacity: 0.6;
        }
      }
    }
  }
}
</style>
