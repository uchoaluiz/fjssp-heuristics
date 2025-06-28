from pathlib import Path

from .processing.metaheuristic.solution import Solution
from .processing.metaheuristic.solbuilder import SolutionBuilder
from .instance.instance import Instance
from .processing.model import MathModel
from .utils.logger import LOGGER
from .processing.metaheuristic.metaheuristics import Metaheuristics


def run(*, instance_path: Path, output_folder_path: Path, method: str, logger: LOGGER):
    yield "loading instance"
    inst = Instance(instance_path)
    yield f"instance {inst._instance_name} succefully loaded | known optimal = {inst.optimal_solution}\n"

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
            math_model = MathModel(
                instance=inst, output_path=instance_output_path, logger=logger
            )
            math_model.optimize(verbose=0, time_limit=5)
            math_model.print(show_gantt=False)

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

            metaheur = Metaheuristics()
