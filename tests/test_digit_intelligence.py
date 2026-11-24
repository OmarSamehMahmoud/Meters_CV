import numpy as np

from src.watermeter.digit_reader import split_register_cells, compose_digit_cells


def test_split_register_into_five_ordered_overlapping_cells():
    image = np.zeros((40, 500, 3), dtype=np.uint8)
    cells = split_register_cells(image, expected_digits=5, overlap=0.08)
    assert len(cells) == 5
    assert all(cell.shape[0] == 40 and cell.shape[1] > 100 for cell in cells)


def test_split_register_rejects_invalid_input():
    assert split_register_cells(np.zeros((0, 20, 3), dtype=np.uint8)) == []
    assert split_register_cells(np.zeros((10, 2, 3), dtype=np.uint8), expected_digits=5) == []


def test_compose_digit_cells_preserves_position_and_flags_missing():
    cells = [
        {"position": 1, "digit": "1", "confidence": 0.9},
        {"position": 2, "digit": "2", "confidence": 0.8},
        {"position": 3, "digit": None, "confidence": 0.0},
        {"position": 4, "digit": "4", "confidence": 0.9},
        {"position": 5, "digit": "5", "confidence": 0.9},
    ]
    reading, complete = compose_digit_cells(cells)
    assert reading == "1245"
    assert not complete
