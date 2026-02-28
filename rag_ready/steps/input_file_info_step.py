from __future__ import annotations

import os

from rag_ready.models.model import FileMessage

from .pipeline_base import PipelineStep


class InputFileInfoStep(PipelineStep):
    def execute(self) -> None:
        path = os.path.abspath(self.context.input_path)
        file_info = FileMessage.from_local_path(
            path=path,
        )
        self.context.file_mes = file_info
