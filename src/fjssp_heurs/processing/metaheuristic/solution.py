from ...instance.instance import Instance
from ...utils.logger import LOGGER
from ...utils.plotting import plot_gantt
from ...utils.gap import evaluate_gap

from pathlib import Path
import numpy as np
import networkx as nx


class Solution:
    def __init__(self, *, instance: Instance, logger: LOGGER, output_path: Path):
        self._instance = instance
        self._logger = logger
        self._output_path = output_path
        self._create_structure()

    def copy_solution(self, *, sol) -> None:
        self._assign_vect[:] = sol._assign_vect[:]
        self._machine_sequence = sol._machine_sequence
        self._start_times = sol._start_times
        self._graph = sol._graph
        self._obj = sol._obj

    def _create_structure(self) -> None:
        instance = self._instance
        logger = self._logger
        logger.log("building solution structure")

        self._assign_vect = np.full(len(instance.O), np.nan)
        self._machine_sequence = [[] for _ in instance.M]
        self._start_times = np.zeros(len(instance.O))
        self._graph = nx.DiGraph()
        self._obj = 0

        logger.log("solution structure built")

    def _build_solution_graph(self) -> None:
        instance = self._instance

        G = self._graph
        G.add_node("S")  # nó inicial fictício
        G.add_node("T")  # nó final fictício

        for op in range(len(self._assign_vect)):
            G.add_node(op)

        for i, j in instance.P_j:
            proc_time = instance.p[(i, self._assign_vect[i])]
            G.add_edge(i, j, weight=proc_time)

        for machine_seq in self._machine_sequence:
            for i in range(len(machine_seq) - 1):
                op_i = machine_seq[i]
                op_j = machine_seq[i + 1]
                proc_time = instance.p[(op_i, self._assign_vect[op_i])]
                G.add_edge(op_i, op_j, weight=proc_time)

        all_ops = set(range(len(self._assign_vect)))
        successors = set(i for (i, j) in instance.P_j) | set(
            i for seq in self._machine_sequence for i in seq[:-1]
        )
        no_preds = (
            all_ops
            - set(j for (i, j) in instance.P_j)
            - set(seq[1] for seq in self._machine_sequence if len(seq) > 1)
        )

        for op in no_preds:
            G.add_edge("S", op, weight=0)

        no_succs = (
            all_ops
            - set(i for (i, j) in instance.P_j)
            - set(seq[:-1] for seq in self._machine_sequence if len(seq) > 1)
        )
        for op in no_succs:
            proc_time = instance.p[(op, self._assign_vect[op])]
            G.add_edge(op, "T", weight=proc_time)

        self._graph = G

    def _find_critical_path(self) -> tuple[list[int]]:
        G = self._graph

        dist = {node: float("-inf") for node in G.nodes}
        dist["S"] = 0
        pred = {node: None for node in G.nodes}

        for u in nx.topological_sort(G):
            for v in G.successors(u):
                weight = G[u][v]["weight"]
                if dist[v] < dist[u] + weight:
                    dist[v] = dist[u] + weight
                    pred[v] = u

        path = []
        current = "T"
        while current:
            path.append(current)
            current = pred[current]
        path.reverse()

        return path

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

    def schedule_solution(self, *, omega: int = 10) -> float:
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

        self._build_solution_graph()

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
        objective_value = self.schedule_solution()

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
