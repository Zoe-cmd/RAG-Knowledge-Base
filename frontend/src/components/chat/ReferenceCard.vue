<script setup>
/**
 * 引用来源卡片（design-system.md 7.4）。
 *
 * 默认折叠（显示前 2 条），点击"查看全部"展开。
 * 每条引用含：文档名（主色）、片段预览（2 行截断）、来源路径、相似度。
 */
import { ref, computed } from 'vue';
import { Link, ArrowDown, ArrowUp } from '@element-plus/icons-vue';

const props = defineProps({
  /** 引用来源数组 */
  references: { type: Array, default: () => [] },
  /** 是否为空引用（未找到相关内容） */
  empty: { type: Boolean, default: false },
});

const COLLAPSE_THRESHOLD = 2;
const expanded = ref(false);

const displayReferences = computed(() =>
  expanded.value ? props.references : props.references.slice(0, COLLAPSE_THRESHOLD),
);

const hasMore = computed(() => props.references.length > COLLAPSE_THRESHOLD);
</script>

<template>
  <div v-if="empty" class="reference-card empty-reference">
    <el-icon class="ref-icon"><Link /></el-icon>
    <span class="empty-text">未在文档库中找到相关内容</span>
  </div>

  <div v-else-if="references.length > 0" class="reference-card">
    <div class="reference-header">
      <el-icon class="ref-icon"><Link /></el-icon>
      <span class="ref-title">引用来源（{{ references.length }}）</span>
    </div>

    <div class="reference-list">
      <div v-for="(item, index) in displayReferences" :key="index" class="reference-item">
        <div class="ref-item-header">
          <span class="ref-doc-name text-ellipsis" :title="item.doc_name">{{ item.doc_name }}</span>
          <el-tag size="small" type="info" effect="plain" class="ref-similarity">
            {{ (item.similarity * 100).toFixed(0) }}%
          </el-tag>
        </div>
        <p class="ref-chunk text-ellipsis-2">{{ item.chunk || item.preview }}</p>
        <div class="ref-meta">
          <span class="ref-path text-ellipsis">片段 #{{ item.chunk_index + 1 }}<template v-if="item.source_path"> · {{ item.source_path }}</template></span>
        </div>
      </div>

      <button v-if="hasMore" type="button" class="expand-btn" @click="expanded = !expanded">
        <el-icon>
          <ArrowUp v-if="expanded" />
          <ArrowDown v-else />
        </el-icon>
        <span>{{ expanded ? '收起' : `查看全部 ${references.length} 条` }}</span>
      </button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.reference-card {
  background-color: $color-reference-card;
  border: 1px solid $color-border;
  border-radius: $radius-base;
  padding: $spacing-md;
  margin-bottom: $spacing-sm;
}

.reference-header {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  margin-bottom: $spacing-sm;

  .ref-icon {
    font-size: 14px;
    color: $color-primary;
  }

  .ref-title {
    font-size: $font-size-small;
    font-weight: $font-weight-medium;
    color: $color-text-regular;
  }
}

.reference-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.reference-item {
  background-color: #fff;
  border-radius: $radius-small;
  padding: $spacing-sm $spacing-md;
}

.ref-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-sm;
  margin-bottom: $spacing-xs;

  .ref-doc-name {
    font-size: $font-size-aux;
    font-weight: $font-weight-medium;
    color: $color-primary;
    flex: 1;
    min-width: 0;
  }
}

.ref-chunk {
  margin: 0;
  font-size: $font-size-small;
  line-height: $line-height-code;
  color: $color-text-regular;
}

.ref-meta {
  margin-top: $spacing-xs;

  .ref-path {
    font-size: 11px;
    color: $color-text-placeholder;
  }
}

.expand-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: $spacing-xs;
  width: 100%;
  margin-top: $spacing-sm;
  padding: $spacing-xs;
  border: none;
  background: transparent;
  color: $color-primary;
  font-size: $font-size-small;
  cursor: pointer;
  border-radius: $radius-small;
  transition: background-color 0.2s ease;

  &:hover {
    background-color: $color-primary-light-9;
  }
}

.empty-reference {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .empty-text {
    font-size: $font-size-aux;
    color: $color-warning;
  }

  .ref-icon {
    color: $color-warning;
  }
}
</style>
