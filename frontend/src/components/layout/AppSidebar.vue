<template>
  <aside :class="['app-sidebar', { collapsed, 'hover-locked': hoverLocked }]">
    <!-- Header: brand + toggle -->
    <div class="sidebar-header">
      <img src="/favicon.svg" alt="logo" class="brand-logo" />
      <span class="brand-text">SSDD</span>
      <button class="toggle-btn" :title="collapsed ? text.expandSidebar : text.collapseSidebar" @click="handleToggle">
        <DockLeft class="toggle-icon" />
      </button>
    </div>

    <!-- Body: navigation + sessions -->
    <div class="sidebar-body">
      <nav class="sidebar-nav">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          :class="['nav-item', { active: activeMenu === item.path }]"
          :title="collapsed ? item.title : ''"
        >
          <el-icon class="nav-icon">
            <component :is="item.icon" />
          </el-icon>
          <span v-show="!collapsed" class="nav-label">{{ item.title }}</span>
          <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
        </router-link>
      </nav>

      <!-- Sessions section (chat history) -->
      <div v-show="!collapsed" class="sidebar-sessions">
        <div class="sessions-header">
          <span>{{ text.chatHistory }}</span>
          <button class="sessions-new-btn" :title="text.newChat" @click="handleNewChat">
            <Plus />
          </button>
        </div>
        <div class="sessions-list">
          <div v-if="!agentStore.sessions.length" class="sessions-empty">
            {{ text.noSessions }}
          </div>
          <div
            v-for="session in agentStore.sessions"
            :key="session.id"
            :class="['session-item', { active: session.id === agentStore.currentSessionId && activeMenu === '/chat' }]"
            @click="handleSwitchSession(session.id)"
          >
            <span class="session-title">
              <template v-if="userStore.isSuperuser && session.ownerUsername">[{{ session.ownerUsername }}] </template>{{ session.title || text.newChat }}
            </span>
            <span
              v-if="!userStore.isSuperuser || session.ownerId === userStore.user?.id"
              class="session-delete"
              :title="text.delete"
              @click.stop="handleDeleteSession(session.id)"
            >
              <Trash />
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer: user menu -->
    <div class="sidebar-footer">
      <el-dropdown trigger="click" placement="top-start" :offset="0" :hide-timeout="0" popper-class="user-dropdown" @command="handleCommand">
        <div class="user-btn">
          <el-avatar :size="24" :src="userStore.avatar || undefined" class="user-avatar">
            {{ userStore.username?.charAt(0)?.toUpperCase() }}
          </el-avatar>
          <span v-show="!collapsed" class="user-name">{{ userStore.username }}</span>
          <ChevronsUpDown v-show="!collapsed" class="user-chevron" />
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="settings">
              <el-icon><Setting /></el-icon>{{ text.settings }}
            </el-dropdown-item>
            <el-dropdown-item command="logout">
              <el-icon><SwitchButton /></el-icon>{{ text.logout }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <SettingsModal v-model="settingsVisible" @closed="restoreSettingsFocus" />
  </aside>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useAgentStore } from '@/stores/agent'
import { useSettingsStore } from '@/stores/settings'
import { Setting, SwitchButton } from '@element-plus/icons-vue'
import { ChevronsUpDown, MessageCircleDetail, Capture, Computer, History, ChartTrend, Plus, Trash, DockLeft, Folder } from '@boxicons/vue'
import { ElMessageBox } from 'element-plus'
import SettingsModal from '@/components/settings/SettingsModal.vue'

const props = defineProps({
  collapsed: { type: Boolean, default: false },
})

const emit = defineEmits(['update:collapsed'])

const hoverLocked = ref(false)
const settingsVisible = ref(false)
const settingsReturnTarget = ref(null)
let hoverLockTimer = null

function handleToggle() {
  emit('update:collapsed', !props.collapsed)
  hoverLocked.value = true
  clearTimeout(hoverLockTimer)
  hoverLockTimer = setTimeout(() => { hoverLocked.value = false }, 300)
}

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const agentStore = useAgentStore()
const settingsStore = useSettingsStore()

onMounted(() => {
  agentStore.fetchSessions(userStore.user?.id).catch(() => {})
})

const activeMenu = computed(() => '/' + route.path.split('/')[1])

