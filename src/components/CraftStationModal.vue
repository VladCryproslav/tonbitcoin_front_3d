<template>
  <div class="modal-mask" name="modal">
    <div class="modal-wrapper">
      <div class="modal-container">
        <button class="close" @click="emitClose">
          <Exit style="color: #fff" />
        </button>
        <div class="grouping">
          <div class="modal-header">
            {{ kind == 'mint'
              ? (allStations.indexOf(app.user?.station_type) >= 5 ? t('modals.craft_station.title_craft') :
                t('modals.craft_station.title_mint'))
              : t('modals.craft_station.title_warning')
            }}
          </div>
          <div class="modal-body">
            {{ kind == 'renew'
              ? t('modals.craft_station.message_renew', { station: app.user.station_type })
              : kind == 'mint'
                ? t('modals.craft_station.message_mint', {
                  station: allStations[allStations.indexOf(app.user?.station_type) + ((!!app.user?.current_mint ||
                    allStations.indexOf(app.user?.station_type) == 3) ? 1 : 0)]
                }) + (app.stationsNft.length || app.user?.current_mint ? t('modals.craft_station.message_mint_burn') :
                  allStations.indexOf(app.user?.station_type) == 3 ? t('modals.craft_station.message_mint_special') : '')
                : kind == 'notfound'
                  ? t('modals.craft_station.message_notfound', { station: app.user.station_type })
                  : ''
            }}
          </div>
          <div class="price">
            <div
              v-if="(app.user?.current_mint && app.stationsNft.length) || allStations.indexOf(app.user?.station_type) == 3"
              class="tbtc-price">
              <span>{{
                kind == 'mint' ? t('modals.craft_station.cost_kw') : t('modals.craft_station.energy_balance')
                }}</span>
              <span class="font-semibold flex gap-1">{{ props.kw || 0 }}<img class="ml-1" src="@/assets/kW.png"
                  width="16px" height="16px" /></span>
            </div>
            <div v-if="props.tbtc && props.kind == 'mint'" class="tbtc-price">
              <span>{{ t('modals.craft_station.cost_fbtc') }}</span>
              <span class="font-semibold flex gap-1">{{((app.user?.current_mint && app.stationsNft.length) ||
                allStations.indexOf(app.user?.station_type) == 3) ? props.tbtc
                : +(+app.stations?.storage_configs?.find((el) => el?.station_type ==
                  allStations[allStations.indexOf(app.user?.station_type)] && el?.level == 1)?.price_tbtc / 2).toFixed(2)
              }}<img class="ml-1" src="@/assets/fBTC.webp" width="16px" height="16px" /></span>
            </div>
            <div
              v-if="props.nft && props.kind == 'mint' && allStations.indexOf(app.user?.station_type) >= 4 && app.stationsNft.length"
              class="tbtc-price">
              <span>{{ t('modals.craft_station.nft') }}</span>
              <span class="font-semibold flex gap-1">{{ props.nft
              }} x2<img class="ml-1" src="@/assets/mintable.png" width="16px" height="16px" /></span>
            </div>
            <div v-if="props.eng_lost && props.kind !== 'mint'" class="tbtc-price">
              <span>{{ t('modals.craft_station.engineers_lost') }}</span>
              <span class="font-semibold flex gap-1">-{{ props.eng_lost
              }}<img class="ml-1" src="@/assets/engineer.webp" width="16px" height="16px" />
              </span>
            </div>
            <div v-if="props.time" class="tbtc-price">
              <span>{{ props.kind == 'mint' ? t('modals.craft_station.build_time') :
                t('modals.craft_station.rollback_time') }}</span>
              <span class="font-semibold flex gap-1">{{((app.user?.current_mint && app.stationsNft.length) ||
                allStations.indexOf(app.user?.station_type) == 3) ?
                convertTimeFormat(props.time) : convertTimeFormat(app.stations?.storage_configs?.find((el) =>
                  el?.station_type == allStations[allStations.indexOf(app.user?.station_type)] && el?.level ==
                  1)?.duration)}}<img class="ml-1" src="@/assets/time.webp" width="16px" height="16px" />
              </span>
            </div>
          </div>
          <div class="buttons-group">
            <button class="confirm" @click="confirm">{{ t('modals.craft_station.confirm') }}</button>
            <button class="cancel" @click="emitClose">{{ t('modals.craft_station.cancel') }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const Exit = defineAsyncComponent(() => import('@/assets/upg-modal-close.svg'))
import { useAppStore } from '@/stores/app'
import { defineAsyncComponent } from 'vue'
import { host } from '../../axios.config'
import { Address, beginCell, toNano } from '@ton/core'
import { useTonConnectUI } from '@townsquarelabs/ui-vue'
import { useTelegram } from '@/services/telegram'
import { useI18n } from 'vue-i18n'

const app = useAppStore()
const { t } = useI18n()

const { networkFee, userAddress } = useTelegram();
const { tonConnectUI } = useTonConnectUI()

const props = defineProps({
  kind: String,
  kw: String,
  tbtc: String,
  eng_lost: String,
  nft: String,
  time: String,
  notif_id: Number
})

const emit = defineEmits(['close'])

const allStations = [...new Set(app.stations?.storage_configs?.map((el) => el?.station_type))]

const emitClose = () => {
  emit('close')
}

function convertTimeFormat(timeStr) {
  if (!timeStr) return;

  let days, hours, minutes, seconds;
  if (timeStr.includes(' ')) {
    const [daysPart, timePart] = timeStr.split(' ');
    days = parseInt(daysPart);
    [hours, minutes, seconds] = timePart.split(':');
  } else {
    days = 0; // Днів немає
    [hours, minutes, seconds] = timeStr.split(':');
  }
  // const [days, time] = timeStr.split(' ');
  // const [hours, minutes, seconds] = time.split(':');

  // Переводимо все в секунди
  const daysInSeconds = parseInt(days) * 24 * 60 * 60;
  const hoursInSeconds = parseInt(hours) * 60 * 60;
  const minutesInSeconds = parseInt(minutes) * 60;
  const secondsTotal = parseInt(seconds);

  // Сумуємо всі секунди
  const totalSeconds = daysInSeconds + hoursInSeconds + minutesInSeconds + secondsTotal;

  // Переводимо назад у формат HH:MM:SS
  const newHours = Math.floor(totalSeconds / 3600);
  const remainingSeconds = totalSeconds % 3600;
  const newMinutes = Math.floor(remainingSeconds / 60);
  const newSeconds = remainingSeconds % 60;

  // Форматуємо з провідними нулями
  const formattedHours = String(newHours).padStart(2, '0');
  const formattedMinutes = String(newMinutes).padStart(2, '0');
  const formattedSeconds = String(newSeconds).padStart(2, '0');

  return `${formattedHours}:${formattedMinutes}:${formattedSeconds}`;
}

async function confirm() {
  if (props.kind == 'mint') {
    let kwPrice = props.kw
    let tbtcPrice = ((app.user?.current_mint && app.stationsNft.length) || allStations.indexOf(app.user?.station_type) == 3) ? props.tbtc : +(+app.stations?.storage_configs?.find((el) => el?.station_type == allStations[allStations.indexOf(app.user?.station_type)] && el?.level == 1)?.price_tbtc / 2)
    if (kwPrice && app?.user?.energy < kwPrice) {
      emit('close', {
        status: 'error',
        title: t('notification.st_error'),
        body: t('notification.insufficient_funds'),
      })
      return;
    }
    if (tbtcPrice && app?.user?.tbtc_wallet < tbtcPrice) {
      emit('close', {
        status: 'error',
        title: t('notification.st_error'),
        body: t('notification.insufficient_funds'),
      })
      return;
    }
    let nfts_to_burn = []
    try {
      if (allStations.indexOf(app.user?.station_type) >= 4) {
        console.log("Burn Stations")
        const receiveWallet = 'UQASp_CpNEoFI-HvTurh74NTxdV_vuXGGd1PzsJsinnJjUkp'
        const receiveWalletAddress = Address.parse(receiveWallet)
        const nft_list = app.stationsNft.filter(el => el?.metadata?.name?.toLowerCase() == app.user?.station_type.toLowerCase())
        if (nft_list.length >= 2) {
          const messages = nft_list.slice(0, 2).map(item => {
            let nftAddress = Address.parse(item.address)
            nfts_to_burn.push(item?.address)
            const nftMsg = beginCell()
              .storeUint(0x5fcc3d14, 32)     // Правильний op код для NFT transfer
              .storeUint(0, 64)              // query_id
              .storeAddress(receiveWalletAddress) // new_owner_address
              .storeAddress(Address.parse(userAddress)) // response_address
              .storeBit(0)                   // Немає custom_payload
              .storeCoins(toNano(0.01))      // forward_amount 
              .storeBit(0)                   // Немає forward_payload
              .endCell()
            return {
              address: nftAddress.toString(),
              amount: toNano(networkFee).toString(), // Сума для відправки на контракт NFT
              stateInit: null,
              payload: nftMsg.toBoc().toString('base64'),
            };
          })
          console.log("NFTS to BURN: ", nfts_to_burn)
          const transData = {
            validUntil: Date.now() + 1000 * 60 * 5,
            messages: messages, // Масив із двома повідомленнями
          };
          try {
            await tonConnectUI.sendTransaction(transData, {
              modals: ['before', 'success'],
              notifications: [],
            })
          } catch (err) {
            // Якщо користувач скасував транзакцію, не показуємо помилку
            if (err.message && err.message.includes('User rejected')) {
              console.log('User cancelled transaction')
              return
            }
            throw err
          }
        } else {
          if (app.user?.current_mint) {
            return;
          }
        }
      }
      const curr_station = app.user?.station_type
      const res = await host.post('mint-station/', nfts_to_burn.length >= 2 ? { "burn_nft1": nfts_to_burn?.[0], "burn_nft2": nfts_to_burn?.[1] } : {})
      console.log("BURN Response: ", res)
      if (res.status == 200 && res.data.message !== 'Insufficient resources') {
        await app.initUser()
        if (!app.stationsNft.length) {
          emit('close', {
            status: 'success',
            title: t('notification.st_success'),
            body: t('modals.craft_station.process_started', { station: allStations[allStations.indexOf(curr_station)] })
          })
        } else {
          emit('close', {
            status: 'success',
            title: t('notification.st_success'),
            body: t('modals.craft_station.nft_sent_burn', { station: allStations[allStations.indexOf(curr_station) + 1] })
          })
        }
      } else if (res.status == 200 && res.data.message == 'Insufficient resources') {
        emit('close', {
          status: 'error',
          title: t('notification.st_error'),
          body: t('notification.insufficient_funds'),
        })
      }
    } catch (err) {
      console.log(err)
      emit('close', {
        status: 'error',
        title: t('notification.st_error'),
        body: err.response.data.error,
      })
    }
  }
  if (props.kind == 'renew') {
    try {
      const res = await host.post('rollback-station/')
      if (res.status == 200) {
        await app.initUser()
        emit('close', {
          status: 'success',
          title: t('notification.st_success'),
          body: t('modals.craft_station.progress_reset')
        })
      }
    } catch (err) {
      console.log(err)
      emit('close', {
        status: 'error',
        title: t('notification.st_error'),
        body: err.response.data.error,
      })
    }
  }
  if (props.kind == 'notfound') {
    emit('close', {
      status: 'success',
      title: t('notification.st_success'),
      body: t('modals.craft_station.progress_reset'),
      notif_id: props.notif_id
    })
  }
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
        width: 70%;
        padding: 0.5rem;
        color: #000;
        border-radius: 5rem;
        background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
          linear-gradient(to bottom, #e2f974, #009600);
        box-shadow:
          inset 0 0 0 2px #10151b,
          0 0 0 1px #8be113;

        &:active {
          background: radial-gradient(ellipse 80% 20% at top, #ffffff50, transparent),
            linear-gradient(to bottom, #e2f97490, #00960090);
        }
      }

      .cancel {
        width: 30%;
        padding: 0.5rem;
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
</style>
