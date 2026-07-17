<script setup>
/**
 * 消息列表（design-system.md 7.1）。
 *
 * 可滚动消息容器，支持流式自动滚动与"回到底部"悬浮按钮。
 * 用户上滑阅读历史时，不强制打断滚动（仅在贴近底部时自动跟随）。
 */
import { ref, watch, onMounted, onBeforeUnmount } from 'vue';
import { ArrowDownBold } from '@element-plus/icons-vue';
import MessageBubble from './MessageBubble.vue';

const props = defineProps({
  /** 消息列表 */
  messages: { type: Array, required: true },
});

const scrollRef = ref(null);
/** 是否贴近底部（用于判断是否自动跟随滚动） */
const isAtBottom = ref(true);
/** 程序化滚动标志：非 null 时忽略 @scroll 事件，防止流式新内容到达时误判 isAtBottom */
let _autoScrollTimer = null;

/** 距底阈值（px），小于此值视为"在底部" */
const BOTTOM_THRESHOLD = 80;

/** 检查当前滚动位置是否贴近底部 */
function checkAtBottom() {
  const el = scrollRef.value;
  if (!el) return;
  isAtBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < BOTTOM_THRESHOLD;
}

/** 滚动到底部 */
function scrollToBottom(smooth = false) {
  const el = scrollRef.value;
  if (!el) return;
  el.scrollTo({
    top: el.scrollHeight,
    behavior: smooth ? 'smooth' : 'auto',
  });
  isAtBottom.value = true;
  // 程序化滚动后短暂忽略 scroll 事件，防止流式 token 到达导致 scrollHeight 增大时误判
  clearTimeout(_autoScrollTimer);
  _autoScrollTimer = setTimeout(() => { _autoScrollTimer = null; }, 120);
}

/** 滚动事件（用户手动滚动时更新 isAtBottom） */
function handleScroll() {
  // 程序化滚动触发的事件不更新 isAtBottom
  if (_autoScrollTimer) return;
  checkAtBottom();
}

/** 点击"回到底部"悬浮按钮 */
function handleBackToBottom() {
  scrollToBottom(true);
}

// 新增消息时自动滚动（仅在用户已在底部时）
watch(
  () => props.messages.length,
  () => {
    if (isAtBottom.value) {
      scrollToBottom();
    }
  },
  { flush: 'post' },
);

// 流式 token 更新时自动滚动（仅在用户已在底部时）
// flush: 'post' 确保 DOM 更新完成后再滚动，scrollHeight 已反映新内容
watch(
  () => {
    const last = props.messages[props.messages.length - 1];
    return last ? last.content : '';
  },
  () => {
    if (isAtBottom.value) {
      scrollToBottom();
    }
  },
  { flush: 'post' },
);

onMounted(() => {
  scrollToBottom();
});

onBeforeUnmount(() => {
  clearTimeout(_autoScrollTimer);
});
</script>

<template>
  <div class="message-list-wrapper">
    <div ref="scrollRef" class="message-list" @scroll="handleScroll">
      <div class="message-list-inner">
        <MessageBubble
          v-for="msg in messages"
          :key="msg.id"
          :message="msg"
        />
      </div>
    </div>

    <!-- 回到底部悬浮按钮 -->
    <transition name="fade">
      <button
        v-show="!isAtBottom"
        class="back-to-bottom"
        type="button"
        aria-label="回到底部"
        @click="handleBackToBottom"
      >
        <el-icon><ArrowDownBold /></el-icon>
      </button>
    </transition>
  </div>
</template>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.message-list-wrapper {
  position: relative;
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.message-list {
  height: 100%;
  overflow-y: auto;
  scroll-behavior: auto;
}

.message-list-inner {
  max-width: 860px;
  margin: 0 auto;
  padding: $spacing-lg $spacing-base $spacing-xl;
}

.back-to-bottom {
  position: absolute;
  right: $spacing-lg;
  bottom: $spacing-lg;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: $layout-border;
  background-color: #fff;
  box-shadow: $shadow-medium;
  color: $color-text-regular;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  z-index: $z-index-content;
  transition: color 0.2s, box-shadow 0.2s;

  &:hover {
    color: $color-primary;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.16);
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
