#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import glob
import hashlib
import json
import os
import re
import shutil
import stat
import time
import binascii
import locale
from copy import deepcopy
from collections import OrderedDict

import cslib

# https://stackoverflow.com/a/1546107
# str.endswith 를 사용하기 위해
#c_extension = ('.c', '.c', '.i')

c_extension = ('.c', '.c')
# STATIC-2087, 전처리된 소스 코드 확장자(.i, .ii) 추가
#cpp_extension = ('.C', ".c++", ".C++", ".cpp", ".CPP", ".cxx", ".CXX", ".cc", ".CC", ".cp", ".CP", ".ii")
cpp_extension = ('.C', ".c++", ".C++", ".cpp", ".CPP", ".cxx", ".CXX", ".cc", ".CC", ".cp", ".CP")
source_extension = bak_source_extension = c_extension + cpp_extension
header_extension = bak_header_extension = (".h", ".H", ".hpp", ".HPP", ".tcc", ".inl", ".INL")
source_and_header_extension = source_extension + header_extension
object_extension = bak_object_extension = (".o", ".O", ".lo", ".obj", ".OBJ")
library_extension = (".a", ".so")
file_extension = source_and_header_extension + object_extension + library_extension
static_library_extension = (".lib", ".a")
extra_extension = ()
# LDH, 사용자 정의 확장자
user_defined_header_extension = ()
user_defined_source_extension = ()
user_defined_object_extension = ()

user_exclusive_pattern_list = []
default_exclusive_pattern_list = ["conftest.c"]
cmake_pattern_list = ["/CMakeTmp/", "feature_tests.c", "testCCompiler.c", "CMakeCXXCompilerABI.cpp", "CMakeCCompilerId",
                      "CMakeCCompilerABI", "CMakeCXXCompilerId.cpp", "testCXXCompiler.cxx"]

is_c_project = True
is_import_spec_mode = False
spec_file_path = ''

start_time = None


def del_rw(action, name, exc):
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)


def new_rmtree(top):
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            filename = os.path.join(root, name)
            os.chmod(filename, stat.S_IWUSR)
            os.remove(filename)
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(top)


def rmtree_force(workspace_path: str):
    flag = False
    for inx in range(3):
        try:
            if os.path.exists(workspace_path):
                shutil.rmtree(workspace_path, onerror=cslib.del_rw)
                time.sleep(1)
            flag = True
            break
        except Exception as e:
            time.sleep(1)
    if not flag:
        raise Exception(
            f'The path("{workspace_path}") cannot delete because other process is already use.')
    os.makedirs(workspace_path, exist_ok=True)


def csbuild_rmtree(path):
    file_list = os.listdir(path)
    for file_name in file_list:
        file_path = os.path.join(path, file_name)
        if os.path.isdir(file_path):
            shutil.rmtree(file_path, onerror=del_rw)
        else:
            os.remove(file_path)


def make_dir(path):
    for i in range(3):
        try:
            if os.path.exists(path):
                csbuild_rmtree(path)
                # shutil.rmtree(path, onerror=del_rw)
            else:
                os.makedirs(path)
            break
        except Exception as e:
            time.sleep(1)


def is_windows():
    if os.name == 'nt':
        return True
    else:
        return False


def display_first_usage():
    print()


# STATIC-2087, 컴파일러가 사용하는 특이한 소스코드 확장자인 경우, 해당 프로젝트의 성격에 맞춘다.
def get_language_type(file_path, language_extension_pair=None):
    def get_language_type_from_extension(ext):
        global is_c_project
        if ext in c_extension:
            is_c_project = True
            return "c"
        elif ext in cpp_extension:
            is_c_project = False
            return "cpp"
        else:
            if ext not in user_defined_source_extension:
                return ""

            if is_c_project:
                return "c"
            else:
                return "cpp"

    global is_c_project
    __, extension = os.path.splitext(file_path)

    # STCS-535, .c 확장자를 CPP 로 기대하는 경우들이 발생함, 이 경우 .STATICFILE 에서 EXTRA_OPTIONS -> LANGUAGE_EXTENSION_PAIR
    # 에 해당 확장자를 알맞게 추가하였으면 여기에서 해당 pair 에 맞게 반환하도록 수정
    if language_extension_pair is not None:
        if 'CPP' in language_extension_pair.keys() and extension in language_extension_pair['CPP']:
            return "cpp"
        elif 'C' in language_extension_pair.keys() and extension in language_extension_pair['C']:
            return "c"
        else:
            return get_language_type_from_extension(extension)
    else:
        return get_language_type_from_extension(extension)


