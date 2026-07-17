<script setup>
/**
 * 对话区空状态欢迎（design-system.md 7.9）。
 *
 * 无消息时在对话区上方展示简洁的欢迎信息。
 * 输入区始终位于下方（由 ChatArea 控制），此处不再放置按钮，
 * 避免功能冗余——用户可直接在输入框提问、在左侧栏上传文档。
 */
import { ChatLineRound } from '@element-plus/icons-vue';
</script>

<template>
  <div class="empty-chat">
    <el-empty :image-size="120" description=" ">
      <template #image>
        <el-icon class="empty-icon"><ChatLineRound /></el-icon>
      </template>
      <div class="empty-content">
        <h2 class="empty-title">AI 文档知识库</h2>
        <p class="empty-desc">上传文档，基于 RAG 检索增强生成，让 AI 基于你的文档回答问题</p>
      </div>
    </el-empty>
  </div>
</template>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.empty-chat {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: $spacing-2xl;

  .empty-icon {
    font-size: 96px;
    color: $color-primary-light-9;
  }

  .empty-content {
    text-align: center;
  }

  .empty-title {
    margin: 0 0 $spacing-sm;
    font-size: 22px;
    font-weight: $font-weight-semibold;
    color: $color-text-primary;
  }

  .empty-desc {
    margin: 0;
    font-size: $font-size-base;
    color: $color-text-regular;
  }
}
</style>
