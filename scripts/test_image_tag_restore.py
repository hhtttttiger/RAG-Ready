from __future__ import annotations

import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from rag_ready.parser.azure_di.di_tools import AzureDocumentIntelligenceTools


def test_replace_by_span_content() -> None:
    helper = AzureDocumentIntelligenceTools()
    pages = [{"page_number": "1", "content": "aaa [FIGURE] bbb"}]
    ok = helper._replace_or_append_image_tag(pages, page_number=1, replace_content="[FIGURE]", image_tag="![x](images/1.png)")
    assert ok is True
    assert "![x](images/1.png)" in pages[0]["content"]
    assert "[FIGURE]" not in pages[0]["content"]


def test_append_when_not_found() -> None:
    helper = AzureDocumentIntelligenceTools()
    pages = [{"page_number": "2", "content": "hello"}]
    ok = helper._replace_or_append_image_tag(pages, page_number=2, replace_content="", image_tag="![x](images/1.png)")
    assert ok is True
    assert pages[0]["content"].startswith("hello")
    assert "![x](images/1.png)" in pages[0]["content"]


if __name__ == "__main__":
    test_replace_by_span_content()
    test_append_when_not_found()
    print("ok")
