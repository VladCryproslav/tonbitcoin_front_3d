<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import ModalNew from '@/components/ModalNew.vue'
import InlineSvg from 'vue-inline-svg'
import TaskModal from '@/components/TaskModal.vue'
import Check from '@/assets/green-check.svg'
import { host } from '../../axios.config'
import { useI18n } from 'vue-i18n'

const app = useAppStore()
const myTasks = ref([])
const taskCateg = ref([])
const taskAttempts = ref({})
const { t, locale } = useI18n()

let controller = null

// const allTaskTabs = ['all', 'daily', 'special', 'miners', 'energizers'];

const modalStatus = ref('')
const modalTitle = ref('')
const modalBody = ref('')
const openModal = ref(false)

const tasksParam = ref(null)
const allTasksLength = ref(0)

const currTaskList = computed(() => {
  return tasksParam.value !== null
    ? myTasks.value?.filter((el) =>
      el?.task?.categories?.includes(
        taskCateg.value?.find((el) => el?.name == tasksParam.value)?.id,
      ),
    )
    : myTasks.value
})

const scrollView = ref(null)
const scrollToTop = () => {
  scrollView.value.scrollTo({ top: 0, behavior: 'smooth' });
};

let timeoutId = null
async function startInfoUpdate() {
  await app
    .initTasks()
    .then((res) => {
      myTasks.value = app?.tasks
      allTasksLength.value = app?.tasks?.filter((el) => !el.claimed).length
    })
    .catch((err) => {
      console.error(err)
    })
    .finally(() => {
      timeoutId = setTimeout(() => startInfoUpdate(), 3000)
    })
}

const openTaskModal = ref(false)
const taskData = ref(null)
const taskStarted = ref([])

const setTaskModal = async (tsk) => {
  if (tsk?.claimed) return
  if (!taskStarted.value.includes(tsk.id)) {
    taskStarted.value.push(tsk.id)
  }
  try {
    controller = new AbortController()
    const check = await host.post('tasks/check_task_completion/', { user_task_id: tsk.id }, { signal: controller.signal })
    if (check.status == 200) {
      if (check.data?.status == 'Task claimed') {
        modalStatus.value = 'success'
        modalTitle.value = t('notification.st_success')
        modalBody.value = t('notification.task_completed', { value: `${tsk.task.reward_amount} ${tsk.task.reward_type}` })
        openModal.value = true
      }
    }
  } catch (err) {
    if (err.response.data.status == 'Task started') {
      taskAttempts.value[tsk.id] = (taskAttempts.value[tsk.id] || 0) + 1
      taskData.value = tsk
      openTaskModal.value = true
    } else if (err.response.data.status == 'Task not completed') {
      taskAttempts.value[tsk.id] = (taskAttempts.value[tsk.id] || 0) + 1
      if (taskStarted.value.includes(tsk.id) && taskAttempts.value[tsk.id] == 2) {
        taskStarted.value = taskStarted.value.filter((id) => id !== tsk.id)
        delete taskAttempts.value[tsk.id]
        modalStatus.value = 'error'
        modalTitle.value = t('notification.st_error')
        modalBody.value = t('notification.task_uncompleted')
        openModal.value = true
      }
      if (taskStarted.value.includes(tsk.id) && taskAttempts.value[tsk.id] !== 2) {
        taskData.value = tsk
        openTaskModal.value = true
      }
    } else if (err.response.data.status == 'Task already claimed') {
      if (taskStarted.value.includes(tsk.id)) {
        taskStarted.value = taskStarted.value.filter((id) => id !== tsk.id)
      }
      if (taskAttempts.value[tsk.id]) {
        delete taskAttempts.value[tsk.id]
      }
      return
    } else {
      modalStatus.value = 'error'
      modalTitle.value = t('notification.st_error')
      modalBody.value = err.response.data.status
      openModal.value = true
    }
  } finally {
    controller = null
  }
}

