import numpy as np

from .solution import Solution
from ...utils.logger import LOGGER


class SolutionBuilder:
    def __init__(self, logger: LOGGER) -> None:
        self._logger = logger

    def build_solution(
        self,
        *,
        solution: Solution,
        machines_strategy: str = "grasp",
        sequence_strategy: str = "greedy",
    ) -> None:
        self.select_machines(solution=solution, strategy=machines_strategy)
        self.sequence_operations(solution=solution, strategy=sequence_strategy)

    def select_machines(self, solution: Solution, strategy: str) -> None:
        if strategy == "greedy":
            self.select_machines_greedy(solution)
        elif strategy == "grasp":
            self.select_machines_grasp(solution)
        else:
            self.select_machines_random(solution)

    def sequence_operations(self, solution: Solution, strategy: str) -> None:
        if strategy == "greedy":
            self.sequence_by_remaining_work(solution)
        else:
            self.sequence_randomly(solution)

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
            if m_candidates:
                solution._assign_vect[o] = np.random.choice(m_candidates)

    def select_machines_grasp(self, solution: Solution, alpha: float = 0.4) -> None:
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
                + alpha * (max(candidates.values()) - min(candidates.values()))
            ]
            solution._assign_vect[o] = np.random.choice(restricted_candidates_list)

    def select_machines_random(self, solution: Solut2ion) -> None:
        instance = solution._instance
        for o in instance.O:
            solution._assign_vect[o] = np.random.choice(instance.M_i[o])

    def sequence_by_remaining_work(self, solution: Solution) -> None:
        instance = solution._instance
        for m in instance.M:
            assigned_operations = [
                op for op, machine in enumerate(solution._assign_vect) if machine == m
            ]

    def sequence_randomly(self, solution: Solution) -> None:
        pass
