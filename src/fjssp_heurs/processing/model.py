from ..instance.instance import Instance
from mip import Model, xsum, minimize, CBC, OptimizationStatus, BINARY, CONTINUOUS


class MathModel:
    def __init__(self, instance: Instance) -> None:
        self._instance = instance
        self._create_model()

    def _create_model(self) -> None:
        instance = self._instance
        # instance.print(type="sets")

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

        self.model.objective = minimize(c_max)

        for i in instance.O:
            self.model += (
                c_max
                >= x.get(i, 0)
                + xsum(instance.p[(i, m)] * z.get((i, m), 0) for m in instance.M_i[i]),
                f"makespan_def_{i}",
            )

        for j in range(instance.num_jobs):
            seq = instance.P_j[j]
            for a in range(len(seq) - 1):
                i, i_ = seq[a], seq[a + 1]
                self.model += (
                    x.get(i_, 0)
                    >= x.get(i, 0)
                    + xsum(
                        instance.p[(i, m)] * z.get((i, m), 0) for m in instance.M_i[i]
                    ),
                    f"preced_{i}_{i_}",
                )

        for i in instance.O:
            self.model += (
                xsum(z.get((i, m), 0) for m in instance.M_i[i]) == 1,
                f"machine_assign_{i}",
            )

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

        self.x = x
        self.z = z
        self.y = y
        self.c_max = c_max

    def run(self) -> None:
        pass
