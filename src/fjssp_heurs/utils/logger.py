from pathlib import Path
import sys
import datetime


class LOGGER:
    def __init__(self, log_path: Path, indent_str="    ", out: str = "both"):
        self._log_path = log_path
        self.level = 0
        self.indent_str = indent_str
        self._log_file = None
        self._out = out if out in ["terminal", "file", "both"] else None
        self.on = 1 if out in ["terminal", "both"] else -1

        try:
            self._log_file = open(self._log_path, "w", encoding="utf-8")

            self._log_file.write("\n" * 5)
            self._log_file.write(f"{datetime.datetime.now()}\n")
            self._log_file.write("\n" * 5)
        except IOError as e:
            print(
                f"error opening log file: '{self._log_path}': {e}",
                file=sys.stderr,
            )
            self.on = -1

    def log(self, message):
        msg = f"{self.indent_str * self.level}> {message}"
        if self._out in ["terminal", "both"]:
            if self.on == 1:
                print(msg)
        if self._out in ["file", "both"]:
            if self._log_file:
                try:
                    self._log_file.write(msg + "\n")
                except IOError as e:
                    print(f"error on writing log on file: {e}", file=sys.stderr)
                    self.on = -1

    def breakline(self, n: int = 1):
        if self.on == 1 and self._out in ["both", "terminal"]:
            print("\n" * (n - 1))
        if self._out in ["file", "both"]:
            for _ in range(n):
                self._log_file.write("\n")

    def switch_on_off(self):
        self.on *= -1

    def __enter__(self):
        self.level += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.level -= 1
