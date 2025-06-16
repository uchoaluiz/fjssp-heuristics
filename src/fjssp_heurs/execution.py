from pathlib import Path

from .instance import instance
from .processing import model


def run(
    *, instance_path: Path, output_folder_path: Path, output_file_name: str, method: str
):
    yield "loading instance"

    inst = instance.Instance(instance_path)

    yield "instance succefully loaded"

    if method == "cbc" or method == "both":
        yield "optimizing with cbc solver"
        math_model = model.MathModel(instance=inst)
        math_model.run()

    if method == "SA" or method == "both":
        yield "optimizing by simulated annealing"
        pass
