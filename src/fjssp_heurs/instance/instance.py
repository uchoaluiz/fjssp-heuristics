from pathlib import Path


class Instance:
    def __init__(self, input: Path) -> None:
        self.input_path = input
        self.read_file()

    def read_file(self) -> None:
        with open(self.input_path, "r") as file:
            lines = file.readlines()
            print(lines)
            lines = [line for line in lines if line.strip()]
            print(lines)
