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

        self._start_times = np.full(len(instance.O), np.nan)
        self._finish_times = np.full(len(instance.O), np.nan)

        logger.log("solution structure built")

    def _get_machines_assignment(self) -> str:
        machine_assignment = dict()
        for machine in self._instance.M:
            ops_in_m = list()
            for op, m in enumerate(self._assign_vect):
                if machine == m:
                    ops_in_m.append(op)
            machine_assignment[machine] = ops_in_m
        return machine_assignment

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
