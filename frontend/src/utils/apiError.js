export function getApiErrorMessage(error, fallback = "请求失败，请稍后重试") {
  const status = error?.response?.status;
  const detail = error?.response?.data?.detail;
  const errorCode = error?.response?.data?.error_code || detail?.code;
  const message = error?.response?.data?.message || detail?.message;

  if (status === 401) return "登录状态已失效，请重新登录";
  if (errorCode === "CLEANUP_RETRY") return "文件清理失败，状态已记录，请点击重试";
  if (errorCode === "RESOURCE_IN_USE") return message || "资源正在使用，暂时不能删除";
  if (errorCode === "BUILTIN_RESOURCE") return message || "内置资源只读，不能修改";
  if (errorCode === "INVALID_FORMAT") return message || "文件格式不支持";
  if (status === 403) return "当前账号没有权限访问此数据";
  if (status === 404) return "请求的数据不存在或已被删除";
  if (status === 422) {
    if (Array.isArray(detail)) return detail[0]?.msg || "筛选参数不正确";
    return detail || "筛选参数不正确";
  }
  if (status >= 500) return "后端服务暂时异常，请稍后重试";
  if (error?.code === "ECONNABORTED") return "请求超时，请稍后重试";
  if (!error?.response) return "无法连接后端服务，请确认服务已启动";
  return message || (typeof detail === 'string' ? detail : fallback);
}
