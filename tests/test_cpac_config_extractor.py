"""Test gen192.cpac_config_extractor"""
import os
import pathlib as pl
import sys
from typing import Generator

import pytest

from gen192 import cpac_config_extractor, utils
from gen192.cli import PIPELINE_NAMES


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


class TestFetchAndExpandCPACConfig:
    def test_fetch_and_expand(self, tmp_path: pl.Path) -> None:
        cpac_dir = tmp_path / "cpac_source"
        output_dir = tmp_path / "cpac_configs"

        cpac_config_extractor.fetch_and_expand_cpac_configs(
            cpac_dir=cpac_dir,
            output_dir=output_dir,
            checkout_sha="main",
            config_names_ids=PIPELINE_NAMES,
        )

        assert os.path.exists(cpac_dir)

        # Check output configurations exist and correctly named
        assert os.path.exists(output_dir)
        for config_name in PIPELINE_NAMES:
            assert os.path.exists(output_dir / (utils.filesafe(config_name) + ".yml"))


class TestCheckCPACConfig:
    def test_check_valid_config(self, tmp_path: pl.Path) -> None:
        ...

    def test_check_invalid_config(self, tmp_path: pl.Path) -> None:
        # Temporary block to install CPAC if it does not already exist
        cpac_dir = tmp_path / "cpac_source"
        output_dir = tmp_path / "cpac_configs"

        if not (cpac_dir / "CPAC").exists():
            cpac_dir.mkdir(parents=True, exist_ok=True)
            cpac_config_extractor._download_cpac_repo(cpac_dir=cpac_dir, checkout_sha="main")

        output_dir.mkdir(parents=True, exist_ok=True)

        if (cpac_module_path := str(cpac_dir.absolute())) not in sys.path:
            sys.path.append(cpac_module_path)

        ok, err = cpac_config_extractor.check_cpac_config("invalid")
        assert not ok
        assert err is not None
