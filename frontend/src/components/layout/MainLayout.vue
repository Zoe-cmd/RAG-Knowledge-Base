<script setup>
/**
 * 主布局容器（design-system.md 9）。
 *
 * 桌面端（≥1024px）：顶部栏 + 左侧栏（固定）+ 右侧主区
 * 平板端（<1024px）：顶部栏 + 左侧栏（抽屉，按需展开）+ 右侧主区
 *
 * 侧边栏内容通过具名插槽 sidebar 注入，避免重复渲染。
 */
import { ref, onMounted, onBeforeUnmount } from 'vue';
import AppHeader from './AppHeader.vue';

const isMobile = ref(false);
const drawerOpen = ref(false);

const MOBILE_QUERY = '(max-width: 1023px)';
let mediaQueryList = null;

function updateMobile(e) {
  isMobile.value = e.matches;
  if (!e.matches) {
    drawerOpen.value = false;
  }
}

onMounted(() => {
  mediaQueryList = window.matchMedia(MOBILE_QUERY);
  isMobile.value = mediaQueryList.matches;
  mediaQueryList.addEventListener('change', updateMobile);
});

onBeforeUnmount(() => {
  mediaQueryList?.removeEventListener('change', updateMobile);
});

function openDrawer() {
  drawerOpen.value = true;
}
</script>

<template>
  <div class="main-layout">
    <AppHeader @toggle-sidebar="openDrawer" />

    <div class="layout-body">
      <!-- 桌面端：固定侧边栏 -->
      <aside v-if="!isMobile" class="sidebar-desktop">
        <slot name="sidebar" />
      </aside>

      <!-- 平板端：抽屉式侧边栏 -->
      <el-drawer
        v-else
        v-model="drawerOpen"
        direction="ltr"
        size="280px"
        :with-header="false"
        :modal-class="'sidebar-drawer'"
      >
        <slot name="sidebar" />
      </el-drawer>

      <!-- 右侧主区 -->
      <main class="content">
        <slot />
      </main>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.main-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.layout-body {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.sidebar-desktop {
  width: $layout-sidebar-width;
  flex-shrink: 0;
  border-right: $layout-border;
  overflow: hidden;
}

.content {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>

<style lang="scss">
/* 抽屉样式（非 scoped，作用于 teleport 后的元素） */
.sidebar-drawer {
  .el-drawer__body {
    padding: 0;
  }
}
</style>
