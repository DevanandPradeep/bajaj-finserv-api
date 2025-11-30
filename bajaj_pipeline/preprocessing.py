"""Document loading and preprocessing utilities."""
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse

import requests
import cv2
import numpy as np
from PIL import Image, ImageOps
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
            # Convert at 300 DPI for better OCR accuracy
            return convert_from_bytes(payload, dpi=300, poppler_path=poppler_path)
        except Exception as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("Failed to convert PDF bytes into images.") from exc

    try:
        image = Image.open(io.BytesIO(payload))
        image.load()
        # Ensure 300 DPI if possible, or resize if too small
        if image.width < 1000:
            scale = 2
            image = image.resize((image.width * scale, image.height * scale), Image.Resampling.LANCZOS)
    except Exception as exc:
        raise RuntimeError("Failed to open document as an image.") from exc

    return [image]


def _deskew(image: np.ndarray) -> np.ndarray:
    """Correct skew using Hough transform."""
    try:
        gray = image
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
        # Detect edges
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Detect lines
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is None:
            return image
            
        # Calculate median angle
        angles = []
        for line in lines:
            rho, theta = line[0]
            angle = theta * 180 / np.pi
            # Look for horizontal-ish lines
            if 80 < angle < 100:  # Near 90 degrees (vertical in Hough is horizontal line)
                angles.append(angle - 90)
            elif -10 < angle < 10: # Near 0 degrees (vertical line)
                angles.append(angle)
                
        if not angles:
            return image
            
        median_angle = np.median(angles)
        
        if abs(median_angle) < 0.5: # Ignore small skew
            return image
            
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated
    except Exception:
        return image


def preprocess_page(image: Image.Image) -> Image.Image:
    """Apply advanced OpenCV preprocessing to improve OCR quality."""
    # Convert PIL to OpenCV format (RGB -> BGR)
    img_np = np.array(image)
    if len(img_np.shape) == 3:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    
    # 1. Convert to Grayscale
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    
    # 2. Deskew
    # gray = _deskew(gray) # Optional: can be risky if few lines
    
    # 3. Noise Reduction (Gaussian Blur)
    # Removes high frequency noise
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # 4. Adaptive Thresholding
    # Better than simple thresholding for shadows/uneven lighting
    # Block size 11, C=2 are standard starting points
    binary = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # 5. Morphological operations (Optional)
    # Dilation can help connect broken characters
    # kernel = np.ones((1, 1), np.uint8)
    # binary = cv2.dilate(binary, kernel, iterations=1)
    
    # 6. Denoise salt-and-pepper
    binary = cv2.medianBlur(binary, 3)
    
    # Convert back to PIL
    return Image.fromarray(binary)

