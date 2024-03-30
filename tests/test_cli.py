"""Test gen192.cli"""

import itertools as it
import os
import pathlib as pl
import random
import tempfile
from typing import Any

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

    def test_dump_notes(self, test_config: cli.PipelineConfig) -> None:
        test_config.notes = "Hello world"
        with tempfile.NamedTemporaryFile() as out_file:
            test_config.file = pl.Path(out_file.name)
            test_config.dump(exist_ok=True)

        assert os.path.exists(f"{test_config.file}.notes.txt")


class TestPipelineCombination:
    @pytest.fixture()
    def test_combi(self) -> cli.PipelineCombination:
        return cli.PipelineCombination(
            pipeline_id=random.choice(list(cli.PIPELINE_NAMES.keys())),
            pipeline_perturb_id=random.choice(list(cli.PIPELINE_NAMES.keys())),
            step=random.choice(cli.PIPELINE_STEPS),
            connectivity_method=random.choice(cli.CONNECTIVITY_METHODS),
            use_nuisance_correction=random.choice(cli.NUISANCE_METHODS),
        )

    def test_init_class(self, test_combi: cli.PipelineCombination) -> None:
        for var_input, var_type in zip(test_combi.__dict__.values(), [str, str, cli.PipelineStep, str, bool]):
            assert isinstance(var_input, var_type)

    def test_name(self, test_combi: cli.PipelineCombination) -> None:
        pipeline_num = random.randint(1, 192)
        pipeline_name = test_combi.name(pipeline_num=pipeline_num)
        expected_name = (
            f"p{pipeline_num:03d}_"
            f"base-{filesafe(test_combi.pipeline_id)}_"
            f"perturb-{filesafe(test_combi.pipeline_perturb_id)}_"
            f"step-{filesafe(test_combi.step.name)}_"
            f"conn-{filesafe(test_combi.connectivity_method)}_"
            f"nuisance-{filesafe(str(test_combi.use_nuisance_correction))}"
        )
        assert pipeline_name == expected_name
        assert isinstance(pipeline_name, str)

    def test_filename(self, test_combi: cli.PipelineCombination) -> None:
        pipeline_num = random.randint(1, 192)
        expected_name = (
            f"p{pipeline_num:03d}_"
            f"base-{filesafe(test_combi.pipeline_id)}_"
            f"perturb-{filesafe(test_combi.pipeline_perturb_id)}_"
            f"step-{filesafe(test_combi.step.name)}_"
            f"conn-{filesafe(test_combi.connectivity_method)}_"
            f"nuisance-{filesafe(str(test_combi.use_nuisance_correction))}"
            ".yml"
        )
        test_fname = test_combi.filename(pipeline_num)

        assert test_fname == expected_name
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


class TestLoadPipelineConfig: ...


class TestGeneratePipelineFromCombi: ...


class TestMain:
    # Test for entry point / end-to-end run
    ...
