"""Layout-aware line item extraction for OCR boxes."""
from __future__ import annotations

import difflib
import itertools
import math
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


NUMERIC_PATTERN = re.compile(r"[-+]?[\d\s,]*\.?\d+")
CURRENCY_SYMBOLS = "₹$€£¥"
HEADER_HINTS = {
    "item",
    "description",
    "service",
    "charge",
    "qty",
    "quantity",
    "rate",
    "price",
    "amount",
    "total",
    "net amount",
    "discount",
}
HEADER_ROLE_KEYWORDS = {
    "quantity": {"qty", "quantity", "hours", "hrs", "day", "days", "qty/hrs", "qtyhrs"},
    "rate": {"rate", "price", "unit", "tariff", "charges"},
    "amount": {"amount", "net amount", "net", "total", "net amt", "amt"},
    "discount": {"disc", "discount"},
}
COMMON_TERMS = [
    "consultation",
    "consultation charge",
    "doctor fee",
    "investigation",
    "pharmacy",
    "procedure",
    "radiology",
    "laboratory",
    "medication",
    "bed charges",
    "surgery",
    "nursing charges",
    "physiotherapy",
    "medicine",
    "room rent",
    "bed rent",
    "icu",
    "step down icu",
    "bystander room",
]
KNOWN_MISSPELLINGS = {
    "cansukation": "consultation",
    "consuttation": "consultation",
    "cansultation": "consultation",
    "cansutation": "consultation",
    "consuitation": "consultation",
    "consuitation": "consultation",
    "mrant": "room rent",
    "rant": "rent",
    "stzp": "step",
    "tou": "icu",
    "nersing": "nursing",
    "nersmg": "nursing",
}
PHRASE_CORRECTIONS = {
    "m rant stzp down tou": "Room Rent Step Down ICU",
    "rr -2-room rant": "RR -2 Room Rent",
    "rr -2-stepdown-nursing charge": "RR -2 Stepdown Nursing Charge",
    "room rare bystander roan": "Room Rent Bystander Room",
}


def _is_numeric_text(text: str) -> bool:
    stripped = text.strip().replace(" ", "")
    if not stripped:
        return False
    stripped = stripped.translate({ord(c): None for c in CURRENCY_SYMBOLS})
    return bool(NUMERIC_PATTERN.fullmatch(stripped))


def _safe_float(token: str) -> float:
    cleaned = token.strip()
    
    # Handle "448 00" -> "448.00" case (common OCR error where dot is read as space)
    # Heuristic: If there is a space and the last part is exactly 2 digits, treat as decimal.
    if " " in cleaned:
        parts = cleaned.split()
        if len(parts) >= 2 and len(parts[-1]) == 2 and parts[-1].isdigit():
            # Reconstruct with dot
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
    
    for symbol in CURRENCY_SYMBOLS:
        cleaned = cleaned.replace(symbol, "")
    
    # Handle European style 12,34 -> 12.34 if it looks like that
    if "," in cleaned and "." not in cleaned:
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) == 2:
             cleaned = cleaned.replace(",", ".")

    cleaned = cleaned.replace(",", "").replace(" ", "")
    cleaned = cleaned.replace("..", ".")
    cleaned = cleaned.replace("|", "")
    cleaned = cleaned.strip(".")
    if cleaned in {"", "-", ".", "+", ","}:
        raise ValueError("Token is not numeric")
    return float(cleaned)


