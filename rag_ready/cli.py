from __future__ import annotations

import argparse
import itertools
import os
import sys
import threading
import time

from loguru import logger

from .context import PipelineContext, PipelineConfig
from .pipeline import RagPreprocessPipeline


def _run_spinner(context: PipelineContext, stop_event: threading.Event) -> None:
    for ch in itertools.cycle("|/-\\"):
        if stop_event.is_set():
            break
        step = context.current_step or "执行中"
        sys.stdout.write(f"\r{step} {ch}")
        sys.stdout.flush()
        time.sleep(0.1)

    sys.stdout.write("\r" + (" " * 80) + "\r")
    sys.stdout.flush()


def main() -> int:
    parser = argparse.ArgumentParser(prog="rag-ready")
    parser.add_argument("--file", required=True, help="外部文件路径")
    parser.add_argument("--output-dir", default=os.path.join(".", "out"))
    parser.add_argument("--chunk-size", type=int, default=1024)
    parser.add_argument("--overlap", type=int, default=0)
    parser.add_argument("--parser", default=None)
    parser.add_argument("--extractor", default=None, choices=["layout"])
    parser.add_argument("--chainsaw", default=None)

    parser.add_argument("--azure-di-endpoint", default=None)
    parser.add_argument("--azure-di-key", default=None)
    parser.add_argument("--azure-di-formulas", action="store_true")
    parser.add_argument("--no-proxy", action="store_true", help="禁用环境变量代理（HTTP_PROXY/HTTPS_PROXY）")

    parser.add_argument("--image-caption", action="store_true", help="对 Markdown 图片标签做视觉描述增强")
    parser.add_argument("--image-caption-limit", type=int, default=0, help="最多调用 AI 次数，0 表示不限制")
    parser.add_argument("--aoai-endpoint", default=None)
    parser.add_argument("--aoai-key", default=None)
    parser.add_argument("--aoai-deployment", default=None)
    parser.add_argument("--aoai-api-version", default="2024-06-01")
    parser.add_argument("--aoai-temperature", type=float, default=0.0)

    args = parser.parse_args()

    input_path = os.path.abspath(args.file)
    if not os.path.exists(input_path):
        raise SystemExit(f"file_not_found: {input_path}")

    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    parser_kwargs: dict = {"output_dir": output_dir}
    if args.azure_di_endpoint:
        parser_kwargs["azure_di_endpoint"] = args.azure_di_endpoint
    if args.azure_di_key:
        parser_kwargs["azure_di_key"] = args.azure_di_key
    if args.azure_di_formulas:
        parser_kwargs["formulas"] = True
    if args.no_proxy:
        parser_kwargs["no_proxy"] = True

    context = PipelineContext(
        input_path=input_path,
        output_dir=output_dir,
        config=PipelineConfig(
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            parser=args.parser,
            extractor=args.extractor,
            chainsaw=args.chainsaw,
            parser_kwargs=parser_kwargs,
        ),
    )

    context.ai_settings = {
        "enable_image_caption": bool(args.image_caption),
        "image_caption_limit": int(args.image_caption_limit),
        "aoai_endpoint": args.aoai_endpoint,
        "aoai_key": args.aoai_key,
        "aoai_deployment": args.aoai_deployment,
        "aoai_api_version": args.aoai_api_version,
        "aoai_temperature": float(args.aoai_temperature),
    }

    logger.info("pipeline_start")

    ok = False
    stop_event = threading.Event()
    spinner_thread: threading.Thread | None = None
    if sys.stdout.isatty():
        spinner_thread = threading.Thread(target=_run_spinner, args=(context, stop_event), daemon=True)
        spinner_thread.start()
    else:
        print("执行中，请稍候...")

    try:
        ok = RagPreprocessPipeline(context).run()
    finally:
        stop_event.set()
        if spinner_thread is not None:
            spinner_thread.join(timeout=1.0)

    if sys.stdout.isatty():
        sys.stdout.write(("完成\n" if ok else "失败\n"))
        sys.stdout.flush()
    else:
        print("完成" if ok else "失败")

    if not ok:
        logger.error("failed")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
