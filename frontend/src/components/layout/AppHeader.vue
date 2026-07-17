<script setup>
/**
 * 顶部栏（design-system.md 9.1）。
 *
 * 内容：应用标题、知识库统计、Embedding Provider 切换、移动端侧边栏开关。
 */
import { computed } from 'vue';
import { ElMessageBox } from 'element-plus';
import { Menu as IconMenu, ChatDotRound, Document, Setting } from '@element-plus/icons-vue';
import { useConfigStore } from '@/stores/config';
import { useDocumentsStore } from '@/stores/documents';
import { useSessionsStore } from '@/stores/sessions';
import { EMBEDDING_PROVIDERS } from '@/utils/constants';
import { showError } from '@/utils/message';

defineEmits(['toggle-sidebar']);

const configStore = useConfigStore();
const documentsStore = useDocumentsStore();
const sessionsStore = useSessionsStore();

const stats = computed(() => configStore.statistics);
const currentProviderLabel = computed(() => {
  const provider = EMBEDDING_PROVIDERS.find((p) => p.value === configStore.currentProvider);
  return provider ? provider.label : configStore.currentProvider;
});

/** 切换 Embedding Provider（含二次确认，design-system.md 7.10）。 */
async function handleSwitchProvider(providerValue) {
  if (providerValue === configStore.currentProvider) return;

  const providerInfo = EMBEDDING_PROVIDERS.find((p) => p.value === providerValue);
  try {
    await ElMessageBox.confirm(
      `切换到「${providerInfo?.label}」方案需要重建索引，所有文档将重新向量化。是否继续？`,
      '切换 Embedding 方案',
      {
        confirmButtonText: '确认切换',
        cancelButtonText: '取消',
        type: 'warning',
      },
    );
  } catch {
    // 用户取消
    return;
  }

  try {
    const result = await configStore.switchProvider(providerValue);
    // 切换后提示需重建索引
    ElMessageBox.alert(
      `已切换到「${providerInfo?.label}」（${result.current_dimension} 维）。\n` +
        `需要重新上传文档以重建索引（共 ${result.documents_to_reindex ?? 0} 篇）。`,
      '切换成功',
      { type: 'success', confirmButtonText: '知道了' },
    );
    // 刷新文档列表（维度变化后状态可能改变）
    await documentsStore.fetchDocuments();
  } catch (err) {
    showError(err, '切换 Provider 失败');
  }
}
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <el-button
        class="sidebar-toggle"
        type="text"
        :icon="IconMenu"
        aria-label="切换侧边栏"
        @click="$emit('toggle-sidebar')"
      />
      <div class="app-title">
        <el-icon class="title-icon"><ChatDotRound /></el-icon>
        <span class="title-text">AI 文档知识库</span>
      </div>
    </div>

    <div class="header-center">
      <div class="stat-item">
        <el-icon class="stat-icon"><Document /></el-icon>
        <span class="stat-label">文档</span>
        <span class="stat-value">{{ stats.total_documents }}</span>
      </div>
      <div class="stat-divider" />
      <div class="stat-item">
        <span class="stat-label">切片</span>
        <span class="stat-value">{{ stats.total_chunks }}</span>
      </div>
      <div class="stat-divider" />
      <div class="stat-item">
        <el-icon class="stat-icon"><ChatDotRound /></el-icon>
        <span class="stat-label">会话</span>
        <span class="stat-value">{{ sessionsStore.list.length }}</span>
      </div>
    </div>

    <div class="header-right">
      <el-dropdown trigger="click" @command="handleSwitchProvider">
        <span class="provider-trigger">
          <el-icon><Setting /></el-icon>
          <span class="provider-label">{{ currentProviderLabel }}</span>
          <span class="provider-dim">{{ configStore.dimension }}维</span>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-for="p in EMBEDDING_PROVIDERS"
              :key="p.value"
              :command="p.value"
              :disabled="p.value === configStore.currentProvider"
            >
              <div class="provider-option">
                <span class="option-label">{{ p.label }}</span>
                <span class="option-desc">{{ p.desc }}</span>
              </div>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: $layout-header-height;
  padding: 0 $spacing-lg;
  background-color: #fff;
  border-bottom: $layout-border;
  z-index: $z-index-fixed;
}

.header-left {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.sidebar-toggle {
  display: none;
  font-size: 20px;
  color: $color-text-regular;
}

.app-title {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .title-icon {
    font-size: 20px;
    color: $color-primary;
  }

  .title-text {
    font-size: $font-size-large;
    font-weight: $font-weight-semibold;
    color: $color-text-primary;
  }
}

.header-center {
  display: flex;
  align-items: center;
  gap: $spacing-md;

  .stat-item {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-size: $font-size-aux;
    color: $color-text-regular;

    .stat-icon {
      font-size: 16px;
      color: $color-primary;
    }

    .stat-value {
      font-weight: $font-weight-semibold;
      color: $color-text-primary;
    }
  }

  .stat-divider {
    width: 1px;
    height: 16px;
    background-color: $color-border;
  }
}

.header-right {
  .provider-trigger {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    padding: $spacing-xs $spacing-md;
    border: 1px solid $color-border;
    border-radius: $radius-base;
    cursor: pointer;
    font-size: $font-size-aux;
    color: $color-text-regular;
    transition: all 0.2s ease;

    &:hover {
      border-color: $color-primary;
      color: $color-primary;
    }

    .provider-dim {
      color: $color-text-placeholder;
      font-size: $font-size-small;
    }
  }
}

.provider-option {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .option-label {
    font-size: $font-size-base;
    color: $color-text-primary;
  }

  .option-desc {
    font-size: $font-size-small;
    color: $color-text-placeholder;
  }
}

// 响应式：< 1024px 显示侧边栏开关，隐藏统计中间区
@media (max-width: ($breakpoint-desktop - 1px)) {
  .sidebar-toggle {
    display: inline-flex;
  }

  .header-center {
    .stat-divider:last-of-type,
    .stat-item:last-of-type {
      display: none;
    }
  }
}
</style>
