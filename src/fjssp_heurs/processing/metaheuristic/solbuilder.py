import numpy as np

from .solution import Solution
from ...utils.logger import LOGGER


class SolutionBuilder:
    def __init__(self, logger: LOGGER) -> None:
        self._logger = logger

    def _define_grasp_alpha(self, *, alpha: float = 0.4) -> None:
        self._logger.log(f"grasp strategy alpha set to: {alpha}")
        self._grasp_alpha = alpha

    def build_solution(
        self,
        *,
        solution: Solution,
        machines_strategy: str = "grasp",
    ) -> None:
        logger = self._logger
        logger.log("building initial solution with constructive heuristic")

        if machines_strategy not in ["grasp", "greedy"]:
            machines_strategy = "random"

        with logger:
            logger.log(f"machines assignment strategy: {machines_strategy}")

            with logger:
                self.select_machines(solution=solution, strategy=machines_strategy)
                logger.log("[1] machines assignment done")

        logger.log("initial solution built")

    def select_machines(self, solution: Solution, strategy: str = "grasp") -> None:
        if strategy == "greedy":
            self.select_machines_greedy(solution)
        elif strategy == "grasp":
            self.select_machines_grasp(solution)
        else:
            self.select_machines_random(solution)

    def select_machines_greedy(self, solution: Solution) -> None:
        instance = solution._instance
        for o in instance.O:
            m_candidates = list()
            best_p = float("inf")
            for m in instance.M_i[o]:
                if instance.p[(o, m)] < best_p:
                    m_candidates = [m]
                    best_p = instance.p[(o, m)]
                elif instance.p[(o, m)] == best_p:
                    m_candidates.append(m)
            solution._assign_vect[o] = np.random.choice(m_candidates)

    def select_machines_grasp(self, solution: Solution) -> None:
        instance = solution._instance
        for o in instance.O:
            candidates = dict()
            for m in instance.M_i[o]:
                candidates[m] = instance.p[(o, m)]
            restricted_candidates_list = [
                machine
                for machine in candidates.keys()
                if candidates[machine]
                <= min(candidates.values())
                + self._grasp_alpha
                * (max(candidates.values()) - min(candidates.values()))
            ]
            solution._assign_vect[o] = np.random.choice(restricted_candidates_list)

    def select_machines_random(self, solution: Solution) -> None:
        instance = solution._instance
        for o in instance.O:
            solution._assign_vect[o] = np.random.choice(list(instance.M_i[o]))
