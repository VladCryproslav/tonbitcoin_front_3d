<template>
  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
  <div class="lottery-screen">
    <!-- Main Content -->
    <div class="main-content">
      <!-- Lottery Main Section -->
      <div class="lottery-main">
        <div class="lottery-bg"></div>
        <div class="lottery-content">
          <div class="lottery-header">
            <h2 class="lottery-title">Лотерея</h2>
            <div class="close-icon" @click="goBack"></div>
          </div>

          <div class="station-info">
            <div class="station-image"></div>
            <h3 class="station-title">Орбитальная электростанция</h3>
          </div>

          <div class="ticket-info">
            <div class="ticket-row">
              <span class="ticket-label">Всего билетов:</span>
              <div class="ticket-value">
                <span class="ticket-count">{{ lotteryData.totalTickets }}</span>
                <div class="ticket-icon"></div>
              </div>
            </div>
            <div class="ticket-row">
              <span class="ticket-label">Осталось билетов:</span>
              <div class="ticket-value">
                <span class="ticket-count">{{ lotteryData.remainingTickets }}</span>
                <div class="ticket-icon"></div>
              </div>
            </div>
          </div>

          <button class="buy-ticket-btn" @click="buyTicket" :disabled="isProcessing || !lotteryData.isActive || lotteryData.remainingTickets <= 0">
            <span class="btn-text">{{
              isProcessing ? 'Обработка...' :
              !lotteryData.isActive ? 'Лотерея не активна' :
              lotteryData.remainingTickets <= 0 ? 'Билеты распроданы' :
              'Купить билет'
            }}</span>
            <div class="btn-price">
              <div class="diamond-icon"></div>
              <span class="price-amount">0.01</span>
            </div>
          </button>
        </div>
      </div>

      <!-- Participants List -->
      <div class="participants-section">
        <div class="participants-header">
          <h3 class="participants-title">Список учасников</h3>
        </div>
        <div class="participants-count">
          <div class="count-icon"></div>
          <span class="count-text">{{ totalParticipants }} чел.</span>
        </div>

        <div class="participants-list">
          <div class="participant-card" v-for="(participant, index) in displayedParticipants" :key="index">
            <div class="participant-rank">#{{ (currentPage - 1) * itemsPerPage + index + 1 }}</div>
            <div class="participant-name">{{ participant.name }}</div>
            <div class="separator"></div>
            <div class="participant-address">{{ participant.address }}</div>
            <div class="separator"></div>
            <div class="participant-tickets">
              <div class="ticket-icon"></div>
              <span class="ticket-count">{{ participant.tickets }}</span>
            </div>
          </div>
        </div>

        <div class="pagination" v-if="totalPages > 1">
          <div class="page-numbers">
            <div
              class="page-number"
              :class="{ active: page === currentPage }"
              v-for="page in pageNumbers"
              :key="page"
              @click="typeof page === 'number' ? currentPage = page : null"
            >
              {{ page }}
            </div>
          </div>
          <div class="pagination-controls">
            <button
              class="page-btn prev"
              :class="{ unactive: currentPage === 1 }"
              @click="prevPage"
            >
              Пред. страница
            </button>
            <button
              class="page-btn next"
              :class="{ unactive: currentPage === totalPages }"
              @click="nextPage"
            >
              След. страница
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTonAddress, useTonConnectUI } from '@townsquarelabs/ui-vue'
import { toNano, beginCell } from '@ton/core'
import ModalNew from '@/components/ModalNew.vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import { host } from '../../axios.config'

const router = useRouter()
const { t } = useI18n()
const ton_address = useTonAddress()
const { tonConnectUI } = useTonConnectUI()
const app = useAppStore()

// Modal states
const openModal = ref(false)
const modalStatus = ref(null)
const modalTitle = ref(null)
const modalBody = ref(null)
const isProcessing = ref(false)

const participants = ref([
  { name: 'Vadim', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 20 },
  { name: 'Alex', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 15 },
  { name: 'Maria', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 30 },
  { name: 'John', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 25 },
  { name: 'Anna', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 18 },
  { name: 'Peter', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 22 },
  { name: 'Lisa', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 28 },
  { name: 'Mike', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 16 },
  { name: 'Sara', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 35 },
  { name: 'Tom', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 12 },
  { name: 'Emma', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 24 },
  { name: 'David', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 19 },
  { name: 'Kate', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 31 },
  { name: 'Chris', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 27 },
  { name: 'Nina', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 14 },
  { name: 'Mark', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 33 },
  { name: 'Julia', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 21 },
  { name: 'Paul', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 17 },
  { name: 'Elena', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 29 },
  { name: 'Steve', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 26 },
  { name: 'Olga', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 23 },
  { name: 'Igor', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 32 },
  { name: 'Tanya', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 18 },
  { name: 'Max', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 25 },
  { name: 'Irina', address: 'UQD4XIdaIRt-42j4d6GIFj7....', tickets: 20 }
])

