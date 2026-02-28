from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .ai.azure_openai_vision_client import AzureOpenAIVisionClient
    from .models.document_model import DocumentInfo, DocumentChunkInfo
    from .models.model import FileMessage


@dataclass
class PipelineConfig:
    chunk_size: int = 1024
    overlap: int = 0
    parser: str | None = None
    extractor: str | None = None
    chainsaw: str | None = None
    parser_kwargs: dict | None = None


@dataclass
class PipelineContext:
    input_path: str
    output_dir: str

    config: PipelineConfig = field(default_factory=PipelineConfig)

    success: bool = True
    should_continue: bool = True

    current_step: str | None = None

    file_mes: FileMessage | None = None
    doc_mes: DocumentInfo | None = None
    chunk_list: list[DocumentChunkInfo] | None = None
    is_md: bool = False
    ai_settings: dict[str, Any] | None = None
    ai_client: AzureOpenAIVisionClient | None = None
