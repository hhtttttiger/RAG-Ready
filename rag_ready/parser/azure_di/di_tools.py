from __future__ import annotations

import html
import io
import os
import re
from dataclasses import dataclass
from typing import Any, Iterator, Optional

import requests
from loguru import logger

from ...models.document_model import DocumentInfo, DocumentPageInfo
from ...utils.file_utils import dhash, hamming_distance


@dataclass(frozen=True)
class AzureDIConfig:
    endpoint: str
    key: str
    no_proxy: bool = False


# Pre-compile regex patterns for performance
_RE_HTML_TAGS = re.compile(r"<[^>]+>")
_RE_WHITESPACE = re.compile(r"\s+")


class AzureDocumentIntelligenceTools:
    def layout_mode_load(
        self,
        file_bytes: bytes,
        figures: bool = True,
        **kwargs,
    ) -> DocumentInfo:
        config = self._resolve_config(**kwargs)
        output_dir = kwargs.get("output_dir")

        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentContentFormat
            from azure.core.credentials import AzureKeyCredential
        except Exception as e:
            raise Exception(f"azure_di_deps_missing: {e}")

        try:
            client = DocumentIntelligenceClient(endpoint=config.endpoint, credential=AzureKeyCredential(config.key))
            common_params: dict[str, Any] = {
                "model_id": "prebuilt-layout",
                "body": AnalyzeDocumentRequest(bytes_source=file_bytes),
                "output_content_format": DocumentContentFormat.MARKDOWN,
            }
            if figures:
                common_params["output"] = ["figures"]

            poller = client.begin_analyze_document(**common_params)
            operation_location = poller._polling_method._initial_response.http_response.headers.get("Operation-Location", "")
            result_id = operation_location.split("/")[-1].split("?")[0] if operation_location else ""
            result = poller.result()

            merge_table_content = getattr(result, "content", "") or ""
            if getattr(result, "tables", None) is not None:
                try:
                    from .merge_table import merge_tables

                    merge_table_content = merge_tables(result)
                except Exception as e:
                    logger.warning(f"azure_di_merge_tables_failed: {e}")
            pages_content = self._split_markdown(merge_table_content)

            if figures:
                try:
                    self._extract_images(
                        result=result,
                        result_id=result_id,
                        pages=pages_content,
                        config=config,
                        output_dir=output_dir,
                    )
                except Exception as e:
                    logger.warning(f"azure_di_extract_images_failed: {e}")

            doc_info = DocumentInfo()
            doc_info.content = merge_table_content
            doc_info.is_md = True

            for item in pages_content:
                page = DocumentPageInfo(
                    content=item["content"],
                    metadata={"page": int(item["page_number"])},
                )
                doc_info.page_list.append(page)

            return doc_info
        except Exception as e:
            raise Exception(f"azure_di_layout_failed: {e}")

    def _split_markdown(self, markdown: str) -> list[dict[str, Any]]:
        pages_content: list[dict[str, Any]] = []
        pages = markdown.split("<!-- PageBreak -->") if markdown else [""]
        for i, page in enumerate(pages):
            pages_content.append(
                {
                    "page_number": str(i + 1),
                    "content": page,
                }
            )
        return pages_content

    def _extract_images(
        self,
        result: Any,
        result_id: str,
        pages: list[dict[str, Any]],
        config: AzureDIConfig,
        output_dir: str | None,
    ) -> None:
        if getattr(result, "figures", None) is None:
            return
        if not output_dir:
            return

        try:
            from PIL import Image
        except Exception:
            return

        images_dir = self._ensure_images_dir(output_dir)
        session, headers = self._create_image_fetch_session(config)
        processed_hash: dict[str, str] = {}
        markdown_content = getattr(result, "content", "") or ""
        pages_map = {p["page_number"]: p for p in pages}

        for figure in result.figures:
            figure_id = getattr(figure, "id", None)
            if not figure_id:
                continue

            page_number = self._figure_page_number(figure_id)
            image_url = self._build_figure_image_url(
                endpoint=config.endpoint,
                result_id=result_id,
                figure_id=figure_id,
            )
            resp = self._fetch_image_with_retries(
                session=session,
                image_url=image_url,
                headers=headers,
                figure_id=figure_id,
            )
            if resp is None:
                continue

            image_name = self._sanitize_image_name(figure_id)
            image_path = os.path.join(images_dir, image_name)
            current_hash, threshold = self._compute_image_hash(Image, resp.content, image_name)
            dup_path = self._find_duplicate_image_path(processed_hash, current_hash, threshold)
            if dup_path:
                image_path = dup_path
            else:
                self._save_bytes(image_path, resp.content)
                processed_hash[current_hash] = image_path

            figure_content = self._extract_figure_content(figure, markdown_content)
            caption = self._extract_figure_caption(figure)
            caption_text = self._build_caption_text(caption, figure_content)
            rel_path = os.path.relpath(image_path, output_dir).replace("\\", "/")
            tag = self._make_md_image_tag(caption_text, rel_path)

            self._replace_or_append_image_tag(
                pages=pages,
                pages_map=pages_map,
                page_number=page_number,
                replace_content=figure_content,
                image_tag=tag,
            )

    def _ensure_images_dir(self, output_dir: str) -> str:
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        return images_dir

    def _create_image_fetch_session(self, config: AzureDIConfig) -> tuple[requests.Session, dict[str, str]]:
        session = requests.Session()
        session.trust_env = not bool(config.no_proxy)
        headers = {"Ocp-Apim-Subscription-Key": config.key}
        return session, headers

    def _figure_page_number(self, figure_id: Any) -> int:
        try:
            return int(str(figure_id).split(".")[0])
        except Exception:
            return 1

    def _build_figure_image_url(self, endpoint: str, result_id: str, figure_id: Any) -> str:
        image_url = "/".join(
            [
                endpoint.rstrip("/"),
                "documentintelligence/documentModels/prebuilt-layout",
                f"analyzeResults/{result_id}/figures/{figure_id}",
            ]
        )
        return f"{image_url}?api-version=2024-11-30"

    def _fetch_image_with_retries(
        self,
        session: requests.Session,
        image_url: str,
        headers: dict[str, str],
        figure_id: Any,
        retries: int = 3,
        timeout_s: int = 60,
    ) -> Optional[requests.Response]:
        resp: Optional[requests.Response] = None
        last_err: Optional[Exception] = None
        for _ in range(retries):
            try:
                resp = session.get(image_url, headers=headers, timeout=timeout_s)
                last_err = None
                break
            except Exception as e:
                last_err = e

        if last_err is not None:
            logger.warning(f"azure_di_fetch_image_failed: figure_id={figure_id} err={last_err}")
            return None
        if resp is None or resp.status_code != 200:
            return None
        return resp

    def _sanitize_image_name(self, figure_id: Any) -> str:
        return f"{figure_id}.png".replace("/", "_").replace("\\", "_")

    def _compute_image_hash(self, Image: Any, image_bytes: bytes, fallback_name: str) -> tuple[str, int]:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            current_hash = dhash(img)
            threshold = 5
        except Exception:
            current_hash = fallback_name
            threshold = 0
        return current_hash, threshold

    def _find_duplicate_image_path(
        self,
        processed_hash: dict[str, str],
        current_hash: str,
        threshold: int,
    ) -> Optional[str]:
        for saved_hash, saved_path in processed_hash.items():
            if hamming_distance(current_hash, saved_hash) <= threshold:
                return saved_path
        return None

    def _save_bytes(self, path: str, data: bytes) -> None:
        with open(path, "wb") as f:
            f.write(data)

    def _extract_figure_caption(self, figure: Any) -> str:
        caption = ""
        if getattr(figure, "caption", None) and getattr(figure.caption, "content", None):
            caption = str(figure.caption.content)
        return caption

    def _extract_figure_content(self, figure: Any, markdown_content: str) -> str:
        try:
            spans = getattr(figure, "spans", None) or []
            if spans:
                span0 = spans[0]
                start = int(getattr(span0, "offset", 0))
                length = int(getattr(span0, "length", 0))
                if length > 0 and start >= 0:
                    return markdown_content[start : start + length]
        except Exception:
            return ""
        return ""

    def _build_caption_text(self, caption: str, figure_content: str) -> str:
        caption_text = (caption or "").strip()
        fig_text = self._html_to_text(figure_content).strip()
        if fig_text:
            caption_text = f"{caption_text} {fig_text}".strip()
        return caption_text

    def _make_md_image_tag(self, caption_text: str, rel_path: str) -> str:
        return f"![{caption_text}]({rel_path})"

    def _replace_or_append_image_tag(
        self,
        pages: list[dict[str, Any]],
        pages_map: dict[str, dict[str, Any]],
        page_number: int,
        replace_content: str,
        image_tag: str,
    ) -> bool:
        replace_content = replace_content or ""
        # Optimization: O(1) lookup
        matching_page = pages_map.get(str(page_number))

        if replace_content and matching_page and replace_content in (matching_page.get("content") or ""):
            matching_page["content"] = matching_page["content"].replace(replace_content, image_tag, 1)
            return True

        if replace_content:
            for p in pages:
                if replace_content in (p.get("content") or ""):
                    p["content"] = p["content"].replace(replace_content, image_tag, 1)
                    return True

        if matching_page is None:
            matching_page = pages[0] if pages else None
        if matching_page is None:
            return False

        content = (matching_page.get("content") or "").rstrip()
        if content:
            matching_page["content"] = f"{content}\n\n{image_tag}\n"
        else:
            matching_page["content"] = f"{image_tag}\n"
        return True

    def _html_to_text(self, content: str) -> str:
        if not content:
            return ""
        text = _RE_HTML_TAGS.sub(" ", content)
        text = html.unescape(text)
        text = _RE_WHITESPACE.sub(" ", text).strip()
        return text

    def _resolve_config(self, **kwargs) -> AzureDIConfig:
        endpoint = kwargs.get("azure_di_endpoint") or os.environ.get("AZURE_DI_ENDPOINT") or ""
        key = kwargs.get("azure_di_key") or os.environ.get("AZURE_DI_KEY") or ""
        no_proxy = bool(kwargs.get("no_proxy", False))

        endpoint = str(endpoint).strip().strip("`").strip("\"").strip("'").strip()
        key = str(key).strip().strip("`").strip("\"").strip("'").strip()
        endpoint = endpoint.rstrip("/")
        if not endpoint or not key:
            raise Exception("azure_di_config_missing")
        return AzureDIConfig(endpoint=endpoint, key=key, no_proxy=no_proxy)
