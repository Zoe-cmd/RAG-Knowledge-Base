<script setup>
/**
 * 聊天主视图。
 *
 * 组装 MainLayout + AppSidebar + ChatArea。
 * 应用启动时初始化数据：会话列表、文档列表、配置信息。
 * 若已有会话，自动选中最近一条并加载消息。
 */
import { onMounted, onBeforeUnmount } from 'vue';
import MainLayout from '@/components/layout/MainLayout.vue';
import AppSidebar from '@/components/layout/AppSidebar.vue';
import ChatArea from '@/components/chat/ChatArea.vue';
import { useSessionsStore } from '@/stores/sessions';
import { useDocumentsStore } from '@/stores/documents';
import { useChatStore } from '@/stores/chat';
import { useConfigStore } from '@/stores/config';

const sessionsStore = useSessionsStore();
const documentsStore = useDocumentsStore();
const chatStore = useChatStore();
const configStore = useConfigStore();

onMounted(async () => {
  // 并行加载初始数据（allSettled 保证单项失败不阻塞其余）
  const results = await Promise.allSettled([
    sessionsStore.fetchSessions(),
    documentsStore.fetchDocuments(),
    configStore.fetchConfig(),
  ]);

  // 会话列表加载成功且存在会话时，自动选中最近一条
  if (results[0].status === 'fulfilled' && sessionsStore.hasSessions && !sessionsStore.currentId) {
    const firstSession = sessionsStore.list[0];
    sessionsStore.select(firstSession.id);
    await chatStore.loadMessages(firstSession.id);
  }
});

onBeforeUnmount(() => {
  // 停止文档处理轮询，避免内存泄漏
  documentsStore.stopPolling();
});
</script>

<template>
  <MainLayout>
    <template #sidebar>
      <AppSidebar />
    </template>
    <ChatArea />
  </MainLayout>
</template>
