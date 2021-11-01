import libcsbuild
import os

"""
기본적인 Composite Pattern 구현임
"""

class RunnerMeta(type):
    pass


class Runner(metaclass=RunnerMeta):
    """작업들의 Composite 을 담당하는 Base Class"""
    def __init__(self):
        self.next_runner = None
        pass

    def next(self, other_runner):
        self.next_runner = other_runner
        return self.next_runner

    def start(self, object, previous_result=None):
        return (True, None)

    def run(self, object, previous_result=None):
        succeed, value = self.start(object, previous_result)
        if succeed is True:
            if self.next_runner is not None:
                os.chdir(libcsbuild.csbuild_build_root())
                return self.next_runner.run(object, value)
        return succeed, value


class EmptyRunner(Runner):
    def start(self, object, previous_result=None):
        pass
