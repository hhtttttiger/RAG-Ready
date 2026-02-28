from __future__ import annotations

from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..models.document_model import DocumentInfo
from .chainsaw_man import ChainsawMan


class RecursiveCharacterText(ChainsawMan):
    def split_text(self, doc_info: DocumentInfo) -> List[str]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        return splitter.split_text(doc_info.content or "")

