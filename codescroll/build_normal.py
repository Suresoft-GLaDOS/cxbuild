#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess

import codescroll.strace
import codescroll.wtrace
import cslib
import json
from codescroll.runner import *


# Commercial only
class WindowsBuild(Runner):
    def start(self, _, previous_result=None):
        libcsbuild.step_message("Build")

        def get_executable():
            if libcsbuild.is_64bit_os():
                return 'wtrace_64.exe'
            else:
                return 'wtrace_32.exe'

        commands = [get_executable()]
        commands.append("/o")
        commands.append(libcsbuild.get_working_dir())
        commands.append('--')
        commands.extend(libcsbuild.get_command())

        is_succeed = subprocess.call(commands) == 0

        return is_succeed, previous_result


class LinuxBuild(Runner):

    with_open_template = 'cstrace -s 65535 -e trace=open,openat,execve -v -y -f -o "$(working_dir)/full_cstrace.log" -- $(args_string)'
    without_open_template = 'cstrace -s 65535 -e trace=execve -v -y -f -o "$(working_dir)/full_cstrace.log" -- $(args_string)'
    with_open_template_front = 'cstrace -s 65535 -e trace='
    with_open_template_back = ' -v -y -f -o "$(working_dir)/full_cstrace.log" -- $(args_string)'
    # without_open_template_back = ' -v -y -f -o "$(working_dir)/full_cstrace.log" -- $(args_string)'

    def __init__(self, with_open=True):
        super().__init__()
        self.template = self.with_open_template

    def start(self, _, previous_result=None):
        def clean_working_dir():
            if os.path.exists(libcsbuild.get_working_dir()):
                cslib.csbuild_rmtree(libcsbuild.get_working_dir())

        def run_cstrace(command):
            cstrace_command = self.template
            command = ' '.join(['"' + cmd + '"' if ' ' in cmd else cmd for cmd in command])
            cstrace_command = cstrace_command.replace('$(working_dir)', libcsbuild.get_working_dir())
            cstrace_command = cstrace_command.replace('$(args_string)', command)
            print(command)

            print(cstrace_command)
            return_value = subprocess.call(cstrace_command, shell=True)

            return return_value

        libcsbuild.step_message("Build")
        clean_working_dir()

        # STCS-50 pyinstaller 가 LD_LIBRARY_PATH 를 선점하여 사용해서 원래 빌드 의미가 달라지는 문제
        library_path = ''
        if not cslib.is_windows():
            if 'LD_LIBRARY_PATH' in os.environ:
                library_path = os.environ['LD_LIBRARY_PATH']
                del os.environ['LD_LIBRARY_PATH']

        okay = run_cstrace(libcsbuild.get_command()) == 0

        if not cslib.is_windows():
            os.environ['LD_LIBRARY_PATH'] = library_path

        return okay, previous_result


class LinuxStracePreprocess(Runner):
    def start(self, _, previous_result=None):
        libcsbuild.step_message("Analyzing build Activities")
        full_cstrace_log_file_path = os.path.join(libcsbuild.get_working_dir(), "full_cstrace.log")
        cstrace_json_path = os.path.join(libcsbuild.get_working_dir(), "xtrace_tree.json")

        if os.path.exists(full_cstrace_log_file_path):
            cstrace_log_path = codescroll.strace.filter_cstrace_log()
            codescroll.strace.create_cstrace_json(cstrace_json_path, cstrace_log_path)
            return True, cstrace_json_path
        else:
            raise Exception("Can't not find cstrace result" )


class WindowsTraceProcessor(Runner):
    def start(self, _, previous_result=None):
        libcsbuild.step_message("Analyzing build Activities")

        jsons = codescroll.wtrace.trace_to_json.collect_wtrace(libcsbuild.get_working_dir())

        fulltrace_filepath = os.path.join(libcsbuild.get_working_dir(), "xtrace_tree.json")
        with open(fulltrace_filepath, 'w', encoding='utf-8') as fulltrace:
            json.dump(jsons, fulltrace, indent=2, ensure_ascii=False)

        return True, fulltrace_filepath


# ----------------------------------- Runner Configurations
def run():
    # make directory, and made side-effects here
    working_directory = os.path.abspath(libcsbuild.get_working_dir())
    cslib.make_dir(working_directory)
    if not os.access(working_directory, os.W_OK | os.R_OK):
        libcsbuild.error_message("%s directory is not right permission to do your request" % working_directory)
        return False, None

    builder = LinuxBuild() #if not cslib.is_windows() else WindowsBuild()
    tracer = LinuxStracePreprocess() #if not cslib.is_windows() else WindowsTraceProcessor()

    builder.next(tracer)
    return builder.run(None)
