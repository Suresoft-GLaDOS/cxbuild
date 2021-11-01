import os
import cslib
import libcsbuild

from collections import OrderedDict


# ---------------------------------------------
class CompilerTool(object):
    def __int__(self):
        pass

    def get_object_extension(self):
        raise NotImplementedError()

    def get_object_file_path(self, commands):
        raise NotImplementedError()

    def get_linked_name(self, commands, is_basename=True):
        raise NotImplementedError()

    def get_source_list(self, commands, cstrace_json, pid):
        raise NotImplementedError()

    def is_multi_file_compile(self, commands):
        raise NotImplementedError()

    def is_preprocess_command(self, commands):
        raise NotImplementedError()

    def is_defined_macro_options(self, command):
        raise NotImplementedError()


# ---------------------------------------------
class DefaultCompilerTool(CompilerTool):
    toolchain_info = None
    toolchain_name = None
    linked_name = None
    build_location = None
    base = None
    object_file_extension = None
    executable_file_extension = []
    static_library_extension = []
    driver_program_name = []
    compiler_program_name = []
    linker_program_name = []
    static_linker_program_name = []
    archive_program_name = []
    assembler_program_name = []
    preprocess_option = []
    compile_only_option = []
    output_option = []
    assembler_option = []
    static_linking_option = []
    parallel_build_option = []
    defined_macro_option = []
    include_option = []
    preinclude_option = []
    create_precompiled_header_option = []
    use_precompiled_header_option = []
    regardless_of_extension = []
    regardless_of_option = []
    regardless_of_option_list = []
    source_object_relation = []
    extract_option_file = {}
    compiler_environment = {}
    enable_include_working_directory = None
    enable_include_source_file_directory = None
    enable_add_static_library_module = False
    activate_install_path_in_staticfile = None
    enable_option_file_extension_after_build_hook = False

    def __init__(self, toolchain=None):
        if toolchain is None:
            self.toolchain_name = "Default"

    def set_build_location(self, location):
        self.build_location = location

    def get_build_location(self):
        return self.build_location

    def get_toolchain_name(self):
        return self.toolchain_name

    def get_compiler_environment(self, tool_version):
        return self.compiler_environment[tool_version]

    def get_object_extension(self):
        return self.object_file_extension

    def get_executable_extension(self):
        return self.executable_file_extension

    def get_program_name(self, command):
        basename = os.path.basename(command).lower()
        basename, ext = os.path.splitext(basename)
        return basename

    def has_output_option_and_get_output_name(self, command_list):
        out_option_list = self.get_output_option()
        out_option_tuple = tuple(out_option_list)

        find_opt_index_list = [command_list.index(option) for option in command_list if option in out_option_list]
        find_opt_list = [option for option in command_list if option.startswith(out_option_tuple)]

        # 먼저 command_list 에서 output_option 과 일치하는 요소가 있는지 확인해서 있으면 다음 command 반환(ex. -o Test)
        if len(find_opt_index_list) != 0:
            find_path = command_list[find_opt_index_list[0] + 1]
            return True, find_path

        # 이후 command_list 에서 output_option 으로 시작하는 요소가 있는지 확인해서 있으면 다음 command 반환(ex. -oTest)
        elif len(find_opt_list) != 0:
            find_path = find_opt_list[0]
            for option in out_option_list:
                if find_path.startswith(option):
                    return True, find_path[len(option):]

        # archive 명령이면 처리
        elif cslib.is_archive_process(command_list[0]):
            return True, cslib.find_archive_type_output_from_command_list(command_list)

        else:
            return False, ''

    def generate_output_file_path(self, command_list, object_mode_flag):
        source_file_path = cslib.find_source_file_path(command_list)
        if source_file_path is not None:
            find_compile_only_option_list = [option for option in command_list if option in self.compile_only_option]
            if ( object_mode_flag and len(find_compile_only_option_list) == 0 ) or \
               ( not object_mode_flag and len(find_compile_only_option_list) != 0 ):
                # gcc test.cpp 로 호출한 경우,
                # 빌드 경로에 a.exe 출력
                return 'a.out'
            elif object_mode_flag:
                file_name, file_ext = os.path.splitext(source_file_path)
                object_file_path = ''.join([file_name, '.' + self.get_object_extension()])
                return object_file_path
            else:
                file_name, file_ext = os.path.splitext(source_file_path)
                return file_name
        else:
            return ''

    def get_output_file_path(self, command_list):
        has_output_option, output_name = self.has_output_option_and_get_output_name(command_list)
        if has_output_option:
            return output_name
        # If can't find -o option
        else:
            return self.generate_output_file_path(command_list, object_mode_flag=False)

    def get_object_file_path(self, command_list):
        def get_obj_path_from_source_path(obj_path):
            if not cslib.is_unit_testing() and not os.path.isdir(obj_path):
                obj_path = os.path.dirname(obj_path)
            source_path = get_source_file(command_list)
            if type(source_path) is bool:
                return obj_path
            if obj_path == '':
                obj_path = os.path.dirname(source_path)
            basename, ext = os.path.splitext(os.path.basename(source_path))
            return os.path.join(obj_path, basename + '.' + self.object_file_extension)

        def get_source_file(command_list):
            import cslib
            for command in command_list:
                if cslib.is_source_file(command):
                    return command
            return False

        def get_object_file_path_without_option(commands):
            src_file_path = get_source_file(commands)
            if src_file_path is not None:
                if len(set(self.compile_only_option).intersection(set(command_list))) == 0:
                    return "a.out"
                else:
                    src_file_name, file_ext = os.path.splitext(src_file_path)
                    object_file_path = ''.join([src_file_name, '.' + self.get_object_extension()])
                    return object_file_path
            return ""

        # FIXED, LDH, 같은 이름을 가지고 확장자가 다른 2개의 tu 에 대해서는 project.json 에서 겹침
        #  ctrace.json 에서 object 파일 명을 지정하였으므로 아래 코드는 필요 없음
        # # STATIC-2220, spec file 이름과 동일한 object 파일 구섣
        # if cslib.is_import_spec_file_mode():
        #     source_file_path = get_source_file(command_list)
        #     file_name, ext = os.path.splitext(os.path.basename(source_file_path))
        #     return os.path.join(os.path.dirname(source_file_path), file_name + '.o')

        has_output_option, output_name = self.has_output_option_and_get_output_name(command_list)

        # If can't find -o option
        if not has_output_option:
            return self.generate_output_file_path(command_list, object_mode_flag=True)

        find_path = output_name
        if not find_path.endswith(self.object_file_extension):
            if not os.path.isdir(find_path):
                find_path = os.path.dirname(find_path)
            source_path = get_source_file(command_list)
            if type(source_path) is bool:
                return find_path
            if find_path == '':
                find_path = os.path.dirname(source_path)
            basename, ext = os.path.splitext(os.path.basename(source_path))
            find_path = os.path.join(find_path, basename + '.' + self.object_file_extension)
        return find_path

    def get_preinclude_path(self, commands, build_location):
        preinclude_header_path_list = []
        preinclude_opt_flag = False
        for command in commands:
            if command in self.preinclude_option:
                preinclude_opt_flag = True
                continue
            elif preinclude_opt_flag:
                preinclude_header_path_list.append(cslib.make_absolute_path(build_location, command))
                preinclude_opt_flag = False
        return preinclude_header_path_list

    def has_precompiled_header_option(self, commands, option_list):
        if len(option_list) == 0:
            return False
        for command in commands:
            command = command.replace('\"', '')
            for precompiled_option in option_list:
                if command.startswith(precompiled_option):
                    return True
        return False

    # STCS-254, LDH, 미리 컴파일된 헤더 생성 옵션과 사용 옵션이 둘 다 존재하는 경우, 생성 옵션을 사용한 TU에서 open 항목을 사용 옵션이 있는 TU의 open 항목에 복사
    def add_precompiled_header_open_list_in_cstrace(self, cstrace_json):
        def get_precompiled_header_path(command_list, current_build_location, is_created_mode=True):
            precompiled_header_path = ""
            for command in command_list:
                command = command.replace('\"', '')
                # 사용 옵션은 검색 대상에서 제거
                # precompiled_option_list = self.create_precompiled_header_option + self.use_precompiled_header_option
                if is_created_mode:
                    search_list = self.create_precompiled_header_option
                else:
                    search_list = self.use_precompiled_header_option
                for precompiled_option in search_list:
                    if not command.startswith(precompiled_option):
                        continue
                    precompiled_src_path = get_source_path_in_command(command_list)
                    dir_path = os.path.join(current_build_location, os.path.dirname(precompiled_src_path))
                    precompiled_header_path = os.path.join(dir_path, command[len(precompiled_option):])
                    break
                if precompiled_header_path != "":
                    break
            if precompiled_header_path != "" and os.path.exists(precompiled_header_path):
                libcsbuild.write_csbuild_log('precompiled_header path: ' + str(precompiled_header_path))
                return precompiled_header_path
            libcsbuild.write_csbuild_log('WARNING: Cannot found precompiled_header path')
            return precompiled_header_path

        def get_include_option_list(command_list):
            include_list = []
            for inx in range(len(command_list)):
                command = command_list[inx]
                if command == "/I" or command == "-I":
                    if self.toolchain_name == "Microsoft":
                        include_list.append("/I")
                    else:
                        include_list.append("-I")
                    include_list.append(command_list[inx + 1])
            return include_list

        def insert_precompiled_header_dir_path_in_include_list(precompiled_header_file_path):
            if precompiled_header_file_path == "":
                return []
            include_list = []
            precompiled_header_dir_path = os.path.dirname(precompiled_header_file_path)
            if self.toolchain_name == "Microsoft":
                include_list.append("/I")
            else:
                include_list.append("-I")
            include_list.append(precompiled_header_dir_path)
            return include_list

        def get_source_path_in_command(command_list):
            for command in command_list:
                if cslib.is_file(command) and cslib.is_source_file(command):
                    return command
            return False

        def get_packed_element_in_created_precompiled_header_mode(command_list):
            precompiled_header_open_list = cstrace_json[pid]['open']

            # STCS-298, '/Yc' 옵션 사용 TU 의 open list에서 TU 소스 파일 경로 제외시키기
            source_file_path = get_source_path_in_command(command_list)
            if type(source_file_path) is not bool and source_file_path in precompiled_header_open_list:
                libcsbuild.write_csbuild_log('Delete TU source file with /Yc opt ( ' + source_file_path + ')')
                precompiled_header_open_list.remove(source_file_path)

            # precompiled_header 절대경로 얻어낸 후 I 옵션에 include directory 를 추가
            precompiled_header_path = get_precompiled_header_path(command_list, build_location)
            include_option_path_list = insert_precompiled_header_dir_path_in_include_list(precompiled_header_path)
            include_option_path_list.extend(get_include_option_list(command_list))
            return precompiled_header_path, precompiled_header_open_list, include_option_path_list

        # STCS-553, /Yc와 /Yu 간 옵션 cycle을 고려하지 않아 발생한 문제, /Yc 가 다시 나오면 이전 /Yc 수집했던 정보 폐기하도록 수정
        precompiled_header_dict = OrderedDict()
        for pid in cstrace_json.keys():
            if 'execve' not in cstrace_json[pid].keys():
                continue
            commands = cstrace_json[pid]['execve'][1]
            build_location = cstrace_json[pid]['execve'][2]

            # /Yc 옵션이 존재하는 경우 open한 header 리스트 얻기
            if self.has_precompiled_header_option(commands, self.create_precompiled_header_option):
                precompiled_header_path, precompiled_header_open_list, include_option_list = \
                    get_packed_element_in_created_precompiled_header_mode(commands)
                precompiled_header_dict[precompiled_header_path] = {"open": precompiled_header_open_list,
                                                                    "include": include_option_list}

            # /Yu 옵션이 존재하는 경우 header 리스트 합치기
            elif self.has_precompiled_header_option(commands, self.use_precompiled_header_option):
                precompiled_header_path = get_precompiled_header_path(commands, build_location, is_created_mode=False)
                if not precompiled_header_dict.get(precompiled_header_path, {}):
                    libcsbuild.write_csbuild_log('WARNING: Created \'Precompiled header\' is not exists.')
                    continue
                value_dict = precompiled_header_dict.get(precompiled_header_path)
                cstrace_json[pid]['open'] += value_dict['open']
                cstrace_json[pid]['open'] = list(set(cstrace_json[pid]['open']))
                cstrace_json[pid]['execve'][1] = [commands[0]] + value_dict['include'] + commands[1:]

            else:
                continue
        return cstrace_json

    def normalize_linked_name(self, file_path):
        if os.path.isabs(file_path):
            file_path = os.path.basename(file_path)
        else:
            if file_path.find('/') != -1:
                index = file_path.rfind('/')
                file_path = file_path[index + 1:]
            elif file_path.find('\\') != -1:
                index = file_path.rfind('\\')
                file_path = file_path[index + 1:]
        return file_path

    def get_linked_name(self, commands, is_basename=True):
        if is_basename:
            name = self.normalize_linked_name(self.get_output_file_path(commands))
        else:
            name = self.get_output_file_path(commands)
        if name == '':
            name = 'DefaultModule'
        if name.startswith('='):
            name = name[1:]
        return name

    def set_linked_name(self, name):
        self.linked_name = name

    def get_source_list(self, commands: list, cstrace_json, pid):
        # STCS-1044, LDH, 소스 파일 경로 수집 시 include 옵션이 걸려 있지 않은 곳에서만 수집하도록 수정
        sources = [command for command in commands if
                   cslib.is_source_file(command) and not self.is_include_option(commands[commands.index(command) - 1])]
        # LDH, for parallel build
        sources = self.get_source_files_in_parallel_build(commands, cstrace_json, pid, sources)
        return sources

    # split option list and source file list
    def split_command(self, commands: list, cstrace_json, pid):
        sources = self.get_source_list(commands, cstrace_json, pid)
        options = [command for command in commands if command not in sources]
        return options, sources

    def get_source_files_in_parallel_build(self, commands, cstrace_json, pid, source_files):
        # LDH, 멀티 프로세서 옵션이 활성화 되어 있는 경우 dependency 처리 필요
        # 멀티 프로세서 옵션이 활성화되면 멀티 프로세스 환경에서 멀티 소스 코드 컴파일이 수행됨
        subprocess_source_list = []
        multi_process_build = False
        # open 된 소스 파일 수집 후 컴파일러 입력 소스 코드와 겹치는 코드 확인
        # 겹치는 코드가 실제 서브 프로세스에서 컴파일되는 대상임
        if self.has_multi_processor_option(commands):
            open_source_path_list = []
            for source_path in cstrace_json[pid]['open']:
                if cslib.is_source_file(source_path):
                    open_source_path_list.append(source_path)
            for open_source_path in open_source_path_list:
                for source in source_files:
                    source = os.path.normpath(os.path.join(self.get_build_location(), source))
                    if open_source_path.lower() == source.lower():
                        subprocess_source_list.append(source)

            # 코드 개수가 일치하면 메인 프로세스임, 이 경우 제외시킨다
            if len(subprocess_source_list) != len(source_files):
                multi_process_build = True
        if multi_process_build:
            source_files = subprocess_source_list

        return list(set(source_files))

    def get_output_option(self):
        return self.output_option

    def is_default_compiler_tool(self):
        if self.toolchain_name == "Default":
            return True
        else:
            return False

    # STCS-151, tool_name 이 관심 있는 프로그램 이름 리스트에 존재하는지 확인
    def is_equal_to_tool_name(self, tool_name, program_list):
        if tool_name in program_list:
            return True

        tool_name_split = tool_name.split('-')
        if tool_name_split[-1] in program_list:
            return True

        return False

    def is_object_file(self, command):
        if self.get_object_extension() is None:
            return False
        file_basename = os.path.basename(command)
        tool_name, ext = os.path.splitext(file_basename)
        if ext == self.object_file_extension or ext.find(self.object_file_extension) != -1:
            return True
        else:
            return False

    def is_include_option(self, command: str):
        if command in self.include_option:
            return True
        if command in ['-I', '--include', '--include_directory']:
            return True
        return False

    def is_compiler_driver_command(self, commands):
        base_name = self.get_program_name(commands[0])
        for driver_name in self.driver_program_name:
            if base_name.find(driver_name) != -1:
                return True
        return False

    def is_preprocess_command(self, commands):
        base_name = self.get_program_name(commands[0])
        if len(self.driver_program_name) == 0:
            for compiler_name in self.compiler_program_name:
                if base_name.find(compiler_name) != -1:
                    for option in self.preprocess_option:
                        if option in commands:
                            return True
        else:
            for driver_name in self.driver_program_name:
                if base_name.find(driver_name) != -1:
                    for option in self.preprocess_option:
                        if option in commands:
                            return True
        return False

    def is_compile_only_command(self, commands):
        basename = self.get_program_name(commands[0])
        for option in self.compile_only_option:
            for driver_name in self.driver_program_name:
                if option in commands and basename.find(driver_name) != -1:
                    return True

        if basename in self.compiler_program_name:
            if len(self.compile_only_option) == 0:
                return True
            elif len(set(self.compile_only_option).intersection(set(commands))) != 0:
                return True
        return False

    def is_assembler_command(self, commands):
        base_name = self.get_program_name(commands[0])
        if self.is_compiler_driver_command(commands):
            for command in commands:
                if command in self.assembler_option:
                    return True
        else:
            if base_name in self.assembler_program_name:
                return True
        return False

    def is_linking_command(self, commands):
        basename = self.get_program_name(commands[0])
        # STCS-268 link와 관련 없는 옵션 제외
        if len(set(commands).intersection(set(self.regardless_of_option))) > 0:
            return False
        for linker_name in self.linker_program_name:
            if basename.find(linker_name) != -1:
                return True
        for driver_name in self.driver_program_name:
            if basename.find(driver_name) != -1:
                if self.is_compile_only_command(commands):
                    return False
                for command in commands:
                    if command in self.get_output_option():
                        return True
        return False

    def is_static_linking_command(self, commands):
        if not self.is_linking_command(commands):
            return False
        for static_liking_opt in self.static_linking_option:
            for command in commands:
                if command.startswith(static_liking_opt) or command.startswith(static_liking_opt.lower()):
                    return True
        return False

    def is_not_compile_and_linking_command(self, commands):
        program_name, ext = os.path.splitext(os.path.basename(commands[0]))
        program_name = program_name.lower()
        interested_program_name_list = self.compiler_program_name + self.linker_program_name + self.driver_program_name + self.static_linker_program_name + self.archive_program_name + self.assembler_program_name
        interested_program_name_list = [program.lower() for program in interested_program_name_list]
        if program_name in interested_program_name_list:
            return False
        if len([interested_prog_name for interested_prog_name in interested_program_name_list if program_name.endswith(interested_prog_name) or program_name.startswith(interested_prog_name)]) != 0:
            return False
        return True

    def is_static_library_file(self, command, command_list, static_link_list):
        import cslib
        if cslib.is_unit_testing():
            if cslib.is_windows() and not command.startswith('/'):
                if not cslib.is_static_lib_file(command):
                    return_flag = False
                else:
                    return_flag = True
            elif command.startswith('/'):
                if not cslib.is_static_lib_file(command):
                    return_flag = False
                else:
                    return_flag = True
            else:
                return_flag = False
            return return_flag
        if not os.path.isfile(command):
            return False
        return False

    @staticmethod
    def _equal_or_startswith_option(command, option) -> bool:
        return command == option or (command.startswith(option) and len(option) < len(command))

    @staticmethod
    def _delete_double_quote_if_exist_start_and_end_command(command, option):
        if option.find('"') != -1 and command[-1] == '"':
            command = command[:-1]
        return command

    @classmethod
    def _get_replaced_command(cls,
                              command: str,
                              option_list: list,
                              change_option: str,
                              is_macro_option: bool) -> str:
        for option in option_list:
            # FIXED, STCS-1155
            if cls._equal_or_startswith_option(command, option):
                command = command.replace(option, change_option)
                if is_macro_option:
                    command = cls._delete_double_quote_if_exist_start_and_end_command(command, option)
                else:
                    command = command.replace('"', '')
        return command

    @classmethod
    def replace_options(cls, commands, option_list, change_option, is_macro_option=False):
        changed_command_list = []
        for command in commands:
            command = cls._get_replaced_command(command, option_list, change_option, is_macro_option)
            changed_command_list.append(command)
        return cslib.deep_copy_of_data(changed_command_list)

    def _replace_include_option(self, commands):
        if len(self.include_option) > 0:
            commands = self.replace_options(commands,
                                            self.include_option,
                                           '-I',
                                            is_macro_option=False)
        return commands

    def _replace_macro_option(self, commands):
        if len(self.defined_macro_option) > 0:
            commands = self.replace_options(commands,
                                            self.defined_macro_option,
                                           '-D',
                                            is_macro_option = True)
        return commands

    def normalize_commands(self, commands):
        new_command_info = []
        # LDH, include 옵션이 '-I' 가 아닐 경우 변경(Cosmic Compiler)
        commands = self._replace_include_option(commands)

        # LDH, define macro 옵션이 '-D' 가 아닐 경우 변경(Cosmic Compiler)
        commands = self._replace_macro_option(commands)

        # STCS-306, regardless_of_option_list 패턴 삭제
        for option in self.regardless_of_option_list:
            option_list = option
            while option_list[0] in commands:
                inx = commands.index(option_list[0])
                inx2 = commands[inx:].index(option_list[1])
                if inx2 == 1:
                    if option_list[1] == '-I' or option_list[1] == '-D':
                        commands = commands[:inx + inx2 + 1] + commands[inx + inx2 + 2:]
                    commands = commands[:inx + inx2] + commands[inx + inx2 + 1:]
                    commands = commands[:inx] + commands[inx + 1:]

        # STCS-306, -I 옵션 경로에 환경 변수가 존재하는 경우 해당 옵션 삭제
        include_list = []
        while '-I' in commands:
            include_dir_path = commands[commands.index('-I')+1]
            if include_dir_path.find('$(') == -1 and include_dir_path.find('%') == -1:
                include_list.append('-I')
                include_list.append(include_dir_path)
            inx = commands.index('-I')
            commands = commands[:inx] + commands[inx + 2:]
        commands = [commands[0]] + include_list + commands[1:]

        # LDH, 경로에 띄어쓰기 존재시 "" 붙이는 작업
        new_command_info.append(commands[0])
        for command in commands[1:]:
            prerequisite = cslib.exists(command)
            have_double_quote = command.startswith(r'"') and command.endswith(r'"')
            if prerequisite and not have_double_quote and command.find(" ") != -1:
                command = '"' + command + '"'
            new_command_info.append(command)

        if self.enable_include_working_directory:
            if self.toolchain_name == 'Microsoft':
                new_command_info.append("/I")
            else:
                new_command_info.append("-I")
            new_command_info.append(self.build_location)

        if self.enable_include_source_file_directory:
            source_list = cslib.get_source_list(new_command_info)
            if len(source_list) > 0:
                if self.toolchain_name == 'Microsoft':
                    new_command_info.append("/I")
                else:
                    new_command_info.append("-I")
                new_command_info.append(os.path.dirname(source_list[0]))

        return new_command_info

    def has_multi_processor_option(self, commands):
        if len(self.parallel_build_option) == 0:
            return False
        for command in commands:
            if command in self.parallel_build_option:
                return True
        return False

    # LDH, 컴파일 단위 명령의 output 이 object file 이 아닌 경우, object file 경로로 교체하기
    # 컴파일러 json 파일에서 source_object_relation 항목 첫번째가 컴파일 단위 프로그램, 두번째가 object file 경로를 가지고
    # 있는 프로그램
    # ex. Cosmic Compiler
    def align_source_object_relation(self, cstrace_json, linked_pid_to_child_map):
        if len(self.source_object_relation) == 0:
            return cstrace_json

        source_info_program = self.source_object_relation[0]
        object_info_program = self.source_object_relation[1]
        source_program_pid = None
        source_program_commands = None
        object_program_pid = None
        object_path = None

        for pid in linked_pid_to_child_map.keys():
            tu = list(linked_pid_to_child_map[pid])
            tu.insert(0, pid)
            tu.sort(key=int)
            for element in tu:
                # 키 검사
                if element not in cstrace_json.keys() or "execve" not in cstrace_json[element].keys():
                    continue
                program_path = cstrace_json[element]["execve"][0]
                basename, ext = os.path.splitext(os.path.basename(program_path))
                commands = cstrace_json[element]["execve"][1]
                if basename == source_info_program:
                    source_program_commands = commands
                    source_program_pid = element
                elif basename == object_info_program:
                    has_output_opt = len(set(self.get_output_option()).intersection(commands)) != 0
                    if has_output_opt:
                        output_opt = list(set(self.get_output_option()).intersection(commands))[0]
                        object_program_pid = element
                        object_path = commands[commands.index(output_opt) + 1]
                else:
                    continue

                if source_program_commands is not None and object_path is not None:
                    # 필요없는 후킹 정보 제거(ex. Cosmic 컴파일러, castm8 정보)
                    del cstrace_json[object_program_pid]
                    has_output_opt = len(set(self.get_output_option()).intersection(source_program_commands)) != 0
                    if has_output_opt:
                        output_opt = list(set(self.get_output_option()).intersection(source_program_commands))[0]
                        source_program_commands[source_program_commands.index(output_opt) + 1] = object_path
                        cstrace_json[source_program_pid]["execve"][1] = source_program_commands
                    source_program_commands = None
                    source_program_pid = None
                    object_path = None
                    object_program_pid = None

        return cstrace_json

    def has_extract_option_from_file(self):
        if len(self.extract_option_file.keys()) > 0:
            return True
        return False

    def get_option_list_from_file(self, file_path, option_list, file_extension_list):
        collected_option_list = []
        collected_file_list = []
        f = open(file_path, "r")
        line = f.readline()
        while line:
            for file_extension in file_extension_list:
                if line.rfind(file_extension) != -1:
                    collected_file_list.append(line.strip())
                    break
            for option in option_list:
                if line.find(option) != -1:
                    collected_option_list.append(option)
            line = f.readline()
        f.close()
        collected_option_list += collected_file_list
        return collected_option_list

    def add_object_file_in_commands(self, cstrace_json, key):
        # LDH, extract_option_file 에는 파일 확장자가 key, 추출할 프로그램명, 추출 정보를 입력하는 value로 구성
        # ex) Cosmic Compiler .lkf파일(목적파일 경로가 해당 파일 내에 기록되어 있음)
        basename = self.get_program_name(cstrace_json[key]['execve'][0])
        basename, ext = os.path.splitext(basename)
        for option_file_extension in self.extract_option_file.keys():
            extract_info = self.extract_option_file[option_file_extension]
            extract_program = extract_info['program']
            if basename in self.toolchain_info[extract_program]:
                commands = cstrace_json[key]['execve'][1]
                option_file_path = None
                for command in commands:
                    if command[command.rfind("\\"):].find(option_file_extension) != -1:
                        option_file_path = command
                        # 확장자를 가진 파일에서 필요한 파일 리스트를 추출
                        option_list = self.get_option_list_from_file(
                            option_file_path,
                            extract_info['option'],
                            extract_info['file_extension']
                        )

                        # 명령 인자에서 확장자 파일 제거
                        cstrace_json[key]['execve'][1].remove(command)
                        self.set_build_location(cstrace_json[key]['execve'][2])
                        # 명령 인자에 실제 필요한 파일 리스트 추가
                        for option in option_list:
                            if cslib.is_file(option):
                                option = cslib.make_absolute_path(self.get_build_location(), option)
                            cstrace_json[key]['execve'][1].append(option)
                        break

                # open 리스트에서도 확장자 파일 제거
                if 'open' in cstrace_json[key].keys():
                    if option_file_path is not None and option_file_path in cstrace_json[key]['open']:
                        cstrace_json[key]['open'].remove(option_file_path)

        return cstrace_json

    def add_option_from_file(self, cstrace_json):
        # LDH, 컴파일러 정보 json 내 extract_option_file 파싱
        if not self.has_extract_option_from_file():
            return cstrace_json
        for key in cstrace_json.keys():
            if 'execve' not in cstrace_json[key].keys():
                continue
            cstrace_json = self.add_object_file_in_commands(cstrace_json, key)
        return cstrace_json

    def get_static_link_name(self, command, command_list):
        return ''

    def get_static_library_file_path(self, command_list, static_link_list, static_lib):
        return ''


