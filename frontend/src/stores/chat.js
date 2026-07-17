/**
 * 对话状态管理（Pinia）。
 *
 * 管理当前会话的消息列表与 SSE 流式问答的全生命周期：
 * references → token → done / error，支持 AbortController 中断。
 *
 * 关键状态机：
 *   idle → sending（发起请求）→ generating（接收 token）→ done / error
 */
import { defineStore } from 'pinia';
import { streamChat } from '@/api/chat';
import { getSessionMessages } from '@/api/sessions';
import { useSessionsStore } from './sessions';
import { MESSAGE_ROLE } from '@/utils/constants';

export const useChatStore = defineStore('chat', {
  state: () => ({
    /** @type {Array} 当前会话的消息列表 */
    messages: [],
    /** 消息加载中 */
    loadingMessages: false,
    /** 是否正在生成回答 */
    isGenerating: false,
    /** 当前流式回答的引用来源（空数组表示无相关内容） */
    currentReferences: [],
    /** 是否命中"无相关内容"（references 为空数组） */
    noContext: false,
    /** AbortController 实例 */
    _abortController: null,
  }),

  getters: {
    /** 是否有消息 */
    hasMessages: (state) => state.messages.length > 0,
    /** 当前会话 ID（取自 sessions store） */
    sessionId() {
      return useSessionsStore().currentId;
    },
  },

  actions: {
    /**
     * 加载指定会话的消息列表。
     * @param {string} sessionId
     */
    async loadMessages(sessionId) {
      if (!sessionId) {
        this.messages = [];
        return;
      }
      this.loadingMessages = true;
      try {
        const res = await getSessionMessages(sessionId);
        this.messages = (res.data?.messages || []).map((msg) => ({
          ...msg,
          streaming: false,
        }));
      } catch {
        this.messages = [];
      } finally {
        this.loadingMessages = false;
      }
    },

    /**
     * 发送消息并接收流式回答。
     *
     * 流程：
     * 1. 追加用户消息
     * 2. 追加 assistant 占位消息（streaming=true）
     * 3. 发起 SSE 请求，逐 token 填充占位消息
     * 4. done 时回填 message_id / elapsed_ms；error 时回填错误信息
     *
     * @param {string} question - 用户问题
     */
    async sendMessage(question) {
      const sessionId = this.sessionId;
      if (!sessionId) {
        throw new Error('未选择会话');
      }
      if (!question || !question.trim()) {
        return;
      }
      if (this.isGenerating) {
        return;
      }

      const now = new Date().toISOString();

      // 1. 追加用户消息
      this.messages.push({
        id: `temp-user-${Date.now()}`,
        role: MESSAGE_ROLE.USER,
        content: question.trim(),
        references: null,
        elapsed_ms: null,
        created_at: now,
      });

      // 2. 追加 assistant 占位消息
      // 注意：push 后需通过 this.messages[index] 获取响应式代理对象，
      // 直接修改原始对象不会触发 Vue 响应式更新（Vue 3 Proxy 机制）。
      this.messages.push({
        id: `temp-assistant-${Date.now()}`,
        role: MESSAGE_ROLE.ASSISTANT,
        content: '',
        references: [],
        elapsed_ms: null,
        created_at: now,
        streaming: true,
        error: null,
      });
      // 获取 Pinia store 中的响应式代理引用（而非原始对象）
      const assistantMsg = this.messages[this.messages.length - 1];

      // 3. 重置流式状态
      this.isGenerating = true;
      this.currentReferences = [];
      this.noContext = false;
      this._abortController = new AbortController();

      const sessionsStore = useSessionsStore();

      try {
        await streamChat(sessionId, question.trim(), {
          signal: this._abortController.signal,
          onReferences: (refs) => {
            this.currentReferences = refs;
            assistantMsg.references = refs;
            // references 为空数组 → 未找到相关内容（FR-RAG-008）
            this.noContext = refs.length === 0;
          },
          onToken: (content) => {
            assistantMsg.content += content;
          },
          onDone: (payload) => {
            assistantMsg.message_id = payload?.message_id;
            assistantMsg.elapsed_ms = payload?.elapsed_ms ?? null;
            assistantMsg.streaming = false;
            // 无相关内容时，给出友好提示文案
            if (this.noContext && !assistantMsg.content) {
              assistantMsg.content = '未在文档库中找到相关内容，请尝试换个问题或上传更多文档。';
            }
          },
          onError: (err) => {
            assistantMsg.streaming = false;
            assistantMsg.error = err;
            // 未生成任何内容时，用错误信息占位
            if (!assistantMsg.content) {
              assistantMsg.content = err?.message || '回答生成失败，请重试';
            }
          },
        });

        // 4. 同步会话统计（消息数、最后活跃时间）
        const newCount = (sessionsStore.currentSession?.message_count || 0) + 2;
        sessionsStore.patchSession(sessionId, {
          message_count: newCount,
          last_message_at: now,
        });
      } finally {
        this.isGenerating = false;
        this._abortController = null;
      }
    },

    /**
     * 中断当前生成（FR-RAG-007：保留已生成内容）。
     */
    stopGenerating() {
      if (this._abortController) {
        this._abortController.abort();
        this._abortController = null;
      }
      this.isGenerating = false;
      // 标记最后一条 assistant 消息为已完成
      const last = this.messages[this.messages.length - 1];
      if (last?.streaming) {
        last.streaming = false;
        last.aborted = true;
      }
    },

    /** 清空消息（切换会话前调用）。 */
    clearMessages() {
      this.stopGenerating();
      this.messages = [];
      this.currentReferences = [];
      this.noContext = false;
    },

    /** 重置 store。 */
    reset() {
      this.clearMessages();
    },
  },
});
