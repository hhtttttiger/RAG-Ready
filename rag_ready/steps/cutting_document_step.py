from __future__ import annotations

from typing import Any

from loguru import logger

from ..models.document_model import DocumentChunkInfo
from ..chainsaw.chainsaw_factory import ChainsawFactory
from .pipeline_base import PipelineStep


class CuttingDocumentStep(PipelineStep):
    def execute(self) -> None:
        file_info = self.context.file_mes
        doc_info = self.context.doc_mes
        config = self.context.config

        if file_info is None or doc_info is None:
            raise ValueError("chainsaw_missing_context")

        chunk_size = config.chunk_size
        overlap = config.overlap
        file_type = getattr(file_info, "extension", "") or ""
        chainsaw_name = config.chainsaw or "default"

        texts: list[dict[str, Any]] = []
        if doc_info.use_chainsaw:
            chainsaw = ChainsawFactory(chunk_size, overlap, file_info=file_info).get_chainsaw(
                chainsaw_name=chainsaw_name,
                file_type=file_type,
            )
            parts = chainsaw.split_text(doc_info)
            for idx, text in enumerate(parts):
                texts.append({"text": text, "metadata": {"part": idx}})
        else:
            page_list = getattr(doc_info, "page_list", []) or []
            for page in page_list:
                page_text = getattr(page, "content", "") or ""
                metadata = getattr(page, "metadata", {}) or {}
                texts.append({"text": page_text, "metadata": metadata})

        segments: list[DocumentChunkInfo] = []
        for i, item in enumerate(texts):
            segments.append(
                DocumentChunkInfo(
                    text=item["text"],
                    metadata=item.get("metadata", {}) or {},
                )
            )

        self.context.chunk_list = segments

        logger.info(f"segments_ready: {len(segments)}")

