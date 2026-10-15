<template>
  <div class="task-center">
    <el-badge :value="unreadCount || undefined" :hidden="!unreadCount" type="danger">
      <el-button class="task-center-trigger" :icon="List" :aria-label="uiText.title" @click="visible = true">{{ uiText.title }}</el-button>
    </el-badge>
    <el-drawer v-model="visible" :title="uiText.title" size="min(440px, 92vw)">
      <div class="toolbar"><span>{{ uiText.summary }}</span><RefreshButton :label="uiText.refresh" :loading="loading" @click="refresh" /></div>
      <PageErrorAlert v-if="error" :message="error" :retry-text="uiText.retry" @retry="refresh" />
      <div v-else class="list" v-loading="loading">
        <section v-if="notifications.length" class="task-group">
          <div class="group-title"><strong>{{ uiText.notice }}</strong><span>{{ notifications.length }}</span></div>
          <button v-for="item in notifications" :key="item.id" class="notice-item" type="button" @click="openNotification(item)"><strong>{{ localizedNotificationTitle(item) }}</strong><span>{{ localizedNotificationMessage(item) }}</span></button>
        </section>
        <section v-for="group in visibleGroups" :key="group.key" class="task-group">
          <div class="group-title"><strong>{{ group.label }}</strong><span>{{ group.items.length }}</span></div>
          <article v-for="task in group.items" :key="`${task.kind}-${task.id}`" class="item">
            <div class="row"><strong>{{ taskTitle(task) }}</strong><span v-if="isUnread(task)" class="new-label">{{ uiText.newLabel }}</span><StatusTag :status="task.status" :label="statusText(task.status)" size="small" /></div>
            <p>{{ taskSummary(task) }}</p>
            <el-progress :percentage="progress(task.progress)" :status="task.status === 'failed' ? 'exception' : task.status === 'completed' ? 'success' : undefined" :stroke-width="8" />
            <el-alert v-if="task.error_message" :title="failureReason(task.error_message)" type="error" :closable="false" show-icon />
            <div class="actions"><el-button link type="primary" @click="openTask(task)">{{ task.status === 'completed' ? uiText.result : task.status === 'failed' ? uiText.detail : uiText.monitor }}</el-button></div>
          </article>
        </section>
        <el-empty v-if="!allTasks.length && !loading" :description="uiText.empty" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { List } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import StatusTag from '@/components/common/StatusTag.vue'
import PageErrorAlert from '@/components/common/PageErrorAlert.vue'
import RefreshButton from '@/components/common/RefreshButton.vue'
import { useTaskStore } from '@/stores/tasks'
import { useUserStore } from '@/stores/user'
import { useSettingsStore } from '@/stores/settings'
import { listNotificationsApi, markNotificationReadApi } from '@/api/notifications'

