from __future__ import annotations

import re
from itertools import zip_longest

from azure.ai.documentintelligence.models import AnalyzeResult, DocumentTable, DocumentTableCellKind

BORDER_SYMBOL = "|"


def _get_table_page_numbers(table):
    return [region.page_number for region in table.bounding_regions]


def _get_table_span_offsets(table):
    if table.spans:
        min_offset = table.spans[0].offset
        max_offset = table.spans[0].offset + table.spans[0].length

        for span in table.spans:
            if span.offset < min_offset:
                min_offset = span.offset
            if span.offset + span.length > max_offset:
                max_offset = span.offset + span.length

        return min_offset, max_offset
    else:
        return -1, -1


def _get_merge_table_candidates_and_table_integral_span(tables):
    table_integral_span_list = []
    merge_tables_candidates = []
    pre_table_idx = -1
    pre_table_page = -1
    pre_max_offset = 0

    for table_idx, table in enumerate(tables):
        min_offset, max_offset = _get_table_span_offsets(table)
        if min_offset > -1 and max_offset > -1:
            table_page = min(_get_table_page_numbers(table))
            if table_page == pre_table_page + 1:
                pre_table = {
                    "pre_table_idx": pre_table_idx,
                    "start": pre_max_offset,
                    "end": min_offset,
                    "min_offset": min_offset,
                    "max_offset": max_offset,
                }
                merge_tables_candidates.append(pre_table)

            table_integral_span_list.append(
                {
                    "idx": table_idx,
                    "min_offset": min_offset,
                    "max_offset": max_offset,
                }
            )

            pre_table_idx = table_idx
            pre_table_page = table_page
            pre_max_offset = max_offset
        else:
            table_integral_span_list.append({"idx": table_idx, "min_offset": -1, "max_offset": -1})

    return merge_tables_candidates, table_integral_span_list


def _check_paragraph_presence(paragraphs, start, end):
    for paragraph in paragraphs:
        for span in paragraph.spans:
            if span.offset > start and span.offset < end:
                if paragraph.role is not None and paragraph.role not in ["pageHeader", "pageFooter", "pageNumber"]:
                    return True
    return False


def _check_tables_are_horizontal_distribution(result, pre_table_idx):
    INDEX_OF_X_LEFT_TOP = 0
    INDEX_OF_X_LEFT_BOTTOM = 6
    INDEX_OF_X_RIGHT_TOP = 2
    INDEX_OF_X_RIGHT_BOTTOM = 4

    THRESHOLD_RATE_OF_RIGHT_COVER = 0.99
    THRESHOLD_RATE_OF_LEFT_COVER = 0.01

    is_right_covered = False
    is_left_covered = False

    if result.tables[pre_table_idx].row_count == result.tables[pre_table_idx + 1].row_count:
        for region in result.tables[pre_table_idx].bounding_regions:
            page_width = result.pages[region.page_number - 1].width
            x_right = max(
                region.polygon[INDEX_OF_X_RIGHT_TOP],
                region.polygon[INDEX_OF_X_RIGHT_BOTTOM],
            )
            right_cover_rate = x_right / page_width
            if right_cover_rate > THRESHOLD_RATE_OF_RIGHT_COVER:
                is_right_covered = True
                break

        for region in result.tables[pre_table_idx + 1].bounding_regions:
            page_width = result.pages[region.page_number - 1].width
            x_left = min(
                region.polygon[INDEX_OF_X_LEFT_TOP],
                region.polygon[INDEX_OF_X_LEFT_BOTTOM],
            )
            left_cover_rate = x_left / page_width
            if left_cover_rate < THRESHOLD_RATE_OF_LEFT_COVER:
                is_left_covered = True
                break

    return is_left_covered and is_right_covered


def _remove_header_from_markdown_table(markdown_table):
    HEADER_CHARS = set("-:| +")
    result = ""
    lines = markdown_table.splitlines()
    header_removed = False
    for line in lines:
        stripped = line.strip()
        if not header_removed and stripped and all(c in HEADER_CHARS for c in stripped):
            header_removed = True
            continue
        tokens = [t.strip() for t in stripped.split("|") if t.strip() != ""]
        if not header_removed and tokens and all(set(t) <= set("-:") for t in tokens):
            header_removed = True
            continue
        result += f"{line}\n"
    return result


def _merge_vertical_content(content1: str, content2: str):
    content2 = _remove_header_from_markdown_table(content2)
    return content1.strip() + "\n" + content2.strip() + "\n"


def _normalize_cell_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def _are_table_headers_equal(table1: DocumentTable, table2: DocumentTable) -> bool:
    def get_headers(table: DocumentTable):
        header_cells = [cell for cell in table.cells if cell.kind == DocumentTableCellKind.COLUMN_HEADER]
        header_cells_sorted = sorted(header_cells, key=lambda c: (c.row_index, c.column_index))
        headers = []
        for cell in header_cells_sorted:
            headers.append(_normalize_cell_text(getattr(cell, "content", "")))
        return headers

    try:
        h1 = get_headers(table1)
        h2 = get_headers(table2)
        return h1 == h2 and len(h1) > 0
    except Exception:
        return False


def _markdown_table_to_rows(markdown_table: str) -> list[list[str]]:
    lines = [ln for ln in markdown_table.splitlines() if ln.strip()]
    rows: list[list[str]] = []
    for ln in lines:
        if set(ln.strip()) <= set("-:| "):
            continue
        parts = [p.strip() for p in ln.strip().strip("|").split("|")]
        rows.append(parts)
    return rows


