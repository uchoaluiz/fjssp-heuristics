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
        help="the complete file path to the instance file(s)",
    )

    parser.add_argument(
        "-m",
        "--method",
        type=str,
        default="",
        choices=["cbc", "SA", "both"],
        help="method(s) to optimize the problem",
    )

    parser.add_argument(
        "-t", "--timelimit", type=float, default=300, help="time limit to stop methods"
    )

    parser.add_argument(
        "-salog",
        "--salogwriting",
        type=str,
        default="N",
        choices=["Y", "N"],
        help="whether SA processing logs should be written to a file",
    )

    parser.add_argument(
        "-sbplog",
        "--sbplogwriting",
        type=str,
        default="N",
        choices=["Y", "N"],
        help="whether SBP processing logs should be written to a file.",
    )

    parser.add_argument(
        "-seed", "--seed", type=int, default=42, help="wanted stochastic seed"
    )

    args = parser.parse_args()
    return args


def main(*, args: Namespace):
    logger = LOGGER(log_path="execlog.log", out="both")
    data_path = Path("files")
    output_data_path = data_path.joinpath("output")

    os.makedirs(data_path, exist_ok=True)
    os.makedirs(output_data_path, exist_ok=True)

    instance_path = Path(args.instance)

    logger.log("selected preferences:")
    with logger:
        logger.log(f"input path: {instance_path}")
        logger.log(f"output path: {output_data_path}")
        logger.log(f"method(s) to optimize FJSSP: {args.method}")
        logger.log(f"time limit: {args.timelimit}")
        logger.log(f"write SA logs? {'yes' if args.salogwriting == 'Y' else 'no'}")
        logger.log(f"write SBP logs? {'yes' if args.sbplogwriting == 'Y' else 'no'}")
        logger.log(f"randomness seed: {args.seed}")
    logger.breakline()

    logger.log("starting program")

    h = 1
    with logger:
        for message in app.run(
            instance_path=instance_path,
            output_folder_path=output_data_path,
            method=args.method,
            logger=logger,
            time_limit=args.timelimit,
            sa_log_writing=True if args.salogwriting == "Y" else False,
            sbp_log_writing=True if args.sbplogwriting == "Y" else False,
            seed=args.seed,
        ):
            logger.log(f"[{h}] {message}")
            h += 1

    logger.log("finishing program")


if __name__ == "__main__":
    args = parse_arguments()

    main(args=args)
