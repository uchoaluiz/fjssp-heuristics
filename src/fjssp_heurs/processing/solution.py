from ..instance.instance import Instance
from ..

import numpy as np


class Solution:
    def __init__(self, *, instance: Instance):
        self._instance = instance
        self._create_structure()

    def copy_solution(self, *, sol) -> None:
        self._assign_vect[:] = sol._assign_vect[:]
        self._start_times_vect[:] = sol._start_times_vect[:]
        self._obj = sol._obj

    def _create_structure(self) -> None:
        self._assign_vect = np.empty(len(self._instance.O))
        self._start_times_vect = np.empty(len(self._instance.O))
        self._obj = 0

        print("   > solution structure built")
    
    def get_objective(self, *, omega = 10) -> float:
        instance = self._instance
        start_times = self._start_times_vect
        assignments = self._assign_vect
        processing_times = instance.p
        operations = instance.O

        makespan = 0
        overlap_penalty = 0

        for m in instance.M:
            ops_on_m = [i for i in operations if assignments[i] == m]

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
        pass

