from ..instance.instance import Instance
from ..utils.crono import Crono
from ..utils.logger import LOGGER
from ..utils.plotting import plot_gantt
from ..utils.gap import evaluate_gap

from mip import Model, xsum, minimize, CBC, OptimizationStatus, BINARY, CONTINUOUS
from pathlib import Path


class MathModel:
    def __init__(
        self, *, instance: Instance, output_path: Path, logger: LOGGER
    ) -> None:
        self._instance = instance
        self._elapsed_time = 0.0
        self._output_path = output_path
        self._logger = logger
        self._create_model()

    def _create_model(self) -> None:
        logger = self._logger
        instance = self._instance

        logger.log("building mathematical model")
        with logger:
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

            logger.log("[1] decision vars created")

            self.model.objective = minimize(c_max)

            logger.log("[2] objective function defined")

            for i in instance.O:
                self.model += (
                    c_max
                    >= x.get(i, 0)
                    + xsum(
                        instance.p[(i, m)] * z.get((i, m), 0) for m in instance.M_i[i]
                    ),
                    f"makespan_def_{i}",
                )

            logger.log("[3] constraints R1 created")

            for j in range(instance.num_jobs):
                seq = instance.P_j[j]
                for i, i_ in seq:
                    self.model += (
                        x.get(i_, 0)
                        >= x.get(i, 0)
                        + xsum(
                            instance.p[(i, m)] * z.get((i, m), 0)
                            for m in instance.M_i[i]
                        ),
                        f"preced_{i}_{i_}",
                    )

            logger.log("[4] constraints R2 created")

            for i in instance.O:
                self.model += (
                    xsum(z.get((i, m), 0) for m in instance.M_i[i]) == 1,
                    f"machine_assign_{i}",
                )

            logger.log("[5] constraints R3 created")

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

            logger.log("[6] constraints R4 & R5 created")

            self.x = x
            self.z = z
            self.y = y
            self.c_max = c_max

        logger.log("mathematical model completely built")
        logger.breakline()

    def optimize(
        self,
        *,
        verbose: int = 0,
        time_limit: int = 1800,
    ) -> None:
        logger = self._logger

        logger.log("starting CBC optimization")

        self.model.verbose = verbose if verbose in [0, 1] else 0

        timer = Crono()
        self._status = self.model.optimize(max_seconds=time_limit)
        self._elapsed_time = round(timer.stop(), 4)

        logger.log(
            f"optimization finished | elapsed time: {self._elapsed_time} s | makespan: {self.c_max.x if self.model.num_solutions else None}"
        )

    def print(self, *, show_gantt: bool = True) -> None:
        logger = self._logger

        with logger:
            if self.model.num_solutions:
                makespan = self.c_max.x
                gap = evaluate_gap(ub=makespan, lb=self._instance.optimal_solution)

                if self._status == OptimizationStatus.FEASIBLE:
                    logger.log(f"feasible integer solution found | gap = {gap}%")
                if self._status == OptimizationStatus.OPTIMAL:
                    logger.log(f"optimal solution found | gap = {gap}%")

                start_times = dict()
                machines_assignments = dict()

                with logger:
                    logger.log(f"makespan: {makespan}")

                    for i in self._instance.O:
                        start = self.x[i].x
                        machine = [
                            m
                            for m in self._instance.M_i[i]
                            if self.z.get((i, m), 0).x >= 0.99
                        ][0]

                        start_times[i] = start
                        machines_assignments[i] = machine

                        logger.log(
                            f"operation: {i} | machine assigned: {machine} | start time: {start} | end time: {start + self._instance.p[(i, machine)]}"
                        )

                gantt_path = (
                    self._output_path
                    / f"{self._instance._instance_name} - solver solution gantt.png"
                )
                logger.log(
                    f"saving optimized solution's gantt graph into path: '{gantt_path}'"
                )

                plot_gantt(
                    start_times=start_times,
                    machine_assignments=machines_assignments,
                    processing_times=self._instance.p,
                    job_of_op=self._instance.job_of_op,
                    machine_set=self._instance.M,
                    title=f"{self._instance._instance_name} - solver solution gantt",
                    verbose=show_gantt,
                    output_file_path=gantt_path,
                )
            else:
                logger.log("no feasible integer solution found in time limit :c")
        logger.breakline()
