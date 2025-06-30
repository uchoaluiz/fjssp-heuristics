from pathlib import Path

from .processing.metaheuristic.solution import Solution
from .processing.metaheuristic.solbuilder import SolutionBuilder
from .instance.instance import Instance
from .processing.model import MathModel
from .utils.logger import LOGGER
from .processing.metaheuristic.metaheuristics import Metaheuristics
from .processing.metaheuristic.shifting_bottleneck import ShiftingBottleneck
from .utils.graph import FJSSPGraph


def run(*, instance_path: Path, output_folder_path: Path, method: str, logger: LOGGER):
    yield "loading instance"
    inst = Instance(instance_path)
    yield f"instance {inst._instance_name} succefully loaded | known optimal = {inst.optimal_solution}\n"

    """
    logger.log("printing built instance")
    with logger:
        inst.print(logger=logger, type="array")
        # inst.print(logger=logger, type="all")
        # inst.print(logger=logger, type="sets")
    """

    instance_output_path = output_folder_path / inst._instance_name
    instance_output_path.mkdir(exist_ok=True)

    inst_machines_assingment = [ops for ops in inst.O_m.values()]
    instance_graph = FJSSPGraph(
        instance=inst,
        machines_assignment=inst_machines_assingment,
        tech_disjunctives=False,
    )
    instance_graph.draw_dag(
        output_path=instance_output_path,
        title=f"{inst._instance_name} - DAG - instance",
        show_no_disjunctives=True,
        arrowstyle="-",
        show_weights=True,
    )

    if method == "cbc" or method == "both":
        yield "solving FJSSP with CBC solver"
        with logger:
            math_model = MathModel(
                instance=inst, output_path=instance_output_path, logger=logger
            )
            math_model.optimize(verbose=0, time_limit=5)
            math_model.print(show_gantt=False)
            solver_dag = FJSSPGraph(
                instance=inst,
                machines_assignment=math_model._machine_assignment,
                tech_disjunctives=True,
            )
            solver_dag.draw_dag(
                output_path=instance_output_path,
                title=f"{inst._instance_name} - DAG - solver solution",
                show_no_disjunctives=False,
                show_weights=True,
            )

    if method == "SA" or method == "both":
        yield "solving FJSSP with simulated annealing"
        with logger:
            sol = Solution(
                instance=inst, logger=logger, output_path=instance_output_path
            )

            sol.print(show_gantt=False, gantt_name="initial solution")

            builder = SolutionBuilder(logger=logger)
            builder.build_solution(
                solution=sol,
                machines_strategy="grasp",
                grasp_alpha=0.3,
            )
            sol.print(show_gantt=False, gantt_name="initial solution")

            heur_sol_dag = FJSSPGraph(
                instance=inst,
                machines_assignment=sol._get_machines_assignment(),
                tech_disjunctives=True,
            )
            heur_sol_dag.draw_dag(
                output_path=instance_output_path,
                title=f"{inst._instance_name} - DAG - heur initial solution",
                show_no_disjunctives=False,
                show_weights=True,
            )

            logger.breakline()

            shift_bottle = ShiftingBottleneck(solution=sol, logger=logger)
            sol.print(show_gantt=False, gantt_name="post SBP solution", by_op=False)
            sol._graph.draw_dag(
                output_path=instance_output_path,
                title=f"{inst._instance_name} - DAG - heur bottleneck",
                show_no_disjunctives=True,
                show_weights=True,
            )
