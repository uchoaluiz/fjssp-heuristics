def evaluate_gap(*, ub: float, lb: float) -> float:
    return round((100 * (ub - lb) / ub), 4)