const text = computed(() => settingsStore.isEnglish ? {
  expandSidebar: 'Expand sidebar',
  collapseSidebar: 'Collapse sidebar',
  chat: 'Chat',
  detection: 'Detection',
  training: 'Training',
  files: 'Files',
  history: 'History',
  dashboard: 'Dashboard',
  chatHistory: 'Chats',
  newChat: 'New chat',
  noSessions: 'No chats',
  delete: 'Delete',
  settings: 'Settings',
  logout: 'Log out',
  logoutTitle: 'Confirm',
  logoutMessage: 'Are you sure you want to log out?',
  confirm: 'Confirm',
  cancel: 'Cancel',
} : {
  expandSidebar: '展开侧栏',
  collapseSidebar: '收起侧栏',
  chat: '智能对话',
  detection: '检测工作台',
  training: '模型训练',
  files: '文件查看',
  history: '历史记录',
  dashboard: '数据看板',
  chatHistory: '会话历史',
  newChat: '新对话',
  noSessions: '暂无会话',
  delete: '删除',
  settings: '设置',
  logout: '退出登录',
  logoutTitle: '提示',
  logoutMessage: '确定要退出登录吗？',
  confirm: '确定',
  cancel: '取消',
})

const menuItems = computed(() => [
  { path: '/chat', title: text.value.chat, icon: MessageCircleDetail },
  { path: '/detection', title: text.value.detection, icon: Capture },
  { path: '/training', title: text.value.training, icon: Computer },
  { path: '/files', title: text.value.files, icon: Folder },
  { path: '/history', title: text.value.history, icon: History },
  { path: '/dashboard', title: text.value.dashboard, icon: ChartTrend },
])

function handleNewChat() {
  agentStore.saveSession()
  agentStore.newChat()
  if (route.path !== '/chat') router.push('/chat')
}

function handleSwitchSession(id) {
  agentStore.saveSession()
  agentStore.loadSession(id)
  if (route.path !== '/chat') router.push('/chat')
}

async function handleDeleteSession(id) {
  try {
    await agentStore.deleteSession(id)
  } catch {
    agentStore.fetchSessions().catch(() => {})
  }
}

function handleCommand(command) {
  if (command === 'settings') {
    settingsReturnTarget.value = document.activeElement
    settingsVisible.value = true
    return
  }

  if (command === 'logout') {
    ElMessageBox.confirm(text.value.logoutMessage, text.value.logoutTitle, {
      confirmButtonText: text.value.confirm, cancelButtonText: text.value.cancel, type: 'warning',
    }).then(() => {
      agentStore.clearUserScope()
      userStore.logout()
      router.push('/login')
    }).catch(() => {})
  }
}

function restoreSettingsFocus() {
  nextTick(() => {
    settingsReturnTarget.value?.focus?.()
    settingsReturnTarget.value = null
  })
}
</script>

<style lang="scss" scoped>
.app-sidebar {
  position: sticky;
  top: 0;
  width: $sidebar-width;
  height: 100vh;
  background: var(--app-sidebar-bg);
  border-right: 1px solid var(--app-border);
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease;
  overflow: hidden;
  flex-shrink: 0;

  &.collapsed {
    width: $sidebar-collapsed-width;
  }
}

/* ── Header ── */
.sidebar-header {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 52px;
  padding: 0 16px;
  flex-shrink: 0;
  position: relative;
}

.brand-logo {
  width: 26px; height: 26px;
  flex-shrink: 0;
  transition: opacity 0.15s;
}

.brand-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--app-text);
  white-space: nowrap;
  flex: 1;
  opacity: 1;
}

.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px; height: 20px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #6e6e6e;
  cursor: pointer;
  flex-shrink: 0;
  opacity: 1;
  transition: opacity 0.12s;
  padding: 0;

  &:hover {
    color: var(--app-text);
    background: var(--app-hover);
  }
}

.toggle-icon {
  width: 20px; height: 20px;
}

/* ── Collapsed state header ── */
.collapsed.hover-locked:hover .brand-logo { opacity: 1; }
.collapsed.hover-locked:hover .toggle-btn { opacity: 0; }

.collapsed .sidebar-header {
  justify-content: flex-start;
  padding: 0 18px;
}

.collapsed .sidebar-header > * {
  position: absolute;
}

.collapsed .brand-text {
  opacity: 0;
  pointer-events: none;
}

.collapsed .brand-logo {
  opacity: 1;
  left: 16px;
}

.collapsed .toggle-btn {
  opacity: 0;
  transition: opacity 0s;
}

.collapsed:hover .brand-logo {
  opacity: 0;
  transition: opacity 0s;
}

