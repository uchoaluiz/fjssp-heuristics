from pathlib import Path
import os
import json

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
        self.M_i = {}  # M_i[i]: máquinas elegíveis para operação i
        self.p = {}  # p[(i, m)]: tempo de processamento da operação i na máquina m
        self.job_of_op = {}  # job que contém a operação i
        self.O_j = []  # lista de operações para cada job
        self.P_j = []  # precedência (i, i') entre operações de um job
        self.O_m = {}  # O_m[m]: operações que podem ser feitas na máquina m

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

    def print(self, type: str = "sets") -> None:
        print()
        print(":" * 50)
        print("printing built instance".center(50))
        print(":" * 50)

        print(f"\n#jobs: {self.num_jobs} | #machines: {self.num_machines}\n")

        if type in ["array", "all"]:
            for i, job in enumerate(self.jobs):
                for j, operation in enumerate(job):
                    print(f"job {i} | operação {j}")
                    for machines in operation:
                        print(
                            f"   > máquina: {machines[0]} | tempo_process (p_im): {machines[1]}"
                        )
                    print()
                print("~" * 10, end="\n\n")

        if type in ["sets", "all"]:
            print(f"O : conjunto global de operações:\n> {self.O}\n")
            print(f"M : conjunto de máquinas:\n> {self.M}\n")
            print(f"J : conjunto de jobs:\n> {set(range(self.num_jobs))}")

            print()
            print("~" * 10)

            print("\nM_i: conjunto de máquinas elegíveis para a operação 'i':")
            for oper, maqs in self.M_i.items():
                print(f"   > M_{oper}: {maqs}")

            print()
            print("~" * 10)

            print("\nO_j: conjunto de operações do job 'j':")
            for job, opers_job in enumerate(self.O_j):
                print(f"   > O_{job}: {opers_job}")

            print()
            print("~" * 10)

            print("\nP_j: sequência tecnológica do job 'j':")
            for job, seqtec in enumerate(self.P_j):
                print(f"   > job {job}: {self.P_j[job]}")

            print()
            print("~" * 10)

            print("\nO_m : operações que podem ser processadas na máquina 'm':")
            for maq, opers in self.O_m.items():
                print(f"   > O_{maq}: {opers}")

            print()
            print("~" * 10)

            print("\np_{i,m} : tempo de processamento da operação 'i' na máquina m:")
            for (oper, maq), process in self.p.items():
                print(f"   > p_({oper}, {maq}): {process}")

            print()
            print("~" * 10)

            print("\nj(o) : job no qual a operação 'o' faz parte:")
            for oper, job in self.job_of_op.items():
                print(f"   > a operação {oper} faz parte do job {job}")

            print()
            print("~" * 10)
            print()

    def get_optimal(self) -> int:
        json_path = os.path.join("files/instances", "instances.json")

        with open(json_path, 'r') as file:
            instances = json.load(file)
        
        for instance in instances:
            if instance["name"] == self._instance_name:
                return instance.get("optimum")
        
        return None