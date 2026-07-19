<template>
  <div class="file-browser-page">
    <ModulePageHeader :title="text.title" :description="text.description">
      <el-upload :auto-upload="false" :show-file-list="false" accept=".zip" :on-change="uploadDataset"><el-button>{{ text.uploadDataset }}</el-button></el-upload>
      <el-button @click="modelUploadVisible = true">{{ text.uploadModel }}</el-button>
      <el-button :icon="Refresh" :loading="loading" @click="loadAssets">{{ text.refresh }}</el-button>
    </ModulePageHeader>
    <PageErrorAlert v-if="pageError" :message="pageError" :retry-text="text.refresh" @retry="loadAssets" />
    <el-card shadow="never" class="asset-card">
      <template #header><div class="card-title">{{ text.datasets }}</div></template>
      <el-table :data="datasets" v-loading="loading" stripe>
        <el-table-column prop="name" :label="text.name" min-width="180" /><el-table-column prop="path" :label="text.path" min-width="220" />
        <el-table-column :label="text.status" width="120"><template #default="{ row }"><el-tag :type="row.ready ? 'success' : 'warning'">{{ row.ready ? text.ready : text.incomplete }}</el-tag></template></el-table-column>
        <el-table-column :label="text.actions" width="210"><template #default="{ row }"><el-button link type="primary" @click="downloadDataset(row)">{{ text.download }}</el-button><el-button v-if="canDelete(row)" link type="primary" @click="openDatasetEditor(row)">{{ text.edit }}</el-button><el-button v-if="canDelete(row)" link type="danger" @click="deleteDataset(row)">{{ text.delete }}</el-button></template></el-table-column>
      </el-table>
      <el-empty v-if="!loading && !datasets.length" :description="text.noDatasets" />
    </el-card>
    <el-card shadow="never" class="asset-card">
      <template #header><div class="card-title">{{ text.models }}</div></template>
      <el-table :data="models" v-loading="loading" stripe>
        <el-table-column prop="sceneName" :label="text.scene" min-width="150" /><el-table-column prop="version" :label="text.version" width="120" /><el-table-column prop="modelName" :label="text.model" min-width="220" />
        <el-table-column :label="text.map50" width="110"><template #default="{ row }">{{ formatPercent(row.map50) }}</template></el-table-column><el-table-column :label="text.status" width="180"><template #default="{ row }"><StatusTag :status="row.cleanupPending ? 'failed' : (row.isDefault ? 'completed' : row.status)" :label="modelStatusLabel(row)" /><el-tooltip v-if="row.cleanupPending && row.cleanupError" :content="row.cleanupError"><el-icon class="cleanup-warning"><WarningFilled /></el-icon></el-tooltip></template></el-table-column>
        <el-table-column :label="text.createdAt" min-width="180"><template #default="{ row }">{{ formatDate(row.createdAt) }}</template></el-table-column>
        <el-table-column :label="text.actions" width="260"><template #default="{ row }"><el-button v-if="!row.cleanupPending" link type="primary" @click="downloadModel(row)">{{ text.download }}</el-button><el-button v-if="row.status !== 'deleted' && !row.isDefault && !row.cleanupPending" link type="primary" @click="setDefaultModel(row)">{{ text.setDefault }}</el-button><el-button v-if="row.cleanupPending && canDelete(row)" link type="warning" @click="retryModelCleanup(row)">{{ settingsStore.isEnglish ? 'Retry cleanup' : '重试清理' }}</el-button><el-button v-if="row.status !== 'deleted' && !row.isDefault && canDelete(row)" link type="danger" @click="deleteModel(row)">{{ text.delete }}</el-button></template></el-table-column>
      </el-table>
      <el-empty v-if="!loading && !models.length" :description="text.noModels" />
    </el-card>
    <el-dialog v-model="modelUploadVisible" :title="text.uploadModel" width="480px"><el-form :model="modelUpload" label-position="top"><el-form-item :label="text.scene"><el-select v-model="modelUpload.sceneId" class="full-width"><el-option v-for="scene in scenes" :key="scene.id" :label="scene.displayName" :value="scene.id" /></el-select></el-form-item><el-form-item :label="text.version"><el-input v-model="modelUpload.version" /></el-form-item><el-form-item :label="text.model"><el-input v-model="modelUpload.modelName" /></el-form-item><el-form-item label=".pt"><el-upload :auto-upload="false" :limit="1" accept=".pt" :on-change="selectModelFile"><el-button>{{ text.selectFile }}</el-button></el-upload></el-form-item></el-form><template #footer><el-button @click="modelUploadVisible = false">{{ text.cancel }}</el-button><el-button type="primary" :loading="uploading" @click="uploadModel">{{ text.upload }}</el-button></template></el-dialog>
    <el-dialog v-model="datasetEditorVisible" :title="text.editDataset" width="min(480px, 92vw)"><el-form :model="datasetEditor" label-position="top"><el-form-item :label="text.name"><el-input v-model="datasetEditor.displayName" maxlength="200" show-word-limit /></el-form-item><el-form-item :label="text.metadataDescription"><el-input v-model="datasetEditor.description" type="textarea" :rows="4" maxlength="2000" show-word-limit /></el-form-item></el-form><template #footer><el-button @click="datasetEditorVisible = false">{{ text.cancel }}</el-button><el-button type="primary" :loading="savingDatasetMetadata" @click="saveDatasetMetadata">{{ text.save }}</el-button></template></el-dialog>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, WarningFilled } from '@element-plus/icons-vue'