const currentPage = ref(1)
const itemsPerPage = 25
const totalParticipants = computed(() => participants.value.length)

// Lottery data
const lotteryData = ref({
  totalTickets: 150,
  remainingTickets: 50,
  isActive: true
})

const totalPages = computed(() => Math.ceil(totalParticipants.value / itemsPerPage))

const displayedParticipants = computed(() => {
  return participants.value.slice(0, Math.min(itemsPerPage, participants.value.length))
})

const pageNumbers = computed(() => {
  const pages = []
  const total = totalPages.value

  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    pages.push(1)
    if (currentPage.value > 4) {
      pages.push('...')
    }

    const start = Math.max(2, currentPage.value - 1)
    const end = Math.min(total - 1, currentPage.value + 1)

    for (let i = start; i <= end; i++) {
      pages.push(i)
    }

    if (currentPage.value < total - 3) {
      pages.push('...')
    }

    if (total > 1) {
      pages.push(total)
    }
  }

  return pages
})

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

const showModal = (status, title, body) => {
  modalStatus.value = status
  modalTitle.value = title
  modalBody.value = body
  openModal.value = true
}

const goBack = () => {
  router.back()
}

// API functions for lottery
const fetchLotteryData = async () => {
  try {
    const response = await host.get('lottery/data/')
    if (response.status === 200) {
      lotteryData.value = response.data
    }
  } catch (err) {
    console.error('Error fetching lottery data:', err)
  }
}

const fetchParticipants = async () => {
  try {
    const response = await host.get('lottery/participants/')
    if (response.status === 200) {
      participants.value = response.data
    }
  } catch (err) {
    console.error('Error fetching participants:', err)
  }
}

const buyLotteryTicket = async (transactionHash) => {
  try {
    const response = await host.post('lottery/buy-ticket/', {
      wallet_address: ton_address.value,
      transaction_hash: transactionHash,
      amount: 0.01
    })

    if (response.status === 200) {
      // Обновляем данные лотереи и участников
      await fetchLotteryData()
      await fetchParticipants()
      return true
    }
    return false
  } catch (err) {
    console.error('Error buying lottery ticket:', err)
    return false
  }
}

const buyTicket = async () => {
  if (!ton_address.value) {
    showModal('warning', t('notification.st_attention'), t('notification.unconnected'))
    return
  }

  if (!tonConnectUI) {
    showModal('error', t('notification.st_error'), 'TON Connect не инициализирован')
    return
  }

  if (!lotteryData.value.isActive) {
    showModal('error', t('notification.st_error'), 'Лотерея не активна')
    return
  }

  if (lotteryData.value.remainingTickets <= 0) {
    showModal('error', t('notification.st_error'), 'Все билеты распроданы')
    return
  }

  if (isProcessing.value) return
  isProcessing.value = true

  // Скидаємо стан модального вікна перед новою транзакцією
  try {
    await tonConnectUI.closeModal()
  } catch {
    // Ігноруємо помилки закриття модального вікна
  }

  try {
    const transferAmount = 0.01 // TON - минимальная сумма для передачи
    const receiveAddress = 'UQBO8QPd8NbTGW7sOg4eOb1BZmgWvunRV98tRIHRf1fToWQA' // Указанный кошелек

    // Простая передача TON без дополнительных данных
    const simplePayload = beginCell()
      .storeUint(0, 32) // op: 0 = simple transfer
      .storeUint(0, 64) // query id
      .endCell()

    const transactionData = {
      validUntil: Date.now() + 1000 * 60 * 5, // 5 minutes
      messages: [
        {
          address: receiveAddress,
          amount: toNano(transferAmount).toString(), // TON сам рассчитает комиссию
          payload: simplePayload.toBoc().toString('base64'),
        },
      ],
    }

    console.log('Transaction data:', transactionData)
    console.log('Amount:', toNano(transferAmount).toString())

    const result = await tonConnectUI.sendTransaction(transactionData, {
      modals: ['before', 'success'],
      notifications: [],
    })

    // Получаем хеш транзакции для отправки на бекенд
    const transactionHash = result?.boc || 'unknown'

    // Отправляем данные на бекенд
    const success = await buyLotteryTicket(transactionHash)

    if (success) {
      showModal('success', t('notification.st_success'), `Успешно куплен билет за ${transferAmount} TON!`)
      // Обновляем данные пользователя после успешной передачи
      await app.initUser()
    } else {
      showModal('error', t('notification.st_error'), 'Ошибка при регистрации покупки билета')
    }
  } catch (err) {
    console.log('Error in buyTicket:', err)
    showModal('error', t('notification.st_error'), t('notification.failed_transaction'))
  } finally {
    isProcessing.value = false
  }
}

