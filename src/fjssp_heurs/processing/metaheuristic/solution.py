from ...instance.instance import Instance
from ...utils.logger import LOGGER

import numpy as np


class Solution:
    def __init__(self, *, instance: Instance, logger: LOGGER):
        self._instance = instance
        self._logger = logger
        self._create_structure()

    def copy_solution(self, *, sol) -> None:
        self._assign_vect[:] = sol._assign_vect[:]
        self._machine_sequence = sol.machine_sequence
        self._obj = sol._obj

    def _create_structure(self) -> None:
        instance = self._instance
        logger = self._logger
        logger.log("building solution structure")

        self._assign_vect = np.full(len(instance.O), np.nan)
        self._machine_sequence = [[] for _ in instance.M]
        self._obj = 0

        logger.log("solution structure built")

    def get_objective(self, *, omega=10) -> float:
        if np.isnan(self._assign_vect).all() or all(
            not seq for seq in self._machine_sequence
        ):
            self._obj = 0
            return 0

        objective = 0

        # makespan + overlaps

        return objective

    def print(self) -> None:
        instance = self._instance
        logger = self._logger

        logger.log("printing solution")
        with logger:
            logger.log(f"objective: {self.get_objective()}")
            # operation | start_time | end_time | machine_assigned
        logger.breakline()
