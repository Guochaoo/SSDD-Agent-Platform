<template>
  <div class="file-browser-page">
    <ModulePageHeader :title="text.title">
      <el-upload :auto-upload="false" :show-file-list="false" accept=".zip" :on-change="uploadDataset"><el-button>{{ text.uploadDataset }}</el-button></el-upload>
      <el-button @click="modelUploadVisible = true">{{ text.uploadModel }}</el-button>
      <el-button :icon="Refresh" :loading="loading" @click="loadAssets">{{ text.refresh }}</el-button>
    </ModulePageHeader>
    <PageErrorAlert v-if="pageError" :message="pageError" :retry-text="text.refresh" @retry="loadAssets" />
    <section class="resource-toolbar">
      <el-tabs v-model="activeTab" class="resource-tabs">
        <el-tab-pane :label="`${text.datasets} (${datasets.length})`" name="datasets" />
        <el-tab-pane :label="`${text.models} (${models.length})`" name="models" />
        <el-tab-pane :label="`${resourceText.detections} (${detectionTasks.length})`" name="detections" />
      </el-tabs>
      <el-input v-model.trim="keyword" clearable :prefix-icon="Search" :placeholder="resourceText.search" />
    </section>
    <el-card v-show="activeTab === 'datasets'" shadow="never" class="asset-card">
      <template #header><div class="card-title">{{ text.datasets }}</div></template>
      <el-table :data="filteredDatasets" v-loading="loading" stripe>
        <el-table-column prop="name" :label="text.name" min-width="180" /><el-table-column prop="path" :label="text.path" min-width="220" />
        <el-table-column :label="text.status" width="120"><template #default="{ row }"><el-tag :type="row.ready ? 'success' : 'warning'">{{ row.ready ? text.ready : text.incomplete }}</el-tag></template></el-table-column>
        <el-table-column :label="text.actions" width="210"><template #default="{ row }"><el-button link type="primary" @click="downloadDataset(row)">{{ text.download }}</el-button><el-button v-if="canDelete(row)" link type="primary" @click="openDatasetEditor(row)">{{ text.edit }}</el-button><el-button v-if="canDelete(row)" link type="danger" @click="deleteDataset(row)">{{ text.delete }}</el-button></template></el-table-column>
      </el-table>
      <el-empty v-if="!loading && !filteredDatasets.length" :description="text.noDatasets" />
    </el-card>
    <el-card v-show="activeTab === 'models'" shadow="never" class="asset-card">
      <template #header><div class="card-title">{{ text.models }}</div></template>
      <el-table :data="filteredModels" v-loading="loading" stripe>
        <el-table-column prop="sceneName" :label="text.scene" min-width="150" /><el-table-column prop="version" :label="text.version" width="120" /><el-table-column prop="modelName" :label="text.model" min-width="220" />
        <el-table-column :label="text.map50" width="110"><template #default="{ row }">{{ formatPercent(row.map50) }}</template></el-table-column><el-table-column :label="text.status" width="180"><template #default="{ row }"><StatusTag :status="row.cleanupPending ? 'failed' : (row.isDefault ? 'completed' : row.status)" :label="modelStatusLabel(row)" /><el-tooltip v-if="row.cleanupPending && row.cleanupError" :content="row.cleanupError"><el-icon class="cleanup-warning"><WarningFilled /></el-icon></el-tooltip></template></el-table-column>
        <el-table-column :label="text.createdAt" min-width="180"><template #default="{ row }">{{ formatDate(row.createdAt) }}</template></el-table-column>
        <el-table-column :label="text.actions" width="260"><template #default="{ row }"><el-button v-if="!row.cleanupPending" link type="primary" @click="downloadModel(row)">{{ text.download }}</el-button><el-button v-if="row.status !== 'deleted' && !row.isDefault && !row.cleanupPending" link type="primary" @click="setDefaultModel(row)">{{ text.setDefault }}</el-button><el-button v-if="row.cleanupPending && canDelete(row)" link type="warning" @click="retryModelCleanup(row)">{{ settingsStore.isEnglish ? 'Retry cleanup' : '重试清理' }}</el-button><el-button v-if="row.status !== 'deleted' && !row.isDefault && canDelete(row)" link type="danger" @click="deleteModel(row)">{{ text.delete }}</el-button></template></el-table-column>
      </el-table>
      <el-empty v-if="!loading && !filteredModels.length" :description="text.noModels" />
    </el-card>
    <el-card v-show="activeTab === 'detections'" shadow="never" class="asset-card">
      <template #header><div class="card-title">{{ resourceText.detections }}</div></template>
      <el-table :data="filteredDetections" v-loading="loading" stripe>
        <el-table-column prop="id" :label="resourceText.taskId" width="100" sortable />
        <el-table-column prop="sceneName" :label="text.scene" min-width="170" show-overflow-tooltip />
        <el-table-column :label="resourceText.type" width="120"><template #default="{ row }">{{ taskTypeLabel(row.taskType) }}</template></el-table-column>
        <el-table-column :label="text.status" width="120"><template #default="{ row }"><StatusTag :status="row.status" :label="row.status" /></template></el-table-column>
        <el-table-column prop="totalImages" :label="resourceText.files" width="90" align="right" sortable />
        <el-table-column prop="totalObjects" :label="resourceText.defects" width="90" align="right" sortable />
        <el-table-column prop="createdAt" :label="text.createdAt" min-width="180" sortable><template #default="{ row }">{{ formatDate(row.createdAt) }}</template></el-table-column>
        <el-table-column :label="text.actions" width="120"><template #default="{ row }"><el-button link type="primary" @click="openDetection(row)">{{ resourceText.view }}</el-button></template></el-table-column>
      </el-table>
      <el-empty v-if="!loading && !filteredDetections.length" :description="resourceText.noDetections" />
    </el-card>
    <el-dialog v-model="modelUploadVisible" :title="text.uploadModel" width="480px"><el-form :model="modelUpload" label-position="top"><el-form-item :label="text.scene"><el-select v-model="modelUpload.sceneId" class="full-width"><el-option v-for="scene in scenes" :key="scene.id" :label="scene.displayName" :value="scene.id" /></el-select></el-form-item><el-form-item :label="text.version"><el-input v-model="modelUpload.version" /></el-form-item><el-form-item :label="text.model"><el-input v-model="modelUpload.modelName" /></el-form-item><el-form-item label=".pt"><el-upload :auto-upload="false" :limit="1" accept=".pt" :on-change="selectModelFile"><el-button>{{ text.selectFile }}</el-button></el-upload></el-form-item></el-form><template #footer><el-button @click="modelUploadVisible = false">{{ text.cancel }}</el-button><el-button type="primary" :loading="uploading" @click="uploadModel">{{ text.upload }}</el-button></template></el-dialog>
    <el-dialog v-model="datasetEditorVisible" :title="text.editDataset" width="min(480px, 92vw)"><el-form :model="datasetEditor" label-position="top"><el-form-item :label="text.name"><el-input v-model="datasetEditor.displayName" maxlength="200" show-word-limit /></el-form-item><el-form-item :label="text.metadataDescription"><el-input v-model="datasetEditor.description" type="textarea" :rows="4" maxlength="2000" show-word-limit /></el-form-item></el-form><template #footer><el-button @click="datasetEditorVisible = false">{{ text.cancel }}</el-button><el-button type="primary" :loading="savingDatasetMetadata" @click="saveDatasetMetadata">{{ text.save }}</el-button></template></el-dialog>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search, WarningFilled } from '@element-plus/icons-vue'
