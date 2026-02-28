from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from ..context import PipelineContext


@dataclass
class PipelineStep:
    context: PipelineContext

    def execute(self) -> None:
        raise NotImplementedError

    def run(self) -> None:
        self.context.current_step = self.__class__.__name__
        try:
            self.execute()
        except Exception:
            self.context.success = False
            logger.exception("step_failed")
        finally:
            if self.context.current_step == self.__class__.__name__:
                self.context.current_step = None
