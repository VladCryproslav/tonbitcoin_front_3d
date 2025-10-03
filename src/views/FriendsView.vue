<script setup>
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref, watch } from 'vue'
// const Energy = defineAsyncComponent(() => import('@/assets/kW_token.svg'))
// const TonBitcoin = defineAsyncComponent(() => import('@/assets/tonbitcoin.svg'))
const SingleUser = defineAsyncComponent(() => import('@/assets/single_user.svg'))
const GroupUser = defineAsyncComponent(() => import('@/assets/group_user.svg'))
const Friends = defineAsyncComponent(() => import('@/assets/friends.svg'))
const Copy = defineAsyncComponent(() => import('@/assets/copy.svg'))
const InfoFriends = defineAsyncComponent(() => import('@/assets/info_friends.svg'))
import { useAppStore } from '@/stores/app'
import ModalNew from '@/components/ModalNew.vue'
import { useTelegram } from '@/services/telegram'
import { host } from '../../axios.config'
import { useI18n } from 'vue-i18n'
import InfoModal from '@/components/InfoModal.vue'

const app = useAppStore()
const { user } = useTelegram()
const { t } = useI18n()
let controller = null

const openModal = ref(false)
const modalStatus = ref(null)
const modalTitle = ref(null)
const modalBody = ref(null)

const currFilter = ref(null)
const currFilterSide = ref('btl')
const currPageRefs = ref(app?.referal?.referrals || [])
const allRefs = ref(
  Math.ceil((app?.referal?.first_level_count + app?.referal?.second_level_count) / 100) || 0,
)
const currPageNum = ref(1)

const friendScrollContainer = ref(null)

const openInfoModal = ref(false)

const setFilter = (filter) => {
  if (friendScrollContainer.value) {
    friendScrollContainer.value.scrollTo({ top: 0, behavior: 'smooth' })
  }
  if (filter == 'num') {
    if (currFilter.value !== null && currFilter.value !== 'num') {
      currFilter.value = 'num'
      currFilterSide.value = 'btl'
    } else if (currFilterSide.value == 'ltb' && currFilter.value !== null) {
      currFilter.value = null
      currFilterSide.value = 'btl'
    } else if (currFilterSide.value == 'btl' && currFilter.value !== null) {
      currFilter.value = 'num'
      currFilterSide.value = 'ltb'
    } else if (currFilter.value == null) {
      currFilter.value = 'num'
      currFilterSide.value = 'btl'
    }
  } else if (filter == 'kw') {
    if (currFilter.value !== null && currFilter.value !== 'bring_bonus_kw_level_1') {
      currFilter.value = 'bring_bonus_kw_level_1'
      currFilterSide.value = 'btl'
    } else if (currFilterSide.value == 'ltb' && currFilter.value !== null) {
      currFilter.value = null
      currFilterSide.value = 'btl'
    } else if (currFilterSide.value == 'btl' && currFilter.value !== null) {
      currFilter.value = 'bring_bonus_kw_level_1'
      currFilterSide.value = 'ltb'
    } else if (currFilter.value == null) {
      currFilter.value = 'bring_bonus_kw_level_1'
      currFilterSide.value = 'btl'
    }
  } else if (filter == 'tbtc') {
    if (currFilter.value !== null && currFilter.value !== 'bring_bonus_tbtc_level_1') {
      currFilter.value = 'bring_bonus_tbtc_level_1'
      currFilterSide.value = 'btl'
    } else if (currFilterSide.value == 'ltb' && currFilter.value !== null) {
      currFilter.value = null
      currFilterSide.value = 'btl'
    } else if (currFilterSide.value == 'btl' && currFilter.value !== null) {
      currFilter.value = 'bring_bonus_tbtc_level_1'
      currFilterSide.value = 'ltb'
    } else if (currFilter.value == null) {
      currFilter.value = 'bring_bonus_tbtc_level_1'
      currFilterSide.value = 'btl'
    }
  } else if (filter == 'nft') {
    if (currFilter.value !== null && currFilter.value !== 'nft_count') {
      currFilter.value = 'nft_count'
      currFilterSide.value = 'btl'
    } else if (currFilterSide.value == 'ltb' && currFilter.value !== null) {
      currFilter.value = null
      currFilterSide.value = 'btl'
    } else if (currFilterSide.value == 'btl' && currFilter.value !== null) {
      currFilter.value = 'nft_count'
      currFilterSide.value = 'ltb'
    } else if (currFilter.value == null) {
      currFilter.value = 'nft_count'
      currFilterSide.value = 'btl'
    }
  } else {
    return
  }
}

