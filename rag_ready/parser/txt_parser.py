from __future__ import annotations

from ..models.document_model import DocumentInfo
from .base_parser import BaseParser


class TxtParser(BaseParser):
    def load(self, file_bytes: bytes, **kwargs) -> DocumentInfo:
        text = file_bytes.decode("utf-8", errors="ignore")
        return DocumentInfo(content=text, use_chainsaw=True, is_md=False)

