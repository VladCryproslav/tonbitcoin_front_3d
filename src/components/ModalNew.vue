<script setup>
const Success = defineAsyncComponent(() => import('@/assets/success.svg'))
const Error = defineAsyncComponent(() => import('@/assets/error.svg'))
const Warning = defineAsyncComponent(() => import('@/assets/info.svg'))
const Exit = defineAsyncComponent(() => import('@/assets/close-modal.svg'))

import { defineAsyncComponent, onMounted } from 'vue'

const props = defineProps({
  status: String,
  title: String,
  body: String,
})

const emit = defineEmits(['close'])

const emitClose = () => {
  emit('close')
}

onMounted(() => {
  setTimeout(() => {
    emit('close')
  }, 2000)
})
</script>

<template>
  <div class="modal-mask" name="modal" @click="emitClose">
    <div class="modal-wrapper">
      <div
        class="modal-container"
        :class="{
          'status-success': props.status == 'success',
          'status-error': props.status == 'error',
          'status-warning': props.status == 'warning',
        }"
      >
        <div class="grouping">
          <Success v-if="props.status == 'success'" :width="22" :height="22" />
          <Error v-if="props.status == 'error'" :width="22" :height="22" />
          <Warning v-if="props.status == 'warning'" :width="22" :height="22" />

          <div class="col-grouping">
            <div class="modal-header">
              <slot name="header">{{ props.title }}</slot>
            </div>
            <div v-if="props.body" class="modal-body">
              <slot name="body"> {{ props.body }} </slot>
            </div>
          </div>

          <button class="close" @click="emit('close')">
            <Exit :width="13" style="color: #fff" />
          </button>
        </div>

        <div class="progress-bar">
          <div
            id="bar"
            class="inner-bar"
            :class="{
              'status-success': props.status == 'success',
              'status-error': props.status == 'error',
              'status-warning': props.status == 'warning',
            }"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
$bar-height: 8px;

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
  vertical-align: bottom;
  padding: 0 0 2rem 0;
}

.modal-container {
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
  box-shadow: inset 0 0 0 1px #fff;
  font-family: Helvetica, Arial, sans-serif;
  border-radius: 1rem;

  &.status-success {
    box-shadow: inset 0 0 0 1px #48b16e;
  }

  &.status-error {
    box-shadow: inset 0 0 0 1px #ff3b59;
  }

  &.status-warning {
    box-shadow: inset 0 0 0 1px #ffd500;
  }

  .grouping {
    width: 90%;
    display: flex;
    align-items: start;
    gap: 0.5rem;

    .col-grouping {
      width: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: start;
      margin-left: 5px;
    }
  }
}

.modal-header {
  color: #fff;
  font-weight: 600;
  font-size: 18px;
  line-height: 1.3;
  font-family: 'Inter' !important;
}

.modal-body {
  white-space: pre-wrap;
  text-align: left;
  font-family: 'Inter' !important;
  font-weight: 400;
  font-size: 11px;
  color: #8b898b;
  margin: 0 0 10px;
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

.progress-bar {
  width: 90%;
  margin: 0 auto;
  height: $bar-height;
  border-radius: 3px;
  background: linear-gradient(#6fa6d66c, #7db1df54);

  .inner-bar {
    height: 100%;
    border-radius: 3px;
    background: #fff;
    animation: progressAnimation 2s linear forwards;

    &.status-success {
      background: #48b16e;
    }

    &.status-error {
      background: #ff3b59;
    }

    &.status-warning {
      background: #ffd500;
    }
  }
}

@keyframes progressAnimation {
  from {
    width: 0;
  }

  to {
    width: 100%;
  }
}
</style>
