from __future__ import annotations

import base64
from dataclasses import dataclass


@dataclass(frozen=True)
class AzureOpenAIVisionConfig:
    endpoint: str
    key: str
    deployment: str
    api_version: str
    temperature: float = 0.0


class AzureOpenAIVisionClient:
    def __init__(self, config: AzureOpenAIVisionConfig) -> None:
        self.config = config
        try:
            from langchain_openai import AzureChatOpenAI
        except Exception as e:
            raise Exception(f"aoai_deps_missing: {e}")

        self.llm = AzureChatOpenAI(
            azure_endpoint=config.endpoint,
            api_key=config.key,
            azure_deployment=config.deployment,
            api_version=config.api_version,
            temperature=config.temperature,
        )

    def describe_image(self, image_bytes: bytes, hint: str = "") -> str:
        try:
            from langchain_core.messages import HumanMessage
        except Exception as e:
            raise Exception(f"langchain_core_missing: {e}")

        b64 = base64.b64encode(image_bytes).decode("ascii")
        prompt = (
            "请识别图片内容，输出一句中文描述（不超过40字），尽量包含关键信息。"
            "只返回纯文本，不要加引号，不要输出 Markdown。"
        )
        hint = (hint or "").strip()
        if hint:
            prompt = f"{prompt}\n\n已知上下文（可选）：{hint}"

        msg = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]
        )
        resp = self.llm.invoke([msg])
        text = getattr(resp, "content", "") or ""
        return str(text).strip()

