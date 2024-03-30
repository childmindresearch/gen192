"""Test gen192.cli"""

import os
import pathlib as pl
import tempfile
from typing import Any

import pytest
from pytest_mock import MockerFixture

import gen192.cli as cli


class TestPipelineConfig:
    @pytest.mark.parametrize("notes", [(None), ("hello world")])
    def test_init_class(self, tmp_path: pl.Path, notes: str | None) -> None:
        pipeline_inputs: list[Any] = ["pipeline_config", tmp_path, {}, notes]
        pipeline_cfg = cli.PipelineConfig(*pipeline_inputs)
        assert isinstance(pipeline_cfg, cli.PipelineConfig)

        for idx, (cfg_input, cfg_type) in enumerate(
            zip(
                pipeline_cfg.__dict__.values(),
                [str, pl.Path, dict, str | None],
            )
        ):
            assert isinstance(cfg_input, cfg_type)  # type: ignore [arg-type]
            assert cfg_input == pipeline_inputs[idx]

    def test_clone(self, test_config: cli.PipelineConfig) -> None:
        pipeline_cfg = test_config.clone()

        assert pipeline_cfg == test_config

    def test_set_name(self, test_config: cli.PipelineConfig, new_name: str = "RandomPipeline") -> None:
        # Set up test pipeline config
        test_config.set_name(new_name)
        assert test_config.name == new_name
        assert test_config.config["pipeline_setup"]["pipeline_name"] == new_name

    def test_dump_file_exists_error(self, test_config: cli.PipelineConfig, mocker: MockerFixture) -> None:
        mocker.patch.object(
            test_config,
            "dump",
            side_effect=FileExistsError(f"File {test_config.file} already exists"),
        )
        with pytest.raises(FileExistsError, match="already exists"):
            test_config.dump(exist_ok=False)

    @pytest.mark.parametrize("exist_ok", [(True), (False)])
    def test_dump_file_valid(self, test_config: cli.PipelineConfig, exist_ok: bool) -> None:
        with tempfile.NamedTemporaryFile() as out_file:
            if not exist_ok:
                os.remove(out_file.name)
            test_config.file = pl.Path(out_file.name)
            test_config.dump(exist_ok=exist_ok)

            assert os.path.exists(out_file.name)


class TestPipelineCombination: ...


class TestIterPipelineCombis:
    # Combine both "all" and "no_duplicate" testing here
    # TODO: refactor into single function
    ...


class TestLoadPipelineConfig: ...


class TestGeneratePipelineFromCombi: ...


class TestMain:
    # Test for entry point / end-to-end run
    ...
