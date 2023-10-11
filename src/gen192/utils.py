import os
import re
from contextlib import contextmanager


@contextmanager
def cd(path):
    """Context manager for changing the working directory"""
    old_wd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_wd)


def filesafe(s: str, replacement: str = "-"):
    """
    Converts a string to a file safe string.
    Removes all non-alphanumeric characters and
    replaces them with the replacement string.
    """
    return re.sub(r"[^\w\d-]", replacement, s).lower()