const shareInvite = () => {
  const link = `https://t.me/share/url?url=https://t.me/tBTCminer_bot?startapp=ref_id${user?.id}&text=Присоединяйся к TonBitcoin Mine`
  return (window.location.href = link)
}

const getBonusData = [
  { type: 'energy', title: t('friends.bonus_title_1'), per_friend: 10, per_next: 5 },
  { type: 'mining', title: t('friends.bonus_title_2'), per_friend: 6, per_next: 3 },
  { type: 'staking', title: t('friends.bonus_title_3'), per_friend: 5, per_next: 2 },
]

const copyInvite = () => {
  const link = `https://t.me/tBTCminer_bot?startapp=ref_id${user?.id}`
  modalStatus.value = 'success'
  modalTitle.value = t('notification.st_success')
  modalBody.value = t('notification.invite_copied')
  openModal.value = true
  return navigator.clipboard.writeText(link)
}

const bonusCardStyle = (idx) => {
  const res = computed(() => ({
    background: `radial-gradient(ellipse 50% 40% at center, ${idx == 0 ? '#3B62C0' : idx == 1 ? '#197A3F' : '#8143FC'}, transparent)${idx == 1 ? ', #0B150F' : ''}`,
  }))
  return res
}

const getBonus = async (bonus_type) => {
  if (bonus_type == 'error') return
  await app.initFriends()
  if (+(app.user.bonus_kw_level_1 + app.user.bonus_kw_level_2) == 0 && bonus_type == 'energy') {
    return
  }
  if (+(app.user.bonus_tbtc_level_1 + app.user.bonus_tbtc_level_2) == 0 && bonus_type == 'tbtc') {
    return
  }
  if (
    +(app.user.bonus_invest_level_1 + app.user.bonus_invest_level_2) == 0 &&
    bonus_type == 'staking'
  ) {
    return
  }
  try {
    controller = new AbortController()
    const res = await host.post(
      `${bonus_type == 'energy' ? 'get-kw-referral-bonuses' : bonus_type == 'tbtc' ? 'get-tbtc-referral-bonuses' : bonus_type == 'staking' ? 'get-staking-referral-bonuses' : null}/`, { signal: controller.signal })
    if (res.status == 200) {
      modalStatus.value = 'success'
      modalTitle.value = t('notification.st_success')
      modalBody.value = t('notification.bonus_withdrawed')
      openModal.value = true
      await app.initFriends()
    }
  } catch (e) {
    console.log(e)
    modalStatus.value = 'error'
    modalTitle.value = t('notification.st_error')
    modalBody.value = e.response.data.error || e.data.error || e.data.message || t('notification.was_error')
    openModal.value = true
    await app.initFriends()
  } finally {
    controller = null
  }
}

const displayedPages = computed(() => {
  const total = allRefs.value
  const current = currPageNum.value
  if (total <= 8) return [...Array(total)].map((_, i) => i + 1)

  const visiblePages = []
  const range = 1 // Скільки сторінок показувати з обох боків від поточної

  // Завжди додаємо першу сторінку
  visiblePages.push(1)

  // Логіка для крапок зліва
  if (current - range > 2) {
    visiblePages.push('...')
  }

  // Центральні сторінки
  const start = Math.max(2, current - range)
  const end = Math.min(total - 1, current + range)

  for (let i = start; i <= end; i++) {
    visiblePages.push(i)
  }

  // Логіка для крапок справа
  if (current + range < total - 1) {
    visiblePages.push('...')
  }

  // Завжди додаємо останню сторінку
  if (total > 1) {
    visiblePages.push(total)
  }

  return visiblePages
})

