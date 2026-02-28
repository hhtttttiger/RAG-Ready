from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..models.document_model import DocumentInfo


class ChainsawMan(ABC):
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @abstractmethod
    def split_text(self, doc_info: DocumentInfo) -> List[str]:
        raise NotImplementedError

