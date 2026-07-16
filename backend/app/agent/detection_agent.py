"""
检测智能体 — ReAct Agent + 检测工具绑定

职责：
  - 创建 LangChain OpenAI Tools Agent
  - 绑定检测工具（单图/批量/ZIP）
  - 提供 chat() 和 chat_stream() 方法，支持动态切换模型

架构：
  用户消息 → Agent（LLM 决策）→ 调用 DetectionTool → 返回结果
"""
import io
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import AsyncGenerator

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.config.settings import settings
from app.core.logger import get_logger
from app.services.detection_service import detection_service

logger = get_logger(__name__)

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "rsod_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}


# ══════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════

def _format_detection_summary(result: dict) -> str:
    if "error" in result:
        return f"检测失败: {result['error']}"
    total = result.get("total_objects", 0)
    inference_time = result.get("inference_time", 0)
    class_counts = result.get("class_counts", {})
    count_lines = "\n".join(f"  - {name}: {count}" for name, count in class_counts.items())
    summary = f"检测完成！共检测到 {total} 个目标，推理耗时 {inference_time}ms。\n"
    if count_lines:
        summary += f"各类别统计:\n{count_lines}"
    return summary


# ══════════════════════════════════════════════════════════════
# 定义 Tool
# ══════════════════════════════════════════════════════════════

@tool
def detect_single_image(image_path: str, conf: float = 0.25, iou: float = 0.45) -> str:
    """
    检测单张图片中的目标物体。用于用户上传了一张图片并要求检测的场景。

    Args:
        image_path: 图片文件路径
        conf: 置信度阈值，取值 0~1，默认 0.25
        iou: NMS IoU 阈值，取值 0~1，默认 0.45

    Returns:
        JSON 字符串，包含 total_objects、class_counts、detections、inference_time
    """
    try:
        result = detection_service._detect_file_sync(image_path, conf=conf, iou=iou)
        summary = _format_detection_summary(result)
        return json.dumps({"summary": summary, "result": result}, ensure_ascii=False)
    except Exception as exc:
        logger.exception("detect_single_image 工具异常")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@tool
def detect_batch_images(image_paths: list[str], conf: float = 0.25) -> str:
    """
    批量检测多张图片。用于用户上传了多张图片或要求批量检测的场景。

    Args:
        image_paths: 图片文件路径列表
        conf: 置信度阈值，默认 0.25

    Returns:
        JSON 字符串，汇总各类别的检测统计
    """
    results = []
    total_objects = 0
    class_counts = {}
    for path in image_paths:
        if not os.path.exists(path):
            results.append({"image": path, "error": "文件不存在"})
            continue
        try:
            r = detection_service._detect_file_sync(path, conf=conf, iou=0.45)
            results.append({"image": path, **r})
            total_objects += r.get("total_objects", 0)
            for name, count in r.get("class_counts", {}).items():
                class_counts[name] = class_counts.get(name, 0) + count
        except Exception as exc:
            results.append({"image": path, "error": str(exc)})

    return json.dumps(
        {"total_images": len(image_paths), "total_objects": total_objects,
         "class_counts": class_counts, "results": results},
        ensure_ascii=False,
    )


@tool
def detect_zip_images_file(zip_path: str, conf: float = 0.25) -> str:
    """
    解压 ZIP 文件并批量检测其中所有图片。
    适用于用户上传 .zip 压缩包（内含多张需要检测的图片）的场景。

    Args:
        zip_path: ZIP 文件在本地的路径
        conf: 置信度阈值，默认 0.25

    Returns:
        JSON 字符串，汇总检测结果
    """
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix="rsod_zip_")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(temp_dir)

        image_files = []
        for root, _, files in os.walk(temp_dir):
            for fname in files:
                if Path(fname).suffix.lower() in IMAGE_EXTENSIONS:
                    image_files.append(os.path.join(root, fname))

        if not image_files:
            return json.dumps({"error": "ZIP 文件内未找到图片"}, ensure_ascii=False)

        batch_result = detect_batch_images.invoke({"image_paths": image_files, "conf": conf})
        return batch_result
    except zipfile.BadZipFile:
        return json.dumps({"error": "无效的 ZIP 文件"}, ensure_ascii=False)
    except Exception as exc:
        logger.exception("detect_zip_images_file 工具异常")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    finally:
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


