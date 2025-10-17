<template>
  <div class="lottery-screen">
    <!-- Main Content -->
    <div class="main-content">
      <!-- Lottery Main Section -->
      <div class="lottery-main">
        <div class="lottery-bg"></div>
        <div class="lottery-content">
          <div class="station-info">
            <h3 class="station-title">Орбитальная электростанция</h3>
          </div>

          <div class="ticket-info">
            <div class="ticket-row">
              <span class="ticket-label">Всего билетов:</span>
              <div class="ticket-value">
                <span class="ticket-count">150</span>
                <div class="ticket-icon"></div>
              </div>
            </div>
            <div class="ticket-row">
              <span class="ticket-label">Осталось билетов:</span>
              <div class="ticket-value">
                <span class="ticket-count">50</span>
                <div class="ticket-icon"></div>
              </div>
            </div>
          </div>

          <button class="buy-ticket-btn" @click="buyTicket">
            <span class="btn-text">Купить билет</span>
            <div class="btn-price">
              <div class="diamond-icon"></div>
              <span class="price-amount">10</span>
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


.main-content {
  flex: 1;
  padding: 20px 16px 120px;
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
  margin: 0;

  .lottery-bg {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: url('@/assets/lottery-bg.png');
    background-size: cover;
    background-position: center;
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

    .station-info {
      text-align: center;
      max-width: 262px;

      .station-title {
        color: #fff;
        font-family: 'Inter', sans-serif;
        font-size: 20px;
        font-weight: 600;
        margin: 0;
      }
    }

    .ticket-info {
      display: flex;
      flex-direction: column;
      gap: 10px;
      width: 262px;

      .ticket-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 19px;

        .ticket-label {
          color: #fff;
          font-family: 'Inter', sans-serif;
          font-size: 14px;
          font-weight: 400;
          opacity: 0.5;
        }

        .ticket-value {
          display: flex;
          align-items: center;
          gap: 5px;

          .ticket-count {
            color: #fff;
            font-family: 'Inter', sans-serif;
            font-size: 14px;
            font-weight: 400;
          }

          .ticket-icon {
            width: 30px;
            height: 18px;
            background: url('@/assets/ticket-icon-6cfb78.png');
            background-size: cover;
            background-position: center;
          }
        }
      }
    }

    .buy-ticket-btn {
      background: radial-gradient(circle at 50% 100%, rgba(255, 255, 255, 1) 0%, rgba(255, 255, 255, 0) 100%),
                  linear-gradient(180deg, #FCD909 0%, #FEA400 100%);
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

      .btn-price {
        display: flex;
        align-items: center;
        gap: 5px;

        .diamond-icon {
          width: 20px;
          height: 20px;
          background: url('@/assets/diamond-icon.png');
          background-size: cover;
          background-position: center;
        }

        .price-amount {
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
  width: 358px;
  margin-left: auto;
  margin-right: auto;

  .participants-header {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 5px;
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
        background: url('@/assets/participants-icon.png');
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
        width: 337px;

        .participant-rank {
          color: #FCD909;
          font-family: 'Inter', sans-serif;
          font-size: 14px;
          font-weight: 700;
          width: 16px;
          text-align: right;
        }

        .participant-details {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 5px;
          width: 311px;

          .participant-name {
            color: #fff;
            font-family: 'Inter', sans-serif;
            font-size: 14px;
            font-weight: 500;
            letter-spacing: -0.011em;
          }

          .participant-address {
            color: rgba(255, 255, 255, 0.8);
            font-family: 'Inter', sans-serif;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: -0.011em;
          }

          .participant-tickets {
            display: flex;
            align-items: center;
            gap: 5px;

            .ticket-icon {
              width: 37px;
              height: 22px;
              background: url('@/assets/ticket-icon-6cfb78.png');
              background-size: cover;
              background-position: center;
            }

            .ticket-count {
              color: #fff;
              font-family: 'Inter', sans-serif;
              font-size: 14px;
              font-weight: 400;
              letter-spacing: -0.011em;
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
    width: 358px;
    margin-left: auto;
    margin-right: auto;

    .page-numbers {
      display: flex;
      align-items: center;
      gap: 3px;
      flex-wrap: wrap;
      justify-content: center;
      padding: 2px 10px 5px;

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
        padding: 0 3px;

        &.active {
          background: radial-gradient(circle at 50% 100%, rgba(255, 255, 255, 1) 0%, rgba(255, 255, 255, 0) 100%),
                      linear-gradient(180deg, #FCD909 0%, #FEA400 100%);
          border: 1px solid linear-gradient(180deg, #DAD69B 0%, #FFBD0A 100%);
          color: #000;
          font-weight: 600;
          font-size: 12px;
          width: 22px;
          height: 22px;
          border-radius: 6px;
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
      width: 277px;
      justify-content: center;

      .page-btn {
        background: radial-gradient(circle at 50% 100%, rgba(255, 255, 255, 1) 0%, rgba(255, 255, 255, 0) 100%),
                    linear-gradient(180deg, #FCD909 0%, #FEA400 100%);
        border: 1px solid linear-gradient(180deg, #DAD69B 0%, #FFBD0A 100%);
        border-radius: 7px;
        padding: 11px 17px;
        color: #212121;
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
        width: 130px;
        height: 37px;
        display: flex;
        align-items: center;
        justify-content: center;

        &.prev {
          opacity: 0.6;
        }
      }
    }
  }
}
</style>
