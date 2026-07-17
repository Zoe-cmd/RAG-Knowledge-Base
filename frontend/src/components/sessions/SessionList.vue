<script setup>
/**
 * 会话列表（design-system.md 7.4）。
 *
 * 展示会话列表，处理选中（加载消息）与删除（含二次确认）。
 */
import { ElMessageBox } from 'element-plus';
import SessionItem from './SessionItem.vue';
import { useSessionsStore } from '@/stores/sessions';
import { useChatStore } from '@/stores/chat';
import { showError, showSuccess } from '@/utils/message';

const sessionsStore = useSessionsStore();
const chatStore = useChatStore();

/** 选中会话并加载对应消息 */
async function handleSelect(id) {
  if (id === sessionsStore.currentId) return;
  sessionsStore.select(id);
  await chatStore.loadMessages(id);
}

/** 删除会话（含二次确认，design-system.md 7.10） */
async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确定要删除此会话吗？对话记录将无法恢复。', '确认删除', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger',
    });
  } catch {
    return; // 用户取消
  }
  try {
    const wasCurrent = sessionsStore.currentId === id;
    await sessionsStore.remove(id);
    // 删除当前会话时，加载新当前会话消息或清空
    if (wasCurrent) {
      if (sessionsStore.currentId) {
        await chatStore.loadMessages(sessionsStore.currentId);
      } else {
        chatStore.clearMessages();
      }
    }
    showSuccess('会话已删除');
  } catch (err) {
    showError(err, '删除会话失败');
  }
}
</script>

<template>
  <div v-loading="sessionsStore.loading" class="session-list">
    <el-empty
      v-if="!sessionsStore.hasSessions && !sessionsStore.loading"
      description="暂无会话"
      :image-size="56"
    />
    <SessionItem
      v-for="session in sessionsStore.list"
      :key="session.id"
      :session="session"
      :active="session.id === sessionsStore.currentId"
      @select="handleSelect"
      @delete="handleDelete"
    />
  </div>
</template>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.session-list {
  min-height: 60px;
}
</style>