const loadPageData = async (page) => {
  try {
    const params = {
      page: page,
      page_size: 100,
      ordering: currFilter.value
        ? `${currFilterSide.value === 'ltb' ? '' : '-'}${currFilter.value}`
        : null,
    }
    controller = new AbortController()
    const ref_res = await host.get('referral-info/', { params, signal: controller.signal })
    if (ref_res.status === 200) {
      currPageRefs.value = ref_res.data?.referrals
      app.setReferrals(ref_res.data)
      allRefs.value = Math.ceil(
        (ref_res.data.first_level_count + ref_res.data.second_level_count) / 100,
      )
    }
  } catch (error) {
    console.error('Ошибка загрузки:', error)
    modalStatus.value = 'error'
    modalTitle.value = t('notification.st_error')
    modalBody.value = t('notification.ref_load_err')
    openModal.value = true
  } finally {
    controller = null
  }
}

const nextPage = () => {
  if (currPageNum.value < allRefs.value) {
    currPageNum.value++
    loadPageData(currPageNum.value)
  } else {
    return
  }
}

const prevPage = () => {
  if (currPageNum.value > 1) {
    currPageNum.value--
    loadPageData(currPageNum.value)
  } else {
    return
  }
}

watch(
  [currFilter, currFilterSide],
  () => {
    currPageNum.value = 1
    loadPageData(1)
  },
  { immediate: true },
)

onMounted(async () => {
  await app.initFriends()
  // if (app?.referal) {
  //   currPageNum.value = 1
  //   currPageRefs.value = app?.referal?.referrals
  //   allRefs.value = Math.ceil((app?.referal?.first_level_count + app?.referal?.second_level_count) / 100)
  //   app.setReferrals(app.referal)
  //   return
  // }
  // const ref_res = await host.get("referral-info/")
  // if (ref_res.status == 200) {
  //   currPageNum.value = 1
  //   currPageRefs.value = ref_res.data?.referrals
  //   app.setReferrals(ref_res.data)
  //   allRefs.value = Math.ceil((ref_res.data?.first_level_count + ref_res.data?.second_level_count) / 100)
  // } else {
  //   modalStatus.value = "error"
  //   modalTitle.value = "Ошибка"
  //   modalBody.value = "Не удалось получить список рефералов, попробуйте перезайти на вкладку Friends"
  //   openModal.value = true
  // }
})

onUnmounted(() => {
  if (controller) {
    controller.abort()
  }
})
</script>

