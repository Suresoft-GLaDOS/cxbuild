#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
from collections import OrderedDict
import cslib
import libcsbuild


def is_exist_pid(pid, cstrace_json):
    if pid in cstrace_json:
        return True
    else:
        return False


# LDH, 리눅스에서 코드와 상관없는 파일 필터링
# STATIC-1730, 분석할 소스에 한글이 존재하는 경우, /usr/lib/locale/ 에 존재하는 언어 관련 파일들이 같이 수집
# 해당 파일들을 cstrace.json에서 삭제
def is_regardless_of_file(value):
    returnValue = False
    if type(value) is str:
        if value.startswith('/proc/') or value.startswith('/usr/lib/locale/'):
            returnValue = True
    return returnValue


def create_empty_content_dict():
    content_dict = OrderedDict()
    content_dict['execve'] = None
    # execve is already list
    content_dict['open'] = list()
    content_dict['sigchld'] = list()
    return content_dict


def parse_cstrace_log_file(cstrace_log_path):
    content_catch_pattern = '(?P<pid>([0-9]+))\s+(?P<kind>(execve|openat|open|--- SIGCHLD|\*\*\*|\+\+\+))(?P<remainder>(.*))'
    file_path_pattern = '^\(.*=.*<(?P<file_path>(.*))>'

    pid_dict = {}
    cstrace_json = OrderedDict()
    with open(cstrace_log_path, 'r', encoding='utf-8') as cstrace_log:
        for line in cstrace_log:
            r = re.match(content_catch_pattern, line)

            if r is None:
                continue

            pid = r.group("pid")
            if pid not in pid_dict:
                pid_dict[pid] = pid

            kind = r.group("kind")
            remainder = r.group('remainder')

            if "open" in kind:
                q = re.match(file_path_pattern, remainder)
                key = "open"
                if q is not None:
                    value = cslib.decode_octal_encoding(q.group("file_path"))

            elif "execve" in kind:
                execve_catch_pattern = '^\(\"(.*)\", \[(.*)\], \$\"(.*)\"\$'
                execve_result = re.search(execve_catch_pattern, remainder)
                process_name = execve_result.group(1)
                # STCS-165, LDH, \" 의 경우 \만 남는 문제 발생
                command_info = []
                for arg in execve_result.group(2).split(','):
                    arg = cslib.decode_octal_encoding(arg.strip()).replace('"', '')
                    if arg.find('=\\') != -1 and arg.endswith('\\'):
                        arg = arg.replace('\\', r'"')
                    command_info.append(arg)
                # command_info = [cslib.decode_octal_encoding(arg.strip()).replace('"', '') for arg in execve_result.group(2).split(',')]
                build_location = execve_result.group(3)
                # LDH, build_location이 정상적으로 추출되지 않는 경우 발생, regular expression 수정보단 후처리로 진행
                if not os.path.isdir(build_location.replace('"', '')):
                    find_inx = build_location.find('\"$')
                    if find_inx != -1:
                        build_location = build_location[:find_inx]
                command_info = cslib.filepath_normalized_option(build_location, command_info)
                execve_result_list = [process_name, command_info, build_location]
                key = "execve"
                value = execve_result_list

            elif "---" in kind:
                sigchld_catch_pattern = " {si_signo=SIGCHLD, si_code=(.*), si_pid=(.*), si_uid="
                matched_value = re.match(sigchld_catch_pattern, remainder).group(2)
                if matched_value not in pid_dict:
                    # logging? sig child 가 있는데, event 가 하나도 안나온 경우?
                    continue

                temp_pid = pid_dict[matched_value]
                temp_pid_list = temp_pid.split('_')

                sigchld_pid = temp_pid

                if len(temp_pid_list) > 1:
                    if temp_pid_list[1] == "1":
                        sigchld_pid = temp_pid_list[0]
                    else:
                        sigchld_pid = temp_pid_list[0] + '_' + str(int(temp_pid_list[1]) - 1)
                else:
                    pass

                key = "sigchld"
                value = sigchld_pid

            # LDH, fork 계열 strace 추출로 부모 자식 프로세스 계층 관계 확인
            elif "***" in kind:
                fork_catch_pattern = "pid-chid\((.*)\)"
                chid = re.match(fork_catch_pattern, remainder).group(1)
                key = "sigchld"
                value = chid

            elif "+++" in kind:
                old_pid = pid_dict[pid]
                splited_pid = old_pid.split("_")
                if len(splited_pid) > 1:
                    new_pid = splited_pid[0] + "_" + str(int(splited_pid[1]) + 1)
                else:
                    new_pid = old_pid + "_1"
                pid_dict[pid] = new_pid
                continue

            else:
                raise Exception('undefined kind in get_content_info')

            if value and not is_regardless_of_file(value):
                real_pid = pid_dict[pid]
                if not is_exist_pid(real_pid, cstrace_json):
                    cstrace_json[real_pid] = create_empty_content_dict()

                if key == "execve":
                    cstrace_json[real_pid][key] = value
                else:
                    cstrace_json[real_pid][key].append(value)
                    cstrace_json[real_pid][key] = list(set(cstrace_json[real_pid][key]))

    return cstrace_json


def create_cstrace_json(cstrace_json_path, cstrace_log_path):
    json_data = parse_cstrace_log_file(cstrace_log_path)
    working_directory = libcsbuild.get_working_dir()
    # LDH, 컴파일 인자에서 '@' 으로 시작된 인자는 파일 내부 데이터를 인자로 사용하기 위함, 해당 파일은 open 대상에서 제거
    json_data = cslib.filter_cstrace_open_file(working_directory, json_data)

    with open(os.path.abspath(cstrace_json_path), 'w', encoding='utf-8') as init_file:
        json.dump(json_data, init_file, indent=4, ensure_ascii=False)
    return json_data
