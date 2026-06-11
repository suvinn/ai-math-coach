import { defineStore } from 'pinia'
import { fetchMe, login, logout, register } from '../api/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    isInitialized: false,
  }),

  getters: {
    isLoggedIn: state => !!state.user,
  },

  actions: {
    async initializeAuth() {
      try {
        this.user = await fetchMe()
      } catch (error) {
        this.user = null
      } finally {
        this.isInitialized = true
      }
    },

    async loginUser(payload) {
      const user = await login(payload)
      this.user = user
      return user
    },

    async registerUser(payload) {
      const user = await register(payload)
      this.user = user
      return user
    },

    async logoutUser() {
      await logout()
      this.user = null
    },
  },
})