<template>
  <InfoModal v-if="openInfoModal" @close="openInfoModal = !openInfoModal">
    <template #modal-body>
      {{ t('modals.friend_info.message') }}
    </template>
  </InfoModal>
  <ModalNew v-if="openModal" :status="modalStatus" :title="modalTitle" :body="modalBody" @close="openModal = false" />
  <div class="screen-box">
    <h1 class="title">{{ t('friends.title') }}</h1>
    <h5 class="desc">{{ t('friends.desc') }}</h5>

    <div class="friend-grid">
      <div class="item invite">
        <div class="buttons-group">
          <button class="invite-btn" @click="shareInvite">
            {{ t('friends.invite_btn') }}
            <Friends :width="22" style="color: #212121" />
          </button>
          <button class="copy-btn" @click="copyInvite">
            <Copy :width="16" />
          </button>
        </div>
      </div>

      <div class="bonus-cards">
        <div class="bonus-card" v-for="(card, index) in getBonusData" :key="index" :style="bonusCardStyle(index).value">
          <InfoFriends class="bonus-card-info" width="17px" height="17px" @click="openInfoModal = true" />
          <h1 class="title">{{ card.title }}</h1>
          <div class="light-line"></div>
          <img v-if="index == 0" src="@/assets/ref_card1.webp" width="62px" height="62px" />
          <img v-if="index == 1" src="@/assets/ref_card2.webp" width="62px" height="62px" />
          <img v-if="index == 2" src="@/assets/ref_card3.webp" width="62px" height="62px" />
          <div class="bonus-data">
            <span><span style="color: #fcd909; font-weight: bold">{{ card.per_friend }}% </span>{{
              t('friends.bonus_desc_1') }}</span>
            <span><span style="color: #fcd909; font-weight: bold">{{ card.per_next }}% </span>{{
              t('friends.bonus_desc_2') }}</span>
          </div>
          <span class="price">
            <img v-if="index == 0" src="@/assets/kW_token.png" width="10px" />
            <img v-if="index !== 0" src="@/assets/fBTC.webp" width="10px" />
            {{
              index == 0
                ? +(app?.user?.bonus_kw_level_1 + app?.user?.bonus_kw_level_2)?.toFixed(2)
                : index == 1
                  ? +(app?.user?.bonus_tbtc_level_1 + app?.user?.bonus_tbtc_level_2)?.toFixed(2)
                  : index == 2
                    ? +(app?.user?.bonus_invest_level_1 + app?.user?.bonus_invest_level_2)?.toFixed(
                      2,
                    )
                    : '0'
            }}</span>
          <button class="get-bonus-button" :class="{
            unactive:
              (index == 0 && +(app.user.bonus_kw_level_1 + app.user.bonus_kw_level_2) == 0) ||
              (index == 1 && +(app.user.bonus_tbtc_level_1 + app.user.bonus_tbtc_level_2) == 0) ||
              (index == 2 &&
                +(app?.user?.bonus_invest_level_1 + app?.user?.bonus_invest_level_2) == 0),
          }" @click="
            getBonus(
              index == 0 ? 'energy' : index == 1 ? 'tbtc' : index == 2 ? 'staking' : 'error',
            )
            ">
            {{ t('friends.bonus_take_btn') }}
          </button>
        </div>
      </div>

      <div class="group-friend-count">
        <span class="title">{{ t('friends.friends_list_title') }}</span>
        <div class="friend-counter">
          <span class="single">
            <SingleUser :width="17" :height="17" />
            <span style="color: #fcd909">{{ app?.referal?.first_level_count || 0 }}</span>{{ t('friends.ref') }}
          </span>
          <span class="group">
            <GroupUser :width="17" :height="17" />
            <span style="color: #fcd909">{{ app?.referal?.second_level_count || 0 }}</span>{{ t('friends.ref') }}
          </span>
        </div>
        <div v-if="currPageRefs.length > 0" class="sorting">
          <div class="sort-pill" :class="{ selected: currFilter == 'num' }" @click="setFilter('num')">
            {{ currFilter == 'num' && currFilterSide == 'ltb' ? '▲' : '▼' }} №
          </div>
          <div class="sort-pill" :class="{ selected: currFilter == 'bring_bonus_kw_level_1' }" @click="setFilter('kw')">
            {{ currFilter == 'bring_bonus_kw_level_1' && currFilterSide == 'ltb' ? '▲' : '▼' }} kW
          </div>
          <div class="sort-pill" :class="{ selected: currFilter == 'bring_bonus_tbtc_level_1' }"
            @click="setFilter('tbtc')">
            {{ currFilter == 'bring_bonus_tbtc_level_1' && currFilterSide == 'ltb' ? '▲' : '▼' }}
            fBTC
          </div>
          <div class="sort-pill" :class="{ selected: currFilter == 'nft_count' }" @click="setFilter('nft')">
            {{ currFilter == 'nft_count' && currFilterSide == 'ltb' ? '▲' : '▼' }} NFT
          </div>
          <!-- ▼ -->
        </div>
      </div>
      <div v-if="currPageRefs.length > 0" class="friends-list"
        :style="currPageRefs.length >= 5 && 'height: calc(100vh - 350px);'" ref="friendScrollContainer">
        <div class="friend" v-for="(friend, idx) in currPageRefs" :key="idx">
          <div class="first-sec">
            <span class="friend-id">#{{ idx + 1 }}</span>
            <span class="friend-name">{{
              friend?.name || friend?.username || friend?.user_id
              }}</span>
          </div>
          <div class="second-sec">
            <div class="currency-line">
              <SingleUser :width="17" :height="17" />
              <div class="grouping">
                <!-- <Energy :width="17" :height="17" /> -->
                <img src="@/assets/kW_token.png" width="17px" height="17px" />
                <span class="energy">{{ friend?.bonus_kw_level_1 || 0 }}</span>
              </div>
              <div class="grouping">
                <!-- <TonBitcoin :width="17" :height="17" /> -->
                <img src="@/assets/fBTC.webp" width="17px" height="17px" />
                <span class="tbtc">{{ friend?.bonus_tbtc_level_1 || 0 }}</span>
              </div>
            </div>
            <div class="currency-line">
              <GroupUser :width="17" :height="17" />
              <div class="grouping">
                <!-- <Energy :width="17" :height="17" /> -->
                <img src="@/assets/kW_token.png" width="17px" height="17px" />
                <span class="energy">{{ friend?.bonus_kw_level_2 || 0 }}</span>
              </div>
              <div class="grouping">
                <!-- <TonBitcoin :width="17" :height="17" /> -->
                <img src="@/assets/fBTC.webp" width="17px" height="17px" />
                <span class="tbtc">{{ friend?.bonus_tbtc_level_2 || 0 }}</span>
              </div>
            </div>
          </div>
          <div class="third-sec">
            <div class="grouping">
              <img src="@/assets/asic_ref.webp" />
              <span class="tbtc">{{ friend?.nft_count || 0 }}</span>
            </div>
          </div>
        </div>
      </div>
      <div v-if="currPageRefs.length > 0" class="friend-pagination">
        <div class="pages">
          <ul class="page-group">
            <li class="page-cell" :class="{ activepage: currPageNum == number, dots: number == '...' }"
              v-for="number in displayedPages" :key="number">
              {{ number }}
            </li>
          </ul>
        </div>
        <div class="navigate-control">
          <button class="prev" :class="{ unactive: currPageNum == 1 }" @click="prevPage">
            {{ t('common.prev_page') }}
          </button>
          <button class="next" :class="{ unactive: currPageNum == allRefs }" @click="nextPage">
            {{ t('common.next_page') }}
          </button>
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
  background: #141e36;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-bottom: 120px;
  overflow-y: scroll;
  -ms-overflow-style: none;
  /* Internet Explorer 10+ */
  scrollbar-width: none;
  /* Firefox */

  &::-webkit-scrollbar {
    display: none;
    /* Safari and Chrome */
  }

  h1 {
    color: #fff;
    font-family: 'Inter' !important;
    font-size: 6vw;
    font-weight: 600;
    margin: 1rem 0 0.2rem;
  }

  .desc {
    width: 70%;
    color: #fff;
    text-align: center;
    font-family: 'Inter' !important;
    font-size: clamp(8px, 3.3vw, 13px);
    font-weight: 400;
    margin: 0 0 1.2rem 0;
  }
}

