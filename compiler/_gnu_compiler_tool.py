import os
import re
import cslib
import subprocess
import libcsbuild

from .icompiler_tool import *


class _GnuCompilerTool(ICompilerTool):
    def __init__(self, compiler_path: str, command: list):
        self.toolchain_name = "GnuCompilerTool"
        self.command = command
        self.compiler_path = compiler_path

    def get_include_option_name(self):
        return "-I"

    def split_command(self):
        sources = [command for command in self.command if cslib.is_source_file(command)]
        options = [command for command in self.command if command not in sources]
        return options, sources

    def get_system_include_list(self):
        compiler_kind = os.path.basename(self.compiler_path)
        if compiler_kind == "gcc":
            command = "gcc -E -Wp,-v -xc /dev/null"
        elif compiler_kind == "g++" or compiler_kind == "c++":
            command = "g++ -E -Wp,-v -xc++ /dev/null"
        else:
            # TODO: Make no such compiler exception, and Exit gracefully
            raise Exception("No Such Compiler Exception")
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True).decode("utf-8")
        collect = False
        collected = []
        for line in output.splitlines():
            if line.strip().startswith("#include <...>"):
                collect = True
            elif line.strip().startswith("End of"):
                collect = False
            if collect:
                collected.append(line.strip())
        return collected[1:]
