<template>
  <div class="file-browser-page">
    <ModulePageHeader :title="text.title" :description="text.description">
      <el-button :icon="Refresh" :loading="loading" @click="loadAssets">{{ text.refresh }}</el-button>
    </ModulePageHeader>

    <el-alert v-if="pageError" :title="pageError" type="error" :closable="false" show-icon class="page-alert" />

    <el-card shadow="never" class="asset-card">
      <template #header><div class="card-title">{{ text.datasets }}</div></template>
      <el-table :data="datasets" v-loading="loading" stripe>
        <el-table-column prop="name" :label="text.name" min-width="180" />
        <el-table-column prop="path" :label="text.path" min-width="220" />
        <el-table-column :label="text.status" width="120">
          <template #default="{ row }"><el-tag :type="row.ready ? 'success' : 'warning'">{{ row.ready ? text.ready : text.incomplete }}</el-tag></template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !datasets.length" :description="text.noDatasets" />
    </el-card>

    <el-card shadow="never" class="asset-card">
      <template #header><div class="card-title">{{ text.models }}</div></template>
      <el-table :data="models" v-loading="loading" stripe>
        <el-table-column prop="sceneName" :label="text.scene" min-width="150" />
        <el-table-column prop="version" :label="text.version" width="120" />
        <el-table-column prop="modelName" :label="text.model" min-width="220" />
        <el-table-column :label="text.map50" width="110"><template #default="{ row }">{{ formatPercent(row.map50) }}</template></el-table-column>
        <el-table-column :label="text.status" width="130"><template #default="{ row }"><el-tag :type="row.isDefault ? 'success' : 'info'">{{ row.isDefault ? text.default : row.status }}</el-tag></template></el-table-column>
        <el-table-column :label="text.createdAt" min-width="180"><template #default="{ row }">{{ formatDate(row.createdAt) }}</template></el-table-column>
        <el-table-column :label="text.actions" width="130">
          <template #default="{ row }">
            <el-button v-if="!row.isDefault" link type="primary" @click="setDefaultModel(row)">{{ text.setDefault }}</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !models.length" :description="text.noModels" />
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import ModulePageHeader from '@/components/common/ModulePageHeader.vue'
import { getTrainingDatasets } from '@/api/training'
import { getModelsApi, getScenesApi, setDefaultModelApi } from '@/api/models'
import { getApiErrorMessage } from '@/utils/apiError'
import { useSettingsStore } from '@/stores/settings'

const settingsStore = useSettingsStore()
const loading = ref(false)
const pageError = ref('')
const datasets = ref([])
const models = ref([])
const text = computed(() => settingsStore.isEnglish ? {
  title: 'Files', description: 'Inspect persisted training datasets and all user-visible model versions.', refresh: 'Refresh',
  datasets: 'Datasets', models: 'Model versions', name: 'Name', path: 'Path', status: 'Status', ready: 'Ready', incomplete: 'Incomplete',
  noDatasets: 'No training datasets are available', noModels: 'No model versions are available', scene: 'Scene', version: 'Version', model: 'Model',
  map50: 'mAP@50', default: 'Default', createdAt: 'Created at', actions: 'Actions', setDefault: 'Set default', loadFailed: 'Failed to load files',
} : {
  title: '文件查看', description: '查看已持久化的训练数据集和当前用户可见的全部模型版本。', refresh: '刷新',
  datasets: '数据集', models: '模型版本', name: '名称', path: '路径', status: '状态', ready: '可用', incomplete: '未完成',
  noDatasets: '暂无训练数据集', noModels: '暂无模型版本', scene: '场景', version: '版本', model: '模型',
  map50: 'mAP@50', default: '默认模型', createdAt: '创建时间', actions: '操作', setDefault: '设为默认', loadFailed: '文件列表加载失败',
})

function formatPercent(value) {
  return Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(2)}%` : '-'
}
function formatDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString(settingsStore.isEnglish ? 'en-US' : 'zh-CN', { hour12: false })
}
async function loadAssets() {
  loading.value = true
  pageError.value = ''
  try {
    const [datasetResponse, scenes] = await Promise.all([getTrainingDatasets(), getScenesApi()])
    datasets.value = datasetResponse?.items ?? datasetResponse ?? []
    const groups = await Promise.all(scenes.map(async (scene) => (await getModelsApi(scene.id)).map((model) => ({ ...model, sceneId: scene.id, sceneName: scene.displayName || scene.name }))))
    models.value = groups.flat()
  } catch (error) {
    pageError.value = getApiErrorMessage(error, text.value.loadFailed)
  } finally {
    loading.value = false
  }
}
async function setDefaultModel(model) {
  try {
    await setDefaultModelApi(model.sceneId, model.id)
    await loadAssets()
  } catch (error) {
    pageError.value = getApiErrorMessage(error, text.value.loadFailed)
  }
}
onMounted(loadAssets)
</script>

<style lang="scss" scoped>
.asset-card { margin-bottom: 18px; }
.card-title { font-weight: 600; color: var(--app-text); }
</style>
