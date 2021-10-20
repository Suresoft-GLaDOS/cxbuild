#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
author : hgsong
This program import wtrace information then convert to json.

Because it is the property of Suresoft Technologies Incs, it is not allowed to modify or distribute without permission.
"""

import sys
import json
import argparse
import re
import os
import glob
import shlex
import libcsbuild
from collections import OrderedDict

import cslib
from . import post_processing_cstrace

contents_delimiter = '-+-'
option_i_list = ['-I', '-i', '/I']


def option_parser():
    parser = argparse.ArgumentParser(description="wtrce to json converter")
    parser.add_argument("-i", dest='wtrace_file', default=None, required=True)
    parser.add_argument("-o", dest='out_file_path', default=None, required=True)
    return parser


def _split_command(command):
    return shlex.split(command)


def is_include_command(command):
    for option_i in option_i_list:
        if command.startswith(option_i) and len(command) != len(option_i) and command[2] == '"':
            return True
    return False


def split_include_command(command):
    return_list = []
    for option_i in option_i_list:
        if command.startswith(option_i) and len(command) != len(option_i) and command[2] == '"':
            include_option = option_i
            return_list.append(include_option)
            include_path = command[2:]
            return_list.append(include_path)
            break
    return return_list


def normalize_include_path(option_list):
    option_i_flag = False
    for inx, option in enumerate(option_list):
        if option_i_flag:
            option_list[inx] = os.path.normpath(option)
            option_i_flag = False
            continue
        for option_i in option_i_list:
            if option == option_i:
                option_i_flag = True
                break
    return option_list


def split_command(command):
    def strip_quotes(s):
        if s and (s[0] == '"' or s[0] == "'") and s[0] == s[-1]:
            return s[1:-1]
        return s

    option_list = []
    start_inx_for_path_with_blank = -1
    # LDH, -I"C:/dfd fdf/dd.c" 와 같이 경로에 공백과 -I를 붙여서 쓰는 경우 분리하고 공백을 인정하도록 re 수정
    # for p in re.findall(r'"(?:\\.|[^"])*"|\'(?:\\.|[^\'])*\'|[^\s]+', command):
    for p in re.findall(r'"(?:\\.|[^"])*"|-[a-zA-Z0-9]+"(?:\\.|[^"])*"|\'(?:\\.|[^\'])*\'|[^\s]+', command):
        p = strip_quotes(p).replace('\\"', '"').replace("\\'", "'")
        # LDH, 정규표현식으로 split 했으나 경로인 경우 제대로 split 되지 않는 경우가 있음
        # if p.startswith("\\"):
        #     if not option_list:
        #         previous_string = ''
        #     else:
        #         previous_string = option_list[-1]
        #         option_list.remove(previous_string)
        #     p = previous_string + p
        # STCS-411, LDH, PATH에 공백이 존재하는 경우, split이 잘 되지 않는 이슈 수정
        # ex. /OUT:"D:\src\ex\csbuild\b l a n k\blankProject\x64\Debug\blankProject.exe"
        if p.count('"') == 1:
            if start_inx_for_path_with_blank == -1:
                start_inx_for_path_with_blank = len(option_list)
            else:
                made_path_with_blank = ''
                end_inx = len(option_list)
                for inx in range(start_inx_for_path_with_blank, end_inx):
                    element = option_list.pop()
                    made_path_with_blank = element + ' ' + made_path_with_blank
                p = made_path_with_blank + p
                start_inx_for_path_with_blank = -1

        # LDH, -I"C:/dfd fdf/dd.c" 와 같이 공백과 -I를 붙여서 쓰는 경우 분리
        if is_include_command(p):
            include_list = split_include_command(p)
            include_list[1] = strip_quotes(include_list[1])
            option_list += include_list
        else:
            option_list.append(p)

    # LDH, 경로 정규화
    option_list = normalize_include_path(option_list)
    return option_list


def make_exec_contents(json_dict, process_id, path, command, buildloc):
    if process_id in json_dict:
        if 'execve' in json_dict[process_id]:
            json_dict[process_id]['execve'] += [path, split_command(command), buildloc]
        else:            
            json_dict[process_id]['execve'] = {}
            json_dict[process_id]['execve'] = [path, split_command(command), buildloc]
    else:
        json_dict[process_id] = {}
        json_dict[process_id]['execve'] = {}
        json_dict[process_id]['execve'] = [path, split_command(command), buildloc]
    return json_dict


def make_open_contents(json_dict, process_id, file):
    if process_id in json_dict:  
        if 'open' in json_dict[process_id]:
            json_dict[process_id]['open'].append(file)
        else:
            json_dict[process_id]['open'] = {}               
            json_dict[process_id]['open'] = [file]     
    else:
        json_dict[process_id] = {}
        json_dict[process_id]['open'] = {}               
        json_dict[process_id]['open'] = [file]  
    return json_dict    


def get_option_files_by_extension(process_path):
    return "rsp"


def extract_string(full_string, find_string, start_flag=True):
    inx = full_string.find(find_string)
    if inx != -1:
        if start_flag:
            return True, full_string[inx+len(find_string):]
        else:
            return True, full_string[:inx]
    return False, ''


def convert_env_in_string_list(str_list):
    def has_env_preset_in_string(full_string, preset_list):
        for preset in preset_list:
            if full_string.find(preset[0]) != -1:
                return True
        return False

    def replace_environment_in_string(full_string, preset_list):
        # $ 로 시작하는 문자열이 있으면 대체해주는 API 있는지 확인해보기
        res, contents = extract_string(full_string, preset_list[0])
        if not res:
            return res, ''
        res, contents = extract_string(contents, preset_list[1], start_flag=False)
        if not res:
            return res, ''
        env_string = env_preset[0] + contents + env_preset[1]
        if contents in os.environ.keys():
            # FIXME: env_string 꺼낼 수 있는 API 있는지 찾아보기
            replace_string = full_string.replace(env_string, os.environ[contents])
            return True, replace_string
        else:
            return False, ''

    env_preset_list = [['$(', ')'], ['${', '}']]
    for inx in range(len(str_list)):
        element = str_list[inx]
        # expandvars 를 통해 환경 변수 치환 가능한 경우 처리
        element = os.path.expandvars(element)
        if not has_env_preset_in_string(element, env_preset_list):
            str_list[inx] = element
            continue
        # expandvars 로 해결되지 않는 경우, 직접 찾아서 치환
        for env_preset in env_preset_list:
            while element.find(env_preset[0]) != -1:
                result, converted_string = replace_environment_in_string(element, env_preset)
                if not result:
                    break
                element = converted_string
                str_list[inx] = element
    return str_list


# STCS-306, 옵션 파일에 대한 정보가 인자에 없고 open 리스트에만 존재하는 경우 옵션 파일 열어서 내용 가져오기
def get_option_list_in_option_file(option_file_path):
    if not os.path.isfile(option_file_path):
        return []

    with open(option_file_path, 'r') as option_file:
        option_file_contents = option_file.read()
    # STCS-569, 치환해야 하는 문자열이 생겼을 경우, 치환하여 반환하도록 수정
    return convert_env_in_string_list(option_file_contents.split('\n'))


def convert_wtrace_data_to_json_dict(lines,
                                     drive_mapped_dict):
    option_file_extension = None
    pid_to_child_map = {}
    json_dict = OrderedDict()
    for line in lines:
        splited = line.split("-+-")
        if len(splited) <= 3:
            continue
        process_id = splited[1].strip()
        parent_id = splited[2].strip()
        kind = splited[0].strip()

        # create placeholder
        if process_id not in json_dict:
            json_dict[process_id] = {'execve': [], 'open': [], 'sigchld': []}

        # collect ppid to pid relation
        if parent_id not in pid_to_child_map:
            pid_to_child_map[parent_id] = set()
        pid_to_child_map[parent_id].add(process_id)

        # process line entry
        if kind == "exec":
            buildloc = splited[3].strip()
            path = os.path.abspath(splited[4].strip())
            command = splited[5].strip()
            json_dict = make_exec_contents(json_dict, process_id, path, command, buildloc)
        elif kind == "open":
            if drive_mapped_dict is not None:
                file = cslib.convert_network_drive_path(splited[3].strip(), drive_mapped_dict)
            else:
                file = os.path.abspath(splited[3].strip())
            # STCS-306, 옵션 파일에 대한 정보가 인자에 없고 open 리스트에만 존재하는 경우 옵션 파일 열어서 내용 가져와서 붙여넣기
            if option_file_extension is None and 'execve' in json_dict[process_id] and len(
                    json_dict[process_id]['execve']) > 0:
                process_path = json_dict[process_id]['execve'][0]
                option_file_extension = get_option_files_by_extension(process_path)
            if option_file_extension is not None and file.endswith('.' + option_file_extension):
                option_list = get_option_list_in_option_file(file)
                new_option_list = []
                for option in option_list:
                    option_split_list = split_command(option)
                    new_option_list.extend(option_split_list)
                if type(new_option_list) is list and len(new_option_list) != 0:
                    json_dict[process_id]['execve'][1].extend(new_option_list)
                continue
            json_dict = make_open_contents(json_dict, process_id, file)
        else:
            pass
    return json_dict, pid_to_child_map


def get_wtrace_data(wtrace_file_path, drive_mapped_dict=None):
    err_flag = False
    encode_value = 'utf-8'
    while True:
        try:
            with open(wtrace_file_path, "r", encoding=encode_value) as f:
                json_dict, pid_to_child_map = convert_wtrace_data_to_json_dict(f.readlines(),
                                                                               drive_mapped_dict)
            break
        except UnicodeDecodeError:
            if err_flag:
                raise Exception(f'error: cannot decode text enc(utf-8, cp949)')
            else:
                err_flag = True

    return json_dict, pid_to_child_map


def write_to_file(json_dict, out_file_path):
    with open(out_file_path, 'w', encoding='utf-8') as output_jason:
        json.dump(json_dict, output_jason, indent=4)

    return


def collect_open_from(pid, cstrace_json):
    opened = []
    opened.extend(cstrace_json[pid]['open'])
    for chpid in cstrace_json[pid]['sigchld']:
        opened.extend(collect_open_from(chpid, cstrace_json))

    return opened


def collect_wtrace(working_directory):
    def is_exclude_file_path(filepath: str):
        dir_name = os.path.dirname(filepath)[os.path.dirname(filepath).rfind('\\')+1:]
        find_input = os.path.join(dir_name, os.path.basename(filepath))
        if cslib.fnmatch(find_input, '**/.staticdata/*.log') or cslib.fnmatch(find_input, '**/.staticdata/*.list'):
            return True
        return False

    drive_mapped_dict = cslib.get_drive_mapped_path_dict()
    # LDH, glob escape 추가
    traces = glob.glob(glob.escape(working_directory) + "/wtrace.*.*")
    final = OrderedDict()
    linked_pid_to_child_map = OrderedDict()
    # 생성 시간 순으로 정렬
    traces.sort(key=lambda x: os.path.getmtime(x))
    for trace in traces:
        # FIXED : wtrace.*.log 또는 wtrace.exclude.file.list 에 해당하는 경우에 대한 예외 추가
        # *.log , *.list ( fnmatch 함수 사용)
        if is_exclude_file_path(trace):
            continue

        json_dict, pid_to_child_map = get_wtrace_data(trace, drive_mapped_dict)
        for key in json_dict.keys():
            final[key] = json_dict[key]

        for key in pid_to_child_map:
            if key not in linked_pid_to_child_map:
                linked_pid_to_child_map[key] = set()
            # fixme - 이미 있던 set 에 set 을 추가하는 방법이 이게 최선?
            linked_pid_to_child_map[key].update(pid_to_child_map[key])
            #linked_pid_to_child_map[key] = linked_pid_to_child_map[key].union(pid_to_child_map[key])

    normalize_cstrace = post_processing_cstrace.postprocessing_cstrace(final, linked_pid_to_child_map)
    # LDH, 컴파일 인자에서 '@' 으로 시작된 인자는 파일 내부 데이터를 인자로 사용하기 위함, 해당 파일은 open 대상에서 제거
    normalize_cstrace = cslib.filter_cstrace_open_file(working_directory, normalize_cstrace)
    return normalize_cstrace


def main(args):
    parser = option_parser()
    options = parser.parse_args(args)
    json_dict = get_wtrace_data(options.wtrace_file)
    write_to_file(json_dict, options.out_file_path)

    return True


if __name__ == "__main__":
    main(sys.argv[1:])
