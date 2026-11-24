from __future__ import annotations

import numpy as np


def split_register_cells(image: np.ndarray, expected_digits: int = 5, overlap: float = 0.08):
    """Split a fixed-width register ROI into ordered, slightly overlapping crops."""
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        return []
    if expected_digits < 1 or image.ndim < 2 or image.shape[1] < expected_digits:
        return []
    overlap = min(max(float(overlap), 0.0), 0.24)
    width = image.shape[1]
    cell_width = width / expected_digits
    cells = []
    for index in range(expected_digits):
        left = max(0, int(round(index * cell_width - cell_width * overlap)))
        right = min(width, int(round((index + 1) * cell_width + cell_width * overlap)))
        if right <= left:
            return []
        cells.append(image[:, left:right].copy())
    return cells


def compose_digit_cells(cells):
    """Compose recognized digits in position order; never invent missing digits."""
    ordered = sorted(cells, key=lambda item: int(item["position"]))
    reading = "".join(str(item["digit"]) for item in ordered if item.get("digit") is not None)
    complete = len(ordered) == 5 and all(
        item.get("digit") is not None and float(item.get("confidence", 0.0)) >= 0.35
        for item in ordered
    )
    return reading, complete