def _normalize_token(token: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", token.lower())


def _match_role(text: str, cutoff: float = 0.78) -> Optional[str]:
    parts = re.split(r"[^\w/]+", text.lower())
    best_role: Optional[str] = None
    best_score = 0.0
    for part in parts:
        normalized = _normalize_token(part)
        if not normalized:
            continue
        for role, keywords in HEADER_ROLE_KEYWORDS.items():
            for keyword in keywords:
                score = difflib.SequenceMatcher(None, normalized, _normalize_token(keyword)).ratio()
                if score > best_score:
                    best_score = score
                    best_role = role
    if best_score >= cutoff:
        return best_role
    return None


def _normalize_box(box: Dict[str, Any]) -> Dict[str, Any]:
    left = int(box.get("left", 0))
    top = int(box.get("top", 0))
    width = int(box.get("width") or box.get("w") or 0)
    height = int(box.get("height") or box.get("h") or 0)
    text = (box.get("text") or "").strip()

    return {
        "text": text,
        "left": left,
        "top": top,
        "width": width,
        "height": height,
        "center_x": left + width / 2,
        "center_y": top + height / 2,
        "bottom": top + height,
    }


def _cluster_rows(boxes: Sequence[Dict[str, Any]], y_tolerance: int = 8) -> List[List[Dict[str, Any]]]:
    """Group boxes into rows using their vertical centers and overlap."""
    # Sort by top first to process from top-down
    sorted_boxes = sorted((b for b in boxes if b["text"]), key=lambda b: b["top"])
    rows: List[List[Dict[str, Any]]] = []

    for box in sorted_boxes:
        matched = False
        box_cy = box["center_y"]
        box_height = box["height"]

        for row in rows:
            # Calculate row stats
            row_cy = sum(b["center_y"] for b in row) / len(row)
            
            # Check vertical center proximity
            if abs(box_cy - row_cy) <= y_tolerance:
                row.append(box)
                matched = True
                break
            
            # Check significant vertical overlap
            # If the box overlaps more than 50% with the row's vertical span
            row_top = min(b["top"] for b in row)
            row_bottom = max(b["bottom"] for b in row)
            
            overlap_start = max(row_top, box["top"])
            overlap_end = min(row_bottom, box["bottom"])
            overlap = max(0, overlap_end - overlap_start)
            
            if box_height > 0 and (overlap / box_height) > 0.6:
                row.append(box)
                matched = True
                break

        if not matched:
            rows.append([box])

    # Sort boxes within each row by left coordinate
    for row in rows:
        row.sort(key=lambda b: b["left"])
        
    # Sort rows by vertical position
    rows.sort(key=lambda r: sum(b["center_y"] for b in r) / len(r))
    
    return rows


def _detect_header_index(rows: Sequence[Sequence[Dict[str, Any]]]) -> int:
    for idx, row in enumerate(rows[:5]):
        text = " ".join(box["text"].lower() for box in row)
        hits = sum(1 for hint in HEADER_HINTS if hint in text)
        if hits >= 2:
            return idx
    return -1


def _map_header_columns(row: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    role_centers: Dict[str, List[float]] = {}
    for box in row:
        role = _match_role(box["text"])
        if role:
            role_centers.setdefault(role, []).append(box["center_x"])
    return {role: sum(vals) / len(vals) for role, vals in role_centers.items()}


def _extract_header_info(rows: Sequence[Sequence[Dict[str, Any]]]) -> Tuple[int, Dict[str, float]]:
    for idx, row in enumerate(rows[:6]):
        role_map = _map_header_columns(row)
        if len(role_map) >= 2:
            return idx, role_map
        text = " ".join(box["text"].lower() for box in row)
        hits = sum(1 for hint in HEADER_HINTS if hint in text)
        if hits >= 2:
            return idx, role_map
    return -1, {}


def _cluster_positions(positions: Iterable[float], tolerance: float = 40.0) -> List[float]:
    clusters: List[List[float]] = []
    for pos in sorted(positions):
        if not clusters or abs(pos - clusters[-1][-1]) > tolerance:
            clusters.append([pos])
        else:
            clusters[-1].append(pos)
    centers = [sum(cluster) / len(cluster) for cluster in clusters]
    return centers


def _estimate_numeric_columns(rows: Sequence[Sequence[Dict[str, Any]]]) -> List[float]:
    numeric_positions = []
    for row in rows:
        for box in row:
            if _is_numeric_text(box["text"]) and len(box["text"]) <= 12:
                numeric_positions.append(box["center_x"])
    if not numeric_positions:
        return []
    
    # Improved clustering: use a smaller tolerance to distinguish columns better
    centers = _cluster_positions(numeric_positions, tolerance=20.0)
    centers = sorted(centers)
    
    # If we have more than 3 columns, try to identify the "amount" column (usually the rightmost)
    # and then look for rate and quantity relative to it.
    # For now, returning all candidates to let the assignment logic handle it is safer,
    # but we can prioritize the rightmost ones.
    return centers


def _merge_adjacent_numeric_tokens(row: List[Dict[str, Any]], gap: float = 18.0) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    idx = 0
    while idx < len(row):
        current = row[idx].copy()
        text = current["text"]
        while idx + 1 < len(row):
            nxt = row[idx + 1]
            if (
                _is_numeric_text(text)
                and _is_numeric_text(nxt["text"])
                and nxt["left"] - (current["left"] + current["width"]) <= gap
            ):
                # Join with space to preserve separation for _safe_float heuristics
                text = f"{text} {nxt['text']}"
                current["text"] = text
                current["width"] = (nxt["left"] + nxt["width"]) - current["left"]
                current["center_x"] = current["left"] + current["width"] / 2
                idx += 1
            else:
                break
        merged.append(current)
        idx += 1
    return merged


def _correct_spelling(text: str) -> str:
    lowered = text.lower()
    for wrong, right in PHRASE_CORRECTIONS.items():
        lowered = lowered.replace(wrong, right.lower())

    tokens = lowered.split()
    corrected_tokens = []
    for token in tokens:
        clean = re.sub(r"[^a-z]+", "", token)
        if clean in KNOWN_MISSPELLINGS:
            corrected_tokens.append(KNOWN_MISSPELLINGS[clean])
            continue
        if len(clean) >= 4:
            match = difflib.get_close_matches(clean.lower(), COMMON_TERMS, n=1, cutoff=0.85)
            if match:
                corrected_tokens.append(match[0])
                continue
        corrected_tokens.append(token)

    corrected = " ".join(corrected_tokens).strip()
    return corrected.title()


def _strip_trailing_numbers(text: str) -> str:
    tokens = text.split()
    while tokens and _is_numeric_text(tokens[-1]):
        tokens.pop()
    return " ".join(tokens).strip()


def _build_fallback_roles(column_centers: Sequence[float]) -> Dict[str, float]:
    if not column_centers:
        return {}
    centers = sorted(column_centers)[-3:]
    labels = ["quantity", "rate", "amount"]
    start = max(0, len(labels) - len(centers))
    return {labels[start + idx]: center for idx, center in enumerate(centers)}


def _assign_numeric_columns(
    numeric_boxes: Sequence[Dict[str, Any]],
    header_roles: Dict[str, float],
    fallback_centers: Sequence[float],
) -> Dict[str, float]:
    result: Dict[str, float] = {}
    if not numeric_boxes:
        return result

    if header_roles:
        label_centers = header_roles
    else:
        label_centers = _build_fallback_roles(fallback_centers)
        if not label_centers:
            label_centers = {"amount": None}

    for box in numeric_boxes:
        if len(label_centers) == 1 and "amount" in label_centers:
            label = "amount"
        else:
            label = None
            best_distance = float("inf")
            for role, center in label_centers.items():
                if center is None:
                    continue
                distance = abs(box["center_x"] - center)
                if distance < best_distance:
                    best_distance = distance
                    label = role
            if label is None:
                label = "amount"
        try:
            value = _safe_float(box["text"])
        except ValueError:
            continue
        result[label] = value
    return result


def _derive_columns_from_values(
    numeric_boxes: Sequence[Dict[str, Any]], values: Dict[str, float]
) -> Dict[str, float]:
    numbers: List[Tuple[float, float]] = []
    for box in numeric_boxes:
        try:
            numbers.append((_safe_float(box["text"]), box["center_x"]))
        except ValueError:
            continue

    if not numbers:
        return values

    numbers.sort(key=lambda item: item[1])
    numeric_values = [val for val, _ in numbers]

    # If we already have some values from column alignment, keep them
    # and try to fill in the gaps.
    
    # Try to find a valid Qty * Rate = Amount relationship
    best_assignment: Optional[Dict[str, float]] = None
    best_error = float("inf")
    
    # Permutations of all available numbers (including those we might have already assigned, 
    # to double check or if we have unassigned numbers)
    # Actually, let's just use the raw numbers found in the row.
    
    if len(numeric_values) >= 3:
        for qty_idx, rate_idx, amount_idx in itertools.permutations(range(len(numeric_values)), 3):
            qty = numeric_values[qty_idx]
            rate = numeric_values[rate_idx]
            amount = numeric_values[amount_idx]
            
            # Basic sanity checks
            if qty < 0 or rate < 0 or amount < 0:
                continue
                
            # Heuristic: Amount is usually the largest or close to it (unless qty < 1)
            # But let's rely on the math.
            
            if qty in (0, 0.0) or rate in (0, 0.0):
                continue
                
            error = abs((qty * rate) - amount)
            # Allow a small error margin for OCR mistakes or rounding
            if error < best_error:
                best_error = error
                best_assignment = {"quantity": qty, "rate": rate, "amount": amount}
    
    # If we found a good mathematical match, use it.
    if best_assignment and best_error <= 5.0:
        for key, val in best_assignment.items():
            values[key] = val
    else:
        # Fallback heuristics based on count and position
        # If we have 3 numbers and no math match, assume Left=Qty, Middle=Rate, Right=Amount
        if len(numeric_values) == 3 and not values:
             values["quantity"] = numeric_values[0]
             values["rate"] = numeric_values[1]
             values["amount"] = numeric_values[2]
        elif len(numeric_values) == 2 and not values:
            # If 2 numbers, usually Rate and Amount, or Qty and Amount.
            # Hard to say without headers.
            # Assume Rate, Amount if they are large?
            # Or Qty, Amount if one is small integer?
            v1, v2 = numeric_values
            if v1 < 100 and v1.is_integer() and v2 > v1:
                 values["quantity"] = v1
                 values["amount"] = v2
            else:
                 values["rate"] = v1
                 values["amount"] = v2
        elif len(numeric_values) == 1 and not values:
            values["amount"] = numeric_values[0]

    return values


def _clean_description(text: str) -> str:
    """Remove noise, dates, and special characters from description."""
    # Remove dates (DD/MM/YYYY or DD-MM-YYYY)
    text = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", "", text)
    
    # Remove common noise symbols
    text = re.sub(r"[~_»|—]", "", text)
    
    # Remove standalone special characters (e.g. " . " or " : ")
    text = re.sub(r"\s+[^a-zA-Z0-9()]\s+", " ", text)
    
    # Remove common header artifacts that leak into rows
    # Case insensitive replacement
    for term in ["particulars", "date", "aly", "amount"]:
        text = re.sub(r"\b" + term + r"\b", "", text, flags=re.IGNORECASE)
    
    # Remove leading/trailing punctuation
    text = text.strip(" .,:;-")
    
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()


def _finalize_item(
    name: str, numeric_values: Dict[str, float], tolerance: float = 0.02
) -> Tuple[str, float, float, float]:
    item_name = _correct_spelling(_strip_trailing_numbers(name).strip(" -"))

    amount = numeric_values.get("amount")
    rate = numeric_values.get("rate")
    quantity = numeric_values.get("quantity")

    # 1. Heal missing/zero Amount if we have Rate and Quantity
    if (amount is None or amount == 0) and rate is not None and quantity is not None:
        amount = rate * quantity

    # 2. Heal missing Rate
    if amount is not None and rate is None and quantity is not None and quantity not in (0, 0.0):
        rate = amount / quantity

    # 3. Heal missing Quantity
    if amount is not None and rate is not None and quantity is None and rate not in (0, 0.0):
        quantity = amount / rate

    # 4. Fallback: If only Rate exists, assume Qty=1
    if amount is None and rate is not None and quantity is None:
        amount = rate
        quantity = 1.0

    # 5. Fallback: If only Amount exists, assume Qty=1, Rate=Amount
    if amount is not None and rate is None and quantity is None:
        rate = amount
        quantity = 1.0

    # Final cleanup of None values
    if amount is None: amount = 0.0
    if rate is None: rate = 0.0
    if quantity is None: quantity = 1.0

    # Consistency Check & Force Correction
    # If we have all three, ensure Amount = Rate * Qty
    # We trust Rate * Qty more than Amount if Amount seems wrong (e.g. 0)
    calc_amount = rate * quantity
    if amount == 0 and calc_amount > 0:
        amount = calc_amount
    elif amount > 0 and calc_amount > 0 and not math.isclose(amount, calc_amount, rel_tol=tolerance):
        # Mismatch. Usually Amount is truth, but if Rate*Qty is clean integer math, it might be better.
        # For now, let's trust the calculated amount if the extracted amount is suspicious?
        # No, usually Amount is the most important field.
        # But for the "X-Ray" case, Amount was 0. We handled that above.
        pass

    return (
        item_name,
        round(float(amount), 2),
        round(float(rate), 2),
        round(float(quantity), 2),
    )


def _clean_description(text: str) -> str:
    """Remove noise, dates, and special characters from description."""
    # Remove dates (DD/MM/YYYY or DD-MM-YYYY)
    text = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", "", text)
    
    # Remove common noise symbols
    text = re.sub(r"[~_»|—]", "", text)
    
    # Remove standalone special characters (e.g. " . " or " : ")
    text = re.sub(r"\s+[^a-zA-Z0-9()]\s+", " ", text)
    
    # Remove leading/trailing punctuation
    text = text.strip(" .,:;-")
    
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()


IGNORED_PHRASES = {
    "room charges",
    "nursing care",
    "laboratory services",
    "consultation",
    "surgery-procedure charges",
    "surgery procedure charges",
    "page of",
    "printed on",
    "particulars",
    "amount",
    "rate",
    "qty",
}


def extract_page_line_items(boxes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert OCR boxes into structured line items using layout-aware heuristics."""
    if not boxes:
        return []

    normalized = [_normalize_box(box) for box in boxes if box.get("text")]
    rows = _cluster_rows(normalized)
    if not rows:
        return []

    header_idx, header_roles = _extract_header_info(rows)
    data_rows = rows[header_idx + 1 :] if header_idx >= 0 else rows
    fallback_centers = _estimate_numeric_columns(data_rows)

    line_items: List[Dict[str, Any]] = []
    pending_description = ""

    for row in data_rows:
        row = _merge_adjacent_numeric_tokens(row)
        name_tokens = []
        numeric_tokens = []

        for box in row:
            if _is_numeric_text(box["text"]):
                numeric_tokens.append(box)
            else:
                name_tokens.append(box)

        row_text = " ".join(token["text"] for token in name_tokens).strip()
        
        # Check for Total rows
        lower_text = row_text.lower()
        if any(keyword in lower_text for keyword in ["total", "grand total", "net amount", "amount due"]):
            continue

        # Check for Ignored Phrases (Headers/Footers)
        # We check if the cleaned text matches exactly or is very close
        clean_check = _clean_description(lower_text)
        if clean_check in IGNORED_PHRASES:
            continue
            
        # Also check if it starts with "Page of"
        if lower_text.startswith("page of") or lower_text.startswith("printed on"):
            continue

        if not numeric_tokens:
            if row_text:
                pending_description = f"{pending_description} {row_text}".strip()
            continue

        description = f"{pending_description} {row_text}".strip() if pending_description else row_text
        pending_description = ""
        if not description:
            description = " ".join(token["text"] for token in row).strip()

        # Clean the description
        description = _clean_description(description)
        if not description:
             continue
             
        # Double check description after cleaning against ignored phrases
        if description.lower() in IGNORED_PHRASES:
            continue

        numeric_values = _assign_numeric_columns(numeric_tokens, header_roles, fallback_centers)
        numeric_values = _derive_columns_from_values(numeric_tokens, numeric_values)
        try:
            item_name, amount, rate, quantity = _finalize_item(description, numeric_values)
        except ValueError:
            continue

        line_items.append(
            {
                "item_name": item_name,
                "item_amount": amount,
                "item_rate": rate,
                "item_quantity": quantity,
            }
        )

    if pending_description and line_items:
        # Append pending text to the last item if it makes sense, or ignore
        # Often trailing text is footer info
        pass

    return line_items

