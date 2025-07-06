from ....instance.instance import Instance
from ....utils.logger import LOGGER


class SchrageScheduler:
    def __init__(
        self,
        operations: list[int],
        release_dates: dict[int, float],
        processing_times: dict[int, float],
        delivery_times: dict[int, float],
        instance: Instance,
        logger: LOGGER,
    ):
        self._operations = operations
        self._release_dates = release_dates
        self._processing_times = processing_times
        self._delivery_times = delivery_times
        self._instance = instance
        self._logger = logger

    def _log_initial_parameters(self):
        logger = self._logger

        logger.log("---------- schrage algorithm parameters ----------")

        with logger:
            logger.log(f"ops: {self._operations}")
            logger.log(f"release dates: {self._release_dates}")
            logger.log(f"processing times: {self._processing_times}")
            logger.log(f"delivery times: {self._delivery_times}")

        logger.log("-" * 50)

        logger.breakline()

    def _update_release_dates_based_on_precedence(self):
        logger = self._logger

        for job, tech_seq in self._instance.S_j.items():
            for i in range(1, len(tech_seq)):
                pred = tech_seq[i - 1]
                curr = tech_seq[i]
                if pred in self._operations and curr in self._operations:
                    new_release = max(
                        self._release_dates[curr],
                        self._release_dates[pred] + self._processing_times[pred],
                    )
                    if new_release != self._release_dates[curr]:
                        logger.log(
                            f"updating release date for op {curr}: {self._release_dates[curr]} -> {new_release} "
                            f"(due to precedence with {pred})"
                        )
                        self._release_dates[curr] = new_release

    def schedule(self) -> tuple[float, dict[int, float], dict[int, float], list[int]]:
        self._log_initial_parameters()
        self._update_release_dates_based_on_precedence()

        logger = self._logger

        t = min(self._release_dates[op] for op in self._operations)
        lmax = 0
        remaining_ops = set(self._operations)
        ready_ops = set()
        start_times = {}
        finish_times = {}
        sequence = []

        logger.log(f"starting schrage scheduling at t = {t}")

        while remaining_ops or ready_ops:
            logger.breakline()
            logger.log(
                f"there are remaining ops to schedule | remaining: {remaining_ops}"
            )

            logger.log(f"current time: {t}")
            logger.log(f"remaining ops: {remaining_ops}")
            logger.log(f"ready ops: {ready_ops}")

            logger.breakline()
            logger.log("checking which ops can become ready:")

            with logger:
                for op in list(remaining_ops):
                    if self._release_dates[op] <= t:
                        job = self._instance.job_of_op[op]
                        tech_seq = self._instance.S_j[job]
                        job_ops = [o for o in self._operations if o in tech_seq]
                        pred_ops = [
                            o for o in job_ops if tech_seq.index(o) < tech_seq.index(op)
                        ]

                        if all(pred_op in sequence for pred_op in pred_ops):
                            ready_ops.add(op)
                            remaining_ops.remove(op)
                            logger.log(
                                f"op {op} is now ready (release date: {self._release_dates[op]})"
                            )
                        else:
                            logger.log(
                                f"op {op} can't be ready yet - missing predecessors: "
                                f"{set(pred_ops) - set(sequence)}"
                            )

            if ready_ops:
                logger.log(f"exists ready ops in time t = {t}")

                op = max(ready_ops, key=lambda o: self._delivery_times[o])
                ready_ops.remove(op)

                start_times[op] = t
                processing_time = self._processing_times[op]
                finish_times[op] = t + processing_time
                sequence.append(op)

                logger.log(
                    f"scheduled op {op} at t = {t} -> {t + processing_time} "
                    f"(q = {self._delivery_times[op]})"
                )

                t += processing_time
                if lmax > t + self._delivery_times[op]:
                    lmax = lmax
                    logger.log(f"staying with best lmax: {lmax}")
                else:
                    lmax = t + self._delivery_times[op]
                    logger.log(f"updated for a NEW lmax: {lmax}")
            else:
                next_release = min(self._release_dates[op] for op in remaining_ops)
                logger.log(f"no ready ops - jumping to t = {next_release}")
                t = next_release

        logger.breakline()

        logger.log("---------- schrage schedule summary ----------")
        with logger:
            logger.log(f"final sequence: {sequence}")
            logger.log(f"start times: {start_times}")
            logger.log(f"finish times: {finish_times}")
            logger.log(f"final lmax: {lmax}")
        logger.log("-" * 50)

        logger.breakline()

        return lmax, start_times, finish_times, sequence