import ModulePageHeader from '@/components/common/ModulePageHeader.vue'
import PageErrorAlert from '@/components/common/PageErrorAlert.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { deleteTrainingDataset, downloadTrainingDataset, getTrainingDatasets, updateTrainingDatasetMetadata, uploadTrainingDataset } from '@/api/training'
import { deleteModelVersionApi, downloadModelVersionApi, getModelsApi, getScenesApi, retryModelCleanupApi, setDefaultModelApi, uploadModelVersionApi } from '@/api/models'
import { getApiErrorMessage } from '@/utils/apiError'
import { useSettingsStore } from '@/stores/settings'
import { useUserStore } from '@/stores/user'
const settingsStore = useSettingsStore(); const userStore = useUserStore(); const loading = ref(false); const uploading = ref(false); const pageError = ref(''); const datasets = ref([]); const models = ref([]); const scenes = ref([]); const modelUploadVisible = ref(false); const modelUpload = ref({ sceneId: '', version: '', modelName: '', file: null }); const datasetEditorVisible = ref(false); const savingDatasetMetadata = ref(false); const datasetEditor = ref({ path: '', displayName: '', description: '' })
const text = computed(() => settingsStore.isEnglish ? { title:'Files', description:'Manage built-in and your own training assets.', refresh:'Refresh', datasets:'Datasets', models:'Model versions', name:'Name', path:'Path', status:'Status', ready:'Ready', incomplete:'Incomplete', noDatasets:'No training datasets are available', noModels:'No model versions are available', scene:'Scene', version:'Version', model:'Model', map50:'mAP@50', default:'Default', createdAt:'Created at', actions:'Actions', setDefault:'Set default', download:'Download', edit:'Edit', editDataset:'Edit dataset metadata', metadataDescription:'Description', save:'Save', delete:'Delete', deleteConfirm:'This operation cannot be undone. Continue?', deleteTitle:'Confirm deletion', deleted:'Deleted', loadFailed:'Failed to load files', actionFailed:'File operation failed', uploadDataset:'Upload dataset', uploadModel:'Upload model', upload:'Upload', selectFile:'Select file', cancel:'Cancel' } : { title:'文件查看', description:'统一查看内置和个人训练资产。', refresh:'刷新', datasets:'数据集', models:'模型版本', name:'名称', path:'路径', status:'状态', ready:'可用', incomplete:'未完成', noDatasets:'暂无训练数据集', noModels:'暂无模型版本', scene:'场景', version:'版本', model:'模型', map50:'mAP@50', default:'默认模型', createdAt:'创建时间', actions:'操作', setDefault:'设为默认', download:'下载', edit:'编辑', editDataset:'编辑数据集元数据', metadataDescription:'描述', save:'保存', delete:'删除', deleteConfirm:'删除后不可恢复，是否继续？', deleteTitle:'确认删除', deleted:'已删除', loadFailed:'文件列表加载失败', actionFailed:'文件操作失败', uploadDataset:'上传数据集', uploadModel:'上传模型', upload:'上传', selectFile:'选择文件', cancel:'取消' })
const canDelete = (asset) => !asset.isBuiltin && (userStore.isSuperuser || Number(asset.ownerId ?? asset.owner_id) === Number(userStore.user?.id))
const modelStatusLabel = (model) => model.cleanupPending ? (settingsStore.isEnglish ? 'Cleanup pending' : '待清理重试') : (model.isDefault ? text.value.default : model.status)
const formatPercent = (value) => Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(2)}%` : '-'
const formatDate = (value) => !value ? '-' : new Date(value).toLocaleString(settingsStore.isEnglish ? 'en-US' : 'zh-CN', { hour12:false })
function saveBlob(blob, filename) { const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url) }
async function loadAssets() { loading.value=true; pageError.value=''; try { const [data, sceneItems] = await Promise.all([getTrainingDatasets(), getScenesApi()]); datasets.value=data?.items ?? data ?? []; scenes.value=sceneItems; models.value=(await Promise.all(sceneItems.map(async scene => (await getModelsApi(scene.id)).map(model => ({...model, sceneId:scene.id, sceneName:scene.displayName || scene.name}))))).flat() } catch(error) { pageError.value=getApiErrorMessage(error,text.value.loadFailed) } finally { loading.value=false } }
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
<style lang="scss" scoped>.asset-card { margin-bottom: 18px; }.card-title { font-weight: 600; color: var(--app-text); }.full-width { width: 100%; }.cleanup-warning { margin-left: 6px; color: var(--el-color-warning); vertical-align: middle; }</style>
