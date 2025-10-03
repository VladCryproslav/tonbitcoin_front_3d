<template>
  <div class="modal-mask" name="modal">
    <div class="modal-wrapper">
      <div class="modal-container">
        <button class="close" @click="emitClose">
          <Exit style="color: #fff" />
        </button>
        <div class="grouping">
          <div class="modal-header">{{ t('modals.rent_ban_modal.title') }}</div>
          <div class="modal-body">
            <p>{{ t('modals.rent_ban_modal.message', {
              points: Math.abs(app?.user?.points),
              days: Math.abs(Math.floor(app?.user?.points / app?.rental_config?.max_points_block) * 7)
            }) }}</p>
            <h3>{{ t('modals.rent_ban_modal.remaining') }} <label>{{ startCountdown(app.user?.rent_blocked_until) }}</label>
            </h3>
            <div class="buttons-group">
              <button class="confirm" @click="emitClose">{{ t('modals.rent_ban_modal.confirm') }}</button>
              <button class="cancel" @click="speedUp">{{ t('modals.rent_ban_modal.speed_up') }}
                <Stars width="18px" height="18px" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const Exit = defineAsyncComponent(() => import('@/assets/upg-modal-close.svg'))
const Stars = defineAsyncComponent(() => import('@/assets/stars.svg'))
import { useAppStore } from '@/stores/app'
import { defineAsyncComponent, onUnmounted } from 'vue'
import { host } from '../../axios.config'
import { useTelegram } from '@/services/telegram'
import { useI18n } from 'vue-i18n'

const app = useAppStore()
const { t } = useI18n()
const { tg } = useTelegram()

const emit = defineEmits(['close'])

const emitClose = () => {
  emit('close')
}

function startCountdown(isoString) {
  const targetDate = new Date(isoString);

  // Перевірка на валідність дати
  if (isNaN(targetDate.getTime())) {
    console.error('Невалидная дата');
    return;
  }

  // Функція для правильного відмінювання
  function getDeclension(number, singular, pluralFew, pluralMany) {
    if (number % 10 === 1 && number % 100 !== 11) {
      return singular;
    } else if (
      [2, 3, 4].includes(number % 10) &&
      ![12, 13, 14].includes(number % 100)
    ) {
      return pluralFew;
    } else {
      return pluralMany;
    }
  }

  // Функція для форматування часу
  function formatTimeRemaining() {
    const now = new Date();
    const diffMs = targetDate - now;

    if (diffMs <= 0) {
      clearInterval(interval);
      return t('modals.rent_ban_modal.time_expired');
    }

    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);

    const dayWord = getDeclension(days, t('modals.rent_ban_modal.day'), t('modals.rent_ban_modal.days_few'), t('modals.rent_ban_modal.days_many'));
    const hourWord = getDeclension(hours, t('modals.rent_ban_modal.hour'), t('modals.rent_ban_modal.hours_few'), t('modals.rent_ban_modal.hours_many'));
    const secondWord = getDeclension(seconds, t('modals.rent_ban_modal.second'), t('modals.rent_ban_modal.seconds_few'), t('modals.rent_ban_modal.seconds_many'));

    return `${days} ${dayWord} ${hours} ${hourWord} ${seconds} ${secondWord}`;
  }

  // Оновлення значення щосекунди
  const update = () => {
    const result = formatTimeRemaining();
    return result; // Для демонстрації, можна замінити на вивід в DOM
  };

  // Початкове оновлення
  const output = update();

  // Запуск інтервалу для оновлення щосекунди
  const interval = setInterval(update, 1000);

  // Повернення функції для зупинки таймера, якщо потрібно
  onUnmounted(() => clearInterval(interval))
  return output
}


const speedUp = async () => {
  const invoiceLink = await host.post(`accelerate-rent-block/`)
  if (invoiceLink.status == 200) {
    tg.openInvoice(invoiceLink.data?.link, (status) => {
      if (status == 'paid') {
        app.initUser()
        emit("close", { status: 'success', title: t('notification.st_success'), body: t('modals.rent_ban_modal.unlock_accelerated') })
      }
    })
  }
  return
}
</script>

<style lang="scss" scoped>
.modal-mask {
  position: fixed;
  z-index: 105;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: table;
  background-color: #00000050;
  transition: opacity 0.3s ease;
}

.modal-wrapper {
  display: table-cell;
  vertical-align: middle;
}

.modal-container {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  margin: 0px auto;
  width: 90%;
  padding: 15px 0 10px;
  background: #10151BE6;
  backdrop-filter: blur(5px);
  transition: all 0.3s ease;
  box-shadow: inset 0 0 0 1px #FF3B59;
  border-radius: 1rem;

  .close {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
  }

  .grouping {
    width: 90%;
    display: flex;
    flex-direction: column;
    align-items: start;
    gap: 0.5rem;

    .price {
      width: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      gap: 0.5rem;

      .kw-price,
      .tbtc-price {
        width: 100%;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: #fff;
        font-family: 'Inter' !important;
        font-size: 11px;
        font-weight: 400;
      }
    }

    .buttons-group {
      width: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
      margin-top: 1rem;
      gap: 1rem;

      .confirm {
        width: 50%;
        padding: 0.5rem;
        color: #fff;
        font-family: 'Inter' !important;
        font-size: 16px;
        line-height: 17px;
        letter-spacing: -0.5px;
        font-weight: 500;
        border-radius: 5rem;
        background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
          linear-gradient(to bottom, #F97474, #960000);
        box-shadow:
          inset 0 0 0 2px #10151b,
          0 0 0 1px #F97474;

        &:active {
          opacity: 0.95;
        }
      }

      .cancel {
        width: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 0.5rem;
        color: #fff;
        font-family: 'Inter' !important;
        font-size: 16px;
        line-height: 17px;
        letter-spacing: -0.5px;
        font-weight: 500;
        border-radius: 5rem;
        box-shadow: inset 0 0 0 2px #10151b, 0 0 0 1px #9851ec;
        background: radial-gradient(ellipse 80% 20% at bottom, #ffffff50, transparent),
          linear-gradient(to left, #e757ec, #9851ec, #5e7cea);

        &:active {
          background-color: #fe3b59;
        }
      }
    }
  }
}

.modal-header {
  width: 100%;
  text-align: center;
  color: #fff;
  font-weight: 700;
  font-size: 18px;
  line-height: 1.3;
  font-family: 'Inter' !important;
}

.modal-body {
  white-space: pre-wrap;
  width: 100%;
  text-align: center;
  font-family: 'Inter' !important;
  font-weight: 500;
  letter-spacing: -0.5px;
  font-size: 14px;
  color: #ffffff80;
  margin: 0 0 10px;

  h3 {
    margin-top: 1rem;
    color: #ffffff80;
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 0;

    label {
      color: #fff;
    }
  }

  ul {
    list-style: disc;
    list-style-position: inside;
  }

  &.left-text {
    text-align: left;
  }
}

.modal-default-button {
  float: right;
}

.modal-enter {
  opacity: 0;
}

.modal-leave-active {
  opacity: 0;
}

.modal-enter .modal-container,
.modal-leave-active .modal-container {
  -webkit-transform: scale(1.1);
  transform: scale(1.1);
}
</style>
