from pathlib import Path

from .processing.metaheuristic.solution import Solution
from .processing.metaheuristic.solbuilder import SolutionBuilder
from .instance.instance import Instance
from .processing.model import MathModel
from .utils.logger import LOGGER
from .processing.metaheuristic.metaheuristics import Metaheuristics
from .processing.metaheuristic.shifting_bottleneck import ShiftingBottleneck
from .utils.graph import FJSSPGraph


def run(
    *,
    instance_path: Path,
    output_folder_path: Path,
    method: str,
    time_limit: int,
    logger: LOGGER,
):
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

    yield "creating output paths"

    instance_output_path = output_folder_path / inst._instance_name
    instance_output_path.mkdir(exist_ok=True)

    inst_gantts_path = instance_output_path / "Gants"
    inst_gantts_path.mkdir(exist_ok=True)

    inst_dags_path = instance_output_path / "DAGs"
    inst_dags_path.mkdir(exist_ok=True)

    yield "created output paths\n"

    yield f"creating the {inst._instance_name} FJSSP instance DAG"
    inst_machines_assingment = [ops for ops in inst.O_m.values()]
    instance_graph = FJSSPGraph(
        instance=inst,
        machines_assignment=inst_machines_assingment,
        tech_disjunctives=False,
    )
    instance_graph.draw_dag(
        output_path=inst_dags_path,
        title=f"{inst._instance_name} - instance",
        show_no_disjunctives=True,
        arrowstyle="-",
    )
    yield f"created and printed the {inst._instance_name} FJSSP instance DAG\n"

    if method == "cbc" or method == "both":
        yield "solving FJSSP with CBC solver\n"
        with logger:
            yield "creating FJSSP mathematical model"
            math_model = MathModel(instance=inst, logger=logger)
            yield "created FJSSP mathematical model\n"

            yield f"optimizing mathematical model | time limit = {time_limit}"
            math_model.optimize(verbose=0, time_limit=time_limit)
            yield "optimized mathematical model\n"

            yield "returning solver solution (schedule + gantt)"
            math_model.print(
                gantts_output_path=inst_gantts_path, show_gantt=False, by_op=False
            )
            yield "returned solver solution (schedule + gantt)\n"

            yield "creating and writing solver solution's DAG"
            math_model.create_dag()
            math_model.write_dag(
                dag_output_path=inst_dags_path,
                title=f"{inst._instance_name} - solver solution",
            )
            yield "created and wrote solver solution's DAG"

    logger.breakline(2)

    if method == "SA" or method == "both":
        yield "solving FJSSP with simulated annealing\n"
        with logger:
            yield "building a solution representation"
            sol = Solution(instance=inst, logger=logger, output_path=inst_gantts_path)
            yield "built a solution representation\n"

            yield "printing initial solution and its gantt graph"
            sol.print(
                show_gantt=False, gantt_name="initial solution - blank", by_op=False
            )
            yield "printed initial solution and its gantt graph\n"

            yield "building an initial solution with constructive heuristic"
            builder = SolutionBuilder(logger=logger)
            builder.build_solution(
                solution=sol,
                machines_strategy="grasp",
                grasp_alpha=0.3,
            )
            yield "built an initial solution with constructive heuristic\n"

            yield "printing built initial solution and its gantt graph"
            sol.print(
                show_gantt=False,
                gantt_name="initial solution - constructive heur",
                by_op=False,
            )
            yield "printed built initial solution and its gantt graph\n"

            yield "creating built initial solution's DAG"
            sol.create_dag()
            yield "created built initial solution's DAG\n"

            yield "writing built initial solution's DAG"
            sol.write_dag(
                dag_output_path=inst_dags_path,
                title=f"{inst._instance_name} - heur initial solution",
                show_no_disjunctives=False,
            )
            yield "wrote built initial solution's DAG"

            logger.breakline()

            yield "rescheduling machines by shifting bottleneck"
            shift_bottle_sol = Solution(
                instance=inst, logger=logger, output_path=inst_gantts_path
            )
            shift_bottle_sol.copy_solution(sol=sol)
            SBP = ShiftingBottleneck(solution=shift_bottle_sol, logger=logger)
            yield "rescheduled machines by shifting bottleneck\n"

            yield "printing post SBP solution (schedule + gantt)"
            shift_bottle_sol.print(
                show_gantt=False, gantt_name="post SBP solution", by_op=False
            )
            yield "printed post SBP solution (schedule + gantt)\n"

            yield "writing post SBP solution's DAG"
            shift_bottle_sol.write_dag(
                dag_output_path=inst_dags_path,
                title=f"{inst._instance_name} - heur bottleneck",
                show_no_disjunctives=True,
            )
            yield "wrote post SBP solution's DAG\n"

            yield "starting simulated annealing metaheuristic"
            metaheur = Metaheuristics()
            sa_sol = Solution(
                instance=inst, logger=logger, output_path=output_folder_path
            )
            sa_sol.copy_solution(sol=sol)
            metaheur.sa(sol=sa_sol, max_time=time_limit)
            yield "finished simulated annealing metaheuristic"
