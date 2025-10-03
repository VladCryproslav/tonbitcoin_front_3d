<script setup>
import { onMounted, ref, watch } from 'vue'

const emit = defineEmits(['close'])

const checkedSwitch = ref(false)

const switchStyle = ref({
  top: '50%',
  left: '50%',
})

const randomizePosition = () => {
  const switchWidth = 150
  const switchHeight = 195
  const windowWidth = window.innerWidth
  const windowHeight = window.innerHeight

  const randomLeft = Math.random() * (windowWidth - switchWidth)
  const randomTop = Math.random() * (windowHeight - switchHeight)

  switchStyle.value = {
    top: `${randomTop}px`,
    left: `${randomLeft}px`,
  }
}

onMounted(() => {
  randomizePosition()
})

watch(
  checkedSwitch,
  () => {
    if (checkedSwitch.value) {
      setTimeout(() => {
        emit('close')
      }, 1200)
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="modal-mask" name="modal">
    <label class="switch" :style="switchStyle">
      <input
        v-model="checkedSwitch"
        type="checkbox"
        :checked="checkedSwitch"
        :disabled="checkedSwitch"
      />
      <div class="button">
        <div class="light"></div>
        <div class="dots"></div>
        <div class="characters"></div>
        <div class="shine"></div>
        <div class="shadow"></div>
      </div>
    </label>
  </div>
</template>

<style lang="scss" scoped>
$background-color_1: black;
$background-color_2: #9b0621;

.modal-mask {
  position: fixed;
  z-index: 9998;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: table;
  background-color: #00000050;
  backdrop-filter: blur(5px);
  transition: opacity 0.3s ease;
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

@keyframes flicker {
  0% {
    opacity: 1;
  }

  80% {
    opacity: 0.8;
  }

  100% {
    opacity: 1;
  }
}

@keyframes light-off {
  0% {
    opacity: 1;
  }

  80% {
    opacity: 0;
  }
}

.switch {
  position: absolute;
  background-color: $background-color_1;
  width: 90px;
  height: 110px;
  box-shadow:
    0 0 10px 2px rgba(0, 0, 0, 0.2),
    0 0 1px 2px black,
    inset 0 2px 2px -2px white,
    inset 0 0 2px 15px #47434c,
    inset 0 0 2px 22px black;
  border-radius: 5px;
  padding: 20px;
  perspective: 700px;

  input {
    display: none;

    &:checked {
      + {
        .button {
          transform: translateZ(20px) rotateX(25deg);
          box-shadow: 0 -10px 20px #ff1818;

          .light {
            animation: flicker 0.2s infinite 0.3s;
          }

          .shine {
            opacity: 1;
          }

          .shadow {
            opacity: 0;
          }
        }
      }
    }
  }

  .button {
    display: block;
    transition: all 0.3s cubic-bezier(1, 0, 1, 1);
    transform-origin: center center -20px;
    transform: translateZ(20px) rotateX(-25deg);
    transform-style: preserve-3d;
    background-color: $background-color_2;
    height: 100%;
    position: relative;
    cursor: pointer;
    background: linear-gradient(#980000 0%, #6f0000 30%, #6f0000 70%, #980000 100%);
    background-repeat: no-repeat;

    &::before {
      content: '';
      background:
        linear-gradient(
            rgba(255, 255, 255, 0.8) 10%,
            rgba(255, 255, 255, 0.3) 30%,
            #650000 75%,
            #320000
          )
          50% 50%/97% 97%,
        #b10000;
      background-repeat: no-repeat;
      width: 100%;
      height: 20px;
      transform-origin: top;
      transform: rotateX(-90deg);
      position: absolute;
      top: 0;
    }

    &::after {
      content: '';
      background-image: linear-gradient(#650000, #320000);
      width: 100%;
      height: 50px;
      transform-origin: top;
      transform: translateY(40px) rotateX(-90deg);
      position: absolute;
      bottom: 0;
      box-shadow:
        0 50px 8px 0px black,
        0 80px 20px 0px rgba(0, 0, 0, 0.5);
    }
  }

  .light {
    opacity: 0;
    animation: light-off 1s;
    position: absolute;
    width: 100%;
    height: 100%;
    background-image: radial-gradient(#ffc97e, #ff1818 40%, transparent 70%);
  }

  .dots {
    position: absolute;
    width: 100%;
    height: 100%;
    background-image: radial-gradient(transparent 30%, rgba(101, 0, 0, 0.7) 70%);
    background-size: 5px 5px;
  }

  .characters {
    position: absolute;
    width: 100%;
    height: 100%;
    background:
      linear-gradient(white, white) 50% 20%/5% 20%,
      radial-gradient(circle, transparent 50%, white 52%, white 70%, transparent 72%) 50% 80%/33%
        25%;
    background-repeat: no-repeat;
  }

  .shine {
    transition: all 0.3s cubic-bezier(1, 0, 1, 1);
    opacity: 0.3;
    position: absolute;
    width: 100%;
    height: 100%;
    background:
      linear-gradient(white, transparent 3%) 50% 50%/97% 97%,
      linear-gradient(
          rgba(255, 255, 255, 0.5),
          transparent 50%,
          transparent 80%,
          rgba(255, 255, 255, 0.5)
        )
        50% 50%/97% 97%;
    background-repeat: no-repeat;
  }

  .shadow {
    transition: all 0.3s cubic-bezier(1, 0, 1, 1);
    opacity: 1;
    position: absolute;
    width: 100%;
    height: 100%;
    background: linear-gradient(transparent 70%, rgba(0, 0, 0, 0.8));
    background-repeat: no-repeat;
  }
}
</style>
