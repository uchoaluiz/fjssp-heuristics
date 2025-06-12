from pathlib import Path


class Instance:
    def __init__(self, input: Path) -> None:
        self.input_path = input
        self.read_file()

    def read_file(self) -> None:
        self.jobs = []
        self.num_jobs = 0
        self.num_machines = 0

        with open(self.input_path, "r") as file:
            first_line = file.readline().strip()
            self.num_jobs, self.num_machines = map(int, first_line.split())

            for _ in range(self.num_jobs):
                line = file.readline().strip()
                tokens = list(map(int, line.split()))
                num_operations = tokens[0]
                operations = []
                idx = 1
                for _ in range(num_operations):
                    num_machines = tokens[idx]
                    idx += 1
                    machine_options = []
                    for _ in range(num_machines):
                        machine = tokens[idx]
                        time = tokens[idx + 1]
                        machine_options.append((machine, time))
                        idx += 2
                    operations.append(machine_options)
                self.jobs.append(operations)
