<template>
  <div class="admin-page">
    <ModulePageHeader :title="text.title" :description="text.description">
      <el-button :loading="loading" @click="load">{{ text.refresh }}</el-button>
    </ModulePageHeader>
    <PageErrorAlert v-if="error" :message="error" :retry-text="text.refresh" @retry="load" />

    <el-card class="section-card" shadow="never">
      <template #header><span class="card-title">{{ text.resourceStatus }}</span></template>
      <div class="summary-grid">
        <div v-for="(value, name) in resourceStatus.resources || {}" :key="name" class="summary-item"><span>{{ text[name] || name }}</span><b>{{ value }}</b></div>
        <div class="summary-item"><span>{{ text.cleanupPending }}</span><b :class="{ danger: resourceStatus.cleanup_pending_total }">{{ resourceStatus.cleanup_pending_total || 0 }}</b></div>
      </div>
      <div class="task-summary">
        <span>{{ text.detectionTasks }}：{{ formatTaskStates(resourceStatus.tasks?.detection) }}</span>
        <span>{{ text.trainingTasks }}：{{ formatTaskStates(resourceStatus.tasks?.training) }}</span>
      </div>
    </el-card>

    <el-card class="section-card" shadow="never">
      <template #header><span class="card-title">{{ settingsStore.isEnglish ? 'Error summary' : '错误汇总' }}</span></template>
      <el-table :data="errorSummary.items || []" size="small">
        <el-table-column prop="module" :label="settingsStore.isEnglish ? 'Module' : '模块'" width="140" />
        <el-table-column prop="action" :label="settingsStore.isEnglish ? 'Action' : '操作'" min-width="180" />
        <el-table-column prop="count" :label="settingsStore.isEnglish ? 'Count' : '次数'" width="90" />
        <el-table-column prop="last_seen" :label="settingsStore.isEnglish ? 'Last seen' : '最近发生'" min-width="180">
          <template #default="{ row }">{{ formatTime(row.last_seen) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="section-card" shadow="never">
      <template #header><span class="card-title">{{ text.users }}</span></template>
      <el-table v-loading="loading" :data="users">
        <el-table-column prop="username" :label="text.user" min-width="150" />
        <el-table-column prop="email" :label="text.email" min-width="210" />
        <el-table-column :label="text.role" min-width="150"><template #default="{ row }">{{ row.roles?.join(', ') || '-' }}</template></el-table-column>
        <el-table-column :label="text.status" width="110"><template #default="{ row }"><StatusTag :status="row.is_active ? 'completed' : 'failed'" :label="row.is_active ? text.active : text.inactive" /></template></el-table-column>
        <el-table-column :label="text.actions" width="300" fixed="right"><template #default="{ row }"><el-button v-if="row.id !== userStore.user?.id" link :type="row.is_active ? 'warning' : 'success'" @click="toggleUser(row)">{{ row.is_active ? text.deactivate : text.activate }}</el-button><el-button v-if="row.id !== userStore.user?.id" link @click="resetPassword(row)">{{ text.resetPassword }}</el-button><el-button v-if="row.id !== userStore.user?.id" link type="danger" @click="removeUser(row)">{{ text.delete }}</el-button></template></el-table-column>
      </el-table>
    </el-card>

    <el-card class="section-card" shadow="never">
      <template #header><div class="audit-header"><span class="card-title">{{ text.audit }}</span><el-button size="small" @click="exportAudit">{{ settingsStore.isEnglish ? 'Export redacted CSV' : '导出脱敏审计 CSV' }}</el-button></div></template>
      <el-table v-loading="loading" :data="logs.items || []">
        <el-table-column prop="username" :label="text.user" min-width="130" />
        <el-table-column prop="module" :label="text.module" width="120" />
        <el-table-column prop="action" :label="text.action" min-width="160" />
        <el-table-column prop="description" :label="text.descriptionColumn" min-width="240" show-overflow-tooltip />
        <el-table-column prop="created_at" :label="text.createdAt" min-width="170"><template #default="{ row }">{{ formatTime(row.created_at) }}</template></el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import ModulePageHeader from '@/components/common/ModulePageHeader.vue'
import PageErrorAlert from '@/components/common/PageErrorAlert.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { activateUser, adminResetPassword, deactivateUser, deleteUser, exportOperationLogs, getAdminUsers, getErrorSummary, getOperationLogs, getResourceStatus } from '@/api/admin'
import { getApiErrorMessage } from '@/utils/apiError'
import { useSettingsStore } from '@/stores/settings'
import { useUserStore } from '@/stores/user'

