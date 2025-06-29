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

    def copy_solution(self, *, sol) -> None:
        self._assign_vect[:] = sol._assign_vect[:]
        self._machine_sequence = sol._machine_sequence
        self._makespan = sol._makespan

        self._start_times = sol._start_times
        self._finish_times = sol._finish_times

    def _create_structure(self) -> None:
        instance = self._instance
        logger = self._logger
        logger.log("building solution structure")

        self._assign_vect = np.full(len(instance.O), np.nan)
        self._machine_sequence = [[] for _ in instance.M]
        self._makespan = 0.0

        self._start_times = list()
        self._finish_times = list()
        logger.log("solution structure built")

    def _find_a_critical_path(self) -> list[int]:
        instance = self._instance
        start_times = self._start_times
        finish_times = self._finish_times
        assign_vect = self._assign_vect
        machine_sequence = self._machine_sequence
        makespan = self._makespan

        end_ops = [op for op in instance.O if finish_times.index(makespan) == op]
        if not end_ops:
            raise ValueError(
                "Nenhuma operação encontrada com término igual ao makespan."
            )

        current_op = np.random.choice(end_ops)
        critical_path = [current_op]

        while start_times[current_op] > 0:
            pred_ops = []

            job = instance.job_of_op[current_op]
            job_ops = instance.S_j[job]
            idx_in_job = job_ops.index(current_op)
            if idx_in_job > 0:
                prev_job_op = job_ops[idx_in_job - 1]
                if finish_times[prev_job_op] == start_times[current_op]:
                    pred_ops.append(prev_job_op)

            machine = int(assign_vect[current_op])
            mach_ops = machine_sequence[machine]
            idx_in_machine = mach_ops.index(current_op)
            if idx_in_machine > 0:
                prev_mach_op = mach_ops[idx_in_machine - 1]
                if finish_times[prev_mach_op] == start_times[current_op]:
                    pred_ops.append(prev_mach_op)

            if not pred_ops:
                break

            current_op = np.random.choice(pred_ops)
            critical_path.insert(0, current_op)

        return list(map(lambda x: int(x), critical_path))

    def print(self, *, show_gantt: bool = True, gantt_name: str) -> None:
        logger = self._logger
        logger.log("printing solution")

        if np.isnan(self._assign_vect).all():
            with logger:
                logger.log("empty solution")
            return None

        instance = self._instance
        makespan = self._makespan

        with logger:
            logger.log(
                f"makespan: {makespan} | gap: {evaluate_gap(ub=makespan, lb=self._instance.optimal_solution)}%"
            )
            for op in instance.O:
                logger.log(
                    f"operation: {op} | machine assigned: {self._assign_vect[op]} | start time: {self._start_times[op]} | end time: {self._start_times[op] + instance.p[(op, self._assign_vect[op])]}"
                )

        gantt_path = (
            self._output_path
            / f"{self._instance._instance_name} - gantt - {gantt_name}.png"
        )
        logger.log(f"saving solution's gantt graph into path: '{gantt_path}'")

        plot_gantt(
            start_times={i: self._start_times[i] for i in instance.O},
            machine_assignments={i: int(self._assign_vect[i]) for i in instance.O},
            processing_times=instance.p,
            job_of_op=instance.job_of_op,
            machine_set=instance.M,
            title=f"{self._instance._instance_name} - Gantt - {gantt_name}",
            verbose=show_gantt,
            output_file_path=gantt_path,
        )
