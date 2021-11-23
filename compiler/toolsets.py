import os
# import list of compiler
from .icompiler_tool import *
from ._gnu_compiler_tool import _GnuCompilerTool


def create(compiler_path, command) -> ICompilerTool:
    tool_basename = os.path.basename(compiler_path).lower()
    tool_name, ext = os.path.splitext(tool_basename)

    # TODO: make as a factory function
    return _GnuCompilerTool(compiler_path, command)
