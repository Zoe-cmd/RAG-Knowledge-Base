<script setup>
/**
 * 根组件。
 *
 * 仅承载路由视图与全局消息容器。
 * 实际布局由 views/ChatView → components/layout/MainLayout 组成。
 */
import { RouterView } from 'vue-router';
</script>

<template>
  <RouterView />
</template>

<style scoped>
/* 根组件无额外样式，布局由子组件负责 */
</style>
