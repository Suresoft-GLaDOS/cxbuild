import json
import shutil
import errno
import cslib
import os
import stat

from codescroll.runner import *
import compiler.toolsets

class _ArtifactBuilder(Runner):
    """
    This runner gathers all available outputs (headers, source files, shared objects, etc.)
    and zip them while preserving the file structures.
    Temporary files are ignored, because they are deleted before building is completed.
    """
    def __init__(self, extra_dependency_blacklist: set = None):
        super().__init__()
        if type(extra_dependency_blacklist) is list:
            extra_dependency_blacklist = set(extra_dependency_blacklist)
        extra_dependency_blacklist = set() if not extra_dependency_blacklist else extra_dependency_blacklist
        self._artifacts_dir_name = 'artifacts'
        self._artifacts_zip_name = 'artifacts.zip'
        self.dependency_blacklist = {
            '/dev/random',
            '/dev/urandom',
            '/dev/arandom'
        }
        self.dependency_blacklist.update(extra_dependency_blacklist)

    def start(self, options, compile_commands_json_path=None):
        if os.name != 'posix':
            raise NotImplementedError('NT system support is not implemented')
        if not os.path.exists(compile_commands_json_path):
            return False, None

        project_json_path = os.path.join(libcsbuild.get_working_dir(), "project.json")
        all_dependencies = set()
        all_compiler_paths = set()
        with open(project_json_path, "r") as project_json_file:
            project_json = json.load(project_json_file)
            for module in project_json['modules']:
                for source in module['sources']:
                    for dependency in source['dependencies']:
                        all_dependencies.add(dependency)
                    all_compiler_paths.add(source['compiler'])
        artifacts_dir_path = libcsbuild.get_working_dir() + os.sep + self._artifacts_dir_name
        if os.name == 'posix':
            for dependency in all_dependencies.difference(self.dependency_blacklist):
                if not dependency.startswith(os.sep):
                    libcsbuild.info_message(
                        'All dependency should start with \''+os.sep+'/\'. ' +
                        'Ignore \''+dependency+'\'.'
                        )
                    continue
                else:
                    src = dependency
                    if not os.path.isfile(src):
                        continue
                    if cslib.is_source_or_header_file(src):
                        continue
                    dest = artifacts_dir_path + dependency
                    if os.path.exists(dest):
                        try:
                            os.remove(dest)
                        except PermissionError as exception:
                            os.chmod(dest, stat.S_IWUSR)
                            os.remove(dest)
                    try:
                        shutil.copy(src, dest)
                    except IOError as e:
                        # ENOENT(2): file does not exist, raised also on missing dest parent dir
                        if e.errno != errno.ENOENT:
                            raise
                        # try creating parent directories
                        os.makedirs(os.path.dirname(dest))
                        shutil.copy(src, dest)
        else:  # not posix (e.g. nt system)
            raise NotImplementedError('NT system support is not implemented')

        macro_dir_path = os.path.join(artifacts_dir_path, '__macro__')
        os.makedirs(macro_dir_path, exist_ok=True)
        for compiler_path in all_compiler_paths:
            # make an empty toolset (do we need command)?
            toolset = compiler.create(compiler_path, [])
            predefined_header_name = compiler_path.replace('/', '_') + '_predefined.h'
            with open(os.path.join(macro_dir_path, predefined_header_name), 'w') as macro_file:
                macro_file.write(toolset.get_predefined_macro())

        # zip artifacts
        artifacts_zip_path = os.path.join(libcsbuild.libcsbuild.get_working_dir(), self._artifacts_zip_name)
        cslib.zip_project(artifacts_dir_path, artifacts_zip_path)
        libcsbuild.step_message("artifacts.zip written [%s]" % artifacts_zip_path)

        # FIXME: This could be dangeraous! Check if 'artifacts' dir place at temp dir is feasible (e.g. /tmp)
        shutil.rmtree(artifacts_dir_path)

        return True, artifacts_zip_path
