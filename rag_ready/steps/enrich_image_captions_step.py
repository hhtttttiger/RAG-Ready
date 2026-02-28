from __future__ import annotations

import os
import re

from loguru import logger

from ..ai.azure_openai_vision_client import AzureOpenAIVisionClient, AzureOpenAIVisionConfig
from .pipeline_base import PipelineStep


IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


class EnrichImageCaptionsStep(PipelineStep):
    def execute(self) -> None:
        segments = self.context.chunk_list
        if not isinstance(segments, list) or not segments:
            return

        if not getattr(self.context, "is_md", False):
            return

        settings = self.context.ai_settings or {}
        if not settings.get("enable_image_caption", False):
            return

        client = self.context.ai_client
        if client is None:
            cfg = AzureOpenAIVisionConfig(
                endpoint=settings.get("aoai_endpoint", ""),
                key=settings.get("aoai_key", ""),
                deployment=settings.get("aoai_deployment", ""),
                api_version=settings.get("aoai_api_version", ""),
                temperature=float(settings.get("aoai_temperature", 0.0)),
            )
            if not cfg.endpoint or not cfg.key or not cfg.deployment or not cfg.api_version:
                raise ValueError("aoai_config_missing")
            client = AzureOpenAIVisionClient(cfg)

        limit = int(settings.get("image_caption_limit", 0) or 0)
        processed: dict[str, str] = {}
        changed = 0
        called = 0

        for seg in segments:
            original = seg.text or ""
            if "![" not in original:
                continue

            def repl(m: re.Match) -> str:
                nonlocal changed, called
                alt = (m.group(1) or "").strip()
                url = (m.group(2) or "").strip()

                if url.startswith("http://") or url.startswith("https://") or url.startswith("data:"):
                    return m.group(0)

                local_path = url
                if not os.path.isabs(local_path):
                    local_path = os.path.abspath(os.path.join(self.context.output_dir, local_path))

                if not os.path.exists(local_path) or os.path.isdir(local_path):
                    return m.group(0)

                cache_key = local_path
                if cache_key in processed:
                    new_alt = processed[cache_key]
                else:
                    if limit > 0 and called >= limit:
                        return m.group(0)
                    with open(local_path, "rb") as f:
                        img_bytes = f.read()
                    new_alt = client.describe_image(img_bytes, hint=alt)
                    new_alt = (new_alt or "").strip()
                    if not new_alt:
                        return m.group(0)
                    new_alt = new_alt.replace("[", "\\[").replace("]", "\\]")
                    processed[cache_key] = new_alt
                    called += 1

                if new_alt != alt:
                    changed += 1
                return f"![{new_alt}]({url})"

            updated = IMAGE_PATTERN.sub(repl, original)
            seg.text = updated

        self.context.chunk_list = segments
        if changed:
            logger.info(f"image_caption_enriched: images_updated={changed} ai_calls={called}")

