from src.watermeter.reading import validate_monotonic

def test_monotonic_accepts_increase():
    ok,flags=validate_monotonic(12.5,12.0)
    assert ok and flags==[]

def test_monotonic_flags_decrease():
    ok,flags=validate_monotonic(11.0,12.0)
    assert not ok and "reading_decreased" in flags
