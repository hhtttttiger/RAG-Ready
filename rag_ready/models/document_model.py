from __future__ import annotations

from pydantic import BaseModel, Field

class DocumentChunkInfo(BaseModel):
    text: str
    metadata: dict = Field(default_factory=dict)


class DocumentPageInfo(BaseModel):
    content: str = ""
    metadata: dict = Field(default_factory=dict)


class DocumentInfo(BaseModel):
    content: str = ""
    page_list: list[DocumentPageInfo] = Field(default_factory=list)
    use_chainsaw: bool = True
    is_md: bool = False
