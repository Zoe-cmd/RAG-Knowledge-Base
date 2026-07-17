<script setup>
/**
 * 左侧栏（design-system.md 9.1）。
 *
 * 上半：会话列表（含新建会话、清空会话）
 * 下半：文档列表（含上传文档）
 */
import { Plus, Delete, UploadFilled } from '@element-plus/icons-vue';
import { ElMessageBox } from 'element-plus';
import SessionList from '@/components/sessions/SessionList.vue';
import DocumentList from '@/components/documents/DocumentList.vue';
import UploadDialog from '@/components/documents/UploadDialog.vue';
import { useSessionsStore } from '@/stores/sessions';
import { useChatStore } from '@/stores/chat';
import { useUploadDialog } from '@/composables/useUploadDialog';
import { showError, showSuccess } from '@/utils/message';

const sessionsStore = useSessionsStore();
const chatStore = useChatStore();

// 上传弹窗共享状态（对话区空状态、文档列表空状态均可触发）
const { visible: uploadVisible, open: openUploadDialog } = useUploadDialog();

/** 新建会话。 */
async function handleNewSession() {
  try {
    chatStore.clearMessages();
    await sessionsStore.create();
    // 新会话消息为空，无需加载
    chatStore.messages = [];
  } catch (err) {
    showError(err, '新建会话失败');
  }
}

/** 清空所有会话（含二次确认，design-system.md 7.10）。 */
async function handleClearAll() {
  try {
    await ElMessageBox.confirm('确定要清空所有会话吗？此操作不可恢复。', '确认清空', {
      confirmButtonText: '确认清空',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger',
    });
  } catch {
    return;
  }
  try {
    const count = await sessionsStore.clearAll();
    chatStore.clearMessages();
    showSuccess(`已清空 ${count} 个会话`);
  } catch (err) {
    showError(err, '清空会话失败');
  }
}

/** 打开上传弹窗。 */
function handleUpload() {
  openUploadDialog();
}
</script>

<template>
  <nav class="app-sidebar" aria-label="侧边导航">
    <!-- 会话列表区 -->
    <section class="sidebar-section sessions-section">
      <div class="section-header">
        <span class="section-title">会话历史</span>
        <div class="section-actions">
          <el-button
            type="danger"
            text
            size="small"
            :icon="Delete"
            :disabled="!sessionsStore.hasSessions"
            aria-label="清空会话"
            @click="handleClearAll"
          />
        </div>
      </div>
      <div class="new-session-btn">
        <el-button type="primary" :icon="Plus" class="full-btn" @click="handleNewSession">
          新建会话
        </el-button>
      </div>
      <div class="section-body">
        <SessionList />
      </div>
    </section>

    <div class="sidebar-divider" />

    <!-- 文档列表区 -->
    <section class="sidebar-section documents-section">
      <div class="section-header">
        <span class="section-title">知识库文档</span>
        <el-button
          type="primary"
          text
          size="small"
          :icon="UploadFilled"
          aria-label="上传文档"
          @click="handleUpload"
        >
          上传
        </el-button>
      </div>
      <div class="section-body">
        <DocumentList @upload="handleUpload" />
      </div>
    </section>

    <!-- 上传弹窗 -->
    <UploadDialog v-model="uploadVisible" />
  </nav>
</template>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.app-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #fff;
}

.sidebar-section {
  display: flex;
  flex-direction: column;
  min-height: 0; // 允许子元素滚动
}

.sessions-section {
  flex: 0 0 auto;
  min-height: $layout-sidebar-min-height;
  max-height: 55%;
}

.documents-section {
  flex: 1 1 auto;
  min-height: 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md $spacing-base $spacing-sm;
  flex-shrink: 0;

  .section-title {
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    color: $color-text-primary;
  }
}

.new-session-btn {
  padding: 0 $spacing-base $spacing-sm;
  flex-shrink: 0;

  .full-btn {
    width: 100%;
  }
}

.section-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: 0 $spacing-sm;
}

.sidebar-divider {
  height: 1px;
  background-color: $color-border;
  flex-shrink: 0;
}
</style>
