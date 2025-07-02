from ..metaheuristic.solution import Solution
from ...instance.instance import Instance
from ...utils.graph import FJSSPGraph
from ...utils.logger import LOGGER
import copy


class SingleMachineScheduling:
    def __init__(
        self,
        operations: list[int],
        release_dates: dict[int, float],
        processing_times: dict[int, float],
        delivery_times: dict[int, float],
        instance: Instance,
        logger: LOGGER,
    ):
        self._operations = operations
        self._release_dates = release_dates
        self._processing_times = processing_times
        self._delivery_times = delivery_times

        self._instance = instance
        self._logger = logger

        self.best_cmax = float("inf")
        self.best_schedule = []

    def schrage_algorithm(self) -> None:
        instance = self._instance
        logger = self._logger

        operations = self._operations
        release_dates = self._release_dates
        processing_times = self._processing_times
        delivery_times = self._delivery_times

        t = min(release_dates[op] for op in operations)
        cmax = 0

        for job, tech_seq in self._instance.S_j.items():
            for i in range(1, len(tech_seq)):
                pred = tech_seq[i - 1]
                curr = tech_seq[i]
                if pred in operations and curr in operations:
                    release_dates[curr] = max(
                        release_dates[curr],
                        release_dates[pred] + processing_times[pred],
                    )

        remaining_ops = set(operations)
        ready_ops = set()

        start_times = dict()
        finish_times = dict()
        sequence = []

        self._logger.log(f"starting schrage algorithm with ops: {operations}")
        with self._logger:
            self._logger.log(
                f"releases: {release_dates} | proccss: {processing_times} | deliveries: {delivery_times}"
            )

        self._logger.breakline()

        with logger:
            logger.log("scheduling all ops in this machine")
            while remaining_ops or ready_ops:
                logger.log(f"current machine time 't' = {t}")
                with logger:
                    for op in list(remaining_ops):
                        if release_dates[op] <= t:
                            job = instance.job_of_op[op]
                            tech_seq = instance.S_j[job]
                            job_ops = [o for o in operations if o in tech_seq]
                            pred_ops = [
                                o
                                for o in job_ops
                                if tech_seq.index(o) < tech_seq.index(op)
                            ]

                            if all(pred_op in sequence for pred_op in pred_ops):
                                ready_ops.add(op)
                                remaining_ops.remove(op)
                                logger.log(
                                    f"operation {op} became ready at time {t} (its release date {release_dates[op]} < {t} and its predecence are in sequence)"
                                )
                            else:
                                logger.log(
                                    f"operation {op} can't become ready because not of all their pred are scheduled"
                                )

                logger.breakline()

                if ready_ops:
                    logger.log(
                        f"ready ops on time {t} : {ready_ops} | choosing that one with greater delivery times"
                    )
                    with logger:
                        op = max(ready_ops, key=lambda o: delivery_times[o])
                        ready_ops.remove(op)

                        start_times[op] = t
                        sequence.append(op)

                        t += processing_times[op]
                        finish_times[op] = t
                        cmax = max(cmax, t + delivery_times[op])
                        self._logger.log(
                            f"selected op {op} scheduled at t={start_times[op]} -> {finish_times[op]}, cmax={cmax}"
                        )
                else:
                    logger.log(f"no ready ops in time {t}, jump for the next earlier")
                    t = min(release_dates[op] for op in remaining_ops)

        return cmax, start_times, finish_times, sequence

    def _get_critical_path(
        self,
        *,
        makespan: float,
        sequence: list[int],
        start_times: dict[int, float],
        finish_times: dict[int, float],
    ) -> list[int]:
        self._logger.log(f"Getting critical path for makespan={makespan}")

        for i in reversed(range(len(sequence))):
            op = sequence[i]
            if finish_times[op] + self._delivery_times[op] == makespan:
                b_index = i
                break

        critical_path = [sequence[b_index]]

        for i in reversed(range(b_index)):
            curr = sequence[i]
            next_op = critical_path[0]
            if finish_times[curr] == start_times[next_op]:
                critical_path.insert(0, curr)

        self._logger.log(f"Critical path: {critical_path}")

        return critical_path

    def carlier_algorithm(self, max_depth=30) -> None:
        logger = self._logger
        self.best_cmax = float("inf")
        self.best_schedule = []

        def _check_optimal(makespan: float, critical_block: list) -> bool:
            r_min = min(self._release_dates[o] for o in critical_block)
            q_min = min(self._delivery_times[o] for o in critical_block)
            p_sum = sum(self._processing_times[o] for o in critical_block)
            optimal = (r_min + p_sum + q_min) == makespan
            self._logger.log(
                f"Check optimal: r={r_min}, p={p_sum}, q={q_min}, L={makespan}, result={optimal}"
            )
            return optimal

        def _branch(depth=0) -> tuple[float, list[int]]:
            if depth > max_depth:
                logger.log("max recursion depth reached")
                return self.best_cmax, self.best_schedule

            logger.log(f"branching at depth {depth} | single-machine by schrage:")
            with logger:
                L, start_times, finish_times, sequence = self.schrage_algorithm()

            if L < self.best_cmax:
                self.best_cmax = L
                self.best_schedule = sequence
                self._logger.log(f"updated best cmax={L}, sequence={sequence}")

            critical_path = self._get_critical_path(
                makespan=L,
                sequence=sequence,
                start_times=start_times,
                finish_times=finish_times,
            )

            if _check_optimal(L, critical_path):
                self._logger.log("Found optimal schedule.")
                return L, sequence

            i2 = critical_path[-1]
            q_i2 = self._delivery_times[i2]

            k = None
            for idx in range(len(critical_path) - 1):
                op = critical_path[idx]
                if self._delivery_times[op] < q_i2:
                    k = op

            if k is None:
                self._logger.log("No valid k found for branching — stopping.")
                return L, sequence

            index_k = critical_path.index(k)
            index_i2 = critical_path.index(i2)
            J = critical_path[index_k + 1 : index_i2 + 1]
            self._logger.log(f"branching on op {k} with block J={J}")

            new_q = copy.deepcopy(self._delivery_times)
            q_p = self._delivery_times[J[-1]]
            new_q[k] = max(
                self._delivery_times[k],
                sum(self._processing_times[j] for j in J) + q_p,
            )

            if new_q[k] > self._delivery_times[k]:
                old_q = self._delivery_times
                self._delivery_times = new_q
                self._logger.log(f"Branch 1: Increasing q[{k}] -> {new_q[k]}")
                f1, _ = _branch(depth + 1)
                self._delivery_times = old_q
            else:
                self._logger.log(f"Branch 1 skipped: no increase in q[{k}]")
                f1 = float("inf")

            new_r = copy.deepcopy(self._release_dates)
            new_r[k] = max(
                new_r[k],
                min(self._release_dates[j] for j in J)
                + sum(self._processing_times[j] for j in J),
            )

            if new_r[k] > self._release_dates[k]:
                old_r = self._release_dates
                self._release_dates = new_r
                self._logger.log(f"Branch 2: Increasing r[{k}] -> {new_r[k]}")
                f2, _ = _branch(depth + 1)
                self._release_dates = old_r
            else:
                self._logger.log(f"Branch 2 skipped: no increase in r[{k}]")
                f2 = float("inf")

            return min(f1, f2), sequence

        final_cmax, final_sequence = _branch()
        self._logger.log(
            f"Finished Carlier: best_cmax={final_cmax}, best_sequence={final_sequence}"
        )

        return final_cmax, final_sequence


