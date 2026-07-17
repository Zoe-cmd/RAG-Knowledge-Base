<script setup>
/**
 * 文档列表项（design-system.md 7.5）。
 *
 * 纯展示组件：文件类型图标、文件名、大小、状态标签、切片数。
 * 失败时展示错误信息（tooltip），悬停显示删除按钮。
 */
import { computed } from 'vue';
import { Delete, Document, WarningFilled } from '@element-plus/icons-vue';
import StatusTag from '@/components/common/StatusTag.vue';
import { FILE_TYPE_COLOR, FILE_TYPE_LABEL, DOCUMENT_STATUS } from '@/utils/constants';
import { formatFileSize } from '@/utils/format';

const props = defineProps({
  /** 文档对象 */
  document: { type: Object, required: true },
});

defineEmits(['delete']);

/** 文件类型（小写扩展名） */
const fileType = computed(() => props.document.file_type || 'txt');
/** 图标颜色（按文件类型） */
const iconColor = computed(() => FILE_TYPE_COLOR[fileType.value] || '#909399');
/** 类型中文标签 */
const typeLabel = computed(() => FILE_TYPE_LABEL[fileType.value] || 'TXT');
/** 文件大小 */
const sizeText = computed(() => formatFileSize(props.document.file_size));
/** 是否处理完成 */
const isCompleted = computed(() => props.document.status === DOCUMENT_STATUS.COMPLETED);
/** 是否处理失败 */
const isFailed = computed(() => props.document.status === DOCUMENT_STATUS.FAILED);
/** 错误信息 */
const errorMessage = computed(() => props.document.error_message || '处理失败');
</script>

<template>
  <div class="document-item" :class="{ failed: isFailed }">
    <div class="doc-icon" :style="{ color: iconColor }">
      <el-icon :size="20"><Document /></el-icon>
    </div>
    <div class="doc-info">
      <div class="doc-name" :title="document.filename">{{ document.filename }}</div>
      <div class="doc-meta">
        <span class="doc-type">{{ typeLabel }}</span>
        <span class="dot">·</span>
        <span>{{ sizeText }}</span>
        <template v-if="isCompleted && document.chunk_count > 0">
          <span class="dot">·</span>
          <span>{{ document.chunk_count }} 切片</span>
        </template>
      </div>
      <div v-if="isFailed" class="doc-error" :title="errorMessage">
        <el-icon><WarningFilled /></el-icon>
        <span>{{ errorMessage }}</span>
      </div>
    </div>
    <div class="doc-status">
      <StatusTag :status="document.status" />
    </div>
    <el-button
      class="delete-btn"
      type="danger"
      text
      size="small"
      :icon="Delete"
      aria-label="删除文档"
      @click.stop="$emit('delete', document.id)"
    />
  </div>
</template>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.document-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  border-radius: $radius-base;
  transition: background-color 0.15s;

  &:hover {
    background-color: $color-bg-card;

    .delete-btn {
      opacity: 1;
    }
  }
}

.doc-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: $radius-base;
  background-color: $color-bg-card;
}

.doc-info {
  flex: 1 1 auto;
  min-width: 0;
}

.doc-name {
  font-size: $font-size-base;
  color: $color-text-primary;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: $line-height-base;
}

.doc-meta {
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

.doc-error {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
  font-size: $font-size-small;
  color: $color-danger;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-status {
  flex-shrink: 0;
}

.delete-btn {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s;
}
</style>