# ---------------------------------------------
class GnuCompilerTool(DefaultCompilerTool):
    def __init__(self, toolchain=None):
        super().__init__(toolchain)

    def is_default_compiler_tool(self):
        return False

    def is_linking_command(self, commands):
        basename = self.get_program_name(commands[0])

        if self.is_compile_only_command(commands):
            return False

        if basename in self.linker_program_name:
            return True

        else:
            # STCS-168, LDH, archive 프로그램명 인식 못하는 문제 수정
            basename_list = basename.split('-')
            if basename_list[-1] in self.archive_program_name or cslib.is_archive_process(basename):
                for command in commands:
                    if command.rfind(".") != -1 and command[command.rfind("."):].find("a") != -1:
                        self.set_linked_name(os.path.basename(command))
                        break
                return True
            elif basename_list[-1] in self.linker_program_name:
                return True

            for compiler_name in self.compiler_program_name:
                if basename.find(compiler_name) != -1:
                    for command in commands:
                        if command in self.get_output_option():
                            return True
        return False

    def get_static_link_name(self, command, command_list):
        basename = self.get_program_name(command_list[0])
        if basename in self.archive_program_name:
            return cslib.find_archive_type_output_from_command_list(command_list)
        return ''

    def get_static_library_file_path(self, command_list, static_link_list, static_lib):
        def get_path_delimiter(file_path):
            if not cslib.is_windows() or file_path.startswith('/'):
                return '/'
            elif cslib.is_windows() or (not file_path.startswith('/') and file_path[1] == ':'):
                return '\\'
            return '\\'

        # 정적 라이브러리 파일명 생성
        def get_static_library_name(static_library_command):
            static_lib_name = ''
            for option in self.static_linking_option:
                if static_library_command.startswith(option):
                    static_lib_name = static_library_command[2:]
                    break
            if static_lib_name == '':
                return ''
            return 'lib' + static_lib_name + '.a'

        if os.path.isfile(static_lib) and static_lib.endswith('.a'):
            if cslib.is_unit_testing():
                return static_lib
            else:
                return os.path.abspath(static_lib)

        static_library_name = get_static_library_name(static_lib)
        libcsbuild.write_csbuild_log('static_library_name: ' + static_library_name)

        # 정적 라이브러리 경로 추출 및 검증
        static_library_dir_list = [dir_path[2:] for dir_path in command_list if dir_path.startswith('-L')]
        for dir_path in static_library_dir_list:
            if not os.path.isabs(dir_path):
                dir_path = cslib.make_absolute_path(self.build_location, dir_path)
            static_library_full_path = dir_path + get_path_delimiter(dir_path) + static_library_name

            if static_library_full_path in static_link_list:
                if os.path.isfile(static_library_full_path):
                    libcsbuild.write_csbuild_log('static_library_full_path: ' + static_library_full_path)
                    return static_library_full_path
                elif cslib.is_unit_testing():
                    libcsbuild.write_csbuild_log('static_library_full_path: ' + static_library_full_path)
                    return static_library_full_path
                else:
                    continue
        return ''

    def is_static_library_file(self, static_lib, command_list, static_link_list):
        static_library_file = self.get_static_library_file_path(command_list, static_link_list, static_lib)
        if static_library_file != '':
            return True
        return False


def get_toolset(invoked_command):
    tool_exec_file_path = invoked_command
    tool_basename = os.path.basename(tool_exec_file_path).lower()
    tool_name, ext = os.path.splitext(tool_basename)

    return GnuCompilerTool()

