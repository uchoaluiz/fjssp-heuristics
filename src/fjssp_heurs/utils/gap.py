def evaluate_gap(*, ub: float, lb: float) -> float:
    if not isinstance(ub, float) or not isinstance(lb, float):
        return "nan"

    return round((100 * (ub - lb) / ub), 4)
