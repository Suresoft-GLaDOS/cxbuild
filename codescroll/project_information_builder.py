import json
import libcsbuild
import cslib
from codescroll.toolsets import get_toolset
from codescroll.runner import *


class ProjectInformationBuilder(Runner):
    """option*cstrace_json_filepath-->Project"""
    def start(self, options, cstrace_json_filepath=None):
        if not os.path.exists(cstrace_json_filepath):
            return False, None

        project_json_path = os.path.join(libcsbuild.get_working_dir(), "project.json")
        with open(cstrace_json_filepath, "r") as tracefile:
            traces = json.load(tracefile)

            if os.path.exists(project_json_path):
                os.remove(project_json_path)

            project_json = self.__create_project_json(traces)

            with open(project_json_path, 'w', encoding='utf-8') as project_json_file:
                json.dump(project_json, project_json_file, indent=4)

        return True, project_json_path

    def get_open_files(self, pid, traces):
        collects = []
        collects.extend(traces[pid]['open'])
        for child_pid in traces[pid]['sigchld']:
            collects.extend(self.get_open_files(child_pid, traces))

        return collects

    def __create_project_json(self, traces):
        working_dir = libcsbuild.get_working_dir()
        module_info_dict_for_dependencies = []
        static_link_list = []
        #self.__toolset = cslib.set_toolset(traces)

        return self.__parse_cstrace_json(module_info_dict_for_dependencies, static_link_list, traces)

    def __normalize_command_list(self, commands):
        # commands 는 모두 절대경로로 변경된 상태로 들어온다
        # absolute_command_list 에 따옴표가 들어 있는 것들을 노멀라이즈한 후 검토
        # STCS-165, 매크로 인자에도 " 가 존재할 수 있으므로 첫번째와 마지막에 같은 기호가 존재하는지 확인
        normalize_commands = []
        for cmd in commands:
            if len(cmd) > 1 and (cmd[0] == '"' or cmd[0] == "'") and cmd[0] == cmd[-1]:
                cmd = cmd.replace(cmd[0], '')
            normalize_commands.append(cmd)
        return normalize_commands

    def __parse_cstrace_json(self, module_info_dict_for_dependencies, static_link_list, traces):
        ret = []
        for pid in traces:
            if traces[pid]['execve'] is None:
                continue

            invoked_command = traces[pid]['execve'][0]
            build_location = traces[pid]['execve'][2]
            commands = self.__normalize_command_list(traces[pid]['execve'][1])

            if not cslib.is_interest_call(invoked_command):
                continue

            toolset = get_toolset(invoked_command)
            toolset.set_build_location(build_location)

            open_files = list(set(self.get_open_files(pid, traces)))
            open_files.sort()
            options, compiling_source_files = toolset.split_command(commands, traces, pid)
            for sourcefile in compiling_source_files:
                source = {}
                source['open'] = open_files
                source['build_location'] = build_location
                source['file'] = sourcefile
                source['command'] = options
                source['compiler'] = invoked_command
                ret.append(source)

        return ret