.collapsed:hover .toggle-btn {
  opacity: 1;
  transition: opacity 0s 0s;
}

/* ── Body (nav + sessions) ── */
.sidebar-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  min-height: 0;
}

/* ── Nav ── */
.sidebar-nav {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex-shrink: 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 6px 10px;
  border-radius: 10px;
  color: var(--app-text);
  text-decoration: none;
  font-size: 14px;
  font-weight: 400;
  transition: all 0.15s ease;
  white-space: nowrap;
  overflow: hidden;
  position: relative;

  &:hover {
    background: var(--app-hover);
  }

  &.active {
    font-weight: 500;
    background: var(--app-active);

    &::before {
      content: '';
      position: absolute;
      left: 0; top: 50%;
      transform: translateY(-50%);
      width: 3px; height: 18px;
      border-radius: 0 3px 3px 0;
      background: #8F8AB0;
    }
  }
}

.nav-icon {
  font-size: 20px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
}

.nav-label {
  flex: 1;
  min-width: 0;
}

.nav-badge {
  font-size: 11px;
  background: rgba(143,138,176,0.18);
  color: #6b6390;
  min-width: 18px; height: 18px;
  line-height: 18px;
  text-align: center;
  border-radius: 9px;
  padding: 0 5px;
  flex-shrink: 0;
}

/* ── Sessions ── */
.sidebar-sessions {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 0 8px 8px;
  overflow: hidden;
  white-space: nowrap;
}

.sessions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 10px 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--app-text);
  flex-shrink: 0;
}

.sessions-new-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px; height: 28px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #6e6e6e;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    color: var(--app-text);
    background: var(--app-hover);
  }

  svg {
    width: 16px; height: 16px;
  }
}

.sessions-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.sessions-empty {
  padding: 16px 14px;
  font-size: 13px;
  color: #b0b0b0;
  text-align: center;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 6px 10px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--app-text);
  cursor: pointer;
  text-align: left;
  font-size: 14px;
  font-weight: 400;
  transition: all 0.1s ease;
  gap: 6px;

  &:hover {
    background: var(--app-hover);
  }

  &.active {
    background: var(--app-active);
    font-weight: 500;
  }
}

.session-title {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-delete {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px; height: 20px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: rgba(0,0,0,0.15);
  cursor: pointer;
  flex-shrink: 0;
  opacity: 0;
  transition: all 0.15s;
  padding: 0;

  svg {
    width: 12px; height: 12px;
  }

  .session-item:hover & {
    opacity: 1;
  }

  &:hover {
    color: #f56c6c;
    background: rgba(245,108,108,0.15);
  }
}

/* ── Footer ── */
.sidebar-footer {
  padding: 12px 10px;
  flex-shrink: 0;
  border-top: 1px solid var(--app-border);

  :deep(.el-dropdown) {
    display: block;
    width: 100%;
  }
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s;
  overflow: hidden;

  &:hover {
    background: var(--app-hover);
  }
}

.user-avatar {
  flex-shrink: 0;
}

.user-name {
  flex: 1;
  font-size: 16px;
  font-weight: 400;
  color: var(--app-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-chevron {
  width: 16px; height: 16px;
  color: rgba(0,0,0,0.3);
  flex-shrink: 0;
}

</style>

<!-- Dropdown popper styles (must be unscoped — rendered outside component) -->
<style lang="scss">
.user-dropdown {
  min-width: 0;
  width: calc($sidebar-width - 20px);
  padding: 8px;
  border-radius: 12px;
  border: 1px solid var(--app-border);
  background: var(--app-surface);
  box-shadow: 0 4px 24px rgba(0,0,0,0.08);

  .el-dropdown-menu {
    background: transparent;
  }

  .el-dropdown-menu__item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    border-radius: 10px;
    font-size: 14px;
    color: var(--app-text);
    transition: background 0.1s;

    &:hover {
      background: var(--app-hover);
      color: var(--app-text);
    }

    .el-icon {
      color: currentColor;
    }
  }
}

:root[data-theme='dark'] {
  .user-dropdown.el-popper.is-light {
    background: var(--app-surface);
    border-color: var(--app-border);
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.38);
  }

  .user-dropdown {
    .el-dropdown-menu__item {
      color: var(--app-text);

      &:not(.is-disabled):focus {
        background: var(--app-hover);
        color: var(--app-text);
      }
    }
  }
}

.el-popper.is-light .el-popper__arrow::before {
  display: none;
}
</style>
