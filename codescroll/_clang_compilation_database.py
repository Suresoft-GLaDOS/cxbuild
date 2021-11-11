import json
from codescroll.runner import *
import compiler


class _ClangCompilationDatabaseExport(Runner):
    def start(self, _, project_json_filepath=None):
        if not os.path.exists(project_json_filepath):
            return False, None

        with open(project_json_filepath, "r") as project_json_file:
            project_json = json.load(project_json_file)
            compile_commands_json_path = os.path.join(libcsbuild.get_working_dir(), "compile_commands.json")
            if os.path.exists(compile_commands_json_path):
                os.remove(compile_commands_json_path)

            include_cache = {}
            with open(compile_commands_json_path, 'w', encoding='utf-8') as f:
                compile_db = []
                for module in project_json['modules']:
                    for compile_info in module['sources']:
                        compiler_path = compile_info['compiler']
                        commands = compile_info['command']

                        toolset = compiler.create(compiler_path, commands)

                        # extract include
                        if compiler_path not in include_cache:
                            includes = toolset.get_system_include_list()
                            include_cache[compiler_path] = includes
                        else:
                            includes = include_cache[compiler_path]

                        # add hidden system include

                        directory = compile_info['buildLocation']

                        file = compile_info['originalPath']

                        # It doesn't seem to have to be a relative path.
                        # file = os.path.relpath(file, directory)

                        for include in includes:
                            commands.append(toolset.get_include_option_name())
                            commands.append(include)

                        commands.append(file)
                        compile_db.append({"directory": directory, "command": " ".join(commands), "file": file})

                json.dump(compile_db, f, indent=4)

        libcsbuild.step_message("compile_commands.json written [%s]" % compile_commands_json_path)
        return True, compile_commands_json_path
