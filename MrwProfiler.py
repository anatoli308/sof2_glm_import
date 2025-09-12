import time
from typing import Dict


class SimpleProfiler:
    def __init__(self, printOutput: bool):
        self.startTimes: Dict[str, float] = {}
        self.printOutput = printOutput

    # starts a clock of the given name
    def start(self, name: str):
        self.startTimes[name] = time.perf_counter()
        if self.printOutput:
            print("Start: {}".format(name))

    # stop the clock of the given name and returns its value, or -1 if no such clock exists.
    def stop(self, name: str) -> int | float:
        if name not in self.startTimes:
            return -1
        timeTaken = time.perf_counter() - self.startTimes[name]
        del self.startTimes[name]
        if self.printOutput:
            print("Done: {} - time taken: {:.3f}s".format(name, timeTaken))
        return timeTaken
