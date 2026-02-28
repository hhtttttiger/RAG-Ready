from __future__ import annotations

from typing import Dict, Type

from .chainsaw_man import ChainsawMan
from .recursive_character_text import RecursiveCharacterText

FILE_TYPE_CHAINSAW: Dict[str, Type[ChainsawMan]] = {
    "default": RecursiveCharacterText,
    "md": RecursiveCharacterText,
    "doc": RecursiveCharacterText,
    "docx": RecursiveCharacterText,
    "json": RecursiveCharacterText,
    "html": RecursiveCharacterText,
    "htm": RecursiveCharacterText,
    "txt": RecursiveCharacterText,
}


class ChainsawFactory:
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def get_chainsaw(self, chainsaw_name: str, file_type: str) -> ChainsawMan:
        ChainsawClass = FILE_TYPE_CHAINSAW.get(
            file_type,
            FILE_TYPE_CHAINSAW.get(chainsaw_name, RecursiveCharacterText),
        )
        return ChainsawClass(self.chunk_size, self.chunk_overlap, self.file_info)
