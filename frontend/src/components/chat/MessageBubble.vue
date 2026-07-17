<script setup>
/**
 * 消息气泡（design-system.md 7.3）。
 *
 * 用户消息：右对齐，主色浅底气泡，纯文本（自动转义，保留换行）
 * AI 回答：左对齐，白色气泡，Markdown 渲染（DOMPurify 净化），
 *          支持流式光标、引用来源、耗时显示、错误/中断状态。
 */
import { computed } from 'vue';
import { Loading, CircleClose, WarningFilled } from '@element-plus/icons-vue';
import { MESSAGE_ROLE } from '@/utils/constants';
import { renderMarkdown } from '@/utils/markdown';
import { formatElapsed, formatDateTime } from '@/utils/format';
import ReferenceCard from './ReferenceCard.vue';

const props = defineProps({
  /** 消息对象 */
  message: { type: Object, required: true },
});

const isUser = computed(() => props.message.role === MESSAGE_ROLE.USER);
const isAssistant = computed(() => props.message.role === MESSAGE_ROLE.ASSISTANT);

/** AI 回答的 Markdown 渲染 HTML（已净化） */
const htmlContent = computed(() => {
  if (!isAssistant.value) return '';
  return renderMarkdown(props.message.content || '');
});

/** 是否展示"正在生成"占位（流式中且尚无内容） */
const isWaiting = computed(
  () => isAssistant.value && props.message.streaming && !props.message.content,
);

/** 引用来源（null 表示无引用字段，如用户消息） */
const references = computed(() => props.message.references || []);
const hasReferences = computed(() => references.value.length > 0);
const isEmptyReferences = computed(
  () => Array.isArray(props.message.references) && references.value.length === 0 && !props.message.streaming,
);
</script>

<template>
  <div class="message-row" :class="{ 'is-user': isUser, 'is-assistant': isAssistant }">
    <!-- AI 头像 -->
    <div v-if="isAssistant" class="avatar">
      <span class="avatar-text">AI</span>
    </div>

    <div class="message-content">
      <!-- 引用来源卡片（AI 回答） -->
      <ReferenceCard
        v-if="isAssistant && hasReferences"
        :references="references"
      />
      <ReferenceCard
        v-else-if="isAssistant && isEmptyReferences"
        :references="[]"
        empty
      />

      <!-- 气泡 -->
      <div class="bubble" :class="{ 'user-bubble': isUser, 'ai-bubble': isAssistant }">
        <!-- 等待首个 token -->
        <div v-if="isWaiting" class="waiting">
          <el-icon class="loading-icon"><Loading /></el-icon>
          <span>正在检索文档并生成回答</span>
          <span class="streaming-cursor" />
        </div>

        <!-- 用户消息：纯文本 -->
        <div v-else-if="isUser" class="user-text">{{ message.content }}</div>

        <!-- AI 回答：Markdown 渲染（已通过 DOMPurify 净化，防止 XSS） -->
        <div v-else class="markdown-body">
          <!-- 流式生成中显示纯文本（避免每次 token 都重新渲染 Markdown 导致卡顿） -->
          <span v-if="message.streaming">{{ message.content }}</span>
          <!-- 流式结束后渲染完整 Markdown -->
          <!-- eslint-disable-next-line vue/no-v-html -->
          <span v-else v-html="htmlContent" />
          <span v-if="message.streaming && message.content" class="streaming-cursor" />
        </div>
      </div>

      <!-- AI 回答元信息 -->
      <div v-if="isAssistant && !message.streaming" class="message-meta">
        <span v-if="message.elapsed_ms != null" class="meta-item">
          耗时 {{ formatElapsed(message.elapsed_ms) }}
        </span>
        <span class="meta-item">{{ formatDateTime(message.created_at, 'HH:MI') }}</span>
        <span v-if="message.aborted" class="meta-item aborted">
          <el-icon><WarningFilled /></el-icon> 已停止
        </span>
        <span v-if="message.error" class="meta-item error">
          <el-icon><CircleClose /></el-icon> 生成失败
        </span>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.message-row {
  display: flex;
  gap: $spacing-sm;
  margin-bottom: $spacing-base;

  &.is-user {
    flex-direction: row-reverse;
  }
}

.avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: $color-primary;
  display: flex;
  align-items: center;
  justify-content: center;

  .avatar-text {
    color: #fff;
    font-size: $font-size-small;
    font-weight: $font-weight-semibold;
  }
}

.message-content {
  display: flex;
  flex-direction: column;
  max-width: 80%;
  min-width: 0;

  .is-user & {
    align-items: flex-end;
  }

  .is-assistant & {
    align-items: flex-start;
    max-width: 80%;
  }
}

.bubble {
  padding: $spacing-md $spacing-base;
  border-radius: $radius-round;
  font-size: $font-size-chat;
  line-height: $line-height-chat;
  word-break: break-word;

  &.user-bubble {
    background-color: $color-user-bubble;
    color: $color-text-primary;
    border-top-right-radius: $radius-small;
  }

  &.ai-bubble {
    background-color: $color-ai-bubble;
    color: $color-text-primary;
    border: 1px solid $color-border;
    border-top-left-radius: $radius-small;
  }
}

.user-text {
  white-space: pre-wrap;
}

.waiting {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  color: $color-text-regular;
  font-size: $font-size-aux;

  .loading-icon {
    animation: rotate 1.2s linear infinite;
    color: $color-primary;
  }
}

@keyframes rotate {
  to {
    transform: rotate(360deg);
  }
}

.message-meta {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-top: $spacing-xs;
  padding: 0 $spacing-xs;
  font-size: $font-size-small;
  color: $color-text-placeholder;

  .meta-item {
    display: inline-flex;
    align-items: center;
    gap: 2px;
  }

  .aborted {
    color: $color-warning;
  }

  .error {
    color: $color-danger;
  }
}
</style>
