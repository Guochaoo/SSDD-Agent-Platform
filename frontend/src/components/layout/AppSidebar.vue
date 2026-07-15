<template>
  <aside :class="['app-sidebar', { collapsed }]">
    <!-- Header: brand + toggle -->
    <div class="sidebar-header">
      <img src="/favicon.svg" alt="logo" class="brand-logo" />
      <span class="brand-text">SSDD</span>
      <button class="toggle-btn" :title="collapsed ? '展开侧栏' : '收起侧栏'" @click="emit('update:collapsed', !collapsed)">
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
          <span>会话历史</span>
          <button class="sessions-new-btn" title="新对话" @click="handleNewChat">
            <Plus />
          </button>
        </div>
        <div class="sessions-list">
          <div v-if="!agentStore.sessions.length" class="sessions-empty">
            暂无会话
          </div>
          <div
            v-for="session in agentStore.sessions"
            :key="session.id"
            :class="['session-item', { active: session.id === agentStore.currentSessionId && activeMenu === '/chat' }]"
            @click="handleSwitchSession(session.id)"
          >
            <span class="session-title">{{ session.title || '新对话' }}</span>
            <span
              class="session-delete"
              title="删除"
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
      <el-dropdown trigger="click" placement="right-start" @command="handleCommand">
        <div class="user-btn">
          <el-avatar :size="28" :src="userStore.avatar || undefined" class="user-avatar">
            {{ userStore.username?.charAt(0)?.toUpperCase() }}
          </el-avatar>
          <span v-show="!collapsed" class="user-name">{{ userStore.username }}</span>
          <ChevronsUpDown v-show="!collapsed" class="user-chevron" />
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">
              <el-icon><SwitchButton /></el-icon>退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useAgentStore } from '@/stores/agent'
import { SwitchButton } from '@element-plus/icons-vue'
import { ChevronsUpDown, MessageCircleDetail, Capture, Computer, History, ChartTrend, Plus, Trash, DockLeft } from '@boxicons/vue'
import { ElMessageBox } from 'element-plus'

const props = defineProps({
  collapsed: { type: Boolean, default: false },
})

const emit = defineEmits(['update:collapsed'])

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const agentStore = useAgentStore()

const activeMenu = computed(() => '/' + route.path.split('/')[1])

const menuItems = [
  { path: '/chat',       title: '智能对话',   icon: MessageCircleDetail },
  { path: '/detection',  title: '检测工作台', icon: Capture },
  { path: '/training',   title: '模型训练',   icon: Computer },
  { path: '/history',    title: '历史记录',   icon: History },
  { path: '/dashboard',  title: '数据看板',   icon: ChartTrend },
]

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

function handleDeleteSession(id) {
  agentStore.deleteSession(id)
}

function handleCommand(command) {
  if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
    }).then(() => {
      userStore.logout()
      router.push('/login')
    }).catch(() => {})
  }
}
</script>

<style lang="scss" scoped>
.app-sidebar {
  position: relative;
  width: $sidebar-width;
  height: 100vh;
  background: #FCFCFC;
  border-right: 1px solid rgba(0,0,0,0.08);
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
  width: 22px; height: 22px;
  flex-shrink: 0;
  transition: opacity 0.2s;
}

.brand-text {
  font-size: 14px;
  font-weight: 600;
  color: #0D0D0D;
  white-space: nowrap;
  flex: 1;
  opacity: 1;
  transition: opacity 0.15s;
}

.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px; height: 30px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: rgba(0,0,0,0.3);
  cursor: pointer;
  flex-shrink: 0;
  opacity: 1;
  transition: opacity 0.15s;
  padding: 0;

  &:hover {
    color: #0D0D0D;
    background: rgba(0,0,0,0.06);
  }
}

.toggle-icon {
  width: 18px; height: 18px;
}

/* ── Collapsed state header ── */
.collapsed .sidebar-header {
  justify-content: center;
  padding: 0;
}

.collapsed .brand-text {
  opacity: 0;
  pointer-events: none;
  position: absolute;
}

.collapsed .brand-logo {
  opacity: 1;
  transition: opacity 0.1s 0.05s;
}

.collapsed .toggle-btn {
  position: absolute;
  opacity: 0;
}

.collapsed:hover .brand-logo {
  opacity: 0;
  transition: opacity 0.08s;
}

.collapsed:hover .toggle-btn {
  opacity: 1;
  transition: opacity 0.12s 0.04s;
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
  gap: 10px;
  height: 40px;
  padding: 0 14px;
  border-radius: 8px;
  color: #6e6e6e;
  text-decoration: none;
  font-size: 14px;
  font-weight: 400;
  transition: all 0.15s ease;
  white-space: nowrap;
  overflow: hidden;
  position: relative;

  &:hover {
    color: #0D0D0D;
    background: rgba(0,0,0,0.04);
  }

  &.active {
    color: #0D0D0D;
    font-weight: 500;
    background: rgba(0,0,0,0.06);

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
  font-size: 18px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
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
}

.sessions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px 8px;
  font-size: 13px;
  font-weight: 600;
  color: #0D0D0D;
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
    color: #0D0D0D;
    background: rgba(0,0,0,0.04);
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
  padding: 8px 14px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #6e6e6e;
  cursor: pointer;
  text-align: left;
  font-size: 14px;
  font-weight: 400;
  transition: all 0.1s ease;
  gap: 6px;

  &:hover {
    background: rgba(0,0,0,0.04);
    color: #0D0D0D;
  }

  &.active {
    background: rgba(0,0,0,0.06);
    color: #0D0D0D;
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
  padding: 8px;
  flex-shrink: 0;
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  overflow: hidden;

  &:hover {
    background: rgba(0,0,0,0.06);
  }
}

.user-avatar {
  flex-shrink: 0;
}

.user-name {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: rgba(0,0,0,0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-chevron {
  width: 20px; height: 20px;
  color: rgba(0,0,0,0.3);
  flex-shrink: 0;
}
</style>