import ModulePageHeader from '@/components/common/ModulePageHeader.vue'
import PageErrorAlert from '@/components/common/PageErrorAlert.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { deleteTrainingDataset, downloadTrainingDataset, getTrainingDatasets, updateTrainingDatasetMetadata, uploadTrainingDataset } from '@/api/training'
import { deleteModelVersionApi, downloadModelVersionApi, getModelsApi, getScenesApi, retryModelCleanupApi, setDefaultModelApi, uploadModelVersionApi } from '@/api/models'
import { getApiErrorMessage } from '@/utils/apiError'
import { getHistoryApi, getHistoryTaskTypeLabel } from '@/api/history'
import { useSettingsStore } from '@/stores/settings'
import { useUserStore } from '@/stores/user'
const settingsStore = useSettingsStore(); const userStore = useUserStore(); const router = useRouter(); const loading = ref(false); const uploading = ref(false); const pageError = ref(''); const datasets = ref([]); const models = ref([]); const scenes = ref([]); const detectionTasks = ref([]); const activeTab = ref('datasets'); const keyword = ref(''); const modelUploadVisible = ref(false); const modelUpload = ref({ sceneId: '', version: '', modelName: '', file: null }); const datasetEditorVisible = ref(false); const savingDatasetMetadata = ref(false); const datasetEditor = ref({ path: '', displayName: '', description: '' })
const text = computed(() => settingsStore.isEnglish ? { title:'Files', refresh:'Refresh', datasets:'Datasets', models:'Model versions', name:'Name', path:'Path', status:'Status', ready:'Ready', incomplete:'Incomplete', noDatasets:'No training datasets are available', noModels:'No model versions are available', scene:'Scene', version:'Version', model:'Model', map50:'mAP@50', default:'Default', createdAt:'Created at', actions:'Actions', setDefault:'Set default', download:'Download', edit:'Edit', editDataset:'Edit dataset metadata', metadataDescription:'Description', save:'Save', delete:'Delete', deleteConfirm:'This operation cannot be undone. Continue?', deleteTitle:'Confirm deletion', deleted:'Deleted', loadFailed:'Failed to load files', actionFailed:'File operation failed', uploadDataset:'Upload dataset', uploadModel:'Upload model', upload:'Upload', selectFile:'Select file', cancel:'Cancel' } : { title:'文件查看', refresh:'刷新', datasets:'数据集', models:'模型版本', name:'名称', path:'路径', status:'状态', ready:'可用', incomplete:'未完成', noDatasets:'暂无训练数据集', noModels:'暂无模型版本', scene:'场景', version:'版本', model:'模型', map50:'mAP@50', default:'默认模型', createdAt:'创建时间', actions:'操作', setDefault:'设为默认', download:'下载', edit:'编辑', editDataset:'编辑数据集元数据', metadataDescription:'描述', save:'保存', delete:'删除', deleteConfirm:'删除后不可恢复，是否继续？', deleteTitle:'确认删除', deleted:'已删除', loadFailed:'文件列表加载失败', actionFailed:'文件操作失败', uploadDataset:'上传数据集', uploadModel:'上传模型', upload:'上传', selectFile:'选择文件', cancel:'取消' })
const canDelete = (asset) => !asset.isBuiltin && (userStore.isSuperuser || Number(asset.ownerId ?? asset.owner_id) === Number(userStore.user?.id))
const resourceText = computed(() => settingsStore.isEnglish ? { detections:'Detection tasks', search:'Search the current resource type', taskId:'Task ID', type:'Type', files:'Files', defects:'Defects', view:'View', noDetections:'No detection tasks are available' } : { detections:'检测任务', search:'搜索当前资源类型', taskId:'任务 ID', type:'类型', files:'文件', defects:'缺陷', view:'查看', noDetections:'暂无检测任务' })
const normalizedKeyword = computed(() => keyword.value.toLowerCase())
const includesKeyword = (...values) => !normalizedKeyword.value || values.some(value => String(value ?? '').toLowerCase().includes(normalizedKeyword.value))
const filteredDatasets = computed(() => datasets.value.filter(item => includesKeyword(item.name, item.display_name, item.path, item.description)))
const filteredModels = computed(() => models.value.filter(item => includesKeyword(item.sceneName, item.version, item.modelName, item.status)))
const filteredDetections = computed(() => detectionTasks.value.filter(item => includesKeyword(item.id, item.sceneName, item.taskType, item.status)))
const taskTypeLabel = (value) => getHistoryTaskTypeLabel(value)
const modelStatusLabel = (model) => model.cleanupPending ? (settingsStore.isEnglish ? 'Cleanup pending' : '待清理重试') : (model.isDefault ? text.value.default : model.status)
const formatPercent = (value) => Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(2)}%` : '-'
const formatDate = (value) => !value ? '-' : new Date(value).toLocaleString(settingsStore.isEnglish ? 'en-US' : 'zh-CN', { hour12:false })
function saveBlob(blob, filename) { const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url) }
async function loadAssets() {
  loading.value = true
  pageError.value = ''
  const [datasetResult, sceneResult, detectionResult] = await Promise.allSettled([
    getTrainingDatasets(),
    getScenesApi(),
    getHistoryApi({ page: 1, pageSize: 100 }),
  ])
  const errors = []
  if (datasetResult.status === 'fulfilled') datasets.value = datasetResult.value?.items ?? datasetResult.value ?? []
  else errors.push(getApiErrorMessage(datasetResult.reason, text.value.loadFailed))
  if (detectionResult.status === 'fulfilled') detectionTasks.value = detectionResult.value.items
  else errors.push(getApiErrorMessage(detectionResult.reason, text.value.loadFailed))
  if (sceneResult.status === 'fulfilled') {
    scenes.value = sceneResult.value
    const modelResults = await Promise.allSettled(sceneResult.value.map(async scene => (await getModelsApi(scene.id)).map(model => ({ ...model, sceneId: scene.id, sceneName: scene.displayName || scene.name }))))
    models.value = modelResults.filter(result => result.status === 'fulfilled').flatMap(result => result.value)
    modelResults.filter(result => result.status === 'rejected').forEach(result => errors.push(getApiErrorMessage(result.reason, text.value.loadFailed)))
  } else {
    errors.push(getApiErrorMessage(sceneResult.reason, text.value.loadFailed))
  }
  pageError.value = [...new Set(errors)].join('；')
  loading.value = false
}
function openDetection(row) { router.push({ name: 'History', query: { task: row.id } }) }
async function setDefaultModel(model) { try { await setDefaultModelApi(model.sceneId,model.id); await loadAssets() } catch(error) { pageError.value=getApiErrorMessage(error,text.value.actionFailed) } }
async function downloadDataset(row) { try { saveBlob(await downloadTrainingDataset(row.path),`${row.name}.zip`) } catch(error) { pageError.value=getApiErrorMessage(error,text.value.actionFailed) } }
function openDatasetEditor(row) { datasetEditor.value = { path: row.path, displayName: row.display_name || row.displayName || row.name, description: row.description || '' }; datasetEditorVisible.value = true }
async function saveDatasetMetadata() { savingDatasetMetadata.value = true; try { await updateTrainingDatasetMetadata(datasetEditor.value.path, { display_name: datasetEditor.value.displayName, description: datasetEditor.value.description }); datasetEditorVisible.value = false; ElMessage.success(text.value.save); await loadAssets() } catch(error) { pageError.value=getApiErrorMessage(error,text.value.actionFailed) } finally { savingDatasetMetadata.value = false } }
async function downloadModel(row) { try { saveBlob(await downloadModelVersionApi(row.sceneId,row.id),row.modelName || `${row.version}.pt`) } catch(error) { pageError.value=getApiErrorMessage(error,text.value.actionFailed) } }
async function confirmDeletion() { try { await ElMessageBox.confirm(text.value.deleteConfirm,text.value.deleteTitle,{type:'warning'}); return true } catch { return false } }
async function deleteDataset(row) { if(await confirmDeletion()) try { await deleteTrainingDataset(row.path); ElMessage.success(text.value.deleted); await loadAssets() } catch(error) { pageError.value=getApiErrorMessage(error,text.value.actionFailed) } }
async function deleteModel(row) { if(await confirmDeletion()) try { await deleteModelVersionApi(row.sceneId,row.id); ElMessage.success(text.value.deleted); await loadAssets() } catch(error) { pageError.value=getApiErrorMessage(error,text.value.actionFailed) } }
async function retryModelCleanup(row) { try { await retryModelCleanupApi(row.sceneId, row.id); ElMessage.success(settingsStore.isEnglish ? 'Cleanup completed' : '清理完成'); await loadAssets() } catch(error) { pageError.value=getApiErrorMessage(error,text.value.actionFailed) } }
async function uploadDataset(file) { try { await uploadTrainingDataset(file.raw); ElMessage.success(text.value.upload); await loadAssets() } catch(error) { pageError.value=getApiErrorMessage(error,text.value.actionFailed) } }
function selectModelFile(file) { modelUpload.value.file=file.raw }
async function uploadModel() { const item=modelUpload.value; if(!item.sceneId || !item.version || !item.modelName || !item.file) return; uploading.value=true; try { await uploadModelVersionApi(item.sceneId,item); modelUploadVisible.value=false; modelUpload.value={sceneId:'',version:'',modelName:'',file:null}; ElMessage.success(text.value.upload); await loadAssets() } catch(error) { pageError.value=getApiErrorMessage(error,text.value.actionFailed) } finally { uploading.value=false } }
onMounted(loadAssets)
</script>
<style lang="scss" scoped>
.file-browser-page { max-width: 1200px; margin: 0 auto; padding: 0; }
.asset-card { margin-bottom: 18px; }
.resource-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 18px; margin-bottom: 16px; padding: 0 4px; }
.resource-tabs { flex: 1; min-width: 0; }
.resource-toolbar :deep(.el-tabs__header) { margin-bottom: 0; }
.resource-toolbar :deep(.el-input) { width: min(320px, 100%); }
.card-title { font-weight: 600; color: var(--app-text); }
.full-width { width: 100%; }
.cleanup-warning { margin-left: 6px; color: var(--el-color-warning); vertical-align: middle; }
@media (max-width: 720px) { .resource-toolbar { align-items: stretch; flex-direction: column; } .resource-toolbar :deep(.el-input) { width: 100%; } }
</style>