def _rows_to_markdown_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    max_cols = max(len(r) for r in rows)
    norm_rows = [r + [""] * (max_cols - len(r)) for r in rows]
    header = norm_rows[0]
    sep = ["---"] * max_cols
    body = norm_rows[1:]
    out_lines = []
    out_lines.append(BORDER_SYMBOL + BORDER_SYMBOL.join(header) + BORDER_SYMBOL)
    out_lines.append(BORDER_SYMBOL + BORDER_SYMBOL.join(sep) + BORDER_SYMBOL)
    for r in body:
        out_lines.append(BORDER_SYMBOL + BORDER_SYMBOL.join(r) + BORDER_SYMBOL)
    return "\n".join(out_lines) + "\n"


def _merge_horizontal_tables(table1_md: str, table2_md: str) -> str:
    rows1 = _markdown_table_to_rows(table1_md)
    rows2 = _markdown_table_to_rows(table2_md)
    if not rows1:
        return table2_md
    if not rows2:
        return table1_md

    merged_rows = []
    for r1, r2 in zip_longest(rows1, rows2, fillvalue=[]):
        merged_rows.append(list(r1) + list(r2))
    return _rows_to_markdown_table(merged_rows)


def _is_table_top_banner(result: AnalyzeResult, table_idx: int) -> bool:
    try:
        table = result.tables[table_idx]
        TOP_Y_THRESHOLD_RATE = 0.2
        SMALL_ROW_THRESHOLD = 2
        SMALL_COL_THRESHOLD = 6

        for region in table.bounding_regions:
            page = result.pages[region.page_number - 1]
            page_height = page.height
            ys = region.polygon[1::2]
            top_y = min(ys) if ys else 0
            top_rate = top_y / page_height if page_height else 0

            if top_rate < TOP_Y_THRESHOLD_RATE and table.row_count <= SMALL_ROW_THRESHOLD and table.column_count <= SMALL_COL_THRESHOLD:
                return True
    except Exception:
        return False

    return False


def merge_tables(result: AnalyzeResult) -> str:
    merge_tables_candidates, table_integral_span_list = _get_merge_table_candidates_and_table_integral_span(result.tables)

    merged_table_list = []
    for merged_table in merge_tables_candidates:
        pre_table_idx = merged_table["pre_table_idx"]
        start = merged_table["start"]
        end = merged_table["end"]
        has_paragraph = _check_paragraph_presence(result.paragraphs, start, end)

        is_banner_pre = _is_table_top_banner(result, pre_table_idx)
        is_banner_nxt = _is_table_top_banner(result, pre_table_idx + 1)

        is_horizontal = (
            not has_paragraph
            and not is_banner_pre
            and not is_banner_nxt
            and _check_tables_are_horizontal_distribution(result, pre_table_idx)
        )
        is_vertical = (
            not has_paragraph
            and not is_banner_pre
            and not is_banner_nxt
            and result.tables[pre_table_idx].column_count == result.tables[pre_table_idx + 1].column_count
            and _are_table_headers_equal(result.tables[pre_table_idx], result.tables[pre_table_idx + 1])
        )

        if is_vertical or is_horizontal:
            remark = result.content[
                table_integral_span_list[pre_table_idx]["max_offset"] : table_integral_span_list[pre_table_idx + 1]["min_offset"]
            ]
            cur_content = result.content[
                table_integral_span_list[pre_table_idx + 1]["min_offset"] : table_integral_span_list[pre_table_idx + 1]["max_offset"]
            ]

            merged_list_len = len(merged_table_list)
            if (
                merged_list_len > 0
                and len(merged_table_list[-1]["table_idx_list"]) > 0
                and merged_table_list[-1]["table_idx_list"][-1] == pre_table_idx
            ):
                merged_table_list[-1]["table_idx_list"].append(pre_table_idx + 1)
                merged_table_list[-1]["offset"]["max_offset"] = table_integral_span_list[pre_table_idx + 1]["max_offset"]
                if is_vertical:
                    merged_table_list[-1]["content"] = _merge_vertical_content(merged_table_list[-1]["content"], cur_content)
                    merged_table_list[-1]["remark"] += remark
                elif is_horizontal:
                    merged_table_list[-1]["content"] = _merge_horizontal_tables(merged_table_list[-1]["content"], cur_content)
                    merged_table_list[-1]["remark"] += remark
            else:
                pre_content = result.content[
                    table_integral_span_list[pre_table_idx]["min_offset"] : table_integral_span_list[pre_table_idx]["max_offset"]
                ]
                merged_table = {
                    "table_idx_list": [pre_table_idx, pre_table_idx + 1],
                    "offset": {
                        "min_offset": table_integral_span_list[pre_table_idx]["min_offset"],
                        "max_offset": table_integral_span_list[pre_table_idx + 1]["max_offset"],
                    },
                    "content": _merge_vertical_content(pre_content, cur_content)
                    if is_vertical
                    else _merge_horizontal_tables(pre_content, cur_content),
                    "remark": remark.strip(),
                }

                if merged_list_len <= 0:
                    merged_table_list = [merged_table]
                else:
                    merged_table_list.append(merged_table)
        else:
            continue

    optimized_content = ""
    if merged_table_list:
        start_idx = 0
        for merged_table in merged_table_list:
            optimized_content += (
                result.content[start_idx : merged_table["offset"]["min_offset"]]
                + merged_table["content"]
                + merged_table["remark"]
            )
            start_idx = merged_table["offset"]["max_offset"]

        optimized_content += result.content[start_idx:]
    else:
        optimized_content = result.content

    return optimized_content
