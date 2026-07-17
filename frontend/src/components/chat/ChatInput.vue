<script setup>
/**
 * 聊天输入区（design-system.md 7.2 / 9.1）。
 *
 * textarea 自动扩展，回车发送、Shift+回车换行。
 * 生成中显示"停止生成"按钮，支持中断（FR-RAG-007）。
 */
import { ref, computed } from 'vue';
import { Promotion, VideoPause } from '@element-plus/icons-vue';
import { QUESTION_MAX_LENGTH } from '@/utils/constants';

const props = defineProps({
  /** 是否正在生成 */
  generating: { type: Boolean, default: false },
  /** 是否禁用（如未选择会话） */
  disabled: { type: Boolean, default: false },
});

const emit = defineEmits(['send', 'stop']);

const input = ref('');
const inputRef = ref(null);

const canSend = computed(() => input.value.trim().length > 0 && !props.disabled && !props.generating);
const overLimit = computed(() => input.value.length > QUESTION_MAX_LENGTH);

/** 发送消息。 */
function handleSend() {
  if (!canSend.value || overLimit.value) return;
  const question = input.value.trim();
  emit('send', question);
  input.value = '';
}

/** 回车发送，Shift+回车换行。 */
function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    handleSend();
  }
}

/** 停止生成。 */
function handleStop() {
  emit('stop');
}

defineExpose({ focus: () => inputRef.value?.focus() });
</script>

<template>
  <div class="chat-input">
    <div class="input-wrapper">
      <el-input
        ref="inputRef"
        v-model="input"
        type="textarea"
        :rows="1"
        :autosize="{ minRows: 1, maxRows: 6 }"
        :maxlength="QUESTION_MAX_LENGTH + 100"
        :show-word-limit="false"
        :placeholder="disabled ? '请先新建或选择会话' : '输入问题，基于知识库回答（Enter 发送，Shift+Enter 换行）'"
        :disabled="disabled"
        resize="none"
        @keydown="handleKeydown"
      />
      <div v-if="overLimit" class="input-warning">
        问题不能超过 {{ QUESTION_MAX_LENGTH }} 字符
      </div>
    </div>

    <div class="input-actions">
      <span v-if="input.length > 0" class="char-count" :class="{ over: overLimit }">
        {{ input.length }}/{{ QUESTION_MAX_LENGTH }}
      </span>
      <el-button
        v-if="!generating"
        type="primary"
        :icon="Promotion"
        :disabled="!canSend || overLimit"
        size="large"
        class="send-btn"
        @click="handleSend"
      >
        发送
      </el-button>
      <el-button
        v-else
        type="danger"
        :icon="VideoPause"
        size="large"
        class="stop-btn"
        @click="handleStop"
      >
        停止生成
      </el-button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.chat-input {
  display: flex;
  align-items: flex-end;
  gap: $spacing-sm;
  padding: $spacing-base $spacing-lg;
  background-color: #fff;
  border-top: $layout-border;
}

.input-wrapper {
  flex: 1;
  min-width: 0;
  position: relative;

  :deep(.el-textarea__inner) {
    min-height: 40px !important;
    max-height: 160px;
    padding: $spacing-sm $spacing-md;
    font-size: $font-size-chat;
    line-height: $line-height-chat;
    border-radius: $radius-round;
    box-shadow: none;

    &:focus {
      box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
    }
  }
}

.input-warning {
  position: absolute;
  bottom: -20px;
  left: 0;
  font-size: $font-size-small;
  color: $color-danger;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  flex-shrink: 0;
  padding-bottom: $spacing-xs;
}

.char-count {
  font-size: $font-size-small;
  color: $color-text-placeholder;

  &.over {
    color: $color-danger;
  }
}

.send-btn,
.stop-btn {
  height: 40px;
  min-width: 96px;
}

.send-btn {
  box-shadow: $shadow-primary;

  &:hover {
    box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
  }
}
</style>
