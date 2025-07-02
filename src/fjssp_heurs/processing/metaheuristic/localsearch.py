from ...processing.metaheuristic.solution import Solution
from ...processing.metaheuristic.shifting_bottleneck import ShiftingBottleneck

from numpy import random

from ...utils.logger import LOGGER

from random import sample


class LocalSearch:
    def __init__(self, logger: LOGGER):
        self._logger = logger

    def random_machine_swap(self, sol: Solution) -> None:
        inst = sol._instance
        logger = self._logger

        op = random.choice(inst.O)

        eligible_machines = inst.M_i[op]
        current_machine = sol._assign_vect[op]

        alternative_machines = [m for m in eligible_machines if m != current_machine]
        if not alternative_machines:
            return

        new_machine = random.choice(alternative_machines)
        sol._assign_vect[op] = new_machine
        sol._machine_sequence = sol._get_machines_assignment()

        logger.log(
            f"op: {op} | old_machine: {current_machine} -> new_machine: {new_machine}"
        )

        sol.create_dag()
        sb = ShiftingBottleneck(solution=sol, logger=sol._logger)
        for m, seq in enumerate(sol._machine_sequence):
            if seq:
                sol._graph.consolidate_machine_disjunctive(machine_assignment=seq)

    def random_k_machine_swap(self, sol: Solution, k: int = 2) -> None:
        inst = sol._instance
        ops_to_swap = sample(inst.O, min(k, len(inst.O)))

        for op in ops_to_swap:
            current_machine = sol._assign_vect[op]
            eligible_machines = [m for m in inst.M_i[op] if m != current_machine]
            if eligible_machines:
                new_machine = random.choice(eligible_machines)
                sol._assign_vect[op] = new_machine

        sol._machine_sequence = sol._get_machines_assignment()
        sol.create_dag()
        sb = ShiftingBottleneck(solution=sol, logger=sol._logger)
        for m, seq in enumerate(sol._machine_sequence):
            if seq:
                sol._graph.consolidate_machine_disjunctive(machine_assignment=seq)
