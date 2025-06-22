from ..instance.instance import Instance
from ..utils.crono import Crono
from ..utils.logger import LOGGER

from mip import Model, xsum, minimize, CBC, OptimizationStatus, BINARY, CONTINUOUS
from pathlib import Path


class MathModel:
    def __init__(
        self, *, instance: Instance, output_folder: Path, logger: LOGGER
    ) -> None:
        self._instance = instance
        self._output_folder = output_folder
        self._logger = logger
        self._create_model()

    def _create_model(self) -> None:
        logger = self._logger

        logger.log("building mathematical model")
        with logger:
            instance = self._instance
            # instance.print(logger=logger, type="array")

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

            logger.log("decision vars created")

            self.model.objective = minimize(c_max)

            logger.log("objective function defined")

            for i in instance.O:
                self.model += (
                    c_max
                    >= x.get(i, 0)
                    + xsum(
                        instance.p[(i, m)] * z.get((i, m), 0) for m in instance.M_i[i]
                    ),
                    f"makespan_def_{i}",
                )

            logger.log("constraints R1 created")

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

            logger.log("constraints R2 created")

            for i in instance.O:
                self.model += (
                    xsum(z.get((i, m), 0) for m in instance.M_i[i]) == 1,
                    f"machine_assign_{i}",
                )

            logger.log("constraints R3 created")

            for m in instance.M:
                ops = instance.O_m[m]
                for i in ops:
                    for j in ops:
                        if i >= j:
                            continue
                        pij = instance.p.get((i, m), 0)
                        pji = instance.p.get((j, m), 0)
                        # i antes de j
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
                        # j antes de i
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

            logger.log("constraints R4 & R5 created")

            self.x = x
            self.z = z
            self.y = y
            self.c_max = c_max

        logger.log("mathematical model completely built")
        logger.breakline()

    def run(
        self,
        *,
        show_sol: bool = True,
        verbose: int = 0,
        time_limit: int = 1800,
    ) -> None:
        def gap(*, ub: float, lb: float) -> float:
            return round((100 * (ub - lb) / ub), 4)

        logger = self._logger

        logger.log("starting CBC optimization")

        if verbose not in [0, 1]:
            self.model.verbose = 0
        else:
            self.model.verbose = verbose

        timer = Crono()
        status = self.model.optimize(max_seconds=time_limit)
        elapsed_time = timer.stop()

        logger.log(f"optimization finished | elapsed time: {elapsed_time} s")

        with logger:
            if self.model.num_solutions:
                makespan = self.c_max.x

                if status == OptimizationStatus.FEASIBLE:
                    logger.log(
                        f"feasible integer solution found | gap = {gap(ub=makespan, lb=self._instance.optimal_solution)}%"
                    )
                if status == OptimizationStatus.OPTIMAL:
                    logger.log(
                        f"optimal solution found | gap = {gap(ub=makespan, lb=self._instance.optimal_solution)}%"
                    )

                with logger:
                    logger.log(f"makespan: {makespan}")

                    if show_sol:
                        for i in self._instance.O:
                            start = self.x[i].x
                            machine = [
                                m
                                for m in self._instance.M_i[i]
                                if self.z.get((i, m), 0).x >= 0.99
                            ][0]
                            logger.log(
                                f"operation: {i} | start time: {start} | machine assigned: {machine} | end time: {start + self._instance.p[(i, machine)]}"
                            )
            else:
                logger.log("no feasible integer solution found in time limit :c")
        logger.breakline()
