"""Entry point for Bajaj pipeline."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, List

from .ocr_engines import DeepSightOCREngine, TesseractOCREngine
from .preprocessing import load_document_as_images, preprocess_page
from .line_item_extractor import extract_page_line_items


def _dump_ocr_boxes(
    boxes: List[dict], engine_name: str, page_index: int, output_dir: Path
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"page_{page_index:02d}_{engine_name}.json"
    target.write_text(json.dumps(boxes, indent=2), encoding="utf-8")


def process_request(payload: List[dict], dump_ocr: bool = False, dump_dir: str | None = None) -> List[Any]:
    if not payload or "document" not in payload[0]:
        raise ValueError("Payload must contain at least one element with a 'document' key.")

    document_url = payload[0]["document"]
    pages = load_document_as_images(document_url)

    pagewise_line_items = []
    total_item_count = 0
    reconciled_amount = 0.0

    for page_index, page_image in enumerate(pages, start=1):
        processed_page = preprocess_page(page_image)
        all_boxes = []

        for engine in (TesseractOCREngine(), DeepSightOCREngine()):
            engine_name = engine.__class__.__name__
            try:
                boxes = engine.recognize(processed_page)
                all_boxes.extend(boxes)
                if dump_ocr and boxes:
                    dump_path = dump_dir or os.environ.get("OCR_DUMP_DIR") or "debug_ocr"
                    _dump_ocr_boxes(boxes, engine_name, page_index, Path(dump_path))
            except NotImplementedError as exc:
                print(f"[WARN] {engine_name} skipped: {exc}")

        bill_items = extract_page_line_items(all_boxes)
        total_item_count += len(bill_items)
        reconciled_amount += sum(item["item_amount"] for item in bill_items)

        pagewise_line_items.append(
            {
                "page_no": str(page_index),
                "bill_items": bill_items,
            }
        )

    result = [
        {"document": document_url},
        {
            "is_success": True,
            "data": {
                "pagewise_line_items": pagewise_line_items,
                "total_item_count": total_item_count,
                "reconciled_amount": round(reconciled_amount, 2),
            },
        },
    ]
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Bajaj Finserv document pipeline.")
    parser.add_argument("input_json", help="Path to input JSON file.")
    parser.add_argument(
        "--dump-ocr",
        action="store_true",
        help="Write raw OCR boxes per page/engine into debug_ocr/ (or --dump-dir).",
    )
    parser.add_argument(
        "--dump-dir",
        default=None,
        help="Directory to store OCR dumps (default debug_ocr or env OCR_DUMP_DIR).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    with open(args.input_json, "r", encoding="utf-8") as f:
        payload = json.load(f)

    result = process_request(payload, dump_ocr=args.dump_ocr, dump_dir=args.dump_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

