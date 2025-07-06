import copy
from .schrage import SchrageScheduler
from ....instance.instance import Instance
from ....utils.logger import LOGGER


class CarlierSolver:
    def __init__(
        self,
        operations: list[int],
        release_dates: dict[int, float],
        processing_times: dict[int, float],
        delivery_times: dict[int, float],
        instance: Instance,
        logger: LOGGER,
        max_depth: int = 30,
    ):
        self._operations = operations
        self._release_dates = release_dates
        self._processing_times = processing_times
        self._delivery_times = delivery_times
        self._instance = instance
        self._logger = logger
        self.max_depth = max_depth

        self.best_lmax = float("inf")
        self.best_schedule = []

    def _log_initial_state(self):
        logger = self._logger

        logger.log("---------- carlier algorithm initial state ----------")

        with logger:
            logger.log(f"ops: {self._operations}")
            logger.log(f"initial release dates: {self._release_dates}")
            logger.log(f"initial delivery times: {self._delivery_times}")
            logger.log(f"max recursion depth: {self.max_depth}")

        logger.log("-" * 53 + "\n")

    def _get_critical_path(
        self,
        makespan: float,
        sequence: list[int],
        finish_times: dict[int, float],
        start_times: dict[int, float],
    ) -> list[int]:
        logger = self._logger

        logger.log(f"identifying critical path for makespan {makespan}")

        b_index = None
        b_op = None
        for op in reversed(sequence):
            if finish_times[op] + self._delivery_times[op] == makespan:
                b_op = op
                b_index = sequence.index(b_op)
                break

        if b_index is None:
            logger.log("no critical operation found!")
            return []

        critical_path = [b_op]
        logger.log(f"critical operation b: {critical_path[0]} at position {b_index}")
        if b_index == 0:
            logger.log("b_index = 0, critical path with just one operation")
            with logger:
                logger.log(f"critical path: {critical_path}")
            return critical_path

        logger.log("searching for preceding operations in sequence")
        for op in reversed(sequence[: b_index + 1]):
            if op != sequence[0]:
                prec_op = sequence[sequence.index(op) - 1]
            else:
                break

            logger.log(f"op: {op} | prec_op: {prec_op}")
            if start_times[op] == finish_times[prec_op]:
                critical_path.insert(0, prec_op)
                logger.log(
                    f"added {prec_op} to critical path (finish[{prec_op}] {finish_times[prec_op]} = start[{op}] {start_times[op]})"
                )
            else:
                logger.log("critical path with just one operation")
                break

        logger.log(f"critical path: {critical_path}")
        return critical_path

    def _check_optimality(self, makespan: float, critical_block: list[int]) -> bool:
        logger = self._logger

        r_min = min(self._release_dates[o] for o in critical_block)
        q_min = min(self._delivery_times[o] for o in critical_block)
        p_sum = sum(self._processing_times[o] for o in critical_block)
        lower_bound = r_min + p_sum + q_min

        logger.log("optimality check")
        with logger:
            logger.log(f"r_min: {r_min}")
            logger.log(f"p_sum: {p_sum}")
            logger.log(f"q_min: {q_min}")
            logger.log(f"LB: {lower_bound}")
            logger.log(f"current makespan: {makespan}")

        is_optimal = lower_bound == makespan
        if is_optimal:
            logger.log("solution is optimal!")
        else:
            logger.log("solution not optimal - continuing search")

        return is_optimal

    def _has_intrajob_precedence(
        self, *, instance: Instance, sequence: list[int]
    ) -> bool:
        jobs_in_sequence = [instance.job_of_op[op] for op in sequence]
        if len(jobs_in_sequence) > len(set(jobs_in_sequence)):
            return True
        return False

    def solve(self) -> tuple[float, list[int]]:
        self._log_initial_state()
        self.best_lmax = float("inf")
        self.best_schedule = []

        logger = self._logger

        logger.breakline()

        def _branch(depth: int = 0) -> tuple[float, list[int]]:
            logger.log(f"{':' * 8} branching at depth {depth} {':' * 8}")

            with logger:
                if depth > self.max_depth:
                    logger.log("max recursion depth reached!")
                    return self.best_lmax, self.best_schedule

                logger.log("[1] run schrage algorithm")

                with logger:
                    schrage = SchrageScheduler(
                        self._operations,
                        self._release_dates,
                        self._processing_times,
                        self._delivery_times,
                        self._instance,
                        logger,
                    )
                    lmax, start_times, finish_times, sequence = schrage.schedule()
                logger.breakline()

                logger.log("[2] verify if a worst schedule was found")
                with logger:
                    if lmax < self.best_lmax:
                        self.best_lmax = lmax
                        self.best_schedule = sequence.copy()
                        logger.log(
                            f"found a better schedule | new lmax: {lmax} with sequence: {sequence}"
                        )
                    else:
                        logger.log(
                            f"no best schedule found | staying with lmax: {self.best_lmax} with sequence: {self.best_schedule}"
                        )
                logger.breakline()

                logger.log("[3] find critical path/block")
                with logger:
                    critical_path = self._get_critical_path(
                        lmax, sequence, finish_times, start_times
                    )
                logger.breakline()

                logger.log("[4] check optimality")
                with logger:
                    if self._check_optimality(lmax, critical_path):
                        return lmax, sequence
                logger.breakline()

                logger.log("[5] checking if sequence has intrajob ops")

                if not self._has_intrajob_precedence(
                    instance=self._instance, sequence=sequence
                ):
                    with logger:
                        logger.log(
                            "current sequence don't have intrajob ops, continue default carlier"
                        )
                        logger.breakline()

                    logger.log("[6] identifying branching operation k")
                    with logger:
                        logger.log(f"critical path: {critical_path}")
                        logger.log(
                            f"q_j: {[self._delivery_times[op] for op in critical_path]}"
                        )
                        i2 = critical_path[-1]
                        q_i2 = self._delivery_times[i2]
                        k = None

                        for op in reversed(critical_path[:-1]):
                            if self._delivery_times[op] < q_i2:
                                k = op
                                break

                        if k is None:
                            logger.log(
                                "no suitable k found for branching - terminating branch"
                            )
                            return lmax, sequence
                        else:
                            logger.log(f"branching operation found: {k}")
                    logger.breakline()

                    logger.log("[7] branching")
                    index_k = critical_path.index(k)
                    index_i2 = critical_path.index(i2)
                    J = critical_path[index_k + 1 : index_i2 + 1]
                    logger.breakline()

                    logger.log(
                        f"[8] branching on operation {k} (q = {self._delivery_times[k]}) with block J = {J}"
                    )
                    logger.breakline()

                    with logger:
                        logger.log(
                            "[8.1] branch 1: modify delivery time of k (process op 'k' before J)"
                        )

                        with logger:
                            new_q = copy.deepcopy(self._delivery_times)
                            q_p = self._delivery_times[J[-1]]
                            new_q[k] = max(
                                self._delivery_times[k],
                                sum(self._processing_times[j] for j in J) + q_p,
                            )

                            if new_q[k] > self._delivery_times[k]:
                                logger.log(
                                    f"branch 1: increasing q[{k}] from {self._delivery_times[k]} to {new_q[k]}"
                                )
                                old_q = self._delivery_times
                                self._delivery_times = new_q
                                f1, _ = _branch(depth + 1)
                                self._delivery_times = old_q
                            else:
                                logger.log(
                                    f"branch 1 skipped: q[{k}] would not increase"
                                )
                                f1 = float("inf")

                        logger.log(
                            "[8.2] branch 2: modify release time of k (process op 'k' after J)"
                        )

                        with logger:
                            new_r = copy.deepcopy(self._release_dates)
                            new_r[k] = max(
                                new_r[k],
                                min(self._release_dates[j] for j in J)
                                + sum(self._processing_times[j] for j in J),
                            )

                            if new_r[k] > self._release_dates[k]:
                                logger.log(
                                    f"branch 2: increasing r[{k}] from {self._release_dates[k]} to {new_r[k]}"
                                )
                                old_r = self._release_dates
                                self._release_dates = new_r
                                f2, _ = _branch(depth + 1)
                                self._release_dates = old_r
                            else:
                                logger.log(
                                    f"branch 2 skipped: r[{k}] would not increase"
                                )
                                f2 = float("inf")
                    return min(f1, f2), sequence
                else:
                    with logger:
                        logger.log(
                            "current sequence HAVE intrajob ops, returning schrage scheduling"
                        )
                    return lmax, sequence

        final_lmax, final_sequence = _branch()

        logger.breakline()

        logger.log("------ carlier algorithm finished ------")
        with logger:
            logger.log(f"greater lmax: {final_lmax}")
            logger.log(f"best sequence: {final_sequence}")
        logger.log("-" * 40)

        return final_lmax, final_sequence
