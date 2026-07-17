<script setup>
/**
 * 文档处理状态标签。
 *
 * 基于 el-tag，按 status 映射类型与文案（design-system.md 7.7）。
 */
import { computed } from 'vue';
import { STATUS_TAG_MAP } from '@/utils/constants';

const props = defineProps({
  /** 文档状态：pending/processing/completed/failed */
  status: { type: String, default: 'pending' },
});

const tagInfo = computed(() => STATUS_TAG_MAP[props.status] || STATUS_TAG_MAP.pending);
</script>

<template>
  <el-tag :type="tagInfo.type" size="small" effect="light" round>
    {{ tagInfo.label }}
  </el-tag>
</template>

<style scoped>
/* 失败状态可悬停查看详情，鼠标提示 */
:deep(.el-tag--danger) {
  cursor: help;
}
</style>
