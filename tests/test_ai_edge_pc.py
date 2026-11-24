from src.watermeter.ai_edge_pc import _evaluate_hybrid_digit


def test_first_digit_uses_integer_part_of_continuous_value():
    assert _evaluate_hybrid_digit(7.8, -1.0, -1) == 7


def test_stable_predecessor_rounds_digit_at_wheel_boundary():
    assert _evaluate_hybrid_digit(2.8, 5.0, 5) == 3


def test_predecessor_rollover_keeps_current_digit_before_its_own_rollover():
    assert _evaluate_hybrid_digit(3.1, 9.8, 9) == 2


def test_predecessor_already_rolled_and_current_digit_past_half():
    assert _evaluate_hybrid_digit(3.8, 0.2, 0) == 4


def test_forward_transition_boundary_is_preserved():
    assert _evaluate_hybrid_digit(3.1, 9.7, 9) == 3