def is_command_list_have_source_file(command_list):
    for command in command_list:
        if is_source_file(command):
            return True
    return False


def get_exclude_list_dict(working_directory):
    exclude_file_list_path = os.path.join(working_directory, "wtrace.exclude.file.list")
    exclude_file_dict = OrderedDict()
    if not os.path.isfile(exclude_file_list_path):
        return exclude_file_dict
    with open(exclude_file_list_path, 'r', encoding='cp949') as exclude_list_file:
        line = exclude_list_file.readline()
        while line:
            line = line.strip()
            splited = line.split("-+-")
            if len(splited) == 2:
                pid = splited[0].strip()
                exclude_file = splited[1].strip()
                exclude_file_dict[pid] = exclude_file
            line = exclude_list_file.readline()
    return exclude_file_dict


# cstrace.json 내 invoke command 를 확인하고 툴체인을 설정함
def set_toolset(cstrace_json):
    import backup.static.compiler_info
    return_value = None
    for pid in cstrace_json:
        if cstrace_json[pid]['execve'] is None:
            continue
        invoked_command = cstrace_json[pid]['execve'][0]
        if not cslib.is_interest_call(invoked_command):
            continue
        return_value = backup.static.get_toolset(invoked_command)
        break
    return return_value


# wtrace 수집 중 '@FILE_PATH'(컴파일/링킹 옵션 정보가 들어있는 파일) 가 존재하는 경우 command line 에서는 풀어서 작성함,
# 그러나 open 대상엔 여전히 포함되어 있으므로 cstrace.json 생성 시 해당 파일은 제외시키는 작업을 수행하여야 함
def filter_cstrace_open_file(working_directory, normalize_cstrace):
    # wtrace에서 'wtrace.exclude.file.list' 파일을 생성함, 이 파일은 @가 인자로 있는 파일 리스트를 기록함
    exclude_file_dict = get_exclude_list_dict(working_directory)
    if len(exclude_file_dict) > 0:
        for pid in normalize_cstrace:
            if normalize_cstrace[pid]['execve'] is None or pid not in exclude_file_dict.keys():
                continue
            build_location = normalize_cstrace[pid]['execve'][2]
            open_list = normalize_cstrace[pid]['open']
            # if pid not in exclude_file_dict.keys():
            #    continue
            exclude_file = os.path.normpath(os.path.join(build_location, exclude_file_dict[pid]))
            # OS 별로 path 비교, windows 의 경우 대소문자 구분이 없음
            if os.name == 'nt':
                for open_file in open_list:
                    if exclude_file.lower() != open_file.lower():
                        continue
                    open_list.remove(open_file)
                    normalize_cstrace[pid]['open'] = open_list
            else:
                if exclude_file in open_list:
                    open_list.remove(exclude_file)
                    normalize_cstrace[pid]['open'] = open_list

    # LDH, 소스가 0 size인 경우 open을 시도하지 않음 혹은
    # open list에 소스가 존재하지 않는 경우 open list에 추가
    normalize_cstrace = cslib.check_omitted_file_in_cstrace(normalize_cstrace)

    return normalize_cstrace


# LDH, 소스가 0 size인 경우 open을 시도하지 않음
def check_omitted_file_in_cstrace(cstrace_json):
    for pid in cstrace_json:
        if cstrace_json[pid]['execve'] is not None:
            command_list = cstrace_json[pid]['execve'][1]
            source_list = get_source_list(command_list)
            open_file_list = cstrace_json[pid]["open"]
            for source_file in source_list:
                if source_file not in open_file_list:
                    open_file_list.append(source_file)
            cstrace_json[pid]["open"] = open_file_list
    return cstrace_json


def get_source_list(commands):
    source_list = []
    for command in commands:
        if is_source_file(command):
            file_name, file_ext = os.path.splitext(command)
            if re.match("^\\.[cC](\\+\\+|pp|PP|xx|XX|C|c)?$", file_ext) is not None:
                source_list.append(command)
    return source_list


