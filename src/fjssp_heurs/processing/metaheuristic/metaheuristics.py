from .solution import Solution
from ...utils.crono import Crono
from .localsearch import LocalSearch
from ...utils.logger import LOGGER

from math import exp
import numpy as np
from numpy import random


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
        logger: LOGGER,
        verbose: bool = False,
    ):
        self._logger = logger
        if not verbose:
            self._logger.on = -1
        ls = LocalSearch(logger=logger)

        logger.log("sa starting sol")
        sol.print(
            show_gantt=False, gantt_name="sa starting sol", by_op=False, plot=False
        )

        def sa_initial_temperature(
            *,
            sol: Solution,
            beta: float,
            gamma: float,
            low_temperature: float,
            SAmax: int,
        ):
            start_temperature = low_temperature
            accept = 0
            min_accept = int(gamma * SAmax)
            while accept < min_accept:
                h = 0

                while h < SAmax:
                    h += 1
                    # placeholder — sempre aceita nesse esboço
                    delta = 1

                    if delta > 0:
                        accept += 1
                    else:
                        rnd = np.random.uniform(0, 1)
                        if rnd < exp(delta / start_temperature):
                            accept += 1

                if accept < min_accept:
                    accept = 0
                    start_temperature *= beta

            return start_temperature

        inst = sol._instance
        num_ops = len(inst.O)
        SAmax = int(k * num_ops)
        logger.log(f"max iterations: {SAmax}")

        initial_temperature = sa_initial_temperature(
            sol=sol,
            beta=beta,
            gamma=alpha,
            low_temperature=low_temperature,
            SAmax=SAmax,
        )
        temperature = initial_temperature

        best_sol = Solution(
            instance=inst, logger=sol._logger, output_path=sol._output_path
        )
        best_sol.copy_solution(sol=sol)

        logger.log("best sol:")
        best_sol.print(
            show_gantt=False, gantt_name="sa best sol", by_op=False, plot=False
        )

        timer = Crono()

        while temperature > final_temperature and timer.elapsed_time() < max_time:
            logger.log(
                f"current temperature: {temperature} | current time: {timer.elapsed_time()}"
            )
            h = 0
            while h < SAmax and timer.elapsed_time() < max_time:
                # wait = input()
                h += 1
                logger.log(f"starting h: {h}")

                current_obj = sol._recalculate_times()
                logger.log(f"current_obj: {current_obj}")

                backup = Solution(
                    instance=inst, logger=sol._logger, output_path=sol._output_path
                )
                backup.copy_solution(sol=sol)

                logger.log("generating neighbor solution")

                """
                if temperature > initial_temperature * 0.5:
                    k = random.randint(int(len(inst.O) / 8), int(len(inst.O) / 3))
                else:
                    k = random.randint(int(len(inst.O) / 30), int(len(inst.O) / 10))
                
                ls.random_k_machine_swap(sol=sol, k=k)
                """
                ls.random_machine_swap(sol=sol)

                new_obj = sol._recalculate_times()
                delta = current_obj - new_obj
                logger.log(
                    f"h {h} | current_sol_obj = {current_obj} | new_neighboor_obj = {new_obj} | delta = {delta}"
                )

                if delta > 0:
                    if new_obj < best_sol._makespan:
                        best_sol.copy_solution(sol=sol)
                else:
                    rnd = np.random.uniform(0, 1)
                    if rnd < exp(delta / temperature):
                        pass
                    else:
                        sol.copy_solution(sol=backup)

                logger.breakline()
            temperature *= alpha
            logger.breakline(2)

        print(f"TEMPO: {timer.elapsed_time()}")

        sol.copy_solution(sol=best_sol)
        self._logger.on = 1
