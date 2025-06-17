from pathlib import Path

from .instance import instance
from .processing import model


def run(*, instance_path: Path, output_folder_path: Path, method: str):
    yield "loading instance"

    inst = instance.Instance(instance_path)

    yield f"instance {inst._instance_name} succefully loaded | optimal = {inst.optimal_solution}"
    

    if method == "cbc" or method == "both":
        yield "optimizing with cbc solver"
        math_model = model.MathModel(instance=inst, output_folder=output_folder_path)
        math_model.run(show_sol=True, verbose=0, time_limit=1800)

    if method == "SA" or method == "both":
        yield "optimizing by simulated annealing"
        pass
