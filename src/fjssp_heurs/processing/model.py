from ..instance.instance import Instance
from ..utils.crono import Crono

from mip import Model, xsum, minimize, CBC, OptimizationStatus, BINARY, CONTINUOUS
from pathlib import Path


class MathModel:
    def __init__(self, *, instance: Instance, output_folder: Path) -> None:
        self._instance = instance
        self._output_folder = output_folder
        self._create_model()

    def _create_model(self) -> None:
        print("   > building mathematical model")

        instance = self._instance
        # instance.print(type="sets")

        steps = 1

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

        print(f"      > [{steps}] decision vars has been created")
        steps += 1

        self.model.objective = minimize(c_max)

        print(f"      > [{steps}] objective function has been defined")
        steps += 1

        for i in instance.O:
            self.model += (
                c_max
                >= x.get(i, 0)
                + xsum(instance.p[(i, m)] * z.get((i, m), 0) for m in instance.M_i[i]),
                f"makespan_def_{i}",
            )

        print(f"      > [{steps}] constraints R1 has been created")
        steps += 1

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

        print(f"      > [{steps}] constraints R2 has been created")
        steps += 1

        for i in instance.O:
            self.model += (
                xsum(z.get((i, m), 0) for m in instance.M_i[i]) == 1,
                f"machine_assign_{i}",
            )

        print(f"      > [{steps}] constraints R3 has been created")
        steps += 1

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

        print(f"      > [{steps}] constraints R4 & R5 has been created")
        steps += 1

        self.x = x
        self.z = z
        self.y = y
        self.c_max = c_max

        print("   > mathematical model has been completely built")

    def run(
        self,
        *,
        show_sol: bool = True,
        verbose: int = 0,
        time_limit: int = 1800,
    ) -> None:

        def gap(
            *, ub: float, lb: float
        ) -> float:
            return round((100 * (ub - lb) / ub), 4)

        if verbose not in [0, 1]:
            self.model.verbose = 0
        else:
            self.model.verbose = verbose

        print("   > starting CBC optimization\n\n")

        timer = Crono()
        status = self.model.optimize(max_seconds=time_limit)
        elapsed_time = timer.stop()

        print(f"\n   > optimization finished | elapsed time: {elapsed_time} s")

        if self.model.num_solutions:
            makespan = self.c_max.x
            
            if status == OptimizationStatus.FEASIBLE:
                print(f"   > feasible integer solution found | gap = {gap(ub=makespan, lb=self._instance.optimal_solution)}%")
            if status == OptimizationStatus.OPTIMAL:
                print(f"   > optimal solution found | gap = {gap(ub=makespan, lb=self._instance.optimal_solution)}%")

            print(f"      > makespan: {makespan}")

            if show_sol:
                for i in self._instance.O:
                    start = self.x[i].x
                    machine = [
                        m for m in self._instance.M_i[i] if self.z.get((i, m), 0).x >= 0.99
                    ][0]
                    print(f"      > operação {i} | início: {start}, na máquina {machine}")
        else:
            print("   > no feasible integer solution found in time limit :c")
        print()
