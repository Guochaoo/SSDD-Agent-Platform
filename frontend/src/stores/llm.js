/**
 * LLM 模型状态管理
 * 启动时自动从后端拉取可用模型列表
 */
import { defineStore } from 'pinia'
import request from '@/utils/request'

export const useLlmStore = defineStore('llm', {
  state: () => ({
    /** 可用模型列表 [{ id, owned_by }] */
    models: [],
    /** 是否正在加载 */
    loading: false,
    /** 是否已加载过 */
    loaded: false,
    /** 错误信息 */
    error: null,
    /** LLM 提供商 */
    provider: null,
  }),

  getters: {
    /** 是否有可用模型 */
    hasModels: (state) => state.models.length > 0,

    /** 推荐模型（优先取 gpt-4o-mini） */
    defaultModel: (state) => {
      if (!state.models.length) return 'gpt-4o-mini'
      const preferred = state.models.find(m => m.id === 'gpt-4o-mini')
      return preferred ? preferred.id : state.models[0].id
    },

    /** 格式化的模型选项列表（供下拉组件使用） */
    modelOptions: (state) =>
      state.models.map((m) => ({
        label: m.id,
        value: m.id,
        ownedBy: m.owned_by,
      })),
  },

  actions: {
    /**
     * 从后端拉取可用模型列表
     */
    async fetchModels() {
      if (this.loading || this.loaded) return
      this.loading = true
      this.error = null
      try {
        const data = await request.get('/agent/models')
        this.models = data?.models ?? []
        this.provider = data?.provider ?? null
        this.loaded = true
      } catch (err) {
        this.error = err?.response?.data?.detail || '获取模型列表失败'
        // 未配置 API Key 时不弹错误，仅记录
        console.warn('[LLM Store] 获取模型列表失败:', this.error)
      } finally {
        this.loading = false
      }
    },
  },
})
