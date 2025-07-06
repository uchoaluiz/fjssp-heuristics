from collections import deque
from copy import copy
from random import sample, shuffle

from ...processing.metaheuristic.solution import Solution
from ...utils.logger import LOGGER
from .sbp.sbp import ShiftingBottleneck


class LocalSearch:
    """
    Implements a local search heuristic with Tabu Search for the Flexible Job Shop Scheduling Problem (FJSSP).

    This class manages the generation of neighboring solutions and applies Tabu Search principles
    to avoid revisiting previously explored solutions, enhancing the search process.
    """

    def __init__(self, logger: LOGGER) -> None:
        """
        Initializes the LocalSearch with a logger and Tabu Search parameters.

        Args:
            logger: An instance of the LOGGER for logging messages.
        """
        self._logger: LOGGER = copy(logger)
        self._logger.level += 1
        self.tabu: dict[int, dict[str, deque]] = {}
        self._sbp: ShiftingBottleneck = None

    def _define_jssp_solver(self, sbp: ShiftingBottleneck) -> None:
        """
        Defines the JSSP solver (ShiftingBottleneck Processor) to be used for rescheduling.

        Args:
            sbp: An optional instance of ShiftingBottleneck. If None, a new one is created.
        """
        self._sbp = sbp if sbp else ShiftingBottleneck(log_out="file")

    def _update_tabu_list(self, sol_hash: int, moves: list[tuple[int, int]]) -> None:
        """
        Updates the Tabu list for a given solution hash by adding new moves.

        Args:
            sol_hash: The hash of the current solution's scheduling.
            moves: A list of (operation, new_machine) tuples to add to the tabu list.
        """
        if sol_hash in self.tabu:
            self.tabu[sol_hash]["tabu_moves"].extend(moves)
            self._logger.log(f"[tabu] updated tabu list with moves: {moves}")

    def _is_tabu(self, sol_hash: int, move: tuple[int, int]) -> bool:
        """
        Checks if a given move is currently in the Tabu list for a specific solution.

        Args:
            sol_hash: The hash of the current solution's scheduling.
            move: A tuple (operation, new_machine) representing the move to check.

        Returns:
            True if the move is tabu, False otherwise.
        """
        return sol_hash in self.tabu and move in self.tabu[sol_hash]["tabu_moves"]

    def generate_adaptive_neighbor_with_tabu(
        self,
        sol: Solution,
        intensity_level: int,
        T_rel: float = 1.0,
    ) -> tuple[float, Solution]:
        """
        Generates an adaptive neighbor solution using Tabu Search.

        The intensity level determines how many critical operations are considered for modification.
        The method attempts to find a non-tabu move to create a new neighbor.

        Args:
            sol: The current Solution object from which to generate a neighbor.
            intensity_level: An integer indicating the intensity of the neighborhood search (0-3).
            T_rel: Relative temperature, used to adapt the number of operations to change.

        Returns:
            A tuple containing the makespan of the new neighbor and the neighbor Solution object,
            or (None, None) if no valid neighbor could be generated.
        """
        logger = self._logger

        logger.breakline()
        sol_scheduling = tuple(tuple(sublist) for sublist in sol._machine_sequence)
        sol_hash = hash(sol_scheduling)

        logger.log(
            f"generating a neighbor from: sol: {sol._makespan} | sol_hash: {sol_hash} | intensity: {intensity_level} | T_rel: {T_rel}"
        )
        logger.breakline()

        with logger:
            logger.log("current tabu:")
            with logger:
                if not self.tabu:
                    logger.log("empty tabu")
                for solution_hash, values_dict in self.tabu.items():
                    logger.log(
                        f"sol hash: {solution_hash} | queue: {list(values_dict['queue'])}"
                    )
                    with logger:
                        logger.log(f"moves: {list(values_dict['tabu_moves'])}")
            logger.breakline()

            if sol_hash not in self.tabu:
                logger.log("brand new solution hash, adding it on tabu...")
                critical_path, _ = sol._find_a_critical_path()
                critical_path_with_flex = [
                    op for op in critical_path if len(sol._instance.M_i[op]) > 1
                ]

                if not critical_path_with_flex:
                    with logger:
                        logger.log("new solution hash with no flexible critical ops..")
                    return None, None

                shuffle(critical_path_with_flex)
                self.tabu[sol_hash] = {
                    "queue": deque(critical_path_with_flex),
                    "tabu_moves": deque(
                        maxlen=sum(
                            [
                                len(sol._instance.M_i[op]) - 1
                                for op in critical_path_with_flex
                            ]
                        )
                    ),
                }
            elif not self.tabu[sol_hash]["queue"]:
                logger.log("known solution but with no queue left, rewriting it...")
                critical_path, _ = sol._find_a_critical_path()
                critical_path_with_flex = [
                    op for op in critical_path if len(sol._instance.M_i[op]) > 1
                ]
                if not critical_path_with_flex:
                    with logger:
                        logger.log(
                            "known solution hash with no flexible critical ops.."
                        )
                    return None, None
                shuffle(critical_path_with_flex)
                self.tabu[sol_hash]["queue"] = deque(critical_path_with_flex)
                logger.log(
                    f"[tabu] reshuffling a critical path for sol {sol_hash}: {critical_path}"
                )

            logger.breakline()

            neighbor_sol = Solution(instance=sol._instance, logger=self._logger)

            max_attempts = 100
            attempts = 0

            logger.log(f"num max attempts: {max_attempts}\n")

            while attempts < max_attempts:
                if not self.tabu[sol_hash]["queue"]:
                    logger.log(
                        f"[*] no flexible critical ops in critical queue for sol: {sol._makespan}"
                    )
                    break

                logger.log(f"it: {attempts}")
                attempts += 1
                neighbor_sol.copy_solution(sol=sol)
                moves_made: list[tuple[int, int]] = []

                if intensity_level == 0:
                    logger.log("generating neighbor changing 1 random critical op")
                    with logger:
                        op, new_machine = self._get_non_tabu_move(
                            sol, neighbor_sol, sol_hash
                        )
                        if op is not None and new_machine is not None:
                            moves_made.append((op, new_machine))

                elif intensity_level in (1, 2):
                    critical_ops = list(self.tabu[sol_hash]["queue"])
                    k = (
                        max(2, int(0.05 * T_rel * len(critical_ops)))
                        if intensity_level == 1
                        else max(3, int(0.10 * T_rel * len(critical_ops)))
                    )
                    selected_ops = [
                        self.tabu[sol_hash]["queue"].pop()
                        for _ in range(min(k, len(self.tabu[sol_hash]["queue"])))
                    ]

                    for op_to_change in selected_ops:
                        op, new_machine = self._get_non_tabu_move(
                            sol, neighbor_sol, sol_hash, op_to_change
                        )
                        if op is not None and new_machine is not None:
                            moves_made.append((op, new_machine))

                elif intensity_level == 3:
                    pct = min(0.3, 0.15 + 0.3 * T_rel)
                    critical_ops = list(self.tabu[sol_hash]["queue"])
                    num_ops = max(1, int(pct * len(critical_ops)))
                    selected_ops = sample(critical_ops, num_ops)

                    for op_to_change in selected_ops:
                        if op_to_change in self.tabu[sol_hash]["queue"]:
                            self.tabu[sol_hash]["queue"].remove(op_to_change)
                        op, new_machine = self._get_non_tabu_move(
                            sol, neighbor_sol, sol_hash, op_to_change
                        )
                        if op is not None and new_machine is not None:
                            moves_made.append((op, new_machine))

                if moves_made:
                    neighbor_sol._machine_sequence = (
                        neighbor_sol._get_machines_assignment()
                    )
                    neighbor_sol.create_graph(
                        tech_disjunc=False, graph_type="partial fjssp"
                    )

                    if self._sbp:
                        self._sbp.process(
                            solution=neighbor_sol, old_logger=self._logger
                        )
                        neighbor_makespan = neighbor_sol._recalculate_times(
                            logger=self._logger
                        )
                        self._update_tabu_list(sol_hash, moves_made)
                        return neighbor_makespan, neighbor_sol
                    else:
                        logger.log("[!] SBP not defined. Cannot reschedule neighbor.")
                        return None, None

        return None, None

    def _get_non_tabu_move(
        self,
        sol: Solution,
        neighbor_sol: Solution,
        sol_hash: int,
        op: int = None,
    ) -> tuple[int, int]:
        """
        Selects a non-tabu move (operation, new_machine) for a given solution.

        If `op` is not provided, it selects a critical operation from the tabu queue.
        It then iterates through alternative machines for the selected operation,
        returning the first non-tabu move.

        Args:
            sol: The original Solution object.
            neighbor_sol: The neighbor Solution object to modify.
            sol_hash: The hash of the original solution's scheduling.
            op: An optional specific operation to find a move for.

        Returns:
            A tuple (operation, new_machine) if a non-tabu move is found,
            otherwise (None, None).
        """
        logger = self._logger
        instance = sol._instance

        logger.log("getting a non tabu move")

        if op is None:
            if not self.tabu[sol_hash]["queue"]:
                logger.log("[getmove] critical path queue is empty")
                return None, None
            logger.log(
                f"[getmove] exists critical path queue remaining: {list(self.tabu[sol_hash]['queue'])}"
            )
            op = self.tabu[sol_hash]["queue"].pop()
            logger.log(f"[getmove] selected new critical op: {op}")

        logger.breakline()

        eligible_machines = instance.M_i[op]
        current_machine = sol._assign_vect[op]
        alternatives = [m for m in eligible_machines if m != current_machine]

        if not alternatives:
            logger.log(f"[tabu] op {op} has no alternative machines")
            if op in self.tabu[sol_hash]["queue"]:
                self.tabu[sol_hash]["queue"].remove(op)
            return None, None
        else:
            logger.log(f"[tabu] op {op} HAS alternative machines")

        shuffle(alternatives)

        logger.log(f"alternative machines to swap for op: {op}: {alternatives}")

        for new_machine in alternatives:
            move = (op, int(new_machine))
            if not self._is_tabu(sol_hash, move):
                logger.log(f"[tabu] move accepted: op {op} -> m{new_machine}")
                neighbor_sol._assign_vect[op] = new_machine
                return op, int(new_machine)
            else:
                logger.log(f"[tabu] move {move} is tabu")

        logger.log(f"[tabu] all moves for op {op} are tabu")
        return None, None
