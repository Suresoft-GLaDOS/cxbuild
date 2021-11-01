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
        """find system includes from 'gcc -c -v __test_dummy_source__.c'"""
        dummy_src_path = libcsbuild.get_new_file_path("__test_dummy_source__.c")
        redirect_path = libcsbuild.get_new_file_path("__redirect__.stdout")
        with open(dummy_src_path, "w") as f:
            f.flush()
            pass

        with open(redirect_path, "w") as f:
            f.flush()
            subprocess.call([self.compiler_path, '-v', '-c', dummy_src_path], stdout=f, stderr=f)

        collect = False
        collected = []
        with open(redirect_path, "r") as f:

            for line in f.readlines():
                if line.strip().startswith("#include <...>"):
                    collect = True
                elif line.strip().startswith("End of"):
                    collect = False

                if collect:
                    collected.append(line.strip())
        # remove 0 index cuz, collected[0] == "#include <...>"
        return collected[1:]
