from ..solution import Solution
from ....instance.instance import Instance
from .carlier import CarlierSolver
from ....utils.logger import LOGGER


class ShiftingBottleneck:
    def __init__(self, *, log_out: str = "both"):
        self._logger = LOGGER(log_path="sbplog.log", out=log_out)

    def process(self, *, solution: Solution, old_logger: LOGGER) -> None:
        with old_logger:
            old_logger.log(
                "SBP algorithm has started, reach 'sbplog.log' for further logs"
            )
            old_logger.breakline()

        logger = self._logger
        instance = solution._instance

        logger.log("starting sbp processing")

        remaining_machines = set(
            [m for m in instance.M if len(solution._machine_sequence[m]) > 0]
        )
        sequenced_machines = set()

        logger.log(f"starting remaining machines to schedule: {remaining_machines}")
        logger.breakline()

        logger.log("sbp algorithm:")

        with logger:
            while len(remaining_machines) > 0:
                logger.log(
                    f"|M'| = {len(remaining_machines)} : there are machines remaining to schedule - continue"
                )

                with logger:
                    logger.log("calling the bottleneck machine finder")
                    bottleneck_machine, machine_seq = self.bottleneck_machine(
                        solution=solution, machines_subset=remaining_machines
                    )

                    logger.log(
                        f"the bottleneck machine is: {bottleneck_machine} | its sequence is: {machine_seq}"
                    )

                    solution._graph.consolidate_sequence_on_machine(
                        machine_id=bottleneck_machine, sequence=machine_seq
                    )
                    solution._machine_sequence[bottleneck_machine] = machine_seq
                    logger.log(f"bottleneck machine {bottleneck_machine} scheduled!")

                    remaining_machines.remove(bottleneck_machine)
                    sequenced_machines.add(bottleneck_machine)

                    logger.log("recalculating times")
                    new_makespan = solution._recalculate_times(logger=logger)

                    logger.log(f"updated makespan: {new_makespan}")
                    logger.breakline()

                    if len(sequenced_machines) > 1:
                        logger.log(
                            "starting reoptimization of already sequenced machines"
                        )
                        with logger:
                            for machine in list(sequenced_machines):
                                if machine == bottleneck_machine:
                                    continue

                                logger.log(f"reoptimizing machine {machine}")

                                operations = solution._machine_sequence[machine]
                                processing_times = {
                                    op: instance.p[(op, machine)] for op in operations
                                }
                                release_dates = {
                                    op: solution._graph.longest_path_to(op=op)
                                    for op in operations
                                }
                                delivery_times = {
                                    op: solution._graph.longest_path_from(op=op)
                                    for op in operations
                                }

                                _, new_sequence = self.solve_single_machine(
                                    operations=operations,
                                    release_dates=release_dates,
                                    processing_times=processing_times,
                                    delivery_times=delivery_times,
                                    instance=instance,
                                )

                                logger.log(f"updating sequence for machine {machine}")
                                solution._graph.remove_sequence_on_machine(
                                    machine_id=machine
                                )
                                solution._graph.consolidate_sequence_on_machine(
                                    machine_id=machine, sequence=new_sequence
                                )
                                solution._machine_sequence[machine] = new_sequence
                                logger.log("recalculating times")
                                solution._recalculate_times(logger=logger)
                                logger.log(f"new makespan: {solution._makespan}")
                    else:
                        logger.log(
                            "only 1 machine scheduled, there's no reoptimization now"
                        )
                    logger.breakline()

    def bottleneck_machine(
        self,
        *,
        solution: Solution,
        machines_subset: set[int],
    ) -> tuple[int, list[int]]:
        logger = self._logger

        instance = solution._instance

        with logger:
            logger.log(
                f"bottleneck machine finder algorithm | elegible machines: {machines_subset} :"
            )

            bottleneck_machine = None
            worst_machine_lateness = -float("inf")
            worst_machine_sequence = list()

            logger.log(
                "for each elegible bottleneck machine, will run a carlier to define its minimum maximum machine lateness"
            )

            release_dates = {
                op: solution._graph.longest_path_to(op=op) for op in instance.O
            }
            delivery_times = {
                op: solution._graph.longest_path_from(op=op) for op in instance.O
            }

            with logger:
                for machine in machines_subset:
                    if not solution._machine_sequence[machine]:
                        continue

                    logger.log(f"machine {machine}")

                    with logger:
                        logger.log(
                            f"time to solve single-machine (by carlier) for machine {machine} | ops assigned: {solution._machine_sequence[machine]}"
                        )

                        operations = solution._machine_sequence[machine]
                        processing_times = {
                            op: instance.p[(op, machine)] for op in operations
                        }

                        logger.log("ops in machine summary:")

                        with logger:
                            for op in operations:
                                logger.log(
                                    f"op: {op} | release: {release_dates[op]} | processing: {processing_times[op]} | delivery: {delivery_times[op]}"
                                )

                        if len(operations) <= 1:
                            logger.log(
                                f"current machine {machine} has only 1 op assigned, there's no carlier's optimization"
                            )
                            op = operations[0]
                            machine_lateness = (
                                release_dates[op]
                                + processing_times[op]
                                + delivery_times[op]
                            )
                            machine_sequence = operations
                        else:
                            logger.log("calling carlier single machine solver")
                            machine_lateness, machine_sequence = (
                                self.solve_single_machine(
                                    operations=operations,
                                    release_dates=release_dates,
                                    processing_times=processing_times,
                                    delivery_times=delivery_times,
                                    instance=instance,
                                )
                            )
                        if machine_lateness > worst_machine_lateness:
                            logger.breakline()
                            logger.log(
                                "found a 'worse' machine than the current bottleneck"
                            )
                            with logger:
                                logger.log(
                                    f"old bottleneck (m: {bottleneck_machine}, lateness: {worst_machine_lateness})"
                                )

                                bottleneck_machine = machine
                                worst_machine_lateness = machine_lateness
                                worst_machine_sequence = machine_sequence

                                logger.log(
                                    f"new bottleneck (m: {bottleneck_machine}, lateness: {worst_machine_lateness})"
                                )
                        else:
                            logger.log(
                                "no 'worse' machine than the current bottleneck found"
                            )
                            logger.log(
                                f"using the same current bottleneck: {bottleneck_machine}, lateness: {worst_machine_lateness}"
                            )

        return bottleneck_machine, worst_machine_sequence

    def solve_single_machine(
        self,
        *,
        operations: list[int],
        release_dates: dict[int, float],
        processing_times: dict[int, float],
        delivery_times: dict[int, float],
        instance: Instance,
    ) -> tuple:
        logger = self._logger

        with logger:
            logger.log("creating a carlier for a single machine scheduling problem")

            carlier_problem = CarlierSolver(
                operations=operations,
                release_dates=release_dates,
                processing_times=processing_times,
                delivery_times=delivery_times,
                instance=instance,
                logger=self._logger,
            )

            logger.log("starting carlier algorithm")
            with logger:
                lmax, sequence = carlier_problem.solve()
            logger.log(
                f"finished carlier algorithm | lmax: {lmax} | machine_sequence: {sequence}"
            )
        return lmax, sequence
