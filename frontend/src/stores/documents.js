/**
 * 文档状态管理（Pinia）。
 *
 * 管理文档列表、分页、上传、删除，
 * 以及处理中文档（pending/processing）的自动轮询。
 */
import { defineStore } from 'pinia';
import { getDocuments, uploadDocuments, deleteDocument } from '@/api/documents';
import { DEFAULT_PAGE_SIZE, DOCUMENT_STATUS, PROCESSING_POLL_INTERVAL } from '@/utils/constants';

export const useDocumentsStore = defineStore('documents', {
  state: () => ({
    /** @type {Array} 文档列表 */
    list: [],
    /** 分页信息 */
    pagination: { page: 1, size: DEFAULT_PAGE_SIZE, total: 0, totalPages: 0 },
    /** 列表加载中 */
    loading: false,
    /** 上传中 */
    uploading: false,
    /** 上传进度（0-100） */
    uploadProgress: 0,
    /** 轮询定时器 */
    _pollTimer: null,
  }),

  getters: {
    /** 是否有文档 */
    hasDocuments: (state) => state.list.length > 0,
    /** 是否有处理中文档 */
    hasProcessing: (state) =>
      state.list.some(
        (doc) => doc.status === DOCUMENT_STATUS.PROCESSING || doc.status === DOCUMENT_STATUS.PENDING,
      ),
    /** 已完成文档数 */
    completedCount: (state) =>
      state.list.filter((doc) => doc.status === DOCUMENT_STATUS.COMPLETED).length,
  },

  actions: {
    /**
     * 获取文档列表。
     * @param {{page?: number, size?: number, status?: string}} params
     */
    async fetchDocuments(params = {}) {
      this.loading = true;
      try {
        const res = await getDocuments(params);
        this.list = res.data || [];
        if (res.meta?.pagination) {
          this.pagination = res.meta.pagination;
        }
        // 存在处理中文档时启动轮询
        this.startPollingIfNeeded();
      } finally {
        this.loading = false;
      }
    },

    /**
     * 上传文档。
     * @param {File[]} files
     * @returns {Promise<{documents: Array, failed: Array}>}
     */
    async upload(files) {
      this.uploading = true;
      this.uploadProgress = 0;
      try {
        const res = await uploadDocuments(files, (percent) => {
          this.uploadProgress = percent;
        });
        // 上传完成后刷新列表（新文档状态为 processing）
        await this.fetchDocuments();
        return res.data || { documents: [], failed: [] };
      } finally {
        this.uploading = false;
        this.uploadProgress = 0;
      }
    },

    /**
     * 删除文档。
     * @param {string} id
     */
    async remove(id) {
      await deleteDocument(id);
      // 本地立即移除，避免等待刷新
      this.list = this.list.filter((doc) => doc.id !== id);
      this.pagination.total = Math.max(0, this.pagination.total - 1);
    },

    /**
     * 启动处理中文档的轮询（若已有轮询则跳过）。
     */
    startPollingIfNeeded() {
      if (this._pollTimer) return;
      if (!this.hasProcessing) return;

      this._pollTimer = setInterval(async () => {
        if (!this.hasProcessing) {
          this.stopPolling();
          return;
        }
        try {
          const res = await getDocuments({ page: this.pagination.page, size: this.pagination.size });
          this.list = res.data || [];
          if (res.meta?.pagination) {
            this.pagination = res.meta.pagination;
          }
          if (!this.hasProcessing) {
            this.stopPolling();
          }
        } catch {
          // 轮询失败时停止，避免频繁报错
          this.stopPolling();
        }
      }, PROCESSING_POLL_INTERVAL);
    },

    /** 停止轮询。 */
    stopPolling() {
      if (this._pollTimer) {
        clearInterval(this._pollTimer);
        this._pollTimer = null;
      }
    },

    /** 重置 store（切换会话/Provider 时调用）。 */
    reset() {
      this.stopPolling();
      this.list = [];
      this.pagination = { page: 1, size: DEFAULT_PAGE_SIZE, total: 0, totalPages: 0 };
    },
  },
});
