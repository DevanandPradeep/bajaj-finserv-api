"""OCR engine implementations for the Bajaj pipeline."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from PIL import Image
import pytesseract


class OCREngineBase(ABC):
    """Abstract base class for OCR engines."""

    @abstractmethod
    def recognize(self, image: Image.Image) -> List[Dict[str, Any]]:
        """Return list of boxes with keys: text, left, top, width, height, conf."""


class TesseractOCREngine(OCREngineBase):
    """OCR engine backed by pytesseract."""

    def __init__(self, lang: str = "eng", config: Optional[str] = None) -> None:
        self.lang = lang
        self.config = config or ""

    def recognize(self, image: Image.Image) -> List[Dict[str, Any]]:
        data = pytesseract.image_to_data(
            image, lang=self.lang, config=self.config, output_type=pytesseract.Output.DICT
        )
        boxes: List[Dict[str, Any]] = []
        num_entries = len(data.get("text", []))
        for idx in range(num_entries):
            text = (data["text"][idx] or "").strip()
            if not text:
                continue

            try:
                conf = float(data["conf"][idx])
            except (ValueError, TypeError, KeyError):
                conf = 0.0

            try:
                left = int(data["left"][idx])
                top = int(data["top"][idx])
                width = int(data["width"][idx])
                height = int(data["height"][idx])
            except (ValueError, TypeError, KeyError):
                # Skip malformed entries.
                continue

            boxes.append(
                {
                    "text": text,
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height,
                    "conf": conf,
                }
            )
        return boxes


class DeepSightOCREngine(OCREngineBase):
    """Vendor stub that will be replaced with real DeepSight integration."""

    def __init__(self, model_name: str = "deepsight-vision") -> None:
        self.model_name = model_name

    def recognize(self, image: Image.Image) -> List[Dict[str, Any]]:
        raise NotImplementedError("DeepSight OCR integration not implemented yet.")

