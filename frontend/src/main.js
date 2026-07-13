// src/main.js

import { createApp } from "vue";

// 全局样式
import "@/assets/styles/global.scss";

// 核心模块
import App from "./App.vue";
import router from "./router";
import pinia from "./stores";

// Element Plus
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import zhCn from "element-plus/es/locale/lang/zh-cn";

// 错误监控
import { setupErrorReporting } from "@/utils/errorReporter";

// ── 创建并配置应用 ────────────────────────────────────
const app = createApp(App);

// 注册插件
app.use(pinia);
app.use(router);
app.use(ElementPlus, { locale: zhCn });

// ── 注册全局错误监控（必须在 mount 之前）─────────────
setupErrorReporting(app); // ← 一定要调用，否则 import 被视为未使用

// 挂载到 DOM
app.mount("#app");