const visible = ref(false)
const router = useRouter()
const userStore = useUserStore()
const settingsStore = useSettingsStore()
const taskStore = useTaskStore()
const { trainingTasks, loadingTrainingTasks, detectionTasks, loadingDetectionTasks } = storeToRefs(taskStore)
const error = ref('')
const notifications = ref([])
const unreadIds = ref(new Set())
const previousStatuses = ref({})
const storageKey = computed(() => `ssdd_task_notifications_${userStore.user?.id || 'anonymous'}`)
const uiText = computed(() => settingsStore.isEnglish ? {
  title: 'Task Center', refresh: 'Refresh', retry: 'Retry', summary: 'Running tasks and recent results', notice: 'New notifications', running: 'Running', failed: 'Failed', completed: 'Recently completed', emptyRunning: 'No running tasks', emptyFailed: 'No failed tasks', emptyCompleted: 'No recently completed tasks', empty: 'No tasks', newLabel: 'New', result: 'View result', detail: 'View details', monitor: 'View monitoring', unknown: 'Unknown status', failure: 'Task failed. View details.',
} : {
  title: '任务中心', refresh: '刷新', retry: '重试', summary: '查看运行中的任务和最近结果', notice: '新通知', running: '正在运行', failed: '运行失败', completed: '最近完成', emptyRunning: '暂无运行中的任务', emptyFailed: '暂无失败任务', emptyCompleted: '暂无最近完成任务', empty: '暂无任务', newLabel: '新', result: '查看结果', detail: '查看详情', monitor: '查看监控', unknown: '未知状态', failure: '任务执行失败，请查看详情。',
})
const activeStatuses = ['pending', 'running', 'processing']
const allTaskItems = computed(() => [
  ...trainingTasks.value.map((task) => ({ ...task, kind: 'training' })),
  ...detectionTasks.value.map((task) => ({ ...task, kind: 'detection', progress: task.status === 'completed' ? 100 : (task.progress || 0), error_message: task.errorMessage })),
])
const runningTasks = computed(() => allTaskItems.value.filter((task) => activeStatuses.includes(task.status)))
const failedTasks = computed(() => allTaskItems.value.filter((task) => task.status === 'failed').slice(0, 3))
const completedTasks = computed(() => allTaskItems.value.filter((task) => task.status === 'completed').slice(0, 3))
const allTasks = computed(() => [...runningTasks.value, ...failedTasks.value, ...completedTasks.value])
const groups = computed(() => [
  { key: 'running', label: uiText.value.running, empty: uiText.value.emptyRunning, items: runningTasks.value },
  { key: 'failed', label: uiText.value.failed, empty: uiText.value.emptyFailed, items: failedTasks.value },
  { key: 'completed', label: uiText.value.completed, empty: uiText.value.emptyCompleted, items: completedTasks.value },
])
const visibleGroups = computed(() => groups.value.filter((group) => group.items.length))
const visibleTaskKeys = computed(() => new Set(allTasks.value.map(allTaskKey)))
const unreadCount = computed(() => notifications.value.length + [...unreadIds.value].filter((key) => visibleTaskKeys.value.has(key)).length)
const loading = computed(() => loadingTrainingTasks.value || loadingDetectionTasks.value)
const progress = (value) => Math.min(100, Math.max(0, Number(value) || 0))
const statusText = (status) => ({ pending: settingsStore.isEnglish ? 'Pending' : '等待中', running: settingsStore.isEnglish ? 'Running' : '运行中', processing: settingsStore.isEnglish ? 'Processing' : '处理中', completed: settingsStore.isEnglish ? 'Completed' : '已完成', failed: settingsStore.isEnglish ? 'Failed' : '失败', cancelled: settingsStore.isEnglish ? 'Cancelled' : '已取消' })[status] || uiText.value.unknown
const typeNames = { single: ['Single image', '单图检测'], batch: ['Batch image', '批量图片检测'], zip: ['ZIP', '压缩包检测'], video: ['Video', '视频检测'], camera: ['Camera', '摄像头检测'] }
const typeName = (value) => typeNames[value]?.[settingsStore.isEnglish ? 0 : 1] || (settingsStore.isEnglish ? 'Detection' : '检测')
const taskTitle = (task) => `${task.kind === 'training' ? (settingsStore.isEnglish ? 'Training' : '训练') : typeName(task.taskType)} #${task.id}`
const taskSummary = (task) => task.kind === 'training' ? `${task.model_name || (settingsStore.isEnglish ? 'Unnamed model' : '未命名模型')} · ${task.dataset_name || task.dataset_path || (settingsStore.isEnglish ? 'Unnamed dataset' : '未命名数据集')}` : `${typeName(task.taskType)} · ${task.sceneName || (settingsStore.isEnglish ? 'Default scene' : '默认场景')}`
const failureReason = (reason) => reason || uiText.value.failure
const allTaskKey = (task) => `${task.kind}-${task.id}`
const isUnread = (task) => unreadIds.value.has(allTaskKey(task))
function readNotifications() { try { unreadIds.value = new Set(JSON.parse(localStorage.getItem(storageKey.value) || '[]')) } catch { unreadIds.value = new Set() } }
function saveNotifications() { localStorage.setItem(storageKey.value, JSON.stringify([...unreadIds.value])) }
function observeStatus(items) { if (!items.length) return; const next = { ...previousStatuses.value }; items.forEach((task) => { const key = allTaskKey(task); const oldStatus = next[key]; if (oldStatus && oldStatus !== task.status && ['completed', 'failed'].includes(task.status)) unreadIds.value.add(key); next[key] = task.status }); previousStatuses.value = next; saveNotifications() }
function markRead(task) { unreadIds.value.delete(allTaskKey(task)); saveNotifications() }
async function loadNotifications() {
  const result = await listNotificationsApi({ limit: 100, unread_only: true })
  const unread = (result?.items || []).filter((item) => !item.read_at).sort((a, b) => new Date(b.created_at || b.createdAt || 0) - new Date(a.created_at || a.createdAt || 0))
  notifications.value = unread.slice(0, 3)
  void Promise.all(unread.slice(3).map((item) => markNotificationReadApi(item.id))).catch(() => {})
}
async function refresh() { error.value = ''; try { await Promise.all([taskStore.fetchTrainingTasks(), taskStore.fetchDetectionTasks(), loadNotifications()]) } catch (err) { error.value = err?.response?.data?.detail || err?.message || (settingsStore.isEnglish ? 'Task center failed to load' : '任务中心加载失败') } }
const notificationTitle = (item) => { const raw = String(item.title || ''); if (/fail|error/i.test(raw)) return settingsStore.isEnglish ? 'Task failed' : '任务执行失败'; if (/success|complete|done/i.test(raw)) return settingsStore.isEnglish ? 'Task completed' : '任务已完成'; return raw || (settingsStore.isEnglish ? 'Task status updated' : '任务状态更新') }
const notificationMessage = (item) => { const raw = String(item.message || item.error_message || ''); return /fail|error/i.test(raw) && !settingsStore.isEnglish ? `失败原因：${raw}` : raw || (settingsStore.isEnglish ? 'Task status updated' : '任务状态已更新') }
const localizedNotificationType = (item) => typeName(item.task_type || item.taskType || item.resource_type?.replace('_task', ''))
const localizedNotificationTitle = (item) => {
  const raw = String(item.title || item.message || '')
  const failed = /fail|error|失败|错误/i.test(raw) || item.status === 'failed'
  const completed = /success|complete|done|完成|成功/i.test(raw) || ['completed', 'success'].includes(item.status)
  const id = item.task_id || item.resource_id
  if (settingsStore.isEnglish) return `${localizedNotificationType(item)} ${failed ? 'failed' : completed ? 'completed' : 'updated'}${id ? ` #${id}` : ''}`
  return `${localizedNotificationType(item)}${failed ? '失败' : completed ? '已完成' : '状态更新'}${id ? ` #${id}` : ''}`
}
const localizedNotificationMessage = (item) => {
  const raw = String(item.error_message || item.errorMessage || item.message || '')
  if (settingsStore.isEnglish) return raw || 'Task status updated.'
  return /fail|error/i.test(raw) ? `失败原因：${raw}` : raw || '任务状态已更新。'
}
async function openNotification(item) { await markNotificationReadApi(item.id); notifications.value = notifications.value.filter((notice) => notice.id !== item.id); if (item.resource_type === 'training_task') await router.push({ path: '/training', query: { task: item.task_id || item.resource_id } }); else if (item.resource_type === 'detection_task') await router.push({ path: '/history', query: { task: item.task_id || item.resource_id } }) }
async function openTask(task) { markRead(task); visible.value = false; if (task.kind === 'training') { taskStore.selectTrainingTask(task.id); await router.push('/training'); return } await router.push(task.taskType === 'video' ? { path: '/detection', query: { videoTask: task.id } } : { path: '/history', query: { task: task.id } }) }
readNotifications()
watch(allTaskItems, observeStatus, { immediate: true })
let timer = null
onMounted(async () => { await refresh(); timer = window.setInterval(refresh, 5000) })
onBeforeUnmount(() => { if (timer) window.clearInterval(timer) })
</script>

<style lang="scss" scoped>
.task-center { position: fixed; z-index: 20; right: 28px; bottom: 28px; }
.task-center-trigger { border-radius: 999px; }
.toolbar, .row, .actions, .group-title { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.toolbar { margin-bottom: 14px; color: $text-secondary; font-size: 13px; }
.list, .task-group { display: grid; gap: 12px; min-height: 40px; }
.group-title { color: var(--app-text); font-size: 14px; }
.group-title span { color: var(--app-text-secondary); font-size: 12px; }
.item, .notice-item { padding: 12px; border: 1px solid var(--app-border); border-radius: $border-radius-md; background: var(--app-surface); }
.notice-item { display: flex; flex-direction: column; gap: 3px; width: 100%; text-align: left; cursor: pointer; }
.notice-item span, .item p { color: $text-secondary; font-size: 13px; }
.item p { margin: 5px 0 10px; }
.item .el-alert { margin-top: 10px; }
.new-label { color: var(--el-color-danger); font-size: 12px; margin-left: auto; }
</style>
