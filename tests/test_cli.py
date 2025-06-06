"""Test gen192.cli"""

import itertools as it
import os
import pathlib as pl
import random
import shutil
import tempfile
from typing import Any, Generator

import pytest
from pytest_mock import MockerFixture

import gen192.cli as cli
from gen192.utils import filesafe


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
        with mocker.patch("builtins.open", side_effect=FileExistsError("File already exists")):
            mocker.patch.object(test_config, "_file_exists", return_value=True)
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

    def test_dump_notes(self, test_config: cli.PipelineConfig) -> None:
        test_config.notes = "Hello world"
        with tempfile.NamedTemporaryFile() as out_file:
            test_config.file = pl.Path(out_file.name)
            test_config.dump(exist_ok=True)

        assert os.path.exists(f"{test_config.file}.notes.txt")


@pytest.fixture()
def test_combi() -> cli.PipelineCombination:
    pipeline_step = cli.PipelineStep(name="TestPipeline", merge_paths=[["path1", "path2"]])

    return cli.PipelineCombination(
        pipeline_id="1",
        pipeline_perturb_id="2",
        step=pipeline_step,
        # connectivity_method="connectivity_method1",
        use_nuisance_correction=True,
    )


@pytest.fixture()
def test_combi_name(test_combi: cli.PipelineCombination) -> str:
    return (
        f"base-{filesafe(test_combi.pipeline_id)}_"
        f"perturb-{filesafe(test_combi.pipeline_perturb_id)}_"
        f"step-{filesafe(test_combi.step.name)}_"
        # f"conn-{filesafe(test_combi.connectivity_method)}_"
        f"nuisance-{filesafe(str(test_combi.use_nuisance_correction))}"
    )


class TestPipelineCombination:
    def test_init_class(self, test_combi: cli.PipelineCombination) -> None:
        for var_input, var_type in zip(test_combi.__dict__.values(), [str, str, cli.PipelineStep, str, bool]):
            assert isinstance(var_input, var_type)

    def test_name(self, test_combi: cli.PipelineCombination, test_combi_name: str) -> None:
        pipeline_num = random.randint(1, 192)
        pipeline_name = test_combi.name(pipeline_num=pipeline_num)
        assert pipeline_name == f"p{pipeline_num:03d}_{test_combi_name}"
        assert isinstance(pipeline_name, str)

    def test_filename(self, test_combi: cli.PipelineCombination, test_combi_name: str) -> None:
        pipeline_num = random.randint(1, 192)
        test_fname = test_combi.filename(pipeline_num)

        assert test_fname == f"p{pipeline_num:03d}_{test_combi_name}.yml"
        assert isinstance(test_fname, str)


class TestIterPipelineCombis:
    @pytest.fixture
    def expected_combis(self) -> int:
        return len(
            list(
                it.product(
                    cli.PIPELINE_NAMES,
                    cli.PIPELINE_NAMES,
                    cli.PIPELINE_STEPS,
                    cli.CONNECTIVITY_METHODS,
                    cli.NUISANCE_METHODS,
                )
            )
        )

    def test_iter_all_combis(self, expected_combis: int) -> None:
        actual_combis = list(cli.iter_pipeline_combis())

        assert len(actual_combis) == expected_combis

    def test_iter_no_duplicates(self, expected_combis: int) -> None:
        actual_combis = list(cli.iter_pipeline_combis_no_duplicates())

        assert len(actual_combis) < expected_combis


class TestLoadPipelineConfig:
    def test_load_pipeline_config(self, test_config: cli.PipelineConfig) -> None:
        with tempfile.NamedTemporaryFile() as tmp_file:
            test_config.file = pl.Path(tmp_file.name)
            test_config.dump(exist_ok=True)

            new_config = cli.load_pipeline_config(pl.Path(tmp_file.name))
            assert isinstance(new_config, cli.PipelineConfig)
            assert new_config.name == test_config.name
            assert new_config.file == test_config.file
            assert new_config.config == test_config.config


@pytest.fixture
def test_configs(test_config: cli.PipelineConfig) -> cli.ConfigLookupTable:
    return {"1": test_config, "2": test_config}


class TestGeneratePipelineFromCombi:
    def test_generate_pipeline_from_combi_w_warnings(
        self,
        test_combi: cli.PipelineCombination,
        test_configs: cli.ConfigLookupTable,
        capsys: Generator[pytest.CaptureFixture[str], None, None],
    ) -> None:
        # Change merge path in one config to
        pipeline = cli.generate_pipeline_from_combi(
            1,
            combi=test_combi,
            configs=test_configs,
        )
        captured = capsys.readouterr().out  # type: ignore
        assert "Can't find path" in captured
        assert "identical to target" in captured

        assert isinstance(pipeline, cli.PipelineConfig)


class TestMain:
    def test_main(self, capsys: Generator[pytest.CaptureFixture[str], None, None]) -> None:
        # Remove existing distribution dirs for testing
        if os.path.exists("build"):
            shutil.rmtree("build")
        cli.main()
        captured = capsys.readouterr().out  # type: ignore
        for msg in [
            "Loaded pipeline",
            "Generating base pipeline",
            "Generated pipeline",
            "Generating 192 permutations",
            "> Generating",
        ]:
            assert msg in captured
