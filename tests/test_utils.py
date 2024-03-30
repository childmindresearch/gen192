"""Test gen192.utils"""

import os
import pathlib as pl
import string
from typing import Any, Generator, Sequence

import pytest

from gen192 import utils


class TestCD:
    def test_cd(self, tmp_path: pl.Path) -> None:
        """Test cd context manager"""
        cwd = os.getcwd()
        with utils.cd(path=tmp_path):
            assert os.getcwd() == str(tmp_path)
        assert os.getcwd() == cwd


class TestFileSafe:
    @pytest.mark.parametrize(
        "s",
        [
            ("hello world"),
            ("hello?world"),
            ("hello:world"),
            ("hello$world"),
        ],
    )
    def test_filesafe(self, s: str) -> None:
        """Test filesafe function."""
        assert utils.filesafe(s=s) == "hello-world"

    @pytest.mark.parametrize(
        "s, replacement, expected",
        [
            ("hello world", "_", "hello_world"),
            ("hello world", "", "helloworld"),
            ("hello?world", "_", "hello_world"),
            ("hello:world", "", "helloworld"),
            ("hello^world", "-", "hello-world"),
        ],
    )
    def test_filesafe_replacement(self, s: str, replacement: str, expected: str) -> None:
        """Test filesafe function with replacement."""
        assert utils.filesafe(s=s, replacement=replacement) == expected


class TestPrintWarning:
    def test_print_warning(self, capsys: Generator[pytest.CaptureFixture[str], None, None]) -> None:
        utils.print_warning("hello world")
        captured = capsys.readouterr().out  # type: ignore
        assert "WARNING" in captured


@pytest.fixture
def nested_dict() -> dict[str, str | dict[str, str]]:
    return {
        "a": "foo",
        "b": {
            "c": "bar",
            "d": "foo2",
        },
    }


class TestMultiGet:
    def test_multi_get_not_dict_type(self) -> None:
        obj: list[Any] = []
        assert not isinstance(obj, dict)
        assert utils.multi_get(obj=obj, index=["a"]) is None  # type: ignore [arg-type]

    @pytest.mark.parametrize("keys", [(["c"]), (["a", "c"]), (["f"])])
    def test_multi_get_not_in_dict(self, nested_dict: dict[str, str | dict[str, str]], keys: Sequence[Any]) -> None:
        assert isinstance(nested_dict, dict)
        assert utils.multi_get(obj=nested_dict, index=keys) is None

    @pytest.mark.parametrize(
        "keys, expected",
        [(["a"], "foo"), (["b", "c"], "bar"), (["b", "d"], "foo2")],
    )
    def test_multi_get_valid(
        self,
        nested_dict: dict[str, str | dict[str, str]],
        keys: Sequence[Any],
        expected: str,
    ) -> None:
        assert isinstance(nested_dict, dict)
        assert utils.multi_get(obj=nested_dict, index=keys) == expected


class TestMultiSet:
    def test_multi_set_not_dict_type(self) -> None:
        obj: list[Any] = []
        assert not isinstance(obj, dict)
        assert not utils.multi_set(obj=obj, index=["a"], value=None)  # type: ignore [arg-type]

    @pytest.mark.parametrize("keys", [(["z"]), (["b", "y"])])
    def test_multi_set_valid(self, nested_dict: dict[str, str | dict[str, str]], keys: Sequence[Any]) -> None:
        assert utils.multi_set(obj=nested_dict, index=keys, value="Test")
        assert utils.multi_get(obj=nested_dict, index=keys) == "Test"


class TestMultiDel:
    def test_multi_del_not_dict_type(self) -> None:
        obj: list[Any] = []
        assert not isinstance(obj, dict)
        assert utils.multi_del(obj=obj, index=["a"]) is None  # type: ignore [arg-type]

    @pytest.mark.parametrize("keys", [(["z"]), (["b", "y"])])
    def test_multi_del_not_in_dict(self, nested_dict: dict[str, str | dict[str, str]], keys: Sequence[Any]) -> None:
        assert utils.multi_del(obj=nested_dict, index=keys) is None

    @pytest.mark.parametrize("keys", [("a"), (["b", "c"])])
    def test_multi_del_valid(self, nested_dict: dict[str, str | dict[str, str]], keys: Sequence[Any]) -> None:
        val = utils.multi_get(obj=nested_dict, index=keys)
        assert utils.multi_del(obj=nested_dict, index=keys) == val


class TestAsList:
    @pytest.mark.parametrize("object", [(["foo"]), ({"foo"}), ("foo")])
    def test_aslist(self, object: Any) -> None:  # noqa: ANN401
        assert isinstance(utils.aslist(obj=object), list)


class Testb64UrlsafeHash:
    @pytest.mark.parametrize("s", [(""), (string.punctuation), (string.printable), (string.whitespace)])
    def test_b64_urlsafe_hash(self, s: str) -> None:
        assert "=" not in utils.b64_urlsafe_hash(s=s)