DETECTION_TOOLS = [detect_single_image, detect_batch_images, detect_zip_images_file]


# ══════════════════════════════════════════════════════════════
# LLM 工厂
# ══════════════════════════════════════════════════════════════

def _make_llm(model: str | None = None):
    """根据 settings 创建 ChatOpenAI 实例。

    Args:
        model: 前端选择的模型名，若为 None 则使用 .env 默认值
    """
    api_key = settings.OPENAI_API_KEY
    base_url = settings.OPENAI_BASE_URL

    if not api_key:
        raise RuntimeError("未配置 OPENAI_API_KEY")

    model_name = model or settings.OPENAI_MODEL
    logger.info("Agent LLM: model=%s base_url=%s", model_name, base_url)
    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0.1,
    )


def _make_executor(llm):
    """用指定 LLM 创建 AgentExecutor"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    agent = create_openai_tools_agent(llm=llm, tools=DETECTION_TOOLS, prompt=prompt)
    return AgentExecutor(
        agent=agent,
        tools=DETECTION_TOOLS,
        verbose=True,
        max_iterations=5,
        return_intermediate_steps=True,
    )


_SYSTEM_PROMPT = """你是一个专业的目标检测助手，可以帮助用户检测图片中的目标物体。

重要规则：
- 当用户消息中包含 [附件图片路径: xxx] 时，xxx 就是服务端的图片路径，你必须直接使用它调用检测工具
- 不要要求用户再次提供路径，直接使用附件中给出的路径
- 单张图片 → 调用 detect_single_image
- 多张图片 → 调用 detect_batch_images
- ZIP 压缩包 → 调用 detect_zip_images_file

工作流程：
1. 理解用户意图
2. 调用对应检测工具
3. 用自然语言总结检测结果

回复要求：
- 先报告检测到的目标总数
- 列出各类别数量统计
- 简洁专业，使用中文"""


class DetectionAgent:
    """检测智能体"""

    def __init__(self):
        self._default_llm = None
        self._default_executor = None
        logger.info("DetectionAgent 初始化完成，绑定 %d 个工具", len(DETECTION_TOOLS))

    @property
    def default_executor(self):
        if self._default_executor is None:
            self._default_llm = _make_llm()
            self._default_executor = _make_executor(self._default_llm)
        return self._default_executor

    def _get_executor(self, model: str | None):
        """根据模型名获取 executor。model=None 时使用默认。"""
        if model is None:
            return self.default_executor
        llm = _make_llm(model)
        return _make_executor(llm)

    async def chat(self, message: str, image_paths: list[str] = None, model: str = None, chat_history: list[dict] | None = None) -> dict:
        if image_paths:
            paths_text = "\n".join(f"[附件图片路径: {p}]" for p in image_paths)
            message = f"{message}\n{paths_text}"
        try:
            executor = self._get_executor(model)
            result = await executor.ainvoke({"input": message, "chat_history": chat_history or []})
            return {
                "output": result["output"],
                "intermediate_steps": result.get("intermediate_steps", []),
            }
        except Exception as exc:
            logger.exception("Agent 执行异常")
            return {"output": f"处理出错：{exc}", "intermediate_steps": []}

    async def chat_stream(self, message: str, image_paths: list[str] = None, model: str = None, chat_history: list[dict] | None = None) -> AsyncGenerator:
        if image_paths:
            paths_text = "\n".join(f"[附件图片路径: {p}]" for p in image_paths)
            message = f"{message}\n{paths_text}"

        executor = self._get_executor(model)
        try:
            async for event in executor.astream_events(
                {"input": message, "chat_history": chat_history or []}, version="v2"
            ):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        yield {"type": "text_chunk", "content": chunk.content}

                elif kind == "on_tool_start":
                    yield {
                        "type": "tool_call",
                        "tool": event["name"],
                        "input": event["data"].get("input", {}),
                    }

                elif kind == "on_tool_end":
                    output = event["data"].get("output", "")
                    yield {
                        "type": "tool_result",
                        "tool": event.get("name", ""),
                        "result": str(output) if output else "",
                    }

        except Exception as exc:
            logger.exception("Agent 流式执行异常")
            yield {"type": "error", "content": f"处理出错：{exc}"}


detection_agent = DetectionAgent()
