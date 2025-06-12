from pathlib import Path

from .instance import instance


def run(*, instance_path: Path, output_folder_path: Path, output_file_name: str):
    yield "loading instance"
    inst = instance.Instance(instance_path)
