<script setup>
/**
 * 对话区容器（design-system.md 7.1）。
 *
 * 输入区始终展示在底部；上方区域有消息时展示 MessageList，
 * 无消息时展示简洁的欢迎信息（EmptyChat，不含按钮）。
 * 接线 ChatInput 的 send/stop 到 chatStore。
 */
import { computed } from 'vue';
import MessageList from './MessageList.vue';
import ChatInput from './ChatInput.vue';
import EmptyChat from './EmptyChat.vue';
import { useChatStore } from '@/stores/chat';
import { useSessionsStore } from '@/stores/sessions';
import { showError } from '@/utils/message';

const chatStore = useChatStore();
const sessionsStore = useSessionsStore();

/** 是否有当前会话 */
const hasSession = computed(() => !!sessionsStore.currentId);
/** 输入框是否禁用（无会话时） */
const inputDisabled = computed(() => !hasSession.value);

/** 发送消息 */
async function handleSend(question) {
  try {
    await chatStore.sendMessage(question);
  } catch (err) {
    showError(err, '发送失败');
  }
}

/** 停止生成（FR-RAG-007） */
function handleStop() {
  chatStore.stopGenerating();
}
</script>

<template>
  <div v-loading="chatStore.loadingMessages" element-loading-text="加载消息中..." class="chat-area">
    <!-- 消息列表 / 空状态欢迎（上方区域） -->
    <div class="chat-content">
      <MessageList v-if="chatStore.hasMessages" :messages="chatStore.messages" />
      <EmptyChat v-else />
    </div>

    <!-- 输入区（始终显示在底部） -->
    <ChatInput
      :generating="chatStore.isGenerating"
      :disabled="inputDisabled"
      @send="handleSend"
      @stop="handleStop"
    />
  </div>
</template>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.chat-area {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background-color: $color-bg-page;
}

.chat-content {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
</style>
