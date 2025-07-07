from math import exp
from copy import copy

import numpy as np

from ...utils.logger import LOGGER
from ...utils.crono import Crono
from ...utils.gap import evaluate_gap
from .solution import Solution
from .localsearch import LocalSearch
from .solbuilder import SolutionBuilder
from .sbp.sbp import ShiftingBottleneck


class SimulatedAnnealing:
    """
    Implements the Simulated Annealing (SA) metaheuristic for solving the Flexible Job Shop Scheduling Problem (FJSSP).

    This class orchestrates the SA process, including temperature management, neighbor generation
    using local search, acceptance criteria, and logging.
    """

    def __init__(
        self,
        local_search: LocalSearch,
        sbp_solver: ShiftingBottleneck,
        alpha: float = 0.97,
        beta: float = 1.1,
        k: int = 2,
        initial_temperature: float = 2.0,
        final_temperature: float = 0.01,
        max_time: int = 300,
        log_writing: bool = False,
        seed: int = 42,
    ) -> None:
        """
        Initializes the Simulated Annealing optimizer.

        Args:
            local_search: An instance of the LocalSearch operator.
            alpha: Cooling rate (0 < alpha < 1).
            beta: Temperature increase factor for initial temperature calculation.
            k: Factor to determine the number of iterations per temperature level.
            initial_temperature: Starting temperature for the algorithm.
            final_temperature: Stopping temperature criterion.
            max_time: Maximum runtime in seconds.
            log_writing: Whether to print detailed logs to a file.
            seed: Randomness seed.
        """
        self._sbp = sbp_solver
        self.local_search: LocalSearch = local_search
        self.local_search._define_jssp_solver(sbp=self._sbp)

        self.logger: LOGGER = LOGGER(
            log_path="salog.log", out=("file" if log_writing else "off")
        )
        # preserve the original logger from local_search for main console output
        self.old_logger: LOGGER = copy(self.local_search._logger)
        self.old_logger.level -= 1  # Adjust level for cleaner output
        self.local_search._logger = (
            self.logger
        )  # redirect local search logs to SA's file logger

        self.alpha: float = alpha
        self.beta: float = beta
        self.k: int = k
        self.initial_temperature_param: float = (
            initial_temperature  # renamed to avoid conflict
        )
        self.final_temperature: float = final_temperature

        self.intensity_level: int = 0
        self.no_improvement_counter: int = 0
        self.stagnation_threshold: float = 0.8
        self.max_intensity_level: int = 3

        self.max_time: int = max_time
        self.log_writing: bool = log_writing

        self.timer: Crono = Crono()
        self.current_temperature: float = None
        self.current_iteration: int = 0
        self.best_solution: Solution = None
        self.start_temperature: float = 0.0

        np.random.seed(seed)

    def _log_iteration(
        self,
        iteration: int,
        current_obj: float,
        new_obj: float,
        acceptance_prob: tuple[float, str],
        rand: tuple[float, str],
        accepted: str,
        time: float,
        no_improvement: int,
        intensity_level: int,
        current_temperature: float = None,
    ) -> None:
        """
        Logs the details of each iteration of the Simulated Annealing algorithm.

        Args:
            iteration: The current iteration number.
            current_obj: The makespan of the current solution.
            new_obj: The makespan of the new (neighbor) solution.
            acceptance_prob: The probability of accepting the new solution (or '-').
            rand: A random number used for acceptance (or '-').
            accepted: A string indicating if the new solution was accepted ('Y', 'N', 'BEST', '-').
            time: Elapsed time in seconds.
            no_improvement: Counter for iterations without improvement.
            intensity_level: Current intensity level of the local search.
            current_temperature: The current temperature. If None, uses self.current_temperature.
        """

        def rounded(number: tuple[float, str], n: int) -> tuple[float, str]:
            """Helper to round float numbers or return as is."""
            return round(number, n) if isinstance(number, float) else number

        temp_to_log = (
            rounded(self.current_temperature, 4)
            if current_temperature is None
            else rounded(current_temperature, 4)
        )

        it_log = (
            f"T: {temp_to_log} | "
            f"it {iteration} | "
            f"neigh. level: {intensity_level} | "
            f"current: {current_obj} | "
            f"new: {new_obj} | "
            f"prob: {rounded(acceptance_prob, 4)} | "
            f"rand: {rounded(rand, 4)} | "
            f"accepted?: {accepted} | "
            f"time: {time} | "
            f"best: {self.best_solution._makespan if self.best_solution else 'N/A'} | "
            f"h_stagnation: {no_improvement}"
        )

        self.old_logger.log(it_log)
        self.logger.log(it_log)

    def _calculate_initial_temperature(
        self, solution: Solution, max_iterations: int
    ) -> float:
        logger = self.logger
        T = self.initial_temperature_param
        max_reasonable_T = solution._makespan * 5
        min_reasonable_T = solution._makespan * 0.1

        acceptance_history = []
        delta_history = []

        logger.log(
            f"[tempcalc] starting T0 calculation with limits [{min_reasonable_T:.2f}, {max_reasonable_T:.2f}]"
        )

        self.timer = Crono()
        temp_calc_time_limit = 0.15 * self.max_time

        while self.timer.elapsed_time() < temp_calc_time_limit:
            accept_count = 0
            for iteration in range(max_iterations):
                _, sol_prime = self.local_search.generate_adaptive_neighbor_with_tabu(
                    sol=solution, intensity_level=0
                )

                if sol_prime is None:
                    continue

                delta = sol_prime._makespan - solution._makespan
                delta_history.append(delta)

                if delta <= 0:
                    accept_count += 1
                else:
                    rand = np.random.uniform(0, 1)
                    if rand < exp(-delta / T):
                        accept_count += 1

                acceptance_rate = accept_count / (iteration + 1)
                acceptance_history.append(acceptance_rate)

                if (
                    len(acceptance_history) > 20
                    and np.mean(acceptance_history[-20:]) > 0.3
                ):
                    break

            current_acceptance = accept_count / max_iterations

            if current_acceptance < 0.2:
                T *= 1.1
            elif current_acceptance > 0.5:
                T *= 0.9
            else:
                break
            T = min(max(T, min_reasonable_T), max_reasonable_T)

            logger.log(
                f"[tempcalc] T={T:.2f} | "
                f"Acceptance={current_acceptance:.2f} | "
                f"Δ median={np.median(delta_history):.2f} | "
                f"Time={self.timer.elapsed_time():.2f}s"
            )

        logger.log(f"[tempcalc] Final initial T: {T:.2f}")
        return T

    def optimize(self, *, solution: Solution) -> Solution:
        """
        Executes the Simulated Annealing optimization process.

        Args:
            solution: The initial Solution object to start the optimization from.

        Returns:
            The best Solution found during the optimization process.
        """
        self.old_logger.level += 1
        self.old_logger.breakline()
        self.old_logger.log(
            "SA algorithm has started, reach 'salog.log' for further logs"
        )
        self.old_logger.breakline()
        self.old_logger.level += 1

        logger = self.logger
        builder = SolutionBuilder(logger=logger)

        instance = solution._instance
        num_operations = len(instance.O)
        max_iterations_per_temp = int(self.k * num_operations)

        msg = "[1] calculating initial temperature"
        logger.log(msg)
        self.old_logger.log(msg)
        self.start_temperature = self._calculate_initial_temperature(
            solution=solution, max_iterations=max_iterations_per_temp
        )
        logger.log("initial temperature calculated\n")

        self.current_temperature = self.start_temperature

        self.no_improvement_counter = 0
        stagnation_limit = int(self.stagnation_threshold * max_iterations_per_temp)

        self.no_neighbors_counter = 0
        max_no_neighbors = max_iterations_per_temp

        msg = "[2] starting SA optimization\n"
        logger.log(msg)
        self.old_logger.log(msg)

        self.old_logger.level += 1

        with logger:
            logger.log(f"stagnation limit: {stagnation_limit} its")

            self.timer = Crono()

            self.best_solution = Solution(
                instance=solution._instance,
                logger=solution._logger,
            )
            self.best_solution.copy_solution(sol=solution)

            current_solution = Solution(
                instance=instance,
                logger=solution._logger,
            )
            current_solution.copy_solution(sol=solution)

            logger.log(
                f"starting best solution: {self.best_solution._makespan} | "
                f"max runtime: {self.max_time} s | "
                f"max its per temp: {max_iterations_per_temp}\n"
            )

            while (
                self.current_temperature > self.final_temperature
                and self.timer.elapsed_time() < self.max_time
            ):
                logger.breakline()
                logger.log(
                    f"temperature: {self.current_temperature:.4f} | "
                    f"elapsed time: {self.timer.elapsed_time():.2f}s"
                )

                iteration = 0

                log_msg = (
                    f"T: >> {round(self.current_temperature, 4)} << | "
                    f"it {iteration} | "
                    f"neigh. level: {self.intensity_level} | "
                    f"current: {current_solution._makespan} | "
                    f"time: {round(self.timer.elapsed_time(), 4)} | "
                    f"best: {self.best_solution._makespan}"
                )
                logger.log(log_msg)
                self.old_logger.log(log_msg)

                with logger:
                    while (
                        iteration < max_iterations_per_temp
                        and self.timer.elapsed_time() < self.max_time
                    ):
                        iteration += 1
                        self.current_iteration += 1
                        accepted: str = "-"
                        acceptance_prob: tuple[float, str] = "-"
                        rand: tuple[float, str] = "-"

                        logger.breakline()
                        logger.log(
                            "[1] checking if current solution can generate neighbor solution"
                        )

                        is_neighbor_possible = True
                        current_critical_path, current_more_criticals = (
                            current_solution._find_a_critical_path()
                        )
                        if (
                            not [
                                op
                                for op in current_critical_path
                                if len(current_solution._instance.M_i[op]) > 1
                            ]
                        ) and current_more_criticals == 0:
                            is_neighbor_possible = False

                        if is_neighbor_possible:
                            self.no_neighbors_counter = 0
                            with logger:
                                logger.log(
                                    "[*] its possible to generate neighbor solution from current's"
                                )

                            logger.breakline()
                            logger.log("[2] generating neighbor solution")

                            makespan_prime, sol_prime = (
                                self.local_search.generate_adaptive_neighbor_with_tabu(
                                    sol=current_solution,
                                    intensity_level=self.intensity_level,
                                    T_rel=self.current_temperature
                                    / self.initial_temperature_param,
                                )
                            )

                            if sol_prime is None:
                                logger.log(
                                    "[!] localsearch failed to generate a non-tabu neighbor after attempts."
                                )
                                # 'grasping' if local search fails
                                builder.define_hiperparams(alpha_grasp=0.5)
                                builder.build_solution(
                                    solution=current_solution,
                                    machines_strategy="grasp",
                                    scheduler_approach="machine_by_machine",
                                )
                                current_solution.create_graph(
                                    tech_disjunc=True, graph_type="complete fjssp"
                                )
                                self.intensity_level = 0
                                self.no_improvement_counter = 0
                                continue

                            logger.breakline()
                            logger.log(
                                "[3] checking if neighbor solution will be accepted"
                            )

                            with logger:
                                current_makespan = current_solution._makespan
                                delta = current_makespan - makespan_prime
                                if delta >= 0:  # improving or equal solution
                                    current_solution.copy_solution(sol=sol_prime)

                                    logger.log(
                                        f"[3.1] neighbor makespan was lower or equal, current now is: {current_solution._makespan}"
                                    )

                                    with logger:
                                        if (
                                            makespan_prime
                                            < self.best_solution._makespan
                                        ):
                                            self.best_solution.copy_solution(
                                                sol=sol_prime
                                            )
                                            self.no_improvement_counter = 0
                                            self.intensity_level = 0
                                            logger.log(
                                                f"[3.1.1] neighbor makespan was lower than BEST, best now is: {self.best_solution._makespan}"
                                            )
                                            accepted = "BEST"
                                        else:
                                            self.no_improvement_counter += 1
                                            accepted = "-"  # no improvement over best
                                else:  # worsening solution
                                    accepted = "N"
                                    self.no_improvement_counter += 1
                                    acceptance_prob = exp(
                                        delta / self.current_temperature
                                    )
                                    rand = np.random.uniform(0, 1)
                                    if rand < acceptance_prob:
                                        current_solution.copy_solution(sol=sol_prime)
                                        accepted = "Y"
                                        logger.log(
                                            f"[3.1] neighbor sol was accepted by prob | current: {current_solution._makespan}"
                                        )
                                    else:
                                        logger.log(
                                            f"[3.1] neighbor sol was NOT accepted by prob | current: {current_solution._makespan}"
                                        )

                                logger.breakline()

                            self._log_iteration(
                                iteration,
                                current_makespan,
                                makespan_prime,
                                acceptance_prob,
                                rand,
                                accepted,
                                round(self.timer.elapsed_time(), 2),
                                self.no_improvement_counter,
                                self.intensity_level,
                            )

                            logger.breakline()

                            if self.no_improvement_counter > stagnation_limit:
                                logger.breakline()

                                if self.intensity_level < self.max_intensity_level:
                                    self.intensity_level += 1
                                    self.no_improvement_counter = 0
                                    logger.log(
                                        f"[*] stagnation of {stagnation_limit} its was reached, new intensity {self.intensity_level}"
                                    )
                                elif self.intensity_level == self.max_intensity_level:
                                    # diversify more aggressively based on stagnation
                                    if self.no_improvement_counter < int(
                                        0.25 * stagnation_limit
                                    ):
                                        diversification_fact = 0.2
                                    elif self.no_improvement_counter <= int(
                                        0.5 * stagnation_limit
                                    ):
                                        diversification_fact = 0.35
                                    else:
                                        diversification_fact = 0.5

                                    builder.define_hiperparams(
                                        alpha_grasp=0.5 + diversification_fact
                                    )
                                    builder.build_solution(
                                        solution=current_solution,
                                        machines_strategy="grasp",
                                        scheduler_approach="machine_by_machine",
                                    )
                                    current_solution.create_graph(
                                        tech_disjunc=True, graph_type="complete fjssp"
                                    )
                                    self.intensity_level = 0
                                    self.no_improvement_counter = 0
                                    logger.log(
                                        f"[**] strong stagnation detected, GRASPING a new brand solution: {current_solution._makespan}"
                                    )
                        else:  # cannot generate neighbor from current solution
                            self.no_neighbors_counter += 1
                            with logger:
                                logger.log(
                                    "[*] its NOT possible to generate neighbor solution from current's, creating different solution"
                                )

                                # 'grasping' based on how many times no neighbor could be generated
                                if self.no_neighbors_counter < int(
                                    0.25 * max_no_neighbors
                                ):
                                    diversification_fact = 0.2
                                elif self.no_neighbors_counter <= int(
                                    0.5 * max_no_neighbors
                                ):
                                    diversification_fact = 0.6
                                else:
                                    diversification_fact = 0.9

                                current_makespan = current_solution._makespan

                                builder.define_hiperparams(
                                    alpha_grasp=0.1 + diversification_fact
                                )
                                builder.build_solution(
                                    solution=current_solution,
                                    machines_strategy="grasp",
                                    scheduler_approach="machine_by_machine",
                                )
                                current_solution.create_graph(
                                    tech_disjunc=True, graph_type="complete fjssp"
                                )
                                self.intensity_level = 0
                                self.no_improvement_counter = 0
                                self.current_temperature = (
                                    self.start_temperature
                                )  # reset temperature upon strong diversification

                            if (
                                current_solution._makespan
                                < self.best_solution._makespan
                            ):
                                self.best_solution.copy_solution(sol=current_solution)

                            self._log_iteration(
                                iteration,
                                current_makespan,
                                current_solution._makespan,
                                "-",
                                "-",
                                "new sol",
                                round(self.timer.elapsed_time(), 2),
                                self.no_improvement_counter,
                                self.intensity_level,
                            )

                if self.no_neighbors_counter > max_no_neighbors:
                    logger.log(
                        "[!] Max no-neighbor attempts reached. Breaking SA loop."
                    )
                    break

                self.current_temperature *= self.alpha  # cool down temperature

            logger.breakline()
            total_runtime = self.timer.elapsed_time()
            logger.log("------ SA optimization complete ------")
            with logger:
                logger.log(f"total iterations: {self.current_iteration}")
                logger.log(f"total runtime: {total_runtime:.2f}s")
            logger.breakline()
            logger.log(f"best solution makespan: {self.best_solution._makespan}")
            logger.breakline()

            return (
                self.best_solution,
                total_runtime,
                evaluate_gap(
                    ub=self.best_solution._makespan, lb=instance.optimal_solution
                ),
            )
