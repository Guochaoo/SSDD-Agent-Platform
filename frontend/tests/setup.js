/**
 * Vitest 全局 setup
 * 在每个测试文件执行前自动运行
 */

// Node.js v22+ 自带实验性 localStorage，会覆盖 happy-dom 的实现
// 但 Node.js 的版本需要 --localstorage-file 参数才能工作，导致
// localStorage 为 undefined。这里手动提供一个内存实现。
if (typeof globalThis.localStorage === "undefined") {
  const _store = {}
  globalThis.localStorage = {
    getItem: (key) => _store[key] ?? null,
    setItem: (key, value) => { _store[key] = String(value) },
    removeItem: (key) => { delete _store[key] },
    clear: () => { Object.keys(_store).forEach(k => delete _store[k]) },
    get length() { return Object.keys(_store).length },
    key: (i) => Object.keys(_store)[i] ?? null,
  }
}

// 模拟 Element Plus 的 ElMessage（避免测试中弹出消息框）
import { vi } from "vitest";

vi.mock("element-plus", async () => {
  const actual = await vi.importActual("element-plus");
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
  };
});
