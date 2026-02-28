from __future__ import annotations

from loguru import logger

from ..parser.parser_factory import ParserFactory
from .pipeline_base import PipelineStep


class ParserDocumentStep(PipelineStep):
    def execute(self) -> None:
        file_info = self.context.file_mes
        if file_info is None:
            raise ValueError("file_info_missing")

        with open(self.context.input_path, "rb") as f:
            file_bytes = f.read()

        config = self.context.config
        parser_name = config.parser or file_info.extension or "txt"
        extractor = config.extractor
        use_extractor = bool(extractor)

        parser = ParserFactory.get_parser(parser_name, extractor=extractor, use_extractor=use_extractor)
        doc_info = parser.load(
            file_bytes=file_bytes,
            file_info=file_info,
            **(config.parser_kwargs or {}),
        )
        self.context.doc_mes = doc_info
        self.context.is_md = bool(getattr(doc_info, "is_md", False))

        logger.info(f"document_parser: use_chainsaw={getattr(doc_info, 'use_chainsaw', True)}")