const taskReponse = (r) => {
  taskData.value = null
  openTaskModal.value = false
  if (r) {
    modalStatus.value = r.status
    modalTitle.value = r.title
    modalBody.value = r.body
    openModal.value = true

    if (r.task_id) {
      taskStarted.value = taskStarted.value.filter((id) => id !== r.task_id)
      delete taskAttempts.value[r.task_id]
    }
  }
}

const handleParam = (param) => {
  scrollToTop()
  tasksParam.value = param
}

onMounted(async () => {
  try {
    const [categRes, tasksRes] = await Promise.all([app.initTaskCateg(), app.initTasks(null)])
    taskCateg.value = app?.task_categ
    myTasks.value = app?.tasks
    allTasksLength.value = app?.tasks?.filter((el) => !el.claimed).length
  } catch (err) {
    console.error(err)
  } finally {
    startInfoUpdate()
  }
})

watch(
  tasksParam.value,
  async (newVal, oldVal) => {
    if (newVal === oldVal) return
    await app.initTasks(taskCateg.value?.find((el) => el?.name === newVal)?.id || null)
    myTasks.value = app?.tasks
  },
  { immediate: true },
)

onUnmounted(() => {
  if (controller) {
    controller.abort()
  }
  if (timeoutId) {
    clearTimeout(timeoutId)
    timeoutId = null
  }
})
</script>

