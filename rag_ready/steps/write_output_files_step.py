from __future__ import annotations

import json
import os

from loguru import logger

from ..models.document_model import DocumentChunkInfo
from .pipeline_base import PipelineStep


class WriteOutputFilesStep(PipelineStep):
    def execute(self) -> None:
        segments = self.context.chunk_list
        if not isinstance(segments, list) or not segments:
            raise ValueError("no_segments_to_write")

        os.makedirs(self.context.output_dir, exist_ok=True)

        json_path = os.path.join(self.context.output_dir, "segments.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump([s.model_dump() for s in segments], f, ensure_ascii=False, indent=2)

        md_path = os.path.join(self.context.output_dir, "segments.md")
        with open(md_path, "w", encoding="utf-8") as f:
            self._write_segments_markdown(f, segments)

        logger.info(f"segments_written: {len(segments)}")

    def _write_segments_markdown(self, f, segments: list[DocumentChunkInfo]) -> None:
        pages: dict[int, list[DocumentChunkInfo]] = {}
        has_any_page = False

        for s in segments:
            page = s.metadata.get("page")
            try:
                page_num = int(page)
                has_any_page = True
            except Exception:
                page_num = 1
            pages.setdefault(page_num, []).append(s)

        if not has_any_page:
            pages = {1: segments}

        for page_num in sorted(pages.keys()):
            f.write(f'<!-- PageNumber="{page_num}" -->\n')
            f.write(f"\n## Page {page_num}\n\n")
            for s in pages[page_num]:
                text = (s.text or "").rstrip()
                if text:
                    f.write(text)
                    f.write("\n\n")
            f.write("<!-- PageBreak -->\n\n")

