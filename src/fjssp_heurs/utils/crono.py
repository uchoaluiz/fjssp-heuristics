from time import perf_counter as pc


class Crono:
    def __init__(self):
        self.start_time = pc()
        self.elapsed = 0

    def stop(self):
        self.elapsed = pc() - self.start_time
        return self.elapsed

    def reset(self):
        self.start = pc()

    def elapsed_time(self):
        return pc() - self.start_time