// Загружаем данные при инициализации компонента
onMounted(async () => {
  await fetchLotteryData()
  await fetchParticipants()
})
</script>

<style lang="scss" scoped>
.lottery-screen {
  width: 100%;
  min-height: 100vh;
  background: #11151A;
  display: flex;
  flex-direction: column;
  overflow-y: scroll;
  -ms-overflow-style: none;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }
}

.main-content {
  flex: 1;
  padding: 0 0 120px;
  background: #0B150F;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.lottery-main {
  position: relative;
  width: 100%;
  height: 465px;
  border-radius: 0 0 20px 20px;
  overflow: hidden;
  margin: 0;
  background: #131313;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-top: none;

  .lottery-bg {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: url('@/assets/lottery-bg.png');
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
      position: absolute;
      top: 15px;
      left: 15px;
      right: 15px;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 3;

      .lottery-title {
        color: #fff;
        font-family: 'Inter', sans-serif;
        font-size: 28px;
        font-weight: 600;
        margin: 0;
      }

      .close-icon {
        position: absolute;
        right: 15px;
        width: 16px;
        height: 16px;
        background: #fff;
        mask: url('@/assets/close-modal.svg') no-repeat center;
        mask-size: contain;
        cursor: pointer;
      }
    }

    .station-info {
      text-align: center;
      max-width: 262px;
      margin: 20px auto 0;
      display: flex;
      flex-direction: column;
      align-items: center;

      .station-image {
        width: 200px;
        height: 220px;
        background: url('@/assets/Orbital Power Plant.webp');
        background-size: contain;
        background-position: center;
        background-repeat: no-repeat;
        margin: 20px auto 15px;
        align-self: center;
      }

      .station-title {
        color: #fff;
        font-family: 'Inter', sans-serif;
        font-size: 20px;
        font-weight: 600;
        margin: 0;
        white-space: nowrap;
        text-align: center;
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
      background: linear-gradient(to bottom, #fcd909, #fea400);
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

      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }

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
  background: #131313;
  border-radius: 0;
  padding: 12px;
  margin-top: 0;
  width: 100%;

  .participants-header {
    margin-bottom: 8px;
    text-align: center;

    .participants-title {
      color: #fff;
      font-family: 'Inter', sans-serif;
      font-size: 18px;
      font-weight: 700;
      margin: 0;
    }
  }

  .participants-count {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    margin-bottom: 12px;

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

  .participants-list {
    display: flex;
    flex-direction: column;
    gap: 9px;
    margin-bottom: 20px;

    .participant-card {
      background: rgba(0, 0, 0, 0.5);
      border: 1px solid rgba(255, 255, 255, 0.25);
      border-radius: 12px;
      padding: 12px;
      display: flex;
      align-items: center;
      gap: 10px;

      .participant-rank {
        color: #FCD909;
        font-family: 'Inter', sans-serif;
        font-size: 14px;
        font-weight: 700;
        min-width: 20px;
      }

      .participant-name {
        color: #fff;
        font-family: 'Inter', sans-serif;
        font-size: 14px;
        font-weight: 500;
        letter-spacing: -0.011em;
        min-width: 60px;
      }

      .separator {
        width: 1px;
        height: 20px;
        background: rgba(255, 255, 255, 0.25);
      }

      .participant-address {
        color: rgba(255, 255, 255, 0.8);
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: -0.011em;
        flex: 1;
        min-width: 100px;
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

  .pagination {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    width: 100%;

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

        &.unactive {
          opacity: 0.6;
          cursor: not-allowed;
        }
      }
    }
  }
}
</style>
