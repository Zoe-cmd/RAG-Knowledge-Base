/**
 * 会话状态管理（Pinia）。
 *
 * 管理会话列表的增删改查，不持有消息内容（消息由 chat store 管理）。
 */
import { defineStore } from 'pinia';
import {
  createSession,
  getSessions,
  deleteSession,
  clearAllSessions,
} from '@/api/sessions';

export const useSessionsStore = defineStore('sessions', {
  state: () => ({
    /** @type {Array} 会话列表 */
    list: [],
    /** 列表加载中 */
    loading: false,
    /** 当前选中的会话 ID */
    currentId: null,
  }),

  getters: {
    /** 当前会话对象 */
    currentSession: (state) => state.list.find((s) => s.id === state.currentId) || null,
    /** 是否有会话 */
    hasSessions: (state) => state.list.length > 0,
  },

  actions: {
    /** 获取会话列表。 */
    async fetchSessions() {
      this.loading = true;
      try {
        const res = await getSessions();
        this.list = res.data || [];
      } finally {
        this.loading = false;
      }
    },

    /**
     * 新建会话。
     * @returns {Promise<object>} 新建的会话对象
     */
    async create() {
      const res = await createSession();
      const session = res.data;
      // 插入列表顶部
      this.list.unshift(session);
      this.currentId = session.id;
      return session;
    },

    /**
     * 选择会话。
     * @param {string} id
     */
    select(id) {
      this.currentId = id;
    },

    /**
     * 删除单个会话。
     * @param {string} id
     */
    async remove(id) {
      await deleteSession(id);
      const wasCurrent = this.currentId === id;
      this.list = this.list.filter((s) => s.id !== id);
      if (wasCurrent) {
        // 删除当前会话后，自动选择第一个（或清空）
        this.currentId = this.list[0]?.id || null;
      }
    },

    /**
     * 清空所有会话。
     */
    async clearAll() {
      const res = await clearAllSessions();
      this.list = [];
      this.currentId = null;
      return res.data?.deleted_count || 0;
    },

    /**
     * 更新会话的最后活跃信息（发送消息后本地同步）。
     * @param {string} id
     * @param {{message_count?: number, last_message_at?: string, title?: string}} patch
     */
    patchSession(id, patch) {
      const session = this.list.find((s) => s.id === id);
      if (session) {
        Object.assign(session, patch);
      }
    },

    /** 重置 store。 */
    reset() {
      this.list = [];
      this.currentId = null;
    },
  },
});
