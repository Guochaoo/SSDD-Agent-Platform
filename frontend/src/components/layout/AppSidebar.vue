<template>
  <aside :class="['app-sidebar', { collapsed }]">
    <!-- Header: brand -->
    <div class="sidebar-header">
      <img src="/favicon.svg" alt="logo" class="brand-logo" />
      <span v-show="!collapsed" class="brand-text">RSOD</span>
    </div>

    <!-- Body: navigation -->
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

    <!-- Footer: user menu -->
    <div class="sidebar-footer">
      <el-dropdown trigger="click" placement="right-start" @command="handleCommand">
        <div class="user-btn">
          <el-avatar :size="28" :src="userStore.avatar || undefined" class="user-avatar">
            {{ userStore.username?.charAt(0)?.toUpperCase() }}
          </el-avatar>
          <span v-show="!collapsed" class="user-name">{{ userStore.username }}</span>
          <el-icon v-show="!collapsed" class="user-chevron"><ArrowDown /></el-icon>
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
import {
  Camera, ChatDotRound, Clock, Cpu, DataAnalysis,
  ArrowDown, SwitchButton,
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

defineProps({
  collapsed: { type: Boolean, default: false },
})

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => '/' + route.path.split('/')[1])

const menuItems = [
  { path: '/chat',       title: '智能对话',   icon: ChatDotRound },
  { path: '/detection',  title: '检测工作台', icon: Camera },
  { path: '/training',   title: '模型训练',   icon: Cpu },
  { path: '/history',    title: '历史记录',   icon: Clock },
  { path: '/dashboard',  title: '数据看板',   icon: DataAnalysis },
]

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
  background: #1a1a1c;
  display: flex;
  flex-direction: column;
  transition: width 0.28s cubic-bezier(0.22, 1, 0.36, 1);
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
  height: 56px;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  flex-shrink: 0;
}

.brand-logo {
  width: 28px; height: 28px;
  flex-shrink: 0;
}

.brand-text {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  letter-spacing: -0.3px;
}

/* ── Nav ── */
.sidebar-nav {
  flex: 1;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 38px;
  padding: 0 12px;
  border-radius: 8px;
  color: rgba(255,255,255,0.5);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s;
  white-space: nowrap;
  overflow: hidden;
  position: relative;

  &:hover {
    color: rgba(255,255,255,0.85);
    background: rgba(255,255,255,0.06);
  }

  &.active {
    color: #fff;
    background: rgba(143,138,176,0.25);

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
  background: rgba(143,138,176,0.35);
  color: #cfcbe6;
  min-width: 18px; height: 18px;
  line-height: 18px;
  text-align: center;
  border-radius: 9px;
  padding: 0 5px;
  flex-shrink: 0;
}

/* ── Footer ── */
.sidebar-footer {
  border-top: 1px solid rgba(255,255,255,0.06);
  padding: 8px;
  flex-shrink: 0;
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  overflow: hidden;

  &:hover {
    background: rgba(255,255,255,0.06);
  }
}

.user-avatar {
  flex-shrink: 0;
}

.user-name {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: rgba(255,255,255,0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-chevron {
  font-size: 12px;
  color: rgba(255,255,255,0.35);
  flex-shrink: 0;
}
</style>