class ShiftingBottleneck:
    def __init__(self, *, solution: Solution, logger: LOGGER):
        self._logger = logger
        self._logger.on = -1

        self._solution = solution
        self._instance = self._solution._instance

        logger.log("starting shifting bottleneck algorithm")

        logger.log("creating JSP instange DAG")
        self._solution.create_dag()
        self._logger.log("created JSP instance DAG")

        self._logger.breakline()

        with logger:
            logger.log("starting algorithm")

            self.execute()
        self._logger.on = 1

    def execute(self) -> None:
        logger = self._logger
        instance = self._solution._instance

        logger.log("starting SBP - scheduling bottleneck machine per time")

        remaining_machines = set(
            [m for m in instance.M if len(self._solution._machine_sequence[m]) > 0]
        )

        logger.log(
            f"remaining machines to schedule: {remaining_machines} | ops assigned to each: {[self._solution._machine_sequence[m] for m in remaining_machines]}"
        )

        logger.breakline()

        with logger:
            while len(remaining_machines) > 0:
                logger.log(
                    f"{len(remaining_machines)} machines remaining to schedule | machines remaining {remaining_machines}"
                )
                with logger:
                    for m in remaining_machines:
                        logger.log(
                            f"machine: {m} | sequence: {self._solution._machine_sequence[m]}"
                        )

                logger.breakline()

                with logger:
                    logger.log("finding bottleneck machine")
                    with logger:
                        bottleneck_machine, machine_seq = self._bottleneck_machine(
                            machines_subset=remaining_machines
                        )

                    logger.log(
                        f"the bottleneck machine is: {bottleneck_machine} | its sequence is: {machine_seq}"
                    )

                    self._solution._graph.consolidate_machine_disjunctive(
                        machine_assignment=machine_seq
                    )

                    remaining_machines.remove(bottleneck_machine)

                    self._solution._machine_sequence[bottleneck_machine] = machine_seq

                    self._solution._recalculate_times()

                    logger.log(f"Makespan atualizado: {self._solution._makespan}")

    def _solve_single_machine(
        self,
        *,
        operations: list[int],
        release_dates: dict[int, float],
        processing_times: dict[int, float],
        delivery_times: dict[int, float],
    ) -> tuple:
        logger = self._logger

        logger.log("creating a single machine scheduling problem")

        subproblem = SingleMachineScheduling(
            operations=operations,
            release_dates=release_dates,
            processing_times=processing_times,
            delivery_times=delivery_times,
            instance=self._instance,
            logger=self._logger,
        )

        logger.log("single machine subproblem created")

        logger.log("starting carlier algorithm")
        L, sequence = subproblem.carlier_algorithm()
        logger.log(
            f"finished carlier algorithm | L: {L} | machine_sequence: {sequence}"
        )
        return L, sequence

    def _bottleneck_machine(self, *, machines_subset: set[int]) -> tuple[int, Solution]:
        logger = self._logger
        solution = self._solution
        instance = self._instance

        bottleneck_machine = None
        worst_lateness = -float("inf")
        worst_machine_sequence = list()

        logger.log(
            f"finding the bottleneck machine | machines to schedule: {machines_subset}"
        )

        with logger:
            logger.log("machines assignment:")
            for m, ops in enumerate(solution._machine_sequence):
                logger.log(f"machine: {m} | ops: {ops}")

        logger.breakline()

        with logger:
            for machine in machines_subset:
                logger.log(
                    f"solving single-machine for machine {machine} | ops assigned: {solution._machine_sequence[machine]}"
                )
                if not solution._machine_sequence[machine]:
                    continue

                operations = solution._machine_sequence[machine]
                processing_times = {op: instance.p[(op, machine)] for op in operations}

                release_dates = {
                    op: self._solution._graph._longest_to(op=op) for op in operations
                }
                delivery_times = {
                    op: self._solution._graph._longest_from(op=op) for op in operations
                }

                logger.log(
                    "calculated new longest_to and longest_from to receive release and delivery dates"
                )

                logger.log(
                    f"solving a single machine subproblem for machine: {machine}"
                )
                with logger:
                    for op in operations:
                        logger.log(
                            f"op: {op} | release: {release_dates[op]} | processing: {processing_times[op]} | delivery: {delivery_times[op]}"
                        )

                    lateness, machine_sequence = self._solve_single_machine(
                        operations=operations,
                        release_dates=release_dates,
                        processing_times=processing_times,
                        delivery_times=delivery_times,
                    )
                    if lateness > worst_lateness:
                        bottleneck_machine = machine
                        worst_lateness = lateness
                        worst_machine_sequence = machine_sequence

        return bottleneck_machine, worst_machine_sequence
