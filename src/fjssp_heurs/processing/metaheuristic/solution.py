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
        self._start_times_vect[:] = sol._start_times_vect[:]
        self._obj = sol._obj

    def _create_structure(self) -> None:
        logger = self._logger
        logger.log("building solution representation structure")

        self._assign_vect = np.full(len(self._instance.O), np.nan)
        self._start_times_vect = np.full(len(self._instance.O), np.nan)
        self._obj = 0

        logger.log("solution representation structure built")
    
    def get_objective(self, *, omega = 10) -> float:
        if np.isnan(self._assign_vect).all() or np.isnan(self._start_times_vect).all():
            self._obj = 0
            return 0

        instance = self._instance
        start_times = self._start_times_vect
        assignments = self._assign_vect
        processing_times = instance.p
        operations = instance.O

        makespan = 0
        overlap_penalty = 0

        for m in instance.M:
            ops_on_m = instance.O_m[m]

            ops_on_m.sort(key=lambda i: start_times[i])

            for idx1 in range(len(ops_on_m)):
                i = ops_on_m[idx1]
                si = start_times[i]
                pi = processing_times[(i, m)]
                fi = si + pi

                for idx2 in range(idx1 + 1, len(ops_on_m)):
                    j = ops_on_m[idx2]
                    sj = start_times[j]
                    pj = processing_times[(j, m)]
                    fj = sj + pj

                    overlap = max(0, min(fi, fj) - max(si, sj))
                    if overlap > 0:
                        overlap_penalty += overlap

        for i in operations:
            m = assignments[i]
            end_time = start_times[i] + processing_times[(i, m)]
            if end_time > makespan:
                makespan = end_time

        total_obj = makespan + omega * overlap_penalty
        self._obj = total_obj
        return total_obj
    
    def print(self) -> None:
        inst = self._instance
        logger = self._logger

        logger.log("printing solution")
        with logger:
            logger.log(f"objective: {self.get_objective()}")
            for op in inst.O:
                logger.log(f"operation: {op} | start time: {self._start_times_vect[op]} | machine assigned: {self._assign_vect[op]}")
        logger.breakline()