def find_source_file_path(args):
    for arg in args:
        file_name, file_ext = os.path.splitext(arg)
        if re.match("^\\.[cC](\\+\\+|pp|PP|xx|XX|C|c)?$", file_ext) is not None:
            return arg
    return None


def is_interest_call(call_command):
    """ A predicate to decide the entry is a compiler call or not. """
    basename = os.path.basename(call_command).lower()
    patterns = [
        re.compile(r'^g(cc|\+\+)(-\d+(\.\d+){0,2})?'),
        re.compile(r'^([^-]*-)*g(cc|\+\+)(-\d+(\.\d+){0,2})?'),
        re.compile(r'^([^-]*-)*clang(\+\+)?(-\d+(\.\d+){0,2})?'),
        re.compile(r'^llvm-g(cc|\+\+)'),
        re.compile(r'^([^-]*-)*ar$'),
        re.compile(r'c\+\+(-\d+(\.\d+){0,2})?'),
        re.compile(r'cc'),
    ]

    results = any((pattern.match(basename) for pattern in patterns))

    if results:
        return True
    else:
        return False


def is_source_or_header_file(file_path, system_include_path_list=None):
    if cslib.is_debug_mode():
        import libcsbuild
        libcsbuild.write_csbuild_log('source and header extension: ' + str(source_and_header_extension))
    if file_path.endswith(source_and_header_extension):
        return True
    # LDH, file_path 가 upper 되어 있어서 확장자 검색하는데 불일치하는 이슈 발생
    for extension in source_and_header_extension:
        if file_path.endswith(extension.upper()):
            return True
    """
    if system_include_path_list is not None:
        root, ext = os.path.splitext(os.path.basename(file_path))
        if not ext:
            for system_include_path in system_include_path_list:
                if file_path.startswith(system_include_path + os.sep):
                    return True
    """

    root, ext = os.path.splitext(os.path.basename(file_path))
    if not ext:
        return True

    return False


def is_exclusive_pattern(command_list):
    exclusive_pattern_list = default_exclusive_pattern_list + cmake_pattern_list + user_exclusive_pattern_list

    for command in command_list:
        for exclusive_pattern in exclusive_pattern_list:
            if exclusive_pattern in command:
                return True
        if command.startswith('/tmp/'):
            return True
        if command.endswith('.os'):
            return True
        if command == "gcc_test.c":
            return True
    return False


def valid_check_for_linking_command(command_list, toolset):
    program_name, ext = os.path.splitext(os.path.basename(command_list[0]))
    for command in command_list:
        toolset_option_list = toolset.get_output_option()
        linker_name_list = toolset.linker_program_name
        if program_name in linker_name_list:
            if command in toolset_option_list:
                return True
            for toolset_option in toolset_option_list:
                if not command.startswith(toolset_option):
                    continue
                if len(command) > len(toolset_option):
                    return True
        if command.startswith("-o"):
            if command == "-o":
                return True
            elif len(command) > 2:
                return True

    if is_archive_process(os.path.basename(command_list[0])):
        if len(command_list) > 2:
            return True

    if find_source_file_path(command_list) is not None:
        return True
    return False


def initializer_for_pool(staticfile, csbuild_log_path, console_log_path, executable_counter=None):
    if staticfile is not None and staticfile.USER_DEFINED_EXTENSIONS is not None:
        cslib.set_user_defined_source_extension(tuple(staticfile.USER_DEFINED_EXTENSIONS['source']))
        cslib.set_user_defined_header_extension(tuple(staticfile.USER_DEFINED_EXTENSIONS['header']))
        cslib.set_user_defined_object_extension(tuple(staticfile.USER_DEFINED_EXTENSIONS['object']))
        cslib.update_extension()

    import libcsbuild
    libcsbuild.set_log_path(csbuild_log_path, console_log_path)

    import processor
    if executable_counter is not None:
        processor.set_execute_counter(executable_counter)


def update_extension():
    global object_extension, file_extension, header_extension, source_extension, source_and_header_extension
    global bak_object_extension, bak_source_extension, bak_header_extension

    bak_header_extension = header_extension
    bak_source_extension = source_extension
    bak_object_extension = object_extension

    source_extension = source_extension + user_defined_source_extension
    header_extension = header_extension + user_defined_header_extension
    object_extension = object_extension + user_defined_object_extension
    source_and_header_extension = source_extension + header_extension
    file_extension = source_and_header_extension + object_extension + library_extension


