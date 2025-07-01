class LOGGER:
    def __init__(self, indent_str="    "):
        self.level = 0
        self.indent_str = indent_str
        self.on = 1

    def log(self, message):
        if self.on == 1:
            print(f"{self.indent_str * self.level}> {message}")

    def breakline(self, n: int = 1):
        print("\n" * (n - 1))

    def switch_on_off(self):
        self.on *= -1

    def __enter__(self):
        self.level += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.level -= 1
