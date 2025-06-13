from pathlib import Path


class Instance:
    def __init__(self, input: Path) -> None:
        self.input_path = input
        self.build_instance()

    def build_instance(self) -> None:
        self.jobs = []
        self.num_jobs = 0
        self.num_machines = 0

        self.O = []
        self.M = set()
        self.M_i = {}  # M_i[i]: máquinas elegíveis para operação i
        self.p = {}  # p[i, m]: tempo de processamento da operação i na máquina m
        self.job_of_op = {}  # job que contém a operação i
        self.O_j = []  # lista de operações para cada job
        self.P_j = []  # precedência (i, i') entre operações de um job
        self.O_m = {}  # O_m[m]: operações que podem ser feitas na máquina m

        with open(self.input_path, "r") as file:
            first_line = file.readline().strip()
            self.num_jobs, self.num_machines = map(int, first_line.split())

            op_counter = 0

            for j in range(self.num_jobs):
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
                        self.p[op_id, machine] = time
                        idx += 2

                    operations.append(machine_options)
                    job_ops.append(op_id)
                    op_counter += 1

                self.jobs.append(operations)
                self.O_j.append(job_ops)

                for a, b in zip(job_ops[:-1], job_ops[1:]):
                    self.P_j.append((a, b))

        self.O = list(self.job_of_op.keys())
        self.M = list(self.M)

        self.O_m = {m: [] for m in self.M}
        for i in self.O:
            for m in self.M_i[i]:
                self.O_m[m].append(i)

    def print(self) -> None:
        print("printing built instance:\n")
        print(f"num_jobs: {self.num_jobs} | num_machines: {self.num_machines}")
        for i, job in enumerate(self.jobs):
            print(f"job {i}")
            for j, operation in enumerate(job):
                print(f"   operação {j}")
                for machines in operation:
                    print(f"      máquina: {machines[0]} | p_im: {machines[1]}")
                print("\n")
            print("\n")

        print(f"O : conjunto global de operações:\n{self.O}\n")
        print(f"M : conjunto de máquinas:\n{self.M}\n")

        print("M_i: conjunto de máquinas elegíveis para a operação i:")
        for oper, maqs in self.M_i.items():
            print(f"M_{oper}: {maqs}")

        print(f"J : conjunto de jobs:\n{set(range(self.num_jobs))}\n")

        print("O_j: conjunto de operações do job j:")
        for job, opers_job in enumerate(self.O_j):
            print(f"O_{job}: {opers_job}\n")

        print("P_j: sequência tecnológica do job j:")
        print(self.P_j)

        print("O_m : operações que podem ser processadas na máquina m:")
        for maq, opers in self.O_m.items():
            print(f"O_{maq}: {opers}\n")

        print("p_{i,m} : tempo de processamento da operação i na máquina m:")
        for (oper, maq), process in self.p.items():
            print(
                f"p_{{oper},{maq}}: {process}\n"
            )

        for oper, job in self.job_of_op.items():
            print(f"a operação {oper} faz parte do job {job}\n")
