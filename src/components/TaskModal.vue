<script setup>
import { useTelegram } from '@/services/telegram'
import { defineAsyncComponent } from 'vue'
import { host } from '../../axios.config'
import { useI18n } from 'vue-i18n'

const Exit = defineAsyncComponent(() => import('@/assets/upg-modal-close.svg'))
const { t, locale } = useI18n()

const props = defineProps({
  data: Object,
})

const emit = defineEmits(['close'])

const { tg, user } = useTelegram()

const emitClose = () => {
  emit('close')
}

const confirm = async () => {
  if (props.data?.task?.modal_button_text == t('modals.task_modal.copy_link')) {
    const link = `https://t.me/tBTCminer_bot?startapp=ref_id${user?.id}`
    navigator.clipboard.writeText(link)
    emit('close', { status: 'success', title: t('notification.st_success'), body: t('modals.task_modal.link_copied') })
  } else if (props.data?.task?.modal_button_text == t('modals.task_modal.subscribe')) {
    tg?.openTelegramLink(props.data?.task?.n1)
    emit('close')
  } else if (props.data?.task?.modal_button_text == t('modals.task_modal.go_to_chat')) {
    tg?.openTelegramLink(props.data?.task?.n1)
    emit('close')
  } else {
    try {
      const check = await host.post('tasks/check_task_completion/', {
        user_task_id: props.data?.id,
      })
      if (check.status == 200) {
        if (check.data?.status == 'Task already claimed' || check.data?.status == 'Task claimed') {
          emit('close', {
            status: 'success',
            title: t('notification.st_success'),
            body: t('modals.task_modal.task_completed', {
              amount: props.data?.task?.reward_amount,
              type: props.data?.task?.reward_type
            }),
            task_id: props.data?.id,
          })
        }
      }
    } catch (err) {
      if (err.status == 400 && err.response.data.status == 'Task not completed') {
        emit('close', {
          status: 'error',
          title: t('notification.st_error'),
          body: t('modals.task_modal.task_not_completed'),
          task_id: props.data?.id,
        })
      } else {
        emit('close')
      }
    }
  }
}
</script>

<template>
  <div class="modal-mask" name="modal">
    <div class="modal-wrapper">
      <div class="modal-container">
        <button class="close" @click="emitClose">
          <Exit style="color: #fff" />
        </button>
        <div class="grouping">
          <div class="modal-header">
            <slot name="header">{{ t('modals.task_modal.title') }}</slot>
          </div>
          <div class="modal-body">{{ props.data?.task?.[`modal_description${locale == 'uk' ? '' : `_${locale}`}`] }}</div>
          <div class="buttons-group">
            <button class="confirm" @click="confirm">
              {{ props.data?.task?.[`modal_button_text${locale == 'uk' ? '' : `_${locale}`}`] }}
            </button>
            <button class="cancel" @click="emitClose">{{ t('modals.task_modal.cancel') }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.modal-mask {
  position: fixed;
  z-index: 9998;
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
  background: #10151b;
  transition: all 0.3s ease;
  box-shadow: inset 0 0 0 1px #ffffff70;
  font-family: Helvetica, Arial, sans-serif;
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
      }
    }

    .buttons-group {
      width: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 1rem;
      margin-bottom: 5px;

      .confirm {
        width: 70%;
        padding: 0.3rem 0.5rem;
        color: #fff;
        border-radius: 5rem;
        background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
          linear-gradient(to bottom, #2eb5de, #134a5b);
        box-shadow:
          inset 0 0 0 2px #10151b,
          0 0 0 1px #2eb5de;

        &:active {
          background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
            linear-gradient(to bottom, #2eb5de90, #134a5b90);
        }
      }

      .cancel {
        width: 30%;
        padding: 0.3rem 0.5rem;
        color: #fff;
        border-radius: 5rem;
        box-shadow: 0 0 0 1px #fe3b59;

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
  font-weight: 600;
  font-size: 18px;
  line-height: 1.3;
  font-family: 'Inter' !important;
}

.modal-body {
  white-space: pre-wrap;
  text-align: center;
  font-family: 'Inter' !important;
  font-weight: 500;
  font-size: 13.5px;
  color: #8b898b;
  margin: 0 0 10px;
  width: 100%;
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
