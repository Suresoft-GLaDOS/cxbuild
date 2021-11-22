class ICompilerTool(object):
    """Interfaces for compiler's common query"""

    def split_command(self):
        """ split command to (option list) and (source file list) tuple """
        raise NotImplementedError()

    def get_system_include_list(self):
        raise NotImplementedError()

    def get_include_option_name(self):
        """ return compiler include option name(like -I, --include)"""
        raise NotImplementedError()

    def get_predefined_macro(self):
        raise NotImplementedError()