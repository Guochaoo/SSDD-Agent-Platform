import { createApp } from 'vue'

import '@/assets/styles/global.scss'

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import pinia from './stores'
import { setupErrorReporting } from '@/utils/errorReporter'

const app = createApp(App)
app.use(pinia)
app.use(router)
app.use(ElementPlus)
setupErrorReporting(app)

app.mount('#app')
