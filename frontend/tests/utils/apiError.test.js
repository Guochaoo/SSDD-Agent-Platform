import { describe, expect, it } from "vitest";
import { getApiErrorMessage } from "@/utils/apiError";

describe("API 错误提示", () => {
  it.each([
    [401, "登录状态已失效，请重新登录"],
    [403, "当前账号没有权限访问此数据"],
    [404, "请求的数据不存在或已被删除"],
    [500, "后端服务暂时异常，请稍后重试"],
  ])("将 HTTP %s 转换为用户可理解的提示", (status, expected) => {
    expect(getApiErrorMessage({ response: { status } })).toBe(expected);
  });

  it("优先展示后端参数校验详情", () => {
    const error = {
      response: {
        status: 422,
        data: { detail: [{ msg: "模型 ID 无效" }] },
      },
    };
    expect(getApiErrorMessage(error)).toBe("模型 ID 无效");
  });

  it("区分请求超时和后端无法连接", () => {
    expect(getApiErrorMessage({ code: "ECONNABORTED" })).toBe(
      "请求超时，请稍后重试",
    );
    expect(getApiErrorMessage({ request: {} })).toBe(
      "无法连接后端服务，请确认服务已启动",
    );
  });
});
