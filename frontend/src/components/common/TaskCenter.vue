<template>
  <div class="task-center">
    <el-badge :value="activeTasks.length || undefined" :hidden="!activeTasks.length" type="warning"><el-button circle :icon="List" aria-label="任务中心" @click="visible = true" /></el-badge>
    <el-drawer v-model="visible" title="任务中心" size="min(420px, 92vw)">
      <div class="toolbar"><span>从服务端恢复训练与检测任务</span><button class="period-trigger refresh-btn" :disabled="loading" @click="refresh"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" :class="{ spin: loading }"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg><span class="period-val">刷新</span></button></div>
      <el-empty v-if="!allTasks.length && !loading" description="暂无可恢复的任务" />
      <PageErrorAlert v-if="error" :message="error" retry-text="重试" @retry="refresh" />
      <div v-else class="list" v-loading="loading">
        <article v-for="task in allTasks" :key="`${task.kind}-${task.id}`" class="item">
          <div class="row"><strong>{{ task.task_uuid || `${task.kind === 'training' ? '训练' : '检测'}任务 #${task.id}` }}</strong><StatusTag :status="task.status" :label="statusText(task.status)" size="small" /></div>
          <p>{{ task.kind === 'training' ? `${task.model_name || '-'} · ${task.dataset_name || task.dataset_path || '-'}` : `${task.taskType || 'detection'} · ${task.sceneName || '-'}` }}</p>
          <el-progress :percentage="progress(task.progress)" :status="task.status === 'failed' ? 'exception' : task.status === 'completed' ? 'success' : undefined" :stroke-width="8" />
          <el-alert v-if="task.error_message" :title="task.error_message" type="error" :closable="false" show-icon />
          <div class="actions"><el-button link type="primary" @click="openTask(task)">{{ task.status === 'completed' ? '查看结果' : '查看监控' }}</el-button></div>
        </article>
      </div>
    </el-drawer>
  </div>
</template>
<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { List } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import StatusTag from '@/components/common/StatusTag.vue'
import PageErrorAlert from '@/components/common/PageErrorAlert.vue'
import { useTaskStore } from '@/stores/tasks'
const visible = ref(false); const router = useRouter(); const taskStore = useTaskStore(); const { trainingTasks, loadingTrainingTasks, detectionTasks, loadingDetectionTasks } = storeToRefs(taskStore)
const allTasks = computed(() => [...trainingTasks.value.map((task) => ({ ...task, kind: 'training' })), ...detectionTasks.value.map((task) => ({ ...task, kind: 'detection', progress: task.status === 'completed' ? 100 : (task.progress || 0), error_message: task.errorMessage }))])
const loading = computed(() => loadingTrainingTasks.value || loadingDetectionTasks.value)
const error = ref('')
const activeTasks = computed(() => allTasks.value.filter((task) => ['pending', 'running', 'processing'].includes(task.status)))
let timer = null
const progress = (value) => Math.min(100, Math.max(0, Number(value) || 0))
const statusText = (status) => ({ pending: '等待中', running: '训练中', processing: '处理中', completed: '已完成', failed: '失败', cancelled: '已取消' })[status] || status || '-'
async function refresh() {
  error.value = ''
  try { await Promise.all([taskStore.fetchTrainingTasks(), taskStore.fetchDetectionTasks()]) }
  catch (err) { error.value = err?.response?.data?.detail || err?.message || '任务中心加载失败' }
}
async function openTask(task) { visible.value = false; if (task.kind === 'training') { taskStore.selectTrainingTask(task.id); await router.push('/training'); return } await router.push(task.taskType === 'video' ? { path: '/detection', query: { videoTask: task.id } } : { path: '/history', query: { task: task.id } }) }
onMounted(async () => { await refresh(); timer = window.setInterval(() => { if (activeTasks.value.length) refresh() }, 5000) })
onBeforeUnmount(() => { if (timer) window.clearInterval(timer) })
</script>
<style lang="scss" scoped>.task-center{position:fixed;z-index:20;right:28px;bottom:28px}.task-center :deep(.el-badge .el-button){width:auto;min-width:46px;padding:10px 14px;border-radius:999px}.task-center :deep(.el-badge .el-button)::after{content:'任务中心';margin-left:6px}.toolbar,.row,.actions{display:flex;align-items:center;justify-content:space-between;gap:8px}.toolbar{margin-bottom:14px;color:$text-secondary;font-size:13px}.list{display:grid;gap:12px;min-height:80px}.item{padding:12px;border:1px solid var(--app-border);border-radius:$border-radius-md;background:var(--app-surface)}.item p{margin:5px 0 10px;color:$text-secondary;font-size:13px}.item .el-alert{margin-top:10px}</style>
