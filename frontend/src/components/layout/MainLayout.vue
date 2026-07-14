<template>
  <div class="main-layout">
    <!-- Sidebar spans full height -->
    <AppSidebar v-model:collapsed="collapsed" />

    <!-- Right area: content header + page -->
    <div class="layout-right">
      <header class="content-header">
        <button class="toggle-btn" :title="collapsed ? '展开侧栏' : '收起侧栏'" @click="collapsed = !collapsed">
          <el-icon><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
        </button>
      </header>

      <main class="layout-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Fold, Expand } from '@element-plus/icons-vue'
import AppSidebar from './AppSidebar.vue'

const collapsed = ref(false)
</script>

<style lang="scss" scoped>
.main-layout {
  width: 100%;
  height: 100%;
  display: flex;
}

.layout-right {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.content-header {
  height: $header-height;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  padding: 0 16px;
  box-shadow: $shadow-sm;
  flex-shrink: 0;
}

.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #737373;
  cursor: pointer;
  font-size: 18px;
  transition: all 0.15s;

  &:hover {
    color: #171717;
    background: #f1f1f0;
  }
}

.layout-content {
  flex: 1;
  background: $bg-color;
  overflow-y: auto;
  padding: $spacing-lg;
}
</style>
