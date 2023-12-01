"""Test everything."""

import os
import pathlib as pl

from gen192 import utils


def test_cd(tmp_path: pl.Path) -> None:
    """Test cd context manager."""
    cwd = os.getcwd()
    with utils.cd(tmp_path):
        assert os.getcwd() == str(tmp_path)
    assert os.getcwd() == cwd


def test_filesafe() -> None:
    """Test filesafe function."""
    assert utils.filesafe("hello world") == "hello-world"
    assert utils.filesafe("hello world", "_") == "hello_world"
    assert utils.filesafe("hello world", "") == "helloworld"
    assert utils.filesafe("hello world", " ") == "hello world"
