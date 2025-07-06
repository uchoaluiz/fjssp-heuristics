def evaluate_gap(*, ub: float, lb: float) -> float:
    if not ub or not lb:
        return "nan"

    return round((100 * (ub - lb) / ub), 4)
