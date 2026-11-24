from src.watermeter.ai_edge_pc import _decode_double_hybrid10, _evaluate_hybrid_digit


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



def test_double_hybrid10_interpolates_towards_next_digit():
    outputs = [0.0] * 10
    outputs[4] = 0.6
    outputs[5] = 0.3
    outputs[3] = 0.1

    result = _decode_double_hybrid10(outputs)

    assert result["class_index"] == 4
    assert abs(result["continuous_value"] - 4.3333333) < 1e-5
    assert abs(result["fit"] - 0.9) < 1e-6


def test_double_hybrid10_interpolates_towards_previous_digit():
    outputs = [0.0] * 10
    outputs[4] = 0.6
    outputs[3] = 0.3
    outputs[5] = 0.1

    result = _decode_double_hybrid10(outputs)

    assert abs(result["continuous_value"] - 3.6666667) < 1e-5


def test_double_hybrid10_wraps_from_nine_to_zero():
    outputs = [0.0] * 10
    outputs[9] = 0.6
    outputs[0] = 0.3
    outputs[8] = 0.1

    result = _decode_double_hybrid10(outputs)

    assert abs(result["continuous_value"] - 9.3333333) < 1e-5
