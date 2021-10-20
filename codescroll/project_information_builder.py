import json

from codescroll.runner import *


# !!!! 개발중


class Project(object):
    def __init__(self):
        self.modules = []


class Module(object):
    def __init__(self):
        self.moduleTyoe = None
        self.sourceFiles = []


class Source(object):
    def __init__(self):
        self.primarySourceFilePath = None
        self.invokedCompiler = None
        self.invokedCommand = None
        self.includeFiles = []


class ProjectInformationBuilder(Runner):
    """option*cstrace_json_filepath-->Project"""
    def start(self, options, cstrace_json_filepath=None):
        if not os.path.exists(cstrace_json_filepath):
            return {}

        with open(cstrace_json_filepath, "r") as tracefile:
            traces = json.load(tracefile)