def clear_extension():
    global object_extension, file_extension, header_extension, source_extension, source_and_header_extension
    global bak_object_extension, bak_source_extension, bak_header_extension
    source_extension = bak_source_extension
    header_extension = bak_header_extension
    object_extension = bak_object_extension
    source_and_header_extension = source_extension + header_extension
    file_extension = source_and_header_extension + object_extension + library_extension


def set_user_defined_source_extension(user_source_extension):
    global user_defined_source_extension
    user_defined_source_extension = user_source_extension


def set_user_defined_header_extension(user_header_extension):
    global user_defined_header_extension
    user_defined_header_extension = user_header_extension


def set_user_defined_object_extension(user_object_extension):
    global user_defined_object_extension
    user_defined_object_extension = user_object_extension


## Move to StaticFile class in static.py
# def set_user_defined_environment(staticfile):
#     import libcsbuild
#     environment_dict = {}
#     extra_options = get_extra_option_of_static_file(staticfile)
#     if extra_options is not None and 'USER_DEFINED_ENVIRONMENTS' in extra_options:
#         environment_dict = extra_options['USER_DEFINED_ENVIRONMENTS']
#
#     for key in environment_dict.keys():
#         value = environment_dict[key]
#         os.environ[key] = value
#
#     env_str = 'user defined environment list: \n'
#     for key in environment_dict.keys():
#         env_str += str(key) + ': ' + str(os.getenv(key)) + '\n'
#     libcsbuild.write_csbuild_log(env_str)


def have_source_file(command_list):
    for command in command_list:
        if is_source_file(command):
            return True
    return False


def is_source_file(file_path):
    if file_path.endswith(source_extension):
        return True
    return False


def is_file(file_path):
    if file_path.endswith(file_extension):
        return True

    if os.path.isfile(file_path):
        return True

    return False


def is_static_lib_file(file_path):
    if file_path.endswith(static_library_extension):
        return True
    return False


def is_header_file(file_path):
    file_name, file_ext = os.path.splitext(file_path)
    # STCS-766, LDH, 확장자가 없는 파일은 헤더 파일일 수 있음
    if file_ext == '':
        return True
    if file_path.endswith(header_extension):
        return True
    return False


def deep_copy_of_data(src_data):
    # FIXME, deepcopy 는 확실히 느릴 수 있음, 그러므로 꼭 필요한 경우에만 써야함
    #  리스트의 경우 slicing 을 통해 얕은 복사할 수 있으나 일단 해당 함수를 사용하는 것들을 보고 나중에 확인할 필요가 있음
    return deepcopy(src_data)


def normalize_path(path):
    if is_windows():
        return os.path.normpath(path.upper()).replace('\\', '/')
    else:
        return os.path.normpath(path)


def find_archive_type_output_from_command_list(command_list):
    return command_list[2]


def is_archive_process(process_name):
    process_name = process_name.lower()
    patterns = [
        re.compile(r'^([^/]*/)*([^-]*-)*ar$'),
        re.compile(r'^link.exe$'),
        re.compile(r'^link$'),
    ]
    return any((pattern.match(process_name) for pattern in patterns))


def get_link_type_from_module_name(module_name):
    base_module_name = os.path.basename(module_name)
    if '.a' in base_module_name:
        return "lib"
    elif '.so' in base_module_name:
        return "lib"
    elif '.lib' in base_module_name:
        return 'lib'
    else:
        return "execute"


def get_absolute_path(source_name, pid, cstrace_json):
    file_list = cstrace_json[pid]["open"]
    source_name_pattern_template = ".*$(SOURCE_NAME)$"
    source_name_pattern = source_name_pattern_template.replace('$(SOURCE_NAME)', source_name)

    for file in file_list:
        if re.search(source_name_pattern, file):
            if os.path.abspath(file):
                return file

    sigchld_list = cstrace_json[pid]["sigchld"]
    if sigchld_list:
        for sigchld in sigchld_list:
            temp_return = get_absolute_path(source_name, sigchld, cstrace_json)
            if temp_return:
                return temp_return
    else:
        return None


