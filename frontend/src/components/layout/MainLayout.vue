<template>
  <div class="main-layout">
    <AppSidebar v-model:collapsed="collapsed" />

    <main :class="['layout-content', { 'layout-content--chat': route.name === 'Chat' }]">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from './AppSidebar.vue'
import { useLlmStore } from '@/stores/llm'

const collapsed = ref(false)
const route = useRoute()

onMounted(() => {
  document.documentElement.classList.add('app-shell-active')
  document.body.classList.add('app-shell-active')
  useLlmStore().fetchModels()
})

onUnmounted(() => {
  document.documentElement.classList.remove('app-shell-active')
  document.body.classList.remove('app-shell-active')
})
</script>

<style lang="scss" scoped>
.main-layout {
  position: fixed;
  inset: 0;
  width: 100%;
  height: auto;
  display: flex;
  align-items: flex-start;
}

.layout-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
  background: var(--app-bg);
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  padding: clamp(16px, 2vw, 28px);

  &.layout-content--chat {
    overflow: hidden;
    padding-bottom: 0;
  }

  > :deep(*) {
    width: min(100%, var(--app-content-max));
    margin-inline: auto;
  }
}

:global(html.app-shell-active),
:global(body.app-shell-active),
:global(body.app-shell-active #app) {
  width: 100%;
  height: 100%;
  overflow: hidden;
}
</style>
