from pathlib import Path
import pandas as pd

from .processing.metaheuristic.solution import Solution
from .processing.metaheuristic.solbuilder import SolutionBuilder
from .instance.instance import Instance
from .processing.model import MathModel
from .utils.logger import LOGGER
from .processing.metaheuristic.sa import SimulatedAnnealing
from .utils.graph import FJSSPGraph
from .processing.metaheuristic.sbp.sbp import ShiftingBottleneck
from .processing.metaheuristic.localsearch import LocalSearch
from .utils.gap import evaluate_gap


def run(
    *,
    instance_path: Path,
    output_folder_path: Path,
    method: str,
    time_limit: int,
    logger: LOGGER,
    sa_log_writing: bool,
    sbp_log_writing: bool,
    seed: int = 42,
):
    inst = Instance(instance_path)
    results_df = pd.DataFrame()

    yield f"instance {inst._instance_name} succefully loaded | known optimal = {inst.optimal_solution}"

    instance_output_path = output_folder_path / inst._instance_name
    instance_output_path.mkdir(exist_ok=True)

    inst_gantts_path = instance_output_path / "Gantts"
    inst_gantts_path.mkdir(exist_ok=True)

    inst_dags_path = instance_output_path / "DAGs"
    inst_dags_path.mkdir(exist_ok=True)

    yield "created output paths"

    inst.write(instance_path=instance_output_path)
    instance_graph = FJSSPGraph(
        instance=inst, tech_disjunc=True, graph_type="fjssp instance"
    )
    instance_graph.export_visualization(
        output_path=inst_dags_path,
        title=f"{inst._instance_name} - instance",
        arrowstyle="-",
        show="both",
    )
    yield f"created and saved '{inst._instance_name}' instance's DAGs and parameters read, check {instance_output_path}"

    if method == "cbc" or method == "both":
        logger.breakline()
        yield "solving FJSSP with CBC solver"

        with logger:
            yield "creating FJSSP mathematical model"
            math_model = MathModel(instance=inst, logger=logger)

            yield f"optimizing mathematical model | time limit = {time_limit} s"
            with logger:
                solver_feasible, solver_makespan, solver_time, solver_gap = (
                    math_model.optimize(verbose=0, time_limit=time_limit)
                )

            if solver_feasible:
                yield "printing solver solution"
                math_model.print(print_style="arrays")

                logger.breakline()

                yield "saving solver solution' gantt graph"
                math_model.save_gantt(gantt_output_path=inst_gantts_path)

                yield "creating and writing solver solution's DAG"
                math_model.create_graph(tech_disjunc=True)
                math_model.export_dag(
                    dag_output_path=inst_dags_path,
                    title=f"{inst._instance_name} - solver solution",
                    show="real disjunctives",
                )

                results_df["solver makespan"] = [solver_makespan]
                results_df["solver time"] = [solver_time]
                results_df["solver gap"] = [solver_gap]

            else:
                yield "solver optimization didn't reach a feasible solution"

    if method == "SA" or method == "both":
        logger.breakline()
        yield "solving FJSSP with heuristic approach"

        with logger:
            sol = Solution(instance=inst, logger=logger)
            yield "built a solution representation"

            yield "building a feasible initial solution with constructive heuristic"
            builder = SolutionBuilder(logger=logger, seed=seed)
            builder.define_hiperparams(alpha_grasp=0.35)

            builder.build_solution(
                solution=sol,
                machines_strategy="grasp",
                scheduler_approach="machine_by_machine",
            )

            results_df["constr.heur makespan"] = [sol._makespan]
            results_df["constr.heur gap"] = [
                evaluate_gap(ub=sol._makespan, lb=inst.optimal_solution)
            ]

            logger.breakline()

            yield "printing built initial solution"
            sol.print(
                print_style="arrays",
            )

            logger.breakline()

            yield "saving built initial solution' gantt graph"
            sol.save_gantt(
                gantt_output=inst_gantts_path, gantt_title="constructive heur solution"
            )

            yield "creating and writing initial solution's DAG"
            sol.create_graph(tech_disjunc=True, graph_type="complete fjssp")
            sol.export_dag(
                dag_output_path=inst_dags_path,
                title=f"{inst._instance_name} - constructive heuristic initial solution",
                show="visual disjunctives",
            )

            yield "preparing simulated annealing initial solution"
            sa_sol = Solution(instance=inst, logger=logger)
            sa_sol.copy_solution(sol=sol)

            yield "starting SA optimization"
            sa = SimulatedAnnealing(
                local_search=LocalSearch(logger=logger, seed=seed),
                log_writing=sa_log_writing,
                max_time=time_limit,
                sbp_solver=ShiftingBottleneck(
                    log_out="off" if not sbp_log_writing else "file"
                ),
                seed=seed,
            )

            sa_sol, sa_time, sa_gap = sa.optimize(solution=sa_sol)

            results_df["SA makespan"] = [sa_sol._makespan]
            results_df["SA time"] = [sa_time]
            results_df["SA gap"] = [sa_gap]

            logger.breakline()

            yield "printing SA solution"
            sa_sol.print(print_style="arrays")

            logger.breakline()

            yield "saving SA solution' gantt graph"
            sa_sol.save_gantt(
                gantt_output=inst_gantts_path, gantt_title="SA best solution"
            )

            yield "creating and writing SA solution's DAG"
            sa_sol.create_graph(tech_disjunc=False, graph_type="complete fjssp")
            sa_sol.export_dag(
                dag_output_path=inst_dags_path,
                title=f"{inst._instance_name} - SA best solution",
                show="visual disjunctives",
            )

    logger.breakline()

    yield f"saving results in a csv, check {instance_output_path}"

    results_df.to_csv(instance_output_path / "results.csv", index=False)

    logger.breakline()