def get_dependency_files(cstrace_json, pid, dependencies_list):
    file_list = cstrace_json[pid]["open"]
    for file in file_list:
        if is_file(file):
            dependencies_list.append(file)

    return list(set(dependencies_list))


def get_file_hash_crc32(file_path):
    import libcsbuild
    if cslib.is_unit_testing():
        return 0
    else:
        # LDH, 파일 전체 내용을 메모리에 로드하는 방식말고 잘라서 읽도록 수정
        crc32 = 0
        with open(file_path, 'rb') as file:
            try:
                for chunk in iter(lambda: file.read(4096), b""):
                    if crc32 == 0:
                        crc32 = binascii.crc32(chunk)
                    else:
                        crc32 = binascii.crc32(chunk, crc32)
            except Exception as ex:
                pass
        # with open(file_path, 'rb') as file:
        #    crc32 = binascii.crc32(file.read())
        return str('%x' % crc32)


def get_file_hash(file_path):
    file_path = cslib.normalize_path(file_path.replace("\\", "/"))
    # return file_path
    if cslib.is_unit_testing():
        return hashlib.md5(file_path.encode('utf-8')).hexdigest()
    # 알고보니 source body hash였음... 이건 되돌려놓기(# LDH, 파일 내용 뿐만 아니라 경로 까지 해시값 생성에 추가)
    md5 = hashlib.md5()
    #md5 = hashlib.md5(file_path.encode('utf-8'))
    with open(file_path, 'rb') as file:
        try:
            for chunk in iter(lambda: file.read(4096), b""):
                md5.update(chunk)
        except Exception as ex:
            pass
        return md5.hexdigest()


def is_system_header_dir(file_dir, system_header_dirs):
    for system_include_path in system_header_dirs:
        if is_windows():
            file_dir_upper = file_dir.upper()
            system_include_path_upper = system_include_path.upper()
            if file_dir_upper.startswith(os.path.abspath(system_include_path_upper)):
                return True
        else:
            if file_dir.startswith(system_include_path):
                return True
    return False


def is_exclusion_file(file, init_json, exclusions):
    if exclusions is None:
        return cslib.is_exclusion_path(file, init_json)
    else:
        return cslib.is_exclusion_path_pattern(file, exclusions)


def get_each_file_hash(file, init_json, exclusions=None):
    if cslib.is_source_or_header_file(file, []):
        file_hash = cslib.get_file_hash(file)
        # ci.exe 와 약속
        if cslib.is_system_header(file, init_json):
            file_hash = '_' + file_hash
        if cslib.is_exclusion_file(file, init_json, exclusions):
            file_hash = file_hash + '_'
        return file_hash
    else:
        return None


def files_to_hash_with_exclusion_mark(files, init_json, exclusions):
    """
    파일 목록을 해쉬로 구하고, system header 인지 user exclusion 인지를 해쉬 앞뒤에 '_' 로 표시합니다.
    '_' 가 앞에 붙어 있으면 system header 고, 뒤에 있으면 user exclusion 입니다. 둘다 붙어 있으면 system header 면서
    user exclude 인 경우 입니다.
    :param files: 파일 목록
    :param init_json: 이거 필요없고, system include 목록만 있으면 되는데...
    :param exclusions:
    :return:
    """
    dependency_hash_list = []
    for file in files:
        if cslib.exists(file):
            file_hash = get_each_file_hash(file, init_json, exclusions)
            if file_hash is not None:
                dependency_hash_list.append(file_hash)
            """
            if cslib.is_source_or_header_file(file, []):
                file_hash = cslib.get_file_hash(file)
                is_system_header = cslib.is_system_header(file, init_json)
                is_exclusion_path = cslib.is_exclusion_path_pattern(file, exclusions)
                # ci.exe 와 약속
                if is_system_header:
                    file_hash = '_' + file_hash
                if is_exclusion_path:
                    file_hash = file_hash + '_'
                dependency_hash_list.append(file_hash)
            """

    dependency_hash_list = list(set(dependency_hash_list))
    dependency_hash_list.sort()
    return dependency_hash_list


