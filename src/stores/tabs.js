import { defineStore } from 'pinia'

export const useTabsStore = defineStore('tabs', {
  state: () => ({
    tab: 'home',
    category: 'energizer',
    openAsicShop: false,
    openEquip: false,
    openBoost: false,
    openDashboard: false,
    background: '#141e36',
  }),
  getters: {
    currentTab(state) {
      return state.tab
    },
    currentCategory(state) {
      return state.category
    },
    currentOpenAsics(state) {
      return state.openAsicShop
    },
    currentOpenEquip(state) {
      return state.openEquip
    },
    currentBackground(state) {
      return state.background
    },
  },
  actions: {
    setTab(tab) {
      this.tab = tab
    },
    setCategory(category) {
      this.category = category
    },
    setOpenAsicsShop(openasics) {
      this.openAsicShop = openasics
    },
    setOpenEquip(openeq) {
      this.openEquip = openeq
    },
    setBackground(color) {
      this.background = color
    },
    setBoost(bool) {
      this.openBoost = bool
    },
    setDashboard(bool) {
      if (this.category == 'boost'){
        return
      }
      this.openDashboard = bool
    },
  },
})
