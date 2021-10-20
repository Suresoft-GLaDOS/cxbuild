from wcmatch import glob


def fnmatch(name, pattern):
    """
    Case Insensitive glob match extension
    """
    return glob.globmatch(name, pattern, flags=glob.GLOBSTAR | glob.EXTGLOB | glob.IGNORECASE | glob.DOTMATCH)
