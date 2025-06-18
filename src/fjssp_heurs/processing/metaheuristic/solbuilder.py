import numpy as np

from .solution import Solution
from ...utils.logger import LOGGER

class SolutionBuilder():
    def __init__(self, logger: LOGGER) -> None:
        self._logger = logger

    def build_solution(self, *, solution: Solution, machines_strategy: str = "greedy", sequence_strategy: str = "greedy") -> None:
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
        pass

    def select_machines_grasp(self, solution: Solution) -> None:
        pass

    def select_machines_random(self, solution: Solution) -> None:
        pass

    def sequence_by_remaining_work(self, solution: Solution) -> None:
        pass

    def sequence_randomly(self, solution: Solution) -> None:
        pass
