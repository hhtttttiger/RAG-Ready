from __future__ import annotations

from ..base_parser import BaseParser
from ...models.document_model import DocumentInfo
from .di_tools import AzureDocumentIntelligenceTools


class AzureDocumentIntelligenceLayoutModeParser(BaseParser):
    def load(self, file_bytes: bytes, **kwargs) -> DocumentInfo:
        doc_info: DocumentInfo = AzureDocumentIntelligenceTools().layout_mode_load(
            file_bytes=file_bytes,
            figures=True,
            **kwargs,
        )
        doc_info.use_chainsaw = False
        return doc_info
