from __future__ import annotations

import os
import sys
import tempfile

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from rag_ready.context import PipelineContext
from rag_ready.models.document_model import DocumentChunkInfo
from rag_ready.steps.enrich_image_captions_step import EnrichImageCaptionsStep


class FakeVisionClient:
    def describe_image(self, image_bytes: bytes, hint: str = "") -> str:
        return "一张测试图片"


def run() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_dir = os.path.join(td, "out")
        os.makedirs(os.path.join(out_dir, "images"), exist_ok=True)
        img_path = os.path.join(out_dir, "images", "a.png")
        with open(img_path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")

        ctx = PipelineContext(input_path="x", output_dir=out_dir)
        ctx.is_md = True
        ctx.ai_settings = {"enable_image_caption": True, "image_caption_limit": 0}
        ctx.ai_client = FakeVisionClient()
        ctx.chunk_list = [DocumentChunkInfo(text="hello ![](images/a.png) world", metadata={})]

        EnrichImageCaptionsStep(ctx).run()
        assert "![一张测试图片](images/a.png)" in ctx.chunk_list[0].text


if __name__ == "__main__":
    run()
    print("ok")
