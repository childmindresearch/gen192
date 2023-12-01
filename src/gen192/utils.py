import os
import re
from contextlib import contextmanager
from typing import Generator


@contextmanager
def cd(path: str | os.PathLike[str]) -> Generator[None, None, None]:
    """Context manager for changing the working directory"""
    old_wd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_wd)


def filesafe(s: str, replacement: str = "-") -> str:
    """
    Converts a string to a file safe string.
    Removes all non-alphanumeric characters and
    replaces them with the replacement string.
    """
    return re.sub(r"[^\w\d-]", replacement, s).lower()
