<template>
  <div class="main-layout">
    <AppSidebar v-model:collapsed="collapsed" />

    <main class="layout-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AppSidebar from './AppSidebar.vue'
import { useLlmStore } from '@/stores/llm'

const collapsed = ref(false)

onMounted(() => {
  useLlmStore().fetchModels()
})
</script>

<style lang="scss" scoped>
.main-layout {
  width: 100%;
  height: 100%;
  display: flex;
}

.layout-content {
  flex: 1;
  min-width: 0;
  background: var(--app-bg);
  overflow-y: auto;
  padding: clamp(16px, 2vw, 28px);

  > :deep(*) {
    width: min(100%, var(--app-content-max));
    margin-inline: auto;
  }
}
</style>
