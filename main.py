from argparse import ArgumentParser, Namespace
from pathlib import Path
import os

import src.fjssp_heurs as app
from src.fjssp_heurs.utils.logger import LOGGER


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
        "-m",
        "--method",
        type=str,
        default="",
        help="available methods: 1. 'cbc': to solve with CBC solver | 2. 'SA': to solve with simulated annealing | 3. 'both': to solve with both methods",
    )
    args = parser.parse_args()
    return args


def main(*, args: Namespace):
    logger = LOGGER()
    data_path = Path("files")
    output_data_path = data_path.joinpath("output")

    os.makedirs(data_path, exist_ok=True)
    os.makedirs(output_data_path, exist_ok=True)

    instance_path = Path(args.instance)

    logger.log("selected preferences:")
    with logger:
        logger.log(f"input path: {instance_path}")
        logger.log(f"output path: {output_data_path}")
        logger.log(f"method(s) to optimize FJSSP: {args.method}\n")

    logger.log("starting program")
    with logger:
        for message in app.run(
            instance_path=instance_path,
            output_folder_path=output_data_path,
            method=args.method,
            logger=logger
        ):
            logger.log(message)


if __name__ == "__main__":
    args = parse_arguments()

    main(args=args)