<template>
  <TaskModal v-if="openTaskModal" :data="taskData" @close="taskReponse" />
  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
  <div class="screen-box">
    <h1 class="title">{{ t('tasks.title') }}</h1>
    <div class="tasks-scroll-block">
      <div class="tasks-navigation">
        <div class="tasks-navigation-item" :class="{ active: tasksParam == null }" @click="handleParam(null)">
          <div v-if="allTasksLength" class="tasks-navigation-item-badge">{{ allTasksLength }}</div>
          {{ t('tasks.all_tab') }}
        </div>
        <div class="tasks-navigation-item" :class="{ active: tasksParam == 'energizers' }"
          @click="handleParam('energizers')">
          <div v-if="
            myTasks?.filter(
              (el) =>
                el?.task?.categories?.includes(
                  taskCateg?.find((el) => el?.name == 'energizers')?.id,
                ) && !el?.claimed,
            ).length
          " class="tasks-navigation-item-badge">
            {{
              myTasks?.filter(
                (el) =>
                  el?.task?.categories?.includes(
                    taskCateg?.find((el) => el?.name == 'energizers')?.id,
                  ) && !el?.claimed,
              ).length
            }}
          </div>
          {{ t('tasks.enr_tab') }}
        </div>
        <!-- <div class="tasks-navigation-item" :class="{ active: tasksParam == 'daily' }" @click="tasksParam = 'daily'">
          <div
            v-if="myTasks?.filter(el => el?.task?.categories?.includes(taskCateg?.find(el => el?.name == 'daily')?.id) && !el?.claimed).length"
            class="tasks-navigation-item-badge">{{ myTasks?.filter(el =>
              el?.task?.categories?.includes(taskCateg?.find(el => el?.name == 'daily')?.id) && !el?.claimed).length }}
          </div>
          Ежедневные
        </div> -->
        <div class="tasks-navigation-item" :class="{ active: tasksParam == 'special' }" @click="handleParam('special')">
          <div v-if="
            myTasks?.filter(
              (el) =>
                el?.task?.categories?.includes(
                  taskCateg?.find((el) => el?.name == 'special')?.id,
                ) && !el?.claimed,
            ).length
          " class="tasks-navigation-item-badge">
            {{
              myTasks?.filter(
                (el) =>
                  el?.task?.categories?.includes(
                    taskCateg?.find((el) => el?.name == 'special')?.id,
                  ) && !el?.claimed,
              ).length
            }}
          </div>
          {{ t('tasks.spec_tab') }}
        </div>
        <div class="tasks-navigation-item" :class="{ active: tasksParam == 'miners' }" @click="handleParam('miners')">
          <div v-if="
            myTasks?.map(
              (el) =>
                el?.task?.categories?.includes(
                  taskCateg?.find((el) => el?.name == 'miners')?.id,
                ) && !el?.claimed,
            ).length
          " class="tasks-navigation-item-badge">
            {{
              myTasks?.filter(
                (el) =>
                  el?.task?.categories?.includes(
                    taskCateg?.find((el) => el?.name == 'miners')?.id,
                  ) && !el?.claimed,
              ).length
            }}
          </div>
          {{ t('tasks.mine_tab') }}
        </div>
        <div class="tasks-navigation-item" :class="{ active: tasksParam == 'new' }" @click="handleParam('new')">
          <div v-if="
            myTasks?.map(
              (el) =>
                el?.task?.categories?.includes(taskCateg?.find((el) => el?.name == 'new')?.id) &&
                !el?.claimed,
            ).length
          " class="tasks-navigation-item-badge">
            {{
              myTasks?.filter(
                (el) =>
                  el?.task?.categories?.includes(taskCateg?.find((el) => el?.name == 'new')?.id) &&
                  !el?.claimed,
              ).length
            }}
          </div>
          {{ t('tasks.new_tab') }}
        </div>
      </div>
    </div>
    <div class="tasks" ref="scrollView">
      <div class="tasks-banner">
        <img src="@/assets/gift.png" width="102px" />
        <div class="tasks-banner-text">
          <h2>{{ t('tasks.banner_title') }}</h2>
          <p>{{ t('tasks.banner_desc') }}</p>
        </div>
      </div>
      <div class="tasks-block">
        <h2>{{ t('tasks.task_list_title') }}</h2>
        <span class="empty-list" v-if="!currTaskList.length">{{ t('tasks.empty_list') }}</span>
        <div class="tasks-block-list">
          <div class="task-item" v-for="(item, index) in currTaskList" :key="index">
            <div class="task-item-icon">
              <InlineSvg v-if="item?.task?.icon" :src="item?.task?.icon" />
            </div>
            <div class="task-item-info">
              <p class="task-item-info-title">{{ item?.task?.[`title${locale == 'uk' ? '' : `_${locale}`}`] }}</p>
              <span class="task-item-info-price">{{ item?.task?.reward_amount }}
                <img v-if="item?.task?.reward_type == 'kW'" src="@/assets/kw_token.png" width="16px" />
                <img v-if="item?.task?.reward_type == 'tBTC'" src="@/assets/fBTC.webp" width="16px" />
              </span>
            </div>
            <button class="task-item-btn" :disabled="item?.claimed" :class="{
              pending: taskStarted.includes(item?.id) && !item?.claimed,
              done: item?.claimed,
            }" @click="setTaskModal(item)">
              {{
                item?.claimed
                  ? t('tasks.done')
                  : taskStarted.includes(item?.id)
                    ? taskAttempts?.[item.id]
                      ? t('tasks.pending')
                      : t('tasks.start')
                    : t('tasks.start')
              }}
              <Check v-if="item?.claimed" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.screen-box {
  position: absolute;
  top: 0;
  width: 100%;
  height: 100vh;
  background: radial-gradient(ellipse 80% 40% at top right, #31cfff30, transparent) #000;
  display: flex;
  flex-direction: column;
  align-items: center;

  h1 {
    text-align: center;
    color: #fff;
    font-family: 'Inter' !important;
    font-size: 6vw;
    font-weight: 700;
    margin: 1rem 2rem 0.7rem;
  }

  .tasks-scroll-block {
    position: relative;
    width: 100%;
    min-height: 50px;
  }

  .tasks-navigation {
    display: flex;
    width: 100vw;
    position: absolute;
    top: 0;
    border-bottom: 1px solid #ffffff25;
    margin: 0 0 1rem 5%;
    padding: 0 1.5rem 0 0;
    overflow-x: scroll;
    -ms-overflow-style: none;
    /* Internet Explorer 10+ */
    scrollbar-width: none;
    /* Firefox */

    &::-webkit-scrollbar {
      display: none;
      /* Safari and Chrome */
    }

    &-item {
      position: relative;
      color: #ffffff50;
      font-family: 'Inter' !important;
      font-weight: 700;
      font-size: 16px;
      letter-spacing: -0.15px;
      padding: 0.5rem 1.2rem;

      &.active {
        color: #31cfff;
        border-bottom: 2px solid #31cfff;
      }

      &-badge {
        color: #fff;
        font-family: 'Inter' !important;
        font-weight: bold;
        font-size: 8px;
        background-color: #ff3b59;
        border-radius: 50px;
        position: absolute;
        padding: 0 8px;
        top: 0;
        right: 0;
      }
    }
  }

  .tasks {
    width: 95%;
    display: flex;
    flex-direction: column;
    justify-content: start;
    background: #31cfff50;
    border-radius: 1rem;
    overflow-y: scroll;
    -ms-overflow-style: none;
    scrollbar-width: none;

    &::-webkit-scrollbar {
      display: none;
    }

    &-banner {
      width: 100%;
      display: flex;
      align-items: center;
      padding: 0.5rem;
      gap: 1.5rem;

      &-text {
        width: 60%;
        color: #fff;
        display: flex;
        flex-direction: column;
        font-family: 'Inter' !important;

        h2 {
          font-weight: 700;
          font-size: 16px;
        }

        p {
          font-weight: 500;
          font-size: 12px;
          opacity: 0.6;
        }
      }
    }

    &-block {
      width: 100%;
      display: flex;
      flex-direction: column;
      justify-content: start;
      background: #182029;
      border-radius: 1rem;
      padding: 1rem;
      padding-bottom: 130px;
      font-family: 'Inter' !important;

      h2 {
        font-family: 'Inter' !important;
        color: #fff;
        font-weight: 600;
        font-size: 17px;
      }

      .empty-list {
        color: #FFFFFF40;
        width: 100%;
        text-align: center;
        padding: 5rem 0 5rem 0;
      }

      &-list {
        width: 100%;
        display: flex;
        flex-direction: column;
        justify-content: start;

        .task-item {
          display: flex;
          align-items: center;
          padding: 1rem 0;
          gap: 10px;
          border-bottom: 1px solid #ffffff25;

          &-icon {
            background: #ffffff25;
            min-width: 42px;
            width: 42px;
            height: 42px;
            border-radius: 0.8rem;
            display: flex;
            justify-content: center;
            align-items: center;
          }

          &-info {
            display: flex;
            flex-direction: column;
            width: 100%;

            &-title {
              color: #fff;
              font-weight: 400;
              font-size: 13px;
              line-height: 18px;
              letter-spacing: -0.15px;
            }

            &-price {
              color: #fcd909;
              font-weight: 600;
              font-size: 12px;
              line-height: 16px;
              letter-spacing: 0px;
              display: flex;
              align-items: center;
              gap: 3px;
            }
          }

          &-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            width: max-content;
            color: #fff;
            font-weight: 700;
            font-size: 14px;
            line-height: 18px;
            letter-spacing: 0px;
            padding: 0.6rem 0.8rem;
            border-radius: 0.5rem;
            transition: all 0.5s linear;
            background: linear-gradient(to bottom, #2eb5de, #134a5b);

            &:active {
              background: linear-gradient(to bottom, #2eb5de90, #134a5b90);
            }

            &.done {
              min-width: 97px;
              background: linear-gradient(to bottom, #e2f974, #009600);

              &:active {
                background: linear-gradient(to bottom, #e2f97490, #00960090);
              }
            }

            &.pending {
              min-width: 97px;
              background: linear-gradient(to bottom, #fcd909, #fea400);

              &:active {
                background: linear-gradient(to bottom, #fcd90990, #fea40090);
              }
            }
          }
        }
      }
    }
  }
}
</style>
