from ...instance.instance import Instance
from ...utils.logger import LOGGER
from ...utils.plotting import plot_gantt
from ...utils.gap import evaluate_gap
from ...utils.graph import FJSSPGraph

from pathlib import Path
import numpy as np


class Solution:
    def __init__(self, *, instance: Instance, logger: LOGGER):
        self._instance = instance
        self._logger = logger
        self._create_structure()

    def copy_solution(self, *, sol) -> None:
        self._assign_vect[:] = sol._assign_vect[:]
        self._machine_sequence = sol._machine_sequence
        self._makespan = sol._makespan

        if hasattr(sol, "_graph"):
            self._graph = sol._graph

        self._start_times = sol._start_times
        self._finish_times = sol._finish_times

    def _create_structure(self) -> None:
        instance = self._instance

        self._assign_vect = np.full(len(instance.O), np.nan)
        self._machine_sequence = [[] for _ in instance.M]
        self._makespan = float("inf")

        self._start_times = list()
        self._finish_times = list()

    def create_graph(self, *, tech_disjunc: bool = False, graph_type: str):
        self._graph = FJSSPGraph(
            instance=self._instance,
            machines_assignment=self._get_machines_assignment(),
            tech_disjunc=tech_disjunc,
            graph_type=graph_type,
        )

    def export_dag(
        self,
        dag_output_path: Path,
        title: str,
        arrowstyle: str = "->",
        show: str = "visual disjunctives",
    ) -> None:
        self._graph.export_visualization(
            output_path=dag_output_path, title=title, arrowstyle=arrowstyle, show=show
        )

    def _find_a_critical_path(self) -> tuple[list[int], int]:
        instance = self._instance
        start_times = self._start_times
        finish_times = self._finish_times
        assign_vect = self._assign_vect
        machine_sequence = self._machine_sequence
        makespan = self._makespan

        multiple_critical_paths = 0

        end_ops = [op for op in instance.O if finish_times.index(makespan) == op]
        if not end_ops:
            raise ValueError("no operations with finish time = makespan.")

        if len(end_ops) > 1:
            multiple_critical_paths = 1

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

            if len(pred_ops) > 1:
                multiple_critical_paths = 1

            current_op = np.random.choice(pred_ops)
            critical_path.insert(0, current_op)

        return list(map(lambda x: int(x), critical_path)), multiple_critical_paths

    def _get_machines_assignment(self):
        instance = self._instance

        machines_assignment = [list() for _ in instance.M]
        for op in instance.O:
            machine = self._assign_vect[op]
            machines_assignment[int(machine)].append(op)

        return machines_assignment

    def reset_to_jssp(self) -> None:
        self._machine_sequence = self._get_machines_assignment()
        self._start_times = []
        self._finish_times = []
        self._makespan = float("inf")
        if hasattr(self, "_graph"):
            self._graph = FJSSPGraph(
                instance=self._instance,
                machines_assignment=self._machine_sequence,
                tech_disjunc=True,
                graph_type="partial fjssp",
            )

    def _recalculate_times(self, logger: LOGGER) -> float:
        if not all(
            self._graph._are_sequence_consolidated(machine_id=m)
            for m, seq in enumerate(self._machine_sequence)
            if seq
        ):
            with logger:
                logger.log(
                    "not all disjunctives edges of the machines sequence are consolidated"
                )

                """
                print("consolidating it")
                for m, ops in enumerate(self._machine_sequence):
                    self._graph.consolidate_sequence_on_machine(machine_id=m, sequence=ops)
                """
                logger.log("ignoring it")

        instance = self._instance
        self._start_times = []
        self._finish_times = []

        for op in instance.O:
            start_time = self._graph.longest_path_to(op=op)
            machine = int(self._assign_vect[op])
            processing_time = instance.p[(op, machine)]

            self._start_times.append(start_time)
            self._finish_times.append(start_time + processing_time)

        self._makespan = max(self._finish_times)
        return self._makespan

    def save_gantt(self, *, gantt_output: Path, gantt_title: str) -> None:
        logger = self._logger

        with logger:
            gantt_path = (
                gantt_output
                / f"{self._instance._instance_name} - heur - {gantt_title}.png"
            )

            try:
                plot_gantt(
                    start_times=self._start_times,
                    machine_assignments=self._machine_sequence,
                    instance=self._instance,
                    title=f"{self._instance._instance_name} - gantt - {gantt_title}",
                    verbose=False,
                    output_file_path=gantt_path,
                )
            except Exception as e:
                logger.log("couldn't plot gantt graph for heur solution")
                with logger:
                    logger.log(e)

    def print(
        self,
        *,
        print_style: str = "arrays",
    ) -> None:
        logger = self._logger

        if (
            np.isnan(self._assign_vect).all()
            or not self._start_times
            or not self._finish_times
        ):
            with logger:
                logger.log("empty solution")
            return None

        with logger:
            instance = self._instance
            makespan = self._makespan

            logger.log(
                f"makespan: {makespan} | "
                f"gap: {evaluate_gap(ub=makespan, lb=self._instance.optimal_solution)}%"
            )

            if print_style == "each_op":
                for op in instance.O:
                    logger.log(
                        f"op: {op} | "
                        f"machine: {self._assign_vect[op]} | "
                        f"start: {self._start_times[op]} | "
                        f"end: {self._start_times[op] + instance.p[(op, self._assign_vect[op])]}"
                    )

            elif print_style == "arrays":
                for m, ops in enumerate(self._machine_sequence):
                    logger.log(
                        f"m: {m} | "
                        f"seq: {ops} | "
                        f"starts: {[self._start_times[op] for op in ops]} | "
                        f"ends: {[(self._start_times[op] + instance.p[(op, m)]) for op in ops]}"
                    )