.friend-grid {
  display: grid;
  width: 90%;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem 0.2rem;

  .item {
    width: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    background: #15140850;
    border: 1px solid #ffffff25;
    border-radius: 1rem;
    padding: 0.5rem 1rem;
    gap: 0.5rem;

    .label-group {
      display: flex;

      .label-text {
        color: #fff;
        font-family: 'Inter' !important;
        font-weight: 700;
        font-size: 11px;
      }
    }

    .price-group {
      display: flex;
      flex-direction: column;
      width: 100%;

      .indicator-row {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;

        h3 {
          color: #fff;
          font-family: 'Inter' !important;
          font-weight: 700;
          font-size: 32px;
        }
      }

      button {
        font-family: 'Inter' !important;
        font-size: 16px;
        font-weight: 600;
        height: 30px;
        width: 100%;
        border-radius: 5px;
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);

        &:active {
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
            linear-gradient(to bottom, #fcd90990, #fea40090);
        }
      }
    }
  }

  .invite {
    grid-column: span 3 / span 3;
    background: radial-gradient(ellipse 50% 35% at bottom, #fcd90950, transparent), #00000050;
    padding: 1rem 1.5rem;

    .buttons-group {
      width: 100%;
      display: flex;
      justify-content: center;
      gap: 1rem;

      .invite-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);
        font-family: 'Inter' !important;
        font-weight: 600;
        font-size: 13px;

        &:active {
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
            linear-gradient(to bottom, #fcd90990, #fea40090);
        }
      }

      .copy-btn {
        padding: 0.9rem 1rem;
        border-radius: 0.5rem;
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);

        &:active {
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
            linear-gradient(to bottom, #fcd90990, #fea40090);
        }
      }
    }
  }

  .bonus-cards {
    grid-column: span 3 / span 3;
    width: 100%;
    display: flex;
    justify-content: center;
    align-items: start;
    gap: 0.3rem;
    text-align: center;

    .bonus-card {
      position: relative;
      display: flex;
      width: 33.33%;
      // height: 240px;
      gap: 0.3rem;
      padding: 0.5rem 0;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      border-radius: 10px;
      color: #fff;
      box-shadow: inset 0 0 0 1px #ffffff20;
      font-family: 'Inter' !important;
      font-size: 10px;
      font-weight: bold;

      @media screen and (max-width: 350px) and (min-height: 800px) {
        height: 250px;
      }

      &-info {
        position: absolute;
        top: 5px;
        right: 5px;
      }

      .title {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 40px;
        max-height: 50px;
        margin: 0 auto;
        font-size: 10px;
        width: 70%;
      }

      .light-line {
        width: 70%;
        height: 1px;
        background: linear-gradient(to right, transparent, #fff, transparent);
      }

      .bonus-data {
        display: flex;
        padding: 0 4px;
        flex-direction: column;
        gap: 0;

        span {
          font-weight: 400;
          font-size: clamp(8px, 2.5vw, 10px);
          text-align: center;
        }
      }

      .price {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0.2rem;
        font-weight: bold;
      }

      .get-bonus-button {
        color: #000;
        text-align: center;
        font-size: 12px;
        font-weight: 600;
        padding: 0.6rem 1rem;
        width: 80%;
        border-radius: 0.5rem;
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);

        &:active {
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff50, transparent),
            linear-gradient(to bottom, #fcd90990, #fea40090);
        }

        &.unactive {
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff50, transparent),
            linear-gradient(to bottom, #fcd90990, #fea40090);
        }
      }
    }
  }

  .group-friend-count {
    grid-column: span 3 / span 3;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    justify-content: center;
    align-items: center;
    color: #fff;
    text-align: center;
    font-family: 'Inter' !important;
    font-size: 16px;
    font-weight: bold;

    .title {
      width: 100%;
    }

    .friend-counter {
      width: 100%;
      display: flex;
      gap: 1rem;
      justify-content: center;
      align-items: center;

      .single,
      .group {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0.3rem;
      }
    }

    .sorting {
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 0 0.2rem;
      gap: 0.5rem;

      .sort-pill {
        padding: 0.2rem 0.8rem;
        border-radius: 1rem;
        font-family: 'Inter' !important;
        font-weight: 400;
        font-size: 12px;
        color: #fff;
        min-width: 20vw;
        border: 1px solid #ffffff25;

        &.selected {
          border: 1px solid #ffffff;
        }
      }
    }
  }

  .friends-list {
    grid-column: span 3 / span 3;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: start;
    gap: 0.3rem;
    // height: calc(100vh - 350px);
    border-radius: 1rem;
    overflow-y: scroll;
    -ms-overflow-style: none;
    /* Internet Explorer 10+ */
    scrollbar-width: none;
    /* Firefox */

    &::-webkit-scrollbar {
      display: none;
      /* Safari and Chrome */
    }

    .friend {
      width: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
      background: #00000050;
      border-radius: 1rem;
      padding: 0.5rem 1rem;
      gap: 0.5rem;

      .first-sec {
        display: flex;
        flex-direction: column;
        align-items: start;
        justify-content: center;
        min-width: 20%;
        max-width: 30%;
        border-right: 1px solid #ffffff50;

        .friend-id {
          color: #fcd909;
          font-family: 'Inter' !important;
          font-weight: bold;
          font-size: 14px;
        }

        .friend-name {
          color: #fff;
          font-family: 'Inter' !important;
          font-weight: 500;
          font-size: 14px;
          max-width: 90%;
          white-space: nowrap;
          text-overflow: ellipsis;
          overflow: hidden;
        }
      }

      .second-sec {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: start;
        gap: 0.3rem;
        border-right: 1px solid #ffffff50;
        width: 90%;
        padding: 0 0.5rem 0 0;

        .currency-line {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 1rem;

          .grouping {
            display: flex;
            align-items: center;
            gap: 0.3rem;

            span {
              color: #fff;
              font-family: 'Inter' !important;
              font-weight: 500;
              font-size: 12px;
            }
          }
        }
      }

      .third-sec {
        display: flex;
        flex-direction: column;
        justify-content: start;
        align-items: start;
        margin-right: 1rem;
        width: 20%;

        .grouping {
          display: flex;
          align-items: center;
          gap: 0.5rem;

          span {
            color: #ffffff;
            font-family: 'Inter' !important;
            font-weight: bold;
            font-size: 14px;
          }
        }
      }
    }
  }

  .friend-pagination {
    grid-column: span 3 / span 3;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.3rem;
    padding-bottom: 1vh;

    .pages {
      display: flex;
      justify-content: center;
      align-items: center;
      margin-bottom: 0.3vh;

      .page-group {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0.3rem;

        .page-cell {
          padding: 0.3rem 0.5rem;
          border-radius: 0.3rem;
          color: #fff;
          background: #08150a50;
          border: 1px solid #ffffff25;
          font-family: 'Inter' !important;
          font-weight: 500;
          font-size: 8px;

          &.dots {
            background: transparent;
            border: none;
            color: #fff;
          }

          &.activepage {
            padding: 0.2rem 0.6rem;
            border-radius: 0.4rem;
            color: #000;
            font-weight: 600;
            font-size: 12px;
            border: none;
            background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
              linear-gradient(to bottom, #fcd909, #fea400);
          }
        }
      }
    }

    .navigate-control {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 1rem;
      width: 80%;

      .prev,
      .next {
        padding: 0.8rem 1rem;
        width: 100%;
        color: #000;
        font-family: 'Inter' !important;
        font-weight: 600;
        font-size: 3vw;
        border-radius: 0.7rem;
        background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff70, transparent),
          linear-gradient(to bottom, #fcd909, #fea400);

        &:active {
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff25, transparent),
            linear-gradient(to bottom, #fcd90990, #fea40090);
        }

        &.unactive {
          background: radial-gradient(ellipse 100% 30% at bottom center, #ffffff25, transparent),
            linear-gradient(to bottom, #fcd90990, #fea40090);
        }
      }
    }
  }
}
</style>
