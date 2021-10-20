# -*- coding: utf-8 -*-

"""
cstrace.json 의 기본형식에서 parent - child 구조를 없애고, 컴파일 플래그의 경로들을 절대 경로로 만드는 등의
후처리 작업을 처리한다.
"""

import sys
import json
import argparse
import re
import os
import glob
from collections import OrderedDict
import cslib


def get_open_list_for_child(opened_from_child_list: list):
    opened = []
    for opened_file in opened_from_child_list:
        filename, ext = os.path.splitext(os.path.basename(opened_file))
        if ext not in ['.so', '.s', '.o', '.cache', '.alias', '.res']:
            if '.so.' not in filename:
                opened.append(opened_file)
    return opened


def collect_open_from(pid,
                      cstrace_json,
                      linked_pid_to_child_map: dict,
                      parent_process_info_tuple: tuple = None):
    def is_skipped_case(process_id, cstrace_json_dict):
        if process_id not in cstrace_json_dict:
            return True
        execve_trace = cstrace_json_dict[process_id]['execve']
        if execve_trace is not None:
            if len(execve_trace) == 0:
                return True
            binaryname = os.path.splitext(os.path.basename(execve_trace[0]))[0]
            if binaryname in ['as', 'collect2', 'ld']:
                return True
        return False

    def get_parent_process_info_tuple(parent_process_tuple):
        if parent_process_tuple is None:
            return '', []
        return parent_process_tuple

    def has_parent_info(parent_process_tuple):
        if parent_process_tuple is None:
            return False
        return True

    def is_fork_child_process(parent_process_tuple, cstrace_dict):
        if has_parent_info(parent_process_tuple):
            command, flag_list = get_parent_process_info_tuple(parent_process_tuple)
            if chpid not in cstrace_dict.keys():
                return False
            if 'execve' in cstrace_dict[chpid] and cstrace_dict[chpid]['execve'] is None:
                return False
            if len(cstrace_dict[chpid]['execve']) != 3:
                return False
            if command == cstrace_dict[chpid]['execve'][0] and flag_list == cstrace_dict[chpid]['execve'][1]:
                return True
        return False

    if is_skipped_case(pid, cstrace_json):
        return [], []

    opened = get_open_list_for_child(cstrace_json[pid]['open'])
    child_process_list_to_forked = []

    for chpid in linked_pid_to_child_map.get(pid, []):
        if is_fork_child_process(parent_process_info_tuple, cstrace_json):
            child_process_list_to_forked.append(chpid)
        includes, _ = collect_open_from(chpid, cstrace_json, linked_pid_to_child_map)
        opened.extend(includes)

    return opened, list(set(child_process_list_to_forked))


def is_forked_process(pid: str,
                      fork_cid_list: list) -> bool:
    if pid in fork_cid_list:
        del fork_cid_list[fork_cid_list.index(pid)]
        return True
    return False


def postprocessing_cstrace(final, linked_pid_to_child_map):
    # 주요 컴파일러 호출 정보만 남기고 나머지는 제거한다.
    # 주요 컴파일러는 가장 밖에서 호출되는 드라이버이며, 내부적으로 호출되는 as 나 cc1plus 등의 정보는
    # open 만 취한다.
    normalize_cstrace = OrderedDict()
    forked_child_id_list = []
    for pid in final:
        # STCS-945, LDH, child process 인데 fork 계열 함수로 생성된 경우 skip
        if is_forked_process(pid, forked_child_id_list):
            continue
        # if pid in forked_child_id_list:
        #     del forked_child_id_list[forked_child_id_list.index(pid)]
        #     continue
        if final[pid]['execve'] is not None:
            # LDH, final[pid]['execve'] 리스트가 비어있을 경우
            if not final[pid]['execve']:
                continue
            invoked_command = final[pid]['execve'][0]
            execve_info = final[pid]['execve'][1]
            build_location = final[pid]['execve'][2]

            if cslib.is_interest_call(invoked_command):
                if pid not in normalize_cstrace:
                    normalize_cstrace[pid] = {}

                # 컴파일러 호출일때는 현재 flag 와 (현재 open 파일 + 자식 open 파일) 리스트를 취한다.
                normalize_cstrace[pid]['execve'] = final[pid]['execve']
                includes, child_id_list_for_forked = collect_open_from(pid, final, linked_pid_to_child_map, (invoked_command, execve_info))
                normalize_cstrace[pid]['open'] = sorted(list(set(includes)))
                # STCS-945, LDH, fork 된 자식 process 는 순회대상에서 제외하도록 순회 제외 대상 리스트에 추가
                if pid in linked_pid_to_child_map.keys():
                    forked_child_id_list.extend(child_id_list_for_forked)
                    forked_child_id_list = list(set(forked_child_id_list))

    # command line 에 포함된 모든 경로를 절대 경로로 바꾼다.
    for pid in normalize_cstrace:
        if normalize_cstrace[pid]['execve'] is not None:
            # 이미 절대 경로 - invoked_command = final[pid]['execve'][0]
            commands = normalize_cstrace[pid]['execve'][1]
            build_location = normalize_cstrace[pid]['execve'][2]
            normalize_cstrace[pid]['execve'][1] = cslib.wildcard_normalize(build_location, cslib.filepath_normalized_option(build_location, commands))

    if len(normalize_cstrace) != 0:
        # LDH, 소스 정보와 목적 파일 정보가 다른 프로세스에 있다면 합쳐주기
        toolset = cslib.set_toolset(normalize_cstrace)
        normalize_cstrace = toolset.align_source_object_relation(normalize_cstrace, linked_pid_to_child_map)

        # LDH, 소스 파일 경로나 목적 파일 경로가 하나의 파일에 모두 정의되어 있다면 command 에 풀어주기
        # LDH, Cosmic 컴파일러의 경우, 링킹 시 object file path 정보를 가지는 *.lkf 파일을 풀어버린다.
        normalize_cstrace = toolset.add_option_from_file(normalize_cstrace)

        # LDH, 미리 컴파일된 헤더 생성 및 사용 옵션이 존재하면 미리 컴파일된 헤더의 절대경로를 open 항목에 추가, -I 옵션 추가해야함
        # normalize_cstrace = toolset.add_precompiled_header_path_in_cstrace(normalize_cstrace)
        # STCS-254, LDH, 미리 컴파일된 헤더 생성 옵션과 사용 옵션이 모두 존재하는 경우, 생성 옵션이 있는 TU의 open 리스트를 사용 옵션이 있는 TU의 open 리스트에 추가
        normalize_cstrace = toolset.add_precompiled_header_open_list_in_cstrace(normalize_cstrace)

    return normalize_cstrace
