from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.document_model import DocumentInfo


class BaseParser(ABC):
    @abstractmethod
    def load(self, file_bytes: bytes, **kwargs) -> DocumentInfo:
        raise NotImplementedError