const settingsStore = useSettingsStore(); const userStore = useUserStore()
const loading = ref(false); const error = ref(''); const users = ref([]); const logs = ref({ items: [] }); const errorSummary = ref({ items: [] }); const resourceStatus = ref({})
const text = computed(() => settingsStore.isEnglish ? { title: 'Administration', description: 'Review users and audit records. Destructive actions are logged.', refresh: 'Refresh', users: 'Users', user: 'User', email: 'Email', role: 'Roles', status: 'Status', active: 'Active', inactive: 'Inactive', actions: 'Actions', activate: 'Activate', deactivate: 'Deactivate', resetPassword: 'Reset password', resetPasswordPrompt: 'Enter a new password (at least 6 characters).', delete: 'Delete', audit: 'Recent audit records', module: 'Module', action: 'Action', descriptionColumn: 'Description', createdAt: 'Created at', confirm: 'Confirm', deactivateConfirm: 'Disable this account?', deleteConfirm: 'Delete this user and associated data? This cannot be undone.', resourceStatus: 'Resource status', datasets: 'Datasets', models: 'Models', knowledge_documents: 'Knowledge docs', sessions: 'Sessions', cleanupPending: 'Pending cleanup', detectionTasks: 'Detection tasks', trainingTasks: 'Training tasks' } : { title: '管理中心', description: '查看用户和审计记录；危险操作会被审计。', refresh: '刷新', users: '用户', user: '用户', email: '邮箱', role: '角色', status: '状态', active: '启用', inactive: '禁用', actions: '操作', activate: '启用', deactivate: '禁用', resetPassword: '重置密码', resetPasswordPrompt: '请输入新密码（至少 6 位）。', delete: '删除', audit: '最近审计记录', module: '模块', action: '操作', descriptionColumn: '说明', createdAt: '创建时间', confirm: '确认', deactivateConfirm: '确定禁用该账户？', deleteConfirm: '确定删除该用户及其关联数据？此操作不可恢复。', resourceStatus: '资源状态', datasets: '数据集', models: '模型', knowledge_documents: '知识文档', sessions: '会话', cleanupPending: '待清理资源', detectionTasks: '检测任务', trainingTasks: '训练任务' })
const formatTime = (value) => value ? new Date(value).toLocaleString(settingsStore.isEnglish ? 'en-US' : 'zh-CN', { hour12: false }) : '-'
const formatTaskStates = (states = {}) => Object.entries(states).map(([status, count]) => `${status}: ${count}`).join(' · ')
async function load() { loading.value = true; error.value = ''; try { const [userData, logData, statusData] = await Promise.all([getAdminUsers({ page: 1, page_size: 100 }), getOperationLogs({ page: 1, page_size: 20 }), getResourceStatus()]); users.value = userData.items || []; logs.value = logData; resourceStatus.value = statusData } catch (err) { error.value = getApiErrorMessage(err, '管理数据加载失败') } finally { loading.value = false } }
async function toggleUser(row) { const message = row.is_active ? text.value.deactivateConfirm : `${text.value.activate} ${row.username}?`; try { await ElMessageBox.confirm(message, text.value.confirm, { type: 'warning' }); await (row.is_active ? deactivateUser(row.id) : activateUser(row.id)); await load() } catch (err) { if (err !== 'cancel' && err !== 'close') error.value = getApiErrorMessage(err, '用户操作失败') } }
async function resetPassword(row) { try { const { value } = await ElMessageBox.prompt(text.value.resetPasswordPrompt, `${text.value.resetPassword}: ${row.username}`, { inputType: 'password', confirmButtonText: text.value.confirm, cancelButtonText: 'Cancel', inputValidator: (value) => value && value.length >= 6 }) ; await adminResetPassword(row.id, value); await load() } catch (err) { if (err !== 'cancel' && err !== 'close') error.value = getApiErrorMessage(err, '密码重置失败') } }
async function removeUser(row) { try { await ElMessageBox.confirm(text.value.deleteConfirm, text.value.confirm, { type: 'error' }); await deleteUser(row.id); await load() } catch (err) { if (err !== 'cancel' && err !== 'close') error.value = getApiErrorMessage(err, '用户删除失败') } }
async function exportAudit() {
  try {
    const blob = await exportOperationLogs({ page_size: 5000 })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'audit_logs.csv'
    link.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    error.value = getApiErrorMessage(err, '审计导出失败')
  }
}
async function loadErrorSummary() {
  try { errorSummary.value = await getErrorSummary({ limit: 20 }) } catch { errorSummary.value = { items: [] } }
}
onMounted(() => { load(); loadErrorSummary() })
</script>

<style scoped lang="scss">.section-card { margin-bottom: 18px; }.card-title { font-weight: 600; }.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; }.summary-item { display: flex; flex-direction: column; gap: 4px; padding: 10px; border-radius: 6px; background: var(--app-bg); }.summary-item b { font-size: 20px; }.danger { color: var(--el-color-danger); }.task-summary { display: flex; flex-wrap: wrap; gap: 18px; margin-top: 12px; font-size: 13px; color: var(--app-text-secondary); }</style>
