from ...instance.instance import Instance
from ...utils.logger import LOGGER
from ...utils.plotting import plot_gantt
from ...utils.gap import evaluate_gap

from pathlib import Path
import numpy as np


class Solution:
    def __init__(self, *, instance: Instance, logger: LOGGER, output_path: Path):
        self._instance = instance
        self._logger = logger
        self._output_path = output_path
        self._create_structure()

    def _create_structure(self) -> None:
        instance = self._instance
        logger = self._logger
        logger.log("building solution structure")

        self._assign_vect = np.full(len(instance.O), np.nan)
        self._machine_sequence = [[] for _ in instance.M]
        self._start_times = np.zeros(len(instance.O))
        self._finish_times = np.zeros(len(instance.O))
        self._makespan = 0.0
        self._obj = 0.0

        logger.log("solution structure built")

    def _evaluate_objective(self) -> None:
        instance = self._instance
        logger = self._logger

        start_times = self._start_times

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

        if overlap_penalty:
            with logger:
                logger.log(f"overlaps in solution | penalty: {overlap_penalty}")

        return self._makespan, overlap_penalty

    def evaluate_solution(self, *, omega: int = 10) -> float:
        if np.isnan(self._assign_vect).all():
            self._obj = 0
            return 0

        makespan, overlap_penalty = self._evaluate_objective()
        self._obj = makespan + omega * overlap_penalty

        return self._obj

    def find_critical_path(self):
        instance = self._instance

        critical_ops = [
            op for op in instance.O if self._finish_times[op] == self._makespan
        ]
        critical_path = []

        while critical_ops:
            current_op = critical_ops.pop()
            critical_path.append(current_op)

            machine = int(self._assign_vect[current_op])
            machine_seq = self._machine_sequence[machine]
            op_index = machine_seq.index(current_op)
            if op_index > 0:
                pred_machine = machine_seq[op_index - 1]
                if self._finish_times[pred_machine] == self._start_times[current_op]:
                    critical_ops.append(pred_machine)

            job = instance.job_of_op[current_op]
            job_ops = instance.O_j[job]
            op_pos = job_ops.index(current_op)
            if op_pos > 0:
                pred_job = job_ops[op_pos - 1]
                if self._finish_times[pred_job] == self._start_times[current_op]:
                    critical_ops.append(pred_job)

        return list(reversed(critical_path))

    def print(self, *, show_gantt: bool = True) -> None:
        logger = self._logger
        logger.log("printing solution")

        if np.isnan(self._assign_vect).all():
            with logger:
                logger.log("empty solution")
            return None

        instance = self._instance
        objective_value = self.evaluate_solution()

        with logger:
            logger.log(
                f"objective: {objective_value} | gap: {evaluate_gap(ub=objective_value, lb=self._instance.optimal_solution)}%"
            )
            for op in instance.O:
                logger.log(
                    f"operation: {op} | start time: {self._start_times[op]} | machine assigned: {self._assign_vect[op]} | end time: {self._start_times[op] + instance.p[(op, self._assign_vect[op])]}"
                )

        gantt_path = (
            self._output_path
            / f"{self._instance._instance_name} - heuristic solution gantt.png"
        )
        logger.log(f"saving solution's gantt graph into path: '{gantt_path}'")

        plot_gantt(
            start_times={i: self._start_times[i] for i in instance.O},
            machine_assignments={i: int(self._assign_vect[i]) for i in instance.O},
            processing_times=instance.p,
            job_of_op=instance.job_of_op,
            machine_set=instance.M,
            title=f"{self._instance._instance_name} - heuristic solution gantt",
            verbose=show_gantt,
            output_file_path=gantt_path,
        )

    def copy_solution(self, *, sol) -> None:
        self._assign_vect[:] = sol._assign_vect[:]
        self._machine_sequence = sol._machine_sequence
        self._start_times = sol._start_times
        self._finish_times = sol._finish_times
        self._obj = sol._obj
        self._makespan = sol._makespan
