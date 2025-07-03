from ..instance.instance import Instance
from ..utils.crono import Crono
from ..utils.logger import LOGGER
from ..utils.plotting import plot_gantt
from ..utils.gap import evaluate_gap
from ..utils.graph import FJSSPGraph

from mip import Model, xsum, minimize, CBC, OptimizationStatus, BINARY, CONTINUOUS
from pathlib import Path


class MathModel:
    def __init__(self, *, instance: Instance, logger: LOGGER) -> None:
        self._instance = instance
        self._elapsed_time = 0.0
        self._logger = logger

        self._makespan = 0.0
        self._assign_vect = list()
        self._machine_scheduling = list()
        self._start_times = list()

        h = 1
        with logger:
            for status in self._create_model():
                logger.log(f"[{h}] {status}")
                h += 1

    def _create_model(self):
        instance = self._instance

        self.model = Model("FJSSP", solver_name=CBC)
        big_m = 1e5

        x = {
            i: self.model.add_var(name=f"x_{i}", var_type=CONTINUOUS, lb=0.0)
            for i in instance.O
        }
        z = {
            (i, m): self.model.add_var(name=f"z_{i}_{m}", var_type=BINARY)
            for i in instance.O
            for m in instance.M_i[i]
        }
        y = {
            (i, j, m): self.model.add_var(name=f"y_{i}_{j}_{m}", var_type=BINARY)
            for m in instance.M
            for i in instance.O_m[m]
            for j in instance.O_m[m]
            if i < j
        }
        c_max = self.model.add_var(name="c_max", var_type=CONTINUOUS, lb=0.0)

        yield "decision vars created"

        self.model.objective = minimize(c_max)

        yield "objective function defined"

        for i in instance.O:
            self.model += (
                c_max
                >= x.get(i, 0)
                + xsum(instance.p[(i, m)] * z.get((i, m), 0) for m in instance.M_i[i]),
                f"makespan_def_{i}",
            )

        yield "constraints R1 created"

        for j in range(instance.num_jobs):
            seq = instance.P_j[j]
            for i, i_ in seq:
                self.model += (
                    x.get(i_, 0)
                    >= x.get(i, 0)
                    + xsum(
                        instance.p[(i, m)] * z.get((i, m), 0) for m in instance.M_i[i]
                    ),
                    f"preced_{i}_{i_}",
                )

        yield "constraints R2 created"

        for i in instance.O:
            self.model += (
                xsum(z.get((i, m), 0) for m in instance.M_i[i]) == 1,
                f"machine_assign_{i}",
            )

        yield "constraints R3 created"

        for m in instance.M:
            ops = instance.O_m[m]
            for i in ops:
                for j in ops:
                    if i >= j:
                        continue
                    pij = instance.p.get((i, m), 0)
                    pji = instance.p.get((j, m), 0)

                    self.model += (
                        x.get(j, 0)
                        >= x.get(i, 0)
                        + pij
                        - big_m
                        * (
                            1
                            - y.get((i, j, m), 0)
                            + 1
                            - z.get((i, m), 0)
                            + 1
                            - z.get((j, m), 0)
                        ),
                        f"no_overlap_1_{i}_{j}_{m}",
                    )

                    self.model += (
                        x.get(i, 0)
                        >= x.get(j, 0)
                        + pji
                        - big_m
                        * (
                            y.get((i, j, m), 0)
                            + 1
                            - z.get((i, m), 0)
                            + 1
                            - z.get((j, m), 0)
                        ),
                        f"no_overlap_2_{i}_{j}_{m}",
                    )

        yield "constraints R4 & R5 created\n"

        self.x = x
        self.z = z
        self.y = y
        self.c_max = c_max

    def optimize(
        self,
        *,
        verbose: int = 0,
        time_limit: int = 1800,
    ) -> tuple:
        logger = self._logger

        self.model.verbose = verbose if verbose in [0, 1] else 0

        timer = Crono()
        self._status = self.model.optimize(max_seconds=time_limit)
        self._elapsed_time = round(timer.stop(), 4)

        if self.model.num_solutions:
            self._makespan = self.c_max.x if self.model.num_solutions else None

            self._assign_vect = [
                machine
                for op in self._instance.O
                for machine in self._instance.M_i[op]
                if self.z.get((op, machine), 0).x == 1
            ]

            self._start_times = [self.x.get((op), 0).x for op in self._instance.O]

            for machine in self._instance.M:
                ops_in_m = list()
                for op, m in enumerate(self._assign_vect):
                    if machine == m:
                        ops_in_m.append(op)
                ops_in_m = sorted(ops_in_m, key=lambda i: self._start_times[i])
                self._machine_scheduling.append(ops_in_m)

            logger.log(
                f"optimization finished | elapsed time: {self._elapsed_time} s | makespan: {self._makespan}"
            )

            gap = evaluate_gap(ub=self._makespan, lb=self._instance.optimal_solution)

            if self._status == OptimizationStatus.FEASIBLE:
                logger.log(f"feasible integer solution found | gap = {gap}%")
            if self._status == OptimizationStatus.OPTIMAL:
                logger.log(f"optimal solution found | gap = {gap}%")
        else:
            logger.log("no feasible integer solution found in time limit :c")

        logger.breakline()

        return self._makespan, self._elapsed_time

    def _machine_of_op(self, *, op: int) -> int:
        for machine, ops in self._machine_scheduling:
            if op in ops:
                return machine

    def print(self, *, print_style: str = "array") -> None:
        logger = self._logger

        with logger:
            if self.model.num_solutions:
                makespan = self.c_max.x

                with logger:
                    logger.log(f"makespan: {makespan}")

                    if print_style == "each_op":
                        for i in self._instance.O:
                            start = self.x[i].x
                            machine = [
                                m
                                for m in self._instance.M_i[i]
                                if self.z.get((i, m), 0).x >= 0.99
                            ][0]

                            logger.log(
                                f"operation: {i} | machine assigned: {machine} | start time: {start} | end time: {start + self._instance.p[(i, machine)]}"
                            )

                    if print_style == "arrays":
                        for m, seq in enumerate(self._machine_scheduling):
                            logger.log(
                                f"machine: {m} | sequence: {seq} | start times: {[self._start_times[op] for op in seq]} | finish times: {[self._start_times[op] + self._instance.p[(op, m)] for op in seq]}"
                            )
            else:
                logger.log("no feasible integer solution found in time limit :c")

            logger.breakline()

    def save_gantt(self, gantt_output_path: Path) -> None:
        logger = self._logger

        with logger:
            gantt_path = (
                gantt_output_path
                / f"{self._instance._instance_name} - solver solution.png"
            )

            try:
                plot_gantt(
                    start_times=self._start_times,
                    machine_assignments=self._machine_scheduling,
                    instance=self._instance,
                    title=f"{self._instance._instance_name} - gantt - solver solution",
                    verbose=False,
                    output_file_path=gantt_path,
                )
            except Exception as e:
                logger.log("couldn't plot gantt graph for solver solution")
                with logger:
                    logger.log(e)

        logger.breakline()

    def create_dag(self, *, tech_disjunc: bool = False) -> None:
        self._graph = FJSSPGraph(
            instance=self._instance,
            machines_assignment=self._machine_scheduling,
            tech_disjunc=tech_disjunc,
        )

    def export_dag(
        self,
        dag_output_path: Path,
        title: str,
        arrowstyle: str = "->",
        show: str = "disjunctives",
    ) -> None:
        self._graph.export_visualization(
            output_path=dag_output_path, title=title, arrowstyle=arrowstyle, show=show
        )
