from __future__ import annotations

import json

from ..models.document_model import DocumentInfo
from .base_parser import BaseParser


class JsonParser(BaseParser):
    def load(self, file_bytes: bytes, **kwargs) -> DocumentInfo:
        try:
            obj = json.loads(file_bytes.decode("utf-8", errors="ignore"))
            text = json.dumps(obj, ensure_ascii=False, indent=2)
        except Exception:
            text = file_bytes.decode("utf-8", errors="ignore")
        return DocumentInfo(content=text, use_chainsaw=True, is_md=False)

