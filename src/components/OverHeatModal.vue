<script setup>
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const emit = defineEmits(['close'])

onMounted(() => {
  setTimeout(() => {
    emit('close')
  }, 2000)
})
</script>

<template>
  <div class="modal-mask" name="modal" @click="emit('close')">
    <div class="modal-wrapper">
      <div class="modal-container status-error">
        <div class="grouping">
          <div class="col-grouping">
            <div class="modal-header">{{ t('modals.overheat.title') }}</div>
            <div class="modal-body">
              {{ t('modals.overheat.message') }}<br /><br /><b>{{ t('modals.overheat.warning') }}</b>
            </div>
          </div>
        </div>
        <div class="progress-bar">
          <div id="bar" class="inner-bar status-error"></div>
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
  vertical-align: middle;
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
  padding: 0 0 10px;
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
      align-items: center;
    }
  }
}

.modal-header {
  color: #ff3b59;
  display: flex;
  width: 100%;
  padding: 10px 0;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-weight: 700;
  font-size: 18px;
  line-height: 1.3;
  font-family: 'Inter' !important;
}

.modal-body {
  white-space: pre-wrap;
  text-align: center;
  font-family: 'Inter' !important;
  font-weight: 500;
  font-size: 12px;
  color: #fff;
  width: 85%;
  margin: 0 auto 10px;
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
