import pathlib as pl
import shutil
import tempfile
import zipfile
from urllib import request

import pytest
import yaml

from gen192.cli import PipelineConfig


@pytest.fixture
def test_config() -> PipelineConfig:
    """Download and load configuration for test suite without relying on created
    methods"""
    test_config = "abcd.yml"
    zip_fname = "cpac_source_configs_RlrTzPGDmrVjfNbBigtDGkfRmp0.zip"
    config_url = f"https://github.com/childmindresearch/gen192/releases/download/dev/{zip_fname}"

    with tempfile.TemporaryDirectory() as temp_dir:
        with request.urlopen(config_url) as response, open((zip_fpath := f"{temp_dir}/{zip_fname}"), "wb") as out_zip:
            shutil.copyfileobj(response, out_zip)

        with zipfile.ZipFile(zip_fpath) as zip_file:
            zip_file.extractall(temp_dir)

        with open((test_config_path := f"{temp_dir}/{test_config}"), "r") as handle:
            test_config = yaml.safe_load(handle)

    return PipelineConfig(
        name=test_config["pipeline_setup"]["pipeline_name"],  # type: ignore [index]
        file=pl.Path(test_config_path),
        config=test_config,
    )
