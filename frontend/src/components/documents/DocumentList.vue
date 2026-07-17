<script setup>
/**
 * 文档列表（design-system.md 7.5）。
 *
 * 展示文档列表，处理删除（含二次确认），空状态引导上传。
 */
import { ElMessageBox } from 'element-plus';
import { Upload } from '@element-plus/icons-vue';
import DocumentItem from './DocumentItem.vue';
import { useDocumentsStore } from '@/stores/documents';
import { showError, showSuccess } from '@/utils/message';

const documentsStore = useDocumentsStore();

const emit = defineEmits(['upload']);

/** 删除文档（含二次确认，design-system.md 7.10） */
async function handleDelete(id) {
  try {
    await ElMessageBox.confirm(
      '删除后文档及其向量数据将无法恢复，确定删除？',
      '确认删除',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
      },
    );
  } catch {
    return; // 用户取消
  }
  try {
    await documentsStore.remove(id);
    showSuccess('文档已删除');
  } catch (err) {
    showError(err, '删除文档失败');
  }
}
</script>

<template>
  <div v-loading="documentsStore.loading" class="document-list">
    <el-empty
      v-if="!documentsStore.hasDocuments && !documentsStore.loading"
      description="暂无文档"
      :image-size="56"
    >
      <el-button type="primary" :icon="Upload" size="small" @click="emit('upload')">
        上传文档
      </el-button>
    </el-empty>
    <DocumentItem
      v-for="doc in documentsStore.list"
      :key="doc.id"
      :document="doc"
      @delete="handleDelete"
    />
  </div>
</template>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.document-list {
  min-height: 60px;
}
</style>
