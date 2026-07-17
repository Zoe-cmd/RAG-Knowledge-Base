<script setup>
/**
 * 会话列表项（design-system.md 7.4）。
 *
 * 纯展示组件：展示会话标题、消息数、最后活跃时间。
 * 点击选中，悬停显示删除按钮。
 */
import { computed } from 'vue';
import { ChatDotRound, Delete } from '@element-plus/icons-vue';
import { formatRelativeTime } from '@/utils/format';

const props = defineProps({
  /** 会话对象 */
  session: { type: Object, required: true },
  /** 是否为当前选中会话 */
  active: { type: Boolean, default: false },
});

defineEmits(['select', 'delete']);

/** 会话标题（无标题时显示"新会话"） */
const title = computed(() => props.session.title || '新会话');
/** 相对时间（优先最后消息时间） */
const timeText = computed(() =>
  formatRelativeTime(props.session.last_message_at || props.session.created_at),
);
/** 消息数 */
const messageCount = computed(() => props.session.message_count || 0);
</script>

<template>
  <div
    class="session-item"
    :class="{ active }"
    role="button"
    tabindex="0"
    :aria-current="active ? 'true' : undefined"
    @click="$emit('select', session.id)"
    @keydown.enter="$emit('select', session.id)"
  >
    <el-icon class="session-icon"><ChatDotRound /></el-icon>
    <div class="session-info">
      <div class="session-title" :title="title">{{ title }}</div>
      <div class="session-meta">
        <span>{{ messageCount }} 条消息</span>
        <span class="dot">·</span>
        <span>{{ timeText }}</span>
      </div>
    </div>
    <el-button
      class="delete-btn"
      type="danger"
      text
      size="small"
      :icon="Delete"
      aria-label="删除会话"
      @click.stop="$emit('delete', session.id)"
    />
  </div>
</template>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.session-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  border-radius: $radius-base;
  cursor: pointer;
  transition: background-color 0.15s;
  outline: none;

  &:hover,
  &:focus-visible {
    background-color: $color-bg-card;

    .delete-btn {
      opacity: 1;
    }
  }

  &.active {
    background-color: $color-primary-light-9;

    .session-title {
      color: $color-primary;
      font-weight: $font-weight-medium;
    }
  }
}

.session-icon {
  flex-shrink: 0;
  font-size: 16px;
  color: $color-text-placeholder;
}

.session-info {
  flex: 1 1 auto;
  min-width: 0;
}

.session-title {
  font-size: $font-size-base;
  color: $color-text-primary;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: $line-height-base;
}

.session-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
  font-size: $font-size-small;
  color: $color-text-placeholder;

  .dot {
    color: $color-border-hover;
  }
}

.delete-btn {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s;
}
</style>