def is_system_header(file, init_json):
    # STCS-322, SDH, 소스코드도 시스템 헤더로 인식하는 버그 존재, 소스 코드 확장자 검사하는 코드 추가
    file_path = os.path.abspath(file)

    # SDH source extension exclusion
    global source_extension
    fileExtension = os.path.splitext(file_path)[1]
    # 확장자가 없는 경우 PASS 되므로 분석대상에 포함됨
    if fileExtension in source_extension:
        return False
    is_system_header_file = False
    if 'toolchains' in init_json:
        for toolchain in init_json["toolchains"]:
            if 'include' in toolchain:
                is_system_header_file |= is_system_header_dir(os.path.dirname(file_path), toolchain['include'])
    return is_system_header_file


def get_system_default_locale_encoding():
    locale_info = locale.getpreferredencoding()
    if locale_info is None or type(locale_info) is not str:
        return ''
    return locale.getpreferredencoding()


def get_json_content_from_path(path, text_encoding='utf-8'):
    if os.path.exists(path):
        with open(path, 'r', encoding=text_encoding) as conf:
            json_content = json.load(conf, object_pairs_hook=OrderedDict)
            return json_content
    else:
        raise Exception("Can't find json file : ", path)


def create_json_from_data(json_data, file_path, text_encoding='utf-8'):
    with open(file_path, 'w', encoding=text_encoding) as json_file:
        json.dump(json_data, json_file, indent=4, ensure_ascii=False)
    os.chmod(file_path, 0o777)


def read_contents_from_file(file_path, text_encoding='utf-8') -> (bool, str):
    if not os.path.exists(file_path):
        return False, ''
    try:
        with open(file_path, 'r', encoding=text_encoding) as file:
            return True, file.read()
    except Exception as e:
        return False, f'Error: {str(e)}'


def make_absolute_path(build_location, current_file_path, os_name=None):
    def get_normalized_path(cur_path, os_env_name):
        if cslib.is_unit_testing():
            path_delimiter = ''
            if os_env_name == 'linux':
                path_list = cur_path.split('/')
                path_delimiter = '/'
            else:
                path_list = cur_path.split('\\')
                path_delimiter = '\\'
            try:
                inx = path_list.index('.')
                del path_list[inx]
            except ValueError:
                pass
            try:
                inx = path_list.index('..')
                del path_list[inx]
                del path_list[inx - 1]
            except ValueError:
                pass
            return path_delimiter.join(path_list)
        else:
            return os.path.normpath(cur_path)

    if os_name is not None:
        if os_name == 'linux':
            if current_file_path.startswith('/'):
                return get_normalized_path(current_file_path, os_name)
            else:
                return get_normalized_path(build_location + '/' + current_file_path, os_name)
        else:
            current_file_path = current_file_path.replace('/', '\\')
            if current_file_path.find(':') == 1:
                return get_normalized_path(current_file_path, os_name)
            else:

                return get_normalized_path(build_location + '\\' + current_file_path, os_name)
    else:
        full_path = os.path.join(build_location, current_file_path)
        abs_path = os.path.abspath(full_path)
        # LDH
        if os.path.exists(abs_path):
            return abs_path
        elif cslib.is_unit_testing():
            return abs_path
        else:
            return current_file_path


def wildcard_normalize(build_location, commands):
    cmds = []
    for command in commands:
        if "*." in command:
            files = glob.glob(os.path.join(build_location, command))
            cmds.extend(files)
        else:
            if cslib.is_unit_testing() and cslib.is_file(command) and not command.startswith('/'):
                cmds.append(os.path.join(build_location, command))
            else:
                cmds.append(command)
    return cmds


def is_defined_macro_options(command):
    defined_macro_option_list = ['-D', '/D']
    for option in defined_macro_option_list:
        # if command == option or (command.startswith(option) and len(option) < len(command)):
        if command == option:
            return True
    return False


