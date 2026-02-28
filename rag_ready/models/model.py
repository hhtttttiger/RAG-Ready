from __future__ import annotations

from pydantic import BaseModel, Field

from ..utils.file_utils import get_file_extension

class FileMessage(BaseModel):
    extension: str

    @classmethod
    def from_local_path(cls, path: str) -> "FileMessage":
        ext = get_file_extension(path)
        return cls(
            extension=ext,
        )



