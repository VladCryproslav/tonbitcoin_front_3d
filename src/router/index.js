import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/tasks',
      name: 'tasks',
      component: () => import('@/views/TasksView.vue'),
    },
    {
      path: '/market',
      name: 'market',
      component: () => import('@/views/MarketView.vue'),
    },
    {
      path: '/wallet',
      name: 'wallet',
      component: () => import('@/views/WalletView.vue'),
    },
    {
      path: '/friends',
      name: 'friends',
      component: () => import('@/views/FriendsView.vue'),
    },
    {
      path: '/games',
      name: 'games',
      component: () => import('@/views/GameSelectionView.vue'),
    },
    {
      path: '/wheel',
      name: 'wheel',
      component: () => import('@/views/WheelView.vue'),
    },
    {
      path: '/lottery',
      name: 'lottery',
      component: () => import('@/views/LotteryView.vue'),
    },
    {
      path: '/game-run',
      name: 'game-run',
      component: () => import('@/views/GameRunView.vue'),
    },
  ],
})

export default router
