from .solution import Solution
from ...utils.crono import Crono
from .localsearch import LocalSearch

from math import exp
import numpy as np


class Metaheuristics:
    def __init__(self):
        pass

    def sa(
        self,
        *,
        sol: Solution,
        alpha: float = 0.97,
        k: float = 2.0,
        beta: float = 1.1,
        low_temperature: float = 2.0,
        final_temperature: float = 0.01,
        max_time: int,
    ):
        ls = LocalSearch()

        def sa_initial_temperature(
            *,
            sol: Solution,
            beta: float,
            gamma: float,
            low_temperature: float,
            SAmax: int,
        ):
            # n = sol.inst.n
            start_temperature = low_temperature
            accept = 0
            min_accept = int(gamma * SAmax)
            while accept < min_accept:
                h = 0
                while h < SAmax:
                    h += 1
                    # movement
                    # j = np.random.randint(n)
                    # delta = ls.swap_bit(sol, j)
                    delta = 0
                    if delta > 0:
                        accept += 1
                    else:
                        rnd = np.random.uniform(0, 1)
                        if rnd < exp(delta / start_temperature):
                            accept += 1
                    # movement
                    # delta = ls.swap_bit(sol, j)
                    delta = 0

                if accept < min_accept:
                    accept = 0
                    start_temperature *= beta
            return start_temperature

        inst = sol.inst
        n = inst.n

        SAmax = k * n
        initial_temperature = sa_initial_temperature(
            sol=sol,
            beta=beta,
            gamma=alpha,
            low_temperature=low_temperature,
            SAmax=SAmax,
        )
        temperature = initial_temperature
        final_temperature = 0.01
        n_temp_changes = 0

        best_sol = Solution(inst)
        best_sol.copy(sol)

        timer = Crono()

        while temperature > final_temperature and timer.get_time() < max_time:
            h = 0
            while h < SAmax:
                h += 1
                j = np.random.randint(n)
                delta = ls.swap_bit(sol, j)
                if delta > 0:
                    if sol.get_obj_val() > best_sol.get_obj_val():
                        best_sol.copy(sol)
                else:
                    rnd = np.random.uniform(0, 1)
                    if rnd < exp(delta / temperature):
                        pass
                    else:
                        ls.swap_bit(sol, j)

            temperature *= alpha
            n_temp_changes += 1
