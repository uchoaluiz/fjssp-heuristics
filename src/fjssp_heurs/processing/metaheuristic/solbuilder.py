import numpy as np

from .solution import Solution
from ...utils.logger import LOGGER


class SolutionBuilder:
    def __init__(self, logger: LOGGER) -> None:
        self._logger = logger

    def _define_grasp_alpha(self, *, alpha: float = 0.35) -> None:
        self._grasp_alpha = alpha

    def build_solution(
        self,
        *,
        solution: Solution,
        machines_strategy: str = "grasp",
        grasp_alpha: float = 0.35,
    ) -> None:
        logger = self._logger
        logger.log("building initial solution with constructive heuristic")

        if machines_strategy not in ["grasp", "greedy"]:
            machines_strategy = "random"

        with logger:
            logger.log(f"machines assignment strategy: {machines_strategy}")

            with logger:
                self.select_machines(
                    solution=solution,
                    strategy=machines_strategy,
                    grasp_alpha=grasp_alpha,
                )
                logger.log("[1] machines assignment done")

                with logger:
                    machines_assignment = solution._get_machines_assignment()
                    for machine, ops_in_m in enumerate(machines_assignment):
                        logger.log(
                            f"operations assigned to machine {machine}: {set(ops_in_m)}"
                        )

                self.schedule(solution=solution)

                logger.log("[2] scheduling done")
                with logger:
                    for machine, ops in enumerate(solution._machine_sequence):
                        logger.log(f"machine {machine}: {ops}")

        logger.log("initial solution built")

    def select_machines(
        self, solution: Solution, strategy: str = "grasp", grasp_alpha: float = 0.35
    ) -> None:
        if strategy == "greedy":
            self._select_machines_greedy(solution)

        elif strategy == "grasp":
            self._define_grasp_alpha(alpha=grasp_alpha)
            self._select_machines_grasp(solution)

        else:
            self._select_machines_random(solution)

    def _select_machines_greedy(self, solution: Solution) -> None:
        instance = solution._instance
        for o in instance.O:
            m_candidates = list()
            best_p = float("inf")
            for m in instance.M_i[o]:
                if instance.p[(o, m)] < best_p:
                    m_candidates = [m]
                    best_p = instance.p[(o, m)]
                elif instance.p[(o, m)] == best_p:
                    m_candidates.append(m)
            solution._assign_vect[o] = np.random.choice(m_candidates)

    def _select_machines_grasp(self, solution: Solution) -> None:
        instance = solution._instance
        for o in instance.O:
            candidates = dict()
            for m in instance.M_i[o]:
                candidates[m] = instance.p[(o, m)]
            restricted_candidates_list = [
                machine
                for machine in candidates.keys()
                if candidates[machine]
                <= min(candidates.values())
                + self._grasp_alpha
                * (max(candidates.values()) - min(candidates.values()))
            ]
            solution._assign_vect[o] = np.random.choice(restricted_candidates_list)

    def _select_machines_random(self, solution: Solution) -> None:
        instance = solution._instance
        for o in instance.O:
            solution._assign_vect[o] = np.random.choice(list(instance.M_i[o]))

    def schedule(self, *, solution: Solution) -> None:
        self._schedule_machine_by_machine(solution=solution)

    def _schedule_machine_by_machine(self, *, solution: Solution) -> None:
        def _get_op_priority(
            *, op: int, solution: Solution, current_machine: int
        ) -> tuple[float, float, float, int]:
            instance = solution._instance

            job = instance.job_of_op[op]
            tech_seq = [i for (i, _) in instance.P_j[job]] + [instance.P_j[job][-1][1]]
            remaining_ops = tech_seq[tech_seq.index(op) + 1 :]

            local_remaining = 0.0
            for succ_op in remaining_ops:
                if solution._assign_vect[succ_op] == current_machine:
                    local_remaining += instance.p[(succ_op, current_machine)]

            global_remaining = sum(
                instance.p[(succ_op, solution._assign_vect[succ_op])]
                for succ_op in remaining_ops
            )

            proc_time = instance.p[(op, current_machine)]
            num_dependents = len(remaining_ops)

            return (local_remaining, global_remaining, proc_time, num_dependents)

        instance = solution._instance

        O = instance.O
        M = instance.M
        job_of_op = instance.job_of_op
        P_j = instance.P_j
        p = instance.p

        pred_ops = {o: [] for o in O}
        for job in range(instance.num_jobs):
            tech_seq = [i for (i, _) in P_j[job]] + [P_j[job][-1][1]]
            for i in range(1, len(tech_seq)):
                pred_ops[tech_seq[i]].append(tech_seq[i - 1])

        start_times = [-1.0] * len(O)
        finish_times = [-1.0] * len(O)
        scheduled_ops = set()
        machine_time = {m: 0.0 for m in M}

        while len(scheduled_ops) < len(O):
            progress_made = False

            for m in sorted(M, key=lambda m: machine_time[m]):
                machine_ops = [
                    o
                    for o in O
                    if solution._assign_vect[o] == m and o not in scheduled_ops
                ]

                ready_ops = [
                    o
                    for o in machine_ops
                    if all(pred in scheduled_ops for pred in pred_ops[o])
                ]

                if not ready_ops:
                    continue

                next_op = max(
                    ready_ops,
                    key=lambda op: _get_op_priority(
                        op=op, solution=solution, current_machine=m
                    ),
                )

                job = job_of_op[next_op]
                pred_finish = max(
                    [finish_times[pred] for pred in pred_ops[next_op]], default=0.0
                )
                start_time = max(pred_finish, machine_time[m])
                finish_time = start_time + p[(next_op, m)]

                start_times[next_op] = start_time
                finish_times[next_op] = finish_time
                machine_time[m] = finish_time
                scheduled_ops.add(next_op)

                progress_made = True

            if not progress_made:
                raise Exception("deadlock: no operation could be scheduled.")

        makespan = max(finish_times)

        machines_sequence = list()
        for m in M:
            machines_sequence.append(list())
            for op in instance.O:
                if solution._assign_vect[op] == m:
                    machines_sequence[m].append((op, start_times[op]))
            machines_sequence[m].sort(key=lambda item: item[1])
            machines_sequence[m] = [item[0] for item in machines_sequence[m]]

        solution._start_times = start_times
        solution._finish_times = finish_times
        solution._makespan = makespan
        solution._machine_sequence = machines_sequence
