from pathlib import Path
import os
import json

from ..utils.logger import LOGGER


class Instance:
    def __init__(self, input: Path) -> None:
        self.input_path = input
        self._instance_name = input.stem
        self.build_instance()
        self.optimal_solution = self.get_optimal()

    def build_instance(self) -> None:
        self.jobs = []
        self.num_jobs = 0
        self.num_machines = 0

        self.O = []
        self.M = set()
        self.M_i = dict()  # M_i[i]: máquinas elegíveis para operação i
        self.p = dict()  # p[(i, m)]: tempo de processamento da operação i na máquina m
        self.job_of_op = dict()  # job que contém a operação i
        self.O_j = []  # lista de operações para cada job
        self.P_j = []  # precedência (i, i') entre operações de um job
        self.O_m = dict()  # O_m[m]: operações que podem ser feitas na máquina m
        self.S_j = dict()  # S_j[j]: lista da sequência tecnológica do job j

        with open(self.input_path, "r") as file:
            first_line = file.readline().strip()
            self.num_jobs, self.num_machines = map(int, first_line.split())

            op_counter = 0

            for j in range(self.num_jobs):
                self.P_j.append(list())
                line = file.readline().strip()
                tokens = list(map(int, line.split()))
                num_operations = tokens[0]
                operations = []
                job_ops = []

                idx = 1
                for _ in range(num_operations):
                    num_machines = tokens[idx]
                    idx += 1
                    machine_options = []
                    op_id = op_counter
                    self.job_of_op[op_id] = j
                    self.M_i[op_id] = set()

                    for _ in range(num_machines):
                        machine = tokens[idx]
                        time = tokens[idx + 1]
                        machine_options.append((machine, time))
                        self.M.add(machine)
                        self.M_i[op_id].add(machine)
                        self.p[(op_id, machine)] = time
                        idx += 2

                    operations.append(machine_options)
                    job_ops.append(op_id)
                    op_counter += 1

                self.jobs.append(operations)
                self.O_j.append(job_ops)

                for a, b in zip(job_ops[:-1], job_ops[1:]):
                    self.P_j[j].append((a, b))

        self.O = list(self.job_of_op.keys())
        self.M = list(self.M)

        self.O_m = {m: [] for m in self.M}
        for i in self.O:
            for m in self.M_i[i]:
                self.O_m[m].append(i)

        for job in range(self.num_jobs):
            self.S_j[job] = [i for (i, _) in self.P_j[job]] + [self.P_j[job][-1][1]]

    def print(self, *, logger: LOGGER, type: str = "sets") -> None:
        logger.log(f"#jobs: {self.num_jobs} | #machines: {self.num_machines}\n")

        if type in ["array", "all"]:
            for i, job in enumerate(self.jobs):
                for j, operation in enumerate(job):
                    logger.log(f"job {i} | operation {j}")
                    with logger:
                        for machines in operation:
                            logger.log(
                                f"machine: {machines[0]} | process_time (p_im): {machines[1]}"
                            )
                        logger.breakline()

        if type in ["sets", "all"]:
            logger.log("O: set of global operations:")
            with logger:
                logger.log(f"{self.O}")
                logger.breakline()
            logger.log("M: set of machines:")
            with logger:
                logger.log(f"{self.M}")
                logger.breakline()
            logger.log("J: set of jobs:")
            with logger:
                logger.log(f"{set(range(self.num_jobs))}")

            logger.breakline()

            logger.log("M_i: allowed machines for operation 'i':")
            with logger:
                for oper, maqs in self.M_i.items():
                    logger.log(f"M_{oper}: {maqs}")

            logger.breakline()

            logger.log("O_j: operations in job 'j':")
            with logger:
                for job, opers_job in enumerate(self.O_j):
                    logger.log(f"O_{job}: {opers_job}")

            logger.breakline()

            logger.log("S_j: technological sequence to job 'j':")
            with logger:
                for job, seqtec in self.S_j.items():
                    logger.log(f"S_{job}: {seqtec}")

            logger.breakline()

            logger.log("P_j: technological sequence edges to job 'j':")
            with logger:
                for job, seqtec in enumerate(self.P_j):
                    logger.log(f"job {job}: {self.P_j[job]}")

            logger.breakline()

            logger.log("O_m: operations that can be processed by machine 'm':")
            with logger:
                for maq, opers in self.O_m.items():
                    logger.log(f"O_{maq}: {opers}")

            logger.breakline()

            logger.log("p_{i,m}: processing time of operation 'i' in machine 'm':")
            with logger:
                for (oper, maq), process in self.p.items():
                    logger.log(f"p_({oper}, {maq}): {process}")

            logger.breakline()

            logger.log("j(o): job to which operation 'o' belongs:")
            with logger:
                for oper, job in self.job_of_op.items():
                    logger.log(f"operation {oper} belongs to job {job}")

        logger.breakline(2)

    def get_optimal(self) -> int:
        json_path = os.path.join("files/instances", "instances.json")

        with open(json_path, "r") as file:
            instances = json.load(file)

        for instance in instances:
            if instance["name"] == self._instance_name:
                return instance.get("optimum")

        return None

    def write(self, *, instance_path: Path) -> None:
        file_path = instance_path / f"instance - {self._instance_name}.inst"
        inst_file = open(
            file_path,
            "w",
            encoding="utf-8",
        )

        inst_file.write(f"#jobs: {self.num_jobs} | #machines: {self.num_machines}\n")

        inst_file.write("O: set of global operations:\n")
        inst_file.write(f"{self.O}\n")

        inst_file.write("M: set of machines:\n")

        inst_file.write(f"{self.M}\n")

        inst_file.write("J: set of jobs:\n")

        inst_file.write(f"{set(range(self.num_jobs))}\n")

        inst_file.write("M_i: allowed machines for operation 'i':\n")

        for oper, maqs in self.M_i.items():
            inst_file.write(f"M_{oper}: {maqs}\n")

        inst_file.write("O_j: operations in job 'j':\n")

        for job, opers_job in enumerate(self.O_j):
            inst_file.write(f"O_{job}: {opers_job}\n")

        inst_file.write("S_j: technological sequence to job 'j':\n")

        for job, seqtec in self.S_j.items():
            inst_file.write(f"S_{job}: {seqtec}\n")

        inst_file.write("P_j: technological sequence edges to job 'j':\n")

        for job, seqtec in enumerate(self.P_j):
            inst_file.write(f"job {job}: {self.P_j[job]}\n")

        inst_file.write("O_m: operations that can be processed by machine 'm':\n")

        for maq, opers in self.O_m.items():
            inst_file.write(f"O_{maq}: {opers}\n")

        inst_file.write("p_{i,m}: processing time of operation 'i' in machine 'm':\n")

        for (oper, maq), process in self.p.items():
            inst_file.write(f"p_({oper}, {maq}): {process}\n")

        inst_file.write("j(o): job to which operation 'o' belongs:\n")

        for oper, job in self.job_of_op.items():
            inst_file.write(f"operation {oper} belongs to job {job}\n")
