/**
 * 鐢ㄦ埛鐘舵€佺鐞?
 * 绠＄悊鐢ㄦ埛鐧诲綍淇℃伅銆乀oken銆佽鑹茬瓑
 */
import { defineStore } from 'pinia'
import { loginApi, getUserInfoApi } from '@/api/auth'

const TOKEN_KEY = 'ssdd_token'
const USER_KEY = 'ssdd_user'

export const useUserStore = defineStore('user', {
  state: () => ({
    // JWT Token
    token: localStorage.getItem(TOKEN_KEY) || '',
    // 鐢ㄦ埛淇℃伅
    user: JSON.parse(localStorage.getItem(USER_KEY) || 'null'),
  }),

  getters: {
    /** 鏄惁宸茬櫥褰?*/
    isLoggedIn: (state) => !!state.token,

    /** 鐢ㄦ埛鍚?*/
    username: (state) => state.user?.username || '',

    /** 鐢ㄦ埛澶村儚 */
    avatar: (state) => state.user?.avatar || '',

    /** 鐢ㄦ埛瑙掕壊鍒楄〃 */
    roles: (state) => state.user?.roles || [],

    /** 鏄惁涓虹鐞嗗憳 */
    isSuperuser: (state) => state.user?.is_superuser || false,
  },

  actions: {
    /**
     * 鐢ㄦ埛鐧诲綍
     * @param {Object} credentials - { username, password }
     */
    async login(credentials) {
      const res = await loginApi(credentials)

      // 淇濆瓨 Token
      this.token = res.access_token
      localStorage.setItem(TOKEN_KEY, res.access_token)

      // 淇濆瓨鐢ㄦ埛淇℃伅
      this.user = res.user
      localStorage.setItem(USER_KEY, JSON.stringify(res.user))

      return res
    },

    /**
     * 鑾峰彇鏈€鏂扮敤鎴蜂俊鎭?
     */
    async fetchUserInfo() {
      try {
        const user = await getUserInfoApi()
        this.user = user
        localStorage.setItem(USER_KEY, JSON.stringify(user))
      } catch {
        this.logout()
      }
    },

    /**
     * 閫€鍑虹櫥褰?
     */
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },
  },
})
