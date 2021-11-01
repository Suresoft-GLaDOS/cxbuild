import json
from codescroll.runner import *


class ClangCompilationDatabaseExport(Runner):
    def start(self, _, project_json_filepath=None):
        if not os.path.exists(project_json_filepath):
            return False, None

        with open(project_json_filepath, "r") as project_json_file:
            project_json = json.load(project_json_file)
            compile_commands_json_path = os.path.join(libcsbuild.get_working_dir(), "compile-commands.json")
            if os.path.exists(compile_commands_json_path):
                os.remove(compile_commands_json_path)

            with open(compile_commands_json_path, 'w', encoding='utf-8') as f:
                compile_db = []
                for compile_info in project_json:
                    compiler = compile_info['compiler']
                    command = compile_info['command']
                    directory = compile_info['build_location']
                    file = compile_info['file']

                    commands = command + [file]
                    compile_db.append({"directory": directory, "command": " ".join(commands), "file": file})

                json.dump(compile_db, f, indent=4)

        return True, None



