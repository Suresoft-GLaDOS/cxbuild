# -*- coding: utf-8 -*-

import cslib

from codescroll._capture_common import _LinuxBuild, _LinuxStracePreprocess
from codescroll._clang_compilation_database import _ClangCompilationDatabaseExport
from codescroll._project_information_builder import _ProjectInformationBuilder
from codescroll.runner import *


# ----------------------------------- Runner Configurations
def run():
    # make directory, and made side-effects here
    working_directory = os.path.abspath(libcsbuild.get_working_dir())
    cslib.make_dir(working_directory)
    if not os.access(working_directory, os.W_OK | os.R_OK):
        libcsbuild.error_message("%s directory is not right permission to do your request" % working_directory)
        return False, None

    build_with_ctrace = _LinuxBuild() #if not cslib.is_windows() else WindowsBuild()
    build_trace_processor = _LinuxStracePreprocess()
    project_json_builder = _ProjectInformationBuilder()
    compile_commands_json_export = _ClangCompilationDatabaseExport()
    build_with_ctrace.next(build_trace_processor).next(project_json_builder).next(compile_commands_json_export)
    return build_with_ctrace.run(None)


def run_post():
    working_directory = os.path.abspath(libcsbuild.get_working_dir())
    if not os.access(working_directory, os.W_OK | os.R_OK):
        libcsbuild.error_message("%s directory is not right permission to do your request" % working_directory)
        return False, None

    build_trace_processor = _LinuxStracePreprocess()
    project_json_builder = _ProjectInformationBuilder()
    compile_commands_json_export = _ClangCompilationDatabaseExport()
    build_trace_processor.next(project_json_builder).next(compile_commands_json_export)
    return build_trace_processor.run(None)
