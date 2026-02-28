from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from .context import PipelineContext
from .steps import (
    EnrichImageCaptionsStep,
    InputFileInfoStep,
    ParserDocumentStep,
    CuttingDocumentStep,
    WriteOutputFilesStep,
)


@dataclass
class RagPreprocessPipeline:
    context: PipelineContext

    STEPS = [
        InputFileInfoStep,
        ParserDocumentStep,
        CuttingDocumentStep,
        EnrichImageCaptionsStep,
        WriteOutputFilesStep,
    ]

    def run(self) -> bool:
        for StepClass in self.STEPS:
            step = StepClass(self.context)
            step.run()

            if not self.context.should_continue:
                break
            if not self.context.success:
                break

        logger.info(f"done: success={self.context.success}")
        return self.context.success

