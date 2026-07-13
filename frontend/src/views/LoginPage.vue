<template>
  <div class="login-page">
    <div class="login-wrapper">
      <!-- Left — Silk brand panel -->
      <div class="login-left">
        <div class="silk-bg">
          <SilkCanvas :speed="6.5" :scale="0.8" color="#1f1f1f" :noise-intensity="0" :rotation="0" />
        </div>
        <div class="silk-overlay" />
        <router-link to="/" class="back-link left-back">
          <el-icon><ArrowLeft /></el-icon>
          返回首页
        </router-link>

        <div class="brand-text">
          <h2>
            让AI
            <br />
            看见缺陷。
          </h2>
          <p>
            钢铁表面缺陷检测智能体平台
            <br />
            基于 YOLOv11，智能识别与训练一站式。
          </p>
        </div>
      </div>

      <!-- Right — login form -->
      <div class="login-right">
        <div class="form-container">
          <router-link to="/" class="back-link mobile-back">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </router-link>

          <div class="form-header">
            <h1>登录</h1>
            <p>输入账号与密码继续。</p>
          </div>

          <el-form
            ref="formRef"
            :model="loginForm"
            :rules="loginRules"
            label-width="0"
            @submit.prevent="handleLogin"
          >
            <el-form-item prop="username">
              <label class="field-label">用户名</label>
              <el-input
                v-model="loginForm.username"
                placeholder="输入您的用户名"
                :prefix-icon="User"
                autofocus
                autocomplete="username"
              />
            </el-form-item>

            <el-form-item prop="password">
              <label class="field-label">密码</label>
              <div class="pwd-wrap">
                <el-input
                  v-model="loginForm.password"
                  :type="showPwd ? 'text' : 'password'"
                  placeholder="••••••••"
                  :prefix-icon="Lock"
                  autocomplete="current-password"
                  @keyup.enter="handleLogin"
                />
                <button
                  type="button"
                  class="pwd-toggle"
                  :aria-label="showPwd ? '隐藏密码' : '显示密码'"
                  @click="showPwd = !showPwd"
                >
                  <el-icon><Hide v-if="showPwd" /><View v-else /></el-icon>
                </button>
              </div>
            </el-form-item>

            <div v-if="errorMsg" class="error-banner">
              {{ errorMsg }}
            </div>

            <el-button
              type="primary"
              class="submit-btn"
              :loading="loading"
              @click="handleLogin"
            >
              {{ loading ? '登录中…' : '登录' }}
            </el-button>
          </el-form>

          <div class="form-footer">
            <span>还没有账号？</span>
            <router-link to="/register">立即注册</router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, View, Hide, ArrowLeft } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import SilkCanvas from '@/components/SilkCanvas.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const showPwd = ref(false)
const errorMsg = ref('')

const loginForm = reactive({
  username: '',
  password: '',
})

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名需要 3-50 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少需要 6 个字符', trigger: 'blur' },
  ],
}

async function handleLogin() {
  errorMsg.value = ''
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.login({
      username: loginForm.username,
      password: loginForm.password,
    })

    ElMessage.success('登录成功')
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch (err) {
    const data = err?.response?.data
    errorMsg.value = data?.detail || data?.error || '登录失败，请检查账号或密码'
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f2f2f2;
  padding: 12px;
}

.login-wrapper {
  width: 100%;
  max-width: 1100px;
  display: grid;
  align-items: stretch;
  overflow: hidden;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 32px rgba(0, 0, 0, 0.15);
  min-height: 640px;
  grid-template-columns: 1.15fr 1fr;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
    min-height: auto;
    max-width: 420px;
  }
}

/* ── Left panel ── */
.login-left {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 48px;
  overflow: hidden;

  @media (max-width: 768px) {
    display: none;
  }
}

.silk-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.silk-overlay {
  pointer-events: none;
  position: absolute;
  inset: 0;
  z-index: 1;
  background: linear-gradient(to bottom right, rgba(0, 0, 0, 0.2) 0%, transparent 50%, rgba(0, 0, 0, 0.4) 100%);
}

.back-link {
  position: relative;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: fit-content;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  text-decoration: none;
  transition: color 0.2s;

  &:hover {
    color: #fff;
  }
}

.brand-text {
  position: relative;
  z-index: 2;
  color: #fff;

  h2 {
    font-size: 40px;
    font-weight: 600;
    line-height: 1.1;
    letter-spacing: -0.5px;
    margin: 0;
  }

  p {
    margin-top: 16px;
    max-width: 320px;
    font-size: 14px;
    line-height: 1.65;
    color: rgba(255, 255, 255, 0.65);
  }
}

/* ── Right panel ── */
.login-right {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  padding: 24px;

  @media (min-width: 769px) {
    padding: 56px;
  }
}

.form-container {
  width: 100%;
  max-width: 360px;
}

.mobile-back {
  margin-bottom: 24px;
  color: #737373;
  font-size: 14px;

  &:hover {
    color: #171717;
  }

  @media (min-width: 769px) {
    display: none;
  }
}

.form-header {
  margin-bottom: 28px;

  h1 {
    font-size: 26px;
    font-weight: 600;
    line-height: 1.2;
    letter-spacing: -0.3px;
    color: #171717;
    margin: 0;
  }

  p {
    margin-top: 8px;
    font-size: 14px;
    color: #737373;
  }
}

.field-label {
  display: block;
  width: 100%;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #404040;
}

:deep(.el-form-item) {
  margin-bottom: 20px;

  .el-form-item__content {
    flex-direction: column;
    flex-wrap: nowrap;
  }
}

:deep(.el-form-item__content > *) {
  width: 100%;
}

:deep(.el-input) {
  --el-input-bg-color: #f1f1f0;
  --el-input-border-color: transparent;
  --el-input-hover-border-color: transparent;
  --el-input-focus-border-color: transparent;
  --el-input-placeholder-color: #a3a3a3;

  .el-input__wrapper {
    border-radius: 10px;
    padding-left: 14px;
    padding-right: 14px;
    padding-top: 6px;
    padding-bottom: 6px;
    background: #f1f1f0;
    box-shadow: none;
    transition: background 0.2s, box-shadow 0.2s;

    &:hover {
      background: #ebebea;
    }

    &.is-focus {
      background: #e7e7e6;
      box-shadow: 0 0 0 1px #8F8AB0;
    }
  }

  .el-input__inner {
    color: #171717;
    font-size: 14px;

    &::placeholder {
      color: #a3a3a3;
    }
  }

  .el-input__prefix-inner {
    color: #a3a3a3;
  }
}

.pwd-wrap {
  position: relative;

  .pwd-toggle {
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    z-index: 2;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: 0;
    background: transparent;
    color: #a3a3a3;
    cursor: pointer;
    font-size: 16px;
    padding: 0;

    &:hover {
      color: #404040;
    }
  }

  :deep(.el-input .el-input__wrapper) {
    padding-right: 42px;
  }
}

.error-banner {
  border-radius: 10px;
  border: 1px solid #d5d1e6;
  background: #f3f2f8;
  padding: 10px 14px;
  margin-bottom: 16px;
  font-size: 14px;
  color: #8F8AB0;
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
  border-radius: 10px;
  padding-top: 12px;
  padding-bottom: 12px;
  background: #171717;
  border-color: #171717;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  transition: background 0.2s;

  &:hover:not(:disabled) {
    background: #262626;
    border-color: #262626;
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.form-footer {
  margin-top: 28px;
  font-size: 13px;
  color: #a3a3a3;

  a {
    color: #171717;
    margin-left: 4px;
    font-weight: 500;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }
}
</style>
