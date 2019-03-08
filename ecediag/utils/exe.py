from shutil import which
import contextlib
import os


def find_exe(name, add_paths=[]):
    """
    Check whether `name` is on PATH and marked as executable.
    Return path to executable
    """
    add_paths.append(os.environ.get("PATH"))
    prependedPath = ":".join(add_paths)

    with set_env(PATH=prependedPath):
        # print(os.environ.get("PATH"))
        # return which(name) is not None
        return which(name)


@contextlib.contextmanager
def set_env(**environ):
    """
    Temporarily set the process environment variables.

    >>> with set_env(PLUGINS_DIR=u'test/plugins'):
    ...   "PLUGINS_DIR" in os.environ
    True

    >>> "PLUGINS_DIR" in os.environ
    False

    :type environ: dict[str, unicode]
    :param environ: Environment variables to set
    """
    old_environ = dict(os.environ)
    os.environ.update(environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_environ)
