import json
import shutil
import errno
import cslib
import os
import stat

from codescroll.runner import *


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
        # FIXME: Want to get project_json, not compile_commands_json.
        if not os.path.exists(compile_commands_json_path):
            return False, None

        project_json_path = os.path.join(libcsbuild.get_working_dir(), "project.json")
        all_dependencies = set()
        with open(project_json_path, "r") as project_json_file:
            project_json = json.load(project_json_file)
            for module in project_json['modules']:
                for source in module['sources']:
                    for dependency in source['dependencies']:
                        all_dependencies.add(dependency)

        artifacts_dir_path = libcsbuild.get_working_dir() + os.sep + self._artifacts_dir_name
        if os.name == 'posix':
            artifacts_dir_path = libcsbuild.get_working_dir() + os.sep + self._artifacts_dir_name
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

        # zip artifacts
        artifacts_zip_path = os.path.join(libcsbuild.libcsbuild.get_working_dir(), self._artifacts_zip_name)
        cslib.zip_project(artifacts_dir_path, artifacts_zip_path)
        libcsbuild.step_message("artifacts.zip written [%s]" % artifacts_zip_path)
        return True, artifacts_zip_path
