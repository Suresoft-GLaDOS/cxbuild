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
        compiler = os.path.basename(self.compiler_path)
        if any(compiler.startswith(c) for c in ["g++", "c++", "clang++"]):
            command = f"{self.compiler_path} -E -Wp,-v -xc++ /dev/null"
        elif any(compiler.startswith(c) for c in ["gcc", "clang"]):
            command = f"{self.compiler_path} -E -Wp,-v -xc /dev/null"
        else:
            raise Exception(f"No Such Compiler Exception.\nCompiler kind is : {compiler}")
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

    def get_predefined_macro(self):
        compiler = os.path.basename(self.compiler_path)
        if any(compiler.startswith(c) for c in ["g++", "c++", "clang++"]):
            command = f"{self.compiler_path} -dM -E -xc++ - < /dev/null"
        elif any(compiler.startswith(c) for c in ["gcc", "clang"]):
            command = f"{self.compiler_path} -dM -E - < /dev/null"
        else:
            raise Exception(f"No Such Compiler Exception.\nCompiler kind is : {compiler}")
        return subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True).decode("utf-8")
