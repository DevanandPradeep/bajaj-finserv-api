"""Document loading and preprocessing utilities."""
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse

import requests
from PIL import Image, ImageFilter, ImageOps
from pdf2image import convert_from_bytes


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _read_remote_document(document_url: str) -> Tuple[bytes, str, str]:
    try:
        response = requests.get(document_url, timeout=30)
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to download document: {document_url}") from exc

    if response.status_code >= 400:
        raise RuntimeError(
            f"Document download failed with status {response.status_code}: {document_url}"
        )

    content_type = (response.headers.get("Content-Type") or "").lower()
    return response.content, content_type, document_url.lower()


def _read_local_document(document_path: str) -> Tuple[bytes, str, str]:
    path = Path(document_path)
    if not path.is_absolute():
        root = _project_root()
        candidate = (root / path).resolve()
        data_candidate = (root / "data" / path).resolve()

        if candidate.exists():
            path = candidate
        elif data_candidate.exists():
            path = data_candidate
        else:
            raise RuntimeError(
                f"Document path '{document_path}' not found. "
                "Place files under project root or data/."
            )

    if not path.exists():
        raise RuntimeError(f"Document file does not exist: {path}")

    with path.open("rb") as f:
        payload = f.read()

    return payload, "", path.suffix.lower()


def load_document_as_images(document_ref: str) -> List[Image.Image]:
    """Load the document (URL or local path) and convert it into PIL Images."""
    parsed = urlparse(document_ref)
    if parsed.scheme in {"http", "https"}:
        payload, content_type, suffix_hint = _read_remote_document(document_ref)
    else:
        payload, content_type, suffix_hint = _read_local_document(document_ref)

    is_pdf = (
        suffix_hint.endswith(".pdf")
        or "application/pdf" in content_type
        or payload.startswith(b"%PDF")
    )

    poppler_path = os.environ.get("POPPLER_PATH") or None

    if is_pdf:
        try:
            return convert_from_bytes(payload, poppler_path=poppler_path)
        except Exception as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("Failed to convert PDF bytes into images.") from exc

    try:
        image = Image.open(io.BytesIO(payload))
        image.load()
    except Exception as exc:
        raise RuntimeError("Failed to open document as an image.") from exc

    return [image]


def preprocess_page(image: Image.Image) -> Image.Image:
    """Apply preprocessing to improve OCR quality on tabular invoices."""
    grayscale = ImageOps.grayscale(image)
    contrasted = ImageOps.autocontrast(grayscale, cutoff=2)
    equalized = ImageOps.equalize(contrasted)
    blurred = equalized.filter(ImageFilter.MedianFilter(size=3))
    sharpened = blurred.filter(ImageFilter.UnsharpMask(radius=2, percent=200, threshold=2))

    # Binarize to keep numeric columns crisp for OCR.
    thresholded = sharpened.point(lambda px: 255 if px > 160 else 0)
    return thresholded

