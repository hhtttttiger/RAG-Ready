from __future__ import annotations

import os
import sys
import tempfile
import time

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from rag_ready.context import PipelineContext
from rag_ready.pipeline import RagPreprocessPipeline


def run() -> None:
    with tempfile.TemporaryDirectory() as td:
        input_path = os.path.join(td, "demo.txt")
        output_dir = os.path.join(td, "out")
        with open(input_path, "w", encoding="utf-8") as f:
            f.write("hello\\n" * 2000)

        file_id = int(time.time_ns() // 1_000_000)
        ctx = PipelineContext(input_path=input_path, output_dir=output_dir)
        ok = RagPreprocessPipeline(context=ctx, chunk_size=200, overlap=20, parser_kwargs={"output_dir": output_dir}).run()
        assert ok is True
        assert os.path.exists(os.path.join(output_dir, "segments.json"))


if __name__ == "__main__":
    run()
