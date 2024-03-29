"""Test gen192.cpac_config_extractor"""
import os
import pathlib as pl
from typing import Generator

import pytest

from gen192 import cpac_config_extractor


class TestDownloadCPACRepo:
    def test_download_cpac_repo_fail(
        self,
        capsys: Generator[pytest.CaptureFixture[str], None, None],
        tmp_path: pl.Path,
        checkout_sha: str = "invalid",
    ) -> None:
        with pytest.raises(SystemExit) as cmd_exit:
            cpac_config_extractor._download_cpac_repo(cpac_dir=tmp_path, checkout_sha=checkout_sha)
            captured = capsys.readouterr().out  # type: ignore
            assert "Could not checkout" in captured

        assert cmd_exit.type == SystemExit
        assert cmd_exit.value.code == 1

    def test_download_cpac_repo_valid(self, tmp_path: pl.Path) -> None:
        cpac_config_extractor._download_cpac_repo(cpac_dir=tmp_path, checkout_sha="main")
        assert os.path.exists(f"{tmp_path}/CPAC")