def filepath_normalized_option(build_location, command_list):
    """
    command line 인자들을 모두 조사해서, 상대경로로 나타날 수 있는 항목들은 절대경로로 치환해준다.
    :param build_location: 빌드가 일어난 위치
    :param command_list: 빌드시 사용된 커맨드 라인 리스트
    :return: 파일 경로가 절대경로로 치환된 커맨드 리스크
    """

    try:
        cslib.chdir(build_location)
    except:
        raise Exception("couldn't change working directory:" + build_location)

    # 다음 flag 는 처리하기 쉽게 나눠둔다
    # LDH, -D 옵션 추가
    # FIXME, 툴체인 별로 include 옵션이 다를 수 있다...
    concat_options = ['-I', '--include', '-o', '/I', "/Fd", "/Fo", '-D', '/D']

    def change_include_abs_path(build_dir_path, file_path):
        if not os.path.isabs(file_path):
            maybe_abs_path = os.path.normpath(os.path.join(build_dir_path, file_path))
            # STCS-322, 해당 경로가 디렉토리일 수도 파일일 수 도 있음, 존재 여부를 확인하도록 수정
            if os.path.exists(maybe_abs_path):
                file_path = maybe_abs_path
        return file_path

    def is_include_path(build_path, maybe_path):
        if maybe_path == "":
            return False
        # STCS-254, LDH, include 옵션 이후 경로가 상대경로일 경우 절대 경로로 치환하여 확인한다.
        maybe_path = change_include_abs_path(build_path, maybe_path)
        if cslib.is_windows() and (len(maybe_path) > 2 and maybe_path[1] == ':') or maybe_path.startswith('.'):
            return True
        elif not cslib.is_windows() and (maybe_path.startswith('.') or maybe_path.startswith('/')):
            return True
        else:
            return False

    def split_option(value):
        for concat_option in concat_options:
            # LDH, 리눅스인 경우 '/' 시작하는 옵션은 예외
            if concat_option.startswith('/') and build_location.startswith('/'):
                continue
            # LDH, concat 문제 해결한듯 # FIXME: 여기서 /I 로 시작하는 옵션은 다 concat 해버림
            target_value = value[len(concat_option):]
            if value.startswith(concat_option) and len(concat_option) < len(value):
                if concat_option in ['-I', '--include', '/I']:
                    if not is_include_path(build_location, target_value):
                        continue
                    # STCS-254, LDH, include 옵션 이후 경로가 상대경로일 경우 절대 경로로 치환한다.
                    target_value = change_include_abs_path(build_location, target_value)
                # 출력 옵션이 붙어있는지 판단 여부
                elif concat_option in ['-o'] and not os.path.exists(target_value):
                    continue
                return value[:len(concat_option)], target_value

        return value, None

    normalize_commands = []
    n_command = len(command_list)
    i = 0
    while i < n_command:
        value = command_list[i]
        option, arg = split_option(value)
        normalize_commands.append(option)
        if arg is not None:
            normalize_commands.append(arg)
        i += 1

    normalized = []

    # LDH, 매크로 옵션인 경우, 절대경로 치환 스킵하도록 변경
    is_macro_flag = False
    for arg in normalize_commands:
        if is_defined_macro_options(arg):
            is_macro_flag = True
            normalized.append(arg)
            continue
        elif is_macro_flag:
            is_macro_flag = False
            normalized.append(arg)
            continue
        unquote_arg = arg.replace('"', '')
        joined = "%s/%s" % (build_location, unquote_arg)  # os.path.join 을 사용하면, \ 와 / 가 join 될때 잘못된 경우가 많이 발생한다
        if os.path.exists(joined):
            normalized.append(os.path.abspath(joined))
            continue

        normalized.append(arg)
    return normalized


def decode_octal_encoding(encoded):
    '''
    "\355\225\234" ==> '한' 과 같이 8진수로 표현된 unicode 문자를 utf-8 로 변환한다.
    :param encoded:
    :return:
    '''
    values = []
    key = ""
    cnt = 0
    for octc in re.findall(r'\\(\d{3})', encoded):
        cnt += 1
        key += (r'\%s' % octc)
        values.append(int(octc, 8))
        if cnt % 3 == 0:
            # STCS-322, SDH, LDH, 한글로 변환 시 예외 발생, 예외 발생 시 변환 처리 생략
            # FIXME, 한글 디코딩 문제는 여전히 남아있음, 받침이 없는 경우 8진수 2개 존재
            # FIXME, ex. \355\225 ==> '하'
            try:
                encoded = encoded.replace(key, bytearray(values).decode('utf-8'))
                key = ""
                values = []
            except:
                encoded = ""
                key = ""
                values = []
                pass
    return encoded


def print_json(jsondict):
    print(json.dumps(jsondict, indent=2))


def is_unit_testing():
    if os.getenv('CSBUILD_UNIT_TEST') is not None:
        return True
    else:
        return False


def is_linux_path(input_path: str):
    if input_path.startswith('/'):
        return True
    return False

