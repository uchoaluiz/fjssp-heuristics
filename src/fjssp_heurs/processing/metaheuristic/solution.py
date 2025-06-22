from ...instance.instance import Instance
from ...utils.logger import LOGGER
from ...utils.plotting import plot_gantt
from ...utils.gap import evaluate_gap

from pathlib import Path
import numpy as np


class Solution:
    def __init__(self, *, instance: Instance, logger: LOGGER, output_path: Path):
        self._instance = instance
        self._logger = logger
        self._output_path = output_path
        self._create_structure()

    def copy_solution(self, *, sol) -> None:
        self._assign_vect[:] = sol._assign_vect[:]
        self._machine_sequence = sol.machine_sequence
        self._obj = sol._obj

    def _create_structure(self) -> None:
        instance = self._instance
        logger = self._logger
        logger.log("building solution structure")

        self._assign_vect = np.full(len(instance.O), np.nan)
        self._machine_sequence = [[] for _ in instance.M]
        self._start_times = np.zeros(len(instance.O))
        self._obj = 0

        logger.log("solution structure built")

    def _compute_schedule(self) -> tuple[list[float], list[float], float]:
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

        instance = self._instance

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

        step = 0
        while len(scheduled_ops) < len(O):
            progress_made = False

            for m in M:
                machine_ops = [
                    o for o in O if self._assign_vect[o] == m and o not in scheduled_ops
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
                        op=op, solution=self, current_machine=m
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

            step += 1

        makespan = max(finish_times)

        machines_sequence = list()
        for m in M:
            machines_sequence.append(list())
            for op, start_time in enumerate(sorted(start_times)):
                if m == self._assign_vect[op]:
                    machines_sequence[m].append(op)

        return start_times, finish_times, makespan, machines_sequence

    def compute_solution(self, *, omega: int = 10) -> float:
        if np.isnan(self._assign_vect).all():
            self._obj = 0
            return 0

        instance = self._instance
        logger = self._logger

        start_times, finish_times, makespan, self._machine_sequence = (
            self._compute_schedule()
        )
        self._start_times = start_times

        makespan = 0
        for i in instance.O:
            m_i = int(self._assign_vect[i])
            end_time = start_times[i] + instance.p[(i, m_i)]
            makespan = max(makespan, end_time)

        overlap_penalty = 0
        for m, op_sequence in enumerate(self._machine_sequence):
            for idx1 in range(len(op_sequence)):
                i1 = op_sequence[idx1]
                m1 = int(self._assign_vect[i1])
                s1 = start_times[i1]
                f1 = s1 + instance.p[(i1, m1)]

                for idx2 in range(idx1 + 1, len(op_sequence)):
                    i2 = op_sequence[idx2]
                    m2 = int(self._assign_vect[i2])
                    s2 = start_times[i2]
                    f2 = s2 + instance.p[(i2, m2)]

                    if m1 == m2:
                        overlap = max(0, min(f1, f2) - max(s1, s2))
                        overlap_penalty += overlap

        if overlap_penalty:
            with logger:
                logger.log(f"overlaps in solution | penalty: {overlap_penalty}")

        self._obj = makespan + omega * overlap_penalty
        return self._obj

    def print(self, *, show_gantt: bool = True) -> None:
        logger = self._logger
        logger.log("printing solution")

        if np.isnan(self._assign_vect).all():
            with logger:
                logger.log("empty solution")
            return None

        instance = self._instance
        objective_value = self.compute_solution()

        with logger:
            logger.log(
                f"objective: {objective_value} | gap: {evaluate_gap(ub=objective_value, lb=self._instance.optimal_solution)}%"
            )
            for op in instance.O:
                logger.log(
                    f"operation: {op} | start time: {self._start_times[op]} | machine assigned: {self._assign_vect[op]} | end time: {self._start_times[op] + instance.p[(op, self._assign_vect[op])]}"
                )

        logger.breakline()

        plot_gantt(
            start_times={i: self._start_times[i] for i in instance.O},
            machine_assignments={i: int(self._assign_vect[i]) for i in instance.O},
            processing_times=instance.p,
            job_of_op=instance.job_of_op,
            machine_set=instance.M,
            title=f"{self._instance._instance_name} - solution",
            verbose=show_gantt,
            output_file_path=self._output_path
            / f"{self._instance._instance_name} - solution.png",
        )
