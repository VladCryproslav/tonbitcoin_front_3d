<template>
  <div class="modal-mask" name="modal">
    <div class="modal-wrapper">
      <div class="modal-container">
        <button class="close" @click="emit('close')">
          <Exit style="color: #fff" />
        </button>
        <div class="grouping">
          <div class="modal-header">{{ t('modals.reconnect_modal.title') }}</div>
          <div class="modal-body">
            {{ props?.example?.firstNumber }} {{ props?.example?.operator }} {{ props?.example?.secondNumber }} = ?
          </div>
          <div class="buttons-group">
            <button v-for="item in props?.example?.answers" :key="item" :class="{
              correct: choosenAnswer == item && choosenAnswer == props?.example?.result,
              wrong: choosenAnswer == item && choosenAnswer !== props?.example?.result,
            }" @click="chooseAnswer(item)" :disabled="choosenAnswer !== null">
              {{ item }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const Exit = defineAsyncComponent(() => import('@/assets/upg-modal-close.svg'))
import { defineAsyncComponent, ref } from 'vue'
import { host } from '../../axios.config'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  example: Object,
})

const choosenAnswer = ref(null)

const emit = defineEmits(['close'])

async function chooseAnswer(item) {
  choosenAnswer.value = item
  let reqData = {
    number1: props?.example?.firstNumber,
    op: props?.example?.operator,
    number2: props?.example?.secondNumber,
    answer: item,
  }
  try {
    await host.post('reconnect-mining/', reqData).then((res) => {
      if (res.status == 200) {
        emit('close', {
          status: 'success',
          title: t('notification.st_success'),
          body: t('modals.reconnect_modal.connection_restored'),
        })
      }
    })
  } catch (err) {
    console.log(err)
    emit('close', {
      status: 'error',
      title: t('notification.st_error'),
      body: t('modals.reconnect_modal.wrong_answer'),
    })
  }
}
</script>

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

    .buttons-group {
      width: 100%;
      display: flex;
      margin: 0 auto;
      justify-content: space-evenly;
      align-items: center;
      margin: 0.5rem 0;

      button {
        width: 60px;
        padding: 0.1rem;
        color: #fff;
        border-radius: 5rem;
        border: 1px solid #ffffff50;
        font-family: 'Inter';
        font-weight: 500;
        font-size: 14px;
        letter-spacing: -0.5px;

        &.correct {
          border: 1px solid #8be113;
        }

        &.wrong {
          border: 1px solid #fe3b59;
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
  width: 100%;
  text-align: center;
  font-family: 'Inter' !important;
  font-weight: 500;
  font-size: 14px;
  color: #8b898b;
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
