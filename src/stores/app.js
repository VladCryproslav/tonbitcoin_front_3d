import { defineStore } from 'pinia'
import { host, tonapi } from '../../axios.config'
import { useTabsStore } from './tabs'
import { getUserProfile, getWallet, getUserTimedNfts } from '@/services/user'
import router from '@/router'

export const useAppStore = defineStore('app', {
  state: () => ({
    loadingProgress: 0,
    wallet_info: {},
    timed_nfts: {},
    score: 0,
    roadmap: {},
    user: {},
    dashboard: {},
    dashboard_info: {},
    referal: {},
    stations: {},
    stationsNft: [],
    availableNftRentals: {},
    rentedNfts: [],
    rentOutNfts: [],
    rental_config: {},
    withdraw_config: {},
    gen_config: {},
    tasks: [],
    task_categ: [],
    wheel_prizes: [],
    boosters: [],
    staking: [],
    special_stake: [],
    staking_config: [],
    nfts: [],
    jettons: [],
    prices: {},
    tonBalance: 0,
    isMining: false,
    power: 0,
    storage: 0,
    energy_run_start_storage: null, // Storage при старте забега (для генерации поинтов)
    hashrate: [],
    miningTime: new Date(),
    pauseUpdate: false,
    showTutorial: false,
    blocked: false,
    kwPerTbtc: null,
    dedust_tbtc: null,
    stonfi_kw: null,
    stonfi_fbtc: null,
    all_fbtc_tokens: null,
    burned_tbtc: [],
  }),
  actions: {
    setBlocked(bool) {
      this.blocked = bool
    },
    setLoadingProgress(progress) {
      if (progress > 100) {
        this.loadingProgress = 100
      } else if (progress < 0) {
        this.loadingProgress = 0
      } else {
        this.loadingProgress = progress
      }
    },
    async init() {
      try {
        this.roadmap = (await host.get('roadmap-items/'))?.data
      } catch (e) {
        console.error(e)
      }
      try {
        this.wallet_info = await getWallet()
      } catch (e) {
        console.error(e)
      }
      try {
        this.timed_nfts = await getUserTimedNfts()
      } catch (e) {
        console.error(e)
      }
      try {
        this.user = await getUserProfile()
      } catch (e) {
        console.error(e)
      }
      try {
        this.score = this.user.energy
      } catch (e) {
        console.error(e)
      }
      const hasSeenTutorial = localStorage.getItem('showTutorial')
      const hoursSinceRegistration = Math.abs(new Date(this.user.register_date).getTime() - new Date().getTime()) / 3600000
      if (hoursSinceRegistration >= 48) {
        // Якщо пройшло більше 48 годин з моменту реєстрації
        localStorage.setItem('showTutorial', false)
        this.showTutorial = false
      } else if (hasSeenTutorial === null) {
        // Якщо значення в localStorage ще не встановлено
        localStorage.setItem('showTutorial', true)
        this.showTutorial = true
      } else {
        // Якщо значення вже є в localStorage
        if (hoursSinceRegistration < 0.016) {
          localStorage.setItem('showTutorial', true)
          this.showTutorial = true
        } else {
          this.showTutorial = hasSeenTutorial === 'true'
        }
      }
      this.power = this.user.power
      this.storage = this.user.storage
      this.isMining = this.user?.is_mining
      try {
        this.referal = (await host.get('referral-info/'))?.data
      } catch (e) {
        console.error(e)
      }
      try {
        this.stations = (await host.get('power-station-configs/'))?.data
      } catch (e) {
        console.error(e)
      }
      try {
        this.withdraw_config = this.stations?.withdraw_config
      } catch (e) {
        console.error(e)
      }
      try {
        this.gen_config = this.stations?.gen_configs
      } catch (e) {
        console.error(e)
      }
      try {
        this.rental_config = this.stations?.rental_config
      } catch (e) {
        console.error(e)
      }
      try {
        this.task_categ = (await host.get('tasks/task_categories/'))?.data
      } catch (e) {
        console.error(e)
      }
      try {
        this.boosters = (await host.get('tasks/boosters/'))?.data
      } catch (e) {
        console.error(e)
      }
      try {
        this.staking = (await host.get('user-stakings/'))?.data
      } catch (e) {
        console.error(e)
      }
      try {
        this.hashrate = (await host.get('hashrate-info/'))?.data
      } catch (e) {
        console.error(e)
      }
      const getPrice = await tonapi.get('rates?tokens=fBTC,kW,TON&currencies=usd')
      if (getPrice.status == 200) {
        this.prices = {
          kW: getPrice.data?.rates['KW']?.prices['USD'],
          fBTC: getPrice.data?.rates['FBTC']?.prices['USD'],
          TON: getPrice.data?.rates['TON']?.prices['USD'],
        }
      }
    },
    async initUser() {
      try {
        this.wallet_info = await getWallet()
      } catch (e) {
        console.error(e)
      }
      try {
        this.timed_nfts = await getUserTimedNfts()
      } catch (e) {
        console.error(e)
      }
      try {
        this.user = await getUserProfile()
      } catch (e) {
        console.error(e)
      }
      this.score = this.user?.energy
      this.power = this.user.power
      this.storage = this.user.storage
      this.isMining = this.user.is_mining
      this.stations = !this.stations
        ? (await host.get('power-station-configs/'))?.data
        : this.stations
      this.withdraw_config = this.stations?.withdraw_config
      this.gen_config = this.stations?.gen_configs
      this.rental_config = this.stations?.rental_config
    },
    initScreen() {
      router.push('/')
      useTabsStore().setTab('home')
      useTabsStore().setCategory('energizer')
    },
    async initFriends() {
      this.user = await getUserProfile()
      if (!this.referal) {
        this.referal = (await host.get('referral-info/'))?.data
      }
    },
    async initTasks(param) {
      this.tasks = (
        await host.get(`tasks/user_tasks/${param ? '?task__categories=' + param : ''}`)
      )?.data
      return this.tasks
    },
    async initTaskCateg() {
      this.tasks = (await host.get('tasks/task_categories/'))?.data
      return this.tasks
    },
    async initBoosters() {
      this.hashrate = (await host.get('hashrate-info/'))?.data
      this.boosters = (await host.get('tasks/boosters/'))?.data
      return this.boosters
    },
    async initStaking() {
      this.staking = (await host.get('user-stakings/'))?.data
      this.special_stake = (await host.get('special-asics/'))?.data
      if (!this.staking_config.length) {
        this.staking_config = (await host.get('staking-configs/'))?.data
      }
    },
    async initWheel() {
      this.wheel_prizes = (await host.get('tasks/wheel_slots/'))?.data
    },
    setMining(bool) {
      this.isMining = bool
    },
    setOverheatedUntil(newValue) {
      if (this.user) {
        this.user.overheated_until = newValue
      }
    },
    setReferrals(referral) {
      this.referal = referral
    },
    setShowTutorial(bool) {
      this.showTutorial = bool
    },
    setPower(pow) {
      if (this.power !== pow) {
        this.power = pow
      }
    },
    setStorage(storage) {
      this.storage = storage
    },
    setEnergyRunStartStorage(storage) {
      this.energy_run_start_storage = storage
    },
    setDashboard(charts) {
      this.dashboard = charts
    },
    setDashboardInfo(info) {
      this.dashboard_info = info
    },
    setMiningTime(time) {
      this.miningTime = time
    },
    setTonBalance(ton) {
      this.tonBalance = ton
    },
    setStationsNft(station_nft) {
      this.stationsNft = station_nft
    },
    setAvailableRental(nfts) {
      this.availableNftRentals = nfts
    },
    setRentedNft(nfts) {
      this.rentedNfts = nfts
    },
    setRentOutNfts(nfts) {
      this.rentOutNfts = nfts
    },
    setNfts(nft) {
      this.nfts = nft
    },
    getAsicsFromStorage() {
      const asicsFromStorage = localStorage.getItem('all_asics')
      if (asicsFromStorage) {
        return JSON.parse(asicsFromStorage)
      }
      return []
    },
    clearAsicsCache() {
      localStorage.removeItem('all_asics')
    },
    setPrices(prices) {
      this.prices = prices
    },
    setJettons(jet) {
      this.jettons = jet
    },
    clearJettonsCache() {
      this.jettons = []
      localStorage.removeItem('last_jettons_address')
    },
    setPauseUpdate(bool) {
      this.pauseUpdate = bool
    },
    setScore(score) {
      if (this.score !== score) {
        this.score = score
      }
    },
    addScore(score = 0.1) {
      this.score += score
    },
    setStonfiKw(price) {
      this.stonfi_kw = price
    },
    setDeDustTbtc(price) {
      this.dedust_tbtc = price
    },
    setStonfiFbtc(price) {
      this.stonfi_fbtc = price
    },
    setKwPerTbtc(price) {
      this.kwPerTbtc = price
    },
    setAllFbtcTokens(count) {
      this.all_fbtc_tokens = count
    },
    setBurnedTbtc(num) {
      this.burned_tbtc = num
    },
    clearAllCaches() {
      this.jettons = []
      this.nfts = []
      this.rentedNfts = []
      this.rentOutNfts = []
      localStorage.removeItem('all_asics')
      localStorage.removeItem('last_jettons_address')
    },
  },
})
