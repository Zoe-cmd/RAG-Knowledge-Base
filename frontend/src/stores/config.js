/**
 * 配置状态管理（Pinia）。
 *
 * 管理应用配置（Embedding Provider、向量维度、RAG 参数）
 * 与全局统计信息（文档数、切片数、会话数等）。
 */
import { defineStore } from 'pinia';
import { getConfig, switchEmbeddingProvider } from '@/api/config';

export const useConfigStore = defineStore('config', {
  state: () => ({
    /** 配置信息 */
    config: {
      embedding_provider: 'openai',
      embedding_dimension: 1536,
      llm_model: 'gpt-4o-mini',
      chunk_size: 500,
      chunk_overlap: 50,
      top_k: 5,
      similarity_threshold: 0.3,
      max_history_rounds: 4,
      max_file_size_mb: 20,
      max_documents: 100,
    },
    /** 统计信息 */
    statistics: {
      total_documents: 0,
      completed_documents: 0,
      processing_documents: 0,
      failed_documents: 0,
      total_chunks: 0,
      total_sessions: 0,
      total_messages: 0,
    },
    /** 加载中 */
    loading: false,
    /** Provider 切换中 */
    switching: false,
  }),

  getters: {
    /** 当前 Provider */
    currentProvider: (state) => state.config.embedding_provider,
    /** 向量维度 */
    dimension: (state) => state.config.embedding_dimension,
    /** 文档总数 */
    totalDocuments: (state) => state.statistics.total_documents,
  },

  actions: {
    /** 获取配置与统计。 */
    async fetchConfig() {
      this.loading = true;
      try {
        const res = await getConfig();
        const data = res.data || {};
        this.config = {
          embedding_provider: data.embedding_provider ?? this.config.embedding_provider,
          embedding_dimension: data.embedding_dimension ?? this.config.embedding_dimension,
          llm_model: data.llm_model ?? this.config.llm_model,
          chunk_size: data.chunk_size ?? this.config.chunk_size,
          chunk_overlap: data.chunk_overlap ?? this.config.chunk_overlap,
          top_k: data.top_k ?? this.config.top_k,
          similarity_threshold: data.similarity_threshold ?? this.config.similarity_threshold,
          max_history_rounds: data.max_history_rounds ?? this.config.max_history_rounds,
          max_file_size_mb: data.max_file_size_mb ?? this.config.max_file_size_mb,
          max_documents: data.max_documents ?? this.config.max_documents,
        };
        if (data.statistics) {
          this.statistics = { ...this.statistics, ...data.statistics };
        }
      } finally {
        this.loading = false;
      }
    },

    /**
     * 切换 Embedding Provider。
     * @param {string} provider - openai / bge
     * @returns {Promise<object>} 切换结果
     */
    async switchProvider(provider) {
      this.switching = true;
      try {
        const res = await switchEmbeddingProvider(provider);
        const data = res.data || {};
        // 更新本地配置
        if (data.current_provider) {
          this.config.embedding_provider = data.current_provider;
        }
        if (data.current_dimension) {
          this.config.embedding_dimension = data.current_dimension;
        }
        return data;
      } finally {
        this.switching = false;
      }
    },
  },
});
