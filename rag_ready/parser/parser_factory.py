from __future__ import annotations

from typing import Dict, Type

from .base_parser import BaseParser
from .html_parser import HtmlParser
from .json_parser import JsonParser
from .markdown_parser import MarkdownParser
from .txt_parser import TxtParser

FILE_TYPE_PAESER: Dict[str, Type[BaseParser]] = {
    "txt": TxtParser,
    "md": MarkdownParser,
    "json": JsonParser,
    "html": HtmlParser,
    "htm": HtmlParser,
}


class ParserFactory:
    @staticmethod
    def get_parser(file_type: str, extractor: str = "", use_extractor: bool = False) -> BaseParser:
        parser_key = f"{file_type}_{extractor}" if use_extractor else file_type
        if use_extractor and extractor == "layout":
            try:
                from .azure_di.layout_mode import AzureDocumentIntelligenceLayoutModeParser
            except Exception as e:
                raise RuntimeError(f"azure_di_layout_parser_unavailable: {e}")
            return AzureDocumentIntelligenceLayoutModeParser()

        the_class = FILE_TYPE_PAESER.get(parser_key, FILE_TYPE_PAESER.get(file_type, TxtParser))
        return the_class()
