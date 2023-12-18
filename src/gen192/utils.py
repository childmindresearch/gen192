import base64
import hashlib
import os
import re
from contextlib import contextmanager
from typing import Any, Generator, Sequence


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


def print_warning(msg: str) -> None:
    """Prints a colored warning message to the console"""
    print(f"\033[93mWARNING: {msg}\033[0m")


def multi_get(obj: dict, index: Sequence) -> Any | None:  # noqa: ANN401
    """
    Gets a value from a nested dictionary.
    Returns None if the path does not exist.
    """
    for i in index:
        if not isinstance(obj, dict) or i not in obj:
            return None
        obj = obj[i]
    return obj


def multi_set(obj: dict, index: Sequence, value: Any) -> bool:  # noqa: ANN401
    """
    Sets a value in a nested dictionary.
    Returns True if the path exists or was able to be created
    and the value was set.
    """
    for idx, i in enumerate(index):
        if not isinstance(obj, dict):
            return False

        if idx == len(index) - 1:
            obj[i] = value
            return True

        if i not in obj:
            obj[i] = {}

        obj = obj[i]
    assert False


def multi_del(obj: dict, index: Sequence) -> Any | None:  # noqa: ANN401
    """
    Deletes a value from a nested dictionary.
    Returns the value if the path exists and
    the value was deleted.
    """
    for idx, i in enumerate(index):
        if not isinstance(obj, dict):
            return None

        if idx == len(index) - 1:
            if i in obj:
                val = obj[i]
                del obj[i]
                return val
            return None

        if i not in obj:
            return None

        obj = obj[i]
    assert False


def aslist(obj: Any) -> list:  # noqa: ANN401
    """
    Converts an object to a list. If the object is
    already a list, it is returned as is.
    """
    if isinstance(obj, list):
        return obj
    return [obj]


def b64_urlsafe_hash(s: str) -> str:
    """
    Hashes a string and returns a base64 urlsafe encoded version of the hash.
    """
    return base64.urlsafe_b64encode(hashlib.sha1(s.encode()).digest()).decode().replace("=", "")
