from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class ReadingResult:
    reading_m3: Optional[float]
    integer_digits: Optional[str]
    fractional_digits: Optional[dict]
    confidence: float
    status: str
    quality_flags: list[str]
    model_version: str = "pc-baseline-0.1"

def validate_monotonic(current: float, previous: float | None) -> tuple[bool, list[str]]:
    flags=[]
    if previous is not None and current < previous:
        flags.append("reading_decreased")
    return not flags, flags
