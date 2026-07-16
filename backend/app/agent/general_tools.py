"""
General Agent 工具 — 知识库检索 / 通用问答

用于处理非检测类的一般性问题，如概念解释、使用帮助等。
"""

from langchain_core.tools import tool


def _make_general_tools():
    """创建 General Agent 工具"""

    @tool
    def search_knowledge(query: str) -> str:
        """
        搜索知识库。用于回答用户关于缺陷类型、检测原理、模型参数等一般性问题。

        Args:
            query: 搜索关键词或问题

        Returns:
            知识库检索结果（当前为预留接口）
        """
        # 预留：后续接入 RAG embedding 搜索
        # from app.services.knowledge_service import knowledge_service
        # results = knowledge_service.search_similar_chunks(...)
        return (
            "知识库功能正在建设中。当前可以回答的问题包括：\n"
            "1. 如何使用检测功能（单图/批量/ZIP 上传）\n"
            "2. 模型训练的基本流程\n"
            "3. 置信度(confidence)和 IoU 的含义\n"
            "4. 各类缺陷（划痕、凹坑、锈斑等）的说明\n\n"
            f"您的问题：{query}"
        )

    return [search_knowledge]
