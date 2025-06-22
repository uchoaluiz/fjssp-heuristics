from pathlib import Path

from .processing.metaheuristic import solution, solbuilder
from .instance import instance
from .processing import model
from .utils.logger import LOGGER


def run(*, instance_path: Path, output_folder_path: Path, method: str, logger: LOGGER):
    yield "loading instance"
    inst = instance.Instance(instance_path)
    yield f"instance {inst._instance_name} succefully loaded | known optimal = {inst.optimal_solution}"
    logger.breakline()

    instance_output_path = output_folder_path / inst._instance_name
    instance_output_path.mkdir(exist_ok=True)

    """
    logger.log("printing built instance")
    with logger:
        inst.print(logger=logger, type="array")
        # inst.print(logger=logger, type="all")
        # inst.print(logger=logger, type="sets")
    """

    if method == "cbc" or method == "both":
        yield "solving FJSSP with CBC solver"
        with logger:
            math_model = model.MathModel(
                instance=inst, output_path=instance_output_path, logger=logger
            )
            math_model.optimize(verbose=0, time_limit=5)
            math_model.print(show_gantt=False)

    if method == "SA" or method == "both":
        yield "solving FJSSP with simulated annealing"
        with logger:
            sol = solution.Solution(
                instance=inst, logger=logger, output_path=instance_output_path
            )
            sol.print()

            logger.breakline()

            builder = solbuilder.SolutionBuilder(logger=logger)
            builder._define_grasp_alpha(alpha=0.3)

            builder.build_solution(solution=sol, machines_strategy="grasp")
            sol.print(show_gantt=False)
