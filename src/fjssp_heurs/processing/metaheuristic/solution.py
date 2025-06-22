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
        self._start_times = np.zeros(len(instance.O))
        self._obj = 0

        logger.log("solution structure built")

    def compute_schedule(self) -> np.array:
        instance = self._instance

        start_times = np.zeros(len(instance.O))
        ready_times = np.zeros(len(instance.O))

        for job_precedences in instance.P_j:
            for i, i_prime in job_precedences:
                m_i = int(self._assign_vect[i])
                p_i = instance.p[(i, m_i)]
                ready_times[i_prime] = max(ready_times[i_prime], ready_times[i] + p_i)

        for m, op_sequence in enumerate(self._machine_sequence):
            current_time = 0
            for i in op_sequence:
                earliest = max(current_time, ready_times[i])
                start_times[i] = earliest
                current_time = earliest + instance.p[(i, m)]

        return start_times

    def get_objective(self, *, omega=10) -> float:
        if np.isnan(self._assign_vect).all() or all(
            not seq for seq in self._machine_sequence
        ):
            self._obj = 0
            return 0

        instance = self._instance
        start_times = self.compute_schedule()
        self._start_times = start_times

        makespan = 0
        for i in instance.O:
            m_i = int(self._assign_vect[i])
            end_time = start_times[i] + instance.p[(i, m_i)]
            makespan = max(makespan, end_time)

        overlap_penalty = 0
        for m, op_sequence in enumerate(self._machine_sequence):
            for idx1 in range(len(op_sequence)):
                i1 = op_sequence[idx1]
                m1 = int(self._assign_vect[i1])
                s1 = start_times[i1]
                f1 = s1 + instance.p[(i1, m1)]

                for idx2 in range(idx1 + 1, len(op_sequence)):
                    i2 = op_sequence[idx2]
                    m2 = int(self._assign_vect[i2])
                    s2 = start_times[i2]
                    f2 = s2 + instance.p[(i2, m2)]

                    if m1 == m2:
                        overlap = max(0, min(f1, f2) - max(s1, s2))
                        overlap_penalty += overlap

        self._obj = makespan + overlap_penalty
        return self._obj

    def print(self) -> None:
        instance = self._instance
        logger = self._logger

        logger.log("printing solution")
        with logger:
            logger.log(f"objective: {self.get_objective()}")
            for op in instance.O:
                logger.log(
                    f"operation: {op} | start time: {self._start_times[op]} | machine assigned: {self._assign_vect[op]} | end time: {self._start_times[op] + instance.p[(op, self._assign_vect[op])]}"
                )
        logger.breakline()
