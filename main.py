from argparse import ArgumentParser, Namespace
from pathlib import Path
import os

import src.fjsp_heurs as app


def parse_arguments():
    parser = ArgumentParser(description="FJSP Heuristics")
    parser.add_argument(
        "-i",
        "--instance",
        type=str,
        default="",
        help="The complete file path to the instance file(s)",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="output",
        help="The desired name for the output file",
    )

    parser.add_argument(
        "-m",
        "--method",
        type=str,
        default="",
        help="available methods:\n1. 'cbc' : to solve with CBC solver\n2. 'SA': to solve with simulated annealing",
    )
    args = parser.parse_args()
    return args


def main(*, args: Namespace):
    data_path = Path("files")
    output_data_path = data_path.joinpath("output")

    os.makedirs(data_path, exist_ok=True)
    os.makedirs(output_data_path, exist_ok=True)

    instance_path = Path(args.instance)

    for message in app.run(
        instance_path=instance_path,
        output_folder_path=output_data_path,
        output_file_name=args.output,
    ):
        print(f"> {message}")


if __name__ == "__main__":
    args = parse_arguments()

    main(args=args)
